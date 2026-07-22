# SSURGO Intelligent Fallback Pilot

## Summary

This read-only pilot establishes an initial empirical baseline for the proposed
intelligent SSURGO fallback. It uses the supplied 2025 gNATSGO MUKEY raster as
the complete mapped-area population, then draws MUKEYs uniformly from mapped
pixels and builds them through the current SSURGO-to-WEPP converter.

Across 2,048 independent mapped-pixel draws, 40 draws (1.95%) could not
produce a WEPP soil: 35 were residual-invalid profiles and 5 failed during
conversion because their texture fractions implied negative silt. The 95%
Wilson interval for the combined unbuildable mapped-area rate is 1.44% to
2.65%. This is an **area-weighted pilot estimate**, not an estimate of the
unweighted national MUKEY rate.

The most common observed failures have no usable profile to repair: no returned
component (13 draws) or components with no returned horizons (12 draws).
Where horizon data exist but conversion still fails, missing sand and very-fine
sand are the most frequent observed missing required fields, and inconsistent
texture totals are a distinct conversion failure. These findings support a
two-stage future policy: first repair demonstrably recoverable converter inputs;
then select an existing valid local soil for the remaining residual-invalid
cases using the SSURGO map and, after validation, elevation.

No production run, fallback assignment, or source raster was modified.

## Population and Method

| Item | Value |
| --- | ---: |
| Raster | `/wc1/geodata/ssurgo/gNATSGSO/2025/gNATSGO_mukey_202502.tif` |
| Raster attribute table | `gNATSGO_mukey_202502.tif.vat.dbf` |
| Grid | 30 m, EPSG:5070, 900 m² per pixel |
| Complete mapped pixels | 8,745,483,151 |
| Distinct MUKEYs | 320,669 |
| Sampling design | 2,048 IID uniform mapped-pixel draws with replacement |
| Seed | `20260721` |
| Unique sampled MUKEYs | 1,991 |
| Tabular source | NRCS Soil Data Access through `SurgoSoilCollection` |
| Converter | current `WeppSoil` logic, `initial_sat=0.75`, `ksflag=True` |

The complete raster inventory used the GeoTIFF's companion raster attribute
table (`mukey`, `Count`) rather than a full pixel scan. This is the correct
frequency source for this file and avoids treating an edge NoData block as a
national sample.

The sampled MUKEYs were fetched in 16 batches of at most 128 unique MUKEYs,
then built with eight local converter workers per batch. The sample is
area-weighted because each draw selects one pixel uniformly. Repeated draws of
the same MUKEY were retained as repeated statistical weight.

## Build Outcomes

| Outcome | Draws | Area-weighted rate |
| --- | ---: | ---: |
| Valid WEPP soil | 2,008 | 98.05% |
| Residual-invalid soil | 35 | 1.71% |
| Converter worker failure | 5 | 0.24% |
| Combined unbuildable | 40 | 1.95% |

The five worker failures were not network or Soil Data Access failures. Direct
single-process reproduction showed `ValueError` from Rosetta texture inputs:
all five profiles implied negative silt. Four paired defaulted/missing sand
with high reported clay; one had measured sand and clay totaling more than
100%. They are included in the combined unbuildable rate but remain distinct
from residual-invalid soils so future remediation can address them at the
converter boundary.

## Failure Evidence

Reason codes are not mutually exclusive. For example, a profile may have no
eligible component because its available horizons also lack required fields.

| Reason code | Draws | Area-weighted rate |
| --- | ---: | ---: |
| `no_components` | 13 | 0.63% |
| `no_horizons` | 12 | 0.59% |
| `no_eligible_component` | 10 | 0.49% |
| `no_valid_horizons` | 10 | 0.49% |
| `invalid_required_attributes` | 5 | 0.24% |
| `nonphysical_texture_balance` | 5 | 0.24% |
| `worker_failed` | 5 | 0.24% |
| `missing_sandtotal_r` | 5 | 0.24% |
| `missing_sandvf_r` | 5 | 0.24% |
| `missing_cec7_r` | 3 | 0.15% |
| `missing_claytotal_r` | 2 | 0.10% |
| `missing_dbthirdbar_r` | 2 | 0.10% |
| `missing_om_r` | 2 | 0.10% |
| `missing_ksat_r` | 1 | 0.05% |

Across the nonvalid sampled MUKEYs, raw horizon observations also contained
missing CEC (27 draw-weighted horizon values), sand (20), very-fine sand (20),
bulk density (15), clay (4), organic matter (3), and conductivity (2). Clay
was nonphysical in six additional draw-weighted horizon values. These are raw
horizon observations, not counts of unique MUKEYs, and should not be summed
across fields.

## Implications for the Fallback Design

The pilot supports the strategy's map-first direction.

1. **Do not use one fallback mechanism for every failure.** `no_components`
   and `no_horizons` cases have no profile evidence to impute; selecting a
   valid existing MUKEY from the local SSURGO map is more defensible than
   inventing a hybrid soil.
2. **Repair before selecting a donor when the defect is local and physical.**
   Missing texture/CEC/bulk-density fields and texture-balance errors should be
   evaluated as converter-repair candidates. Any changed default, formula, or
   threshold requires a parameterization ADR.
3. **Derive proximity from the soil raster, not hillslope topology.** The
   sample establishes that fallback is not a negligible edge condition; the
   next evidence must identify neighboring valid MUKEY regions and their
   shared-boundary/distance relationship to each invalid region.
4. **Evaluate elevation only as an aligned raster covariate.** It was not part
   of this pilot. A future test must specify its DEM, resampling, region summary
   statistic, and contribution to a score before using it in a choice.

## Limitations and Next Steps

- This is one date-stamped NRCS retrieval cohort. Source data can change, so
  repeatable cache/provenance capture is required before comparing future runs.
- The IID pixel design estimates mapped area, not the prevalence among unique
  MUKEYs, geographic regions, or individual watersheds.
- The sample does not yet construct connected MUKEY regions, shared boundaries,
  candidate valid soils, or elevation summaries. It cannot choose a fallback.
- The current research runner derived field-level completeness from returned
  component/horizon rows. The planned structured production collector should
  record the same information at the build boundary without relying on a
  separate rerun.

Next, build deterministic fixtures for the observed classes (no component, no
horizons, missing required texture fields, and nonphysical texture balance),
then construct raster-region adjacency and aligned elevation evidence for the
invalid MUKEYs. Compare local map candidates against the watershed-global
baseline in masked-valid trials before proposing a production score.

## Reproducibility Artifacts

The local, non-versioned study directory is
`/tmp/ssurgo_empirical_study_20260721/`:

- `gnatsgo_2025_mukey_inventory.json` — complete VAT-derived MUKEY pixel
  inventory.
- `gnatsgo_2025_area_weighted_pilot_2048.jsonl` — per-MUKEY diagnostic records
  with draw weights.
- `gnatsgo_2025_area_weighted_pilot_2048_summary.json` — aggregate outcomes.
- `gnatsgo_2025_area_weighted_pilot_2048_diagnostic_summary.json` — validated
  reason-code aggregation.

The raw diagnostic JSONL is intentionally not committed: it is a large,
date-sensitive external-data extract. The inventory and JSONL can be recreated
with `tools/ssurgo_empirical_study.py`, the recorded raster path, seed, and
converter settings above. The current scaffold is documented in
`docs/planning/ssurgo-intelligent-fallback-strategy.md`.
