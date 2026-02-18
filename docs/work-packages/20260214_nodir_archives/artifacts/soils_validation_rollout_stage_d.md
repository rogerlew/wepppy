# Soils Validation and Rollout Stage D (Phase 6)

Scope: executable gates and rollout checks for soils Phase 6 adoption.

## Required Gates

| Gate | Command | Expected Result | Status |
| --- | --- | --- | --- |
| Soils route + bp + builder regression | `wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py tests/weppcloud/routes/test_soils_bp.py tests/soils/test_ssurgo.py` | Exit `0`; soils route preflight + enqueue + controller behavior remain stable | passed |
| Shared mutation/state safety | `wctl run-pytest tests/nodir` | Exit `0`; lock/thaw/freeze/mutation helper invariants remain green | passed |
| Docs consistency | `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` | Exit `0`; no markdown-doc violations | passed |

## Rollout Checks

- Mixed state (`409`), invalid archive (`500`), and transitional lock (`503`) handling are enforced in route preflight before RQ enqueue.
- Archive-form mutation retry remains deterministic because callback failures after thaw preserve thawed/dirty state.

## Rollback Trigger and Action

- Trigger: any regression where archive-form `build-soils` enqueues without canonical preflight, or returns non-canonical error status/code.
- Action: revert Phase 6 soils mutation-owner changes in `wepppy/rq/project_rq.py` and route preflight changes in `wepppy/microservices/rq_engine/soils_routes.py`, then re-run Stage D gate commands.
