"""sqlmap 同名: 空格 -> + (query string 中按空格解析)。"""


def tamper(payload, headers=None):
    return payload.replace(' ', '+')
