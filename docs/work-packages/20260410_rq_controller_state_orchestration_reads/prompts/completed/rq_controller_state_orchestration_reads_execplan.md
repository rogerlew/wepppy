# Implement RQ Controller State Orchestration Reads (`/pipeline` + `/readiness`)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Deliver run-scoped orchestration read APIs so an agent can execute WEPPcloud runs deterministically from machine-readable state. After this package, an agent with `runid/config` can query `/pipeline` and `/readiness`, identify runnable operations, recover from blockers using stable issue joins, and avoid heuristic sequencing.

## Progress

- [x] (2026-04-10 17:11 UTC) Created package scaffold and authored this active ExecPlan.
- [x] (2026-04-10 17:28 UTC) Completed required-reading pass across contract docs, predecessor package outputs, freeze artifacts, and rq-engine route inventory.
- [x] (2026-04-10 17:31 UTC) Implemented orchestration-read route module and registered router in `wepppy/microservices/rq_engine/__init__.py`.
- [x] (2026-04-10 17:33 UTC) Implemented deterministic pipeline/readiness payload assembly with run-scoped auth, issue joins, invalidation lineage, and deterministic next-action ordering.
- [x] (2026-04-10 17:36 UTC) Added/extended route, OpenAPI, frozen-artifact, and contract-rule guard coverage.
- [x] (2026-04-10 18:08 UTC) Re-ran all required code gate commands on final remediation set and captured passing evidence.
- [x] (2026-04-10 18:07 UTC) Completed independent `reviewer`, `qa_reviewer`, and `security_reviewer` passes; dispositioned all findings.
- [x] (2026-04-10 18:08 UTC) Completed package docs/security closeout and prepared ExecPlan archive with outcome note.

## Surprises & Discoveries

- OpenAPI aggregate size and frozen metadata budgets required minor tightening after adding two new frozen agent-facing endpoints; endpoint metadata remained within per-route limits after trimming route descriptions.
- Review passes exposed subtle orchestration semantics: broad `ValueError` mapping hid non-not-found failures as `404`, and generic finished-job fallback could misclassify fan-out parent jobs without child-status folding.
- Empty timeline payloads originally produced per-request `updated_at` drift while keeping stable etags; a deterministic fallback timestamp was required for payload/etag coherence.

## Decision Log

- Decision: Keep this package scoped to orchestration reads only (`/pipeline`, `/readiness`) and defer schema/default/errors/outputs/auth-concurrency to roadmap follow-ons.
  Rationale: Preserves dependency order from the contract roadmap and keeps review surfaces focused.
  Date/Author: 2026-04-10 / Codex.

- Decision: Require all three independent review gates (`reviewer`, `qa_reviewer`, `security_reviewer`) before closure.
  Rationale: Endpoint semantics here directly control autonomous agent decision-making and run-state disclosure.
  Date/Author: 2026-04-10 / Codex.

- Decision: Build orchestration payloads from existing NoDb + RedisPrep state snapshots with explicit deterministic DAG ordering, instead of introducing new persistence fields in this package.
  Rationale: Keeps row-3 scope additive and avoids cross-package schema/storage churn while preserving deterministic machine-readable reads.
  Date/Author: 2026-04-10 / Codex.

- Decision: Narrow not-found mapping to a dedicated `RunConfigMismatchError` and treat all other runtime state-load value errors as canonical `500`.
  Rationale: Preserves explicit failure semantics and prevents internal data faults from being misreported as missing runs.
  Date/Author: 2026-04-10 / Codex.

- Decision: Normalize naive job timestamps to UTC and derive effective job status/ended-at from recursive child-job trees before readiness/pipeline status evaluation.
  Rationale: Avoids timezone-dependent drift and premature completion classification for fan-out orchestration jobs.
  Date/Author: 2026-04-10 / Codex.

## Outcomes & Retrospective

- Implemented and wired:
  - `GET /api/runs/{runid}/{config}/pipeline`
  - `GET /api/runs/{runid}/{config}/readiness`
- Added deterministic orchestration payload assembly with stable issue joins, invalidation lineage, next-action prioritization, and run-state revision/etag generation.
- Hardened boundary/error semantics after independent review:
  - dedicated config-mismatch exception for `404`
  - canonical `500` for non-not-found value failures
  - timezone-stable timestamp parsing
  - deterministic `updated_at` fallback
  - child-job status folding for fan-out queue trees
- Expanded route regression coverage to 25 tests, including:
  - run-access denial and malformed path handling
  - completion fallback and revision sensitivity
  - traceback redaction
  - baseline/disturbed determinism
  - roads/swat completion semantics
  - child-tree status precedence and ended-at folding
- Closed code, QA, and security gates with no unresolved medium/high findings and completed lifecycle closeout artifacts.

## Context and Orientation

Primary contract references:
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`

Package inputs from completed predecessor:
- `docs/work-packages/20260410_rq_controller_state_setup_discovery/package.md`
- `docs/work-packages/20260410_rq_controller_state_setup_discovery/tracker.md`

Likely implementation/test touchpoints:
- `wepppy/microservices/rq_engine/__init__.py`
- `wepppy/microservices/rq_engine/openapi.py`
- `wepppy/microservices/rq_engine/` (new orchestration-read routes module)
- `tests/microservices/test_rq_engine_openapi_contract.py`
- `tests/microservices/` (new orchestration-read route tests)
- `tools/rq_engine_contract_rules.py`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

Core requirements to enforce:
- Canonical step IDs must be a deterministic subset of the contract core step vocabulary.
- `status`, `preconditions_met`, `can_run_now`, `allow_rerun`, `parallel_group`, and `last_attempt` semantics must align with contract state-machine definitions.
- Readiness joins must be machine-safe (`blocked_by_issue_ids` references concrete `issue_id` values).
- Run-scoped auth and response/error contracts must remain canonical.

## Plan of Work

Milestone 1 (route scaffolding and auth/contract boundaries): add the orchestration-read router, route wiring, canonical error boundaries, and auth/run-access checks for both endpoints.

Milestone 2 (payload assembly): implement pipeline/readiness builders that emit deterministic state for baseline and disturbed runs. Include `active_mods`, state transitions, invalidation lineage (`recent_invalidations`, `invalidated_steps`), and deterministic `next_actionable_steps` ordering.

Milestone 3 (tests + checklist parity): add focused route tests (auth matrix, payload contracts, failure boundaries), extend OpenAPI contract coverage, update route contract guards and frozen inventory/checklist artifacts.

Milestone 4 (independent review gates + closeout): run and disposition `reviewer`, `qa_reviewer`, and `security_reviewer` findings; run required validation commands; update package/tracker/security artifact and archive this ExecPlan on closure.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Required reading and orientation
   - Review package and tracker docs for this package and predecessor package (`setup_discovery`).
   - Re-read contract sections covering step vocabulary, state machine semantics, pipeline/readiness payloads, and roadmap dependencies.

2. Implementation
   - Add new orchestration-read route module under `wepppy/microservices/rq_engine/`.
   - Register router in `wepppy/microservices/rq_engine/__init__.py`.
   - Add/adjust OpenAPI metadata in rq-engine route annotations/helpers.

3. Tests and guard updates
   - Add `tests/microservices/test_rq_engine_orchestration_read_routes.py`.
   - Update `tests/microservices/test_rq_engine_openapi_contract.py`.
   - Update `tools/rq_engine_contract_rules.py` as needed.
   - Update frozen artifacts:
     - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
     - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

4. Code validation gate
   - `wctl run-pytest tests/microservices/test_rq_engine_orchestration_read_routes.py --maxfail=1`
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
- `/pipeline` and `/readiness` endpoints are implemented, authenticated correctly, and return contract-aligned payloads.
- Deterministic readiness-to-next-action loop is verified for both baseline and disturbed configs.
- OpenAPI + frozen inventory/checklist + guard tests are updated and passing.
- No unresolved medium/high findings remain from `reviewer`, `qa_reviewer`, or `security_reviewer`.

## Idempotence and Recovery

Work should be performed in small, testable increments. If a milestone fails validation, fix only the failing surface and re-run targeted commands before broad sweeps. Keep payload shape changes and contract-doc updates in the same commit to avoid drift during handoff.

## Artifacts and Notes

- Package tracker: `docs/work-packages/20260410_rq_controller_state_orchestration_reads/tracker.md`
- Security artifact: `docs/work-packages/20260410_rq_controller_state_orchestration_reads/artifacts/2026-04-10_security_review.md`

## Interfaces and Dependencies

No new external dependencies are expected. Route handlers must preserve canonical rq-engine response/error contracts and must remain aligned with frozen route contract artifacts. Any change to agent-facing endpoint inventory/checklist must be reflected in artifact and guard updates within this package.

Change log:
- 2026-04-10 17:11 UTC - Initial active ExecPlan authored for package kickoff.
- 2026-04-10 18:08 UTC - Final remediation, validation, and closeout complete; plan ready for archive to `prompts/completed/`.
