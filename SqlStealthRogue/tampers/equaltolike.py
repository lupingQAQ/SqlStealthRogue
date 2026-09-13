"""sqlmap 同名: = 替换为 LIKE(会引入空格, 常配 space2comment)。"""
import re


def tamper(payload, headers=None):
    return re.sub(r'(?<![<>!=])=(?![=>])', ' LIKE ', payload)
