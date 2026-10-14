# ADR-0093: Observed flow-duration conversion and population

Status: Accepted; implemented and locally validated. Date: 2026-10-14.

## Context and decision

Add an optional observed daily flow-duration curve to both simulated sources.
Observed accepts Streamflow (mm). Reuse its model-fit watershed-area convention:
maximum Area from project totalwatsed3.parquet, finite and positive. Convert to
m³/s by depth × area / 1000 / 86400. Use all observed dates without simulated
warm-up and rank independently using existing Weibull 100m/(N+1). Default off.

## Rationale and alternatives

The same measured distribution should compare to either model source. Matched
model-fit CSVs would silently restrict dates and require extra processing. Applying
simulation warm-up would discard real measurements. Common-date intersection
would change the accepted independent-population graph policy. No invented area
or automatic unit guessing is permitted.

## Decision provenance

Venue: user/Codex workspace conversation, 2026-10-14, America/Los_Angeles.
Participants: requesting operator and Codex. Decision owner: operator authorizes
the optional overlay; Codex selects these implementation details within scope.
Implementer: Codex. Change: no observed overlay previously; add explicit depth
conversion and full-record population. No model parameterization is changed.

## Evidence, risks and rollback

Source: Observed._load_hillslope_simulation uses maximum Area; parse_textdata writes
zero-based Julian. Contract: docs/ui-docs/contracts/gl-dashboard-flow-duration-contract.md,
Observed streamflow overlay. Execution evidence: work package
20261014_gl_dashboard_observed_flow_duration. Different record periods can mislead;
show period/N and full-record policy. Invalid/missing area disables observation
only. Roll back additive overlay code; persisted artifacts need no migration.

## Resource bounds

Bound eager CSV transport to 16 MiB and 100,000 rows. Oversize means explicitly
unavailable, never a partial distribution. These conservative page-size limits
cover over 270 daily years and prevent an optional upload from unbounded dashboard
allocation. They do not alter accepted samples or persisted uploads.
