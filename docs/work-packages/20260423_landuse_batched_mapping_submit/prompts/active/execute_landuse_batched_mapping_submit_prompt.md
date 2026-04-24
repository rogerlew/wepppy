# Execute: Landuse Batched Mapping Submit

Execute the active work package end-to-end:

- Package: `/home/workdir/wepppy/docs/work-packages/20260423_landuse_batched_mapping_submit/`
- Active ExecPlan: `/home/workdir/wepppy/docs/work-packages/20260423_landuse_batched_mapping_submit/prompts/active/landuse_batched_mapping_submit_execplan.md`

Required outcomes:
1. Landuse mapping selects no longer submit network requests on every `change`.
2. User can stage one or more mapping edits and submit once using a secondary action button.
3. Single-OFE and Multi-OFE use the same staged-submit UX pattern.
4. Mapping submit enqueues one RQ job without predecessor `depends_on` chaining.
5. Mapping batch is applied under one lock window with deterministic semantics and one completion trigger.

Implementation scope:
- Frontend/report UX:
  - `wepppy/weppcloud/templates/reports/landuse.htm`
  - `wepppy/weppcloud/controllers_js/landuse.js`
- rq-engine route:
  - `wepppy/microservices/rq_engine/landuse_routes.py`
- RQ worker path:
  - `wepppy/rq/project_rq.py`
- Regression coverage:
  - `wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
  - `tests/microservices/test_rq_engine_landuse_routes.py`
  - `tests/rq/test_project_rq_mutation_guards.py`

Required contract decisions (must be explicit and documented in ExecPlan + tracker):
- Batch payload shape and limits (for example, `changes: [{dom, newdom}]`).
- Duplicate/chained edits semantics in one submit (reject vs normalize; if normalize, define ordering).
- Failure behavior (all-or-nothing validation expected; no silent partial apply).
- Backward compatibility policy for legacy single-edit payloads.

Execution constraints:
- Remove mapping `depends_on` enqueue behavior from this path.
- Preserve explicit error contracts; do not add silent fallbacks.
- Keep changes minimal and localized to mapping UX/API/RQ path.
- Keep coverage override behavior unchanged unless explicitly required.

Validation commands:
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1`
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
- `wctl doc-lint --path docs/work-packages/20260423_landuse_batched_mapping_submit`

Package lifecycle updates required:
- Keep ExecPlan living sections current (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`).
- Update `tracker.md` with UTC-stamped progress/decisions.
- Update `package.md` as implementation clarifies contract and at closure.
- Update `PROJECT_TRACKER.md` status when package moves from Backlog to In Progress/Done.
- On completion, move ExecPlan from `prompts/active/` to `prompts/completed/` with outcome notes.

Finish with a concise closure summary:
- changed files
- behavior delta
- validation commands + results
- residual risks/follow-ups
