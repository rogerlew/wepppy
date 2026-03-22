# Milestone 4 Correctness Review

Date: 2026-03-21
Reviewer: Codex (correctness pass)
Scope: RUSLE NoDb facade, RQ/API wiring, run-page/UI mod-toggle behavior, preflight integration, and stale invalidation paths.

## Findings

### Resolved Medium Findings

1. Route inventory freeze drift after adding `build-rusle`.
- Evidence: `tests/tools/test_endpoint_inventory_guard.py` failed with missing route.
- Resolution: Added `POST /api/runs/{runid}/{config}/build-rusle` to `endpoint_inventory_freeze_20260208.md` and updated snapshot counts.
- Status: Resolved.

2. Route contract checklist drift for `build-rusle`.
- Evidence: `tests/tools/test_route_contract_checklist_guard.py` failed with missing checklist row.
- Resolution: Added checklist row in `route_contract_checklist_20260208.md` with exact required response codes and updated total route count.
- Status: Resolved.

3. Frozen agent-route count mismatch in OpenAPI contract test.
- Evidence: `tests/microservices/test_rq_engine_openapi_contract.py` expected 54 frozen agent routes.
- Resolution: Updated expectation to 55 after adding the new agent-facing route.
- Status: Resolved.

## Correctness Checks Performed

- Verified `Rusle` facade composes `R`, `K`, `LS`, `C`, and `P` and writes final `A` output.
- Verified selected-mode output behavior in K/C integration paths to prevent wrong-artifact emission.
- Verified `scenario_sbs` no-SBS path uses unburned parameters and does not write synthetic `sbs_4class.tif`.
- Verified RAP year options/default source from RAP implementation surface used by `rap.py`.
- Verified POLARIS auto-acquisition requirement checks and explicit payload handoff.
- Verified disturbed-gated `rusle` eligibility and enable-only (no auto-build) behavior.
- Verified build execution path is async through RQ route/worker.
- Verified preflight and stale invalidation for climate rebuild and SBS upload/change/removal paths.

## Outcome

Milestone 4 correctness review complete. No unresolved high or medium findings remain.
