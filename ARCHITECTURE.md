# Architecture

## Module Map

```
┌─────────────────────────────────────────────────────────────┐
│ SqlStealthRogue.py (thin entry)                              │
└──────────────┬──────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────┐
│ cli.py                                                      │
│  args → resolve(dbms/technique/templates) → validate        │
│  → dispatch(engine) → output/stats                          │
└──────┬───────────────────────────────┬──────────────────────┘
       ▼                               ▼
┌──────────────────────┐   ┌──────────────────────────────────┐
│ dbms/ (registry)     │   │ tampers/ (registry)              │
│  auto-discovery      │   │  auto-discovery + --tamper-dir   │
│  base inheritance    │   │  wire_encode normalization       │
│  12 engine PROFILEs  │   │  13 sqlmap-compatible tampers    │
└──────┬───────────────┘   └───────────────┬──────────────────┘
       ▼ templates                        ▼ transforms
┌─────────────────────────────────────────────────────────────┐
│ core.py                                                     │
│  Sender (thread-local keep-alive, err-mark retry)           │
│  5 algorithms: union / error(+prefetch) / bool(+bit-para)   │
│                / time / prefix                               │
│  run_rows (row parallelism, PROBE_POOL bandwidth cap)       │
│  guards: all-0xFF value / empty-row streak                  │
└─────────────────────────────────────────────────────────────┘
```

## Design Decisions

### 1. Zero negotiation, templates as data

sqlmap's "supports everything" capability = a payload matrix (DBMS × version × technique) plus an auto-negotiation phase that fires probe requests. SqlStealthRogue deletes the negotiation and externalizes the matrix into declarative PROFILE plugins. Consequence: `--dbms X --technique Y` must be user-supplied knowledge; payoff is that every request is an extraction request. This trade is the product's identity — see CONTRIBUTING for the invariant.

### 2. Five extraction algorithms, one engine-agnostic core

| algorithm | requests | oracle | notes |
|---|---|---|---|
| union | 1 per result set | regex over full response | fastest; needs column-count knowledge |
| error | 1 per 30–500 chars | SQL error message echo | chunk sizes measured per engine; adaptive window prefetch |
| bool | 8 per char (binary search) | page differentiates true/false | serial fallback engine |
| bit-parallel bool | 8 per char (parallel bits) | `char & mask > 0` | same request count, ~5× lower latency; bits are independent → batched |
| time | 8 per char, serial | response latency ≥ ¾·`--sec` | deliberately serial: parallel SLEEPs stack server load |
| prefix | ~8 per char | `^prefix[\x20-\xHH]` regex | NoSQL `$regex` standard; charset binary search |

### 3. Concurrency model: one bandwidth knob

Rows iterate on a thread pool (`--threads`), but every probe funnels through `PROBE_POOL` sized `--bwidth`. In-flight HTTP concurrency is therefore **exactly bwidth regardless of row count** — predictable load, no accidental target meltdown.

### 4. Keep-alive with honest downgrade

Thread-local persistent connections give 5.6× on HTTP/1.1 targets. Servers that answer HTTP/1.0 or `Connection: close` get zero benefit and paid overhead — so the sender detects the response version and permanently downgrades to urllib for the rest of the run. Measured, not assumed.

### 5. Failure must be cheap and loud

Two sentinel guards (zero extra requests) cap misconfiguration blast radius:

- value turns all-0xFF (true-mark matches both pages) → immediate abort (~128 requests instead of 16k+ garbage)
- 20 consecutive empty rows (error regex matches everything) → abort instead of `--max-rows` flood

`--err-mark` additionally treats backend error pages as invalid probes (retry once, then fail) so backend errors never silently masquerade as `false` bits — a corruption mode observed against real Oracle under connection storms.

### 6. Tamper contract: transform, then normalize

Tampers produce wire-ready text; `wire_encode` then preserves existing `%XX` sequences and `+`, while force-encoding only URL-structural characters (`& # ?`), whitespace and controls. One rule covers all 13 tampers and custom sqlmap-style scripts; learned the hard way when a raw `&` in a bit-probe payload silently truncated a query string.

### 7. Verification as a feature

Engines are labeled by real-machine evidence: verified ✅ / shipped-but-unverified ⚠️ / disabled-by-evidence ❌ (e.g. Oracle 23ai XMLType no longer echoes data; OceanBase lacks `extractvalue`). Interesting engine quirks found by testing are encoded in templates (openGauss `NULL||'x' = 'x'` → CASE-based row terminator; PG error-message chunk capacity ≥800 chars).

## Known Trade-offs

- Zero probing means zero self-diagnosis: wrong config yields `no rows extracted` with a hint, nothing more. `--err-mark` is the mitigation.
- Byte-wise blind extraction mangles multi-byte characters; error/union transmit whole segments.
- No redirect/auth chains beyond manual `-H` headers — it's a scalpel.
