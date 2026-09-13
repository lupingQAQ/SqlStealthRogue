# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/); versioning follows [SemVer](https://semver.org/).

## [1.0.0] - 2026-09-14

Initial public release.

### feat

- **Zero-probe extraction core**: 5 algorithms (union / error / boolean / time / prefix); every request sent is a data-extraction request, verified by per-request accounting on a mock harness and 12 real engines
- **12 engine plugins** with real-machine verification: MySQL 8, PostgreSQL 14, MSSQL 2022, SQLite, Redis, MongoDB 7, openGauss 5, OceanBase CE, Oracle 23ai Free, Elasticsearch 8, Milvus 2.4, pgvector — drop-in `dbms/` plugin registry with `base` inheritance
- **High-speed engines**: bit-parallel blind extraction (5.35× measured, request count unchanged), HTTP keep-alive with HTTP/1.0 auto-downgrade (5.6× measured), adaptive error-chunk prefetch, measured per-engine chunk sizes (600-char value: 22 → 6 requests on PG/MSSQL)
- **WAF-bypass tamper framework**: 13 sqlmap-compatible tampers, composable chains, custom plugin directories (`--tamper-dir`), zero extra traffic
- **Minimal-blast-radius failure handling**: static validation (0 packets), sentinel guards against always-true true-mark and always-matching regex (~128 packets cap instead of 16k+), `--err-mark` invalid-probe retry to prevent silent data corruption
- **Bilingual docs** (EN + zh-CN), MIT license, SECURITY/CONTRIBUTING/ARCHITECTURE docs

### Engine-evidence notes

- Oracle 23ai: error technique disabled (XMLType no longer echoes data); template preserved in `dbms/oracle.py` for older versions
- OceanBase: error technique disabled (no `extractvalue`, CAST returns warning not error in MySQL mode)
- openGauss quirks handled: `NULL || 'x' = 'x'` concat semantics, md5 dual-hash auth
- Redis/Elasticsearch time templates shipped but not lab-verified (⚠️ in matrix)
