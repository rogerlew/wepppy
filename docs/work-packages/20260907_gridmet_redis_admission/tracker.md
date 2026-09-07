# Tracker - GridMET Redis Admission and Queue Visibility

## Quick Status

**Timezone**: UTC
**Started**: 2026-09-07 15:53 UTC
**Current phase**: Contract checkpoint drafting and two independent reviews
**Last updated**: 2026-09-07 15:53 UTC
**Security impact**: `high`; independent review required
**Live authorization**: `forest` development stack only
**Later batch validation**: explicitly deferred to the post-package
`openwepp.org` deployment

## Task Board

### Ready / Backlog

- [ ] Execute the active ExecPlan contract-first from repository `master`.
- [ ] Add the GridMET admission contract and parameterization ADR.
- [ ] Implement FIFO queue state, expiring leases, configuration, diagnostics,
  and explicit error taxonomy in a separate admission module.
- [ ] Integrate every GridMET client and indirect runtime caller while
  preserving default-off behavior.
- [ ] Add unit, real-Redis, multiprocessing, and client-wiring tests.
- [ ] Add Compose propagation, configuration reference, operational runbook,
  and reusable Forest probe.
- [ ] Complete focused and full local/container validation.
- [ ] Complete independent correctness, QA/code, and security reviews.
- [ ] Commit and push the reviewed candidate before Forest deployment.
- [ ] Deploy the exact candidate and environment values to `forest`, recreate
  only affected services, and verify revision/config parity.
- [ ] Run the cross-container concurrency probe and one admitted public GridMET
  acquisition on Forest; save evidence and prove cleanup.
- [ ] Close the package without running a batch or deploying Kubernetes.

### In Progress

Contract and ADR drafting, with independent correctness and security reviews.
Preflight verified Forest, clean master at
`583e6870c639999515035423f133e5925dae2da5`, the installed development wctl
preset, and healthy standalone Redis 8.6.2. Baseline focused validation passed:
54 tests across download clients and climate build helpers.

### Blocked

None known. Forest access and Redis availability must be verified before the
live milestone; failure there is evidence to record, not permission to switch
targets.

### Done

- [x] Assessed the present GridMET acquisition paths and confirmed that the
  multiple-interpolated limit is process-local (2026-09-07 15:53 UTC).
- [x] Ratified Redis coordination, queue-state visibility, and opt-in
  construction with Roger Lew (2026-09-07 15:53 UTC).
- [x] Scaffolded package, tracker, active ExecPlan, deployment boundary, and
  Forest integration acceptance (2026-09-07 15:53 UTC).

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
| Pod/process death leaks capacity | High | Medium | Expiring ownership leases and renewal tests | Open |
| Dead waiter blocks FIFO queue | High | Medium | Queue-ticket TTL, heartbeat, and pruning | Open |
| Retry amplification retains permits | High | Medium | Per-attempt permit and release before backoff | Open |
| Redis outage removes protection | High | Low | Enabled mode fails closed with explicit error | Open |
| Process pool pickles unsafe client state | High | Medium | Pass immutable config; connect lazily in child | Open |
| Long stream outlives lease | High | Medium | Ownership-safe renewal during streaming | Open |
| Queue position misrepresented as ETA | Medium | Medium | Contract and logs expose state without ETA | Open |
| Live probe pollutes operational keys | Medium | Low | Unique namespaced key, final emptiness proof, targeted cleanup | Open |
| Forest-only success overclaimed | High | Medium | Explicit Kubernetes/batch exclusion in every closeout artifact | Open |

## Verification Checklist

- [ ] Default-off path proves zero Redis construction/I/O.
- [ ] Configuration rejects invalid boolean, numeric, and timing relationships.
- [ ] Atomic scripts use Redis time and ownership tokens.
- [ ] FIFO, limit, renewal, release, cancellation, and expiry tests pass.
- [ ] Retry sleeps occur with no active permit.
- [ ] Public point and gridded clients are wired.
- [ ] PRISM, Daymet, SNOTEL/supplement, monthly precipitation, observed GridMET,
  and multiple-interpolated callers propagate opt-in configuration.
- [ ] `ProcessPoolExecutor` path uses serializable configuration only.
- [ ] `docker/docker-compose.dev.yml` renders with default-off and enabled values.
- [ ] `docs/configuration-reference.md` and operator guidance are updated.
- [ ] Focused tests pass.
- [ ] Full repository suite passes.
- [ ] Correctness, QA/code, and security reviews have no unresolved medium/high findings.
- [ ] Exact candidate commit is deployed only to Forest.
- [ ] Forest containers agree on candidate revision and effective environment.
- [ ] Cross-container probe observes queued state and `2 <= peak_active <= test_limit`.
- [ ] Actual GridMET client request acquires/releases admission and leaves no state.
- [ ] Forest rollback is rehearsed or directly demonstrated without DB flush.
- [ ] No batch or Kubernetes deployment occurred.

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

Execute
`prompts/active/gridmet_redis_admission_execplan.md` end-to-end. The executor is
authorized to update Forest's gitignored `docker/.env`, recreate affected
services in `docker/docker-compose.dev.yml`, and run the bounded integration
probes after the candidate is committed and pushed. This authority does not
extend to another Compose topology, a batch, `forest1`, `wepp.cloud`, registry
publication, or Kubernetes/openwepp.org.
