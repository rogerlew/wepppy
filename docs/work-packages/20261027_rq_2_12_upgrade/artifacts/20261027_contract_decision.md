# RQ212 contract checkpoint

**Date**: 2026-10-27 19:10 UTC
**Starting revision**: `9231f2427d33b64f971992ac969fd9420c49afd3`
**Status**: accepted by two independent reviews; implementation has not begun.

## Authority and exact delta

The operator explicitly requested execution of the exact RQ 2.12.0 migration,
local forest rebuild/acceptance, independent reviews, and the required standalone
ancestor revision. This authorizes the bounded checkpoint commit, with no branch
change or push. Application behavior is unchanged. The only normative addition
is the version target and migration acceptance/rollout boundary in
`docs/schemas/rq-response-contract.md#rq-212-runtime-migration`.
Native webhooks remain disabled/unexposed; no infrastructure is introduced.

## Applicable contracts and discrepancy classification

`docs/schemas/rq-response-contract.md` governs IDs, acknowledgments, public
status/error serialization and cancellation ownership.
`docs/schemas/nodb-persistence-concurrency-contract.md` and
`docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md` remain unchanged:
lock ownership, fresh mutation hydration and atomic persistence are preserved.
Additional unchanged authorities are:

- `docs/schemas/directory-maintenance-lock-contract.md`, RQ cancellation ownership:
  exact execution/token ownership and verified termination of all writers.
- `docs/schemas/rq-engine-agent-api-contract.md`, Auth Model, Scope Contract,
  Cancellation directory-lock cleanup and Correlation ID Debugging: preserve
  access, cancellation and correlation semantics.
- `docs/schemas/batch-task-boundary-contract.md`, Tasks and handoff, Failure,
  retry and cancellation, Compatibility/state matrix/artifacts: preserve gated
  terminal observers, strict scientific prerequisites and durable receipts.
- `docs/schemas/query-engine-catalog-refresh-contract.md`, Identity and admission,
  Recovery and liveness, Lifecycle and visibility, Shared batch admission:
  preserve coalescing, exact job ownership, recovery and disclosure boundaries.
- `docs/schemas/query-catalog-pilot-deployment-contract.md`, Preflight and
  acceptance: preserve unrelated work and retained image identity. Its remote
  pilot-specific deployment scope is not authorization for this local upgrade;
  no pilot enablement or remote deployment is included.
- `docs/ui-docs/contracts/fork-console-contract.md`, Destination readiness and
  Scope and authority: retain exact job/source/destination binding and legacy
  argument compatibility. Archive directory metadata and byte-preserving restore
  remain governed by `docs/standards/artifact-observability-standard.md`.
- `docs/schemas/run-sync-contract.md`, Replacement semantics and Failure and
  compatibility: preserve bounded file replacement, auth, queue and failure
  behavior. No remote synchronization acceptance is authorized; use local fixture.

No normative amendment to these domains is proposed. Confirmed incompatibilities are conformance repairs under the
new runtime, not permission to change domain behavior.

## Compatibility and security

Preserve actor/correlation/profile metadata, strict downstream requirements,
approved tolerant finalizers, receipt ambiguity recovery, retries, stop/cancel,
timeout/abandonment and directory/process containment. RQ execution IDs are
internal. No permission or serialization trust boundary is expanded. Security
impact is high because runtime changes can affect all of these boundaries.

## State and regression matrix

| State | Required outcome | Evidence required |
| --- | --- | --- |
| Absent/expired job | Existing not-found contract | Actual polling |
| Empty queues/new project | Existing initialization/submission | Real API and worker |
| Populated graph | Exact acknowledgment, strict release, existing status | Real Redis graph and generated output |
| Historical six lifecycle states | Proven compatibility or preserving drain procedure | Persisted 1.16.2 fixtures in 2.12 |
| Retry/partial failure | No false terminal completion or duplicate execution | Crash/retry/resubmit and artifact readback |
| Malformed/hostile input | Existing bounded authorization/validation failure | Ownership/cancel/context isolation tests |

No new user-reachable failure policy is authorized. Existing domain-required
failures retain canonical envelopes. Failure to import removed RQ APIs or parse
new status/execution representations is a migration defect to repair.

## Acceptance and review

The active ExecPlan defines lifecycle coverage, local production-equivalent
identity/mount/API/generated-output acceptance, and isolated rollback proof.
Two independent checkpoint reviews must pass before this checkpoint is committed
as an implementation ancestor. Final correctness/security reviews require actual
evidence and closed medium/high findings. No implementation or runtime cutover
claim is made by this checkpoint.

## Review disposition

Independent correctness and security checkpoint reviews passed on 2026-10-27
19:10 UTC. Correctness COR-01 (explicit domain authority inventory) and COR-02
(timestamp accuracy) were corrected and independently rechecked. No open
medium/high findings. See `20261027_checkpoint_correctness.md` and
`20261027_checkpoint_security.md`. These approvals cover the checkpoint only.
