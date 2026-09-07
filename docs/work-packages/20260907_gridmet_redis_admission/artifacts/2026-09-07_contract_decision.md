# GridMET Redis admission contract checkpoint

Date: 2026-09-07, 16:22 UTC. Status: accepted for implementation; runtime
conformance and Forest acceptance pending.

## Authority and classification

- Starting implementation revision: `583e6870c639999515035423f133e5925dae2da5`
  on `master`.
- Operator approval: Roger Lew instructed `execute
  docs/work-packages/20260907_gridmet_redis_admission/prompts/active/gridmet_redis_admission_execplan.md`
  in this task session on 2026-09-07. The invoked plan explicitly authorizes the
  finite implementation, checkpoint/candidate commits and push to `master`,
  Forest development Compose deployment, and isolated acceptance probes.
- Classification: intended optional acquisition behavior change, requiring a
  standalone pre-implementation contract ancestor. This is not a conformance
  fix or an urgent exception to contract-first sequencing.
- Boundaries: GridMET clients, their climate orchestration callers, existing
  Redis connection helpers, development Compose, and bounded diagnostic probes.
  No batch, registry publication, Kubernetes, other host deployment, RQ topology,
  NoDb persistence changes, or climate data-schema mutation is authorized here.
- Implementation remained unchanged during these contract reviews. At review
  close, changed and new files were documentation only. The primary executor
  records the checkpoint commit SHA in the tracker before runtime edits.

## Applicable canonical authority

- [GridMET Redis admission contract](../../../schemas/gridmet-redis-admission-contract.md):
  all sections, particularly public configuration, ownership, permit lifecycle,
  safety limits, and acceptance.
- [ADR-0050](../../../adrs/ADR-0050-gridmet-redis-admission.md): initial values,
  decision provenance, alternatives, tuning ownership, and rollback.
- [ADR-0028](../../../adrs/ADR-0028-gridmet-download-retry-concurrency.md): existing
  HTTP retry, timeout, payload validation, byte ceilings, redirect refusal, and
  local grid concurrency obligations remain in force.
- [Contract-first standard](../../../standards/contract-first-change-standard.md):
  required checkpoint, valid-state review, two independent reviews, and ancestor
  sequencing.
- [Parameterization ADR standard](../../../standards/parameterization-adr-standard.md):
  explicit parameter delta, rationale, owner, evidence, and rollback.

## Normative delta and compatibility

The prior local grid pool remains four workers per build. Enabled orchestration
adds one shared FIFO Redis pool for every point/grid HTTP attempt, with limit
4, a 900-second admission scheduling deadline across retries, 300-second renewed
leases, 60-second waiting liveness, and 0.25-second jittered polling. Redis
connect/socket timeouts are two seconds, automatic retries are off, and renewals
run every `min(lease / 3, 5)` seconds. The contract and ADR define all timing
inequalities and the operational key `wepppy:gridmet:admission:v1`.

Literal or omitted public `admission=None` remains disabled regardless of the
environment. Only named orchestration boundaries resolve the environment once
per operation; intermediate public clients forward the immutable value and
child processes construct their own connections. Absent or explicit false
enable values perform no Redis construction or I/O. Invalid enabled policy,
Redis failure, incompatible shared policy, or lease loss cannot bypass admission.

Each attempt owns its ticket/token, takes its turn by Redis sequence, and holds
its permit through response close. Validation, conversion, publication, and
retry backoff run after release; retries join the tail with a new token and the
original scheduling deadline. Distinct admission errors subclass the existing
acquisition error and never enter upstream retry handling. Successful public
DataFrame/file results, HTTP bounds, and atomic publication remain compatible.

Rationale: aggregate control covers independent workers and point requests that
a per-build pool cannot coordinate. Explicit configuration preserves library
consumers. FIFO and expiring owned state provide fairness, diagnosis, and crash
recovery; policy fingerprinting prevents mixed worker limits. A live Redis
permit bound is explicit because GridMET cannot fence already-started remote
requests using an expired token.

Security impact is high: Redis ownership/expiry, worker concurrency, outbound
request admission, and deployment configuration cross process boundaries.
The design uses the existing connection/secret contract, server time, atomic
same-slot scripts, ownership checks, finite values, safe namespaces, bounded
commands, and sanitized errors. No new external dependency is introduced.

## Valid states and user-reachable failures

Input and stored-state coverage are separate dimensions; the matrix below is
the required regression scope, not a claim of completed runtime testing.

| Dimension | State | Required outcome |
| --- | --- | --- |
| Input | Public `None`; absent or false environment | Existing acquisition, zero admission Redis activity |
| Input | Valid enabled policy | Explicit immutable propagation and shared admission |
| Input | Empty/unknown enable text; invalid numbers/key/timings | Configuration error before Redis or HTTP |
| Redis | Namespace absent or present-empty | Atomic initialization and normal admission |
| Redis | Populated queue/live holders | FIFO, bounded live occupancy, visible position/counts |
| Redis | Stale waiter/expired holder | Prune stale entry; no resurrection; resumed waiter obtains a fresh ticket |
| Redis | Canceled or timed out waiter | Ownership-safe cleanup and explicit bounded failure |
| Redis | Foreign token or conflicting policy | Reject operation without altering another owner's live state |
| Redis | Corrupt types/state or unavailable/ambiguous command | Sanitized explicit failure, no admission bypass |
| Lifecycle | Paused owner or delayed Redis reply beyond freshness | Independent monotonic check rejects stale ownership before new HTTP |
| Compatibility | Existing disabled deployment; no prior namespace | Supported unchanged path; no legacy Redis state migration required |

Configuration faults, Redis outages/corruption, policy conflict, and lease loss
are exceptional and surface distinct acquisition subclasses. Waiting exhaustion
is an expected bounded pressure outcome and surfaces an admission timeout.
Ordinary upstream/payload failures retain ADR-0028 retry behavior. Cleanup
preserves the primary error, closes the response, and attempts only owned state;
unavailable Redis leaves expiring state for later reclamation. These outcomes
are authorized by the contract's state-transition and permit-lifecycle sections.

## Independent reviews and disposition

Both reviewers independently read the contract/ADR and current clients. Neither
authored those canonical amendments or changed runtime code. Review findings
were sent to the author and rechecked after correction.

| ID | Severity | Finding | Resolution and post-fix confirmation |
| --- | --- | --- | --- |
| C1 | Medium | Present-empty enable text silently disabled admission despite the malformed-boolean requirement | Configuration section now rejects empty/whitespace; both reviewers confirmed |
| C2 / SEC-C01 | Medium | Heartbeat error state alone could let a resumed foreground use an expired lease before its renewal thread ran | Permit lifecycle requires independent pre-command monotonic expiry and rejects delayed replies; acceptance requires both regressions; both reviewers confirmed |
| C3 | Medium | Exception wording could remove the existing acquisition base-class contract | Permit lifecycle explicitly requires distinct acquisition subclasses and excludes upstream retry; both reviewers confirmed |

- Correctness reviewer: Codex `/root/review_contract`, PASS at 2026-09-07
  16:22 UTC; zero unresolved high or medium findings.
- Independent security contract reviewer: Codex `/root/contract_security`, PASS
  at 2026-09-07 16:22:07 UTC; zero unresolved high or medium findings. Its
  read-only signoff also checked finite values, corruption handling, policy
  fingerprinting, hash-slot safety, explicit configured-operational-key probe
  refusal, and scope authority.
- Gate: accepted for the standalone documentation checkpoint commit. This
  approval does not approve an untested implementation or assert deployment.

## Required evidence and residual risk

Implement deterministic configuration, lifecycle, FIFO, occupancy, ownership,
clock disagreement, cancellation, outage, timeout, killed-owner, and stale-reply
tests. Real Redis must exercise the atomic boundary across processes. Client
tests must prove disabled zero-I/O behavior, explicit indirect propagation,
pickle-safe pool arguments, release before validation/backoff, requeue on
retry, sanitized errors, and no successful publication after admission loss.
Run focused/full suites, applicable stub gates, Compose renders, docs lint,
and the independent correctness, QA/code, and dedicated runtime security gates.

Forest must run the exact pushed candidate and demonstrate a peak of two with
at least six contenders across two containers, visible queuing, FIFO, killed
waiter/holder reclamation, empty cleanup, a successful real public GridMET
request, and rollback evidence. Admission-only cleanup during upstream failure
does not satisfy the real-download criterion. No batch is submitted.

Residual risk: expiring Redis permits do not forcibly stop a remote request;
process suspension, DNS stalls, partitions, or trickling responses can delay
local cancellation. The contract explicitly limits its guarantee to live
permits and cooperative failure handling. Runtime implementation, real Redis
evidence, final reviews, and Forest acceptance remain pending at this checkpoint.
