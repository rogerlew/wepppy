# Implement RQ Controller State Schema and Defaults Surfaces

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Deliver run-scoped schema/default metadata APIs so an agent can validate and assemble controller/operation parameters without scraping UI payloads or hardcoding field semantics. After this package, an agent with `runid/config` can discover controller metadata (`schema`, `hints`, `templates`) and operation request metadata (`schema`, `defaults`) with machine-checkable constraints and run-resolved defaults.

## Progress

- [x] (2026-04-10 18:21 UTC) Created package scaffold and authored this active ExecPlan.
- [x] (2026-04-10 18:33 UTC) Completed required-reading pass across contract docs, predecessor package outputs, freeze artifacts, and rq-engine route inventory.
- [x] (2026-04-10 18:54 UTC) Implemented schema/default route module and registered router in `wepppy/microservices/rq_engine/__init__.py`.
- [x] (2026-04-10 19:05 UTC) Implemented deterministic controller and endpoint metadata payload assembly aligned with contract semantics.
- [x] (2026-04-10 19:12 UTC) Added/extended route, OpenAPI, frozen-artifact, and contract-rule guard coverage.
- [x] (2026-04-10 19:49 UTC) Re-ran all required code gate commands on final remediation set and captured passing evidence.
- [x] (2026-04-10 19:24 UTC) Completed independent `reviewer`, `qa_reviewer`, and `security_reviewer` passes; dispositioned findings.
- [x] (2026-04-10 19:49 UTC) Completed package docs/security closeout and prepared ExecPlan archive with outcome note.

## Surprises & Discoveries

- Initial schema/default metadata was not fully contract-parity-safe for several operations; review surfaced mismatches between declared endpoint metadata and actual handler request/response fields.
- Climate defaults required integer enum normalization (`climate_mode_code`) to match schema type expectations.
- `/upload-sbs` availability must account for disturbed fire-mod support (`disturbed`, `baer`, `ash`, `debris_flow`) rather than generic disturbed-state assumptions.

## Decision Log

- Decision: Keep this package scoped to schema/default metadata surfaces only and defer geospatial/uploads, outputs/progress/errors, and auth-concurrency hardening to follow-on roadmap rows.  
  Rationale: Preserves dependency order and keeps implementation/review surfaces focused.  
  Date/Author: 2026-04-10 / Codex.

- Decision: Require all three independent review gates (`reviewer`, `qa_reviewer`, `security_reviewer`) before closure.  
  Rationale: Schema/default metadata directly controls autonomous parameter selection and validation behavior.  
  Date/Author: 2026-04-10 / Codex.

- Decision: Treat live route handlers as contract source of truth when schema/default descriptor drift is detected.  
  Rationale: Prevents agent planners from consuming unsupported fields and preserves request/response correctness.  
  Date/Author: 2026-04-10 / Codex.

## Outcomes & Retrospective

- Implemented and wired:
  - `GET /api/runs/{runid}/{config}/controllers`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/schema`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/hints`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/templates`
  - `GET /api/runs/{runid}/{config}/endpoints`
  - `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/schema`
  - `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/defaults`
- Added deterministic run-state revision/etag-coupled metadata payload assembly with contract-aligned predicate grammar (`required_if`, `available_if`) and `constraint_mode` handling.
- Hardened review-driven parity fixes:
  - integer climate defaults
  - upload-SBS disturbed-mod gating
  - operation schema/default alignment for soils/wepp/watershed/session-token surfaces
- Expanded regression coverage to include contract-shape assertions, disturbed/baseline availability semantics, and OpenAPI/frozen-artifact parity.
- Closed code, QA, and security gates with no unresolved medium/high findings and completed lifecycle closeout artifacts.

## Context and Orientation

Primary contract references:
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`

Package inputs from completed predecessors:
- `docs/work-packages/20260410_rq_controller_state_foundation/package.md`
- `docs/work-packages/20260410_rq_controller_state_orchestration_reads/package.md`
- `docs/work-packages/20260410_rq_controller_state_orchestration_reads/tracker.md`

Likely implementation/test touchpoints:
- `wepppy/microservices/rq_engine/__init__.py`
- `wepppy/microservices/rq_engine/openapi.py`
- `wepppy/microservices/rq_engine/schema_defaults_routes.py`
- `tests/microservices/test_rq_engine_openapi_contract.py`
- `tests/microservices/test_rq_engine_schema_defaults_routes.py`
- `tools/rq_engine_contract_rules.py`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

Core requirements to enforce:
- Controller and endpoint metadata surfaces align with the proposed contract endpoint set.
- Schema payloads represent `constraint_mode`, conditional predicates, and enum/default semantics in machine-checkable form.
- Defaults payloads are run-resolved where required and deterministic for equivalent state.
- Route auth and error payloads remain canonical and consistent with run access boundaries.

## Plan of Work

Milestone 1 (route scaffolding and auth/contract boundaries): add schema/default routers, route wiring, canonical error boundaries, and run-access checks across controller and endpoint metadata surfaces.

Milestone 2 (payload assembly): implement controller and operation metadata builders with deterministic ordering and contract fields (`constraint_mode`, predicate grammar objects, run-resolved defaults context).

Milestone 3 (tests + checklist parity): add focused route tests (auth matrix, payload contracts, failure boundaries), extend OpenAPI contract coverage, update route contract guards and frozen inventory/checklist artifacts.

Milestone 4 (independent review gates + closeout): run and disposition `reviewer`, `qa_reviewer`, and `security_reviewer` findings; run required validation commands; update package/tracker/security artifact and archive this ExecPlan on closure.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Required reading and orientation
   - Review package and tracker docs for this package and predecessor packages.
   - Re-read contract sections covering controller metadata, endpoint schema/default semantics, and roadmap dependencies.

2. Implementation
   - Add new schema/default route module(s) under `wepppy/microservices/rq_engine/`.
   - Register router(s) in `wepppy/microservices/rq_engine/__init__.py`.
   - Add/adjust OpenAPI metadata in rq-engine route annotations/helpers.

3. Tests and guard updates
   - Add `tests/microservices/test_rq_engine_schema_defaults_routes.py`.
   - Update `tests/microservices/test_rq_engine_openapi_contract.py`.
   - Update `tools/rq_engine_contract_rules.py` as needed.
   - Update frozen artifacts:
     - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
     - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

4. Code validation gate
   - `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
   - `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
   - `python tools/check_endpoint_inventory.py`
   - `python tools/check_route_contract_checklist.py`
   - `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1`

5. Mandatory independent reviews
   - Run `reviewer` subagent and resolve/disposition findings.
   - Run `qa_reviewer` subagent and resolve/disposition findings.
   - Run `security_reviewer` subagent and resolve/disposition findings.
   - Record final findings disposition in package tracker and security artifact.

6. Docs + closeout
   - Update `package.md`, `tracker.md`, and security artifact with final outcomes and gate results.
   - Run `wctl doc-lint` across changed docs and root tracker.
   - Archive this ExecPlan to `prompts/completed/` and add `<plan>_outcome.md`.

## Validation and Acceptance

Acceptance criteria:
- Controller and endpoint schema/default surfaces are implemented with contract-aligned payloads.
- Metadata is deterministic for equivalent run state across baseline and disturbed configs.
- OpenAPI + frozen inventory/checklist + guard tests are updated and passing.
- No unresolved medium/high findings remain from `reviewer`, `qa_reviewer`, or `security_reviewer`.

## Idempotence and Recovery

Work should be performed in small, testable increments. If a milestone fails validation, fix only the failing surface and re-run targeted commands before broad sweeps. Keep payload shape changes and contract-doc updates in the same commit to avoid drift during handoff.

## Artifacts and Notes

- Package tracker: `docs/work-packages/20260410_rq_controller_state_schema_defaults/tracker.md`
- Security artifact: `docs/work-packages/20260410_rq_controller_state_schema_defaults/artifacts/2026-04-10_security_review.md`

## Interfaces and Dependencies

No new external dependencies are expected. Route handlers must preserve canonical rq-engine response/error contracts and remain aligned with frozen route contract artifacts. Any change to agent-facing endpoint inventory/checklist must be reflected in artifact and guard updates within this package.

Change log:
- 2026-04-10 18:21 UTC - Initial active ExecPlan authored for package kickoff.
- 2026-04-10 19:49 UTC - Final remediation, validation, and closeout complete; plan ready for archive to `prompts/completed/`.
