# Source-Freeze Final Operations and Security Review

## Metadata

- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Reviewer**: independent operations/security control agent
- **Date**: 2026-07-30 UTC
- **Reviewed state**: frozen SURF-14A implementation and tests in the shared
  worktree atop `b1f1f99c8f808528315abce001a70200ab068bc7`
- **Review scope**: Redis/RQ WBT admission and recovery, authorization and
  initiating-user snapshot provenance, viewer-scoped Unitizer isolation, and
  the release evidence supplied for this work package
- **Forest or production mutation by this review**: none

## Verdict

**PASS — approve the operations/security release gate and the coordinated
local stack restart for the frozen reviewed state.**

There are no open High, Medium, or Low operations/security findings. The
implementation now provides a bounded atomic admission boundary, validates
active-tail execution location, fails closed on non-exact reconciliation, and
does not release the run tail before the mutable child becomes terminal.
Authorization precedes preference lookup, the initiating user's decision is
snapshotted into the RQ tree, and request-local Unitizer views do not mutate or
replace the durable project controller.

This approval is state-specific. Any implementation or generated RQ-graph
drift requires renewed review. Forest remains subject to the contract's
separate local-acceptance, post-acceptance dual-review, exact-SHA, quiescence,
drain, migration, canary, cleanup, and post-action gates.

## Findings by Severity

| Severity | Open findings |
| --- | ---: |
| High | 0 |
| Medium | 0 |
| Low | 0 |

### Review-driven issues closed before approval

The initial final-review pass found two release blockers and one related
reconciliation weakness. All are closed in the frozen state:

1. The mutable child previously compare-deleted its tail from the task
   function before RQ recorded a terminal state. The child now leaves the tail
   intact. A successful completion receipt can release only its matching build
   tail after the build dependency is terminal, while the worker failure
   handler releases only after superclass terminalization
   (`wepppy/rq/project_rq.py:1751`,
   `wepppy/rq/project_rq.py:1786`,
   `wepppy/rq/rq_worker.py:218`).
2. A present but nonterminal tail job previously counted as active without an
   execution location. Admission now recognizes queued, RQ intermediate,
   deferred, and started locations, watches the relevant location keys, and
   fails without work when the watched job is an orphan
   (`wepppy/rq/project_rq.py:392`,
   `wepppy/rq/project_rq.py:428`,
   `wepppy/rq/project_rq.py:655`).
3. Exact-tree reconciliation previously did not reject dependency residue
   after a job left the deferred state. It now validates status-specific
   registry membership, both dependency directions, empty post-deferred
   dependency sets, and supported terminal states
   (`wepppy/rq/project_rq.py:459`).

Regression evidence for these closures is at
`tests/rq/test_wbt_controlled_failure_integration.py:397`,
`tests/rq/test_wbt_controlled_failure_integration.py:502`,
`tests/rq/test_wbt_controlled_failure_integration.py:607`,
`tests/rq/test_wbt_controlled_failure_integration.py:719`,
`tests/rq/test_wbt_controlled_failure_integration.py:768`, and
`tests/rq/test_wbt_controlled_failure_integration.py:819`.

## Control Assessment

### Atomic admission, traceability, and rollback safety

- Stable build and receipt IDs are allocated once before the five-attempt
  `WATCH` loop. Tail, parent, prior-job, and applicable registry keys are
  watched before admission (`wepppy/rq/project_rq.py:651`).
- Job construction remains in memory until one `MULTI`/`EXEC` writes the
  queued/deferred child, deferred receipt, dependency directions, root links,
  and persistent run tail. No child-specific durable state is written before
  `MULTI` (`wepppy/rq/project_rq.py:713`,
  `wepppy/rq/project_rq.py:740`).
- `WatchError` retries are bounded at five. Conflict exhaustion restores the
  parent view and returns without admitted work
  (`wepppy/rq/project_rq.py:750`).
- A lost response after `EXEC` returns only a fully linked, exact tree with the
  expected current tail. A pre-commit connection failure or any mismatch
  fails closed and does not create a duplicate
  (`wepppy/rq/project_rq.py:769`).
- The exact-tree validator covers root/build/receipt identity, fingerprint,
  both child links, active and intermediate registry membership, dependency
  directions, and stale dependency residue
  (`wepppy/rq/project_rq.py:459`).

This closes the no-pre-`EXEC` orphan window and preserves a reconstructable
execution trace. The relevant Redis tests force a watch retry, five-conflict
exhaustion, competing exact commit, commit-then-connection-error, no-commit
failure, linkage mismatch, exact retry, and intermediate-queue transition
(`tests/rq/test_wbt_controlled_failure_integration.py:658`,
`tests/rq/test_wbt_controlled_failure_integration.py:819`,
`tests/rq/test_wbt_controlled_failure_integration.py:877`,
`tests/rq/test_wbt_controlled_failure_integration.py:964`,
`tests/rq/test_wbt_controlled_failure_integration.py:1018`,
`tests/rq/test_wbt_controlled_failure_integration.py:1088`,
`tests/rq/test_wbt_controlled_failure_integration.py:1145`, and
`tests/rq/test_wbt_controlled_failure_integration.py:1201`).

### Same-run containment, tail lifecycle, and failure paths

- A later same-run build depends on the still-active tail with
  `allow_failure=True`. Missing and terminal tails are replaced without a
  dependency; a nonterminal tail outside every valid execution location is
  rejected without changing root, queue, registry, or tail state
  (`wepppy/rq/project_rq.py:658`).
- The complete build-plus-abstraction mutation runs under one watershed
  directory-root lock whose TTL is the 43,200-second job timeout plus the
  300-second cleanup margin (`wepppy/rq/project_rq.py:1563`,
  `wepppy/rq/project_rq.py:1647`).
- The mutable child does not delete the tail while RQ still reports it active.
  Successful receipt cleanup and failed-worker cleanup are compare-and-delete,
  so an older tree cannot erase a newer reservation
  (`wepppy/rq/project_rq.py:796`,
  `wepppy/rq/project_rq.py:1786`,
  `wepppy/rq/rq_worker.py:243`).
- Controlled snapshot, policy-application, boundary-touch, and unexpected
  child failures cancel only the matching completion receipt. Cancellation
  removes the deferred registry entry, dependency set, and reverse dependency
  before marking the receipt canceled
  (`wepppy/rq/project_rq.py:239`,
  `wepppy/rq/project_rq.py:258`,
  `wepppy/rq/project_rq.py:1669`).
- Real Redis/RQ evidence covers both opposite-policy orders, controlled
  failure, sanitized stored failure, receipt cancellation, empty dependency
  residue, terminal stale-tail replacement, orphan rejection, and
  compare-delete isolation
  (`tests/rq/test_wbt_controlled_failure_integration.py:155`,
  `tests/rq/test_wbt_controlled_failure_integration.py:303`,
  `tests/rq/test_wbt_controlled_failure_integration.py:502`,
  `tests/rq/test_wbt_controlled_failure_integration.py:541`,
  `tests/rq/test_wbt_controlled_failure_integration.py:607`, and
  `tests/rq/test_wbt_controlled_failure_integration.py:1301`).

### Authorization and initiating-user snapshot provenance

- The RQ-engine route authenticates and authorizes run access before payload,
  project, or preference access. Denied access therefore cannot become a
  preference-existence oracle
  (`wepppy/microservices/rq_engine/watershed_routes.py:903`).
- Only an account-bearing `user` or `session` identity resolves an active
  account. Service/MCP and session-without-user flows remain config-only;
  malformed, unknown, inactive, or invalid stored account state fails closed
  (`wepppy/weppcloud/user_preferences.py:277`).
- The route creates an exact snapshot containing run ID, actor token class,
  actor user ID, config policy, effective policy, and source, validates it,
  and places it in private root metadata while passing only the bounded
  execution argument (`wepppy/weppcloud/user_preferences.py:303`,
  `wepppy/weppcloud/user_preferences.py:334`,
  `wepppy/microservices/rq_engine/watershed_routes.py:1006`,
  `wepppy/microservices/rq_engine/watershed_routes.py:1085`).
- The root validates the snapshot again and copies it into the stable child
  tree. RQ retry reuses the original IDs, argument, and actor snapshot rather
  than consulting a later preference value
  (`wepppy/rq/project_rq.py:1826`,
  `tests/rq/test_wbt_controlled_failure_integration.py:1201`).
- Negative route evidence proves denied access never calls the preference
  resolver and preference-resolution failure creates no job or grouped
  watershed mutation
  (`tests/microservices/test_rq_engine_watershed_routes.py:1202`,
  `tests/microservices/test_rq_engine_watershed_routes.py:1228`).

### Viewer-scoped Unitizer isolation

- Non-`Auto` presentation is a detached view with a copied instance dictionary
  and a new request-local preference map. Persistence, locking, preference,
  and inherited NoDb control mutations are rejected
  (`wepppy/weppcloud/user_preferences.py:412`).
- `Auto` returns the exact durable Unitizer. SI/English returns a detached
  read-only view, preserving existing callers' type and conversion surface
  (`wepppy/weppcloud/user_preferences.py:504`,
  `wepppy/weppcloud/user_preferences.py:518`).
- Concurrent PostgreSQL evidence for two users viewing the same project proves
  different presentation units, unchanged durable controller identity and
  preferences, byte-identical `unitizer.nodb`, unchanged modification time,
  and no lock artifacts
  (`tests/weppcloud/test_user_preferences_postgres.py:405`).

## Validation Evidence

| Gate | Result |
| --- | --- |
| Full Python suite, final frozen tree | **PASS — 5,721 passed, 58 skipped** |
| Focused affected suite | **PASS — 371 passed** |
| Independent Redis/RQ review subset | **PASS — 80 passed** |
| Frontend lint/tests | **PASS — 745 tests passed; lint green** |
| RQ dependency graph/catalog | **PASS** |
| Stub and test-stub gates | **PASS** |
| Test isolation gate | **PASS** |
| Changed-file broad-exception enforcement | **PASS, net -4** |
| `git diff --check HEAD --` | **PASS** |

The reviewer independently reran the 80-test Redis/RQ subset,
`wctl check-rq-graph`, changed-file broad-exception enforcement, and
`git diff --check`. The supplied focused, frontend, stub, isolation, and final
full-suite results were produced against the frozen shared-worktree state. The
final run reported 5,778 collected tests plus one collection skip, 5,721
passed, 58 skipped, and 1,023 warnings in 628.16 seconds.

## Recovery and Release Conditions

The recovery path remains durable and nondestructive:

- apply and rollback both stop enqueue surfaces, drain queues, verify idle
  workers, stop all changed web/worker consumers, and move them together to an
  exact reviewed commit before restart;
- if exact reconciliation fails, a nonterminal orphan appears, dependency
  residue remains, or same-run output becomes timing-dependent, stop affected
  enqueue surfaces, drain workers, and preserve the Redis tail, job hashes,
  registry membership, root links, logs, and error IDs before intervention;
- remove only a tail whose referenced job is verified missing or terminal;
  compare-and-delete is the normal cleanup authority;
- use the pre-reviewed forward application revert. Destructive schema
  downgrade or database restoration still requires separate operator
  authority; and
- record the restart, migration/canary output, cleanup proof, and any recovery
  action in the required post-action review.

These conditions are specified in
`docs/adrs/ADR-0033-user-defaults-and-wbt-boundary-policy.md:145` and
`docs/work-packages/20260729_user_preferences_wbt_boundary/artifacts/2026-07-30_contract_amendment_delineation_snapshot.md:343`.

## Release Decision

- **Coordinated local stack restart**: **APPROVED** for the exact frozen state.
- **Local acceptance mutation**: permitted only under the bounded contract
  canary and cleanup procedure.
- **Forest preflight/migration/canary**: not authorized by this artifact alone;
  it follows successful local acceptance and the required post-acceptance dual
  review.
- **Production rollout**: outside this review.

This reviewer changed only this review artifact. Test-scoped Redis/RQ keys were
created and cleaned by the focused test gate; no application database,
acceptance, Forest, or production mutation was performed.
