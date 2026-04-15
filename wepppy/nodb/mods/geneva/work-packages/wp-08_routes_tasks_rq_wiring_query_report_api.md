# WP-08 Evidence: Routes, Tasks, RQ Wiring, Query/Report API
Status: done  
Last Updated: 2026-04-15  
Work-Package: `WP-08`  
Owner: `codex`

References:
- Plan: `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- Spec: `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- Prior package evidence: `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-07_cn_table_workflow_edit_csv_integration.md`
- NoDb facade standard: `/workdir/wepppy/docs/standards/nodb-facade-collaborator-pattern.md`
- RQ response contract: `/workdir/wepppy/docs/schemas/rq-response-contract.md`
- CSRF contract: `/workdir/wepppy/docs/schemas/weppcloud-csrf-contract.md`

## 1. Scope Implemented
Implemented WP-08 end-to-end for Geneva route/task/query/report integration while preserving WP-07 CN-table contracts.

Delivered endpoints (spec `Expected route family`):
- `GET|POST /runs/<runid>/<config>/api/geneva/config`
- `POST /runs/<runid>/<config>/tasks/geneva/prepare_hrus`
- `POST /runs/<runid>/<config>/tasks/geneva/build_frequency_panel`
- `POST /runs/<runid>/<config>/tasks/geneva/run_batch`
- `GET /runs/<runid>/<config>/api/geneva/status`
- `GET /runs/<runid>/<config>/api/geneva/results`
- `GET /runs/<runid>/<config>/api/geneva/frequency_panel`
- `GET /runs/<runid>/<config>/query/geneva/summary`
- `GET /runs/<runid>/<config>/report/geneva/summary`

Key contract behaviors implemented:
- Async task endpoints return canonical RQ submission payload (`job_id`, `status_url`, `message`) with HTTP `202`.
- Error responses map to canonical `error` envelope (`message`, `code`, `details`) using Geneva typed errors.
- Status/results payloads support `completed_with_gaps` for partial-availability batches.
- Frequency panel and run-batch selectors enforce canonical enum IDs (`datasource_id`, `distribution_type`, `measure`).
- Route tasks call NoDb guardrails (`assert_task_guardrails`) so WBT-only and US-domain policies propagate from NoDb without route-layer duplication.
- Query/report summary payload parity implemented; report template embeds exactly one JSON payload matching query shape.

## 2. Code Changes
### Repo: `/workdir/wepppy`
Core Geneva implementation and wiring:
- `wepppy/weppcloud/routes/nodb_api/geneva_bp.py`
- `wepppy/rq/geneva_rq.py` (new)
- `wepppy/nodb/mods/geneva/geneva.py`
- `wepppy/nodb/mods/geneva/collaborators/report_payload_service.py` (new)
- `wepppy/nodb/mods/geneva/collaborators/frequency_panel_service.py`
- `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`
- `wepppy/nodb/mods/geneva/collaborators/results_service.py`
- `wepppy/nodb/mods/geneva/collaborators/__init__.py`
- `wepppy/nodb/mods/geneva/schemas/query_schema.py` (new)
- `wepppy/nodb/mods/geneva/schemas/run_batch_schema.py`
- `wepppy/nodb/mods/geneva/schemas/config_schema.py`
- `wepppy/nodb/mods/geneva/schemas/__init__.py`

Report/template surface:
- `wepppy/weppcloud/templates/reports/geneva/summary.htm` (new)
- `wepppy/weppcloud/templates/controls/edit_csv.htm`

Queue dependency artifacts (required after wiring changes):
- `wepppy/rq/job-dependency-graph.static.json`
- `wepppy/rq/job-dependencies-catalog.md`

Evidence/planning:
- `wepppy/nodb/mods/geneva/work-packages/wp-08_routes_tasks_rq_wiring_query_report_api.md`
- `wepppy/nodb/mods/geneva/work-packages/wp-08_execution_prompt.md`
- `wepppy/nodb/mods/geneva/implementation-plan.md`

## 3. Tests Added/Extended
Added coverage for WP-08 requirements:
- `tests/weppcloud/routes/test_geneva_wp08_routes.py` (new)
  - endpoint family contracts
  - canonical RQ envelopes
  - schema/enum validation paths
  - `completed_with_gaps` status/results expectations
  - query/report payload parity
  - route-level WBT/US guard propagation
- `tests/nodb/mods/geneva/test_geneva_schema_contracts.py` (new)
  - strict type contracts (`default_hsg_code`, booleans)
  - datasource enum enforcement
  - frequency-panel reason-code invariants
- `tests/nodb/mods/geneva/test_geneva_report_payload_service.py` (new)
  - query/report payload shape
  - chart/event-table filters
  - invalid filter handling
- `tests/weppcloud/routes/test_pure_controls_render.py`
  - Geneva summary report template contract (single embedded JSON payload)

## 4. Required Gates
Executed from `/workdir/wepppy` on final WP-08 changes:

1. `wctl run-pytest tests/nodb/mods/geneva --maxfail=1`
- Result: **pass** (`24 passed`)

2. `wctl run-pytest tests/nodb --maxfail=1`
- Result: **pass** (`959 passed, 4 skipped`)

3. `wctl run-pytest tests --maxfail=1`
- Result: **pass** (`3615 passed, 36 skipped`)

4. `wctl doc-lint --path wepppy/nodb/mods/geneva`
- Result: **pass** (`15 files validated, 0 errors, 0 warnings`)

5. `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- Result: **pass** (`Result: PASS`)

6. `wctl check-rq-graph`
- Result: **pass** (`RQ dependency graph artifacts are up to date`)

UI gates (template touched):
7. `wctl run-npm lint`
- Result: **pass**

8. `wctl run-npm test`
- Result: **pass** (`76 suites passed, 510 tests passed`)

## 5. Manual Integration Evidence
Manual WP-08 API harness executed via Flask test client (inside `weppcloud` container using `wctl run-python`) for full route-family flow:
- enable/update config
- submit `prepare_hrus` task
- submit `build_frequency_panel` task
- submit `run_batch` task
- inspect `status` and `results`
- inspect `query` summary
- render `report` summary

Observed evidence:
- `manual.config.status = 200`
- `manual.prepare_hrus.status = 202`
- `manual.build_frequency_panel.status = 202`
- `manual.run_batch.status = 202`
- `manual.status.status = 200`
- `manual.results.status = 200`
- `manual.query.status = 200`
- `manual.report.status = 200`
- `manual.report.template = reports/geneva/summary.htm`
- `manual.query.measure = runoff_depth`
- `manual.report.payload_measure = runoff_depth`
- `manual.results.payload_status = completed_with_gaps`
- `manual.results.unavailable_count = 1`

## 6. Review Workflow
### 6.1 Code Review (risk-focused)
Reviewed route/task wiring against spec contracts:
- endpoint coverage complete for WP-08 route family
- canonical RQ envelopes and canonical error envelopes enforced
- NoDb guardrails called from tasks (WBT/US enforcement centralized)
- queue wiring included explicit worker entrypoints and dependency artifacts update

### 6.2 QA Review
Verified through automated and manual evidence:
- route schema/enum regressions covered
- `completed_with_gaps` surfaced in status/results contracts
- query/report payload parity confirmed
- report template payload embedding contract confirmed
- full required gate suite passed

### 6.3 Security Review
Validated security-sensitive boundaries:
- run-scoped auth preserved (`authorize_and_handle_with_exception_factory` + explicit route auth on mutating paths)
- CSRF/session expectations unchanged for Flask browser mutating routes
- no broad exception swallowing introduced in changed production files
- WBT/US guard checks remain NoDb-origin and explicit (`unsupported_backend`, `unsupported_domain`)

## 7. Findings and Disposition
- Finding ID: `WP08-CODE-INVALID-SCHEMAVERSION-500`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action/Notes: `build_frequency_panel` request normalization could raise raw `ValueError` on malformed integers, producing generic exception envelope. Added explicit `GenevaValidationError` mapping for schema and selector integer parsing; added route regression test.

- Finding ID: `WP08-QA-FULL-SUITE-TEMPLATE-CONTEXT`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action/Notes: full repo gate revealed `url_for_run` undefined in minimal template context for shared editor. Added safe fallback run-home URL in `controls/edit_csv.htm`; reran full gates.

- Finding ID: `WP08-SEC-GUARD-PROPAGATION-COVERAGE`
  - Severity: low
  - Disposition: resolved_fix_now
  - Action/Notes: added explicit route tests for `unsupported_backend` and `unsupported_domain` propagation on task endpoints to prevent future route-layer bypasses.

## 8. Exit-Criteria Check
- [x] Endpoint family implemented and schema-conformant.
- [x] Route/task contracts follow canonical RQ/error/CSRF expectations.
- [x] RQ dependency graph + catalog updates completed.
- [x] Required tests and gates passed with recorded outcomes.
- [x] Manual integration checks recorded.
- [x] Code/QA/security reviews completed.
- [x] Fix-now findings resolved.
