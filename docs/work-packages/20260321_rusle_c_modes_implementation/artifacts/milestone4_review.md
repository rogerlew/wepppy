# Milestone 4 Correctness Review

Date: 2026-03-21
Reviewer: Codex (correctness pass)
Scope: `wepppy/nodb/mods/rusle/c_*.py`, `tests/nodb/mods/test_rusle_c_*.py`, package docs, and spec/tracker updates.

## Findings

No unresolved high or medium correctness findings.

## Checks Performed

- Reviewed `observed_rap` contract implementation:
  - `fg = clamp(100 - bare_ground_pct, 0, 100)`
  - `C = exp(-0.04 * fg)`
  - neutral canopy/roughness/biomass/consolidation terms
- Reviewed RAP alignment/nodata behavior:
  - DEM-grid alignment via raster reprojection
  - union-mask behavior across required RAP cover bands
  - preservation of `>100` bare-ground values until the contract clamp applies
- Reviewed `scenario_sbs` contract implementation:
  - disturbed-family normalization from `disturbed.json`
  - burn-only application to `forest`, `shrub`, and `tall_grass`
  - explicit masking of water/developed/wetland/ice-snow classes
  - fail-fast behavior for missing required lookup rows
- Reviewed auditability contract:
  - `c.tif`, `c_fg.tif`, `disturbed_class.tif`, `sbs_4class.tif`, and lookup-copy artifact paths
  - `manifest.json` mode metadata and lookup-key reporting
  - catalog refresh coverage for new artifacts

## Outcome

Milestone 4 review pass complete with no unresolved high/medium issues.

