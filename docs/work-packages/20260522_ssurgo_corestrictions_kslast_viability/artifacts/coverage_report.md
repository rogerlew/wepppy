# Coverage Report - SSURGO Corestrictions `kslast` Viability

Generated: 2026-05-23 00:54:49 UTC

## M0 Freeze

- Baseline legacy behavior definition anchored to current `wepppy/soils/ssurgo/ssurgo.py` and `wepppy/soils/ssurgo/ssurgo.md` (non-AG: `0.01` mm/h when no restrictive layer; restrictive case uses `(res_lyr_ksat_um_s * 3.6) / 1000` mm/h).
- Production code was not modified by this assessment package.
- Exact extraction workflow is captured in `artifacts/run_corestrictions_kslast_viability.py` and `artifacts/query_provenance.json`.

## National Coverage

- Components total: 1288808
- Components with any corestrictions row: 366652 (28.4%)
- Components with `resdept_r`: 365391 (99.7% of restrictive components)
- Components with `reshard`: 315923 (86.2% of restrictive components)
- Components with positive `ksat_r` horizon support: 1024472 (79.5%)

## Ecoregion Coverage

Per-ecoregion denominators in this table are **sampled component counts** (not full-region census counts).  
Restrictive-present shortfalls reported below are execution-time extraction constraints (SDA query/runtime limits in this run), not a claim that SSURGO lacks underlying records.
Sampling method:
- `Marine West Coast Forest`, `Cascades`, `Sierra Nevada` used polygon-ranked top-component extraction.
- Remaining regions used bounded point-sampling (two rounds) plus component enrichment on discovered `mukey` values.

| Ecoregion | Components | Restrictive components | `resdept_r` given restrictive | `reshard` given restrictive |
|---|---:|---:|---:|---:|
| Marine West Coast Forest | 300 | 50.00% | 100.00% | 100.00% |
| Cascades | 300 | 50.00% | 100.00% | 100.00% |
| Sierra Nevada | 300 | 50.00% | 99.33% | 99.33% |
| Mediterranean California | 300 | 50.00% | 100.00% | 100.00% |
| Columbia Plateau / Intermountain Basins | 286 | 47.55% | 99.26% | 100.00% |
| High Plains / Northern Great Plains | 250 | 40.00% | 100.00% | 98.00% |
| Central Corn Belt Plains | 236 | 36.44% | 100.00% | 93.02% |
| Ridge and Valley / Blue Ridge | 300 | 50.00% | 100.00% | 96.67% |
| Southeastern Plains | 192 | 21.88% | 97.62% | 90.48% |
| Southern Coastal Plain | 231 | 35.06% | 100.00% | 100.00% |
| Mississippi Alluvial Plain | 178 | 15.73% | 100.00% | 92.86% |
| Mojave/Chihuahuan Basin and Range | 300 | 50.00% | 100.00% | 100.00% |

### Low-Confidence Regions (Execution-Limited Restrictive-Present Bin Completion)

- `Columbia Plateau / Intermountain Basins` (`n_present=136`, target `150`)
- `High Plains / Northern Great Plains` (`n_present=100`, target `150`)
- `Central Corn Belt Plains` (`n_present=86`, target `150`)
- `Southeastern Plains` (`n_present=42`, target `150`)
- `Southern Coastal Plain` (`n_present=81`, target `150`)
- `Mississippi Alluvial Plain` (`n_present=28`, target `150`)

## Notes

- Denominators are explicit in all CSV artifacts (`national_coverage.csv`, `ecoregion_coverage.csv`).
- `ecoregion_comparison_matrix.csv` is the integration table for M1-M4.
