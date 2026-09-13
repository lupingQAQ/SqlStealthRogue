"""sqlmap 同名: UNION ALL -> UNION。"""
import re


def tamper(payload, headers=None):
    return re.sub(r'(?i)union\s+all', 'UNION', payload)
