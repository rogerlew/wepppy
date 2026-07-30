# ADR-0033: Account Defaults and WBT DEM-Boundary Policy

**Status**: Accepted

**Date**: 2026-07-30

## Context

WEPPcloud project configurations currently choose initial Unitizer behavior,
and WBT delineation records watershed identifiers found on the DEM raster
edges without a configurable continue/fail policy. A user may prefer consistent
default units across new projects. Mariana also stated that an actionable error
requesting another outlet or a larger extent is preferable to silently
accepting a clipped watershed.

Account preferences and project configuration have different lifetimes. A live
account value must not change existing, shared, or forked run behavior.

## Decision

Add two account preferences:

- unit system: `config` (default), `si`, or `english`;
- WBT DEM-boundary behavior: `config` (default), `warn`, or `error`.

For new projects, precedence is explicit per-project creation input, then a
non-`config` account preference, then project configuration. Snapshot the
effective values into the new run before NoDb initialization. Existing runs
and forks do not re-resolve account preferences.

Persist the new-run WBT choice as
`Watershed._wbt_boundary_touch_behavior`. Legacy Watershed state missing this
field hydrates to `warn` and preserves that compatibility value through
archive/restore and forks regardless of later configuration or account
changes.

Add `[watershed.wbt] boundary_touch_behavior` with accepted values `warn` and
`error` and default `warn`. `warn` preserves current behavior. `error` raises
the existing typed edge exception and prevents a clipped result from becoming
ready for downstream work. The user-visible choice is `Stop with an error`.

## Parameterization Delta

Previously, project `[unitizer] is_english` always supplied the initial unit
system unless an explicit creation override was present. After this decision, a
non-`config` authenticated account preference overrides that configuration for
new projects only.

Previously, WBT edge contact continued after recording edge hillslopes. After
this decision, the explicit `error` mode stops with an actionable typed error.
The default remains warning/continue, so users, configs, and existing runs do
not change behavior without an explicit selection.

No conversion formula, precision, measurement category, raster-edge test,
conditioning algorithm, or hydrologic threshold changes.

## Decision Provenance

Decision Venue: Codex API workspace thread, 2026-07-29 21:10 PDT
(2026-07-30 04:10 UTC)

Participants Present: requesting WEPPcloud operator; Codex

Stakeholder Input: Mariana's quoted preference was relayed by the operator;
Mariana was not present.

Decision Owner(s): requesting WEPPcloud operator

Implementer(s): Codex/WEPPcloud maintainers

The operator first approved the `Stop with an error` label, scaffold, and
Forest migration, then instructed Codex to execute the named SURF-14A package.
That instruction approves the complete documented delta: typed storage, enums,
precedence, missing-row behavior, snapshot/fork compatibility, `warn` default,
failure semantics, and the contained Forest canary.

## Rationale

Account `config` defaults preserve project authorship and existing behavior.
Snapshotting removes mutable profile state from asynchronous and shared-run
execution. Retaining `warn` as the WBT config default avoids an unrequested
behavior change, while `error` gives users/config authors a fail-closed option.
`Stop with an error` communicates intentional behavior more accurately than
`Crash`.

## Alternatives Considered

Defaulting the account boundary preference to `warn` was rejected because it
would override configs set to `error` for every existing user. Resolving live
preferences on every report/job was rejected because it would make results
viewer-dependent. Storing account defaults in cookies, JSON, generic key/value
state, or run NoDb was rejected because those choices weaken validation,
cross-device consistency, or lifetime boundaries. Automatically enlarging the
extent or moving the outlet was rejected because either action changes the
user's geospatial intent.

## Evidence

- `wepppy/nodb/unitizer.py` reads `[unitizer] is_english` and persists
  run-scoped preferences.
- `wepppy/microservices/rq_engine/project_routes.py` applies explicit creation
  overrides before `Ron` initialization.
- `wepppy/topo/watershed_abstraction/support.py` identifies positive values on
  all four raster edges.
- `wepppy/nodb/core/watershed_mixins.py` invokes that detector after WBT
  subcatchment delineation.
- Work package:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`.

Implementation, synthetic fixture, local E2E, and Forest canary evidence remain
pending.

## Risk and Rollback

Primary risks are overriding an explicit project selection, changing existing
or forked runs, silently falling back when account persistence fails, leaving
stale ready state after an edge error, and deploying incompatible schema/code.
The contract requires exact precedence tests, snapshot evidence,
failure-atomic creation, stale-readiness tests, additive migration, and staged
Forest validation.

Application rollback may ignore the additive table while preserving its rows.
Migration downgrade is optional and must not run if it would discard preference
rows without explicit operator approval and backup. Reverting the WBT config
default is unnecessary because it preserves prior warning behavior; disabling
the resolver/page restores config-only creation while retaining stored rows for
later recovery.
