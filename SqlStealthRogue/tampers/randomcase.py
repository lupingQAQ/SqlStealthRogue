"""sqlmap 同名: SQL 关键字随机大小写, 绕大小写敏感的特征规则。"""
import random
import re

KEYWORDS = set('''and or not select union all from where substr substring ascii sleep
if between like is null case when then else end order by limit offset fetch next
rows only char unicode concat extractvalue updatexml cast xmltype bitand waitfor
delay eval this charcodeat doc'''.split())


def _randcase(m):
    w = m.group(0)
    if w.lower() not in KEYWORDS:
        return w
    return ''.join(c.upper() if random.random() < 0.5 else c.lower() for c in w)


def tamper(payload, headers=None):
    return re.sub(r'[A-Za-z_]{2,}', _randcase, payload)
