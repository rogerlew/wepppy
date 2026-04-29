# Execute: WEPP Interchange Dependency Race Guard

Execute this work package end-to-end:

- Package: `/workdir/wepppy/docs/work-packages/20260428_wepp_interchange_dependency_race_guard/`
- Archived ExecPlan: `/workdir/wepppy/docs/work-packages/20260428_wepp_interchange_dependency_race_guard/prompts/completed/wepp_interchange_dependency_race_guard_execplan.md`

Required outcomes:
1. `_post_watershed_interchange_rq` is serialized after `_build_hillslope_interchange_rq` in all affected pipeline helpers.
2. Regression tests prove the dependency edge(s) and protect against reversion.
3. Queue dependency graph/docs are synchronized and validated.
4. Independent sub-agent code review and QA review artifacts are completed.
5. Dedicated security review artifact is completed with gate status `pass`.

Implementation scope:
- Queue wiring:
  - `wepppy/rq/wepp_rq_pipeline.py`
- Regression tests:
  - `tests/rq/test_wepp_rq_pipeline.py`
- Queue contract docs:
  - `wepppy/rq/job-dependencies-catalog.md`
- Package lifecycle docs:
  - `docs/work-packages/20260428_wepp_interchange_dependency_race_guard/package.md`
  - `docs/work-packages/20260428_wepp_interchange_dependency_race_guard/tracker.md`
  - `PROJECT_TRACKER.md`
- Review artifacts:
  - `artifacts/2026-04-28_code_review.md`
  - `artifacts/2026-04-28_qa_review.md`
  - `artifacts/2026-04-28_security_review.md`

Execution constraints:
- Do not add time-delay/sleep based mitigation.
- Keep scope limited to dependency ordering + tests + required contract docs.
- Preserve existing job payload/status contracts.
- Follow `AGENTS.md` queue-wiring requirements (`wctl check-rq-graph`, catalog sync).

Sub-agent review requirement:
- Run `reviewer` for correctness/regression findings.
- Run `qa_reviewer` for test-quality findings.
- Resolve all medium/high findings before closure.

Validation commands:
- `wctl run-pytest tests/rq/test_wepp_rq_pipeline.py --maxfail=1`
- `wctl check-rq-graph`
- If drift: `python tools/check_rq_dependency_graph.py --write`
- `wctl doc-lint --path wepppy/rq/job-dependencies-catalog.md --path docs/work-packages/20260428_wepp_interchange_dependency_race_guard --path PROJECT_TRACKER.md`
- `git diff --check`

Package lifecycle updates required:
- Keep ExecPlan living sections current.
- Update `tracker.md` with UTC-stamped progress, decisions, and validation evidence.
- Update `package.md` closure notes at completion.
- Move active ExecPlan to `prompts/completed/` on close.
- Move package state in `PROJECT_TRACKER.md` (`Backlog -> In Progress -> Done`).
