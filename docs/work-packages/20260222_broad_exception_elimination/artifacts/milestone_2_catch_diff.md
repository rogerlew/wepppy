# Milestone 2 Catch Diff

## Scope

Milestone 2 narrowed broad catches in rq-engine routes while preserving canonical error payload behavior:

- `wepppy/microservices/rq_engine/job_routes.py`
- `wepppy/microservices/rq_engine/fork_archive_routes.py`
- `wepppy/microservices/rq_engine/project_routes.py`
- `wepppy/microservices/rq_engine/bootstrap_routes.py`
- `wepppy/microservices/rq_engine/omni_routes.py`

Regression tests added/updated:
- `tests/microservices/test_rq_engine_fork_archive_routes.py`
- `tests/microservices/test_rq_engine_bootstrap_routes.py`
- `tests/microservices/test_rq_engine_omni_routes.py`

## Catch Count Delta (Touched Files)

Checker source: `python3 tools/check_broad_exceptions.py --json`

| File | Before | After | Delta |
|------|-------:|------:|------:|
| `wepppy/microservices/rq_engine/bootstrap_routes.py` | 17 | 16 | -1 |
| `wepppy/microservices/rq_engine/omni_routes.py` | 15 | 12 | -3 |
| `wepppy/microservices/rq_engine/fork_archive_routes.py` | 12 | 11 | -1 |
| `wepppy/microservices/rq_engine/project_routes.py` | 10 | 8 | -2 |
| `wepppy/microservices/rq_engine/job_routes.py` | 6 | 5 | -1 |
| **Total (touched files)** | **60** | **52** | **-8** |

Global checker summary:
- Before Milestone 2 (from Milestone 1 snapshot): `1120` unsuppressed broad catches.
- After Milestone 2: `1112` unsuppressed broad catches.
- Net reduction: `-8`.

## Commands Run

- `python3 tools/check_broad_exceptions.py --json` -> pass (report generated; non-zero exit expected while findings exist).
- `python3 -m py_compile wepppy/microservices/rq_engine/bootstrap_routes.py wepppy/microservices/rq_engine/omni_routes.py wepppy/microservices/rq_engine/job_routes.py wepppy/microservices/rq_engine/fork_archive_routes.py wepppy/microservices/rq_engine/project_routes.py tests/microservices/test_rq_engine_bootstrap_routes.py tests/microservices/test_rq_engine_omni_routes.py tests/microservices/test_rq_engine_fork_archive_routes.py` -> pass.
- `wctl run-pytest tests/microservices/test_rq_engine_fork_archive_routes.py tests/microservices/test_rq_engine_omni_routes.py tests/microservices/test_rq_engine_bootstrap_routes.py tests/microservices/test_rq_engine_jobinfo.py tests/microservices/test_rq_engine_project_routes.py` -> blocked (Docker socket unavailable in this execution environment).
- `PYTHONPATH=/workdir/wepppy python3 -m pytest -rs tests/microservices/test_rq_engine_fork_archive_routes.py tests/microservices/test_rq_engine_omni_routes.py tests/microservices/test_rq_engine_bootstrap_routes.py tests/microservices/test_rq_engine_jobinfo.py tests/microservices/test_rq_engine_project_routes.py` -> skipped (`fastapi` missing in host Python env).

## Residual Risks / Deferred Items

- Several rq-engine contract concerns discovered by reviewer (async enqueue status code consistency, auth error classification, polling auth-mode contract mismatch) were already pre-existing and are deferred to later milestone batches to avoid contract churn during this minimal narrowing pass.
- Full microservices validation remains pending in canonical `wctl` runtime.
