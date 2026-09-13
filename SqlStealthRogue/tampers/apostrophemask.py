"""sqlmap 同名: 单引号 -> UTF-8 全角引号 %EF%BC%87, 绕简单引号过滤(依赖目标宽字符归一化)。"""


def tamper(payload, headers=None):
    return payload.replace("'", '%EF%BC%87')
