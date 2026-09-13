"""sqlmap 同名(IIS/ASP): 每字符前加 %, 依赖 IIS 宽容解析, 建议 POST 场景使用。"""


def tamper(payload, headers=None):
    return ''.join('%' + c for c in payload)
