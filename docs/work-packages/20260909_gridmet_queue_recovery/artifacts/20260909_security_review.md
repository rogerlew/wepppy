# GridMET queue recovery: independent QA and security review

## Findings

| ID | Severity | Surface | Finding and evidence | Required action | Disposition |
| --- | --- | --- | --- | --- | --- |
| QAS-01 | Medium | Cancellation and exceptional cleanup | Initial `GridMetPermit.__exit__` always used unlimited release recovery, even with `KeyboardInterrupt`, `SystemExit`, an upstream exception, or an already detected lease failure. A direct permit probe performed four release calls during canceled-context cleanup before eventual Redis recovery. A persistent outage could indefinitely delay the primary exception. The old mocked client lifecycle test could not detect this. | Use one bounded ownership-safe cleanup attempt when an exception/failure is already pending or entry is invalid; retain recovery for ordinary successful release. Exercise the actual permit implementation. | Resolved: `release(recover=False)` is selected for exceptional exit/invalid entry. The actual-permit cancellation cases and existing failure-precedence tests passed independently. |
| QAS-02 | Low | Terminal-error regression coverage | Initial tests exercised fabricated private transport errors but did not prove redis-py's authentication/authorization subclasses stay outside the retry branch. Those classes can inherit connection-related types. | Exercise actual Redis exception classes through `_transition` and `_retry_transition`; assert terminal call counts and redaction, with transport recovery as the valid counterpart. | Resolved: five parametrized cases passed independently for AuthenticationError, AuthorizationError, ResponseError, ConnectionError, and TimeoutError. |

No unresolved code finding remains from this review. Correctness, cancellation,
ownership, terminal-error, and final package-wide checks pass.

## Metadata and scope

- Reviewer: independent `security_review` agent, acting as the package's requested QA/security reviewer.
- Date: 2026-09-10 UTC / 2026-09-09 PDT.
- Reviewed code base: WEPPpy `master` at `d32a3981c` plus this package's worktree changes. Final admission source SHA256: `4b7ea2be5a5839d383d8ae844c594b3f119388ab3f283c342200e95cf9ede07b`; final annotation-only corrections were inspected and the module's stubtest passes.
- Scope: `wepppy/climates/gridmet/admission.py`, `acquisition.py`, `client.py`, associated admission/client/real-Redis tests, probe help, and updated documentation.
- Authority: [admission contract](../../../schemas/gridmet-redis-admission-contract.md), especially State transitions and ownership, Permit lifecycle/errors/recovery, and Safety guarantee and limits; [ADR-0061](../../../adrs/ADR-0061-gridmet-persistent-queue-recovery.md).
- Related artifact: [independent correctness review](correctness-review.md), whose three findings are now closed. No production code, operational Redis, or deployment state was changed by this reviewer.
- Consolidated incident and execution evidence: [incident and validation](incident-and-validation.md).

## Triage and threat assumptions

Security triage is **high** under the work-package standard because the change
affects shared worker admission and ownership recovery. This is distinct from
the severity of individual findings. The initial package's `medium` triage
label was corrected to the canonical none/low/high vocabulary. The contract now
explicitly records bounded exceptional cleanup and immediate local revocation.

Redis remains trusted coordination infrastructure. Ownership tokens are
cryptographically random and secret to their attempt. The design coordinates
cooperative HTTP clients; it does not fence an upstream socket after a process
pause or network partition. Waiting for healthy capacity is a valid user state,
not malformed state. Redis transport failure is distinct from authentication,
authorization, configuration conflict, foreign ownership, and state corruption.

## QA assessment

The implementation removes the elapsed admission deadline from the controller
and both HTTP callers without changing HTTP payload validation, retry status
classification, byte limits, response closing, or file publication. The retained
wait configuration and fingerprint preserve compatibility with existing live
policy records while the revised code stops enforcing a queue-age cutoff.

One internal retry helper handles operation replay, sanitized diagnostics,
jitter, and optional renewal stop/validity bounds. Lua same-token enqueue/poll
replay retains the live queue ordinal or confirms an already granted lease.
Foreign-owner rejection and pre-mutation structural validation remain intact.
The helper retries only its private transport exception; terminal exceptions
escape explicitly. This is a focused extension of the existing owner protocol,
with no new dependency or alternate admission implementation.

The separate `_closed` and `_released` flags have distinct purposes: local HTTP
authority is revoked before a release can commit, while Redis cleanup can be
replayed after an uncertain reply. Their regression tests verify that retrying
cleanup cannot restore authority. Renewal retains the conservative pre-command
local expiry bound and cannot use a reply after that bound to authorize work.
The final renewal guard serializes manual/background renewal so a delayed
earlier reply cannot invalidate a newer confirmed lease. The exceptional-release
path rechecks renewal failure after joining the background thread, preserving
the confirmed primary failure if cleanup also fails.

Tests combine fast branch/lifecycle fixtures with real Redis scenarios in fresh
interpreters, avoiding the repository's global Redis stub at the Lua boundary.
The real-socket suite explicitly requires opt-in on a disposable service before
using `CLIENT PAUSE`; it must run serially. No pause test may target operational
Redis. A delay injected before the real command and a fabricated lost response
after a committed command exercise different uncertain-outcome paths; neither
alone proves both.

### Valid-state and test matrix

| State | Contracted behavior | Evidence reviewed |
| --- | --- | --- |
| Admission omitted/None, or environment disabled | No Redis construction/I/O; legacy HTTP behavior | Existing disabled/lazy config and client tests |
| Namespace absent or idle | Initialize/adopt policy atomically | Real-Redis ownership scenario and Lua inspection |
| Populated healthy FIFO queue beyond old wait budget | Remain eligible with same live ticket until admitted | Real persistent scenario plus 901-second simulated-clock regression |
| Unknown enqueue/poll command outcome | Replay matching owner; no invented grant or duplicate occupancy | Independently rerun real lost-reply scenario; owner socket-delay suite |
| Active owner with transient renewal failure | Retry only before the last confirmed local bound | Recovery/expiry and delayed-reply tests; real renewal-delay scenario |
| Successful HTTP receipt with lost release reply | Revoke local authority; recover idempotent release before validation/publication | Actual permit authority tests; real HTTP release-delay scenario |
| Cancellation or exceptional exit | Close response, stop renewal, attempt bounded owned cleanup, preserve error policy | Actual permit cancellation tests and HTTP lifecycle tests |
| Expired or abandoned owner/ticket | Reclaim by lease/heartbeat; no resurrection | Existing real ownership/killed-owner/heartbeat scenarios |
| Foreign token, policy conflict, corrupted Redis state, auth failure | Explicit terminal error; no foreign repair/deletion or unlimited retry | Lua checks, real ownership/corruption scenarios, new error-classification tests |

The matrix is representative and does not claim exhaustive process-scheduling,
network-fault, or input-state combinations.

## Security surface checks

### Auth, secrets, and logging

No route authentication, JWT, CSRF, public upload, or secret configuration is
changed. Redis auth/ACL failures are terminal. Error translation suppresses
original exception details and logs bounded operation/error-class context;
tests assert sensitive original messages do not reach diagnostics. Ticket and
ownership tokens are not logged. Existing Redis connection construction remains
lazy and process-local.

### Input, network, and file safety

Validated namespace/request-kind bounds remain. No user-provided text is added
to shell commands, Lua source, or network destinations. Existing GridMET
redirect refusal, byte limits, timeouts, payload checks, staged NetCDF writes,
and response lifetime are preserved. Indefinite healthy queue waiting and
successful-release recovery are explicit user-authorized semantics, not a
silent bypass of capacity or HTTP validation.

### Queue ownership, concurrency, and cancellation

No RQ enqueue edges are changed. The Redis FIFO script still guards the shared
live-permit limit and token ownership. Same-token replay is permitted only after
structural checks and pruning; expired authority cannot be renewed into a
previously valid owner. The response is closed before release. QAS-01's bounded
exceptional cleanup closes the cancellation regression; failed cleanup leaves
only owned state to expire normally. Cleanup retries do not alter foreign owners.

### Tooling, deployment, and supply chain

No new dependency, workflow permission, service exposure, or deployment wiring
is introduced. The reviewer ran isolated Python checks and canonical targeted
tests only. Dedicated Redis pause tests are coordinated by the package owner;
this review does not authorize production Redis interruption or deployment.
The existing coordinated activation gate still applies before production use.

## Validation evidence

- Initial `wctl run-python -` permit probe used actual `GridMetPermit.__exit__` and `_retry_transition` with a scripted transport boundary: canceled-context cleanup issued **four release calls** before recovery. This confirmed QAS-01's retry control flow; it was not presented as a real-network test.
- Independent `wctl run-pytest tests/climates/gridmet/test_admission.py tests/climates/gridmet/test_admission_clients.py --maxfail=1`: **83 passed**, two dependency deprecation warnings, 9.42 seconds. Includes actual permit cancellation, local release revocation, repeated cleanup, and renewal failure precedence.
- Independent `wctl run-pytest tests/climates/gridmet/test_admission.py::test_redis_exception_classification_and_redaction --maxfail=1`: **5 passed**, two dependency deprecation warnings, 9.40 seconds. Terminal cases made one command attempt; transport cases recovered on the second. Original exception details were absent from error/log output.
- Independent final recheck of `test_inflight_renew_is_joined_before_terminal_failure_check` and `test_manual_and_background_renewals_do_not_overlap`: **5 passed**, two dependency deprecation warnings, 9.54 seconds. These cover all four inflight-renew/release-failure combinations and renewal serialization after the last code changes.
- Independent fresh-interpreter execution of real Redis **ownership, corruption, and lost-reply** scenarios: all passed, each ending with queued **0** and active **0**. These used unique disposable namespaces and made no `CLIENT PAUSE` or global deletion calls.
- Independent actual-permit/real-Lua cancellation probe: release committed, then the reply adapter raised redis-py TimeoutError while `KeyboardInterrupt` was pending. Exactly **one** cleanup call ran, local `check()` rejected further use, final queued/active counts were **0**, and cleanup logging exposed only the translated exception class.
- The independent correctness reviewer reran **91 permit/client tests** and the concurrent-renewal probe against actual Redis; all findings closed. The serial full real-Redis boundary/socket suite passed **14 cases** in 192.53 seconds.
- Final post-correction boundary logs inspected: **4 ownership/lost-reply/clocks/heartbeat cases passed** in 54.63 seconds (`/tmp/gridmet-real-recheck.txt`); **4 actual socket-delay cases passed** in 46.18 seconds (`/tmp/gridmet-delay-final.txt`). The latter cover enqueue, poll, renew, and release with actual redis-py timeouts. Both runs completed successfully.
- Final focused result inspected: **145 passed, 14 opt-in Redis cases skipped**, 9.67 seconds (`/tmp/gridmet-focused-final3.txt`). The separate explicit real-Redis runs above supply the skipped opt-in coverage.
- Final broad result inspected: **8192 passed, 77 skipped**, 3109 warnings, 852.04 seconds (`/tmp/gridmet-full-final.txt`), successful completion. No broad-suite pass is inferred from the focused tests.
- Owner-recorded public download acceptance used Forest worker and batch-worker environments: **366 validated rows**, observed peak active **1** over **595 samples**, and zero final queue/active state. This is local worker acceptance, not a production rollout claim.
- Final module API check inspected: `wctl run-stubtest wepppy.climates.gridmet.admission` reported **Success: no issues found in 1 module** (`/tmp/gridmet-stubtest-final3.txt`). The additional source changes are type annotations/imports, with no changed retry or ownership behavior; no new runtime tests were needed for those annotations.
- Final documentation review confirms high triage and the explicit exceptional-cleanup/local-revocation contract. `wctl doc-lint --path docs/work-packages/20260909_gridmet_queue_recovery/artifacts/20260909_security_review.md`: **1 file validated, 0 errors, 0 warnings**; spelling preview and `git diff --check` also pass.

## Residual risk and operational conditions

- A prolonged outage intentionally leaves uncanceled waiting/successful-release operations blocked. Active HTTP authority still ends at the last confirmed local lease bound.
- Redis leases do not forcibly stop an upstream request under arbitrary process suspension or blocked I/O. Existing contract limits remain explicit; no hard remote-socket ceiling is claimed.
- A ticket whose heartbeat expires during a prolonged outage rejoins at the tail. FIFO is preserved among continuously live tickets, not across reclaimed state.
- Mixed old/new workers retain the same fingerprint, but old processes keep the prior timeout behavior until recreated. Local correctness does not establish production activation.
- Production activation remains a separate boundary. The dedicated disposable Redis was removed after testing; no production restart or admission bypass is authorized by this sign-off.

## Verdict and sign-off

- QA code review: **pass**, QAS-01 and QAS-02 resolved and independently rechecked.
- Security code findings: High **0**, Medium **0**, Low **0** unresolved.
- Security review: **pass** for the final reviewed implementation and completed boundary/package evidence.
- Release recommendation: **ship the reviewed source change**; package closure and scoped commit/push may proceed. Production deployment remains held as a separate operational action.
- Reviewer: independent `security_review` agent, 2026-09-10 UTC. No risk acceptance requested; no production activation approval is implied.
