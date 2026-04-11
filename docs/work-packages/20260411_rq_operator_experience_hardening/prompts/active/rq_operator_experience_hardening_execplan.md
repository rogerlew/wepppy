# RQ Operator Experience Hardening

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, an API operator can run rq-engine acceptance smoke end-to-end using only HTTP clients, with deterministic state/freshness semantics across controller-state endpoints and reliable smoke gates that do not break on unrelated test-count changes. This removes brittle auth/bootstrap choreography and reduces false blocker noise during autonomous operations.

Observable behavior after completion:
- Operator token bootstrap works without `wctl` and without scraping HTML pages.
- Controller-state payloads expose explicit revision domains and freshness state so cross-endpoint joins are deterministic.
- Smoke pass/fail is determined by exit codes and contract-shape assertions, not hard-coded pass counts.

## Progress

- [x] (2026-04-11 06:03 UTC) Created package scaffold and activated this ExecPlan.
- [x] (2026-04-11 06:03 UTC) Added contract-level target requirements in `rq-engine-agent-api-contract.md` and `rq-controller-state-contract.md`.
- [x] (2026-04-11 06:03 UTC) Updated smoke runbook expected-outcome wording to count-agnostic checks.
- [x] (2026-04-11 06:55 UTC) Defined implementation-ready auth bootstrap design and endpoint contract (Milestone 1).
- [x] (2026-04-11 06:55 UTC) Implemented machine-safe auth bootstrap route(s) and tests.
- [x] (2026-04-11 06:55 UTC) Implemented revision-domain and freshness payload semantics across read endpoints.
- [x] (2026-04-11 06:55 UTC) Added route/openapi/guard coverage and scripted operator acceptance smoke.
- [x] (2026-04-11 07:37 UTC) Completed reviewer, qa_reviewer, and security_reviewer gates with no unresolved medium/high findings.
- [x] (2026-04-11 15:58 UTC) Closed second-acceptance blocker by hardening climate parse validation and aligning climate schema/default semantics.
- [x] (2026-04-11 15:58 UTC) Added batched run-endpoint discovery snapshot (`include_operation_docs=true`) to reduce per-operation discovery chatter.
- [x] (2026-04-11 16:20 UTC) Closed follow-up QA atomicity finding and re-closed reviewer/qa/security gates with no unresolved medium/high findings.

## Surprises & Discoveries

- Observation: Source and forked target runs can have matching pipeline/readiness shape while exposing different revision families between orchestration and metadata endpoint groups.
  Evidence: `2026-04-11_clueless-aftertaste_replication_acceptance_report.md` showed `pipeline/readiness` and schema/defaults/errors/geospatial/outputs revisions did not align without explicit domain metadata.

- Observation: Existing operator token bootstrap is API-callable but operationally brittle because it depends on session + CSRF data sourced from HTML pages.
  Evidence: acceptance smoke required scraping CSRF from `/weppcloud/login` and `/weppcloud/profile` before minting token.

- Observation: Smoke guidance that hard-codes expected pass counts drifts quickly and causes false triage friction.
  Evidence: runbook expected `248 passed` while baseline now reports `251 passed`.

- Observation: Local caddy endpoint redirects plain HTTP on `:8080` to `https://localhost`, which can fail in local environments without a mapped TLS listener.
  Evidence: operator smoke against `http://localhost:8080/rq-engine/api/*` returned `301` to `https://localhost/...`; acceptance was executed against direct service ports (`:8042` rq-engine, `:8000` weppcloud auth) to keep the flow API-only and deterministic.

- Observation: Filesystem mtimes can be ahead of current UTC in local run roots, so freshness fallback logic must clamp to `now` to keep `updated_at` non-future.
  Evidence: first post-review smoke pass showed future `updated_at` values until mtime clamp was added and acceptance was rerun.

- Observation: `build-climate` route still surfaced parser traceback detail on malformed payloads (`KeyError: future_start_year`) even when endpoint-level schema/default discovery succeeded.
  Evidence: second acceptance run (`foaming-chervil/disturbed9002_wbt`) failed at `build-climate` with `400` parse error payload containing parser internals.

- Observation: Discovery-first agents incur unnecessary call volume when they must fetch schema/defaults/errors operation-by-operation after listing `/endpoints`.
  Evidence: second acceptance friction log reported 107 calls for one flow and specifically requested a batched operation snapshot.

## Decision Log

- Decision: Treat operator ergonomics as contract and implementation scope, not runbook-only polish.
  Rationale: Acceptance friction was caused by missing machine-safe primitives and ambiguous payload semantics, not lack of instructions.
  Date/Author: 2026-04-11 / Codex.

- Decision: Use explicit revision-domain fields (`run_state_domain`, `run_state_vector`) plus freshness fields (`data_state`, `data_updated_at`) rather than continuing implicit global revision assumptions.
  Rationale: Domain-explicit semantics let agents make deterministic stale-read decisions and avoid ad hoc heuristics.
  Date/Author: 2026-04-11 / Codex.

- Decision: Ship phased `run_state_vector` semantics with explicit `null` for non-local domains on each surface, while requiring domain-correct `run_state_revision` and vector self-alignment.
  Rationale: Delivers deterministic join-safe semantics immediately without introducing tight cross-module revision-coupling in this package.
  Date/Author: 2026-04-11 / Codex.

- Decision: Apply revocation-path throttling before Redis denylist checks and return explicit `503` + `Retry-After` on revocation backend outage.
  Rationale: Reduces outage amplification risk while preserving fail-closed auth behavior with machine-actionable retry semantics.
  Date/Author: 2026-04-11 / Codex.

- Decision: Treat climate parse failures as contract-level validation failures and return canonical `validation_error` payloads with machine-actionable missing-field entries.
  Rationale: Prevents traceback leakage, improves automation reliability, and directly addresses the `build-climate` blocker.
  Date/Author: 2026-04-11 / Codex.

- Decision: Add optional batched endpoint-doc snapshot on existing run endpoint catalog (`include_operation_docs=true`) instead of adding a new route family.
  Rationale: Smallest additive change that materially reduces discovery call count for operator agents.
  Date/Author: 2026-04-11 / Codex.

## Outcomes & Retrospective

Package implementation outcomes (2026-04-11 06:55 UTC):
- Machine-safe operator bootstrap shipped:
  - `POST /weppcloud/api/auth/rq-engine-operator-token`
  - strict requested-scope allowlist + authorization intersection
  - short TTL default, rate limiting, audit logging, and no-store responses
  - CSRF exemption explicitly registered for bearer-only operator path.
- Revision-domain + freshness semantics shipped across read surfaces:
  - orchestration reads: `run_state_domain=orchestration`, phased `run_state_vector`, deterministic `updated_at`, explicit `data_state/data_updated_at`
  - metadata reads: `run_state_domain=metadata`, phased `run_state_vector`
  - outputs reads: `run_state_domain=outputs`, outputs-domain revision, metadata-linked vector, explicit materialization state (`not_materialized` when no artifacts).
- Descriptor/schema metadata for snapshot reads now require:
  - `run_state_domain`
  - `run_state_vector`
  - `updated_at`
  - `data_state`
  - `data_updated_at`
  - `etag`
- Maintainer preflight gate passed:
  - consolidated microservice suite (`251 passed`)
  - inventory/checklist parity checks passed
  - guard tests passed.
- Operator API-only acceptance smoke passed with UTC/redacted evidence artifact:
  - `docs/work-packages/20260411_rq_operator_experience_hardening/artifacts/2026-04-11_operator_smoke_evidence.md`
- Security artifact updated with controls/findings disposition:
  - `docs/work-packages/20260411_rq_operator_experience_hardening/artifacts/2026-04-11_security_review.md`

Post-review closure addendum (2026-04-11 07:37 UTC):
- Addressed independent review findings:
  - freshness fallback revision-coherence hardening;
  - non-future freshness clamp;
  - revocation outage handling (`503` + retry guidance) with pre-revocation throttling;
  - contract/runbook alignment for required source-token `jti`.
- Reran targeted microservice + route suites (pass) and reran operator API-only smoke with refreshed evidence.
- Final independent `reviewer`/`qa_reviewer`/`security_reviewer` re-reviews report no unresolved medium/high findings.

Final closure addendum (2026-04-11 07:40 UTC):
- Orchestration revision signature now includes `data_updated_at` whenever timeline freshness is present, preventing freshness drift without revision movement.
- Operator evidence snippet redacts `session_id` to match artifact redaction policy.
- Final reviewer follow-up confirms no unresolved medium/high findings.

Second acceptance remediation addendum (2026-04-11 15:58 UTC):
- Climate parse boundary now emits canonical `validation_error` payloads (no traceback details) with missing-field entries for machine remediation.
- Climate schema/default contract aligned for mode coverage and mode-conditional year fields:
  - supported schema enum: `0,2,3,5,6,11`
  - observed-year requirements: observed/gridmet modes
  - future-year requirements: future mode
  - defaults switch to future-year defaults when run mode is future.
- Batched discovery support added:
  - `GET /api/runs/{runid}/{config}/endpoints?include_operation_docs=true`
  - response includes per-operation descriptor + schema + defaults + errors snapshot.
- Validation gates for this addendum passed:
  - parser/climate/schema suites
  - setup/openapi parity suite
  - endpoint/checklist guard checks
  - docs lint on updated contract/runbook/work-package docs.

Final remediation closure addendum (2026-04-11 16:20 UTC):
- Future-mode parse ordering now validates required future years before clearing observed-year state, preventing partial state mutation on invalid payloads.
- `include_operation_docs` query parameter is now explicit boolean in FastAPI/OpenAPI, with contract test coverage.
- Independent `reviewer`, `qa_reviewer`, and `security_reviewer` re-reviews confirm no unresolved medium/high findings remain for the follow-up delta.

## Context and Orientation

Key contract docs:
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/schemas/rq-controller-state-contract.md`
- `docs/dev-notes/auth-token.spec.md`

Key runtime/route areas expected to change:
- `wepppy/weppcloud/routes/weppcloud_site.py` (token bootstrap and auth bridge routes)
- `wepppy/weppcloud/routes/user.py` (profile token minting behavior and metadata)
- `wepppy/microservices/rq_engine/` route handlers and descriptor payload builders for controller-state endpoints

Key test suites:
- `tests/microservices/test_rq_engine_auth*.py`
- `tests/microservices/test_rq_engine_setup_discovery_routes.py`
- `tests/microservices/test_rq_engine_orchestration_read_routes.py`
- `tests/microservices/test_rq_engine_schema_defaults_routes.py`
- `tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py`
- `tests/microservices/test_rq_engine_errors_progress_outputs_routes.py`
- `tests/microservices/test_rq_engine_openapi_contract.py`
- `tests/tools/test_endpoint_inventory_guard.py`
- `tests/tools/test_route_contract_checklist_guard.py`

## Plan of Work

Milestone 1: Machine-safe operator bootstrap contract and route behavior.
Define and implement at least one fully machine-safe auth bootstrap path that does not depend on HTML parsing or `wctl`. Prefer additive behavior that keeps browser/session flows intact. Update route descriptors/OpenAPI/auth docs to clearly distinguish browser-oriented vs machine-oriented paths.

Milestone 2: Revision coherence semantics.
Implement explicit revision-domain metadata for run-scoped read endpoints. Ensure each response identifies the revision domain for `run_state_revision`, and expose a consistent revision vector so cross-endpoint consistency checks are deterministic.

Milestone 3: Freshness semantics.
Normalize snapshot freshness behavior by enforcing non-null, non-epoch `updated_at` and explicit data materialization state via `data_state` and `data_updated_at`. Update outputs/geospatial/controller-state payloads and tests accordingly.

Milestone 4: Smoke reliability and acceptance tooling.
Replace pass-count-based runbook assumptions with scriptable contract checks (exit code + payload shape). Add an API-only operator smoke script/runbook flow that captures UTC method/path/status evidence with redaction.

Milestone 5: Verification and gates.
Run required route/openapi/guard tests, perform manual API smoke, complete reviewer/qa/security gates, and record finding dispositions in package tracker and security artifact.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Implement/auth bootstrap + contract metadata updates.
2. Implement revision-domain + freshness payload updates.
3. Run maintainer preflight tests (contract/route parity gate; `wctl` allowed)
   using canonical Phase A command set from:
   `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md`.

4. Run API-only operator acceptance smoke with redacted logging and UTC
   `method/path/status` evidence using canonical sequence from:
   `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md`
   (operator path, no `wctl`).
5. Run docs gate:

    wctl doc-lint --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-controller-state-contract.md --path docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md --path docs/work-packages/20260411_rq_operator_experience_hardening/package.md --path docs/work-packages/20260411_rq_operator_experience_hardening/tracker.md --path docs/work-packages/20260411_rq_operator_experience_hardening/prompts/active/rq_operator_experience_hardening_execplan.md --path PROJECT_TRACKER.md

## Validation and Acceptance

Acceptance requires all of the following:
- Operator bootstrap can be executed end-to-end with API calls only and no
  HTML scraping.
- Required token scopes are explicitly documented and validated in route tests.
- `run_state_domain` and `run_state_vector` semantics are present and deterministic across run-scoped read endpoints.
- Snapshot freshness fields are semantically correct (`updated_at` not null/epoch, `data_state` and `data_updated_at` coherent).
- Smoke runbook checks are exit-code and contract-shape based (count-agnostic).
- Required test/guard/docs gates pass.
- No unresolved medium/high findings remain after reviewer/qa/security passes.

## Idempotence and Recovery

All schema/doc edits are additive and can be reapplied. Route behavior changes should be deployed incrementally behind compatibility guards where needed. If rollout reveals downstream client breakage, preserve legacy fields while keeping new fields authoritative and documented, then stage client migration in follow-up patches within this package.

## Artifacts and Notes

- Security review artifact (required):
  `docs/work-packages/20260411_rq_operator_experience_hardening/artifacts/2026-04-11_security_review.md`
- Acceptance evidence artifact to create during execution:
  `docs/work-packages/20260411_rq_operator_experience_hardening/artifacts/2026-04-11_operator_smoke_evidence.md`

## Interfaces and Dependencies

Target interfaces to exist by package completion:
- A machine-safe operator auth bootstrap API contract documented in:
  - `docs/schemas/rq-engine-agent-api-contract.md`
  - `docs/dev-notes/auth-token.spec.md` (if claim/flow semantics change)
- Run-scoped read payload metadata contract in `docs/schemas/rq-controller-state-contract.md`:
  - `run_state_domain`
  - `run_state_vector`
  - `data_state`
  - `data_updated_at`
- Smoke-runbook operator gate contract in:
  - `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md`

---
Revision Note (2026-04-11 / Codex): Initial active ExecPlan authored with implementation milestones for operator auth bootstrap, revision/freshness semantics hardening, and deterministic acceptance gating.
