"""Milvus — 注入面: 查询 API 的 expr 参数值。
union: 直接改写 expr 为全真表达式, 一次拉回全部实体(含目标标量字段), --regex 从响应 JSON 提取。
bool/time: 表达式语言无字符函数与受控延时, 未内置。
Milvus 2.4 真机已验证(union)。"""

PROFILE = {
    'name': 'milvus',
    'note': 'Milvus expr 注入 (union 全量拉取, 已验证)',
    'err_tpl':   None,
    'err_regex': None,
    'err_chunk': 30,
    'err_strip': 0,
    'bool_tpl':  None,
    'time_tpl':  None,
    'union_tpl': 'id >= 0',
    'row_wrap':  None,
}
