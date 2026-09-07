# Tracker - GridMET Redis Admission and Queue Visibility

## Quick Status

**Timezone**: UTC
**Started**: 2026-09-07 15:53 UTC
**Current phase**: Complete; Forest enabled and verified
**Last updated**: 2026-09-07 17:08 UTC
**Security impact**: `high`; independent review required
**Live authorization**: `forest` development stack only
**Later batch validation**: explicitly deferred to the post-package
`openwepp.org` deployment

## Task Board

### Ready / Backlog

None within this package.

### In Progress

None.

### Blocked

None.

### Done

- [x] Execute the active ExecPlan contract-first from repository `master`.
- [x] Add the GridMET admission contract and parameterization ADR.
- [x] Implement FIFO queue state, expiring leases, configuration, diagnostics,
  and explicit error taxonomy in a separate admission module.
- [x] Integrate every GridMET client and indirect runtime caller while
  preserving default-off behavior.
- [x] Add unit, real-Redis, multiprocessing, and client-wiring tests.
- [x] Add Compose propagation, configuration reference, operational runbook,
  and reusable Forest probe.
- [x] Complete focused and full local/container validation.
- [x] Complete independent correctness, QA/code, and security reviews.
- [x] Commit and push the reviewed candidate before Forest deployment.
- [x] Deploy the exact candidate and environment values to `forest`, recreate
  only affected services, and verify revision/config parity.
- [x] Run the cross-container concurrency probe and one admitted public GridMET
  acquisition on Forest; save evidence and prove cleanup.
- [x] Close the package without running a batch or deploying Kubernetes.

- [x] Assessed the present GridMET acquisition paths and confirmed that the
  multiple-interpolated limit is process-local (2026-09-07 15:53 UTC).
- [x] Ratified Redis coordination, queue-state visibility, and opt-in
  construction with Roger Lew (2026-09-07 15:53 UTC).
- [x] Scaffolded package, tracker, active ExecPlan, deployment boundary, and
  Forest integration acceptance (2026-09-07 15:53 UTC).

## Completion

Contract ancestor: `1b4835ca73bc67c9c84ecbb26f596aab4078e234`. Runtime
candidate: `ae5d107d44a77c6ff3d0288e97b86cac174a77a4`, pushed before Forest
deployment. Final full suite 7,651 passed / 72 skipped; nine isolated Redis
scenarios passed. All independent reviews passed.
[Forest evidence](artifacts/2026-09-07_forest_integration.md) records two-container
peak two/FIFO, killed waiter and holder reclamation, a successful 366-row public
request, zero final state, actual rollback, and restored enabled limit four.
All 11 workers remained healthy/idle. No batch or Kubernetes work was performed.

## Decisions Log

### 2026-09-07 15:53 UTC: Separate admission module and explicit opt-in

**Decision**: Place coordination in `wepppy.climates.gridmet.admission` and
construct configuration/admission only when the enable environment variable is
present and true.

**Rationale**: GridMET HTTP clients need one reusable boundary, while scripts,
tests, and deployments without the variables must retain zero Redis dependency.

### 2026-09-07 15:53 UTC: Queue state is part of correctness

**Decision**: Track FIFO waiting tickets and expiring active leases rather than
only an active counter. Expose position/count/wait state, but not an ETA.

**Rationale**: A counter cannot distinguish waiting from hung work or support
bounded, diagnosable admission timeouts. Variable upstream durations make ETA
claims unreliable even when position is known.

### 2026-09-07 15:53 UTC: Forest integration is a closeout gate

**Decision**: Package completion requires an agent-run test across independent
containers sharing the live Forest Redis plus an actual admitted GridMET client
request. A batch and all Kubernetes work remain deferred.

**Rationale**: Unit tests cannot prove the deployment-wide property, while a
bounded unique-key probe can prove coordination without starting a batch.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Pod/process death leaks capacity | High | Medium | Expiring ownership leases and renewal tests | Mitigated; validated |
| Dead waiter blocks FIFO queue | High | Medium | Queue-ticket TTL, heartbeat, and pruning | Mitigated; validated |
| Retry amplification retains permits | High | Medium | Per-attempt permit and release before backoff | Mitigated; validated |
| Redis outage removes protection | High | Low | Enabled mode fails closed with explicit error | Mitigated; validated |
| Process pool pickles unsafe client state | High | Medium | Pass immutable config; connect lazily in child | Mitigated; validated |
| Long stream outlives lease | High | Medium | Ownership-safe renewal during streaming | Mitigated; validated |
| Queue position misrepresented as ETA | Medium | Medium | Contract and logs expose state without ETA | Mitigated; validated |
| Live probe pollutes operational keys | Medium | Low | Unique namespaced key, final emptiness proof, targeted cleanup | Mitigated; validated |
| Forest-only success overclaimed | High | Medium | Explicit Kubernetes/batch exclusion in every closeout artifact | Mitigated; validated |

## Verification Checklist

- [x] Default-off path proves zero Redis construction/I/O.
- [x] Configuration rejects invalid boolean, numeric, and timing relationships.
- [x] Atomic scripts use Redis time and ownership tokens.
- [x] FIFO, limit, renewal, release, cancellation, and expiry tests pass.
- [x] Retry sleeps occur with no active permit.
- [x] Public point and gridded clients are wired.
- [x] PRISM, Daymet, SNOTEL/supplement, monthly precipitation, observed GridMET,
  and multiple-interpolated callers propagate opt-in configuration.
- [x] `ProcessPoolExecutor` path uses serializable configuration only.
- [x] `docker/docker-compose.dev.yml` renders with default-off and enabled values.
- [x] `docs/configuration-reference.md` and operator guidance are updated.
- [x] Focused tests pass.
- [x] Full repository suite passes.
- [x] Correctness, QA/code, and security reviews have no unresolved medium/high findings.
- [x] Exact candidate commit is deployed only to Forest.
- [x] Forest containers agree on candidate revision and effective environment.
- [x] Cross-container probe observes queued state and `2 <= peak_active <= test_limit`.
- [x] Actual GridMET client request acquires/releases admission and leaves no state.
- [x] Forest rollback is rehearsed or directly demonstrated without DB flush.
- [x] No batch or Kubernetes deployment occurred.

## Required Evidence Artifacts

- `artifacts/2026-09-07_contract_decision.md`
- `artifacts/2026-09-07_correctness_review.md`
- `artifacts/2026-09-07_code_qa_review.md`
- `artifacts/2026-09-07_security_review.md`
- `artifacts/2026-09-07_validation.md`
- `artifacts/2026-09-07_forest_integration.md`

Dates may advance if execution continues on a later UTC day. Record exact
commands, candidate SHA, container identities, sanitized Redis snapshots,
observed peak, queue observation, cleanup state, and rollback result.

## Handoff

Package complete. Forest remains enabled with the ratified seven values and
runtime candidate above; closeout commits contain documentation/evidence only.
The durable rules live in [the canonical contract](../../schemas/gridmet-redis-admission-contract.md)
and [ADR-0050](../../adrs/ADR-0050-gridmet-redis-admission.md).
The operator's subsequent registry build, openwepp.org deployment, and batch
validation are outside this package and have not been performed.
