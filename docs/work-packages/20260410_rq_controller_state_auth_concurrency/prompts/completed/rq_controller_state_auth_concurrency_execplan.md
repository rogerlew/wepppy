# Implement RQ Controller State Auth and Concurrency Surfaces

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Deliver auth-scope, concurrency, and idempotency hardening so autonomous agents can operate safely without stale writes or ambiguous auth behavior. After this package, controller-state surfaces have contract-aligned auth metadata/behavior, explicit optimistic concurrency guarantees, and idempotency behavior that matches declared policies.

## Progress

- [x] (2026-04-10 20:17 UTC) Created package scaffold and authored this active ExecPlan.
- [x] Complete required-reading pass across contract docs, predecessor package outputs, freeze artifacts, and rq-engine route inventory.
- [x] Implement/finish auth scope rollout behavior and metadata parity (`rq:read` and compatibility boundaries).
- [x] Implement/finish concurrency precondition enforcement with canonical conflict responses.
- [x] Implement/finish idempotency behavior parity where policies declare support.
- [x] Add/extend route/openapi/frozen-artifact tests and guards.
- [x] Run required code gates and record outcomes in package tracker.
- [x] Run mandatory `reviewer`, `qa_reviewer`, and `security_reviewer` subagent passes; disposition findings.
- [x] Complete package docs closeout and archive this ExecPlan to `prompts/completed/` with an outcome note.

## Surprises & Discoveries

- Initial review passes surfaced a real idempotency parity gap for anonymous public-run fallback: replay keys were effectively non-deduplicated due per-request random namespace. Fixed with a stable anonymous namespace and dedicated regression coverage.
- Initial implementation added a broad JSON parse catch; changed-file broad-exception enforcement flagged this drift. Narrowing the parse exception path restored policy compliance.
- Security review highlighted that bearer `rq:status` can mint broader session scopes. This is explicit in current contract and descriptor metadata, so it was recorded as an accepted residual design risk rather than a package defect.

## Decision Log

- Decision: Keep this package scoped to auth/concurrency/idempotency semantics only and defer final contract cutover reconciliation to row 8.
  Rationale: Preserves roadmap sequencing and isolates high-risk behavior changes.
  Date/Author: 2026-04-10 / Codex.

- Decision: Require all three independent review gates (`reviewer`, `qa_reviewer`, `security_reviewer`) before closure.
  Rationale: Authorization and write-safety semantics are security-critical boundaries.
  Date/Author: 2026-04-10 / Codex.

- Decision: Preserve contract-defined session-token scope bridge (`rq:status` bearer requirement with broader minted session scopes) in this package.
  Rationale: Behavior is explicit across contract/descriptor/runtime and changing it here would be policy-level cutover scope expansion.
  Date/Author: 2026-04-10 / Codex.

## Outcomes & Retrospective

- Added `rq:read` to minted session token scopes and validated compatibility boundaries for controller-state read surfaces.
- Added session-token optimistic concurrency precondition enforcement (`X-Run-State-Match` and `expected_run_state_revision`) with canonical `stale_run_state` conflicts.
- Added idempotency replay/mismatch enforcement for session-token operation and aligned descriptor metadata with runtime policy (including dedupe TTL parity).
- Added route regressions for malformed/non-object JSON, idempotency key length validation, replay/mismatch handling, and anonymous public-fallback duplicate replay handling.
- Completed all required code gates and independent review gates.
- Final status: no unresolved medium/high defects from reviewer, QA reviewer, or security reviewer.

## Artifacts and Notes

- Package tracker: `docs/work-packages/20260410_rq_controller_state_auth_concurrency/tracker.md`
- Security artifact: `docs/work-packages/20260410_rq_controller_state_auth_concurrency/artifacts/2026-04-10_security_review.md`
- Outcome note (to be archived with this ExecPlan):
  `docs/work-packages/20260410_rq_controller_state_auth_concurrency/prompts/completed/rq_controller_state_auth_concurrency_execplan_outcome.md`

Change log:
- 2026-04-10 20:17 UTC - Initial active ExecPlan authored for package kickoff.
- 2026-04-10 22:52 UTC - Execution complete; ready for archive.
