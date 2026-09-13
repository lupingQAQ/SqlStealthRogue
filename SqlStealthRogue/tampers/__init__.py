"""tamper 插件注册表: sqlmap 同名同语义的经典绕 WAF 载荷变换 + 自定义目录扩展。

契约: tamper(payload, headers=None) -> str — 收到已就绪的完整载荷文本,
返回内容【原样上链】(不再自动 URL 编码), 因此链尾需自行保证 wire-safe
(如 space2comment 消空格 / charencode 全编码)。headers 参数允许篡改请求头
(如 xforwardedfor)。单参数 tamper(payload) 的 sqlmap 风格脚本同样兼容。
"""

import importlib
import importlib.util
import inspect
import os
import pkgutil
import re
import urllib.parse

TAMPERS = {}  # name -> {'fn':, 'desc':, 'arity':}


def _register(name, fn, mod_doc=''):
    doc = inspect.getdoc(fn) or mod_doc or ''
    TAMPERS[name] = {'fn': fn,
                     'arity': len(inspect.signature(fn).parameters),
                     'desc': doc.strip().splitlines()[0] if doc.strip() else ''}


def _load_pkg():
    for m in pkgutil.iter_modules(__path__):
        mod = importlib.import_module('.' + m.name, __package__)
        fn = getattr(mod, 'tamper', None)
        if callable(fn):
            _register(m.name, fn, mod.__doc__ or '')


def load_dir(path):
    """加载自定义 tamper 目录: 每个 *.py 暴露一个 tamper() 函数, 同名覆盖内置;
    无 tamper() 或语法损坏的文件跳过(不中断)。"""
    if not path or not os.path.isdir(path):
        return
    for fname in sorted(os.listdir(path)):
        if not fname.endswith('.py'):
            continue
        modname = 'SqlStealthRogue_tamper_' + fname[:-3]
        try:
            spec = importlib.util.spec_from_file_location(modname, os.path.join(path, fname))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception:
            continue
        fn = getattr(mod, 'tamper', None)
        if callable(fn):
            _register(fname[:-3], fn, mod.__doc__ or '')


def get_chain(names):
    chain = []
    for n in names:
        t = TAMPERS.get(n)
        if not t:
            raise KeyError(n)
        chain.append((t['fn'], t['arity']))
    return chain


def wire_encode(text):
    """tamper 输出上链前归一化: 保留已有 %XX 与 +(space2plus 语义)、括号等安全 ASCII,
    仅强制编码 URL 结构致命字符(& # ?)、空白与控制/非 ASCII — 语义不变, 传输必达。"""
    out = []
    for i, c in enumerate(text):
        o = ord(c)
        if c == '%' and re.fullmatch(r'%[0-9A-Fa-f]{2}', text[i:i + 3]):
            out.append(c)
        elif c in '&#?' or o < 0x21 or o > 0x7e:
            out.append(urllib.parse.quote(c, safe=''))
        else:
            out.append(c)
    return ''.join(out)


def apply(chain, payload, headers=None):
    for fn, arity in chain:
        payload = fn(payload, headers) if arity >= 2 else fn(payload)
    return payload


_load_pkg()
