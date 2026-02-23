# Milestone 3 Catch Diff

## Scope

Milestone 3 narrowed selected broad catches in RQ worker code while preserving worker publish/log/re-raise semantics:

- `wepppy/rq/project_rq.py`
- `wepppy/rq/batch_rq.py`
- `wepppy/rq/omni_rq.py`

Regression tests added:
- `tests/rq/test_project_rq_readonly.py`

## Catch Count Delta (Touched Files)

Checker source: `python3 tools/check_broad_exceptions.py --json`

| File | Before | After | Delta |
|------|-------:|------:|------:|
| `wepppy/rq/project_rq.py` | 29 | 27 | -2 |
| `wepppy/rq/batch_rq.py` | 17 | 16 | -1 |
| `wepppy/rq/omni_rq.py` | 11 | 10 | -1 |
| **Total (touched files)** | **57** | **53** | **-4** |

Global checker summary:
- Before Milestone 3 (from Milestone 2 snapshot): `1112` unsuppressed broad catches.
- After Milestone 3: `1108` unsuppressed broad catches.
- Net reduction: `-4`.

## Commands Run

- `python3 tools/check_broad_exceptions.py wepppy/rq/project_rq.py wepppy/rq/batch_rq.py wepppy/rq/culvert_rq.py wepppy/rq/wepp_rq.py wepppy/rq/omni_rq.py` -> pass (report generated; non-zero exit expected while findings exist).
- `python3 tools/check_broad_exceptions.py wepppy services` -> pass (report generated; non-zero exit expected while findings exist).
- `python3 -m py_compile wepppy/rq/batch_rq.py wepppy/rq/omni_rq.py wepppy/rq/project_rq.py tests/rq/test_project_rq_readonly.py` -> pass.
- `wctl run-pytest tests/rq/test_exception_logging.py tests/rq/test_wepp_rq_stage_post.py --maxfail=1` -> pass (`6 passed`).
- `wctl run-pytest tests/rq/test_project_rq_readonly.py --maxfail=1` -> pass (`3 passed`).
- `python3 -m pytest tests/rq/test_project_rq_readonly.py --maxfail=1` -> skipped in host env (`flask` missing); canonical `wctl` run above passed.

## Residual Risks / Deferred Items

- `set_run_readonly_rq` still has some pre-boundary setup that can fail before the outer function exception block, and broader control-flow hardening of that path is deferred to later RQ cleanup batches.
- Silent best-effort notification catches (`send_discord_message`) remain in worker finalization paths and are deferred as approved boundary cleanups for later milestones.
