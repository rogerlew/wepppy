# Broad Exception Baseline (2026-02-22)

This baseline is an AST-based inventory of broad exception handlers in production scope (`wepppy/` + `services/`).

## How this baseline was generated

Command:

```bash
python3 tools/check_broad_exceptions.py --json
```

Notes:
- The checker honors inline suppressions on the `except` line: `# noqa: BLE001` and `# broad-except: ...`.
- Counts below reflect **unsuppressed** findings.

## Summary

- Python files scanned: `705`
- Broad exception handlers found: `1120`
  - `bare-except`: `96`
  - `except-Exception`: `1024`
  - `except-BaseException`: `0`
- Suppressed broad handlers (excluded from findings): `6`
- Parse errors: `0`

## Counts by subsystem (selected)

- `wepppy/weppcloud`: `249`
- `wepppy/microservices/rq_engine`: `174`
- `wepppy/rq`: `162`
- `wepppy/nodb`: `141`
- `wepppy/query_engine`: `26`
- `services/cao`: `71`

## Top files (by broad handlers)

| Count | File |
|------:|------|
| 29 | `wepppy/rq/project_rq.py` |
| 26 | `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` |
| 25 | `wepppy/nodb/base.py` |
| 18 | `wepppy/profile_recorder/assembler.py` |
| 17 | `wepppy/microservices/rq_engine/bootstrap_routes.py` |
| 17 | `wepppy/rq/batch_rq.py` |
| 15 | `wepppy/microservices/rq_engine/omni_routes.py` |
| 15 | `wepppy/nodb/core/watershed.py` |
| 14 | `services/cao/src/cli_agent_orchestrator/api/main.py` |
| 14 | `wepppy/weppcloud/routes/nodb_api/project_bp.py` |
| 13 | `wepppy/export/arc_export.py` |
| 13 | `wepppy/profile_recorder/playback.py` |
| 13 | `wepppy/rq/culvert_rq.py` |
| 13 | `wepppy/weppcloud/routes/nodb_api/climate_bp.py` |
| 12 | `wepppy/microservices/rq_engine/fork_archive_routes.py` |

