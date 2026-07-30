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
