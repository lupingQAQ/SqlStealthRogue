"""OceanBase (MySQL 模式) — bool/time/union 真机已验证(CE 4.x mini)。
MySQL 模式未实现 extractvalue/updatexml, CAST 非 SQLSTRICT 报错, error 判不可用已关;
Oracle 模式用 --dbms oracle。"""

PROFILE = {
    'name': 'oceanbase',
    'base': 'mysql',
    'note': 'OceanBase MySQL 模式 (bool/time/union 已验证; 无 extractvalue, error 已关; Oracle 模式用 --dbms oracle)',
    'err_tpl':   None,
    'err_regex': None,
}
