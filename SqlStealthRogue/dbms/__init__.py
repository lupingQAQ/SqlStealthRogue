"""dbms 插件注册表: 本目录下每个模块暴露 PROFILE dict 即自动注册。

PROFILE 字段(均可选, 详见各模块):
  name        注册名
  base        继承的父 profile 名(子覆盖父)
  note        --list 展示的说明
  err_tpl / err_regex / err_chunk / err_strip   报错模式
  bool_tpl / time_tpl / prefix_tpl             盲注/时间/前缀模式
  union_tpl   UNION 默认载荷(通常仍需 -U 按页面列数定制)
  row_wrap    行迭代自动包裹语法(含 {Q} {R})

新增一个库 = 在本目录加一个 .py 文件, 零注册代码。
"""

import importlib
import pkgutil

PROFILES = {}


def _load():
    for m in pkgutil.iter_modules(__path__):
        mod = importlib.import_module('.' + m.name, __package__)
        p = getattr(mod, 'PROFILE', None)
        if p and 'name' in p:
            PROFILES[p['name']] = p


def get(name):
    """取 profile 并沿 base 链合并(父字段先铺底, 子字段覆盖)。"""
    p = PROFILES[name]
    chain, base = [p], p.get('base')
    while base:
        parent = PROFILES[base]
        chain.append(parent)
        base = parent.get('base')
    merged = {}
    for ancestor in reversed(chain):
        merged.update({k: v for k, v in ancestor.items() if k not in ('base',)})
    return merged


_load()
