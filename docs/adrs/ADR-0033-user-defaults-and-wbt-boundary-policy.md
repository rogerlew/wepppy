# ADR-0033: User-Context Units and WBT DEM-Boundary Policy

**Status**: Original persistence decision accepted; user-context amendment
pending independent approval

**Date**: 2026-07-30

## Context

WEPPcloud configurations and persisted Unitizer state choose project units.
WBT delineation records watershed identifiers on DEM raster edges and may
continue with a clipped watershed. Users need account preferences that follow
them across authorized projects without rewriting another project's settings.

Two live jobs proved that creation-time WBT policy did not follow the
initiating user's later preference. The operator then clarified that the
preference tracks the user, not the run owner, and that non-Auto units must
change the user's view without mutating project units.

## Decision

Store two account preferences:

- unit system: `config` (Auto), `si`, or `english`;
- WBT DEM-boundary behavior: `config` (Auto), `warn`, or `error`.

Resolve them only in an authenticated user context after ordinary run
authorization. User and account-bearing session identities use their own
preference, whether owner, shared user, administrator, or authorized public-run
user. Anonymous, public sessions without numeric `user_id`, service/MCP, and
direct/batch paths use project/config state. Invalid account-bearing identity
or storage fails closed.

A non-Auto unit preference is a request-local presentation overlay. SI selects
the first canonical Unitizer option per category; English selects the second
when present. Auto uses the exact persisted project Unitizer preferences.
Rendering and conversion use the overlay without changing `unitizer.nodb`,
the cached controller, project configuration, or project creation inputs.

A non-Auto boundary preference is snapshotted when that user submits WBT
delineation. Auto uses the immutable per-run config baseline. The validated
snapshot travels through RQ; workers do not query account state. The effective
policy is applied only to that execution and is not persisted as project
policy. A retry reuses its snapshot; a new submission refreshes it.

Persist `_wbt_boundary_touch_config_behavior` as the project/config baseline.
Legacy state resolves and persists that baseline once under lock only after
read-only snapshot validation. Archive/restore and fork copy it.

`[watershed.wbt] boundary_touch_behavior` accepts `warn|error` and defaults to
`warn`. `warn` continues with a caution. `error` raises the existing typed
edge exception, removes clipped canonical output, prevents downstream
readiness, and tells the user to select another outlet or larger extent. The
label is `Stop with an error`.

## Parameterization Delta

The initial implementation used account units as new-project defaults and
persisted the account boundary choice into run state. This amendment removes
both account-to-project mutations. Project creation/config and explicit
project Unitizer controls remain authoritative durable state. User preferences
are presentation/action overlays.

No conversion formula, precision, measurement category, raster-edge test,
conditioning algorithm, or hydrologic threshold changes.

Same-run WBT submissions are serialized through their complete mutable
build-plus-abstraction child. Its watershed directory-root lock lasts for the
43,200-second RQ task timeout plus a 300-second cleanup margin. Admission uses
an optimistic Redis transaction, a non-expiring per-run tail, and at most five
`WATCH` conflict retries. These are operational coordination parameters, not
hydrologic parameters: the long directory lock prevents a valid job from
outliving its mutation exclusion, while the short transaction atomically
registers the job tree without a fallible admission lease. The persistent tail
prevents queue delay from silently dropping ordering; compare-and-delete
release and stale missing/terminal-job cleanup prevent an older job from
erasing a newer reservation or creating a dependency that can no longer emit
a completion transition.

The abstraction job-tree node is a nonmutating completion receipt. Admission
atomically registers that receipt, both dependency directions, both root
links, the tail, and the mutable child's queued/deferred membership. This
preserves observable tree shape without duplicate abstraction, orphaned
prepared jobs, or failure/registration and execution/trace races.

The requesting WEPPcloud operator owns the user-visible outcome and release
decision. Codex/WEPPcloud maintainers own the queue mechanism and evidence;
independent governance and operations/security reviewers approve its control
contract. Rejected alternatives were a post-activation receipt, a
time-limited admission mutex without fencing, a worker-blocking execution
mutex, and a saved dormant child with later activation. Each has an
unrecoverable race, worker-capacity cost, or hard-interruption orphan window.

Required evidence includes forced concurrent admission conflicts, hard-stop
boundaries before and after transaction commit, exact root/child/receipt/tail
linkage, same-run opposite-policy execution in both orders, terminal stale-tail
recovery, ambiguous-response reconciliation, idempotent root retry, receipt
cancellation, and empty dependency registries. Release rollback first stops
enqueue surfaces, drains workers, and moves all web/worker consumers to the
reviewed revert together. Existing tail keys and terminal jobs are inert; the
revert runbook may remove only a verified tail whose referenced job is
missing/terminal. Revoke or change these parameters only through a new ADR
amendment and the same independent checkpoint gate.

### Queue-revision provenance

- **Decision venue**: Codex API workspace thread, 2026-07-30 10:59 UTC
  (America/Los_Angeles: 03:59 PDT).
- **Participants present**: requesting WEPPcloud operator and Codex.
- **Outcome decision owner**: requesting WEPPcloud operator, through the
  instruction to execute this work package and deliver user-following
  preferences without project mutation.
- **Queue-control decision owner and implementer**: Codex/WEPPcloud
  maintainers. The atomic-admission revision is an implementation control that
  preserves the operator-approved behavior after the leased design failed
  checkpoint review.
- **Independent checkpoint decision**: the operations/security reviewer
  approved the revised documentation on 2026-07-30 UTC; governance approval
  remains required before the standalone ancestor and implementation.

### Queue-revision evidence

Evidence that motivated and bounded the decision:

- the accepted user-context reviews specify both forced same-run policy orders
  and complete mutable-state isolation:
  [governance](../work-packages/20260729_user_preferences_wbt_boundary/artifacts/2026-07-30_user_context_checkpoint_governance_review.md)
  and
  [operations/security](../work-packages/20260729_user_preferences_wbt_boundary/artifacts/2026-07-30_user_context_checkpoint_ops_security_review.md);
- the retained
  [governance FAIL](../work-packages/20260729_user_preferences_wbt_boundary/artifacts/2026-07-30_queue_sequencing_checkpoint_governance_review.md)
  and
  [operations/security FAIL](../work-packages/20260729_user_preferences_wbt_boundary/artifacts/2026-07-30_queue_sequencing_checkpoint_ops_security_review.md)
  identify the dormant-child orphan and unfenced-lease failures in the
  superseded design;
- the revised
  [operations/security PASS](../work-packages/20260729_user_preferences_wbt_boundary/artifacts/2026-07-30_queue_sequencing_checkpoint_ops_security_rereview.md)
  accepts the no-pre-`EXEC` atomic admission contract; and
- the existing forced-order and real-Redis evidence lives in
  `tests/rq/test_wbt_controlled_failure_integration.py`. The harder
  transaction-conflict, hard-stop, ambiguous-response, and exact-state matrix
  listed above remains a pre-final-review implementation obligation, not
  evidence already claimed as complete.

### Residual risks and revert triggers

The selected design still depends on Redis transaction semantics and RQ's
queued/deferred registry representation. Revert or withhold release when any
of these observable conditions occurs:

- five `WATCH` conflicts are exhausted under ordinary non-adversarial load;
- an ambiguous Redis response cannot reconcile the exact tail, root links,
  child/receipt IDs, dependency directions, and registry membership;
- a tail references a nonterminal job that is absent from every valid
  queued/deferred/started execution location;
- receipt cancellation leaves deferred-registry or dependency-set residue;
- opposite-policy same-run execution changes final durable policy or output
  according to arrival/worker timing rather than serialized order; or
- all enqueue surfaces and worker consumers cannot be quiesced and moved to
  one reviewed revision together.

An isolated conflict-exhaustion response fails without work and may be retried
after diagnosis. Any non-exact reconciliation, orphan, dependency residue, or
cross-user state leak requires stopping affected enqueue surfaces, draining
workers, preserving Redis/job evidence, and moving all consumers to the
reviewed forward revert before reopening delineation.

## Decision Provenance

Decision Venue: Codex API workspace thread, 2026-07-29 through 2026-07-30.

Participants Present: requesting WEPPcloud operator; Codex.

Stakeholder Input: Mariana's preference for an actionable error was relayed by
the operator; Mariana was not present.

The operator first approved typed storage, the `Stop with an error` label,
work-package execution, and a contained Forest migration/canary. On 2026-07-30
the operator explicitly corrected lifetime and authority: the preference
tracks the user rather than the owner, and non-Auto units follow that user
without mutating project units. This later statement supersedes the original
creation-time unit snapshot and the draft owner-only WBT amendment.

## Rationale

Account preferences should have account lifetime. A presentation overlay lets
two authorized viewers use different units over identical canonical project
state. An enqueue-time boundary snapshot makes async execution deterministic
without leaking one user's preference into the next user's action. Auto keeps
project/config authorship useful. Typed PostgreSQL columns provide exact
validation and cross-device consistency.

Worker-time account lookup, cookies/local storage as the source of truth,
owner-selected preference, and durable account-derived project mutation were
rejected because they create timing dependence, cross-user leakage, or the
wrong lifetime. Automatically moving an outlet or enlarging an extent was
rejected because it changes geospatial intent.

## Evidence

- `wepppy/nodb/unitizer.py` owns persisted project Unitizer state and canonical
  conversion categories.
- `wepppy/microservices/rq_engine/watershed_routes.py` is the authenticated WBT
  submission boundary.
- `wepppy/topo/watershed_abstraction/support.py` detects edge identifiers.
- SURF-14A's user-context amendment contains the exact identity, overlay, RQ,
  failure, migration, and acceptance contracts.
