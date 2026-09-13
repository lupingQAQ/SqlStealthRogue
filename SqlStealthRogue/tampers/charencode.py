"""sqlmap 同名: 载荷整体 URL 编码一次(wire-safe, 可作链尾)。"""
import urllib.parse


def tamper(payload, headers=None):
    return urllib.parse.quote(payload, safe='')
