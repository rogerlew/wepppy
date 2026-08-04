# Tracker - Fork/Archive Serial Queue Isolation

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-04 05:38 UTC
**Current phase**: live rollout pending after local implementation validation
**Last updated**: 2026-08-04 08:03 UTC
**Next milestone**: Execute Forest cutover/rollback and guarded wepp3 canary
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260803_fork_archive_serial_queue/artifacts/2026-08-04_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Obtain two independent read-only checkpoint reviews, disposition every
  finding, and commit the accepted checkpoint as a standalone ancestor.
- [ ] Add the single worker service to dev and Forest; add a dedicated,
  dependency-minimal wepp3 compose while preserving the
  repurposed HPC and wepp1/wepp2 non-consumer boundaries.
- [ ] Route fork, archive-create, and restore to `fork-archive`; regenerate the
  RQ graph/catalog.
- [ ] Update default operator queue listings and tests.
- [ ] Add exact queue-wait and execution-time-state guidance to both consoles.
- [ ] Characterize queued fork destination visibility and queued restore
  mutation drift; implement only the ratified bounded safety changes.
- [ ] Validate locally, then execute Forest drain/cutover/serialization/rollback
  acceptance.
- [ ] Complete security/correctness reviews and a drain-first wepp3 canary.

### In Progress

- [x] Independent governance and operations/security checkpoint reviews passed
  after disposition and post-fix confirmation.
- [x] Independent correctness re-review passed with no remaining major
  correctness, authorization, locking, or contract findings.
- [x] Independent operations/security re-review approved the repository
  implementation with all High/Medium findings closed and no release-blocking
  Low findings. Live rollout remains separately gated on host evidence.

### Blocked

- [ ] Production implementation is blocked until the exact matrix is
  registered, explicitly approved, independently reviewed, and committed as a
  standalone ancestor.

### Done

- [x] Implemented named queue routing, one-process dev/Forest workers, dedicated
  minimal wepp3 compose, operator queue visibility/service selection, exact UI
  guidance, restore lock recheck, and queue-specific cancellation authority.
- [x] Regenerated the RQ graph/catalog; focused Python passed 227 tests, graph
  tooling passed 18, wctl passed 8, and frontend lint plus 105 suites/756 tests
  passed. Compose renders, stub checks, broad-exception enforcement, and docs
  lint passed.
- [x] Closed implementation-review findings: atomic queued-only user
  cancellation, restored legacy cancellation regressions, truthy restore-lock
  filtering, wepp1 scale-zero containment, installable wepp3 wctl preset,
  Forest/wepp3 rollout commands, and untruncated queue visibility.
- [x] Full repository Python sweep passed 5,828 tests with 61 skips; the final
  focused set passed 53 tests, stubtest passed, six Compose paths rendered,
  graph drift/broad-exception checks passed, and affected docs linted cleanly.
- [x] Committed the accepted checkpoint as standalone ancestor
  `bc996d336` before implementation edits. (2026-08-04 PDT)
- [x] Read the NFS benchmark/incident note and isolated the archive D-state and
  loaded full-output fork evidence. (2026-08-04 05:38 UTC)
- [x] Mapped current fork/archive/restore enqueue sites, worker pools, supported
  compose variants, UI surfaces, RQ observability, graph artifacts, and tests.
  (2026-08-04 05:38 UTC)
- [x] Identified the restore dispatch-safety, fork destination, legacy-queue
  rollout, worker-only topology, and operator visibility gaps. (2026-08-04
  05:38 UTC)
- [x] Scaffolded the package, tracker, active ExecPlan, contract draft,
  security-review placeholder, infrastructure cross-reference, and project
  tracker entry. (2026-08-04 05:38 UTC)
- [x] Passed Markdown lint, spelling preview, whitespace validation, and
  baseline compose renders for all five deployment paths. The worker-only
  render used its required non-secret `RQ_REDIS_URL` placeholder. (2026-08-04
  05:50 UTC)
- [x] Recorded wepp3 production isolation across the package, contract draft,
  ExecPlan, security checklist, infrastructure map, Docker operator docs, and
  project tracker; documentation validation passed. (2026-08-04 06:13 UTC)
- [x] Registered SURF-03A/GOV-00A-M1G, amended
  SURF-03/SURF-04/SURF-07/SURF-17,
  recorded starting revision `d63df477c887d59e813542a1c2f22730a7f75faa`,
  and obtained explicit approval of the complete final matrix. The operator
  later superseded its cancellation clause: existing buttons remain;
  authorized project users may cancel queued `fork-archive` jobs; only
  Admin/Root may cancel after start.
  (2026-08-04 PDT)

## Timeline

- **2026-08-04 05:38 UTC** - Package created from the August 2 archive-worker
  NFS stall and August 3 loaded full-output fork evidence; no production code or
  compose file changed.
- **2026-08-04 05:50 UTC** - Documentation and baseline compose validation
  passed; implementation remains gated on the exact contract checkpoint.
- **2026-08-04 06:13 UTC** - Replaced the wepp1 placement proposal with a
  dedicated, dependency-minimal wepp3 production consumer and revalidated docs.
- **2026-08-04 PDT** - Operator explicitly approved the complete final matrix,
  then superseded its cancellation clause with queue-specific queued-user and
  started-Admin/Root authorization and directed Codex to proceed.

## Decisions Log

### 2026-08-04 05:38 UTC: Propose one queue for three top-level filesystem jobs

**Context**: Fork, archive creation, and archive restore all traverse or rewrite
the NAS-backed run tree. Delete removes one archive file synchronously, while an
undisturbifying fork may later launch ordinary WEPP work.

**Options considered**:

1. Serialize only fork and archive creation, leaving restore concurrent.
2. Serialize fork, archive creation, and restore on one queue.
3. Move every downstream fork child and archive delete operation to the new queue.

**Decision**: Propose option 2: queue `fork_rq`, `archive_rq`, and
`restore_archive_rq` on `fork-archive`. Preserve synchronous delete and existing
downstream WEPP queue topology.

**Impact**: The queue contains the known NAS-intensive top-level operations
without turning it into a general model queue. Exact approval remains pending.

### 2026-08-04 05:38 UTC: Initial wepp1 placement proposal (superseded)

**Context**: The August 3 fork ran on wepp2 because both hosts consumed the
default queue. A one-process service on both hosts would still permit two
concurrent NAS-intensive jobs.

**Decision**: Initially proposed one `fork-archive` consumer in the wepp1
primary stack and no consumer in the worker-only compose.

**Impact**: Superseded by the 2026-08-04 06:09 UTC wepp3 placement decision.

### 2026-08-04 05:38 UTC: Treat queue visibility and deployment order as part of the feature

**Context**: Current default operator lists know only `default` and `batch`, and
jobs already on `default` are not migrated when an enqueue site changes queue.

**Decision**: Include `fork-archive` in all default RQ summaries/Admin listings
and require a drain-first two-stage rollout. On rollback, keep the dedicated
worker alive until its existing jobs are terminal.

**Impact**: Operators can see waiting work, and deploy/rollback cannot silently
strand or overlap legacy and new jobs.

### 2026-08-04 05:38 UTC: Require safety characterization before queue cutover

**Context**: The fork route registers an empty destination before enqueue; a
long queue extends the incomplete-destination window. Restore checks NoDb locks
at request time but its worker currently does not repeat that check immediately
before deleting the current run tree.

**Decision**: Make both behaviors explicit contract-checkpoint questions.
Propose retaining execution-time fork semantics with clear UI guidance and
requiring restore dispatch-time lock revalidation before destructive removal.

**Impact**: The queue change cannot rely on the prior near-immediate-dispatch
assumption. Stronger revision conflict detection, if needed, requires explicit
scope approval.

### 2026-08-04 05:57 UTC: Exclude the repurposed HPC compose

**Context**: The operator confirmed that the HPC configuration is being
repurposed and does not need the fork/archive worker.

**Decision**: Remove HPC from the implementation and acceptance matrix. Treat
`docker/docker-compose.dev.hpc.yml` as an explicit non-consumer alongside the
worker-only wepp2 stack.

**Impact**: The package changes only development, Forest test production, and
production worker compose. Documentation must not present the HPC selector as
a supported WEPPcloud deployment preset.

### 2026-08-04 06:09 UTC: Isolate the production consumer on wepp3

**Context**: D-state worker isolation is not needed on development forest or
Forest test production. Wepp3 has the production NFS mount and no other running
containers, so it provides a smaller production failure domain than wepp1.

**Decision**: Development and Forest retain one local consumer for behavioral
parity. Production runs the sole consumer on wepp3 from
`docker/docker-compose.prod.wepp3.yml`, which contains no normal workers,
`f-esri`, or `weppcloudr`. Wepp1 and wepp2 remain non-consumers; there is no
automatic failover.

**Impact**: An NFS-blocked serial worker can be signaled, remounted, or the host
can be fenced without disrupting wepp1 application services. Wepp3 requires an
explicit Redis, secret, image, mount, permissions, and out-of-band reset
preflight before deployment.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Old default-queue job overlaps a new dedicated job during rollout. | High | Medium | Inventory/drain in-scope default jobs before route cutover; stage worker first. | Open |
| Dedicated queue has jobs but no registered worker. | High | Medium | Include queue in all operator summaries; validate exactly one wepp3 worker. | Open |
| A normal wepp2 worker deployment starts the service. | High | Low | Keep the service out of wepp2 compose; structural test plus live host mapping proves non-consumption. | Open |
| Worker enters uninterruptible NFS D state and blocks the entire serial queue. | High | Medium | Preserve D-state triage; do not add a second worker reflexively; recover NAS first. | Open |
| Queued restore starts after conflicting project mutation. | High | Medium | Ratify dispatch-time revalidation and characterize need for revision conflict detection. | Open |
| Queued fork destination appears incomplete in another UI. | Medium | High | Characterize Runs catalog/direct URL; preserve readiness-gated console link; document outcome. | Open |
| Users interpret a long queued state as failure and resubmit. | Medium | Medium | Static and live-status guidance; retain existing single-job guards and tracking. | Open |
| Rollback strands or overlaps `fork-archive` jobs. | High | Low | Fence admission, drain registries, fence any D-state host, then revert routing and remove the service. | Open |
| Updating default queue lists misses wctl registry-repair internals. | Medium | Medium | Test command text, job summaries, API listings, and RQ info details together. | Open |

## Hardening Signal Log

- **Baseline health signals**: concurrent/default-queue fork/archive work can
  run on either wepp1 or wepp2; loaded production benchmark was 1.70x longer
  overall for create/delete/rewrite phases than the historical NAS baseline.
- **Post-change health signals**: at most one in-scope started job, no new
  in-scope default-queue enqueue, one registered wepp3 consumer, ordinary queues
  continue dispatching, and users can distinguish queued from started.
- **Danger signals observed**: none post-change; implementation not started.
- **Temporary callus register**: one-worker serialization, owner WEPPcloud
  operations, proposed 2026-08-04 UTC, review after the 14-day production
  observation window.
- **Softening experiments**: none authorized. A future concurrency experiment
  requires representative NAS measurements and a separate reviewed topology
  decision.

## Verification Checklist

### Code Quality

- [x] Focused microservice, Docker, wctl, listing, route-render, and client tests pass.
- [x] `wctl run-pytest tests --maxfail=1` passes.
- [x] `wctl run-npm lint` and `wctl run-npm test` pass.
- [x] `wctl check-test-stubs` and changed broad-exception enforcement pass.
- [x] `wctl check-rq-graph` passes after graph regeneration.

### Security

- [x] Security impact triage recorded as `high`.
- [x] Accepted checkpoint ancestor exists before production edits.
- [x] Dedicated security review has no unresolved medium/high finding.
- [x] Queue, worker placement, filesystem, restore, cancellation, deploy, and
  rollback surfaces are explicitly reviewed.

### Documentation

- [ ] SURF-03, SURF-04, SURF-07, SURF-17, and GOV-00A register/checkpoint docs are current.
- [x] `docker/README.md`, `wctl/README.md`, and NFS/operator guidance are current.
- [x] RQ dependency catalog/static graph are current.
- [x] Package, tracker, ExecPlan, and security review are current; live rollout
  evidence remains pending.
- [x] No parameterization ADR is required for the scoped queue topology.

### Testing and Deployment

- [x] Compose config validates for dev, Forest, prod+wepp1 non-consumption, and
  the dedicated wepp3 service.
- [x] The repurposed HPC compose proves no `fork-archive` consumer.
- [x] Wepp2 compose excludes `fork-archive`; wepp3 compose starts exactly that
  one container.
- [ ] Local two-job serialization acceptance passes.
- [ ] Forest drain-first cutover, normal dispatch, queued wait, cancellation,
  rollback, and worker placement pass.
- [ ] Wepp3 preflight confirms Redis, secrets, image, mount, permissions,
  fencing, and no legacy overlap before cutover.
- [ ] Wepp3 canary and 14-day observation evidence are recorded.

## Progress Notes

### 2026-08-04 05:38 UTC: Discovery and scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Read all applicable repository, documentation, work-package, Docker, RQ,
  rq-engine, WEPPcloud, testing, and wctl guidance.
- Traced the three enqueue sites and the default/batch worker topology across
  supported compose variants.
- Traced console templates, queue-aware job listings, graph/catalog artifacts,
  and targeted tests.
- Recorded omitted compatibility, safety, observability, and rollout concerns.

**Blockers encountered**:

- The exact bounded enhancement has not yet been registered or approved. This
  is an expected contract-first gate, not an implementation blocker to bypass.

**Next steps**:

- Finalize the proposed matrix, register GOV-00A-M1G/SURF-03A, obtain explicit
  operator approval and two independent checkpoint reviews, then commit the
  checkpoint as a standalone ancestor.

**Test results**: all seven new/touched Markdown paths passed `wctl doc-lint`;
`git diff --check` passed; `uk2us` preview found no differences in the new or
touched prose; dev, Forest, wepp1 layered, repurposed HPC, and worker-only
compose renders passed. The worker-only render was supplied its required
placeholder `RQ_REDIS_URL`.

## Watch List

- **Restore drift**: request-time confirmation and lock checks may be stale by
  dispatch after a long queue wait.
- **Fork destination visibility**: SQL/run-directory registration precedes copy
  and may expose an incomplete destination outside the readiness-gated console.
- **D-state containment**: one worker limits NAS concurrency but also makes one
  blocked NFS RPC a queue-wide head-of-line stall.
- **Remote worker topology**: wepp3 is the sole production consumer; accidental
  activation on wepp1 or wepp2 violates the contract.

## Communication Log

### 2026-08-04 05:38 UTC: Initial operator direction

**Participants**: Roger Lew, Codex
**Question/Topic**: Implement a single fork/archive worker queue across dev,
Forest test production, and wepp1; warn users that jobs may wait before dispatch.
**Outcome**: Work package scaffolded. Exact restore inclusion, worker placement,
UI wording, safety revalidation, and rollback remain subject to the formal
contract checkpoint.

### 2026-08-04 05:57 UTC: HPC scope correction

**Participants**: Roger Lew, Codex
**Question/Topic**: Whether the HPC development compose needs the dedicated
worker.
**Outcome**: No. HPC is being repurposed and is excluded from implementation;
its documentation and non-consumer status must remain explicit.

### 2026-08-04 06:09 UTC: Production failure-domain placement

**Participants**: Roger Lew, Codex
**Question/Topic**: Whether the production serial worker should run on wepp1.
**Outcome**: Place it on otherwise-idle wepp3, which already has the production
NFS mount. Dev forest and Forest test production retain local workers for
behavioral parity, not D-state containment.
