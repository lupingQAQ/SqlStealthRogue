"""sqlmap 同名(MySQL): 关键字包 /*!0kw*/ 版本注释, 中间件常不解析带版本注释的关键字。"""
import re

KW = (r'\b(?:and|or|not|select|union|all|from|where|substr|substring|ascii|sleep|'
      r'if|between|like|case|when|then|else|end|order|by|limit|offset|fetch|next|rows|only)\b')


def tamper(payload, headers=None):
    return re.sub(r'(?i)' + KW, lambda m: '/*!0' + m.group(0) + '*/', payload)
