# Legacy vs Candidate Summary - SSURGO Corestrictions `kslast`

Generated: 2026-05-23 00:54:49 UTC

## Candidate Definitions

- Candidate A (Depth-gated legacy anchor): `legacy_anchor * depth_factor * hardness_factor`, bounded to `[0.0005, 0.05]` mm/h.
- Candidate B (Restriction-class transfer): `legacy_anchor * class_factor * depth_factor * hardness_factor`, bounded to `[0.0005, 0.05]` mm/h.
- Fallback for missing restrictive signal or missing positive `ksat_r`: `0.01` mm/h.

## Input-space Comparison

These comparisons are on sampled components (`component_sample.csv`), with explicit restrictive-present and restrictive-absent bins. Regions with restrictive-present shortfalls should be interpreted as low-confidence for directional inference because bin completion was infrastructure-limited (SDA extraction/runtime), not because SSURGO records are presumed missing.

| Ecoregion | Sample n | Candidate A mean delta vs legacy (mm/h) | Candidate B mean delta vs legacy (mm/h) | A < legacy | B < legacy |
|---|---:|---:|---:|---:|---:|
| Marine West Coast Forest | 300 | -0.004802 | -0.008706 | 47.67% | 48.00% |
| Cascades | 300 | -0.009434 | -0.015101 | 42.67% | 44.00% |
| Sierra Nevada | 300 | -0.006336 | -0.007838 | 29.33% | 43.00% |
| Mediterranean California | 300 | -0.003420 | -0.005623 | 40.33% | 42.33% |
| Columbia Plateau / Intermountain Basins | 286 | -0.007690 | -0.009319 | 38.81% | 38.81% |
| High Plains / Northern Great Plains | 250 | -0.003406 | -0.005922 | 27.20% | 27.20% |
| Central Corn Belt Plains | 236 | -0.000831 | -0.001299 | 34.75% | 34.75% |
| Ridge and Valley / Blue Ridge | 300 | -0.006722 | -0.011218 | 33.33% | 34.33% |
| Southeastern Plains | 192 | -0.000767 | -0.001297 | 20.31% | 20.31% |
| Southern Coastal Plain | 231 | -0.014828 | -0.018079 | 32.03% | 32.47% |
| Mississippi Alluvial Plain | 178 | -0.000342 | -0.000504 | 15.73% | 15.73% |
| Mojave/Chihuahuan Basin and Range | 300 | -0.002158 | -0.002887 | 19.00% | 19.33% |

## M4 Hydrologic Comparison Scope

- This package runs representative **input-space** and directional hydrologic proxy comparisons (changes in restrictive-layer conductivity imply runoff/infiltration direction changes).
- Full WEPP hydrograph re-runs per ecoregion are not executed in this package because a pre-approved, reproducible run fixture matrix is not yet defined here.
- Therefore, M4 conclusions are an investigation signal and should be confirmed with explicit run fixtures in follow-up implementation gating.
