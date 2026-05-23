# Recommendation Memo - SSURGO Corestrictions `kslast` Viability

Generated: 2026-05-23 00:54:49 UTC

## Decision: **retain legacy**

## Basis

- Regions meeting minimum sample sufficiency (>=300 sampled components target bins with >=75 in each bin): 6/12.
- Regions with execution-limited restrictive-present sample shortfall (<150 due SDA extraction/runtime constraints in this run): 6/12.
- Regions with unresolved reasonableness anomalies: 9/12.
- Regions with high Candidate-B fallback usage (>20% sample): 12/12.

## Guardrails

- Keep legacy fallback `0.01` mm/h whenever restrictive-layer evidence is missing or inconsistent.
- Gate candidate application on minimum field completeness thresholds (`resdept_r`, `ksat_r`, and class/hardness where used).
- Clamp outputs to hard bounds `[0.0005, 0.05]` mm/h to avoid pathological conductivity values.
- Treat regional anomaly hotspots as opt-out zones until validated by explicit WEPP run fixtures.

## Implementation Gating Checklist (follow-up package)

- Define and freeze a representative ecoregion WEPP run fixture matrix (single OFE + watershed signals).
- Re-run legacy vs candidate on full hydrograph metrics (runoff volume, peak runoff, hydrograph smoothness, infiltration/percolation terms).
- Add production tests around fallback behavior and bounds enforcement.
- Add operator-facing observability for candidate vs legacy selected path and bound/fallback hits.
