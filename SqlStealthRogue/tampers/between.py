"""sqlmap 同名: 比较符 > N 替换为 NOT BETWEEN 0 AND N, 消除 > 特征(会引入空格, 常配 space2comment)。"""
import re


def tamper(payload, headers=None):
    return re.sub(r'>(\s*)(\d+)', r' NOT BETWEEN 0 AND \g<1>\g<2>', payload)
