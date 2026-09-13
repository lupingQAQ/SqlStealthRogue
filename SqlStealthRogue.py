#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SqlStealthRogue 入口 — 实现在 SqlStealthRogue/ 包中: core.py(引擎) + cli.py + dbms/(插件)。

插件目录 SqlStealthRogue/dbms/ 下新增一个 PROFILE 模块即支持一个新数据库。
用法与支持矩阵: python SqlStealthRogue.py -h / --list
仅限已授权的安全测试使用。
"""

from SqlStealthRogue.cli import main

if __name__ == '__main__':
    main()
