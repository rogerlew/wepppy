# RQ 2.12.0 upgrade

**Status**: Closed 2026-10-27
**Timezone**: UTC

## Overview

Upgrade WEPPpy from RQ 1.16.2 to exactly 2.12.0 while preserving existing task behavior. This is a faithful behavior-preserving migration, not a scaffold-only deliverable. Implementation, rebuilt forest runtime, generated-output acceptance and independent reviews are separate mandatory gates.

## Scope and authority

The operator authorized local forest development rebuild/recreation, safe worker drainage, disposable projects and fault injection against package-owned jobs. Compose authority is `docker/docker-compose.dev.yml` through installed `wctl`. Preserve unrelated jobs and working-tree changes. No branch change, remote operation, production deployment or push. Never flush Redis, erase queues, delete volumes or discard existing runs.

## Complexity Budget

Reuse existing services, queues, identities, mounts, permissions and persistence. Permit only exact dependency updates (including required transitive dependencies), confirmed compatibility repairs, regression coverage and documentation. Test the minimal dependency update first. No new topology, datastore, service, permission model, broad compatibility wrapper or unrelated refactor. Native webhooks are out of scope: no configuration exposure, delivery enablement or infrastructure.

## Implementation Fidelity and Evidence

Faithful migration of `wepppy/rq/`, enqueue hooks, profile runtime, rq-engine and recovery/status consumers. Prove the exact version in every producer/worker container. Actual Redis and worker subprocesses must establish dependency, retry, cancellation, execution tracking and recovery semantics; mocks cannot establish these boundaries.

## Generated Artifact Validation Gate

Required on forest: clone a bounded available project using its supported lifecycle, submit through actual API/auth and installed workers, retain request/configuration, reload persisted state, parse generated model inputs at consumed paths, inspect fresh outputs and retrieve user-facing report/output. Compare with 1.16.2 baseline or explicit semantic expectations. Repeat a representative fan-out/fan-in workflow, failure/recovery and successful resubmission. Record identities/groups/mounts/umask/build/source and fixture provenance. No completion claim based solely on job success.

## Security Impact

High: queue serialization, auth metadata, ownership, cancellation and process containment span trust boundaries. Dedicated independent security and correctness reviews are required; all medium/high findings must close with evidence. Preserve current auth/access, disclosure, locks and descendant-process containment. Parameterization changes: none; ADR not required.

## Success Criteria

- [x] Versioned distribution provenance, full dependency resolution and compatibility matrix retained.
- [x] Baseline, old-job fixtures and safe historical-state/rollback procedures verified.
- [x] Minimal compatibility fixes and all thirteen lifecycle/consumer categories plus no-webhook coverage pass.
- [x] Required migration checks pass on isolated committed source; unrelated working-tree Roads provenance failure is independently attributed and preserved.
- [x] Rebuilt forest producers/workers run 2.12.0 and actual API/model/report acceptance passes.
- [x] Independent correctness/security findings closed; durable docs promoted and plan archived.

## Execution

See [tracker](tracker.md) and [completed ExecPlan](prompts/completed/implementation_execplan.md). Starting revision: `9231f2427d33b64f971992ac969fd9420c49afd3`. Completed: implementation, rebuilt forest acceptance, isolated full regression and independent reviews. Production unchanged.

## Delivered implementation and evidence

- Checkpoint `b1054fac7` precedes implementation `b5cac8166`; sibling dashboard
  compatibility commit `91f62b9` is also retained as a reproducible repository patch.
- Exact RQ 2.12.0 and required croniter 6.0.0 are the only installed distribution
  changes in the shared runtime. Four existing package versions were pinned to
  prevent unrelated rebuild drift. Redis remains 6.2.0.
- Compatibility repairs cover prepublication metadata, plain status values,
  timezone-aware timestamps, execution-registry discovery, removed version-cache
  API, approved stopped-parent finalizers and scheduler socket ownership.
- [Compatibility inventory](artifacts/compatibility_inventory.md),
  [dependency delta](artifacts/installed-dependency-delta.json) and
  [historical compatibility](artifacts/historical_compatibility.md) establish the
  distribution and supported migration boundary.
- [Forest cutover](artifacts/forest_cutover.md) and
  [final runtime readback](artifacts/forest_runtime_final.json) identify all 17
  installed services, images, identities, mounts and permissions.
- [Integrated acceptance](artifacts/acceptance_upgraded.md) proves the real
  18-node model graph, 155 identical consumed inputs, 25 scientifically identical
  Parquets, three exact CSV reports, cancellation/ownership/resubmission and
  archive/download/restoration of 417 generated files.
- [Final validation ledger](artifacts/final_validation.md),
  [correctness review](artifacts/20261027_correctness_review.md) and
  [security review](artifacts/20261027_security_review.md) retain final gate results and sign-offs.

## Durable decisions and remaining limits

Normative scope and rationale live in
[RQ response contract — runtime migration](../../schemas/rq-response-contract.md#rq-212-runtime-migration).
Operational compatibility, historical-state drainage, rollback boundaries and
the existing NFS retained-log-handle restore limitation live in
[RQ migration and recovery](../../dev-notes/rq-2-12-migration.md).
Running 1.x jobs must drain; mixed workers and in-place downgrade of 2.x-written
state are unsupported. The isolated original-state rollback proof does not
permit discarding accepted newer work. No production rollout or push occurred;
native webhooks remain disabled and unexposed.

Final regression: **11,948 passed, 226 skipped** on isolated committed migration source; **598 targeted + 13 lifecycle passed**, with zero skips in those focused runs. Original dirty-tree full invocation stopped at 6,810 passed/61 skipped on an unrelated Roads provenance mismatch, reproduced under RQ 1.16.2. No unrelated source or publication record was changed.
