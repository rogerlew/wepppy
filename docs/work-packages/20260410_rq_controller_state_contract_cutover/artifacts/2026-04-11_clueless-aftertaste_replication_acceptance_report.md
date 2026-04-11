# `clueless-aftertaste` Replication Acceptance Report (API Operator)

## Executive Result
`PASS`

## Environment
- Base URL: `https://wc.bearhive.duckdns.org/rq-engine/api`
- Source run URL: `https://wc.bearhive.duckdns.org/weppcloud/runs/clueless-aftertaste/disturbed9002_wbt/`
- Source run context: `runid=clueless-aftertaste`, `config=disturbed9002_wbt`
- Target run context (created during test): `runid=ergonomic-sociopath`, `config=disturbed9002_wbt`
- Auth mode: bearer JWT minted from authenticated WEPPcloud session (`POST /weppcloud/profile/mint-token`), no manual UI clicking used
- Minted token scopes: `runs:read queries:validate queries:execute rq:status rq:enqueue rq:export`
- UTC test window: `2026-04-11T04:11:38Z` to `2026-04-11T04:15:05Z`

## Exact Steps Run

### 1) Preflight (Runbook Phase A)
- Command: `wctl run-pytest tests/microservices/test_rq_engine_setup_discovery_routes.py ... tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- Start/End: `2026-04-11T04:11:38Z` -> `2026-04-11T04:12:01Z`
- Result: `251 passed, 9 warnings`, exit `0`

- Command: `python tools/check_endpoint_inventory.py`
- Time: `2026-04-11T04:12:07Z`
- Result: `Endpoint inventory check passed`, exit `0`

- Command: `python tools/check_route_contract_checklist.py`
- Time: `2026-04-11T04:12:11Z`
- Result: `Route contract checklist check passed`, exit `0`

- Command: `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1`
- Start/End: `2026-04-11T04:12:15Z` -> `2026-04-11T04:12:29Z`
- Result: `2 passed, 2 warnings`, exit `0`

### 2) Auth/Token Preflight
- `2026-04-11T04:12:56Z | GET /weppcloud/login | 200`
- `2026-04-11T04:12:56Z | POST /weppcloud/login | 200`
- `2026-04-11T04:12:56Z | GET /weppcloud/profile | 200`
- `2026-04-11T04:12:56Z | POST /weppcloud/profile/mint-token | 200`
- Sensitive values redacted: credential values and bearer token body were not logged in report text.

### 3) Source Baseline Capture (`clueless-aftertaste/disturbed9002_wbt`)
- `2026-04-11T04:13:26Z | GET /configs | 200`
- `2026-04-11T04:13:26Z | GET /endpoints | 200`
- `2026-04-11T04:13:26Z | GET /endpoints/rq_engine_create/schema | 200`
- `2026-04-11T04:13:26Z | GET /runs/clueless-aftertaste/disturbed9002_wbt/pipeline | 200`
- `2026-04-11T04:13:26Z | GET /runs/clueless-aftertaste/disturbed9002_wbt/readiness | 200`
- `2026-04-11T04:13:26Z | GET /runs/clueless-aftertaste/disturbed9002_wbt/controllers | 200`
- `2026-04-11T04:13:26Z | GET /runs/clueless-aftertaste/disturbed9002_wbt/controllers/watershed/schema | 200`
- `2026-04-11T04:13:27Z | GET /runs/clueless-aftertaste/disturbed9002_wbt/endpoints | 200`
- `2026-04-11T04:13:27Z | GET /runs/clueless-aftertaste/disturbed9002_wbt/endpoints/rq_engine_build_climate/schema | 200`
- `2026-04-11T04:13:27Z | GET /runs/clueless-aftertaste/disturbed9002_wbt/endpoints/rq_engine_build_climate/defaults | 200`
- `2026-04-11T04:13:27Z | GET /runs/clueless-aftertaste/disturbed9002_wbt/endpoints/rq_engine_build_climate/errors | 200`
- `2026-04-11T04:13:27Z | GET /runs/clueless-aftertaste/disturbed9002_wbt/geospatial-metadata | 200`
- `2026-04-11T04:13:27Z | GET /runs/clueless-aftertaste/disturbed9002_wbt/outputs | 200`
- `2026-04-11T04:13:27Z | POST /runs/clueless-aftertaste/disturbed9002_wbt/session-token | 200`

### 4) Replication Execution (API-only)
- `2026-04-11T04:14:41Z | POST /runs/clueless-aftertaste/disturbed9002_wbt/fork | 200`
- Fork response keys used: `job_id=8e2ced6a-c721-4545-bf81-93d6fabce8f9`, `new_runid=ergonomic-sociopath`
- Polling:
- `2026-04-11T04:14:41Z | GET /jobstatus/8e2ced6a-c721-4545-bf81-93d6fabce8f9 | 200 | started`
- `2026-04-11T04:14:43Z | GET /jobstatus/8e2ced6a-c721-4545-bf81-93d6fabce8f9 | 200 | started`
- `2026-04-11T04:14:45Z | GET /jobstatus/8e2ced6a-c721-4545-bf81-93d6fabce8f9 | 200 | started`
- `2026-04-11T04:14:47Z | GET /jobstatus/8e2ced6a-c721-4545-bf81-93d6fabce8f9 | 200 | started`
- `2026-04-11T04:14:49Z | GET /jobstatus/8e2ced6a-c721-4545-bf81-93d6fabce8f9 | 200 | finished`

### 5) Target Validation Capture (`ergonomic-sociopath/disturbed9002_wbt`)
- `2026-04-11T04:15:04Z | GET /runs/ergonomic-sociopath/disturbed9002_wbt/pipeline | 200`
- `2026-04-11T04:15:05Z | GET /runs/ergonomic-sociopath/disturbed9002_wbt/readiness | 200`
- `2026-04-11T04:15:05Z | GET /runs/ergonomic-sociopath/disturbed9002_wbt/controllers | 200`
- `2026-04-11T04:15:05Z | GET /runs/ergonomic-sociopath/disturbed9002_wbt/controllers/watershed/schema | 200`
- `2026-04-11T04:15:05Z | GET /runs/ergonomic-sociopath/disturbed9002_wbt/endpoints | 200`
- `2026-04-11T04:15:05Z | GET /runs/ergonomic-sociopath/disturbed9002_wbt/endpoints/rq_engine_build_climate/schema | 200`
- `2026-04-11T04:15:05Z | GET /runs/ergonomic-sociopath/disturbed9002_wbt/endpoints/rq_engine_build_climate/defaults | 200`
- `2026-04-11T04:15:05Z | GET /runs/ergonomic-sociopath/disturbed9002_wbt/endpoints/rq_engine_build_climate/errors | 200`
- `2026-04-11T04:15:05Z | GET /runs/ergonomic-sociopath/disturbed9002_wbt/geospatial-metadata | 200`
- `2026-04-11T04:15:05Z | GET /runs/ergonomic-sociopath/disturbed9002_wbt/outputs | 200`
- `2026-04-11T04:15:05Z | POST /runs/ergonomic-sociopath/disturbed9002_wbt/session-token | 200`

## Acceptance Criteria Results
- Criterion: Phase A pre-smoke contract/guard checks pass.
- Result: `PASS`
- Evidence: `251 passed` microservice suite + both guard scripts + `2 passed` guard tests, all exit `0`.

- Criterion: API orchestration surfaces function for source and target contexts.
- Result: `PASS`
- Evidence: all setup + run-scoped read calls listed above returned `200`; fork async mutation submitted and reached terminal `finished`.

- Criterion: Pipeline completion shape parity (source vs target).
- Result: `PASS`
- Evidence: both runs reported `14` steps with identical status distribution: `completed=6`, `ready=4`, `blocked=4`; per-step status differences `0`.

- Criterion: Readiness terminal condition parity.
- Result: `PASS`
- Evidence: both runs are non-terminal with identical actionable queue:
  `rq_engine_build_landuse`, `rq_engine_build_soils`, `rq_engine_run_wepp`, `rq_engine_build_rusle`; blocking issue count `4` on both.

- Criterion: Outputs/artifact availability parity.
- Result: `PASS`
- Evidence: both runs returned `artifacts=[]` (count `0`) and no available exports.

## Blockers
- None encountered.

## High-Friction Points (Ranked)

1. Auth bootstrap is not operator-native API.
- Friction: bearer minting required HTML CSRF token extraction across `/weppcloud/login` + `/weppcloud/profile` pages before `POST /weppcloud/profile/mint-token`.
- Impact on autonomous agent operation: adds brittle HTML parsing and session choreography before any rq-engine call.
- Proposed short-term fix: publish a supported script/wrapper command that returns a bearer token from stored dev-agent credentials.
- Proposed long-term fix: add a dedicated machine-oriented token mint endpoint/flow for non-browser operators with explicit audit semantics.
- Suggested owner/team: WEPPcloud auth/session maintainers.

2. `run_state_revision` is inconsistent across endpoint families for the same run snapshot window.
- Friction: `pipeline/readiness` returned one revision while schema/defaults/errors/geospatial/outputs returned another (`f9d...` vs `31ab...` on source, `8e99...` vs `31ab...` on target).
- Impact on autonomous agent operation: client-side consistency checks become ambiguous and can force conservative retries or false conflict handling.
- Proposed short-term fix: document endpoint-family revision source semantics explicitly in contract text and runbook.
- Proposed long-term fix: unify revision generation or return both family revision and global revision fields with clear compatibility rules.
- Suggested owner/team: rq-engine controller-state contract owners.

3. Low-signal timestamp fields hinder freshness decisions.
- Friction: `outputs.updated_at` returned `1970-01-01T00:00:00Z` with no artifacts; `geospatial-metadata.updated_at` was `null`.
- Impact on autonomous agent operation: impossible to distinguish “never computed yet” from stale cache without extra endpoint fan-out.
- Proposed short-term fix: add explicit `state`/`availability` markers and avoid sentinel epoch values.
- Proposed long-term fix: enforce non-null, semantically correct timestamps via OpenAPI + contract guard tests.
- Suggested owner/team: rq-engine API contract + route guard maintainers.

4. Runbook expectation drift (`248` vs observed `251` tests) adds operator ambiguity.
- Friction: expected-count text was stale relative to passing suite.
- Impact on autonomous agent operation: can trigger false suspicion of hidden drift during acceptance checks.
- Proposed short-term fix: update runbook expected output text to current baseline.
- Proposed long-term fix: derive expected counts dynamically in runbook helper scripts instead of hard-coding.
- Suggested owner/team: work-package documentation owner.

## Recommended Next Actions
1. Update the smoke runbook to remove hard-coded expected pytest count and link to command outputs in CI artifacts.
2. Add a machine-friendly auth bootstrap path (or an official operator wrapper) so acceptance smoke can start without HTML token scraping.
3. Reconcile and document `run_state_revision` semantics across pipeline/readiness vs schema/defaults/errors/geospatial/outputs before broader automation rollout.
4. Normalize `updated_at` semantics for `outputs` and `geospatial-metadata` (no epoch/null sentinels) and add guard tests for these fields.
