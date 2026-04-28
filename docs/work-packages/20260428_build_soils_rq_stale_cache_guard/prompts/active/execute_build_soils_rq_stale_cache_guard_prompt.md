# Execute: `build_soils_rq` Stale NoDb Cache Guard

Execute the active work package end-to-end:

- Package: `/workdir/wepppy/docs/work-packages/20260428_build_soils_rq_stale_cache_guard/`
- Completed ExecPlan: `/workdir/wepppy/docs/work-packages/20260428_build_soils_rq_stale_cache_guard/prompts/completed/build_soils_rq_stale_cache_guard_execplan.md`

Required outcomes:
1. `build_soils_rq` clears scoped NoDb cache for `soils.nodb` before mutable soils hydration/build.
2. Existing lock-root and status/timestamp behavior remains unchanged.
3. Existing archive-root rejection behavior for `build_soils_rq` remains unchanged.
4. Targeted regression tests and docs lint pass.

Implementation scope:
- RQ worker path:
  - `wepppy/rq/project_rq.py`
- Regression coverage:
  - `tests/rq/test_project_rq_mutation_guards.py`
- Optional non-regression confidence:
  - `tests/microservices/test_rq_engine_soils_routes.py`
- Package lifecycle docs:
  - `docs/work-packages/20260428_build_soils_rq_stale_cache_guard/package.md`
  - `docs/work-packages/20260428_build_soils_rq_stale_cache_guard/tracker.md`
  - `PROJECT_TRACKER.md`

Execution constraints:
- Keep scope narrow to the confirmed stale-cache failure path.
- Prefer explicit failure contracts; do not introduce silent fallback wrappers.
- Do not broaden into queue-topology or NoDb cache architecture redesign.
- Add only minimal targeted tests needed to prove guard behavior and non-regression.

Validation commands:
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1`
- `wctl doc-lint --path docs/work-packages/20260428_build_soils_rq_stale_cache_guard --path PROJECT_TRACKER.md`
- `git diff --check`

Package lifecycle updates required:
- Keep ExecPlan living sections current (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`).
- Update `tracker.md` with UTC-stamped progress, decisions, and validation evidence.
- Update `package.md` at closure with summary and outcomes.
- Move active ExecPlan to `prompts/completed/` with closure notes.
- Update `PROJECT_TRACKER.md` package status at completion.

Finish with a concise closure summary:
- changed files
- behavior delta
- validation commands + results
- residual risks/follow-ups
