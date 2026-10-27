# RQ212 checkpoint correctness review

## Metadata

- Reviewer: independent `checkpoint_correctness` agent (reviewer role).
- Reviewed: 2026-10-27 19:11 UTC.
- Scope: package, tracker, active ExecPlan, contract-decision checkpoint and new RQ 2.12 migration section in `docs/schemas/rq-response-contract.md`.
- Starting implementation revision: `9231f2427d33b64f971992ac969fd9420c49afd3`.
- This is a preimplementation contract review, not implementation or rollout approval.

## Findings

| ID | Severity | Finding | Required action | Status |
| --- | --- | --- | --- | --- |
| CK-COR-01 | Medium | The checkpoint's Applicable contracts section names cross-cutting contracts but defers exact domain obligations until the later inventory. The required checkpoint must identify applicable current authorities before becoming the implementation ancestor. Cancellation containment, gated batch finalizers, catalog recovery, fork readiness and run-sync recovery are explicitly included surfaces. | Enumerate exact current contract paths/sections and unchanged obligations before committing: directory-maintenance-lock, rq-engine-agent-api cancellation cleanup, batch-task-boundary, query-engine-catalog-refresh and applicable pilot deployment, fork-console, run-sync and the shared fork prerequisite policy. Record that implementation must restore conformance without silently amending those domains. | Resolved |
| CK-COR-02 | Low | The checkpoint records 19:15 UTC although the review clock is approximately 19:11 UTC. Future timestamps weaken the ancestry/timing audit requested by the contract-first standard. | Use actual creation/review time and retain the eventual checkpoint SHA in the tracker. | Resolved |

## Assessment

The operator explicitly authorized exact RQ 2.12.0, local forest rebuild and acceptance, bounded fault injection and an ancestor checkpoint revision. The package correctly treats that as a faithful behavior-preserving migration. It excludes native webhooks, remote operations, Redis flushing, queue erasure, branch changes, new topology and unrelated refactoring. Existing Roads changes remain outside the package diff.

The normative addition is appropriately confined to the runtime version, preserved application contracts, execution-ID boundary, no-webhook requirement and evidence gates. No scientific formula, NoDb schema, permission model or public status/acknowledgment change is authorized. Unsupported historical transitions require preserving procedures; mixed-version safety and reverse-state compatibility are explicitly unproven.

The state matrix separates absent/expired, empty/new, populated, legacy, retry/partial failure and malformed/hostile states. Planned evidence addresses real Redis and worker subprocesses, exact metadata propagation, strict dependencies versus approved tolerant finalizers, real API/auth boundaries and generated-input/output/report semantics. The plan forbids substituting green job status or mocks for artifact acceptance. Planned runtime cutover requires rebuilding/recreating producers and workers and recording actual identities, mounts and versions.

## Residual evidence obligations

No historical-state transition, rollback, real-process behavior or generated model output is approved by this checkpoint review. Before cutover, the active plan must record concrete service commands, fixture provenance and semantics, plus preserved retained-job inventories. Before closeout, reviewers must verify all requested lifecycle categories, no webhook delivery, final forest health and the full generated-artifact evidence chain. Existing unrelated failures require before/after attribution; skipped integration tests do not satisfy direct boundary coverage.

## Verdict

Checkpoint gate: **pass**. Zero unresolved high, medium or low findings. On 2026-10-27 19:11 UTC, the reviewer confirmed the checkpoint now enumerates exact domain authorities and unchanged obligations, and its timestamp is corrected to 19:10 UTC. No RQ implementation edits are present at review time. The primary agent must still obtain the second independent review and commit this checkpoint/disposition as a standalone ancestor before implementation. Final correctness/security review remains mandatory after implementation and actual acceptance.
