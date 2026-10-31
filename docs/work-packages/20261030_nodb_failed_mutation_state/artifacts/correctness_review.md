# NFMS-01 independent correctness review

Reviewer: `/root/final_correctness`, 2026-10-31 UTC. Actual working implementation
and tests after checkpoint `2b998e08d`; read-only review. Reviewer edited no files
and did not personally execute tests. Primary retained this independent result.
Canonical authority: persistence NFMS-01, single-input publication/recovery,
preserved WAM/MRS and applicable postfire/climate contracts. Related reviews:
`security_review.md`, `qa_review.md`.

## Verdict and user outcome

APPROVE local code scope; no unresolved medium/high correctness findings.
Unchanged disk and lock release do not imply reverted memory. Acquired high-level
failures now restore authoritative state into held controller identity or prevent
reuse until safe recovery. Atomic commits and low-level retries remain distinct.
This does not certify a completed full suite, deployment or affected-run recovery;
final results and limits are retained separately in `validation.md`.

## Findings

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| C1 | High | Delayed hydration overwrites newly acquired owner's state | Install-time ownership recheck coordinated with acquisition; controlled race test; resolved |
| C2 | High | Previously hydrated state clears later quarantine | Install rejects currently failed instance; delayed-hydration/quarantine test; resolved |
| C3 | Medium | Migration fresh admission rejected stale valid state | Explicit owned fresh recovery; newer-generation admission tests; resolved |
| C4 | High | Proposed identity changes orphan original Redis token | Captured identity checked before dump lookup/clearing; original identity recovery/cleanup; resolved |
| C5 | Medium | Secondary cancellation swallowed or masked | Signals propagate with primary context; combined recovery/unlock tests; resolved |
| C6 | Medium | Recovery omitted equivalent legacy class rebinding | Same module/name normalization restored; resolved |
| C7 | High | Concurrent explicit recoveries replace/release another token | Exclusive recovery reservation, acquisition fence, captured cleanup token; expiry/overlap test; resolved |

Wrong-thread recovery, atomic state installation and quarantine assignment/deletion
fences were also reviewed. Failure-class dispositions are in `consumer_matrix.md`
and `remaining_boundary_audit.md`; shared context alone was not treated as closure.

## Valid states and error policy

| State / condition | Policy | Evidence |
| --- | --- | --- |
| First initialization absent | Preserve original failure; failed object fenced; fresh initialization works | Matrix first-create/fresh retry |
| Optional absent | Remains valid None; no invented file | Matrix optional absence |
| Present-empty / populated | Successful edits remain supported; acquired abort restores current durable data | Base/consumer/manual matrices |
| Supported legacy / detached / readonly | Preserve decode and read contracts; readonly writes still reject | Matrix compatibility and existing base suites |
| Corrupt/missing/unreadable recovery | Exceptional explicit unavailable state, original operation diagnosable | Matrix recovery fault and subsequent recovery |
| Busy or replaced owner | Expected contention; no mutation/release of other's state/token | Disposable Redis and controlled race tests |
| Postcommit failure | Exceptional partial success; keep committed authority, no shared rollback | Matrix metadata/notification/unlock/hook/intermediate cases |
| Cancellation | Propagate signal including cleanup-time signal, preserve primary context | Body and secondary cancellation cases |

Runtime unavailable-state errors derive from canonical NFMS and are not a new
HTTP error-envelope policy. Expected optional absence is not corruption.

## Artifact evidence chain

| Stage | Evidence / scope |
| --- | --- |
| Intent | Accepted 0.02 conductivity / 0.2 saturation, rejected 0.9 via valid application then storage/domain failure |
| Persisted state | Actual file reload and held singleton after abort/unrelated save |
| Prepared executable input | Actual prep_soil writes wepp/runs/p101.sol; WeppSoilUtil parses accepted values; actual phosphorus.txt/gwcoeff.txt parsed after failure/retry |
| Execution / report | N/A: requested outcome is generated-input preparation, no full model or production job required |

Tests exercise real serialization, atomic replace and hydration. Fault injection
names the failing boundary; preparation is not replaced by a mock. Resource test
preserves logger/listener/handler identities and bounded descriptors over twelve
failures. No arbitrary nested-alias repair or artifact rollback promise.

## Reported validation and performance

Reviewed reported passes: 139 base/Climate; 36 matrix with actual Redis/no skips;
71 WAM/MRS actual persistence and 164 transport; six real-consumer and 86 parser/
preparation; 11 grouped recovery, 23 grouped unit and 135 route; 58 manual plus
focused additions; 27 prelock/culvert plus ten expanded; stubtest/test-stubs.
Counts overlap. Interrupted first broad runs are not full passes; final broad gates
remain separately documented in `validation.md`.

Final performance probe: median locked-update increases approximately 8.2% Soils,
14.7% Wepp, roughly 60 ms per 100,000 field reads. Guard cost is documented and
justified by held-reference enforcement; no recovery-only healthy serialization,
deep-copy or disk reload. Small controllers do not establish production throughput.

Independent non-NoDbBase RunStatistics and RedisPrep are outside the implementation;
RunStatistics remains unresolved separately. No out-of-band writer, process-death,
deployment or affected-run repair claim. Final release remains conditional on
recorded broad-gate outcomes and explicit limitations.

## Broad-gate compatibility follow-up

The NoDb sweep exposed an ordinary unknown-commit exception-class regression in
_derived_build. Restore the existing _CommitOutcomeUnknown(RuntimeError), chained
from the original storage failure; cancellation remains the original marked signal.
Both paths retain recovery artifacts. An initially omitted restored class definition
was caught by review/focused failure and corrected before the final focused run.
All three reviewers reread and retain local approval; QA verified **51 passed**
in the actual RAP contention/manual-publication rerun. This is existing-contract
conformance, not a new normative decision. Broad outcomes remain in validation.md.

## TTL fixture compatibility follow-up

The old TTL race test simulated a separate process with the same cached singleton.
It now uses a distinct detached controller, records success after persistence,
and asserts only the accepted second writer remains in memory and on disk.
Correctness and QA reviewers approved this test-only clarification; production
locking is unchanged. The complete race module passed 17 tests. Same-singleton
ownership fencing remains covered by the actual-Redis matrix.
