# SURF-14A Source-Freeze Final Governance/Correctness Review

## Metadata

- **Reviewer**: independent governance/correctness control agent
- **Date**: 2026-07-30 UTC
- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Git base**: `b1f1f99c8f808528315abce001a70200ab068bc7`
- **Contract ancestors**: user-context amendment `4d2ef5838`; atomic
  admission amendment `b1f1f99c8`
- **Review boundary**: the final working-tree implementation, contract,
  ADR, tests, active ExecPlan/tracker, and validation evidence identified
  below
- **Runtime, local acceptance, Forest, or production mutation by this
  reviewer**: none

Historical final-review FAIL artifacts remain immutable. This is a fresh
source-freeze review of the superseding viewing-user, initiating-user, and
atomic-admission contract.

## Verdict

**PASS — APPROVE the governance/correctness side of this exact source
fingerprint for the receipt-bound local two-user acceptance gate.**

**Unresolved findings**: 0 High, 0 Medium, 0 Low.

The final implementation follows the authenticated viewing user for
request-local unit presentation and the authenticated initiating user for an
immutable WBT job snapshot. Neither behavior is selected from project
ownership, and neither account preference becomes durable project state. WBT
admission is one optimistic Redis transaction with exact-tree idempotency,
bounded conflict handling, active-location validation, and post-terminal tail
cleanup.

This approval does not authorize Forest or production. Forest remains gated
on the completed local acceptance and cleanup transcript, the required
post-acceptance independent reviews, an exact reviewed release/revert pair,
and the contract's deployment preflight. Production/wepp1 remains outside the
operator's authority. No break-glass basis was requested or used.

## Review-Driven Corrections

The following defects were found during source-freeze review and corrected
before this PASS. They are closed for the fingerprint below.

### GOV-SF-01 — Closed: a competing exact root commit could be overwritten

The first admission implementation checked the root only before entering its
`WATCH` retry loop. If another execution of the same root committed between
that check and `EXEC`, the losing execution retried with new child IDs and
could replace the root links, leaving a second hidden tree.

The final implementation watches both the tail and root job key, refreshes the
root after every conflict, and reuses only a fully validated exact committed
tree before attempting again
(`wepppy/rq/project_rq.py:658-762`). The forced competing-commit regression
proves both executions return the same build/receipt IDs and leave one
queued/deferred pair
(`tests/rq/test_wbt_controlled_failure_integration.py:877-961`).

### GOV-SF-02 — Closed: tail cleanup had to occur after terminal publication

Build-side `finally` cleanup could expose an empty tail while RQ still
reported the mutable child as started. Moving all cleanup to the completion
receipt then left a failed build's tail behind because controlled failure
cancels that receipt.

The final split is terminal-safe. A successful build's nonmutating receipt
compare-deletes only that build's still-current tail
(`wepppy/rq/project_rq.py:1786-1803`). On failure,
`WepppyRqWorker.handle_job_failure()` delegates to RQ first, which publishes
the terminal state and removes started-registry membership, and only then
compare-deletes a tail for a recognized admitted WBT build
(`wepppy/rq/rq_worker.py:218-264`). The real-worker policy-apply failure test
proves failed state, receipt cancellation, dependency cleanup, readiness
preservation, and tail removal
(`tests/rq/test_wbt_controlled_failure_integration.py:1301-1387`).

### GOV-SF-03 — Closed: valid RQ transition state was missing from admission

RQ 1.16 moves a queued job to the queue's intermediate list before marking it
started. Treating only queued/deferred/started registries as active could
misdiagnose this live transition as an orphan and could reject an exact-tree
retry.

The final implementation recognizes the intermediate list, watches the
status-appropriate execution-location keys before diagnosing an orphan, and
validates exact-tree dependency and registry residue
(`wepppy/rq/project_rq.py:392-456`, `459-610`, and `655-683`). Regression
coverage accepts an exact queued tree in the intermediate list and rejects
stale build/receipt dependency residue
(`tests/rq/test_wbt_controlled_failure_integration.py:719-875`).

## Governance and Correctness Assessment

### Authority, authentication, and identity

- The authoritative amendment records the requesting operator's superseding
  user-not-owner decision and was committed before its runtime implementation.
  The atomic queue contract and its parameter provenance were independently
  approved and committed as a second standalone ancestor.
- RQ authentication and run authorization occur before preference lookup
  (`wepppy/microservices/rq_engine/watershed_routes.py:903-914`); the regression
  at `tests/microservices/test_rq_engine_watershed_routes.py:1228-1265` proves a
  denial cannot read preferences.
- User and account-session identities resolve to an active positive numeric
  User. A present malformed/inactive/missing account identity fails closed.
  Service, MCP, and session-without-user identities use the project/config
  baseline (`wepppy/weppcloud/user_preferences.py:277-300`).
- Preference selection grants no access. Ownership remains relevant only to
  existing creation ownership behavior and never selects either preference.

### Request-local unit presentation

- SI and English create a detached read-only presentation view whose
  preferences are copied locally; mutation, lock, dump, and inherited state
  setters reject writes
  (`wepppy/weppcloud/user_preferences.py:412-515`). Auto/config returns the
  exact durable project Unitizer.
- Authenticated browser presentation resolves `current_user.id`; anonymous
  presentation uses project units. Resolution failure becomes the exact
  sanitized 500 contract
  (`wepppy/weppcloud/user_preferences.py:518-548`).
- The production adoption inventory leaves raw `Unitizer.getInstance()` only
  in the explicit Unitizer mutation endpoint. PostgreSQL two-user concurrency
  proves different simultaneous views with byte-, mtime-, cache-instance-,
  preference-, and lock-stable project state
  (`tests/weppcloud/test_user_preferences_postgres.py:405-460`).

### Initiating-user WBT snapshot and failure behavior

- The authorized request synchronously resolves the initiating identity,
  builds and round-trips the exact private snapshot against the immutable
  config baseline, and only then persists a missing legacy config baseline or
  changes enqueue inputs
  (`wepppy/microservices/rq_engine/watershed_routes.py:966-1030`).
- The snapshot's bounded child argument carries only schema version,
  effective policy, and source. Workers validate root metadata and argument
  equality and never query account state
  (`wepppy/weppcloud/user_preferences.py:303-409` and
  `wepppy/rq/project_rq.py:306-327`).
- A retry reuses the root's original private snapshot and exact child tree; a
  new submission resolves preferences again. Account-derived effective policy
  is applied only inside the complete mutable child's directory-root lock.
  Both durable WBT policy fields remain unchanged.
- Route, snapshot, and application failures preserve the contract's exact
  status, code, message, correlation ID, receipt cancellation, and aggregate
  terminal behavior. Public job status and job info expose neither the private
  snapshot nor an actor identifier.

### Atomic serial admission and revocation posture

- Nothing is durable before the single `MULTI`/`EXEC`. That transaction stores
  child and receipt jobs, dependency directions, root links, tail, and
  queued/deferred membership together
  (`wepppy/rq/project_rq.py:620-749`).
- Tail, root, prior job, and active-location keys are watched. Five conflicts
  exhaust without work. Ambiguous responses return only an exact reconciled
  tree whose tail, root, jobs, links, dependencies, and registries agree;
  otherwise admission fails closed.
- Missing or terminal tails are replaceable. A nonterminal tail outside every
  queued, intermediate, deferred, or started execution location fails closed
  for operator diagnosis. Compare-delete prevents an older build or receipt
  from clearing a newer reservation.
- The complete build-plus-abstraction mutation remains under the 43,500-second
  directory-root lock. The visible abstraction node is nonmutating. Controlled
  and unexpected failures cancel only the matching receipt and remove its
  dependency residue.
- Rollback remains coordinated and revocable: stop enqueue surfaces, drain and
  stop workers, use the exact reviewed forward-revert target, retain the
  additive table absent separate downgrade authority, and remove only a
  verified missing/terminal tail.

### Documentation and ADR posture

- Contract-first sequencing is complete through ancestors `4d2ef5838` and
  `b1f1f99c8`; runtime did not define the user-context or atomic-admission
  behavior first.
- ADR-0033 records the five-attempt conflict bound, 43,200-second RQ timeout,
  300-second lock margin, persistent tail, rejected alternatives, ownership,
  evidence, rollback, and revocation triggers. The review corrections add no
  formula, user-visible default, threshold, or new tunable parameter, so a new
  parameterization ADR is not required.
- The active ExecPlan and tracker are living release records. Immediately
  after the dual final-review artifacts exist, they must replace their stale
  pending-checkpoint labels and 5,675-test historical baseline with the final
  review disposition, 5,721-test source-freeze result, and remaining
  local/Forest gates. This required administrative update does not change the
  reviewed runtime contract or fingerprint.

## Validation Evidence

- Final RQ/Redis correction selection:
  **23 passed** (20 controlled-failure integration tests and 3 worker tests).
- Final canonical Python suite:
  **5,721 passed, 58 skipped, 1 collection skip, 1,023 warnings** in 628.16
  seconds (5,778 collected tests).
- Final affected source/test selection: **371 passed**.
- Frontend: lint passed and **745 JavaScript tests passed**.
- The recorded stub, test-stub completeness, isolation, RQ graph,
  broad-exception, documentation, PostgreSQL migration/concurrency, and focused
  preference/route/NoDb gates pass.
- `git diff --check` passes for the corrected RQ source and integration test.

The JavaScript and non-RQ gate results were supplied as the package's retained
validation evidence. This reviewer independently reran the real-Redis
integration module during review, observed and reported the intermediate
failure caused by receipt-only tail cleanup, and relied on the final
post-correction 23-test result plus the final full-suite result for approval.

## Remaining Release Gates

This PASS authorizes only the governance/correctness side of the local
acceptance gate. Before Forest:

1. obtain the parallel final operations/security PASS on the same fingerprint;
2. update the active ExecPlan and tracker with both final-review dispositions,
   the final source-freeze evidence, and the still-pending local/Forest gates;
3. complete the exact two-disposable-user, one-shared-run local acceptance and
   retain its redacted receipt-bound transcript;
4. obtain the required post-local cleanup dual review;
5. commit and record one exact reviewed release SHA and one reviewed
   forward-revert SHA; and
6. complete Forest backup, quiescence, migration, canary, cleanup, and
   post-action dual audit exactly as contracted.

Any change to viewing/initiating identity, authorization ordering, snapshot
schema, redaction, persistence lifetime, Redis admission phases, dependency
policy, tail cleanup, lock scope/timeout, failure state, migration graph, or
acceptance/deployment authority invalidates this approval.

## Review Fingerprint

The review used Git `HEAD`
`b1f1f99c8f808528315abce001a70200ab068bc7` plus the final working-tree
implementation. Hashes are SHA-256:

| Reviewed item | SHA-256 |
| --- | --- |
| Contract amendment | `c51e794bfbc633ef545e344c3aedaa9a8a0bd51c483ea0fe61c8d723f2216edd` |
| ADR-0033 | `6ec7ea926f1ed595dfd2ee635d69fa1bd59ea35ece804a4e6eb752e584ed19e4` |
| `weppcloud/user_preferences.py` | `3a42aa0e4d9a8bb9b3623116fc6dc2cc0f546c9355b3151fa46af4ec3ceebbaa` |
| `rq_engine/watershed_routes.py` | `1d19b7ed2dfd09e7e2e1e58a5b7f6c94e111b1835ef493d932b300e049168019` |
| `nodb/core/watershed.py` | `cdd7550d24255da1852b8be45793abfe6513300d31e078df68aced77ee89c86b` |
| `nodb/core/watershed_mixins.py` | `547c6e5b2a4c74b1c6ac9f5848c63246cc863e33378aa847bc7e10ae21ed4b43` |
| `rq/project_rq.py` | `2716aea0915ef25550c20b1f1bcea10ca91d745470bd20791491d0966c2ee102` |
| `rq/rq_worker.py` | `c22fa0a63757cb9c3b068e0e34f36e355b83af3c10fa762514960cd8aac05c91` |
| `rq/job_info.py` | `83621521bbac97c106f11e2d2e09216ec08b486c08a321a531a4f218e591f9ce` |
| PostgreSQL two-user test | `bbd1aa3c7ad57f5eacf14c01ab5c2871c3104bc7ecf73056ccafb50082e1e6d1` |
| RQ-engine snapshot/auth test | `4e4a565bbe7eed8377a0280a2b415733b23126b0ca27cff3a9e17f2325ff159e` |
| Real-Redis admission/failure test | `5f274607d4d12cdff939c8a9a2dd595e91690461a037ade2386ba0d6523c1a17` |
| Ordered in-scope source/test working-tree diff | `e64cff05adb1cfecfb0b9920b8a8a403747bf8baed73f9a65ba7816e0e815877` |

The ordered diff excludes unrelated Pure UI/Command Bar work,
code-quality-report outputs, `PROJECT_TRACKER.md`, the generated
`wepppy/weppcloud/routes/usersum/generated/docs_index.json`, review artifacts,
and the living package ExecPlan/tracker. The latter two were inspected but are
excluded from the implementation fingerprint because their next update must
record this review and cannot logically precede it.

## Review Validation

- `wctl doc-lint --path
  docs/work-packages/20260729_user_preferences_wbt_boundary/artifacts/2026-07-30_source_freeze_final_governance_review.md`
- `diff -u <review-artifact> <(uk2us <review-artifact>)`
- `git diff --check -- <review-artifact>`

All three review-artifact checks pass.
