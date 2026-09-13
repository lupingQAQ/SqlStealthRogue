"""sqlmap 同名: 每个空格随机替换为一种空白(%09/%0A/%0C/%0D//**/)。"""
import random
import re

BLANKS = ('%09', '%0A', '%0C', '%0D', '/**/')


def tamper(payload, headers=None):
    return re.sub(' ', lambda _: random.choice(BLANKS), payload)
