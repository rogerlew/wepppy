# Code Review Findings - RQ Worker Startup and NoDb Redis Cache Hardening

**Status**: Complete  
**Review date**: 2026-04-24 UTC  
**Reviewers**: Codex + independent `reviewer` agent rounds

## Scope Reviewed
- `wepppy/nodb/base.py`
- `tests/nodb/test_base_unit.py`
- `tests/nodb/test_base_misc.py`
- `docker/rq-worker-startup.sh`
- `docker/docker-compose.prod.yml`
- `docker/docker-compose.prod.worker.yml`
- `tests/docker/unit/test_rq_worker_startup_contract.py`
- `docker/README.md`

## Findings

| ID | Severity | File | Finding | Disposition |
|----|----------|------|---------|-------------|
| CR-01 | High | `wepppy/nodb/base.py` | `dump()` could proceed when any lock existed, even if local token ownership was lost. | Resolved - added `_assert_lock_owned_for_dump()` token checks before persistence. |
| CR-02 | Medium | `wepppy/nodb/base.py` | `locked()` failure path force-unlocked via `flag="-f"`, potentially clearing another owner lock. | Resolved - removed force-unlock fallback and preserve foreign lock on ownership mismatch. |
| CR-03 | Medium | `wepppy/nodb/base.py` | `_ensure_redis_lock_client()` could leave stale globals after failed `ping()`. | Resolved - allocate local client/pool first and set globals only on successful ping; clear globals on exception. |
| CR-04 | Medium | `tests/nodb/test_base_unit.py` | Missing explicit coverage for `dump()` guard branches (missing distributed lock, missing local token). | Resolved - added branch coverage tests for both failure modes and side effects. |
| CR-05 | Medium | `tests/docker/unit/test_rq_worker_startup_contract.py` | Startup contract checks initially validated only `RQ_REDIS_URL`; `REDIS_URL` alignment risk remained. | Resolved - contract tests now assert both env entries enforce `${RQ_REDIS_URL:?...}`. |

## Resolution Summary
- Two independent review rounds were executed.
- All high/medium findings were fixed in code/config/docs and re-validated.
- Post-fix reviewer rerun reported no remaining high/medium findings.

## Verification Evidence
- `wctl run-pytest tests/nodb/test_base_misc.py tests/nodb/test_base_unit.py tests/docker/unit/test_rq_worker_startup_contract.py --maxfail=1` -> `61 passed`.
