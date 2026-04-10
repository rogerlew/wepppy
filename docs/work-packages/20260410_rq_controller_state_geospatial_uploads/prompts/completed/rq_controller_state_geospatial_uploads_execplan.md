# Implement RQ Controller State Geospatial and Upload Metadata Surfaces

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Deliver run-scoped geospatial metadata and upload metadata contracts so an agent can pick valid first-step watershed parameters and validate upload files before submission. After this package, an agent with `runid/config` can query `/geospatial-metadata` and use endpoint metadata for upload operations to validate format/CRS/extent/resolution/value semantics without trial-and-error.

## Progress

- [x] (2026-04-10 20:17 UTC) Created package scaffold and authored this active ExecPlan.
- [x] Complete required-reading pass across contract docs, predecessor package outputs, freeze artifacts, and rq-engine route inventory.
- [x] Implement geospatial-metadata route module and register router in `wepppy/microservices/rq_engine/__init__.py`.
- [x] Implement upload metadata contract hardening for DEM/CLI/SBS/cover-transform operation metadata.
- [x] Add/extend route/openapi/frozen-artifact tests and guards.
- [x] Run required code gates and record outcomes in package tracker.
- [x] Run mandatory `reviewer`, `qa_reviewer`, and `security_reviewer` subagent passes; disposition findings.
- [x] Complete package docs closeout and archive this ExecPlan to `prompts/completed/` with an outcome note.

## Surprises & Discoveries

- Reviewer/security passes surfaced parity and enforcement gaps that were not obvious in initial green code-gate runs:
  - climate/soils/watershed value drift across metadata surfaces
  - unbounded upload payload sizes in live handlers despite machine-readable metadata hardening goals
- Resolving those gaps required shared helper refactors and additional runtime enforcement/tests, not only descriptor edits.

## Decision Log

- Decision: Keep this package scoped to geospatial and upload metadata surfaces only and defer outputs/progress/errors and auth-concurrency hardening to follow-on roadmap rows.
  Rationale: Preserves dependency order and keeps implementation/review surfaces focused.
  Date/Author: 2026-04-10 / Codex.

- Decision: Require all three independent review gates (`reviewer`, `qa_reviewer`, `security_reviewer`) before closure.
  Rationale: Upload metadata and geospatial defaults directly control autonomous route/parameter and file-validation decisions.
  Date/Author: 2026-04-10 / Codex.

- Decision: Add explicit per-route `max_bytes` enforcement for upload DEM/CLI/SBS/cover-transform handlers in this package.
  Rationale: Security review identified medium risk for authenticated DoS with unbounded uploads; descriptor-only hardening was insufficient.
  Date/Author: 2026-04-10 / Codex.

## Outcomes & Retrospective

- Implemented and shipped:
  - `GET /api/runs/{runid}/{config}/geospatial-metadata`
  - hardened upload metadata descriptors/schemas/defaults for DEM/CLI/SBS/cover-transform
  - runtime upload `max_bytes` enforcement + oversize tests
  - parity helpers/tests for climate mode, soils mode, and watershed defaults across metadata surfaces
- Required code gates, guard scripts, and independent reviewer/QA/security re-reviews all passed.
- No unresolved medium/high findings remained at closeout.

## Context and Orientation

Primary contract references:
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`

Package inputs from completed predecessors:
- `docs/work-packages/20260410_rq_controller_state_setup_discovery/package.md`
- `docs/work-packages/20260410_rq_controller_state_schema_defaults/package.md`
- `docs/work-packages/20260410_rq_controller_state_schema_defaults/tracker.md`

Likely implementation/test touchpoints:
- `wepppy/microservices/rq_engine/__init__.py`
- `wepppy/microservices/rq_engine/openapi.py`
- `wepppy/microservices/rq_engine/` (new geospatial/upload metadata routes module)
- `tests/microservices/test_rq_engine_openapi_contract.py`
- `tests/microservices/` (new geospatial/upload metadata route tests)
- `tools/rq_engine_contract_rules.py`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

Core requirements to enforce:
- `/geospatial-metadata` payload must provide run-resolved coverage/default metadata with deterministic behavior.
- Upload operation metadata must expose machine-checkable file constraints where applicable (type/extension/size/CRS/extent/resolution/value semantics).
- Route auth and error payloads must remain canonical and consistent with run access boundaries.

## Plan of Work

Milestone 1 (route scaffolding and auth/contract boundaries): add `/geospatial-metadata` router, route wiring, canonical error boundaries, and run-access checks.

Milestone 2 (payload assembly): implement geospatial metadata payload generation and upload metadata enrichment for target upload operations through endpoint metadata surfaces.

Milestone 3 (tests + checklist parity): add focused route tests (auth matrix, payload contracts, failure boundaries), extend OpenAPI contract coverage, update route contract guards and frozen inventory/checklist artifacts.

Milestone 4 (independent review gates + closeout): run and disposition `reviewer`, `qa_reviewer`, and `security_reviewer` findings; run required validation commands; update package/tracker/security artifact and archive this ExecPlan on closure.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Required reading and orientation
   - Review package and tracker docs for this package and predecessor packages.
   - Re-read contract sections covering geospatial metadata and upload metadata requirements.

2. Implementation
   - Add new geospatial/upload metadata route module(s) under `wepppy/microservices/rq_engine/`.
   - Register router(s) in `wepppy/microservices/rq_engine/__init__.py`.
   - Add/adjust OpenAPI metadata in rq-engine route annotations/helpers.

3. Tests and guard updates
   - Add `tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py`.
   - Update `tests/microservices/test_rq_engine_openapi_contract.py`.
   - Update `tools/rq_engine_contract_rules.py` as needed.
   - Update frozen artifacts:
     - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
     - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

4. Code validation gate
   - `wctl run-pytest tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py --maxfail=1`
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
- `/geospatial-metadata` is implemented with contract-aligned payload semantics.
- Upload metadata constraints for core upload operations are machine-checkable and aligned with live handler behavior.
- OpenAPI + frozen inventory/checklist + guard tests are updated and passing.
- No unresolved medium/high findings remain from `reviewer`, `qa_reviewer`, or `security_reviewer`.

## Idempotence and Recovery

Work should be performed in small, testable increments. If a milestone fails validation, fix only the failing surface and re-run targeted commands before broad sweeps. Keep payload shape changes and contract-doc updates in the same commit to avoid drift during handoff.

## Artifacts and Notes

- Package tracker: `docs/work-packages/20260410_rq_controller_state_geospatial_uploads/tracker.md`
- Security artifact: `docs/work-packages/20260410_rq_controller_state_geospatial_uploads/artifacts/2026-04-10_security_review.md`

## Interfaces and Dependencies

No new external dependencies are expected. Route handlers must preserve canonical rq-engine response/error contracts and remain aligned with frozen route contract artifacts. Any change to agent-facing endpoint inventory/checklist must be reflected in artifact and guard updates within this package.

Change log:
- 2026-04-10 20:17 UTC - Initial active ExecPlan authored for package kickoff.
- 2026-04-10 21:06 UTC - Execution complete; plan archived to `prompts/completed/` with outcome note.
