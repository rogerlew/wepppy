# GridMET persistent queue recovery correctness review

## Metadata

- Reviewer: independent `correctness_review` agent, 2026-09-10 UTC.
- Context: WEPPpy `master`, base `d32a3981c`; implementation worktree under active revision.
- Scope: `wepppy/climates/gridmet/admission.py`, `acquisition.py`, `client.py`, and admission/controller/client/real-Redis tests.
- Authority: [GridMET admission contract](../../../schemas/gridmet-redis-admission-contract.md), especially State transitions and ownership, Permit lifecycle, errors, and recovery, and Safety guarantee and limits; [active ExecPlan](../prompts/completed/gridmet_queue_recovery_execplan.md).
- Review policy: [hardening lifecycle](../../../standards/hardening-lifecycle-standard.md). The separate [QA/security review](20260909_security_review.md) covers security triage and terminal error classes. Final validation evidence is recorded below and in [incident and validation](incident-and-validation.md).

## User outcome and error policy

A live GridMET request must remain in FIFO beyond the former queue-age limit and recover from transient Redis transport failures without duplicate occupancy. A completed HTTP response must survive an uncertain release reply. No HTTP may start or continue on unconfirmed, expired, or released local authority.

Legacy positive wait settings remain accepted and fingerprint-compatible but do not expire waiting. Disabled admission remains a valid no-Redis path. Authentication/authorization, configuration conflict, malformed state, and foreign ownership are terminal errors. Transport failures retry with the same ownership token; acquisition cancellation attempts bounded owned cleanup. A primary exception or lost lease must not be trapped behind indefinite cleanup recovery.

## State matrix

| State | Valid? | Expected behavior | Evidence reviewed |
| --- | --- | --- | --- |
| Admission disabled/never used | Yes | No controller or Redis I/O; existing HTTP behavior | Disabled configuration/client fixtures |
| Namespace absent or idle | Yes | Initialize agreed policy and admit FIFO head if capacity exists | Real Redis ownership/FIFO scenarios |
| Populated queue with live waiters | Yes | Preserve sequence and heartbeat; no elapsed wait expiry | Persistent scenario, long-wait unit test, heartbeat scenario |
| Live holder and queued contenders | Yes | At most configured live permits; fill slots in FIFO order | Six-process contention and FIFO scenarios |
| Committed enqueue/poll reply lost | Recoverable | Replay same token; preserve live ordinal; confirm/refresh active lease before returning | Lost-reply and real socket-delay scenarios |
| Committed release reply lost | Recoverable | Revoke local authority before I/O; replay cleanup without resurrection | Independent disposable-Redis release probe; release regression |
| Active lease expired | No further authority | Reject late renewal and prevent use/publication | Expiry/delayed-reply fixtures and killed-owner reclamation |
| Concurrent manual/background renewal | Yes | Serialize confirmation so an older reply cannot poison newer authority | COR-03 fixed; independent real-Redis serialization probe |
| Caller canceled or primary failure pending | Expected termination | Bounded owned cleanup, then propagate original failure | KeyboardInterrupt/SystemExit/upstream-error fixtures |
| Foreign token, malformed state, conflicting policy | Invalid | Explicit terminal error; no foreign mutation or transport retry | Ownership, corruption, policy and error-classification fixtures |

Input combinations are separate from these states: operation kind (enqueue/poll/renew/release/cancel), reply before/after commit, delay below/above the last confirmed lease bound, foreground/background thread ordering, HTTP success/error/cancellation, and enabled/disabled configuration. The tests do not constitute an exhaustive cross-product.

## Findings

| ID | Severity | Description | Required action | Status |
| --- | --- | --- | --- | --- |
| COR-01 | Medium | Initial `GridMetPermit.release()` set `_closed` only after transport recovery. A committed-but-lost release reply left `check()` locally valid even after Redis removed the permit. Concurrent use could proceed without live ownership. | Revoke local authority before release I/O; separately track cleanup completion so retry remains possible. | Resolved: `_closed`/`_released` split; unit regression and independent real-Redis recheck passed |
| COR-02 | Medium | Initial exception/invalid-entry cleanup called unbounded release recovery. Redis outage could indefinitely delay KeyboardInterrupt, SystemExit, or an already-known primary error. | Use bounded cleanup when terminating due to cancellation/error; include a renewal failure discovered during release's join in this decision. | Resolved: exceptional/invalid-entry cleanup is bounded; release rechecks failure after join and exit preserves that failure over cleanup errors; expanded four-case test passed independently |
| COR-03 | Medium | `_retry_transition(... valid_until=self._valid_until)` captures an old authority bound. When another renewal confirms a newer lease while the first reply is delayed, the older call rejects the obsolete bound and records a terminal shared failure. | Serialize background/manual renewals or reconcile reply generation against current confirmed authority; stale calls must neither shorten nor invalidate a newer confirmed lease. Add the exact concurrent regression. | Resolved: dedicated renewal lock serializes confirmation; direct real-Redis recheck and manual/background regression passed independently |

### Independent evidence

1. `wctl run-pytest tests/climates/gridmet/test_admission.py tests/climates/gridmet/test_admission_clients.py -q`: **88 passed**, two dependency deprecation warnings, 10.04 seconds at the first corrected checkpoint. This covered the release/cancellation fixes but did not construct COR-03.
2. A fresh `wctl run-python -` process used a unique `wepppy:gridmet:review:<uuid>` namespace on the dedicated `gridmet-recovery-test-20260909` Redis. The real Lua release committed; its response was then replaced with a synthetic timeout, and a barrier held the replay. An independent snapshot reported active **0**, while `permit.check()` correctly rejected authority. Replay completed and final active count stayed **0**. No shared Redis was paused or flushed.
3. A second unique-namespace probe used real Redis, a real **22-second** lease and actual monotonic time. Automatic renewal was disabled only in the isolated probe so the original bound could approach expiry. Near that bound, renewal A committed but its reply was held; concurrent renewal B returned successfully and confirmed another **22 seconds** of local authority. A's reply then arrived just after the original bound. A raised `GridMetAdmissionLostLease` and poisoned `permit.check()`, even though Redis active count was **1** and B's confirmed bound still had **21.65 seconds** remaining. Owned cleanup restored active count **0**. This directly confirms COR-03 without changing clocks or fabricating Redis grant state.
4. After adding the renewal lock, a third independent real-Redis probe held the first committed renewal reply and launched a second renewal. The second EVAL did not enter while the first remained unconfirmed. Releasing the reply barrier allowed both renewals to complete; `check()` remained valid, active count was **1**, and owned release returned occupancy to **0**. This proves the conflicting confirmation ordering in COR-03 is no longer reachable through the permit methods.
5. Final independent `wctl run-pytest tests/climates/gridmet/test_admission.py tests/climates/gridmet/test_admission_clients.py -q`: **91 passed**, two dependency deprecation warnings, 9.88 seconds. This includes cancellation/error cleanup, the manual/background serialization regression, and all four in-flight renewal-failure/release-timeout combinations.
6. Reviewed package-owner `/tmp/gridmet-real-final.txt`: **14 passed**, two warnings, 192.53 seconds, covering real ownership/FIFO/processes/persistence/lost replies/expiry/heartbeat and socket timeouts. These use the explicitly disposable service. Final `/tmp/gridmet-real-recheck.txt` records **4 passed**, ten deselected, 54.63 seconds for ownership/lost-reply/clocks/heartbeat after the review corrections. The consolidated record reports the final four actual socket-delay cases also passed in 46.18 seconds. No production activation is claimed from these local checks.
7. Final focused log `/tmp/gridmet-focused-final3.txt`: **145 passed, 14 opt-in Redis tests skipped**, three warnings, 9.67 seconds. Those Redis cases have separate real-service evidence above; a skipped focused test is not being counted as a runtime pass.
8. Final broad log `/tmp/gridmet-full-final.txt`: **8192 passed, 77 skipped, 3109 warnings in 852.04 seconds**, successful completion. The reviewer inspected the final log summary; this closes the required broad-suite gate without claiming coverage of the skipped states.
9. API check `/tmp/gridmet-stubtest-final3.txt`: **Success: no issues found in 1 module** for `wepppy.climates.gridmet.admission`. The final follow-up adds `typing`, annotations for environment configuration/wait bookkeeping, and `Literal[False]` for context exit; source inspection found no behavior change from the reviewed implementation.
10. Public client/observer logs `/tmp/gridmet-public-observed.txt` and `/tmp/gridmet-public-observer.txt`: the public client in rq-worker container `6a5a81f81002` returned **366 validated daily rows** for 2020. A separate rq-worker-batch container `6c90246e0aec` observed the same unique test namespace over **595 samples**, peak active **1**, no limit violations, and final queued/active **0**. This establishes a successful external GridMET acquisition under the revised local worker path; it is distinct from the loopback release-fault fixture and does not imply production rollout.

The lost-reply hooks alter response delivery after actual Lua execution; they do not replace the ownership transition being tested. Separate package tests use actual socket timeouts against explicitly disposable Redis. The reviewer did not pause Redis or rerun the production incident.

## Boundary and concurrency observations

Same-token enqueue replay refreshes existing live state without allocating a new ordinal. Poll replay confirms an already active owner and renews server expiry. Expired tickets are pruned before replay, so prolonged outages rejoin FIFO at the tail instead of preserving a dead place. The existing script's structural/policy/foreign-token guards remain in front of grants, and occupancy is still derived from the active set rather than a counter.

Normal successful response release may recover indefinitely because no HTTP remains open and local authority has been revoked. Exceptional cleanup must be bounded. After a primary error or cancellation, one failed cleanup leaves only an owned entry subject to its existing lease/heartbeat expiry; no counter decrement or global cleanup is introduced.

Release stops and joins background renewal before removing the Redis entry. The revised local revocation precedes release I/O, while a separate completion flag allows failed cleanup to be retried. A dedicated renewal lock prevents overlapping manual/background confirmations. Release now checks the shared failure after joining; a failure discovered there selects bounded cleanup. Exit also refreshes that failure before deciding error precedence, so a subsequent cleanup timeout cannot replace the actual renewal failure.

## Review checks and limits

- [x] Canonical user intent is separate from implementation/tests.
- [x] Optional absence, empty/populated state, supported legacy configuration, stale state and invalid state are distinguished.
- [x] Direct unmocked Redis ownership transitions were exercised.
- [x] Release noninterference is checked in both valid and canceled/error states.
- [x] The confirmed concurrent renewal/release races are resolved and independently rechecked.
- [x] Final focused/real-boundary/broad-suite results and independent QA disposition are recorded.
- [x] No hard upstream socket-fencing claim is made; cooperative checks and Redis occupancy remain distinct guarantees.

Residual limits include arbitrary process suspension, DNS/transport blocking outside socket inactivity bounds, and hostile corruption coverage beyond the explicit fixtures. A loopback HTTP fixture can prove the real requests/client/close/release path without proving production activation or external GridMET availability. Production rollout is outside this local review and must satisfy the existing deployment workflow gate.

## Verdict

- Code correctness gate: **pass**, all three medium findings resolved.
- Unresolved findings: High **0**, Medium **0**, Low **0**.
- Package correctness evidence gate: **pass**, final focused, real-boundary, public-client, API and broad-suite evidence inspected. No production activation is implied.
- Release recommendation: **ship** the reviewed local correction and record the authorized commit/push receipts. Production deployment remains held separately pending operator clarification.
- Sign-off: independent correctness reviewer, 2026-09-10 UTC; code corrections, actual permit/client fixtures, independent Redis ownership/renewal probes and final package validation verified within the stated limits.
