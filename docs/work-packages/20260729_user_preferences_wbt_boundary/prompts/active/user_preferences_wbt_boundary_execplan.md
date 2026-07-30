# Add user-context units and fail-closed WBT boundary handling

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current while it
is active.

## Purpose / Big Picture

An authenticated user can open User Preferences from Profile and select
their presentation units plus what happens when their WBT delineation reaches
the DEM boundary. SI/English follows the viewing user without changing project
Unitizer state. Each account-bearing submission snapshots the initiating
user's current boundary choice before enqueue without persisting it as project
policy. Choosing `Stop with an error` prevents a clipped WBT watershed from
appearing successful and tells the user to select a different outlet or
enlarge the project extent.

## Progress

- [x] (2026-07-30 04:10 UTC) Mapped the current account, Profile, run-scoped
  Unitizer, creation override, WBT edge detector, typed error, configuration,
  and migration surfaces.
- [x] (2026-07-30 04:10 UTC) Scaffolded SURF-14A and recorded the operator's
  UI-label decision and Forest migration authority.
- [x] (2026-07-30 05:20 UTC) Completed two independent initial checkpoint
  reviews; both rejected the scaffold and implementation remained blocked.
- [x] (2026-07-30 05:30 UTC) Dispositioned all authority, ownership, identity,
  creation inventory, legacy state, error-state, asynchronous RQ, concurrency,
  migration-topology, and Forest-containment findings in the contract.
- [x] (2026-07-30 06:10 UTC) Completed first re-review and amended its five
  remaining findings: canonical field matrix, Cartesian precedence, exact
  warning/jobinfo contract, canonical RQ schema, and bind-mount-contained
  Forest commands.
- [x] (2026-07-30 06:35 UTC) Governance passed. The second operations review
  closed SEC-03 and retained OPS-04; added a verified one-off backup, enqueue
  quiesce, queue/worker drain, graceful stop, post-stop registry, and exact
  schema/User-count assertions.
- [x] (2026-07-30 06:50 UTC) Completed both independent checkpoint reviews;
  governance and operations/security passed with no unresolved finding.
- [x] (2026-07-30 06:55 UTC) Committed the dual-reviewed documentation-only
  checkpoint as standalone ancestor `1b412d61a`.
- [x] (2026-07-30 07:30 UTC) Implemented and focused-tested account
  persistence, merge migration, Profile link, and User Preferences GET/POST.
- [x] (2026-07-30 07:30 UTC) Implemented and focused-tested exact creation
  precedence, fail-closed identity lookup, atomic ownership, and compensating
  cleanup for regular and HUC-fire creation.
- [x] (2026-07-30 07:30 UTC) Implemented and focused-tested WBT boundary
  warning/error behavior, deterministic diagnostics, stale readiness cleanup,
  dependent cancellation, and sanitized aggregate jobinfo.
- [x] (2026-07-30 06:05 UTC) Completed the initial broad validation: the full
  Python suite passed with 5,643 tests and 58 skips; frontend lint and all 745
  JavaScript tests passed. This evidence predates final-review remediation and
  does not replace the pending final gate rerun.
- [x] (2026-07-30 06:15 UTC) Retained both independent final-review FAIL
  artifacts. Governance reported two High and four Medium findings;
  operations/security reported four High and four Medium findings. Forest and
  acceptance E2E remained blocked.
- [x] (2026-07-30 06:40 UTC) Remediated response disclosure, exact-provenance
  SQL cleanup, symlink-resistant filesystem cleanup, cleanup correlation,
  service/MCP compatibility, stale WBT diagnostics/readiness, canonical
  exception identity, controlled RQ retention, and deferred dependency
  lifecycle findings.
- [x] (2026-07-30 06:40 UTC) Added real PostgreSQL model/concurrency/identity/
  ownership evidence, a disposable two-head PostgreSQL migration cycle,
  persisted Ron snapshot evidence, and a real Redis/worker/root/HTTP/retry
  lifecycle test.
- [x] (2026-07-30 07:10 UTC) Passed the post-remediation focused selection
  (243 tests), full Python suite (5,675 passed, 58 skipped), frontend lint,
  all 745 JavaScript tests, stubs, test-stub completeness, and documentation
  lint.
- [x] (2026-07-30 07:10 UTC) Corrected the isolation wrapper's virtualenv and
  Pytest 9 recorder defects; two package-order runs and all four per-file runs
  pass. Restarted the locally version-skewed web/workers, verified authenticated
  Profile/Preferences rendering, and recovered the one affected RQ tree to
  3/3 finished.
- [x] (2026-07-30 07:15 UTC) Committed implementation checkpoint
  `e861aae36`, then used an isolated worktree to expose and repair stale
  line-only RQ graph metadata and relocated legacy broad-catch suppressions;
  the graph, broad-exception gate, and 68 affected WBT/RQ tests now pass.
- [x] (2026-07-30 07:35 UTC) Retained immutable governance and
  operations/security re-review FAIL artifacts. Governance left three Medium
  gaps; operations/security left one migration Medium and found one new High
  from live existing-run behavior.
- [x] (2026-07-30 07:40 UTC) Diagnosed root job
  `0734dcbc-dd03-4c28-98f4-cb42ea64170c`: its run was created before the
  preference page was operational, persisted `warn`, found eight edge
  hillslopes, and finished despite the owner's later `error` preference.
- [x] (2026-07-30 07:51 UTC) Diagnosed the reverse live case: run
  `depleted-hyperlink` persisted creation-time `error`, the owner changed to
  `warn`, and root job `4b81f2cb-0b6f-4743-a152-5e7f9b658541` failed on seven
  edge hillslopes. Repaired that exact run to persisted `warn` for retry.
- [x] (2026-07-30 07:55 UTC) Retained the first amendment checkpoint FAIL
  reviews and scope-reduced the next revision to owner-initiated behavior with
  exact owner/session binding, private snapshot schema, immutable config
  baseline, and failure-atomic NoDb ordering.
- [x] (2026-07-30 08:15 UTC) Recorded the operator's superseding decision that
  both preferences follow the authenticated user, with request-local
  nonmutating units and initiating-user WBT job input.
- [x] (2026-07-30 08:35 UTC) Passed the independent user-context governance
  and operations/security reviews with no finding and committed their exact
  documentation-only checkpoint as standalone ancestor `4d2ef5838`.
- [x] (2026-07-30 09:25 UTC) Removed account preferences from durable project
  creation, implemented immutable viewing-user Unitizer overlays, adopted
  them across the contracted run/report inventory, and added sanitized
  fail-closed preference errors.
- [x] (2026-07-30 09:25 UTC) Implemented exact initiating-user WBT root/child
  snapshots, immutable configuration baselines, execution-only worker policy,
  open-jobinfo redaction, and compatibility paths for non-account-bearing and
  batch submissions.
- [x] (2026-07-30 09:25 UTC) Passed focused creation, PostgreSQL two-user
  no-mutation, Profile, report, WBT NoDb, route, RQ, real-Redis controlled
  failure, and public jobinfo selections (more than 500 collected tests
  across the retained focused runs).
- [x] (2026-07-30 10:20 UTC) Closed same-run policy leakage and job-tree races:
  one serialized build-plus-abstraction child now holds the watershed lock,
  its nonmutating receipt and root links exist before activation, and a
  persistent compare-delete tail orders fresh submissions after either
  predecessor outcome.
- [x] (2026-07-30 10:20 UTC) Added both-order PostgreSQL read/save
  serialization, simultaneous two-user Unitizer presentation, production
  adoption inventory, exact identity fallback, pre-activation receipt/root
  linkage, and real-Redis same-run `error`/`warn` order evidence. The latest
  focused runs passed 138 and 44 tests respectively.
- [x] (2026-07-30 11:05 UTC) Retained independent queue-sequencing checkpoint
  FAIL artifacts. Both rejected the leased multi-step admission because a
  hard interruption could orphan a saved non-runnable child; governance also
  required complete queue parameter provenance and rollback.
- [x] (2026-07-30 11:05 UTC) Obtained final governance and
  operations/security PASS reviews with no finding and committed the exact
  atomic Redis admission contract as standalone ancestor `b1f1f99c8`.
- [x] (2026-07-30 11:20 UTC) Replaced the leased multi-step admission with one
  watched Redis transaction. Added bounded conflict retry, exact-tree
  idempotency, ambiguous-response reconciliation, active/missing/terminal tail
  handling, and atomic root/job/dependency/registry/tail persistence.
- [x] (2026-07-30 11:20 UTC) Passed 205 focused preference, PostgreSQL,
  Profile, Unitizer, WBT route/NoDb/RQ, and real-Redis tests. Added fault
  injection before/after `EXEC`, conflict exhaustion, actual root RQ retry,
  stored-invalid preference, unauthorized lookup ordering, and terminal policy
  apply-failure cleanup evidence.
- [x] (2026-07-30 12:05 UTC) Closed final-review atomic-admission findings:
  root WATCH conflicts reconcile a competing exact commit; live tails require
  queued/intermediate/deferred/started registry membership; exact replay
  rejects stale dependency residue; success receipts and post-terminal worker
  failure handling compare-delete only their own current tail.
- [x] (2026-07-30 12:20 UTC) Passed the final source-freeze validation:
  371 affected tests; the full Python suite with 5,721 passed and 58 skipped;
  frontend lint and all 745 JavaScript tests; stubs, test-stub completeness,
  isolation, RQ graph, broad-exception, documentation, and diff gates.
- [x] (2026-07-30 12:25 UTC) Received independent source-freeze governance
  and operations/security PASS reviews with zero unresolved findings.
- [x] (2026-07-30 12:50 UTC) Preserved the initial post-acceptance FAIL
  reviews. They rejected incomplete cleanup, nonnumeric Create-subject
  fallback, missing fallback rows, and stale source-freeze evidence.
- [x] (2026-07-30 13:00 UTC) Removed the email-subject fallback and hardened
  the canary's incremental job, session, access-log, count, and cleanup
  receipts. A proposed public failed-cleanup receipt was rejected during
  governance review and removed before release.
- [x] (2026-07-30 13:10 UTC) Repeated the two-user canary on disposable Users
  312/313 and run `inflammatory-bilberry`: distinct SI/English presentation,
  Auto and accountless project units, user `error`/`warn`, Auto/config and
  service WBT fallback, private redaction, byte-stable Unitizer, and unchanged
  durable WBT fields all passed. Exact SQL/Redis cleanup passed; the operator
  completed the reported NFS directory cleanup after restarting only the two
  handle-owning services.
- [x] (2026-07-30 13:25 UTC) Passed the corrected source's full Python suite
  with 5,727 passed and 58 skipped, plus affected stubtest, stub completeness,
  RQ graph, documentation, broad-exception, and diff checks.
- [x] (2026-07-30 13:35 UTC) Fresh ops review found six exact stale DB-11
  working-directory cache keys across acceptance attempts. Deleted only those
  named keys, verified them absent, and added exact WD-cache deletion and
  assertion to the harness.
- [x] (2026-07-30 14:05 UTC) Verified the same six disposable run IDs absent
  from Redis DB 0/2/9/11/13/14/15. Expanded the product cleanup boundary to
  close run instances, strictly purge and verify DB 0/11/13, preserve the
  existing public error envelope, and correlate cleanup failures internally by
  `error_id` and run ID.
- [x] (2026-07-30 14:20 UTC) Repeated the local two-user canary with exact
  Users 341/342 and run `pain-free-prospectus`. Functional, redaction,
  byte-stability, SQL, and Redis postconditions passed. The harness emitted a
  structured cleanup-pending receipt for NFS-held files; exact directory
  cleanup completed after restarting only WEPPcloud and rq-engine, and both
  workers returned healthy.
- [x] (2026-07-30 14:40 UTC) Passed frozen-source validation: 5,732 Python
  tests with 58 skipped; frontend lint and 104 suites/745 tests; three
  stubtests; test-stub, RQ graph, broad-exception, documentation, and vulture
  gates; and exact two-seed plus per-file isolation for the remediation
  modules.
- [x] (2026-07-30 14:50 UTC) Received final governance/correctness and
  operations/security PASS reviews for exact fingerprint `4aa271981f...`,
  both with zero findings.
- [ ] Apply and validate the authorized Forest migration and canary.

## Surprises & Discoveries

- Observation: `Unitizer` preferences are currently run-scoped, not
  account-scoped.
  Evidence: `wepppy/nodb/unitizer.py` persists `unitizer.nodb` under each run.

- Observation: new-project creation already supports an explicit
  `unitizer:is_english` override through the configuration query.
  Evidence: `interfaces.htm` leaves the value blank normally and supplies
  `true`/`false` only after an explicit unit choice; `project_routes.py`
  serializes non-empty overrides before constructing `Ron`.

- Observation: WBT already records hillslope identifiers touching raster edges
  immediately after subcatchment delineation, but does not enforce a policy.
  Evidence: `Watershed.build_subcatchments()` calls
  `identify_edge_hillslopes()`, whose support function reads all four raster
  edges and returns positive identifiers.

- Observation: the rq-engine already handles
  `WatershedBoundaryTouchesEdgeError`.
  Evidence: `watershed_routes.py` has a dedicated exception branch, so this
  package can preserve the typed response contract instead of inventing an
  error envelope.

- Observation: the existing exception catch is enqueue-time, while real WBT
  edge detection fails asynchronously in the subcatchment child job.
  Evidence: the operations/security review traced
  `watershed_routes.py` to `project_rq.py`; the contract now governs the actual
  child/dependency/root and sanitized public-status lifecycle.

- Observation: Alembic has two heads rather than one.
  Evidence: repository revisions `7b3c068e7a1d` and `b7d9c3e2f1a4`; the new
  preference revision must merge both.

- Observation: Alembic reports an ambiguous walk for a relative downgrade
  directly from an unlabeled two-parent merge revision.
  Evidence: local `flask db downgrade -- -1` rejected the walk. The migration
  body therefore has a disposable upgrade/downgrade/upgrade test, while local
  PostgreSQL upgrade and exact schema introspection validate the real dialect.

- Observation: the original repository migration history cannot bootstrap an
  empty PostgreSQL database because its first revision alters a preexisting
  `user` table.
  Evidence: disposable `flask db upgrade` failed at revision `28e48afd0090`
  with `relation "user" does not exist`. The retained migration evidence uses
  a representative application schema stamped at both real merge parents.

- Observation: `wctl check-test-isolation` previously produced five identical
  internal failures followed by a false clean result.
  Evidence: the wrapper selected system Python without pytest; after selecting
  `/opt/venv/bin/python`, the recorder accessed an optional Pytest 9
  `wasxfail` field unconditionally. Both tooling defects now have regression
  coverage and the scoped gate is genuinely clean.

- Observation: the generated RQ dependency catalog includes source line
  numbers, and the broad-exception allowlist is also line-sensitive.
  Evidence: the isolated `e861aae36` release check found no dependency-edge
  change but reported seven stale line references and two preexisting boundary
  catches displaced by this package. Regeneration plus explicit inline
  boundary suppressions restored both gates without changing runtime behavior.

- Observation: the original new-run-only WBT snapshot does not meet the
  operator's clarified existing-run expectation.
  Evidence: root job `0734dcbc-dd03-4c28-98f4-cb42ea64170c` and both children
  finished after finding eight edge hillslopes because
  `rock-ribbed-triplicate` persisted `warn`; the active owner preference was
  `error`, and the operator explicitly said the run should stop.

- Observation: an explicit Alembic merge-parent target removes the ambiguity
  seen with relative `-1`.
  Evidence: a fresh disposable representative PostgreSQL database completed
  both parents -> `c91f6b2a4d7e` -> explicit `7b3c068e7a1d` (restoring both
  parents) -> `c91f6b2a4d7e`, then proved constraints, missing-row defaults,
  persistence, cascade, and teardown.

- Observation: several report tests patched a route-local `Unitizer` symbol
  and therefore could not exercise the new viewing-user resolver.
  Evidence: the first report-inventory run failed at fixture setup after the
  durable imports were removed. Updating those fixtures to patch
  `resolve_unitizer_presentation` made all 83 affected report tests pass and
  now verifies the actual integration seam.

- Observation: a directory-root lock around only subcatchment construction
  still allowed another submission to replace shared Watershed state before
  abstraction.
  Evidence: forced opposite-policy same-run scheduling showed the mutable
  lifetime must include abstraction and must be ordered before queue execution.

- Observation: enqueueing the abstraction receipt after activating its build
  has a failure-registration race, and activating either child before saving
  root links has a traceability race.
  Evidence: independent operations/security review identified both
  interleavings. The first remediation pre-registered a dormant build and
  receipt before activation; the atomic-admission revision below supersedes
  that multi-step sequence while preserving its ordering guarantees.

- Observation: pre-registering a dormant child under a time-limited admission
  mutex still has a hard-interruption orphan window.
  Evidence: both independent queue-sequencing checkpoint reviews rejected the
  design. The revised contract makes tree persistence, dependencies, root
  links, tail replacement, and queued/deferred membership one optimistic
  Redis transaction with no pre-commit durable state.

- Observation: RQ 1.16 exposes `Job.dependency_ids` as Redis job keys rather
  than plain IDs, while the dependency sets themselves contain plain IDs.
  Evidence: ambiguous-response reconciliation initially rejected a correctly
  committed receipt. Reading and normalizing the canonical dependency set now
  makes exact-tree validation agree with RQ's persisted representation.

## Decision Log

- Decision: Serialize build plus abstraction as one mutable child under one
  watershed directory-root lock. Preserve the historical abstraction node as
  a nonmutating receipt, register it and both root links before activation,
  and order fresh same-run submissions with a persistent compare-delete tail.
  Rationale: per-user WBT policy is safe only when submissions cannot observe
  each other's intermediate NoDb/cache state; pre-registration guarantees a
  failing child has a receipt to cancel and a durable public root trace.
  Date/Author: 2026-07-30 / Codex, following independent operations/security
  race analysis.

- Superseded decision: Use a 30-second Redis admission mutex, save a dormant
  mutable child, register its receipt/root links, and activate it afterward.
  Rationale: this closed execution races but not lease expiry or host loss
  between save and activation.
  Date/Author: 2026-07-30 / Codex; rejected by both independent checkpoint
  reviewers.

- Decision: Admit the entire tree with one optimistic Redis transaction and a
  persistent watched tail, retrying conflicts at most five times.
  Rationale: `MULTI`/`EXEC` makes a crash pre-commit/no-state or
  post-commit/complete-tree, while the watched tail serializes concurrent
  admissions without an unfenced lease.
  Date/Author: 2026-07-30 / Codex, pending independent checkpoint approval.

- Decision: Use canonical tokens `config|si|english` and
  `config|warn|error`.
  Rationale: short stable values separate storage/API identity from labels and
  admit exact validation.
  Date/Author: 2026-07-30 / requesting operator and Codex.

- Decision: Use `Stop with an error` as the user-visible boundary choice.
  Rationale: the behavior is an intentional typed guard, not an uncontrolled
  crash.
  Date/Author: 2026-07-30 / requesting operator.

- Superseded decision: Use explicit creation input > account preference >
  project config.
  Rationale: this was the original creation-time interpretation.
  Date/Author: 2026-07-30 / proposed by Codex and approved by the requesting
  operator through the instruction to execute this documented package.

- Superseded decision: Apply account preferences only when creating a new
  project.
  Rationale: existing/shared runs and asynchronous jobs must not depend on
  mutable viewer profile state. Forks preserve the source run.
  Date/Author: 2026-07-30 / requesting operator and Codex.
  Superseded on 2026-07-30 for both fields by the operator's explicit
  user-context and nonmutating-unit clarification.

- Decision: Run the schema migration on Forest only after local tests and final
  reviews.
  Rationale: the operator authorized Forest migration, while staged deployment
  keeps incompatible application/schema states out of the canary environment.
  Date/Author: 2026-07-30 / requesting operator and Codex.

- Superseded decision: Resolve WBT boundary preference from the initiating run
  owner.
  Rationale: the operator demonstrated both `warn -> error` and
  `error -> warn` on owned runs. Restricting lookup to an initiating actor who
  exactly matches `Run.owner_id` avoids unapproved cross-user behavior.
  Date/Author: 2026-07-30 / Codex draft; superseded by the requesting
  operator's explicit "track the user, not the owner" clarification.

- Decision: Resolve both fields from the authenticated viewing/initiating
  User, independent of run ownership.
  Rationale: the operator explicitly stated that these are user preferences.
  Unit choice is a request-local presentation overlay; WBT choice is an
  enqueue-time action snapshot.
  Date/Author: 2026-07-30 / requesting operator and Codex.

- Decision: Snapshot the bounded initiating-user WBT policy before enqueue and
  pass it unchanged through RQ without durable account-derived project policy.
  Rationale: worker-time database lookup would make preference edits and
  retries timing-dependent.
  Date/Author: 2026-07-30 / Codex; pending independent checkpoint approval.

## Outcomes & Retrospective

The original creation-time implementation and remediation pass completed but
is now superseded by the user-context decision. Real PostgreSQL and
Redis evidence is retained in
`artifacts/2026-07-30_local_postgresql_redis_evidence.md`; local restart and
incident recovery evidence is retained in
`artifacts/2026-07-30_local_runtime_smoke.md`. The post-remediation focused
selection passed 243 tests, the complete Python suite passed 5,675 tests with
58 skips, frontend lint and all 745 JavaScript tests passed, both stubs and
test-stub completeness passed, package docs passed, and the corrected
isolation gate passed two order runs plus every per-file run. The first
immutable-revision check exposed line-sensitive RQ graph and broad-catch
metadata; those repairs and 68 affected tests now pass. A replacement immutable
checkpoint re-reviews rejected release. A documentation-only amendment now
defines request-local units, initiating-user enqueue snapshotting,
nonpersistent account-derived policy, supported dependent cancellation, and
the reproducible explicit-target migration graph cycle. It requires two
independent approvals and a standalone ancestor before runtime edits.
The implementation and source-freeze validation are complete. Acceptance E2E
mutation and Forest rollout remain gated on the final review artifacts and
the local two-user canary.

## Context and Orientation

The SQLAlchemy `User` model and migrations live under
`wepppy/weppcloud/app.py` and `wepppy/weppcloud/migrations/`. The current
Profile route/template are `wepppy/weppcloud/routes/user.py` and
`wepppy/weppcloud/templates/user/profile.html`. The new page should reuse
`security/_layout.html` and `controls/_pure_macros.html`.

`wepppy/nodb/unitizer.py` reads `[unitizer] is_english` when a new run is
initialized and then persists the resulting category map in `unitizer.nodb`.
Project creation and `Ron` initialization remain account-preference
independent. Account units are resolved only after view authorization into a
request-local presentation adapter; they never become run configuration or
durable Unitizer state.

`wepppy/nodb/core/watershed.py` reads WBT configuration and owns persisted
Watershed fields. `wepppy/nodb/core/watershed_mixins.py` delineates WBT
subcatchments and calls the edge detector in
`wepppy/topo/watershed_abstraction/support.py`. The policy check belongs
immediately after edge detection and before success timestamping.

## Plan of Work

First finish the contract-first ancestor. Obtain two independent read-only
reviews of `package.md`, the contract decision, ADR-0033, security plan, and
SURF-14A register entry. Resolve all authority, precedence, compatibility,
security, failure-atomicity, migration, and regression findings. Commit only
the documentation checkpoint as a standalone ancestor and record its SHA in
the tracker.

Next add a `UserPreferences` SQLAlchemy model with a one-to-one User
relationship, exact string constraints, timestamps, and cascading foreign key.
Add an Alembic merge migration whose parents are repository heads
`7b3c068e7a1d` and `b7d9c3e2f1a4` and which cleanly downgrades. Implement a
small typed preference service that returns defaults
for a missing row, validates exact tokens, performs one atomic upsert/update,
and resolves immutable request/job snapshots without silently swallowing
database errors.

Add login-required GET/POST `/preferences` routes in the existing user
blueprint. Render a server-side form through the existing security/Pure shell
and Pure form macros, add a Profile link, enforce CSRF, display field errors,
and use POST/Redirect/GET on success. Avoid new JavaScript unless direct
evidence proves it necessary.

Remove account preference parameterization from regular and HUC-fire creation.
Explicit `unitizer:is_english` and selected configuration alone determine
durable project state. Add a request-local Unitizer presentation resolver for
authorized Flask views and conversion/browser initialization endpoints. Auto
returns exact project selections; SI/English returns a detached/read-only
metric or customary view without changing cache, locks, or `unitizer.nodb`.
Adopt it across the finite inventory in the amendment: run shell, storm event
analyzer, Geneva, observed, debris flow, WATAR, WEPP, RHEM, Unitizer GET
conversion endpoints, and rendered Unitizer/UnitizerClient initialization.
Leave the explicit project Unitizer POST mutation endpoint unchanged.

Add `boundary_touch_behavior = "warn"` to the WBT configuration defaults or
the canonical default-loading path and validate `warn|error` when Watershed
initializes. Persist only the project policy and immutable configuration
baseline with guarded setters; account-derived effective values remain
execution-only. Hydrate legacy missing project/config state to `warn`. After
WBT edge identification, publish an actionable warning for `warn`; for
`error`, delete canonical `subwta.tif`, clear build and abstraction completion
state, retain deterministic diagnostic edge IDs, and raise
`WatershedBoundaryTouchesEdgeError` with the contract message and deterministic
edge identifiers.

After the amendment ancestor, add an initiating-user policy resolver at
`watershed_routes.build_subcatchments_and_abstract_watershed`. It must bind
the initiating positive numeric active User after ordinary run authorization,
resolve that user's preference or immutable per-run config baseline, validate
the exact private RQ snapshot, and finish before any NoDb/Redis/queue mutation.
Only after that successful validation may a legacy missing baseline persist
the computed configuration value under the Watershed lock, before every other
route mutation. Public sessions without a user, service/MCP, direct, and batch
paths retain project state; shared/admin account-bearing users use their own
preference.

Pass only the bounded schema version, effective policy, and source to the
child. In the child, clear the NoDb cache, hydrate durable state, validate,
construct a nonpersistent execution policy, then enter existing WBT attempt
invalidation/delineation. Add structured audit fields without exposing the
private snapshot through open jobinfo. Mixed-version deployment must
quiesce enqueue, drain jobs, and restart rq-engine/workers together.

Write model/migration, route/render/security, resolution, NoDb, synthetic
raster, RQ error, and compatibility tests before broad validation. Update the
Profile/User Preferences user guide, Channel Delineation guide, config/developer
documentation, ADR, package records, stubs, and generated artifacts only when
their owning source changes.

After implementation gates, obtain pre-acceptance governance and
operations/security approval. Then restart the complete local stack. Prove the
exact local-only emails `surf14a-local-a@example.invalid` and
`surf14a-local-b@example.invalid` are absent before creating two disposable
User-role receipts; stop on collision rather than reuse an account. Keep
credentials only in the gitignored local test-secret boundary. Create one
ordinary authenticated project and one exact `runs_users` sharing receipt.
Prove distinct SI/English views over byte-stable project Unitizer state and
distinct `error`/`warn` submissions on the same unchanged run. Prove
Auto/config, anonymous/public-session/service fallback, private snapshot
redaction, and unchanged durable boundary fields. Remove only the receipt-bound
association, run, preferences, role associations, Users, and credentials;
assert their absence and unchanged unrelated table counts. Obtain
post-acceptance confirmation before Forest.

Finally execute the authorized schema-first Forest canary. Record the code
revision, current Alembic head, backup/preflight evidence, and migration SQL
scope. Confirm old code with the additive schema before starting new code. Run
the reviewed `flask db upgrade` command inside the Forest application
container with explicit `FLASK_APP=wepppy.weppcloud.app:app`, verify the new
merge head/table/constraints, restart WEPPcloud/rq-engine/affected workers
together, then resolve the requesting operator and a second existing
operator-designated active test User. Record both numeric IDs and both exact
prior preference-row states. Stop for operator direction if the second User
does not already exist; do not create a User or alter roles. Exercise both
users' distinct units and WBT behavior on one disposable canary shared through
one recorded `runs_users` association without durable account-derived project
mutation. Remove only that run and association, restore both preference rows
exactly (deleting one only if it was absent before), prove both Users and all
unrelated rows remain, and complete a post-action dual audit. Do not migrate
production/wepp1.

## Concrete Steps

Run development commands from `/home/workdir/wepppy`:

    wctl doc-lint --path \
      docs/work-packages/20260729_user_preferences_wbt_boundary
    wctl doc-lint --path \
      docs/adrs/ADR-0033-user-defaults-and-wbt-boundary-policy.md

    wctl run-pytest tests/weppcloud/test_user_preferences.py \
      tests/weppcloud/test_user_preferences_postgres.py \
      tests/weppcloud/routes/test_user_profile_token.py \
      tests/weppcloud/routes/test_unitizer_user_preferences.py \
      tests/microservices/test_rq_engine_project_routes.py \
      tests/microservices/test_rq_engine_upload_huc_fire_routes.py \
      tests/microservices/test_rq_engine_watershed_routes.py \
      tests/nodb/test_wbt_boundary_touch_behavior.py \
      tests/rq/test_project_rq_mutation_guards.py \
      tests/rq/test_wbt_controlled_failure_integration.py --maxfail=1

    wctl run-stubtest wepppy.weppcloud.user_preferences
    wctl check-test-stubs
    wctl check-test-isolation
    wctl check-rq-graph
    wctl run-npm lint
    wctl run-npm test
    python3 tools/check_broad_exceptions.py --enforce-changed \
      --base-ref <checkpoint-sha>
    wctl run-pytest tests --maxfail=1
    git diff --check

Forest uses the exact target and Compose identity below. Set
`SURF14A_RELEASE_SHA` to the reviewed release commit and
`SURF14A_ROLLBACK_SHA` to a pre-reviewed forward revert commit that descends
from it. Record the previous SHA. The checkout must be clean. Create and
validate a fresh backup, block
enqueue, prove both queues and all workers idle, stop workers gracefully, then
change the bind-mounted tree. Run migration in a one-off container and do not
restart on any failure:

    ssh forest
    cd /home/workdir/wepppy
    set -euo pipefail
    export SURF14A_RELEASE_SHA=<reviewed-release-sha>
    export SURF14A_ROLLBACK_SHA=<reviewed-forward-revert-sha>
    export SURF14A_BACKUP_PATH="/backups/weppcloud-surf14a-$(date -u +%Y%m%d-%H%M%S).dump"
    git status --short
    test -z "$(git status --porcelain)"
    git rev-parse HEAD
    test "$(git rev-parse "$SURF14A_RELEASE_SHA^{commit}")" = \
      "$SURF14A_RELEASE_SHA"
    test "$(git rev-parse "$SURF14A_ROLLBACK_SHA^{commit}")" = \
      "$SURF14A_ROLLBACK_SHA"
    git merge-base --is-ancestor "$SURF14A_RELEASE_SHA" \
      "$SURF14A_ROLLBACK_SHA"
    docker compose -p docker -f docker/docker-compose.dev.yml run \
      --rm --no-deps -e SURF14A_BACKUP_PATH="$SURF14A_BACKUP_PATH" \
      postgres-backup bash -lc '
        set -euo pipefail
        umask 077
        password="$(cat /run/secrets/postgres_password)"
        pgpass_file="$(mktemp)"
        trap "rm -f \"$pgpass_file\"" EXIT
        printf "%s:%s:%s:%s:%s\n" \
          "$PGHOST" "$PGPORT" "$PGDATABASE" "$PGUSER" "$password" \
          > "$pgpass_file"
        export PGPASSFILE="$pgpass_file"
        tmp_path="${SURF14A_BACKUP_PATH}.tmp"
        pg_dump -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
          -Fc -f "$tmp_path"
        test "$(head -c 5 "$tmp_path")" = "PGDMP"
        pg_restore -l "$tmp_path" >/dev/null
        mv "$tmp_path" "$SURF14A_BACKUP_PATH"
        printf "verified_backup=%s\n" "$SURF14A_BACKUP_PATH"
      '
    docker compose -p docker -f docker/docker-compose.dev.yml stop \
      --timeout 120 weppcloud rq-engine scheduler
    docker compose -p docker -f docker/docker-compose.dev.yml ps --all \
      weppcloud rq-engine scheduler
    export SURF14A_RQ_DRAIN_LOG="$(mktemp)"
    wctl rq-info --raw > "$SURF14A_RQ_DRAIN_LOG"
    test "$(grep -Ec '^queue (default|batch) 0, 0 executing' \
      "$SURF14A_RQ_DRAIN_LOG")" -eq 2
    export SURF14A_WORKER_COUNT="$(
      awk '/^worker / {count++} END {print count + 0}' \
        "$SURF14A_RQ_DRAIN_LOG"
    )"
    test "$SURF14A_WORKER_COUNT" -gt 0
    test "$(awk '/^worker .* idle / {count++} END {print count + 0}' \
      "$SURF14A_RQ_DRAIN_LOG")" \
      -eq "$SURF14A_WORKER_COUNT"
    docker compose -p docker -f docker/docker-compose.dev.yml stop \
      --timeout 1800 rq-worker rq-worker-batch
    docker compose -p docker -f docker/docker-compose.dev.yml ps \
      --all weppcloud rq-engine rq-worker rq-worker-batch scheduler
    docker compose -p docker -f docker/docker-compose.dev.yml run \
      --rm --no-deps rq-worker bash -lc '
        set -euo pipefail
        redis_url="$(PYTHONPATH=/workdir/wepppy /opt/venv/bin/python -c \
          "from wepppy.config.redis_settings import RedisDB, redis_url; print(redis_url(RedisDB.RQ))")"
        /opt/venv/bin/rq info -u "$redis_url" default batch --raw
      ' > "$SURF14A_RQ_DRAIN_LOG.post-stop"
    test "$(grep -Ec '^queue (default|batch) 0, 0 executing' \
      "$SURF14A_RQ_DRAIN_LOG.post-stop")" -eq 2
    test "$(awk '/^worker / {count++} END {print count + 0}' \
      "$SURF14A_RQ_DRAIN_LOG.post-stop")" -eq 0
    export SURF14A_USER_COUNT_BEFORE="$(
      docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
        postgres psql -U wepppy -d wepppy -Atc \
        'SELECT count(*) FROM "user";'
    )"
    git fetch origin
    git merge --ff-only "$SURF14A_RELEASE_SHA"
    test "$(git rev-parse HEAD)" = "$SURF14A_RELEASE_SHA"
    docker compose -p docker -f docker/docker-compose.dev.yml run \
      --rm --no-deps -e FLASK_APP=wepppy.weppcloud.app:app \
      weppcloud flask db current
    docker compose -p docker -f docker/docker-compose.dev.yml run \
      --rm --no-deps -e FLASK_APP=wepppy.weppcloud.app:app \
      weppcloud flask db upgrade
    docker compose -p docker -f docker/docker-compose.dev.yml run \
      --rm --no-deps -e FLASK_APP=wepppy.weppcloud.app:app \
      weppcloud flask db current
    test "$(
      docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
        postgres psql -U wepppy -d wepppy -Atc \
        "SELECT count(*) = 4 FROM pg_constraint WHERE conrelid = \
        'user_preferences'::regclass AND conname = ANY (ARRAY[ \
        'pk_user_preferences', \
        'fk_user_preferences_user_id_user', \
        'ck_user_preferences_unit_system', \
        'ck_user_preferences_wbt_boundary_touch_behavior']);"
    )" = "t"
    test "$SURF14A_USER_COUNT_BEFORE" = "$(
      docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
        postgres psql -U wepppy -d wepppy -Atc \
        'SELECT count(*) FROM "user";'
    )"
    docker compose -p docker -f docker/docker-compose.dev.yml up \
      -d --no-deps weppcloud rq-engine rq-worker rq-worker-batch
    docker compose -p docker -f docker/docker-compose.dev.yml up \
      -d --no-deps scheduler

The backup output records its exact path only after `PGDMP` header and
`pg_restore -l` validation. The first `ps --all` proves enqueue surfaces
stopped; both drain assertions prove zero queued/executing work, and the second
`ps --all` proves all five services stopped before `git merge`. Constraint and
User-count checks run before `up`. If any command fails, leave the five
services stopped; do not downgrade or start the new checkout.

If application rollback is required, first repeat the exact enqueue-stop,
queue-drain, worker-idle, graceful worker-stop, and zero-registry commands
above. Then move only to the preflight-recorded forward revert and assert the
target before restarting:

    git fetch origin
    git merge --ff-only "$SURF14A_ROLLBACK_SHA"
    test "$(git rev-parse HEAD)" = "$SURF14A_ROLLBACK_SHA"
    docker compose -p docker -f docker/docker-compose.dev.yml up \
      -d --no-deps weppcloud rq-engine rq-worker rq-worker-batch
    docker compose -p docker -f docker/docker-compose.dev.yml up \
      -d --no-deps scheduler

Do not put database passwords, session cookies, JWTs, or preference-form CSRF
tokens into work-package artifacts.

## Validation and Acceptance

Model tests against disposable PostgreSQL must prove one row per user, both
check constraints, cascade delete, missing-row defaults, atomic two-field
updates, whole-record last-committed-write-wins behavior, one bounded
first-create race retry, and fresh/two-head migration
upgrade/downgrade/upgrade. Route/render tests must prove login, CSRF, exact
tokens, visible errors, no partial mutation, escaped values, selected state,
Pure macros, prefix-aware Profile navigation, and PRG success.

Creation tests must prove regular and HUC-fire creation ignore account
preferences and preserve explicit-input/config durable Unitizer and WBT state.
Presentation tests cover Auto, SI, English, mixed project selections,
owner/shared/admin/public authorized users, anonymous and session-without-user
fallback, server-rendered reports, conversion endpoints, and browser initial
payload. They assert byte/mtime/cache identity/lock stability for
`unitizer.nodb` and simultaneous distinct views for two users.

Delineation-route tests cover user and account-bearing session identity,
missing/malformed session `user_id`, inactive/deleted User, shared/admin/public
authorized User, public session without User, service/MCP, direct/batch,
fork/archive/restore, missing/invalid preference, and database failure. Config
tests cover both users choosing Auto, legacy baseline hydration, and copied
project state. Failure tests assert byte-stable NoDb/readiness/queue state
before resolution and snapshot validation succeed.
RQ tests validate exact private metadata, open jobinfo redaction, bounded child
arguments, cache/hydrate/validate/execution-view ordering, preference change
after enqueue, same-snapshot retry, a distinct fresh resubmission, terminal
snapshot/apply failures, and no persisted account-derived policy.

Synthetic rasters must cover every edge, corners, nodata/non-positive edges,
no-edge, multiple deterministic identifiers, `warn`, `error`, invalid config,
stale prior completion state, and rerun recovery. The error case must expose
the contract message through the existing rq-engine error envelope and must
not allow downstream readiness.

Forest acceptance requires the reviewed application revision, exact target
and database identity, repository/database head agreement, restore owner/point,
the reviewed merge head, exact new table/constraints, unchanged user count, no
required backfill, preference save/reload, two users' distinct presentation
units over one unchanged project, user A `error`, user B `warn`, Auto/config
fallback on the same unchanged run, private snapshot redaction, canary
cleanup, healthy services, post-action review, and a documented
nondestructive application rollback.
Production remains untouched.

## Idempotence and Recovery

Local tests and documentation checks are repeatable. The migration must be
additive and safe to rerun through Alembic head detection. A failed preference
save rolls back its transaction. A failed authenticated preference lookup
cannot mutate presentation, project, readiness, or queue state.

Before Forest apply, confirm both expected current revisions and a database
backup or approved restore point. If migration apply fails, stop, preserve logs, and do
not repeatedly mutate the database without diagnosing the exact revision. If
the schema succeeds but the application canary fails, first stop enqueue
surfaces, drain queued/executing work, prove workers idle, stop both worker
services, and prove the registry empty. Only then move to reviewed old code
and restart the four changed services together before `scheduler`. Preserve
the additive table; downgrade only with separate reviewed authority.

## Artifacts and Notes

Keep checkpoint reviews, disposition, final reviews, migration preflight/apply
transcripts with secrets removed, and local/Forest E2E evidence under this
package's `artifacts/` directory. Record exact revisions and test counts in the
tracker and this plan.

## Interfaces and Dependencies

Use existing Flask-SQLAlchemy, Flask-Migrate/Alembic, Flask-Security login,
global CSRF enforcement, PureCSS shell/macros, NoDb locking, RQ response
envelopes, and the owned WBT edge detector. Add no external dependency.

Expose stable Python enums or literal-validated constants for the six tokens,
a typed account resolver, a request-local Unitizer presentation view, and a
bounded WBT snapshot validator. Keep account persistence independent of
run-scoped Unitizer and Watershed policy mutation. Reuse
`WatershedBoundaryTouchesEdgeError`; do not add a generic exception or silent
fallback wrapper.

## Revision Notes

2026-07-30: Initial scaffold records the operator-approved label, typed storage
decision, precedence, reproducibility boundary, WBT policy, contract/review
gates, and scoped Forest migration authority.

2026-07-30: Revised after both live WBT incidents. The operator clarified that
both preferences follow the authenticated user rather than the owner;
non-Auto units are presentation-only and WBT is an enqueue-time action
snapshot. The plan retains all review/Forest gates.
