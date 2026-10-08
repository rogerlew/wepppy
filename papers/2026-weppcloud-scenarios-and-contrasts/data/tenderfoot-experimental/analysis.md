# Tenderfoot experimental-forest application and larger-basin comparison

## Scope and provenance

The primary application is public project
[`turbinate-melodrama`](https://wc.openwepp.org/weppcloud/runs/turbinate-melodrama/disturbed9002_wbt/).
Read-only SSH inspection on October 8, 2026 located it on `hpc` at
`/tank/kubernetes/weppcloud/weppcloud-wc1/pvc-d4c5528b-3204-438b-909a-61af286d6fea/runs/tu/turbinate-melodrama`.
The public URL returned a verification page to automated HTTP requests; the
analysis used filesystem artifacts, not a verified browser session.

The locally retained `raw/` directory contains 1,037 acquired files: project and
child metadata, scenario summaries, contrast definitions/status/assignment
sidecars, and selected individual mean and annual output tables. The
[manifest](snapshot_manifest.json) records paths, sizes, and SHA-256 hashes.
Acquisition was non-atomic; the hashes describe the local snapshot, not a
transactional production snapshot. The copy was retained from the initial
inspection rather than refreshed after the manuscript revision. Raw files are
ignored by Git. Prepared management, soil, slope, climate, pass files, and the
executable were not acquired. Presence of prepared management/soil files on
`hpc` was checked, but their parameter contents remain unaudited.

The companion case is `animal-misgiving`; its September 23 snapshot remains at
[`../tenderfoot/raw/`](../tenderfoot/analysis.md). No production run or exporter
was changed. These data reproduce output analysis, not WEPP execution.

## Case definitions

| Property | Primary application | Larger-basin comparison |
| --- | --- | --- |
| Run ID | `turbinate-melodrama` | `animal-misgiving` |
| Contributing area (ha, outlet summary) | 3,083.91 | 26,992.7 |
| Hillslope area (ha, summed summaries) | 3,080.644 | 26,956.978 |
| Eligible treated area (ha) | 3,066.154 | 25,768.182 |
| Hillslopes / channels | 455 / 239 | 2,149 / 918 |
| Grouping | 33 groups, two order-reduction passes | 18 groups, three passes |
| Contrasts | 66 | 36 |
| Climate | PRISM stochastic, 100 years, station `mt241552` | Same mode, duration, and station |
| CLIGEN seed | 92740 | 76729 |
| Mean precipitation (mm/year) | 801.119 | 559.728 |
| Selected executable | `wepp_260803` | `wepp_260803` |

Both use 30/75 and 65/90 canopy/ground-cover prescriptions against the unburned
baseline. Both enable snow/baseflow, disable frost, and specify channel critical
shear of 19 Pa. These selected metadata do not prove all consumed inputs match.
The administrative experimental-forest boundary and the relationship between
the two delineations still need overlay verification. Do not assert exact forest
coverage or nested basins from the area values alone.

## Numerical method and precision decision

For each case, pair baseline, full-scenario, and contrast values by simulation
year using `loss_pw0.all_years.out.parquet`. Calculate each outlet/channel
increment from these annual values, then average the 100 years. Calculate
hillslope loss from the source hillslope summaries and normalize by their
summed area. Outlet depths use contributing area from `loss_pw0.out.parquet`.
All signs are treatment minus baseline. Group IDs are local to each application.

If B is baseline, C_g is an isolated group response, and S is the full scenario,
the signed discrepancy is `100 * (sum(C_g - B) / (S - B) - 1)`.
The denominator is the full-scenario increment, not total scenario sediment.
The comparison is valid here because each application's groups form a complete
partition of its hillslopes and eligible treatments.

**October 8 precision decision:** use annual tables consistently for both
applications. Repeated subtraction of a rounded baseline accumulates error in
the sum. Earlier larger-basin values of 51.0%/36.5% used rounded mean summaries;
the annual-table results are 51.4%/37.0%. Preliminary primary-case values of
3.2%/7.4% underestimation similarly become 3.7%/8.3%. The direction of either
result is unchanged. Do not combine numbers from the two calculation methods.
Annual source tables are themselves printed model outputs, not unrounded
internal model states; extra digits are retained for computation only.

| Case | Prescription | Summed isolated sediment increment (tonne/year) | Full increment (tonne/year) | Signed discrepancy (%) |
| --- | --- | ---: | ---: | ---: |
| Primary | 30/75 | 222.809 | 231.319 | −3.6789 |
| Primary | 65/90 | 107.073 | 116.751 | −8.2894 |
| Larger | 30/75 | 309.841 | 204.597 | +51.4397 |
| Larger | 65/90 | 164.835 | 120.296 | +37.0245 |

Outlet-water discrepancies are below 0.001% for all four comparisons. Source
hillslope soil-loss increments sum within numerical precision. Full-scenario
outlet sediment increases in all 100 primary-case years, versus 76/78 years in
the larger case. Tiny negative primary group means (minimum −0.043/−0.186
tonne/year) must not be interpreted as robust management benefits.

## Checks and limitations

The [comparison script](analyze.py) verifies all 1,037 primary and 743 larger-case
snapshot hashes, 132/72 source-output dependency hashes, sidecar hashes and
selected treatment assignments, group coverage without overlap, completed status
artifacts, combined versus individual summaries, annual versus long-term means,
and mixed hillslope-loss reconstruction. Tolerances for printed summaries are
0.1% relative and 0.11 absolute for annual/mean comparisons; mixed hillslope
loss uses 0.12 tonne/year absolute with zero relative tolerance. These checks
establish internal consistency, not independent full-run equivalence.

Both combined contrast exports store zero differences because their controls
repeat the contrast values. There are 296 primary and 172 larger-case control
entries inconsistent with the actual baseline at the script's strict tolerance.
The script bypasses those columns and calculates differences independently.
The production problem remains unresolved. The larger case's previously
identified daily-label duplication does not affect the separate annual-table
method; daily timing has not been validated for the primary case.

Correction to the earlier analysis record: larger-basin contrasts do retain
channel-level mean and annual loss summaries (918 and 91,800 rows per contrast).
The previous statement that channel-resolved outputs were disabled was too
broad. Those summaries can support reach-level analysis, but do not substitute
for all event-scale diagnostics. No reach-level mechanism is established yet.

Both runs report an unknown source commit. The executable name, status artifacts,
and hashes of selected outputs cannot establish complete runtime provenance.

## Narrative decision and follow-up

Roger accepted the primary experimental-forest case plus larger-basin comparison
on October 8. The narrative is conditional treatment response and application-
dependent nonadditivity. Basin extent is a working hypothesis, not a demonstrated
cause. Grouping and climate also differ; a larger network does not by itself
establish a direction of summation bias. Exact geographic nesting is unverified.

The first diagnostic experiment should change grouping resolution within one
fixed basin using the same scenario pass files, climate, and channel settings.
Compare full-scenario increments against sums for each complete partition;
retain group memberships, areas, annual values, and assignment hashes. This
isolates partition sensitivity before varying extent. Then evaluate compatible
extents with aligned weather and treatment inputs over verified shared areas.
Use channel summaries to trace where the sediment responses differ. These
experiments have not been run as part of this manuscript edit.

Before coauthor/submission closure, audit consumed treatment parameters,
initialization and temporal treatment assumptions; verify boundaries; capture
and check the screenshot placeholders in the manuscript; compare at least one
assembled contrast with an independently prepared full run; resolve or document
the interactive export defect; archive exact model inputs and runtime identity.

## Reproduction

From the repository root, with both local snapshots present:

```bash
.venv/bin/python papers/2026-weppcloud-scenarios-and-contrasts/data/tenderfoot-experimental/analyze.py
```

The command checks inputs before generating `results/scenarios.csv`,
`contrasts.csv`, `contrast_annual_deltas.csv`, `additivity.csv`,
`annual_diagnostics.csv`, `validation.json`, and `basin_comparison.png`/`.svg`.
It makes no network requests. Both raw snapshots must accompany a durable
research archive; checking out this repository alone is insufficient.
