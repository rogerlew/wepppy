# EDDE v2 feasibility findings

**Study date**: 2026-10-13 UTC. **Disposition**: extraction and experimental daily replay are feasible; **hold WEPPcloud production integration** pending the scientific and integration gates below. No application mode, locale capability, NoDb state, RQ wiring, or deployment was changed.

## Scope clarification

The operator clarified that the application scope is future climate only. Historical EDDE runs are diagnostic baselines for source assessment and future-change checks, not a proposed historical climate method. Existing CLIGEN quality-guard failures and PRN/CLI quantization are known limitations; retain their reporting and current safeguards, but do not require this package to solve them as new integration blockers. This clarification does not approve a bias correction or decide how future auxiliary fields or PRISM temperature inversions should be handled.

## What was executed

The new public-S3 client queried 15 eligible U.S./Canadian locations across 120 model-years: both models in 1995–2014, both models' SSP2-4.5 in 2060–2079, and MPI SSP2-4.5/SSP3-7.0 in 2080–2099. A separate [native metadata audit](artifacts/native-metadata-audit.json) checked all 4,320 monthly objects: grid axes/CRS, both published time encodings, source units, and manifest endpoints agree. All 657,450 point-days passed completeness, finiteness, precipitation nonnegativity, and temperature-order checks. [Source quality](artifacts/source-quality.json) and [reproducible evidence archive index](artifacts/evidence-index.json).

The 42 full-period CLIGEN attempts produced 32 successful climates; ten stopped at the existing quality guard. Successful files drove **69 fresh 20-year WEPP hillslope runs**: 45 single/PRISM runs on six actual U.S. hillslope fixtures, and 24 Canadian-point climate smoke runs using one frozen U.S. hillslope. Canadian smoke tests are not acceptance on Canadian watershed geometry. A separate one-year pilot passed 59 WEPP runs; the current development-container check passed single and PRISM EDDE input through CLIGEN and WEPP under its configured identity. [U.S. executions](artifacts/workflow-execution-full.json), [Canadian cases](artifacts/canadian-workflows-full.json), [container evidence](artifacts/container-acceptance.json).

## Coverage and available combinations

| Driving model | Historical listing | Future listing inspected |
| --- | --- | --- |
| MPI-ESM1-2-HR (`WRF-MPI`) | 1985–2014 | SSP2-4.5 and SSP3-7.0, 2025–2099 |
| NorESM2-MM (`WRF-Nor`) | 1985–2014 | SSP2-4.5, 2025–2079; no SSP3-7.0 directory |

The published folder name `2025-2100` is not an inclusive availability contract. The queried terminal years end on December 31, 2099 (MPI) and December 31, 2079 (NorESM). Re-inventory before offering choices. [Live inventory](artifacts/archive-inventory.json); exact file/timestamp records are retained in `point-data.tar.gz`.

Vancouver, Calgary, Edmonton, Winnipeg, Toronto, Montreal, Quebec City, and Halifax select valid land cells in both grids and have complete records in the studied windows. Yellowknife is outside the domain. All three sampled Topanga hillslopes and the Miami point select ocean-mask cells despite being land locations: these are rejected rather than moved to a nearby cell. Interior/edge/outside probes exercise native projected geometry, not a geographic bounding rectangle. [Location matrix](artifacts/location-eligibility.json), [edge probes](artifacts/native-edge-probes.json).

Existing locale identifiers are `us` and `canada`; `bc-ca` also exists in legacy British Columbia configuration. These are candidate presentation filters for the successor package, not enabled capabilities. All require actual project and required-hillslope eligibility. The eight Canadian cities fail the tested PRISM January precipitation grid coverage check; EDDE eligibility therefore does not establish Multiple PRISM eligibility. The six U.S. study hillslopes have retained all-month precipitation/temperature normals. [PRISM exclusion probe](artifacts/prism-coverage-probe.json).

## Data quality and bias

The actual inspected daily objects are NetCDF3 classic, rather than the registry's generic compressed-NetCDF4 description. Daily `PRECIP` is kg/m², numerically mm; `T2MAX`/`T2MIN` are 2 m air temperatures in Kelvin. Direct file indexing agrees with extracted CSV values at native float32 precision. Same-labeled 00:00–23:00 UTC hourly precipitation sums agree with daily totals within **1.22 × 10⁻⁶ mm** over 465 point-days; shifting hourly timestamps by an hour produces much larger differences. [Direct parity](artifacts/warm-cache-and-direct-parity.json), [aggregation check](artifacts/hourly-daily-precipitation-parity.json).

Historical bias is material and spatially variable. The table compares 1995–2014 mean annual precipitation on common calendar days against Daymet's observed-data interpolation. It does not treat individual simulated dates as forecasts.

| Point | MPI precipitation bias | NorESM precipitation bias |
| --- | ---: | ---: |
| Vancouver | −4.6% | −12.1% |
| Calgary | +81.2% | +84.8% |
| Edmonton | +64.1% | +77.1% |
| Toronto | +43.8% | +19.9% |
| Phoenix | +130.6% | +75.3% |
| Tiger-Mill study reference (`apostolic-saw-h122`) | +22.8% | +5.0% |
| Cascade foothills reference (`cryptic-beechnut-h78`) | +22.8% | +12.9% |

Across all points, mean daily maximum-temperature bias ranges from −4.07 to +1.40 C and minimum-temperature bias from −2.79 to +3.90 C. Scale/terrain mismatch, reference interpolation, differing day definitions, model bias, and finite sample variability all affect interpretation. Daymet is not independent raw station data. No universal bias cutoff or correction was invented. [Complete bias table](artifacts/historical-daymet-bias.csv), [figure](artifacts/historical-bias.png), [monthly climate](artifacts/monthly-climate.csv), [assessment conventions](artifacts/assessment-conventions.json).

Future signals remain model/scenario dependent. For Toronto in 2060–2079 SSP2-4.5, mean maximum temperature increases about 2.37 C (MPI) or 2.52 C (NorESM), and annual precipitation increases about 9.6% or 18.7% relative to each model's 1995–2014 baseline. These are raw modeled changes, not bias-corrected local predictions. [All future changes](artifacts/future-changes.csv).

## CLIGEN and Multiple PRISM

The experimental adapter replays EDDE precipitation and temperature through the existing CLIGEN PRN interface with explicit station/seed and no quality bypass. Maximum source-to-CLI differences across successful full-period files were 0.17693 mm precipitation and 0.32222 C temperature, within documented PRN/CLI quantization. Small wet amounts can round to zero; 31,665 source-positive days across the successful generated files became dry. This count uses any positive source amount, distinct from the >=1 mm wet-day definition in climate statistics. [Generated-climate checks](artifacts/generated-climate-quality.json), [ADR-0091](../../adrs/ADR-0091-edde-v2-experimental-daily-replay.md).

The ten rejected generations comprise both historical `cryptic-beechnut` reference cases, both historical Vancouver cases, and both models' future Calgary, Edmonton, and Halifax cases. These are specific selected-station/seed failures, not proof that every station or seed fails. They remain explicit failed experiments; no seed search, station substitution, or quality bypass was used.

Multiple PRISM applies existing monthly precipitation ratios and temperature offsets, using the same normals for historical and future climates. Twenty-one of 24 attempted full-period PRISM revisions passed. Three revisions at `cryptic-beechnut-h132` would invert daily temperature extrema: five days in MPI SSP2-4.5, two in NorESM SSP2-4.5, and eight in MPI SSP3-7.0; maximum inversion was 0.5 C. They are rejected without clamping. PRISM coverage alone cannot guarantee valid revision. [Generation/rejection records](artifacts/workflow-generation-full.json).

The inversion mechanism is generic to independent PRISM temperature offsets, not specific to EDDE: revised daily range equals source daily range plus the Tmax offset minus the Tmin offset. For the retained Cascade reference h78 to target h132 pair, January offsets are -1.1 C (Tmax) and -0.6 C (Tmin), shrinking the range by 0.5 C; a source range below 0.5 C can invert. December also shrinks the range by 0.5 C. Existing `wepppy/climates/prism/__init__.py:prism_revision` applies these same independent offsets without an explicit ordering check. Occurrence is demonstrated for EDDE; frequency in other datasets has not been established. The operator directed that this be documented as a known spatialization limitation, not a separate EDDE integration blocker. This documentation decision does not change executable behavior: the experimental EDDE adapter currently rejects affected revisions, while the existing generic PRISM routine is unchanged.

For supported historical/future pairs, 108 monthly checks retain additive temperature changes to floating-point precision. The largest absolute precipitation-ratio difference after CLI rounding is 0.007491 (about 0.75 percentage points when expressed as percentage change). These paired checks cover the Tiger-Mill group; the other group's historical quality-guard failures prevent equivalent full-period claims. Seasonal wet-day frequencies, spells, and precipitation extremes before/after revision are retained for 36 seasonal pairs in [seasonal diagnostics](artifacts/prism-seasonal-extremes.csv). Across those pairs, the revised-minus-base change in wet-day fraction spans −0.00720 to +0.00388, and the difference in daily P99 change spans −2.116 to +4.900 mm. These reflect spatial scaling and threshold/rounding effects, not a claim that extremes are invariant. DJF uses calendar-year grouping for seasonal maxima; discontinuous season boundaries reset spell lengths. The fixed 1 mm wet-day definition is a diagnostic, not a source correction. Multiple Interpolated remains excluded. [Signal checks](artifacts/prism-future-signal.csv).

Storm structure, intensity, radiation, wind, and dewpoint remain station-derived rather than directly EDDE-derived. Their future response is unvalidated. In the January 1995 Tiger-Mill pilot, hourly-sampled EDDE radiation corresponds to roughly 161 Langleys/day versus 95 from CLIGEN, and mean wind is 7.13 versus 3.55 m/s. This limited diagnostic confirms that the auxiliary fields are not interchangeable; it does not validate a full-period replacement. [Auxiliary comparison](artifacts/auxiliary-station-comparison.json). No successful generated record has dewpoint above daily maximum temperature, but 101,097 records have dewpoint above daily minimum temperature; no clipping was applied. The CLI header still describes the auxiliary station and nominal CLIGEN simulation length; actual source point and dates are explicit in the manifest and daily rows. These are integration/scientific limitations, not hidden corrections.

WEPP precipitation readback agrees with exact consumed CLI values within water-output formatting. All successful executions have finite daily outputs and positive minimum soil-water storage. Annual flux/storage diagnostics cover 1,380 case-years. For years with a preceding storage state, the partial annual balance residual ranges from −0.113 to +2.889 mm. It excludes some storage/flux terms and does not establish calibrated hydrology or complete water-balance closure. [Annual diagnostics](artifacts/annual-water-diagnostics.csv).

## Acquisition cost and implementation

A 20-year, three-variable extraction for 15 points reads about **23.26 GB** of monthly source objects and took **20–22 minutes** per sequential worker in this concurrent study. Peak process resident memory stayed below approximately **158 MiB**. The complete 120-model-year study transferred about 139.55 GB; native files remain in scratch cache and compact point/manifests are archived. One-year verified warm-cache extraction took 7.5 seconds versus 72 seconds cold and downloaded no weather bytes. [Benchmarks](artifacts/acquisition-benchmarks.csv).

This establishes a bounded batch path, not interactive latency. Existing asynchronous climate orchestration is the first integration candidate; no new service or archive mirror was needed to complete acceptance. Integration still needs explicit storage retention, timeout, admission, and concurrent-cache ownership decisions. The client is documented in [usage notes](notes/client-usage.md) and the [durable contract](../../schemas/edde-v2-experimental-client-contract.md).

## Required handoff gates

1. Document the interpretation of raw future projections and their model-bias limitations. Historical comparisons are supporting diagnostics, not an in-scope historical method or an automatic requirement to build bias correction. Any proposed adjustment requires a separate scientific decision and future-signal validation.
2. Decide how to derive or validate future storm structure, radiation, wind, and dewpoint. Hourly fields and 5-minute precipitation exist in inspected inventories; this study did not build full-period source-derived auxiliary weather.
3. Document the generic PRISM temperature-inversion limitation and expose the actual workflow outcome; this is not a separate EDDE integration blocker. Preserve existing CLIGEN failure reporting and rounding behavior as known limitations; resolving those existing limitations is not a new EDDE integration prerequisite. Do not bypass, clamp, or silently relocate.
4. Confirm project-level eligibility and actual Canadian project/locale acceptance in the integration environment. The current Canadian consumer runs use a U.S. hillslope fixture.
5. Resolve the existing broad-suite regression gate before package closeout. Independent correctness and security reviews assess the bounded research implementation separately from scientific production adoption; their artifacts are linked below.

The [integration package](../20261013_edde_v2_weppcloud_integration/package.md) remains gated. This study supports a reusable research client and identifies concrete blockers; it does not authorize production rollout.

## Data references

EPA Dynamically Downscaled Ensemble (EDDE), Version 2, U.S. EPA (2024), [DOI 10.23719/1531941](https://doi.org/10.23719/1531941), accessed 2026-10-13 via the [AWS registry](https://registry.opendata.aws/epa-edde-v2/). Dataset methodology: [Mallard et al., 2025](https://doi.org/10.1016/j.dib.2025.112070). Public Daymet single-pixel request URLs and hashes are retained with each reference series; PRISM 1991–2020 normals and native-grid provenance are retained in the cited prior study and current coverage/normal manifests.

## Implementation validation

The required broad test command stopped at an unchanged SBS upload-metadata contract assertion after 1,265 passed and 28 skipped; the same failure reproduced in isolation. The follow-on run ended without a summary at roughly 34% and is recorded as incomplete, not passing. No unrelated SBS behavior was changed. Focused client/real-CLIGEN tests, API stubtest, stub hygiene, and review outcomes are retained under [validation evidence](artifacts/validation/). The feasibility study is executed; its broad regression gate remains open, and production integration remains held for the scientific conditions above.

Independent [correctness review](artifacts/20261013_independent_correctness_review.md) passed after resolving source-validation, provenance-preservation, and seasonal-evidence findings. [Security review](artifacts/20261013_independent_security_review.md) records the anonymous-request correction and its verification; [implementer QA](artifacts/20261013_qa_review.md) is explicitly separate. Focused validation: **25 passed**; stubtest: **four modules passed**; stub hygiene, changed-exception enforcement, and documentation lint passed. The full native metadata audit passed all 4,320 objects.

## Follow-up: proposed PRISM inversion repair

After the operator requested a patch approach, a candidate evaluation applied midpoint projection only to inverted adjusted extrema: set both to `(adjusted_Tmax + adjusted_Tmin) / 2`, before existing serialization. This is the smallest squared change that restores ordering and preserves the arithmetic midpoint of daily extremes. It does not claim to preserve true daily mean air temperature. Valid days and other fields remain unchanged relative to the existing serializer.

The [evaluation](artifacts/prism-inversion-patch-evaluation.json) covers all 24 retained revisions. It repairs 15 days across the three rejected climates; all three pass fresh 20-year WEPP runs. All 21 previously accepted revisions remain unchanged. Maximum adjustment to either extreme is 0.25 C before serialization; maximum 20-year monthly mean difference is below 0.001 C after serialization, and the largest change to any individual calendar-month mean is 0.00968 C. Existing 0.1 C rounding can move the written midpoint by up to 0.05 C. These measured effects do not establish a universal bound on other datasets.

The previously validated historical/future pairs require no repairs, so their existing signal checks are unchanged. Equivalent paired claims for the Cascade failures remain unavailable because historical CLIGEN generation failed; the measured future-only monthly perturbations are retained instead.

[ADR-0092](../../adrs/ADR-0092-prism-temperature-inversion-midpoint-proposal.md) compares alternatives and identifies the required implementation paths: the Rust daily writer used by WEPPcloud, the Python breakpoint writer, public PRISM revision, and EDDE adapter. The candidate is evaluated, not wired: no production formula, existing project, or installed Rust extension was changed. [Changed-day values](artifacts/prism-inversion-patch-days.csv) and [exact repaired/consumed evidence](artifacts/prism-inversion-patch-evidence.tar.gz) are retained.
