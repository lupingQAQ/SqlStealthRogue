"""sqlmap 同名: 载荷 URL 双重编码, 绕一层解码型 WAF(wire-safe, 可作链尾)。"""
import urllib.parse


def tamper(payload, headers=None):
    return urllib.parse.quote(urllib.parse.quote(payload, safe=''), safe='')
