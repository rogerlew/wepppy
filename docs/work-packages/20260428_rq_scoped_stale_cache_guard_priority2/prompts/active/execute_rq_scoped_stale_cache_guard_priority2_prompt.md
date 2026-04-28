# Execute: RQ Scoped Stale NoDb Cache Guard Priority 2

Execute the active work package end-to-end:

- Package: `/workdir/wepppy/docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2/`
- Completed ExecPlan: `/workdir/wepppy/docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2/prompts/completed/rq_scoped_stale_cache_guard_priority2_execplan.md`

Required outcomes:
1. Every Priority 2 candidate path has implementation or explicit split/defer/not-applicable disposition.
2. Confirmed mutation paths clear scoped NoDb cache before mutable controller hydration.
3. Existing lock, archive-root, status, timestamp, enqueue, clone, deletion, autocommit, and runtime-lock behavior remains unchanged.
4. Targeted regression tests and docs lint pass.

Implementation scope:
- Candidate RQ worker modules:
  - `wepppy/rq/wepp_rq.py`
  - `wepppy/rq/swat_rq.py`
  - `wepppy/rq/omni_rq.py`
  - `wepppy/rq/path_ce_rq.py`
  - `wepppy/rq/roads_rq.py`
  - `wepppy/rq/geneva_rq.py`
  - `wepppy/rq/project_rq_fork.py`
- Candidate regression coverage:
  - `tests/rq/test_bootstrap_enable_rq.py`
  - `tests/rq/test_bootstrap_autocommit_rq.py`
  - `tests/rq/test_omni_rq.py`
  - `tests/rq/test_path_ce_rq.py`
  - `tests/rq/test_roads_rq.py`
  - `tests/rq/test_geneva_rq.py`
  - `tests/rq/test_project_rq_fork.py`
- Package lifecycle docs:
  - `docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2/package.md`
  - `docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2/tracker.md`
  - `PROJECT_TRACKER.md`

Execution constraints:
- Treat this package as conformance to `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`, not hardening.
- Keep scope narrow to confirmed stale-cache risk shapes.
- Prefer exact `pup_relpath` values; do not replace scoped guards with broad run-wide cache clears.
- Do not add fallback wrappers that silently mask missing Redis cache dependencies.
- Do not mechanically guard read-only `getInstance(...)` calls.
- Preserve existing lock/archive/status/timestamp/enqueue/clone/delete/autocommit/runtime-lock contracts.
- If a module is too broad for safe implementation in this package, record explicit split/defer disposition instead of broadening the change.

Validation commands:
- Add focused pytest commands for every non-`project_rq.py` module touched.
- Suggested starting commands:
  - `wctl run-pytest tests/rq/test_bootstrap_enable_rq.py tests/rq/test_bootstrap_autocommit_rq.py --maxfail=1`
  - `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1`
  - `wctl run-pytest tests/rq/test_path_ce_rq.py --maxfail=1`
  - `wctl run-pytest tests/rq/test_roads_rq.py --maxfail=1`
  - `wctl run-pytest tests/rq/test_geneva_rq.py --maxfail=1`
  - `wctl run-pytest tests/rq/test_project_rq_fork.py --maxfail=1`
- `wctl doc-lint --path docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2 --path PROJECT_TRACKER.md`
- `git diff --check`
- If queue wiring changes, update `wepppy/rq/job-dependencies-catalog.md` and run `wctl check-rq-graph`.

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
