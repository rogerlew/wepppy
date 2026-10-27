# RQ 2.12.0 upgrade

**Status**: Open (2026-10-27)  
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

- [ ] Versioned distribution provenance, full dependency resolution and compatibility matrix retained.
- [ ] Baseline, old-job fixtures and safe historical-state/rollback procedures verified.
- [ ] Minimal compatibility fixes and all thirteen lifecycle/consumer categories plus no-webhook coverage pass.
- [ ] Required repository checks pass, or unrelated failures are explicitly isolated and resolved for closeout.
- [ ] Rebuilt forest producers/workers run 2.12.0 and actual API/model/report acceptance passes.
- [ ] Independent correctness/security findings closed; durable docs promoted and plan archived.

## Execution

See [tracker](tracker.md) and [active ExecPlan](prompts/active/implementation_execplan.md). Starting revision: `9231f2427d33b64f971992ac969fd9420c49afd3`. Current claim: investigation only; production unchanged.
