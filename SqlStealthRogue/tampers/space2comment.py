"""sqlmap 同名: 空格 -> /**/ 注释, 最常用的去空格特征变换。"""


def tamper(payload, headers=None):
    return payload.replace(' ', '/**/')
