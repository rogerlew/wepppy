# Implement RQ Setup Discovery Endpoints

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` were kept current during execution.

This document is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Deliver setup discovery in rq-engine so an agent can discover valid configs and setup operation contracts directly from `/api/configs` and `/api/endpoints*`, then call `/create/` without out-of-band docs.

## Progress

- [x] (2026-04-10 06:58 UTC) Completed required-reading pass and bootstrapped package scaffold (`package.md`, `tracker.md`, `prompts/active/`, `prompts/completed/`, `artifacts/`).
- [x] Implemented rq-engine setup-discovery route module and wired it into `wepppy/microservices/rq_engine/__init__.py`.
- [x] Added route-level and OpenAPI contract tests for setup discovery.
- [x] Updated frozen inventory/checklist artifacts and contract-rule helpers.
- [x] Updated schema/docs/work-package lifecycle docs and `PROJECT_TRACKER.md`.
- [x] Ran required code gates, QA/security subagent reviews, docs lint, and package closeout archive.

## Surprises & Discoveries

- `POST /create/` runtime behavior is redirect-only (`303`) and does not currently enforce idempotency, so setup descriptor/schema metadata had to be aligned to runtime behavior.
- Setup detail routes needed explicit route-boundary exception handling to guarantee canonical JSON `500` payloads under helper failures.
- OpenAPI metadata budget needed recalibration for the expanded 67-route frozen baseline after adding six setup routes.

## Decision Log

- Decision: Setup discovery remains bearer-authenticated with `rq:status` compatibility and `rq:read` parity for rollout.
  Rationale: Preserves existing read compatibility while keeping setup routes explicit and read-only.
  Date/Author: 2026-04-10 / Codex

- Decision: For this package, align `rq_engine_create` setup metadata to runtime (`idempotency_policy.supported=false`) instead of implementing idempotency behavior in `/create/`.
  Rationale: Keeps scope minimal and contract-driven; defers idempotency rollout to `20260410_rq_controller_state_auth_concurrency`.
  Date/Author: 2026-04-10 / Codex

## Outcomes & Retrospective

- Added setup-discovery routes:
  - `GET /api/configs`
  - `GET /api/configs/{config}`
  - `GET /api/endpoints`
  - `GET /api/endpoints/{operation_id}/schema`
  - `GET /api/endpoints/{operation_id}/defaults`
  - `GET /api/endpoints/{operation_id}/errors`
- Added/expanded setup-route tests for:
  - full auth matrix across all setup endpoints
  - strict payload key/type checks
  - canonical `500` boundary behavior
  - metadata/runtime parity for create redirect behavior
- Updated frozen artifacts and contract checks for six new agent-facing routes.
- Completed reviewer, QA, and security subagent disposition with no unresolved medium/high findings.
- Closed package lifecycle docs and archived this ExecPlan.

## Context and Orientation

Relevant implementation paths:
- `wepppy/microservices/rq_engine/setup_discovery_routes.py`
- `wepppy/microservices/rq_engine/__init__.py`
- `tests/microservices/test_rq_engine_setup_discovery_routes.py`
- `tests/microservices/test_rq_engine_openapi_contract.py`
- `tools/rq_engine_contract_rules.py`

Relevant contracts and freeze artifacts:
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

## Plan of Work

Implemented a dedicated setup-discovery router that emits operation descriptors and per-operation schema/default/error documents with OpenAPI-aligned `operation_id` values, canonical error payloads, and read-only auth semantics. Then updated tests, frozen artifacts, and lifecycle docs, and completed security/QA/reviewer dispositions before closeout.

## Validation and Acceptance

Required commands executed and passing:
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_setup_discovery_routes.py --maxfail=1`
- `python tools/check_endpoint_inventory.py`
- `python tools/check_route_contract_checklist.py`
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1`

Acceptance criteria met:
- Setup-discovery routes implemented and discoverable.
- `operation_id` alignment and route-contract parity enforced by tests/guards.
- Freeze/checklist artifacts updated to include setup routes.
- Reviewer/QA/security gates closed with no unresolved medium/high findings.

## Artifacts and Notes

- Package tracker: `docs/work-packages/20260410_rq_controller_state_setup_discovery/tracker.md`
- Security artifact: `docs/work-packages/20260410_rq_controller_state_setup_discovery/artifacts/2026-04-10_security_review.md`
- Outcome note:
  - `docs/work-packages/20260410_rq_controller_state_setup_discovery/prompts/completed/rq_controller_state_setup_discovery_execplan_outcome.md`

## Interfaces and Dependencies

Setup discovery route metadata must remain aligned with FastAPI OpenAPI operation IDs (`rq_engine_*`) and the frozen artifact guard set. Runtime and descriptor parity for auth modes, response shape, and idempotency claims is required to prevent client planning drift.

Change log:
- 2026-04-10 06:58 UTC - Initial active ExecPlan authored.
- 2026-04-10 07:29 UTC - Archived as completed after implementation, validation, and closeout.
