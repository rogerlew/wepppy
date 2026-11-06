# Production notifications and asynchronous catalog cutover

Status: executing, authorized 2026-11-06 UTC (November 5 Pacific).

## Purpose and authority

Deploy the published WEPPpy release to wepp1, wepp2 and wepp3, then enable the
notification inbox/population and complete the query-catalog default-worker
cutover with actual production artifact acceptance. The operator explicitly
requested this work package and instructed proceeding with deployment, including
`2111d0eb2` and its five WEPP 261029 defaults (ADR-0138).

The approved readiness sequence includes preserving existing project selections,
additive database migration, coordinated RQ 1.16.2 → 2.12.0 fleet transition,
bounded remote worker holds, and separate feature activation. Existing GC pause
and Runs listing catalog modes remain unchanged. The operator's execution request
ratifies the described bounded worker-hold and scheduler-activation operations;
no repeated approval is needed for those concrete steps. Active scientific jobs
must drain without termination. Unrelated services and unfinished local work are
outside scope. No registry/Kubernetes deployment, new queue/service or project
repair is authorized.

## Complexity and security

Use existing Docker Compose, canonical deployment script, PostgreSQL, Redis/RQ,
shared NFS guards and operator pilot tools. Repair only confirmed deployment
prerequisites. Security impact is high: fleet runtime, private inbox state and
shared queue/publication boundaries. Independent correctness and security reviews
must close medium/high findings before activation and final acceptance.

## Contract and evidence

Canonical authorities: [notifications](../../schemas/user-notifications-contract.md),
[query refresh](../../schemas/query-engine-catalog-refresh-contract.md),
[RQ migration](../../dev-notes/rq-2-12-migration.md), and ADR-0138.
The [readiness assessment](notes/production-deployment-readiness.md) retains
initial inspection and authorized cleanup. Execute the [active plan](prompts/active/deployment_execplan.md)
and maintain the [tracker](tracker.md).

## Acceptance

- [ ] Candidate published with scheduler queue repair and user config defaults.
- [ ] Database backup/restore rehearsal and additive migration verified.
- [ ] Compatible fleet runs the intended images/dependencies/native artifacts.
- [ ] Real notification worker/scheduled/browser/read-state/TTL evidence passes.
- [ ] Fresh default-worker catalog pilot, actual scheduler and full-root capacity
      observation pass with ordinary arrivals and consumer artifacts.
- [ ] Independent reviews, retained rollback/recovery records and scoped cleanup pass.

Fresh model inputs, matched native outputs, reports, notification source/content
and query catalog/schema/receipt chains are required; process health and job
success alone cannot establish completion. A full reconciliation cycle may take
many hours; retain the gate until observed. No production RQ downgrade is claimed
safe after 2.x writes. Stage-specific rollback preserves all accepted work.
