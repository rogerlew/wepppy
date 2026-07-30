# SURF-14A Post-Remediation Operations and Security Closure

## Metadata

- **Reviewer**: independent operations/security control agent
- **Date**: 2026-07-30 UTC
- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Git base**: `b1f1f99c8f808528315abce001a70200ab068bc7`
- **Reviewed source/test/tool fingerprint**:
  `4aa271981f363b1a126e5fdf92fcb7d47d0f6804449ed92d0511494f4721ec73`
- **Fingerprint command**:
  `git diff --cached --binary -- .`
  `':(exclude)docs/work-packages/20260729_user_preferences_wbt_boundary/**'`
  `':(exclude)PROJECT_TRACKER.md' | sha256sum`
- **Forest or production mutation by this reviewer**: none
- **Break-glass basis**: none requested or used

This is a new additive artifact. It does not revise the earlier source-freeze
PASS reviews, the post-acceptance FAIL reviews, or the superseded remediation
review. Those historical decisions remain immutable evidence for their exact
states.

## Verdict

**PASS — APPROVE the operations/security closure gate for exact fingerprint
`4aa271981`.**

There are no open High, Medium, or Low operations/security findings.

The failed-create boundary now preserves the existing sanitized public error
contract, provides exact internal `error_id` and run ID correlation when
cleanup fails, and does not disclose the run ID in the public response. Exact
DB-0, DB-13, and DB-11 postconditions precede deletion of one canonical run
directory. A remaining key or Redis error stops cleanup before `rmtree`, so
operator evidence is retained rather than silently discarded.

The corrected local acceptance harness emits no PASS before cleanup. Its
strict canary exercised viewer and initiating-user scoping, reported the
observed NFS handle condition as `checks_passed_cleanup_pending`, exited
nonzero, and supported exact operator recovery. Independent post-action checks
found no canary SQL, Redis/RQ, filesystem, access-log, temporary-cookie, queue,
or worker residue.

This approval is fingerprint-specific. It authorizes packaging and the
already-approved Forest workflow only after the exact commit, quiescence,
rollback, and dual-review preconditions are rechecked. It does not authorize
production/wepp1 action or any broad cleanup.

## Findings Closure

| Historical finding | Closure evidence |
| --- | --- |
| `POST-OPS-01` — failed Create could leave an unreceipt-bound directory | Ron and ownership failures invoke exact cleanup. Cleanup failure retains the directory and emits one internal record with the same public `error_id` plus the generated run ID. |
| `POST-OPS-02` — acceptance cleanup was not durably asserted | The harness records receipts incrementally, applies exact SQL/RQ/session/run cleanup, checks DB-0/11/13 state, emits pending rather than PASS on cleanup failure, and exits nonzero. The strict rerun and independent residue audit are clean. |
| `POST-SEC-01` — Create token could use a nonnumeric subject | The issuer accepts only `type(current_user.id) is int` and a positive value. Missing, zero, negative, Boolean, and string IDs fail before token issuance; email and `fs_uniquifier` are not subject fallbacks. |
| `GOV-PR-01` — public cleanup receipt lacked a contract ancestor | The public cleanup receipt was removed. The unchanged response exposes only the existing sanitized error and `error_id`; recovery correlation is internal. |
| `GOV-PR-02` — corrected acceptance omitted DB-11 | Product and harness cleanup now delete and assert the exact DB-11 run key, alongside strict DB-0 and DB-13 postconditions. |
| `GOV-PR-03` — fingerprint and isolation evidence were not frozen | The exact binary-diff fingerprint was independently reproduced before and after review. The final full suite and both isolation seeds are terminal and passing. |
| `GOV-PR-04` — hardening lifecycle evidence was incomplete | The package now records the trigger, scope freeze, precedent, permanent-control decision, health and danger signals, guardrails, observation window, owner, rollback, and 14-day Forest review. |

## Control Assessment

### Public error boundary and internal recovery trace

The two post-directory failure paths generate one `error_id`, attempt exact
cleanup, and return the preexisting sanitized error with that `error_id`
(`wepppy/microservices/rq_engine/project_routes.py:421`,
`wepppy/microservices/rq_engine/project_routes.py:440`). Cleanup catches are
limited to the documented filesystem, Redis, runtime, and validation failures.
They log the exact same `error_id` and generated run ID internally
(`wepppy/microservices/rq_engine/project_routes.py:426`,
`wepppy/microservices/rq_engine/project_routes.py:456`).

The regression injects both `OSError` and `RedisError`, proves a 500 response,
proves the generated run ID is absent from the public body, and proves exactly
one cleanup record carries matching `error_id` and run ID
(`tests/microservices/test_rq_engine_project_routes.py:430`). No new public
cleanup field or public run ID is present.

An operator must capture the rq-engine record before restarting that service.
If cleanup fails, the public `error_id` is the lookup handle and the correlated
internal run ID is the only deletion target. Operators must preserve the log,
exact Redis keys, and directory until the cause is understood.

### Exact cleanup containment and postconditions

Cleanup accepts only the normalized path returned for the generated run ID,
confines it below the primary runs root, rejects the root itself, rejects a
top-level symlink or non-directory, and requires symlink-resistant
file-descriptor cleanup
(`wepppy/weppcloud/user_preferences.py:577`).

After closing run-scoped NoDb instances, the operation:

1. clears locks and deletes the exact DB-0 hash, then asserts it absent;
2. clears the NoDb file cache and scans DB-13 for the exact resolved target and
   its descendants, then asserts no key remains;
3. deletes the exact DB-11 run key, then asserts it absent; and
4. only then calls `shutil.rmtree` for the canonical directory.

The strict helpers are at
`wepppy/weppcloud/user_preferences.py:29` and the ordered operation is at
`wepppy/weppcloud/user_preferences.py:596`. Redis exceptions propagate.
Remaining-key and Redis-error probes independently covered DB-0, DB-11, and
DB-13 and proved that the directory remains present before `rmtree`. The
repository regressions also prove call ordering, exact canonical deletion,
DB-13 remaining-key and Redis-error behavior, cache-purge failure retention,
root/symlink rejection, and symlink-replacement resistance
(`tests/weppcloud/test_user_preferences.py:268`).

This is a permanent compensating control, not a temporary callus. It does not
authorize recursive scans or deletion of sibling runs.

### Acceptance receipt and recovery behavior

The harness records each created session and WBT root as it succeeds. A failed
Create receipt contains the status code and public `error_id`, not a guessed or
publicly disclosed run ID
(`tools/surf14a_local_acceptance.py:200`). A successful behavioral receipt is
held in memory until the `finally` cleanup completes.

Cleanup removes the exact sessions, jobs, mutation tail, SQL associations,
Run, Users, run caches, run directory, and adjacent access log. It compares
pre/post SQL counts and verifies exact DB-0, DB-11, and DB-13 state. Any
bounded cleanup error changes the receipt to
`checks_passed_cleanup_pending`, prints the non-secret recovery receipt, and
raises a nonzero failure. PASS is printed only after all postconditions
(`tools/surf14a_local_acceptance.py:322`).

The strict rerun used Users 341/342, Run 1404
`pain-free-prospectus`, and four receipt-bound WBT roots. Its behavioral checks
passed, but 13 zero-length NFS `.nfs*` handles prevented directory removal.
The harness correctly emitted pending, not PASS. The operator restarted only
WEPPcloud and rq-engine to release the handles, removed the exact now-empty
directory, proved the directory and adjacent access log absent, and restarted
both workers. This is an observable recovery path with a bounded blast radius.

### Viewer and initiating-user scoping

Authenticated Unitizer presentation resolves the active viewer's positive
numeric User ID. `Auto` returns the durable project Unitizer; SI or English
returns a detached immutable view whose persistence, lock, and NoDb mutations
are rejected
(`wepppy/weppcloud/user_preferences.py:438`,
`wepppy/weppcloud/user_preferences.py:530`).

WBT execution resolves the already-authorized initiating account and creates a
private immutable snapshot containing the actor User ID, config policy,
effective policy, and source. Service/accountless execution remains
project-config scoped. The route and worker validate that snapshot, while
public job information redacts it.

The strict two-user canary proved distinct SI/English views of one byte-stable
project, distinct `error`/`warn` initiating-user snapshots, Auto/config and
service fallback, public snapshot redaction, and unchanged durable Unitizer
and WBT fields. Authorization-before-preference and negative user-scoping paths
remain covered by the final full suite.

### Token subject integrity

The Create-page issuer binds a user-class token only to the exact positive
integer database User ID and stringifies that ID only at token issuance
(`wepppy/weppcloud/routes/run_0/run_0_bp.py:2266`). Its regression proves ID
42 wins over `get_id()` and rejects `None`, zero, negative, Boolean, and string
IDs without calling the token issuer
(`tests/weppcloud/routes/test_run_0_create_token.py:16`).

Email remains an informational claim, not an identity subject. There is no
email or Flask-Security `fs_uniquifier` fallback.

## Independent Post-Action Evidence

The reviewer performed read-only exact SQL, Redis, and filesystem checks after
the strict cleanup and operator recovery:

| Boundary | Independent result |
| --- | --- |
| Users 284/285, 312/313, and 341/342, plus both disposable emails | 0 rows |
| Exact preference and User-role receipts | 0 rows |
| Runs 1394/1404 and all four acceptance-era run IDs | 0 rows |
| Exact run associations | 0 rows |
| Redis DB 0/2/9/11/13/14/15 key-name and value search for all four run IDs and eight WBT job IDs | 0 hits |
| All four run directories and adjacent access-log paths | absent |
| `/tmp/surf14a-cookies.txt` and `/tmp/surf14a*` | absent |
| `default` and `batch` queues | 0 queued, 0 executing |
| RQ workers | 10 registered, all idle |
| WEPPcloud, rq-engine, Redis, PostgreSQL, and both worker services | running; Redis and PostgreSQL healthy |

The canonical `wctl rq-info` status command refreshes local RQ worker
registration sets as part of its inspection. It did not enqueue, delete, or
execute a job. The reviewer created no application data and performed no
Forest or production action.

## Validation Evidence

| Gate | Result |
| --- | --- |
| Exact fingerprint reproduction | **PASS — `4aa271981f363b1a126e5fdf92fcb7d47d0f6804449ed92d0511494f4721ec73`** |
| Final full Python suite | **PASS — 5,732 passed, 58 skipped, 1,023 warnings in 635.35s** |
| Exact quick isolation, seeds 42 and 123 | **PASS — project-routes and user-preferences modules isolated; no issue** |
| Independent focused token/Create/cleanup suite | **PASS — 71 passed** |
| Independent strict DB-0/11/13 failure probe | **PASS** |
| Frontend | **PASS — lint plus 104 suites/745 tests** |
| Stub gates | **PASS — 3 stubtests and test-stub completeness** |
| RQ dependency graph/catalog | **PASS — independently reproduced** |
| Changed-file broad exceptions | **PASS — net -5, independently reproduced** |
| Documentation and configured vulture gates | **PASS** |
| Cached diff whitespace check | **PASS** |

The final fingerprint was reproduced after the independent focused suite and
strict failure probe. The focused probe used automatically removed temporary
directories and mocked Redis clients; it did not mutate shared Redis.

## Recovery, Rollback, and Release Conditions

- Bind any Forest action to one committed SHA containing exact fingerprint
  `4aa271981`, then rerun the package's exact-SHA and clean-tree checks.
- Before migration or canary, stop the affected enqueue surfaces, drain both
  queues, prove all workers idle, capture schema and rollback preconditions,
  and restart all changed consumers on the same reviewed commit.
- On any cleanup failure, preserve the public `error_id`, correlated internal
  run ID, exact DB-0/11/13 keys, directory, logs, queue state, and SQL receipts.
  Do not guess a run ID or broaden deletion.
- On any residual key, missing correlation, out-of-scope deletion, snapshot
  leak, viewer/initiator cross-talk, or timing-dependent WBT result, stop the
  rollout and use the package's pre-reviewed forward revert/rollback path.
- Record migration output, exact canary IDs, cleanup proof, restart state, and
  any recovery action in the required post-action review. Keep the 14-day
  hardening observation window and danger-signal review.
- Production/wepp1 remains outside this package's authority.

## Final Control Decision

Exact fingerprint `4aa271981` satisfies the operations/security closure gate.
It may proceed to the separately authorized Forest preflight and canary
workflow only with the containment, rollback, exact-SHA, dual-review, and
post-action conditions above. Historical FAIL artifacts remain valid for
their rejected states; this PASS does not retroactively alter them.
