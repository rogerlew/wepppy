# Subagent Review Disposition - 2026-05-06

## Scope

Review coverage for the fork copy optimization introducing `skip_wepp_runs_output` across:

- Fork console UI + submit payload
- rq-engine fork API payload and response contract
- RQ worker/helper copy behavior and directory guarantees
- Targeted regression coverage and schema-default discoverability

## Reviewers

- `reviewer` subagent (`019dff23-d044-7423-9b39-e10fd6d64bb9`)
- `qa_reviewer` subagent (`019dff23-d596-7ea1-8b94-f115b6925b95`)

## Findings and Disposition

1. **Auth/scope coverage gap for new fork schema/default endpoints**
- Severity: Low
- Source: reviewer
- Disposition: **Fixed**
- Action: Added `FORK_SCHEMA_PATH` and `FORK_DEFAULTS_PATH` to shared `SCHEMA_DEFAULT_PATHS` auth/scope parametrization.
- Evidence: `tests/microservices/test_rq_engine_schema_defaults_routes.py`

2. **Skip-copy helper test did not assert rsync exclude behavior or non-copy of WEPP content**
- Severity: Medium (qa_reviewer), Low (reviewer framing)
- Disposition: **Fixed**
- Action:
  - Seeded source sentinel files under `wepp/runs` and `wepp/output`.
  - Captured and asserted rsync excludes include both paths.
  - Implemented exclude-aware fake rsync behavior and asserted sentinels are not copied while directories still exist.
- Evidence: `tests/rq/test_project_rq_fork.py::test_prepare_fork_run_skip_wepp_copy_ensures_output_dirs`

3. **Default/omitted `skip_wepp_runs_output` not explicitly asserted at API boundary**
- Severity: Medium
- Source: qa_reviewer
- Disposition: **Fixed**
- Action: Added parameterized route test for omitted and explicit `false` input, asserting response value and queue args include `False`.
- Evidence: `tests/microservices/test_rq_engine_fork_archive_routes.py::test_fork_skip_wepp_runs_output_defaults_false`

4. **Fork UI doc mismatch for query-param parsing**
- Severity: Low
- Source: qa_reviewer
- Disposition: **Fixed**
- Action: Updated blueprint route note to include both `undisturbify` and `skip_wepp_runs_output` query params.
- Evidence: `docs/ui-docs/weppcloud-project-forking.md`

5. **Schema-defaults response-required assertion missing for new field**
- Severity: Low
- Source: qa_reviewer
- Disposition: **Fixed**
- Action: Extended schema-defaults test to assert `skip_wepp_runs_output` appears in success required response fields.
- Evidence: `tests/microservices/test_rq_engine_schema_defaults_routes.py`

6. **Residual UI route->template->JS default-propagation test gap**
- Severity: Low
- Source: qa_reviewer
- Disposition: **Accepted (deferred)**
- Rationale: Existing integration path already validated by route rendering logic, dataset attributes, and JS coercion path; this adds low incremental risk relative to current targeted coverage. Deferred to future UI harness hardening if fork-console template tests are expanded.

## Validation After Disposition

- `wctl run-pytest tests/rq/test_project_rq_fork.py tests/microservices/test_rq_engine_fork_archive_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py`
  - Result: `96 passed`
- Prior queue wiring guard:
  - `wctl check-rq-graph` -> drift detected
  - `python tools/check_rq_dependency_graph.py --write`
  - `wctl check-rq-graph` -> up to date

## Outcome

All medium findings were remediated in this change set. Remaining risk is a single low-severity, accepted UI default-propagation test gap.
