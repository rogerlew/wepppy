# Account User Preferences and WBT Boundary Policy

**Status**: Open (2026-07-30)

**Timezone**: UTC

**Package ID**: SURF-14A

**Parent owners**: SURF-14 User Profile/Session, SHR-05 Unitizer Preferences,
and DOM-05 Channel Delineation

## Overview

Add an authenticated User Preferences page where a person can choose the
default unit system for new projects and decide whether a WBT watershed that
reaches the DEM boundary may continue with a warning or must stop with an
actionable error. Preferences are account-scoped PostgreSQL state, while the
effective values are snapshotted into each new run so later account changes do
not silently change an existing project's behavior.

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
existing PureCSS account layout and uses the existing Pure form macros. The
server renders and validates the complete form; no new browser controller is
required.

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
field errors and no database mutation. Successful submission commits both
values in one transaction and follows a POST/Redirect/GET flow with a visible
success message.

### Effective-value precedence and run compatibility

For new projects, explicit per-project creation input has highest precedence,
then a non-`config` account preference, then the selected project
configuration. The existing explicit `unitizer:is_english` creation override
therefore remains authoritative when supplied. There is no explicit
per-project boundary-policy input in this package.

The effective values are resolved before `Ron` initializes the run and are
snapshotted into the run's existing configuration/NoDb state:

1. `si` maps to `unitizer:is_english=false`;
2. `english` maps to `unitizer:is_english=true`;
3. `config` preserves `[unitizer] is_english`;
4. boundary `warn` or `error` overrides
   `[watershed.wbt] boundary_touch_behavior`;
5. boundary `config` preserves that configuration value.

Anonymous/CAP creation and an authenticated identity without a preference row
use the project configuration. An invalid persisted value, database error, or
authenticated preference-resolution failure is explicit and must not silently
create a project with different defaults.

Preference edits affect only projects created afterward. Existing runs retain
their persisted Unitizer selections and WBT boundary policy. Forks copy the
source run's effective values and do not re-resolve the destination owner's
account preferences. Shared-run viewers do not dynamically alter run behavior.

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
  does not mark subcatchment construction complete, and leaves no stale
  ready-state that downstream work can consume.

The user-visible error is:

> The delineated watershed reaches the DEM boundary and may be clipped. Select
> a different outlet or enlarge the project extent, then delineate again.

The error is an intentional job failure, not a process crash. Existing
rq-engine typed error handling remains the response authority. No silent
fallback from `error` to `warn` is permitted.

## Objectives

- Add typed, account-scoped preference persistence with an additive Alembic
  migration.
- Add the authenticated, contract-tested PureCSS User Preferences page and
  Profile link.
- Resolve and snapshot defaults for every supported new-project creation path
  without changing explicit creation choices, existing runs, or forks.
- Add the WBT configuration parameter and fail-closed boundary behavior.
- Run focused and full regression gates, independent reviews, a local E2E, and
  an authorized Forest migration/canary.

## Scope

### Included

- SQLAlchemy model, relationship, validation service, and Alembic migration.
- User Preferences GET/POST routes, template, Profile link, CSRF, and tests.
- Authenticated new-project preference resolution and run snapshotting.
- WBT configuration parsing, persisted Watershed state, warning/error behavior,
  typed exception propagation, diagnostics, and tests.
- User, developer, configuration, operator, and migration documentation.
- A Forest schema migration and authenticated new-project canary after local
  tests and review gates pass.

### Explicitly Out of Scope

- Dynamic per-viewer units for existing/shared projects.
- Retroactive migration of existing runs or users.
- Re-resolving preferences when a run is forked.
- New Channel Delineation form fields for the boundary policy.
- Changing Unitizer conversion formulas, categories, precisions, or the
  run-scoped Unitizer modal contract.
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
- [ ] Explicit creation units outrank account preferences; account preferences
  outrank configuration; anonymous and fork behavior matches this contract.
- [ ] New runs persist effective unit and WBT boundary values.
- [ ] Synthetic WBT edge fixtures prove `warn`, `error`, no-edge, invalid
  configuration, stale-readiness, determinism, and actionable error behavior.
- [ ] Focused, frontend, stub, RQ graph when applicable, broad Python,
  documentation, migration upgrade/downgrade/upgrade, and review gates pass.
- [ ] Forest migration and canary evidence show the new table, constraints,
  missing-row compatibility, preference save/reload, and one new-run snapshot.

## Parameterization ADR Gate

- **Parameterization change present**: yes.
- **ADR required**: yes.
- **ADR**:
  `docs/adrs/ADR-0033-user-defaults-and-wbt-boundary-policy.md` (draft).
- **Decision provenance captured**: yes; the ADR distinguishes the requesting
  operator and Codex from Mariana, whose quoted user need was relayed but who
  was not present in the decision venue.

## Dependencies and Related Packages

- **Depends on**:
  [SURF-14](../20260728_pure_ui_user_profile_session_contract/package.md),
  [SHR-05](../20260728_pure_ui_unitizer_preferences_contract/package.md), and
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
  handling, database schema/state, creation-path preference propagation, and
  failure behavior on an RQ worker path.
- **Security artifact**:
  `artifacts/2026-07-30_security_review.md`.

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions plus Forest canary.
- **Complexity**: high.
- **Risk level**: high because the feature crosses account, project creation,
  NoDb, and worker boundaries.

## Forest Migration Authority

The requesting operator explicitly authorized Codex to run the additive
database migration on Forest. This authority is scoped to the reviewed
`user_preferences` migration from this package and does not authorize
production/wepp1 migration or unrelated deployment changes. The Forest
migration remains gated on a committed contract checkpoint, completed
implementation, passing local migration/full-suite tests, and final
governance/security reviews.

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
