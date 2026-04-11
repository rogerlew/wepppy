---
name: rq-agent-operator
description: "Operate WEPPcloud rq-engine as an API client operator (not a developer operator): discover config/endpoint contracts, inspect run orchestration state, submit mutations, poll jobs, recover from contract-defined errors, and validate outputs."
---

# RQ Agent Operator Skill

Use this skill when the task is to run or verify rq-engine API workflows as an operator client (automation/agent behavior), not to refactor server code.

## Use This Skill For

- Running end-to-end agent workflows against rq-engine APIs.
- Determining next actionable operation from pipeline/readiness surfaces.
- Validating request parameters via endpoint schema/default metadata.
- Polling jobs and handling failure/recovery from documented error catalogs.
- Performing smoke checks of the frozen controller-state surface.

## Do Not Use This Skill For

- Refactoring rq-engine route handlers.
- Queue wiring, worker internals, or service deployment surgery.
- Frontend/browser UI operations unrelated to API contract execution.

## Source-of-Truth Documents

Read these first:

- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/schemas/rq-controller-state-contract.md`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md`

## Required Runtime Inputs

At minimum, define:

- `BASE_URL` (usually `http://localhost/rq-engine/api`)
- `TOKEN` (bearer token)
- `RUNID`
- `CONFIG`

Example:

```bash
export BASE_URL="http://localhost/rq-engine/api"
export TOKEN="<bearer-token>"
export RUNID="<runid>"
export CONFIG="<config>"
```

## Standard Operator Loop

1. Setup discovery before run-scoped calls
- `GET /api/configs`
- `GET /api/endpoints`
- `GET /api/endpoints/{operation_id}/schema`

2. Run-scoped orchestration read
- `GET /api/runs/{runid}/{config}/pipeline`
- `GET /api/runs/{runid}/{config}/readiness`

3. Validate operation payload
- `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/schema`
- `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/defaults`
- `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/errors`

4. Submit operation
- `POST /api/runs/{runid}/{config}/...` endpoint from operation descriptor.

5. Poll if async
- Use `job_id` from response.
- Poll `GET /api/jobstatus/{job_id}` until terminal status.
- On failure, fetch `GET /api/jobinfo/{job_id}`.

6. Re-read orchestration state
- Re-fetch `pipeline` and `readiness`.
- Continue until no required actionable steps remain.

7. Retrieve outputs
- `GET /api/runs/{runid}/{config}/outputs`
- Use export/download paths from returned metadata.

## Minimal Command Set

Use `curl` + `jq` for deterministic checks:

```bash
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/configs" | jq '.configs | length'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/pipeline" | jq '.steps | length'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/readiness" | jq '.next_actionable_steps'
```

## Error and Recovery Rules

- Treat HTTP status as primary signal; then inspect canonical error payload.
- For operation recovery, use `.../endpoints/{operation_id}/errors` catalog and `recovery_actions`/required fields.
- Do not invent parameter names; only send fields present in operation schema.
- If auth fails, verify required scope for that endpoint family before retrying.

## Safety Guardrails

- Stay within run scope (`RUNID/CONFIG`) unless explicitly instructed otherwise.
- Do not execute destructive mutations unless the user asked for them.
- Do not bypass scope checks or use undocumented internal endpoints as substitutes.
- Preserve auditability: report exact command/result pairs for critical steps.

## Smoke-Test Shortcut

When asked to "get ready for smoke" or "run smoke":

1. Execute Phase A from the canonical runbook:
- `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md`
2. If needed, execute Phase B manual API smoke using the same runbook.
3. Report pass/fail with command outputs and first failing step (if any).

## Reporting Template

Use this concise structure:

- `Status`: pass/fail
- `Environment`: BASE_URL + run context used
- `Checks Run`: command list and outcomes
- `Findings`: blocker first, then medium/low
- `Next Action`: exact command or API step
