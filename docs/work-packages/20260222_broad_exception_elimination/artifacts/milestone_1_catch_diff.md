# Milestone 1 Catch Diff

## Scope

Milestone 1 added characterization tests only (no production catch narrowing yet):
- `tests/microservices/test_rq_engine_jobinfo.py`
- `tests/nodb/test_base_unit.py`
- `tests/weppcloud/routes/test_wepp_bp.py`
- `tests/weppcloud/routes/test_user_profile_token.py`
- `tests/query_engine/test_mcp_router.py`

## Before/After Broad-Catch Counts

Checker source: `python3 tools/check_broad_exceptions.py --json`

- Before Milestone 1:
  - scanned files: `705`
  - unsuppressed broad catches: `1120`
  - bare catches: `96`
  - `except Exception`: `1024`
  - `except BaseException`: `0`
  - suppressed broad catches: `6`
- After Milestone 1:
  - scanned files: `705`
  - unsuppressed broad catches: `1120`
  - bare catches: `96`
  - `except Exception`: `1024`
  - `except BaseException`: `0`
  - suppressed broad catches: `6`

Delta: `0` (expected; test-only milestone).

## Commands Run

- `wctl run-pytest tests/tools/test_check_broad_exceptions.py --maxfail=1` -> blocked (Docker socket unavailable in this execution environment).
- `python3 -m pytest tests/tools/test_check_broad_exceptions.py --maxfail=1` -> pass (`3 passed`).
- `python3 -m py_compile tools/check_broad_exceptions.py tests/tools/test_check_broad_exceptions.py tests/microservices/test_rq_engine_jobinfo.py tests/nodb/test_base_unit.py tests/weppcloud/routes/test_wepp_bp.py tests/weppcloud/routes/test_user_profile_token.py tests/query_engine/test_mcp_router.py` -> pass.
- `python3 -m pytest tests/microservices/test_rq_engine_jobinfo.py --maxfail=1 -rs` -> skipped (missing optional dependency `fastapi`).
- `python3 -m pytest tests/nodb/test_base_unit.py --maxfail=1 -rs` -> error (missing optional dependency `jsonpickle`).
- `python3 -m pytest tests/weppcloud/routes/test_wepp_bp.py --maxfail=1 -rs` -> skipped (missing optional dependency `flask`).
- `python3 -m pytest tests/weppcloud/routes/test_user_profile_token.py --maxfail=1 -rs` -> skipped (missing optional dependency `flask`).
- `python3 -m pytest tests/query_engine/test_mcp_router.py --maxfail=1 -rs` -> skipped (missing optional dependency `starlette`).

## Residual Risks / Deferred Items

- Characterization tests for rq-engine/NoDb/WEPPcloud/query-engine were authored but not fully executable in this host Python environment due missing optional dependencies and unavailable Docker socket for `wctl` execution.
- Milestone 1 validation is pending rerun in canonical `wctl` runtime.
