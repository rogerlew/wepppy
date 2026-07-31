# ADR-0035: Fail WBT Least-Cost Delineation on Unresolved Depressions

Status: Accepted
Date: 2026-07-30

Default update: ADR-0037 supersedes only this ADR's statement that the
configured default distance remains 1,000 m. The fail-on-unresolved behavior
and all incident evidence recorded here remain accepted.

## Context

WhiteboxTools `BreachDepressionsLeastCost` searches only within its configured
distance. WEPPcloud historically enabled Whitebox's `--fill` fallback, which
raises every depression the bounded breach search cannot resolve. On
`srivas42-reconciled-turf/disturbed9002_wbt`, the 1,000 m setting converts to
33 cells, leaves 377 depressions unresolved, and produces a maximum
source-to-conditioned elevation increase of 379.162 m.

Omitting `--fill` alone is insufficient because established Whitebox behavior
writes the no-fill raster and returns success.

## Decision

Add the opt-in `BreachDepressionsLeastCost --fail_on_unresolved` flag to
`weppcloud-wbt`. It returns a nonzero
`WBT_UNRESOLVED_DEPRESSIONS count=<n> max_dist_cells=<n>` error before writing
the requested output when the bounded search leaves any depression unresolved.
Ordinary `--fill=false` behavior remains unchanged for other callers.

WEPPcloud channel delineation invokes least-cost breaching with
`fill=false` and `fail_on_unresolved=true`. It translates the stable native
failure into the controlled RQ error `wbt_unresolved_depressions`, suppresses
the expected traceback from open job information, does not timestamp channel
completion, and presents instructional retry guidance. It never silently
increases the breach distance or changes the conditioning algorithm.

## Decision Provenance

Decision Venue: Codex API workspace thread, 2026-07-30 17:11-17:37 UTC
Participants Present: requesting WEPPcloud operator; Codex
Decision Owner(s): requesting WEPPcloud operator
Implementer(s): Codex

## Change Summary

Old behavior:

- WEPPcloud passed `fill=true`.
- Bounded least-cost search failures were automatically filled.
- A successful output could contain extreme terrain increases.

New behavior:

- WEPPcloud passes `fill=false` and `fail_on_unresolved=true`.
- Any positive unresolved count stops channel delineation before output write.
- The user receives the unresolved count, configured distance, and explicit
  recovery choices.

The configured default distance remains 1,000 m. No formulas, unit
conversions, pruning thresholds, CSA, or MCL values change.

## Rationale

The native algorithm owns the authoritative unresolved count before filling
and can guarantee the requested output was not written. An opt-in flag
preserves upstream-compatible no-fill behavior and avoids brittle stdout
parsing or elevation-difference heuristics.

## Alternatives Considered

1. Set `fill=false` only — rejected because the tool returns success and writes
   a raster containing unresolved depressions.
2. Change every `fill=false` call to fail — rejected because it breaks
   established caller expectations.
3. Infer fallback filling from elevation differences — rejected because valid
   fills have no universal safe magnitude threshold.
4. Automatically enlarge the distance or switch methods — rejected because
   those choices change modeling intent.
5. Parse verbose stdout — rejected as a brittle human-text contract.

## Consequences

Some least-cost channel builds that previously completed through fallback
filling will now require user action. Solvable builds remain unchanged.
TerrainProcessor callers retain their explicit `blc_fill` behavior unless they
opt into the new flag.

The application and fork must be deployed together because older binaries and
wrappers do not recognize the new argument.

## Evidence

- [Work package](../work-packages/20260730_wbt_least_cost_unresolved_depression/package.md)
- Fixture SHA-256:
  `b87f189bf3aa79b7f25542f0982378e193d11164fec55a68f7310e6256a8282a`
- Baseline at 33 cells: 904 solved, 377 unresolved; fill maximum delta
  `+379.16178369142 m`; no-fill maximum delta `+3.3350192187499 m`.
- `weppcloud-wbt` commit
  `17ebe99d92210679f120e83033920109eb99a767`
- Native acceptance: fail-fast exits 1, writes no output, and emits
  `WBT_UNRESOLVED_DEPRESSIONS count=377 max_dist_cells=33`; historical no-fill
  exits 0 and writes output.

## Risk and Rollback Notes

Deploy the WBT fork before or atomically with WEPPpy. Roll back the application
and WBT binary together. Reverting to `fill=true` restores availability but
also restores the extreme-fill scientific risk.

Monitor controlled-error frequency, corrected retries, and unexpected failures
for 30 days. Stop rollout if solvable fixtures fail, canonical partial
artifacts survive, or the controlled error leaks native tracebacks.

## Implementation Notes

The controlled public details are additive:

```json
{
  "unresolved_depression_count": 377,
  "search_distance_m": 1000,
  "search_distance_cells": 33
}
```

Dynamic values are numeric and never interpolated as HTML.
