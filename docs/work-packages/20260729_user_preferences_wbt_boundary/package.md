# Account User Preferences and WBT Boundary Policy

**Status**: Open (2026-07-30)

**Timezone**: UTC

**Package ID**: SURF-14A

**Parent owners**: SURF-14 User Profile/Session, SHR-05 Unitizer Preferences,
SURF-01 creation, SURF-04 fork, DOM-02 Project Shell, DOM-05 Channel
Delineation, and DOM-05A Topaz Conditioning

## Overview

Add an authenticated User Preferences page where a person can choose how
authorized projects are presented in units and whether their WBT delineation
may continue when it reaches the DEM boundary. Preferences are account-scoped
PostgreSQL state and follow the initiating/viewing user. They do not become
project defaults: units are a request-local presentation overlay, while the
boundary choice is an immutable job snapshot.

This package is a registered, bounded cross-owner feature. It does not reopen
the verified SURF-14 profile, SHR-05 run-scoped Unitizer, or DOM-05 Channel
Delineation contracts outside the exact deltas below.

## Normative Contract

This section becomes the authoritative SURF-14A behavior contract only after
the required documentation-only checkpoint is independently reviewed,
dispositioned, and committed as a standalone ancestor. Implementation
conformance is currently pending.

### Account persistence

The application stores at most one `user_preferences` row per authenticated
`user.id`. The row has typed, non-null `unit_system` and
`wbt_boundary_touch_behavior` fields, timestamps, a cascading foreign key, and
database check constraints. Missing rows mean both preferences are `config`;
the application need not backfill existing users. A row is created atomically
on the first successful preference save.

Canonical stored values are:

- `unit_system`: `config`, `si`, or `english`;
- `wbt_boundary_touch_behavior`: `config`, `warn`, or `error`.

No cookie, browser local storage, generic key/value table, JSON preference
blob, or run-scoped NoDb file is the account-level source of truth.

### User Preferences page

Authenticated GET and POST requests use `/preferences`. The Profile page links
to that endpoint with `url_for('user.preferences')`. The page extends the
existing PureCSS account layout and uses the existing Pure form macros. Each
select change saves the complete two-field record automatically through one
same-origin, CSRF-protected request. Saves are serialized and replay the latest
complete selection after an active request finishes.

The Default units choices are:

- `Auto — use project configuration` (`config`, default);
- `SI — metric defaults` (`si`);
- `English — US customary defaults` (`english`).

The When a WBT watershed reaches the DEM boundary choices are:

- `Auto — use project configuration` (`config`, default);
- `Warn and continue` (`warn`);
- `Stop with an error` (`error`).

POST is login-required, same-origin CSRF-protected, and accepts only the two
named fields with exact enum values. Invalid or missing input produces visible
field errors and no database mutation. Successful auto-save commits both
values in one transaction and returns bounded JSON when JSON is requested.
The page announces saving and saved states through a polite live region and
uses an assertive visible message for failures. Ordinary form POST retains
POST/Redirect/GET as a `noscript` fallback; the enhanced page does not show a
general Save preferences button.

### User-context resolution and run compatibility

Existing authorization first decides whether an identity may view or mutate a
run. A verified active User then resolves their own preference; `Run.owner_id`
and `runs_users` do not choose whose preference applies. User tokens,
cookie-authenticated requests, and run sessions with verified positive numeric
`user_id` are account-bearing. Anonymous/CAP, public sessions without
`user_id`, service/MCP, direct worker, and batch paths use project/config
state. Invalid account-bearing identity, stored state, or database access
fails closed with `preference_resolution_failed`.

For presentation, `config` exposes the project's exact persisted Unitizer
selections. `si` or `english` creates a request-local read-only Unitizer view
using metric or US customary defaults. It must not mutate the cached
controller, acquire its persistence lock, or write `unitizer.nodb`. The
overlay applies to authorized existing, shared, public, restored, forked, and
new projects. Two users may view the same unchanged project in different
units.

Profile units no longer participate in project creation. Explicit creation
input and project configuration continue to define durable project Unitizer
state. Existing Unitizer project-mutation controls retain their contract; a
non-Auto account overlay remains the viewing user's presentation until they
choose Auto.

For WBT submission, `warn|error` controls only the initiating user's job.
`config` uses the immutable project config baseline. The effective choice is
not persisted as project policy, so a later authorized user's submission
resolves independently. Retry retains its original snapshot; a new submission
refreshes the current user preference.

A separate `_wbt_boundary_touch_config_behavior` stores the configuration
baseline and is copied by archive/restore and fork. Legacy runs resolve and
persist it once under the Watershed lock only after read-only snapshot
validation. Account-derived effective behavior is never the baseline.

The exact identity, overlay, RQ, failure, concurrency, and Forest contracts are
normative in
`artifacts/2026-07-30_contract_amendment_delineation_snapshot.md`.

### WBT DEM-boundary behavior

`[watershed.wbt] boundary_touch_behavior` accepts exactly `warn` or `error` and
defaults to `warn`, preserving current WBT behavior. This policy applies only
to the WBT delineation backend.

After WBT produces the subcatchment raster, the existing edge detector finds
positive watershed identifiers on the top, bottom, left, or right raster
edge. When none are present, delineation continues normally. When any are
present:

- `warn` records the edge identifiers, publishes an actionable warning, and
  permits the clipped result to continue;
- `error` raises `WatershedBoundaryTouchesEdgeError` with an actionable message,
  deletes canonical WBT `subwta.tif`, leaves build and abstraction timestamps
  absent, retains sorted edge identifiers as diagnostics, publishes no
  completion trigger, and leaves no ready state downstream work can consume.

The user-visible error is:

> The delineated watershed reaches the DEM boundary and may be clipped. Select
> a different outlet or enlarge the project extent, then delineate again.

The error is an intentional job failure, not a process crash. Existing
rq-engine orchestration remains the job-state authority, while the public
status surface exposes only a sanitized code, the actionable message, and an
`error_id`; internal tracebacks remain operator diagnostics. The failed
subcatchment child prevents dependent abstraction, the root becomes terminal
failed, and retry remains available. No silent fallback from `error` to `warn`
is permitted.

For account-bearing submissions, the route first verifies ordinary run
mutation authority and then resolves the initiating user's preference. That
preference outranks the immutable per-run config baseline.
Resolution and validation finish before any NoDb, Redis, readiness, or queue
mutation. A legacy missing config baseline may then persist only the validated
configuration value under the Watershed lock before any other route mutation;
a failed write stops the request. Non-account-bearing paths retain project
policy. The root stores the exact private snapshot schema defined by the
canonical RQ contract; the child receives only its bounded policy/source
argument. It clears cache, hydrates durable state, validates, constructs a
nonpersistent execution-policy view, and only then begins WBT. Preference
changes after enqueue cannot alter the job or retry.

Every worker/direct/batch attempt clears prior build/abstraction timestamps,
removes prior canonical `subwta.tif`, and replaces prior edge identifiers.
`warn` retains the new raster, logs and publishes the warning on
`<runid>:subcatchment_delineation`, and timestamps success. A later successful
rerun after `error` restores the raster/readiness lifecycle. Older derived
files may remain on disk but downstream preflight must reject them until the
timestamps are rebuilt.

## Objectives

- Add typed, account-scoped preference persistence with an additive Alembic
  migration.
- Add the authenticated, contract-tested PureCSS User Preferences page and
  Profile link.
- Apply per-user unit presentation without durable project mutation and
  deterministically snapshot the initiating user's WBT boundary preference.
- Add the WBT configuration parameter and fail-closed boundary behavior.
- Run focused and full regression gates, independent reviews, a local E2E, and
  an authorized Forest migration/canary.

## Scope

### Included

- SQLAlchemy model, relationship, validation service, and Alembic migration.
- User Preferences GET/POST routes, template, Profile link, CSRF, and tests.
- Request-local user Unitizer presentation for authorized project views and
  conversion endpoints without durable mutation.
- Authorized WBT initiating-user policy resolution and deterministic RQ
  snapshotting for existing, shared, public, and forked runs.
- WBT configuration parsing, persisted Watershed state, warning/error behavior,
  typed exception propagation, diagnostics, and tests.
- User, developer, configuration, operator, and migration documentation.
- A Forest schema migration and authenticated two-user same-project canary
  after local tests and review gates pass.

### Explicitly Out of Scope

- Worker-time live preference lookup.
- Bulk retroactive migration of existing runs or users.
- Re-resolving preferences when a run is forked.
- New Channel Delineation form fields for the boundary policy.
- Changing Unitizer conversion formulas, categories, precisions, canonical
  stored values, or explicit project-mutation controls.
- Changing TOPAZ boundary behavior or WBT edge-detection geometry.
- Production/wepp1 deployment or database migration without separate
  authorization.

## Stakeholders

- **Decision owner**: requesting WEPPcloud operator.
- **User need source**: Mariana's preference for an actionable error over a
  clipped watershed.
- **Implementation owner**: Codex/WEPPcloud maintainers.
- **Required reviewers**: independent governance/correctness and
  operations/security reviewers.

## Success Criteria

- [ ] The contract checkpoint predates all implementation changes.
- [ ] Existing users require no backfill and resolve to `config`/`config`.
- [ ] The page persists only exact enum values under login and CSRF protection.
- [ ] Explicit creation/config units alone determine durable project state;
  account SI/English changes presentation without a Unitizer write.
- [ ] Two authorized users view one byte-stable project in different units.
- [ ] Each account-bearing WBT submission uses the initiating user's current
  boundary preference with a deterministic RQ snapshot and no durable
  account-derived project policy.
- [ ] Synthetic WBT edge fixtures prove `warn`, `error`, no-edge, invalid
  configuration, stale-readiness, determinism, and actionable error behavior.
- [ ] Focused, frontend, stub, RQ graph when applicable, broad Python,
  documentation, migration upgrade/downgrade/upgrade, and review gates pass.
- [ ] Forest migration and canary evidence show the new table, constraints,
  missing-row compatibility, preference save/reload, two-user unit views, and
  distinct WBT behavior on one unchanged run.

## Parameterization ADR Gate

- **Parameterization change present**: yes.
- **ADR required**: yes.
- **ADR**:
  `docs/adrs/ADR-0033-user-defaults-and-wbt-boundary-policy.md` (original
  decision accepted; user-context amendment pending).
- **Decision provenance captured**: yes; the ADR distinguishes the requesting
  operator and Codex from Mariana, whose quoted user need was relayed but who
  was not present in the decision venue.

## Dependencies and Related Packages

- **Depends on**:
  [SURF-14](../20260728_pure_ui_user_profile_session_contract/package.md),
  [SHR-05](../20260728_pure_ui_unitizer_preferences_contract/package.md),
  [SURF-01](../20260729_pure_ui_public_creation_cap_contract/package.md),
  [SURF-04](../20260729_pure_ui_fork_console_contract/package.md),
  [DOM-02](../20260728_project_shell_ui_contract/package.md),
  [DOM-05](../20260728_channel_delineation_ui_contract/package.md), and
  [DOM-05A](../20260729_topaz_conditioning_wepppy_integration/package.md).
- **Governed by**:
  `docs/standards/contract-first-change-standard.md`,
  `docs/schemas/weppcloud-csrf-contract.md`,
  `docs/schemas/rq-response-contract.md`, and
  `docs/schemas/nodb-persistence-concurrency-contract.md`.
- **Blocks**: no unrelated package.

## Security Impact and Review Gate

- **Security impact triage**: `high`.
- **Dedicated security review required**: yes.
- **Rationale**: this adds authenticated account mutation, CSRF-sensitive form
  handling, database schema/state, removal of creation-path preference
  propagation with compatibility coverage, per-user presentation, and failure
  behavior on an RQ worker path.
- **Security artifact**:
  `artifacts/2026-07-30_security_review.md`.

## Incident Hardening Lifecycle

### Trigger and scope freeze

The 2026-07-30 local two-user acceptance left exact failed-create state for
six disposable run IDs in Redis DB 0, DB 11, and DB 13 after SQL and RQ cleanup.
The operator-visible impact was orphaned runtime state and an NFS-held run
directory after an otherwise successful canary. Scope is frozen to making
failed-create and acceptance cleanup exact and observable without changing the
existing public RQ error envelope or broadening project deletion behavior.

### Precedent

The remediation reuses the confinement, correlation, and explicit-failure
rules in this package's security review, the NoDb persistence/concurrency
contract, and `docs/standards/hardening-lifecycle-standard.md`. It deliberately
does not add a public `{cleanup_required, runid}` receipt because that would
create a new cross-cutting response contract after implementation began.
Operators instead correlate the existing public `error_id` to the one internal
record containing the exact `error_id` and generated run ID.

### Hypothesis and signals

**Hypothesis**: if failed-create cleanup closes run-scoped NoDb instances,
purges DB 0/11/13 with strict absence checks, and only then removes the
canonical run directory, new failed creates and disposable canaries will leave
zero exact SQL, RQ, Redis, or filesystem residue.

- **Primary health signals**: zero exact keys for a receipt-bound run in Redis
  DB 0/11/13; zero durable account/run rows and RQ jobs; canonical directory
  absent; one correlated cleanup log on injected failure.
- **Guardrails**: no public run ID disclosure, no sibling/project deletion,
  no Unitizer or Watershed durable mutation, and no increase in unrelated
  create failures.
- **Observation window**: the local fault-injection and two-user canary plus
  14 days after the authorized Forest canary.
- **Observation owner and closure**: the requesting operator owns the Forest
  signal check with the WEPPcloud maintainer; they close the observation 14
  days after the Forest canary only if no exact DB-0/11/13 residue,
  uncorrelated cleanup failure, or out-of-scope deletion is reported.
- **Danger signal and rollback**: any residual exact key, missing correlation,
  or cleanup outside the generated run stops rollout; revert the cleanup
  hardening commit and retain the existing failed run for manual evidence-led
  recovery.
- **Sunset**: the strict postconditions are permanent integrity checks, not a
  temporary retry or fallback callus. Review their necessity after the
  observation window only if evidence shows an owned lower-complexity cleanup
  primitive with the same postconditions.

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions plus Forest canary.
- **Complexity**: high.
- **Risk level**: high because the feature crosses account, project creation,
  NoDb, and worker boundaries.

## Forest Migration Authority

The requesting operator explicitly authorized Codex to run the additive
database migration and disposable authenticated canary on Forest. This
authority is scoped to the reviewed `user_preferences` merge revision and
exact canary from this package and does not authorize production/wepp1
migration or unrelated deployment changes. The schema-first rollout, target
discovery, restore, coordinated restart, abort, cleanup, and post-action audit
gates are defined in the contract decision. Forest remains gated on a
committed checkpoint, completed implementation, passing disposable-PostgreSQL
migration/full-suite tests, and final governance/security reviews.

## References

- `wepppy/weppcloud/app.py` — current User model and SQLAlchemy datastore.
- `wepppy/weppcloud/routes/user.py` — current Profile route owner.
- `wepppy/weppcloud/templates/user/profile.html` — Profile link source.
- `wepppy/nodb/unitizer.py` — project-scoped Unitizer defaults and persistence.
- `wepppy/nodb/core/ron.py` — new-run controller initialization.
- `wepppy/nodb/core/watershed_mixins.py` — WBT subcatchment construction and
  edge identification.
- `wepppy/topo/watershed_abstraction/support.py` — existing raster-edge
  detector.
- `wepppy/microservices/rq_engine/project_routes.py` — canonical new-project
  creation and explicit configuration overrides.
