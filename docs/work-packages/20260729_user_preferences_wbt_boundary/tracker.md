# Tracker - Account User Preferences and WBT Boundary Policy

## Quick Status

**Timezone**: UTC

**Started**: 2026-07-30 04:10 UTC

**Current phase**: Forest healthy; post-action authority incident

**Last updated**: 2026-07-30 15:10 UTC

**Next milestone**: operator designation, reviewed corrected canary, dual review

**Security impact**: `high`

**Dedicated security review**:
`artifacts/2026-07-30_security_review.md`

**Hardening observation owner**: requesting operator with the WEPPcloud
maintainer.

**Hardening closure criterion**: 14 days after the Forest canary, close only
with zero reported exact DB-0/11/13 residue, uncorrelated cleanup failure, or
out-of-scope deletion. If the canary runs on 2026-07-30, review is due
2026-08-13 UTC.

## Task Board

### In Progress

- [ ] Obtain explicit operator reconfirmation and designation of the
  requesting-operator account plus a second pre-existing active account, then
  review and run a Forest-specific corrected canary.

### Ready

- None.

### Blocked

- Post-action closure is blocked pending explicit operator reconfirmation and
  account designation, a reviewed corrected canary, and renewed dual review.
  The healthy Forest release remains deployed.

### Done

- [x] Mapped current User/Profile, Unitizer, new-project override, WBT edge
  detection, typed error, migration, and contract surfaces
  (2026-07-30 04:10 UTC).
- [x] Recorded the operator's `Stop with an error` decision and Forest
  migration authority (2026-07-30 04:10 UTC).
- [x] Scaffolded SURF-14A package, active ExecPlan, contract decision, ADR, and
  security review artifact (2026-07-30 04:10 UTC).
- [x] Received independent governance and operations/security checkpoint FAIL
  reviews and retained both artifacts (2026-07-30 05:20 UTC).
- [x] Dispositioned authority, owner cross-links, legacy state, exact WBT
  cleanup, identity/ownership, creation inventory, async failure, concurrency,
  dual-head migration, and Forest containment findings in the normative
  contract (2026-07-30 05:30 UTC).
- [x] First re-review closed ten findings and retained GOV-02/07/08, SEC-03,
  and OPS-04; amended the field matrix, Cartesian precedence, canonical RQ
  polling schema, and exact bind-mount-safe Forest commands
  (2026-07-30 06:10 UTC).
- [x] Governance second re-review passed. Operations/security closed SEC-03
  and retained only OPS-04; added executable backup verification, enqueue
  quiesce, worker drain/graceful stop/post-stop registry evidence, and exact
  schema assertions (2026-07-30 06:35 UTC).
- [x] Operations/security final confirmation passed OPS-04; both independent
  checkpoint reviews now pass with no unresolved finding
  (2026-07-30 06:50 UTC).
- [x] Committed the reviewed documentation-only checkpoint as standalone
  ancestor `1b412d61a` (2026-07-30 06:55 UTC).
- [x] Implemented and focused-tested the typed model, merge migration,
  preferences service/page, exact creation precedence, and failure-atomic
  ownership for regular and HUC-fire creation (2026-07-30 07:30 UTC).
- [x] Implemented and focused-tested WBT warn/error behavior, deterministic
  edge diagnostics, readiness cleanup, controlled RQ failure, dependent
  cancellation,
  and sanitized aggregate jobinfo (2026-07-30 07:30 UTC).
- [x] Added and validated User Preferences and Channel Delineation Usersum
  guidance and rebuilt the generated search index (2026-07-30 07:30 UTC).
- [x] Passed the complete Python suite (5,643 passed, 58 skipped), frontend
  lint, and all 745 JavaScript tests before final-review remediation
  (2026-07-30 06:05 UTC).
- [x] Retained independent final-review FAIL artifacts and blocked Forest/E2E
  on two governance High/four Medium and four operations/security High/four
  Medium findings (2026-07-30 06:15 UTC).
- [x] Remediated creation disclosure and cleanup confinement/correlation,
  WBT stale readiness and exception identity, controlled RQ retention and
  dependent lifecycle, plus HUC service/MCP compatibility
  (2026-07-30 06:40 UTC).
- [x] Added real PostgreSQL concurrency/identity/ownership tests, disposable
  two-head PostgreSQL migration evidence, persisted NoDb snapshot coverage,
  and real Redis worker/tree/HTTP/retry coverage
  (2026-07-30 06:40 UTC).
- [x] Passed 243 focused tests, the post-remediation full Python suite (5,675
  passed, 58 skipped), frontend lint, 745 JavaScript tests, stubs, test-stub
  completeness, and package documentation lint (2026-07-30 07:10 UTC).
- [x] Repaired and passed the scoped isolation gate, restored the mixed local
  web/worker runtime, verified authenticated Profile/Preferences rendering,
  and recovered the affected RQ tree to 3/3 finished
  (2026-07-30 07:10 UTC).
- [x] Checked implementation commit `e861aae36` in an isolated worktree,
  regenerated its line-only RQ graph metadata, annotated the two displaced
  legacy broad-catch boundaries, and passed the graph, broad-exception, and
  68-test affected WBT/RQ gates (2026-07-30 07:15 UTC).
- [x] Retained immutable re-review FAIL artifacts: governance closed its
  Highs but left three Medium gaps; operations/security left one migration
  Medium and added one High for undefined existing-run preference authority
  (2026-07-30 07:35 UTC).
- [x] Diagnosed the operator's live job: the existing run persisted `warn`,
  found eight edge hillslopes, and finished despite the owner's current
  `error` preference; recorded the clarified expectation in a contract
  amendment (2026-07-30 07:40 UTC).
- [x] Proved an explicit-target PostgreSQL Alembic graph cycle from both
  parents through upgrade/downgrade/re-upgrade plus constraints,
  missing-row defaults, persistence, cascade, and cleanup
  (2026-07-30 07:40 UTC).
- [x] Retained the first delineation-amendment checkpoint FAIL reviews
  (governance: two High/three Medium; operations/security: two High/five
  Medium) without changing runtime code (2026-07-30 07:53 UTC).
- [x] Diagnosed the reverse live transition: `depleted-hyperlink` retained
  creation-time `error` after its owner selected `warn`; its root job failed on
  seven edge hillslopes. Repaired that exact run to persisted `warn`
  (2026-07-30 07:51 UTC).
- [x] Scope-reduced the first amendment to exact initiating-owner behavior and
  added
  singular owner/session binding, immutable config baseline, exact private RQ
  schema/redaction, cache/lock/readiness sequencing, and two-phase local
  acceptance review (2026-07-30 07:55 UTC). This owner-only interpretation was
  superseded by the user-context decision below.
- [x] Recorded the operator's superseding user-context decision: both
  preferences follow the authenticated user; non-Auto units are
  presentation-only and WBT is an initiating-user job snapshot
  (2026-07-30 08:15 UTC).
- [x] Passed both independent user-context checkpoint reviews and committed
  the exact documentation-only amendment as standalone ancestor `4d2ef5838`
  (2026-07-30 08:35 UTC).
- [x] Serialized each same-run WBT build-plus-abstraction mutation behind a
  persistent per-run tail, extended the watershed lock beyond the RQ timeout,
  retained abstraction as a nonmutating completion receipt, and guaranteed
  receipt plus root-link persistence before child activation
  (2026-07-30 10:20 UTC).
- [x] Added and passed both-order PostgreSQL read/save tests, simultaneous
  two-user byte-stable Unitizer views, an account-identity matrix, a production
  Unitizer adoption inventory, and real-Redis opposite-policy ordering with
  terminal receipt/dependency cleanup (2026-07-30 10:20 UTC).
- [x] Retained both independent queue-sequencing checkpoint FAIL artifacts;
  rejected the unfenced admission lease and saved-but-never-activated orphan
  window, then revised the contract to atomic optimistic Redis admission with
  full parameter provenance and rollback (2026-07-30 11:05 UTC).
- [x] Obtained final governance and operations/security PASS reviews and
  committed the exact atomic-admission contract as standalone ancestor
  `b1f1f99c8` (2026-07-30 11:05 UTC).
- [x] Implemented one-transaction admission, bounded WATCH retry, exact-tree
  idempotency and ambiguous-response reconciliation; passed 205 focused tests
  plus pre/post-EXEC fault injection, actual RQ retry, and policy-apply cleanup
  evidence (2026-07-30 11:20 UTC).
- [x] Implemented request-local viewing-user units without durable Unitizer
  mutation, removed account defaults from creation, and added sanitized
  preference-resolution failures across the contracted report inventory
  (2026-07-30 09:25 UTC).
- [x] Implemented initiating-user WBT private snapshots through route, root,
  child, and execution-only Watershed policy with public actor/snapshot
  redaction (2026-07-30 09:25 UTC).
- [x] Passed the focused creation, Profile, PostgreSQL two-user Unitizer,
  report inventory, WBT NoDb/RQ, real-Redis failure-tree, and jobinfo
  selections (2026-07-30 09:25 UTC).
- [x] Closed atomic root-retry, child-tail timing, intermediate-queue,
  orphan-tail, and exact dependency-residue findings; passed the 371-test
  affected suite and regenerated the RQ graph (2026-07-30 12:05 UTC).
- [x] Passed final source-freeze validation: 5,721 Python tests passed with
  58 skipped, frontend lint and 745 JavaScript tests passed, and stub,
  test-stub, isolation, broad-exception, docs, RQ graph, and diff gates were
  clean (2026-07-30 12:20 UTC).
- [x] Received independent source-freeze governance and operations/security
  PASS reviews with zero unresolved findings (2026-07-30 12:25 UTC).
- [x] Restarted the complete local stack and passed a real two-user,
  same-project canary for SI/English/Auto presentation, byte-stable Unitizer,
  `error`/`warn` WBT snapshots, redaction, durable-field stability, exact
  cleanup, and healthy queues/workers (2026-07-30 12:50 UTC).
- [x] Corrected real Create-page token subject binding from `fs_uniquifier` to
  the numeric User ID required by fail-closed ownership resolution; the exact
  regression plus project-route suite pass (2026-07-30 12:50 UTC).
- [x] Found and removed exact DB-0/11/13 state for six disposable acceptance
  runs, then verified those IDs absent across DB 0/2/9/11/13/14/15
  (2026-07-30 14:05 UTC).
- [x] Scope-reduced failed-create recovery to the existing public error
  envelope and added strict DB-0/11/13 plus filesystem cleanup postconditions
  with correlated internal `error_id`/run-ID diagnostics
  (2026-07-30 14:05 UTC).
- [x] Repeated the local two-user canary on Users 341/342 and run
  `pain-free-prospectus`; all functional and strict Redis/SQL cleanup checks
  passed. The harness reported NFS cleanup pending, and exact directory cleanup
  completed after restarting only the two handle-owning services
  (2026-07-30 14:20 UTC).
- [x] Passed frozen-source validation: 5,732 Python tests with 58 skipped;
  frontend lint and 104 suites/745 tests; three stubtests; test-stub, RQ graph,
  broad-exception, documentation, and vulture gates; plus two-seed and
  per-file isolation for the remediation modules (2026-07-30 14:40 UTC).
- [x] Received final governance/correctness and operations/security PASS
  reviews for exact fingerprint `4aa271981f...`, both with zero findings
  (2026-07-30 14:50 UTC).
- [x] Committed and pushed release `363ab8ac3`; independently reviewed,
  published, and verified rollback `0517bb8de` at the immutable dedicated
  rollback ref (2026-07-30 15:30 UTC).
- [x] Began read-only Forest preflight and proved the active workspace and
  `ssh forest` are the same host/index. Release and migration heads are
  current, queues are empty, and all ten workers are idle; stopped before
  mutation because unrelated work makes the checkout dirty
  (2026-07-30 15:40 UTC).
- [x] Committed and pushed the shared Command Bar/Pure UI work, independently
  approved replacement rollback `d5944a3dc`, and published its immutable ref
  while retaining the earlier rollback ref unchanged
  (2026-07-30 15:02 UTC).
- [x] Created and validated a fresh Forest backup, quiesced enqueue surfaces,
  proved empty queues and idle workers, stopped workers gracefully, verified
  the merge head, four constraints, and unchanged User count, then restarted
  the coordinated service set (2026-07-30 15:06 UTC).
- [x] Passed the Forest two-user canary for request-local units and
  initiating-user WBT behavior. Exact SQL/Redis cleanup passed; known NFS
  handles cleared after stopping only their two owning services, and the
  empty receipt-bound directory was removed with `rmdir`. Final services,
  queues, workers, schema, counts, and release HEAD are healthy
  (2026-07-30 15:10 UTC).
- [x] Operations/security independently verified the healthy technical state
  but rejected closure with High finding OPS-PA-01: Forest identity procedure
  required two pre-existing designated accounts, while the local harness
  created and deleted disposable Users 361/362. Exact cleanup does not cure
  the authority deviation (2026-07-30 15:13 UTC).
- [x] Governance confirmed OPS-PA-01 as High, superseded its earlier PASS,
  found the technical exposure contained, and required a corrected canary
  using two explicitly designated pre-existing active accounts. Rollback is
  not warranted because it cannot cure the historical authority deviation
  (2026-07-30 15:16 UTC).

## Decisions

### 2026-07-30 04:10 UTC: Use typed account persistence

**Decision**: Store one constrained `user_preferences` row per User rather than
cookies, JSON, generic key/value state, or run-scoped NoDb.

**Rationale**: The values are account-scoped, security-sensitive defaults with
small stable enums. Typed columns and database constraints make migration,
validation, audit, and compatibility behavior explicit.

### 2026-07-30 04:10 UTC: Snapshot preferences into new runs (superseded)

**Historical decision**: Resolve explicit project input, then account
preference, then configuration before `Ron` initialization and persist the
effective run state.

**Superseded 2026-07-30 08:15 UTC**: Account units are request-local
presentation and never parameterize project creation. WBT behavior is resolved
from the initiating user and snapshotted into that submission without
persisting account-derived project policy.

### 2026-07-30 08:15 UTC: Preferences follow the active user

**Decision**: Non-Auto units follow the authenticated viewing user through an
immutable presentation overlay. Non-Auto WBT behavior follows the
authenticated initiating user through a validated job snapshot.

**Rationale**: A preference belongs to the person using the project, not the
project owner or the durable project. Two authorized users must be able to use
the same byte-stable project with different presentation and submission
choices.

### 2026-07-30 04:10 UTC: Label failure as Stop with an error

**Decision**: The UI uses `Stop with an error`; the stored token is `error`.

**Rationale**: This describes a controlled typed failure and avoids presenting
an intentional guard as a process crash.

### 2026-07-30 04:10 UTC: Preserve warning compatibility

**Decision**: Account preferences default to `config`; the WBT config option
defaults to `warn`.

**Rationale**: Existing users and configs retain current behavior while a
config or explicit user preference can choose fail-closed handling.

## Risks

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| One user's preference leaks into project or another user | High | Request-local Unitizer view, immutable WBT job snapshot, and no durable account-derived project policy | Mitigated and source-freeze tested |
| Explicit project unit selection is overwritten | High | Keep project creation account-independent; apply account units only to a request-local presentation view | Mitigated and source-freeze tested |
| DB/preference lookup failure silently falls back | High | Fail the authorized view/submission with a sanitized correlated error before project or queue mutation | Mitigated and source-freeze tested |
| Invalid enum bypasses UI | High | Exact route/service enums plus DB check constraints | Mitigated and focused-tested |
| Boundary error leaves stale ready output | High | Invalidate readiness and canonical clipped output before typed failure | Mitigated and focused-tested |
| Migration deploys before compatible code | High | Contract, test, review, and Forest preflight gates | Open |
| Concurrent preference saves lose one field | Medium | Validate complete form, lock existing row, retry first-insert race, and update both fields in one transaction | Mitigated and PostgreSQL-tested |
| Authenticated creation leaves an ownerless/public run | High | Historical creation hardening remains covered; the superseding preference contract makes no creation-time account lookup or mutation | Mitigated and PostgreSQL-tested |
| Public job status discloses an internal traceback | High | Sanitize retained RQ state and public tree/HTTP payload; preserve structured correlated diagnostics | Mitigated and real-Redis-tested |
| Dual Alembic heads produce an unsafe Forest rollout | High | Merge revision over both heads, representative PostgreSQL cycle, schema-first coordinated restart | Mitigated locally; Forest pending |
| Initiating user gets stale or another user's WBT behavior | High | Synchronous initiating-user resolution, exact private RQ snapshot, and no durable account-derived project policy | Mitigated and source-freeze tested |
| Failed create/canary leaves Redis or filesystem residue | High | Close run instances, strictly purge and verify DB 0/11/13, remove only the canonical run directory, and correlate any failure by `error_id` | Remediation validation in progress |

## Verification Checklist

### Contract and review

- [x] Original checkpoint reviews passed and its documentation-only ancestor
  is `1b412d61a`; its creation/owner lifetime interpretation is superseded.
- [x] ADR-0033's original persistence/configuration decision is accepted with
  complete provenance.
- [x] Post-remediation governance/correctness and operations/security reviews
  pass with no unresolved findings for exact fingerprint `4aa271981f...`.
- [x] User-context amendment has two independent checkpoint approvals,
  findings disposition, and a standalone ancestor.

### Backend and migration

- [x] Model, constraints, migration upgrade/downgrade/upgrade, missing-row
  compatibility, and concurrent update tests pass.
- [x] GET/POST login, CSRF, exact enum, atomic save, PRG, hostile-value, and
  prefix-aware link tests pass.
- [x] Creation precedence, failure atomicity, anonymous, token identity,
  explicit input, existing run, shared run, and fork tests pass.

### WBT behavior

- [x] Config parser and persisted Watershed enum tests pass.
- [x] Synthetic no-edge, warn, error, invalid-value, actionable message,
  stale-readiness, and deterministic edge-ID tests pass.
- [x] rq-engine response preserves the canonical typed error contract.

### Broad and deployment

- [x] Frozen-source `wctl run-pytest tests --maxfail=1` passes
  (5,732 passed, 58 skipped).
- [x] Post-remediation frontend lint and all 745 JavaScript tests pass.
- [x] Stub, test-stub, broad-exception, docs, and RQ graph gates pass.
- [x] Exact remediation-module isolation passes seeds 42 and 123 plus isolated
  per-file runs; the earlier complete-source isolation gate also passed.
- [x] Local stack E2E proves two distinct unit views and `error`/`warn` WBT
  behavior for two users on one byte-stable project.
- [x] Forest preflight records current migration head and database backup
  readiness.
- [x] Forest migration, schema verification, service restart if required, and
  authenticated two-user same-project canary pass.
- [x] Implemented the contract-first User Preferences auto-save interaction,
  accessible save/error/retry feedback, increased field spacing, current
  guidance, and the repaired WBT Usersum runtime-catalog entry
  (2026-07-30 15:38 UTC).
- [x] Restored salient save feedback with the standard informational and
  success alert treatments while retaining polite live announcements
  (2026-07-30 15:40 UTC).

## Progress Notes

### 2026-07-30 15:40 UTC: Salient save confirmation

The muted status line was too easy to miss. Saving now reveals the standard
informational alert, and confirmation promotes the same live region to the
standard success alert with `Preferences saved.` Error and retry behavior are
unchanged. Focused template tests, frontend lint, and all 105 frontend suites
with 749 tests pass.

### 2026-07-30 15:38 UTC: Preference auto-save and Usersum repair

Both preference selectors now save the complete form immediately on change.
Requests are serialized so a later change is replayed after an active request,
and the page exposes polite saving/success status plus an assertive error and
retry action. The ordinary Save button remains only as a `noscript` fallback.
The stale explanatory copy and spacing were corrected.

The WBT guide source and manifest entry already existed; its 404 came from a
stale generated runtime index. The index was rebuilt and the exact legacy URL
now has route regression coverage. The complete WEPPcloud test selection
passes with 1,253 tests, and the frontend, documentation, Usersum, test-stub,
broad-exception, and diff gates pass. OPS-PA-01 and its corrected Forest
canary remain independently open.

### 2026-07-30 04:10 UTC: Scaffold

The package was registered as SURF-14A and scoped across the verified Profile,
Unitizer, and Channel Delineation owners. No production implementation or
database migration was performed. The shared worktree already contained
unrelated Pure UI and Command Bar changes; those remain outside this package.

Next, obtain the two required read-only checkpoint reviews, disposition every
finding, and commit only the documentation checkpoint before touching
implementation files.

### 2026-07-30 05:30 UTC: Initial checkpoint review disposition

Both independent reviewers rejected the scaffold revision. Their findings were
accepted and retained under `artifacts/`. The amended contract now records the
operator's execution approval, every affected owner and `Ron(...)` path,
identity and ownership fail-closed rules, legacy field hydration, exact WBT
state/asynchronous transitions, complete-form concurrency, the two-head
Alembic merge, and schema-first Forest containment. No implementation file has
changed. Re-review remains the blocking next step.

### 2026-07-30 06:10 UTC: First re-review

Both reviewers narrowed the remaining checkpoint gaps. The second amendment
round makes the warning/status payload literal, adds the bounded jobinfo schema
to the canonical RQ response contract, factors precedence into a tested
Cartesian product, corrects the DOM-05 field matrix, and stops every
bind-mounted consumer before Forest checkout/migration. Second re-review is
pending; implementation remains untouched and blocked.

### 2026-07-30 06:35 UTC: Second re-review

Governance passed. Operations/security accepted the async RQ contract and
retained only deployment quiescence. The plan now creates and validates a
fresh backup, blocks all enqueue surfaces, proves default/batch queues drained,
stops idle workers gracefully, re-checks registries, and asserts User count
plus all four named constraints before restart. Final OPS-04 confirmation is
pending.

### 2026-07-30 06:40 UTC: Final-review remediation

Both independent final reviews rejected the first implementation. All
reported implementation controls were remediated locally, and durable
PostgreSQL/Redis evidence was added under
`artifacts/2026-07-30_local_postgresql_redis_evidence.md`. The focused
post-remediation selection reached 242 passes with one test-only structured
log field assertion failure; that logging field was added and its focused
rerun passed. Broad gates and immutable-revision re-review remain pending, so
Forest and acceptance E2E remain blocked.
