# Contributing

Thanks for improving SqlStealthRogue. This project has strong design constraints — read them before contributing.

## Core Principle: Zero-Probe

Every accepted change must preserve the invariant: **no request is ever sent that is not a data-extraction request.** No fingerprinting, no version detection, no capability calibration, no availability checks. If your feature needs a probe request, it belongs behind an explicit opt-in flag with a documented traffic cost.

## Development Principles

1. **Zero dependency, pure standard library** — the tool runs anywhere Python 3.7+ runs. Do not add `requirements.txt`.
2. **Plugins over core** — new engines go in `dbms/`, new WAF bypasses go in `tampers/`. `core.py` stays engine-agnostic.
3. **Every payload claim needs evidence** — if you add or change a template, verify against a real engine (a disposable local container is fine) and state the exact version tested in the plugin's note. Unverified templates must be marked ⚠️ in the matrix.
4. **Bounded failure** — misconfiguration must abort cheaply, never flood the target. Changes that can send >O(first value) requests on bad config need a sentinel guard.
5. **Chinese + English docs stay in sync** — a README change ships with its bilingual counterpart in the same PR.

## Adding a dbms Plugin

One file in `SqlStealthRogue/dbms/`, exposing a `PROFILE` dict:

```python
PROFILE = {
    'name': 'myengine',
    'base': 'postgres',          # optional: inherit + override
    'note': 'MyEngine 1.2 (error/bool 已验证)',
    'err_tpl':   " AND 1=(SELECT CAST(...))",   # {Q}{F}{P}{N} placeholders
    'err_regex': 'type integer: "([^"]*)"',
    'err_chunk': 500,
    'err_strip': 1,              # trailing marker chars to strip
    'bool_tpl':  " AND ...>{K}",
    'bit_tpl':   " AND (...&{M})>0",
    'time_tpl':  " AND ...{T}",
    'prefix_tpl': '^{S}[\\x20-\\x{HH}]',        # NoSQL regex engines
    'union_tpl': 'id >= 0',                     # optional default for -U
    'row_wrap':  "SELECT * FROM ({Q}) x LIMIT 1 OFFSET {R}",
}
```

Contract details: [ARCHITECTURE.md](ARCHITECTURE.md).

## Adding a tamper Plugin

One file in `SqlStealthRogue/tampers/` exposing `tamper(payload, headers=None) -> str` (single-argument sqlmap-style scripts also work). Output is normalized by `wire_encode` before hitting the wire — preserve existing `%XX`, avoid structural characters.

## Commit / PR Conventions

- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`
- One logical change per commit; engine plugins grouped by family
- PR must include: what changed, which real engine/version it was verified against (or ⚠️ unverified), request-count evidence for any performance claim
- All modules must pass `python -m py_compile`

## Testing

Minimum bar for template changes — reproduce against a local disposable instance of the engine:

```
3-row fixture (normal / long value / terminator) → dump must match exactly
request count must equal the theoretical minimum ± documented overshoot
```
