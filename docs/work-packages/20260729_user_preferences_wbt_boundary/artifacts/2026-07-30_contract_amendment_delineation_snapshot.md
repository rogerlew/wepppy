# SURF-14A User-Context Preference Contract Amendment

**Status**: Pending independent checkpoint review

**Starting implementation revision**:
`b593fb1d8595f6c3c9862ce773def31d372d787c`

**Original contract ancestor**:
`1b412d61ab1173c53c6def06f123d124aaf8bfd1`

**Decision venue**: Codex API workspace thread, 2026-07-30 UTC

**Participants present**: requesting WEPPcloud operator; Codex

## Trigger and Operator Approval

Run `rock-ribbed-triplicate` persisted `warn`, then delineated eight edge
hillslopes even though the initiating user's current preference was `error`.
Run `depleted-hyperlink` persisted creation-time `error`, then failed on seven
edge hillslopes after that user changed their preference to `warn`. The
operator explicitly expected the current preference to govern both
submissions.

During checkpoint review the operator corrected the controlling identity:
"this is a user preference. it should track the user, not the owner." The
operator then made the unit lifetime explicit: "units should be treated the
same. the unit preference (non-auto) follows the user. a user should be able
to view the project with their preferred units without mutating the projects
units."

These statements approve two user-context overlays:

- a non-`config` unit preference controls presentation for the authenticated
  user viewing an authorized project without mutating project Unitizer state;
- a non-`config` WBT boundary preference controls the delineation submitted by
  that authenticated user without becoming another user's preference.

Existing authorization still decides whether the user may view or mutate the
run. `Run.owner_id` and `runs_users` do not select the preference controller.

## Applicable Authority

This amendment changes the SURF-14A package/contract decision, ADR-0033, the
bounded WBT section of `docs/schemas/rq-response-contract.md`, the active
ExecPlan, and tracker. It applies the existing NoDb cache-guard standard
without revising that repository-wide standard.

## Exact User Identity and Fallback Contract

Account resolution occurs only after existing view or mutation authorization.
A `user` token binds the initiating/viewing account through its verified
positive numeric User subject. A cookie-authenticated Flask request binds
`current_user.id`. A run `session` token is account-bearing when a `user_id`
claim is present: a verified positive numeric claim must bind to one active
User, while a present malformed, Boolean, zero, or negative claim fails closed.
Only an absent `user_id` claim makes the session non-account-bearing.

An authorized public/run session without numeric `user_id`, service/MCP
principal, anonymous/CAP viewer, direct worker, or batch path has no account
overlay and uses project/config state. A malformed or inactive account-bearing
identity, invalid stored preference, or database failure fails closed with
sanitized `preference_resolution_failed` and an `error_id`; it never silently
falls back. Shared users and administrators with valid account identity use
their own preferences after ordinary run authorization.

Preference resolution uses one bounded application/database context. It locks
the active User row before reading the constrained preference row. Preference
saves acquire the same User lock first. The transaction that obtains the lock
first determines one coherent old-or-new snapshot; a later save affects only
a later view or submission. Tests force both race orders.

## Unit Presentation Overlay

`config` means use the run's persisted Unitizer preferences. `si` and
`english` construct a request-local presentation view over the durable
Unitizer:

- `si` selects the first canonical unit in every Unitizer category;
- `english` selects the second canonical unit when present and otherwise the
  category's first canonical unit.

The overlay is an immutable/request-local adapter or detached copy. It may be
used by server-rendered reports, controls, conversion endpoints, and the
initial browser Unitizer payload, but it must not call `set_preferences`,
`dump`, acquire the Unitizer persistence lock, alter the shared cached
instance, or write `unitizer.nodb`. Auto/config continues to expose the
project's exact persisted category selections, including mixed custom units.

Profile unit preference no longer adds `unitizer:is_english` during project
creation. Explicit project-creation input and project configuration continue
to determine durable project units. Existing creation routes remain
compatible, but account preference lookup is not part of their unit
parameterization. Changing SI/English affects the user's next authorized view,
including existing, shared, public, restored, and forked projects. Two users
may view the same unchanged `unitizer.nodb` in different unit systems.
Anonymous and non-account-bearing views use project units.

Existing project Unitizer mutation controls remain project mutations and are
not silently converted into profile writes. A non-auto account overlay still
wins for that user's presentation until they choose Auto. This package does
not change conversion formulas, precision tables, canonical stored model
units, or category-level project customization.

The finite presentation adoption inventory is:

- one typed resolver/view helper in `wepppy/weppcloud/user_preferences.py`;
- run-shell/report producers in `routes/run_0/run_0_bp.py` and
  `routes/storm_event_analyzer.py`;
- report producers in `routes/nodb_api/{geneva,observed,debris_flow,watar,
  wepp,rhem}_bp.py`;
- GET conversion endpoints `unitizer` and `unitizer_units` in
  `routes/nodb_api/unitizer_bp.py`; and
- the rendered `controls/unitizer.htm` state that initializes
  `UnitizerClient`.

The route-level authorization disposition is:

| Presentation producer | Authorization before overlay | Disposition |
| --- | --- | --- |
| `run_0_bp.runs0` | inline `authorize(runid, config)` after CAP | retain; resolve only after it returns |
| `storm_event_analyzer` | inline `authorize(runid, config)` after CAP | retain; resolve only after it returns |
| `geneva_bp.report_geneva_summary` | `authorize_and_handle_with_exception_factory` | replace its report helper's Unitizer only |
| `observed_bp.report_observed` | canonical authorize decorator, then CAP | retain ordering; overlay follows authorization |
| `watar_bp.hillslope0_ash`, `report_ash`, `report_contaminant` | canonical authorize decorator; report routes also CAP | replace each presentation lookup |
| all nine Unitizer-using WEPP report/plot functions in `wepp_bp.py` | canonical authorize decorator; report routes also CAP | replace each presentation lookup |
| `rhem_bp.report_rhem_avg_annuals`, `report_rhem_return_periods` | inline `authorize(runid, config)` after CAP | retain; resolve only after it returns |
| `unitizer_bp.unitizer_route`, `unitizer_units_route` | canonical authorize decorator | replace GET conversion lookup |
| `debris_flow_bp.report_debris_flow` | CAP only today | add canonical ordinary authorization beneath CAP before overlay |

The repository-search adoption test enumerates the exact WEPP function names
and fails when a new production presentation lookup lacks an authorization
disposition. Tests prove no preference query occurs before each authorization
boundary succeeds. Admin/Root bypass remains whatever canonical ordinary run
authorization already permits; this package adds no preference-based access.

`ui_showcase` keeps its explicit stub. The POST
`tasks/set_unit_preferences` endpoint remains the explicit project Unitizer
mutation contract and does not become an account-preference endpoint. A
repository search for production `Unitizer.getInstance` and
`unitizer_nodb=` call sites must be retained as adoption evidence; every
presentation call site is converted to the helper or explicitly dispositioned.

The debris-flow report currently has only an anonymous CAP gate, which lets
any authenticated user bypass that gate without ordinary run authorization.
Before it may resolve an account overlay, this package brings that report
under the canonical ordinary run authorization decorator while retaining the
CAP gate for anonymous public-run viewers. Tests prove an authenticated
non-owner cannot view a private run, an authorized owner/shared/admin may
view it, and a CAP-verified anonymous viewer may view only a run that ordinary
authorization treats as public.

The two `wepppy/nodb/mods/features_export/service.py` Unitizer call sites are
explicitly excluded from the presentation overlay. They implement
artifact-generation `units=project` conversion and its persisted-project
preference fingerprint for shared cache correctness, not an authenticated
HTML/API view. Feature exports continue to obey their explicit export-units
request and project fingerprint; an account presentation preference must not
alter or partition those durable artifacts.

## WBT Submission Overlay

For an authorized WBT subcatchment submission, rq-engine resolves the
initiating user's boundary preference before any NoDb, RedisPrep, readiness,
job-ID, or queue mutation. `warn` or `error` controls that submission.
`config` or a missing row uses the run's immutable configuration baseline,
`_wbt_boundary_touch_config_behavior`.

New runs initialize the baseline from selected configuration independently of
account preference. Legacy runs missing it compute the named configuration
value during read-only resolution. After successful snapshot validation, that
legacy baseline alone may be persisted under the canonical Watershed lock
before any other route mutation. Archive/restore and fork copy the baseline.
Account-derived effective behavior is never stored as the baseline.

The user's effective boundary selection is job input, not durable project
preference. The child applies it to a detached/in-memory execution view or an
explicit `build_subcatchments` parameter; it must not persist it to
`_wbt_boundary_touch_behavior`. Project policy and the next user's behavior
remain unchanged. Direct/batch and non-account-bearing paths use the
project's persisted policy. Retry reuses the original job snapshot; a new
submission resolves the initiating user's current preference again.

## Exact RQ Snapshot and Failure Contract

Private root/child metadata key `wbt_boundary_policy_snapshot` has exactly:

```json
{
  "schema_version": 1,
  "runid": "<canonical run ID>",
  "actor_token_class": "user|session",
  "actor_user_id": 1,
  "config_policy": "warn|error",
  "effective_policy": "warn|error",
  "source": "user_preference|project_config"
}
```

Every key is required; booleans, extra keys, nonpositive IDs, unknown enums,
and run-ID mismatch are invalid. `config_policy` is exactly the immutable
`_wbt_boundary_touch_config_behavior`, never
`_wbt_boundary_touch_behavior`. With `source=project_config`,
`effective_policy` must equal `config_policy`; with
`source=user_preference`, `effective_policy` is the initiating user's exact
`warn|error` value and may differ from `config_policy`. The bounded root/child
function argument is
exactly `{schema_version, effective_policy, source}`. The route enqueues the
root with complete private metadata and the bounded argument. The root
validates exact consistency before enqueueing children and attaches both to
the subcatchment child. The child validates exact consistency before touching
run state. Workers never query account state.

Open `jobstatus` and `jobinfo` never expose the private snapshot. Their
generic `auth_actor` projection is always `null`; in particular it never
returns a session ID, service/MCP subject, service group, email, or numeric
User ID. Existing Admin/Root-only job listings and server logs may retain the
sanitized internal actor object for operations. Audit logs
may record numeric actor ID, run ID, project/effective policy, source,
root/child IDs, outcome, correlation ID, and error ID. They never contain a
JWT, cookie, session identifier, email, CSRF token, or database credential.

Route-time resolution failure returns HTTP 500
`preference_resolution_failed`, exact public message
`Could not resolve user preferences.`, and `error_id`, and creates no job.
Missing, malformed, extra, or inconsistent root/child snapshot uses
`wbt_boundary_policy_snapshot_invalid` with exact public message
`The WBT boundary policy snapshot is invalid. Submit delineation again.` A
cache, hydration, directory-root lock, or execution-policy
construction/application failure uses `wbt_boundary_policy_apply_failed` with
exact public message
`The WBT boundary policy could not be applied. Submit delineation again.`
Both async codes include an `error_id`, keep the failing raw job `failed`,
cancel any created deferred abstraction child, and make the public aggregate
root `failed` after all created descendants are terminal. A raw orchestration
root already `finished` after creating children remains raw `finished`; public
polling reports aggregate failure. Open polling exposes only the allowlisted
code, exact message, and `error_id`; `details` is absent for these three
preference/policy infrastructure failures.

The child follows the scoped cache-guard contract. The entire directory
preflight, exact Watershed cache clear, durable hydration, snapshot validation,
nonpersistent execution-policy construction, WBT attempt invalidation, and
delineation executes inside the existing watershed directory-root lock.
Invalid snapshot, cache, lock, stale state, or execution-view failure cannot
clear readiness or start WBT. Concurrent submissions for the same run are
therefore serialized for their complete mutable child operation; no effective
policy may live in shared cached or durable controller state between jobs.

The existing edge result contract remains:

- `warn` retains output, publishes the caution, and permits abstraction;
- `error` raises `WatershedBoundaryTouchesEdgeError`, deletes canonical
  `subwta.tif`, leaves build/abstraction timestamps absent, retains sorted edge
  diagnostics, fails the subcatchment child, and cancels abstraction.

## Compatibility and Regression Evidence

This amendment removes the already-implemented creation-time account unit
override and replaces it with a presentation-only overlay. Existing durable
Unitizer state is preserved. Existing WBT configuration and project policy
remain valid. No successful output is retroactively removed. TOPAZ behavior,
edge geometry, conditioning, formulas, thresholds, and config defaults are
unchanged.

Before final review, tests must prove:

- Auto, SI, and English views across server-rendered pages, Unitizer conversion
  endpoints, and initial browser payload without any `unitizer.nodb` byte,
  mtime, cache-instance, lock, or preference change;
- two authorized users view the same project simultaneously in different
  units; anonymous/session-without-user/service paths use project units;
- explicit project creation and config still determine durable Unitizer state,
  with no account-derived creation override;
- initiating user/session, shared user, administrator, public authorized user,
  service/MCP, public session, direct/batch, inactive/missing identity,
  stored-invalid, database-failure, and config-baseline WBT rows;
- user A `error`, user B `warn`, and both users' Auto/config submissions on one
  unchanged project, including save/submit race ordering;
- preference changes after enqueue and retry retain the original snapshot,
  while a new submission refreshes it;
- forced same-run concurrent user A/error and user B/warn children serialize
  under the directory-root lock in both forced orders. In A/error then B/warn,
  A fails and cancels only its abstraction, B succeeds, and final raster/
  readiness reflect B's successful warning result. In B/warn then A/error, B
  succeeds, A fails and cancels only its abstraction, and final canonical
  raster/readiness are absent with A's edge diagnostics retained. Each job
  uses only its own snapshot, neither leaks policy into the other, both
  durable policy fields remain byte-for-byte unchanged, and active/deferred
  registries are empty after each order;
- exact private metadata, bounded args, open-polling redaction, terminal
  invalid/apply failures, cancellation, cache ordering, and no durable
  account-derived boundary policy;
- a legacy/superseded-state fixture where
  `_wbt_boundary_touch_behavior != _wbt_boundary_touch_config_behavior`
  proves root metadata uses the named config baseline, child arguments use
  the correct effective choice/source, polling stays redacted, and both
  durable fields remain unchanged;
- both observed edge cases, full focused/broad/frontend/stub/isolation/graph/
  documentation gates, local two-user acceptance, and Forest canary.

## Migration Evidence and Deployment

The additive account-preference migration and its explicit two-parent graph
cycle remain unchanged. The reproducible local PostgreSQL artifact must retain
exact create, representative-schema initialization, parent stamping,
upgrade/downgrade/re-upgrade, application assertions, User preservation,
cascade, and drop commands.

Mixed-version deployment must stop enqueue surfaces, drain queues, stop both
worker services, verify zero registered workers, move to the exact reviewed
release SHA, assert `git rev-parse HEAD` equals it, migrate, and restart
`weppcloud`, `rq-engine`, `rq-worker`, and
`rq-worker-batch` together before `scheduler`. Application rollback repeats
the same quiesce/drain/stop checks before moving to reviewed old code; the
rollback target is an exact pre-reviewed forward revert commit recorded before
apply, and `git rev-parse HEAD` must equal it before services restart. The
additive table stays unless a separately authorized downgrade is required.

Local acceptance requires pre-acceptance dual review, a full stack restart,
and two new disposable local-only authenticated Users with exact stable emails
`surf14a-local-a@example.invalid` and
`surf14a-local-b@example.invalid`. Preflight must prove both emails are absent;
if either exists, stop rather than reuse or overwrite it. Creation records
each numeric User ID and exact User-role association receipt. Credentials stay
only in the gitignored local test-secret boundary and never enter an artifact.
One user creates one exact disposable run through the ordinary authenticated
path, and the second receives ordinary access through one recorded
`runs_users` association. Both preference rows must be absent before the test.

The local canary proves distinct unit presentation and WBT behavior on that
same run, config/anonymous/service fallback, redaction, and byte/hash-stable
project Unitizer and both durable boundary-policy fields. Cleanup removes only
the recorded run association, run, two preference rows, two User-role
associations, and two Users. Post-cleanup assertions prove both exact emails,
IDs, preference rows, run/association, and credentials are absent and no other
User, role, preference, or run-association count changed. The redacted
transcript records all non-secret receipts and before/after counts.
Post-acceptance dual review must confirm cleanup before Forest.

Forest repeats the bounded canary using the requesting operator account and a
second existing operator-designated authenticated test account. Preflight
must resolve and record both numeric User IDs, prove the second account already
exists and is active, and stop for operator direction rather than create or
alter an account or role if it does not. The canary creates one exact
disposable run through the ordinary authenticated path, grants the second
account ordinary run access through the existing `runs_users` association,
and records the exact run/association identifiers. Before mutation it records
whether each preference row exists and, when present, both exact enum values
and timestamps. It then proves two-user unit views and distinct WBT behavior
on the same unchanged project.

Cleanup deletes only the exact disposable run and added run association,
restores each preexisting preference row to its recorded values, and deletes
a preference row only when that exact row was absent before the canary. It
does not delete either User, change roles, or touch unrelated associations.
Post-cleanup assertions prove both Users remain, prior preference state is
exactly restored, the canary run/association are absent, and no other row was
changed. Production/wepp1 remains unauthorized.

Acceptance mutation and Forest remain blocked until this amendment is
independently approved, committed as a standalone ancestor, implemented, and
reviewed.

## Prior Review Disposition

The first owner-only amendment and its immutable FAIL reviews remain
historical evidence. Their authority objection is now resolved by the
operator's explicit initiating-user decision, which supersedes owner-only
scope. Applicable identity, exact-schema, terminal-state, config-baseline,
NoDb ordering, migration, and two-phase acceptance findings are incorporated
above. No owner-only re-review artifact was finalized after the correction.
