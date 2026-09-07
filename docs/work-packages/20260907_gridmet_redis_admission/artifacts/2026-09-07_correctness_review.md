# Correctness and user-experience review - GridMET Redis admission

## Metadata

- Reviewer: independent Codex `/root/review_contract`; no runtime edits.
- Final review: 2026-09-07 16:37 UTC, implementation working tree on `master`.
- Starting revision: `583e6870c639999515035423f133e5925dae2da5`.
- Contract checkpoint: `1b4835ca73bc67c9c84ecbb26f596aab4078e234`.
  Verified it is an ancestor of HEAD and preceded the runtime changes.
- Scope: admission Lua/controller/permit, point/grid HTTP acquisition, public
  forwarding, Daymet/PRISM and NoDb orchestration, tests, probe, development
  Compose, and operator documentation.
- Canonical authority: [admission contract](../../../schemas/gridmet-redis-admission-contract.md),
  [ADR-0050](../../../adrs/ADR-0050-gridmet-redis-admission.md), and preserved
  [ADR-0028](../../../adrs/ADR-0028-gridmet-download-retry-concurrency.md).
- Related evidence: [checkpoint](2026-09-07_contract_decision.md),
  [call inventory](2026-09-07_call_inventory.md),
  [QA/code](2026-09-07_code_qa_review.md),
  [security](2026-09-07_security_review.md), and
  [validation](2026-09-07_validation.md).

## Findings and closure

| ID | Severity | Finding and affected state | Required correction and verified closure |
| --- | --- | --- | --- |
| COR-01 / SEC-02 | Medium | `admission.py:GridMetPermit.__exit__` checked failure before joining an in-flight renewal. A failure recorded during join could disappear behind successful release. Direct failed renewal was not terminal. | `renew` records terminal failure; `release` joins before closing; exit rereads failure after join. Real-thread success/failure regressions pass. An independent thread/event reproduction confirmed failure arising during exit is raised. |
| COR-02 / SEC-01 / SEC-03 | Medium | `_SCRIPT` could restart sequence numbering with live queued tickets when its sequence key was missing. Cardinality checks missed mismatched members and duplicate ordinals. Pruning before full validation could mutate live foreign state before an error. | Pre-write validation covers types, canonical sequence representation, strictly increasing ranks, matching queue/liveness/owner membership, disjoint active membership, and finite expiries. Independent real-Redis corruption checks rejected missing sequence, duplicate rank, and same-count mismatched members with all six serialized keys unchanged. Security independently verified four additional malformed cases. |
| COR-03 | Medium | `climate_build_helpers.py:run_observed_daymet_multiple_build` parsed GridMET environment even when effective GridMET wind was disabled, allowing unrelated invalid admission settings to fail a Daymet-only build. | Resolve after the build-input snapshot and only when GridMET wind is enabled. The complete final-output regression passes for both wind states; the false case uses malformed GridMET enable text and the real parser. |
| COR-04 | Low | `GridMetAdmissionController.snapshot` counted active holding time as queue wait for locally tracked tickets. | Freeze the local wait interval on admission, retain it through active observation, and clear it on release. The final admission suite verifies the frozen value and foreign-observer sentinel. |

No finding is accepted as a risk exception. All listed findings are resolved.

## User outcome and valid-state matrix

Enabled climate work shares a FIFO live-permit limit while preserving successful
public DataFrame results and validated NetCDF publication. Disabled direct
clients preserve their existing behavior without constructing a controller or
Redis connection. Queue pressure, Redis failure, and upstream acquisition
failure remain distinguishable.

Input combinations and Redis/lifecycle state were reviewed separately. These
are coverage categories, not a claim that every possible interleaving was tested.

| Dimension/state | Valid? | Required outcome | Evidence |
| --- | --- | --- | --- |
| Public `None`; absent/false enable | Yes | Existing client result; zero admission Redis activity | `test_admission.py` parser tests and `test_admission_clients.py` disabled paths |
| Valid enabled policy, absent/empty namespace | Yes | Atomic initialization and admission | Real-Redis scenarios admit a valid owner before each scenario |
| Populated queue and active holders | Yes | FIFO among live tickets, occupancy at most limit, observed queuing | Real-Redis `fifo` and six-process `processes` scenarios |
| Healthy waiter/holder beyond refresh interval | Yes | Waiting ticket retains sequence beyond TTL; active expiry advances automatically | Real-Redis `heartbeat` scenario: waiter survives eight seconds with seven-second TTL |
| Stale waiting ticket or expired lease | Expected recovery | Prune; no renewal resurrection; permit cannot authorize HTTP after expiry | Real-Redis `ownership`/`killed`; local and delayed-reply tests |
| Timeout or cancellation | Expected | Explicit bounded failure and owned-state cleanup | Real-Redis `timeout`; HTTP KeyboardInterrupt and invalid-context-entry tests |
| Foreign token, conflicting policy, malformed Redis state | No | Explicit rejection without modifying another live owner's state | Real-Redis ownership and corruption scenarios plus independent serialized-state checks |
| Invalid/empty enable, nonfinite or unrepresentable values | No | Configuration error before Redis/HTTP | Configuration and HTTP lease-relation tests |
| Daymet workflow with GridMET wind disabled | Yes | No GridMET configuration dependency | `test_run_observed_daymet_multiple_build_sets_final_outputs` |
| Existing deployment without Redis admission state | Supported legacy | No migration or new admission dependency | Disabled tests and default-off Compose contract |

## User-reachable error policy and partial state

The contract's state-transition and permit-lifecycle sections authorize distinct
`GridMetAcquisitionError` subclasses for configuration/conflict, waiting
exhaustion, Redis unavailability, and lost lease. Waiting exhaustion is an
expected pressure outcome; the others indicate configuration or coordination
failure. Admission failures do not enter the ordinary upstream retry loop.

ADR-0028 continues to control transport/payload retries, three attempts,
5/10-second sleeps, redirects, byte ceilings, exact date coverage, and atomic
publication. Both HTTP clients close the response while admitted and release
before payload validation, file publication, or backoff. Every retry gets a
new FIFO ticket under the original monotonic scheduling deadline. Lease loss
prevents successful validation/publication and closes the response on resumed
control. Cleanup attempts only owned state; Redis outage may leave expiring
state for reclamation while preserving an explicit primary failure.

## Independent validation

- `wctl run-pytest tests/climates/gridmet/test_admission.py
  tests/climates/gridmet/test_admission_clients.py
  tests/nodb/test_climate_build_helpers.py --maxfail=1`: **104 passed**, two
  existing dependency deprecation warnings, 10.49 seconds.
- After the last local-wait and context-entry fixes,
  `wctl run-pytest tests/climates/gridmet/test_admission.py --maxfail=1`:
  **41 passed**, two existing dependency deprecation warnings, 10.09 seconds.
- Independent `wctl run-python -c` thread/event reproduction placed an actual
  renewal failure between the initial exit check and renewal-thread join.
  Result: `renewal_exit_race_rejected=True`; the thread terminated.
- Independent `wctl run-python -c` used disposable Redis
  `gridmet-admission-test-20260907:6379`, three unique UUID namespaces, and the
  actual `_SCRIPT`. Missing sequence, duplicate ordinal, and equal-count
  mismatched membership each returned explicit failure with all six Redis
  `DUMP` values identical before and after. Only those exact test keys were
  removed; no operational namespace or database flush was used.
- Implementation-owner real-Redis run: **9 scenarios passed**, 153.11 seconds,
  including independent processes, killed owners, clock disagreement,
  corruption, and automatic heartbeat/queue liveness. This reported result is
  supplementary to the direct independent checks above.
- `git diff --check` passed. Full-suite, final probe/Compose/stub checks, exact
  candidate commit, and Forest results belong to the linked validation and
  integration artifacts; none are inferred from focused pass counts.

## Contract clarification review

Post-checkpoint prose makes representability constraints explicit: Lua-exact
integer retention/limit values and Python's maximum thread timeout. These
clarify the implementation domain needed for the already-required explicit
configuration failure contract; they do not revise the ratified operating
values, formulas, HTTP behavior, or tuning authority.

The elapsed-wait clarification identifies its existing local monotonic origin.
An external controller reports zero when that origin is unavailable; zero is
an unavailable sentinel there and must not be interpreted as actual zero wait.
Queue position, live counts, policy, and Redis time remain observable across
processes. Locally known active tickets retain their completed queue wait.

## Verdict and residual risk

- Correctness gate: **PASS**; unresolved high 0, medium 0, low 0.
- Reviewer sign-off: Codex `/root/review_contract`, 2026-09-07 16:37 UTC.
- Release recommendation: proceed through the remaining full validation,
  independent final QA/security gates, exact committed/pushed candidate, and
  required Forest deployment acceptance. This review is not Forest acceptance.

Residual risk is explicit: Redis bounds live permits and cooperative clients;
it cannot fence an already-running remote request during process suspension,
partition, DNS stalls, or trickling I/O. Opted-out or separately configured
callers bypass the shared pool by design, so worker configuration parity must
be proved at deployment. Default automated runs skip the opt-in real-Redis
tests unless their isolated service is configured. Forest must still prove
cross-container behavior and a successful real public request. No batch,
registry publication, or Kubernetes acceptance is claimed.
