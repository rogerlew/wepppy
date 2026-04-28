# Execute: RQ Scoped Stale NoDb Cache Guard Follow-Ups

Execute the active work package end-to-end:

- Package: `/workdir/wepppy/docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/`
- Active ExecPlan: `/workdir/wepppy/docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/prompts/active/rq_scoped_stale_cache_guard_followups_execplan.md`

Required outcomes:
1. Priority 0 RQ mutation paths clear scoped NoDb cache before mutable controller hydration.
2. Existing lock-root, archive-root rejection, status, timestamp, and enqueue behavior remains unchanged.
3. Priority 1 and Priority 2 candidate call sites have implementation or explicit split/defer disposition.
4. Targeted regression tests and docs lint pass.

Implementation scope:
- Primary RQ worker path:
  - `wepppy/rq/project_rq.py`
- Primary regression coverage:
  - `tests/rq/test_project_rq_mutation_guards.py`
- Conditional follow-on modules if audit confirms simple, testable guards:
  - `wepppy/rq/wepp_rq.py`
  - `wepppy/rq/swat_rq.py`
  - `wepppy/rq/omni_rq.py`
  - `wepppy/rq/path_ce_rq.py`
  - `wepppy/rq/roads_rq.py`
  - `wepppy/rq/geneva_rq.py`
  - `wepppy/rq/project_rq_fork.py`
- Package lifecycle docs:
  - `docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/package.md`
  - `docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/tracker.md`
  - `PROJECT_TRACKER.md`

Execution constraints:
- Keep scope narrow to confirmed stale-cache risk shapes.
- Prefer exact `pup_relpath` values; do not replace scoped guards with broad run-wide cache clears.
- Do not add fallback wrappers that silently mask missing Redis cache dependencies.
- Do not mechanically guard read-only `getInstance(...)` calls.
- Preserve existing lock/archive/status/timestamp/enqueue contracts.

Validation commands:
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1`
- Add focused pytest commands for any non-`project_rq.py` module touched.
- `wctl doc-lint --path docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups --path PROJECT_TRACKER.md`
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
