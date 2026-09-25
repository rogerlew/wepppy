# GridMET rerun audit

Date: 2026-09-17 UTC. Run: thespian-cleanness.
New accepted attempt: `f493a714df9d4fbfbfd4370c46ad54f8`.
Previous accepted attempt: `0a34c96cd0dc4e6bb7bb7780d8f8915b`.

## What changed

The rerun now uses **GridMetPRISM, calendar dates 1980–2025**: 46 years,
16,802 daily rows and 8,381 wet days. Previously it used 100 simulated PRISM
years with labels 1–100. The new date semantics allow a historical-window
comparison; they do not make generated subdaily intensities gauge observations.

All **25,143 event probability rows**, 12 design rows and three P50 rows pass
independent equation and rainfall-source checks. Event values link exactly to
the saved climate parquet. The selected PDS design values match independent
sorting/rank extraction. All recorded source/artifact hashes checked by the
numeric audit match. The result publication matches the accepted attempt.

T/F/S, coverage and all inverse-table values are identical between attempts.
P50 remains **30.11676, 22.23981 and 18.98903 mm/hour** for 15/30/60 minutes.
Some regenerated terrain TIFF and manifest bytes differ; their accepted scalar
values and independently recomputed terrain/support calculations agree. No
claim of byte-identical regeneration is made.

| 15-minute PDS recurrence | Previous intensity, mm/hour | GridMET intensity, mm/hour | New M3 probability |
| --- | --- | --- | --- |
| 1 year | 18.81 | 23.89 | 31.72% |
| 2 years | 24.52 | 29.67 | 48.61% |
| 5 years | 30.20 | 44.24 | 85.06% |
| 10 years | 35.62 | 49.50 | 91.59% |

The probability curve did not change: the different rainfall-frequency record
selects different locations along it. These are rainfall recurrence intervals,
not debris-flow recurrence intervals. See [comparison.json](comparison.json)
and [all durations](design_comparison.csv).

## Comparison with the August 2021 observation

Rengers et al. (2024), section 3.4.3, places Dead Horse Creek deposition
approximately August 5–12, 2021, without assigning a single triggering storm.
Its fire-wide M1 I15 P50 is 25.9 mm/hour, not a basin-specific M3 benchmark.
[Reference paper](https://nhess.copernicus.org/articles/24/2093/2024/).

**Every day from August 5 through August 12 has 0.0 mm in both the saved original
GridMET daily series and the generated CLIGEN daily record.** All three modeled
peak intensities are also zero; the wet-event table consequently has no rows
for that interval. The exclusion of dry days follows the event-table contract;
it is not lost rainfall during the debris-flow computation.

See [eight daily records](august_2021_daily.csv) and the header-only
[wet-event extract](august_2021_events.csv). These zeros do not establish that
no storm occurred at a debris-flow source. They expose a mismatch between this
gridded daily record and the paper's approximate deposition timing. This audit
cannot resolve local rainfall variability, timing uncertainty or dataset error
without representative gauge data. Do not move the event to a nearby wet date
merely to create agreement.

GridMET is a daily approximately 4 km gridded meteorological product, as described
by its [publisher](https://www.climatologylab.org/gridmet.html). The actual build
path in `wepppy/nodb/core/climate_build_helpers.py`, `build_observed_gridmet`,
retains the retrieved daily series, supplies it to `Cligen.run_observed` via
`_run_observed_with_quality_guard_handling`, and generates the CLI. The report
correctly labels subdaily values **modeled/disaggregated**. Across all dates,
saved GridMET versus CLI daily precipitation differs by at most 0.1 mm; this
comparison records that difference rather than claiming byte/exact daily parity.
The eight-day zero result is exact in both sources.

An observed-intensity hindcast still requires measured 15/30/60-minute rainfall
and a defensible storm/outcome pairing. The earlier audit's 45.53% missing SBS,
26.83 km² basin and soil-component qualifications also remain unchanged.
The current rerun does not supply independent predictive validation.

## Why the report is marked out of date

Both local and authenticated report reads return `current: false` for this
accepted attempt, while saved results remain available. The only live-input
snapshot difference is `climate/wepp.cli` filesystem **ctime**:

- Accepted: 1789606517582688867 ns.
- Current at audit: 1789606773014495607 ns.
- Size remains 1,177,082 bytes; mtime remains 1789606508469623319 ns.

All accepted result artifact signatures pass. See [freshness.json](freshness.json).
Ctime can change after metadata operations or content writes; unchanged size
and mtime alone do not prove unchanged contents. The accepted active-CLI
signature lacks a content hash, so this audit cannot attribute the change or
prove a false stale result. It does not clear or overwrite freshness state.
The saved climate-parquet hash and result equations still pass verification.

The first browser audit incorrectly assumed `current: true`; its retained
[diagnostic](browser_initial_currentness_assumption.log) led to the snapshot
comparison. The corrected audit records actual freshness and verifies the
saved report independently. This is an observed stale-input indication, not
an unexplained numerical failure.

## Validation and next step

The authenticated report, all duration payloads, saved curve points, five
attachments and reload are checked using normal login. No new model job was
submitted. See [browser evidence](browser/thespian-cleanness/evidence.json),
[numeric checks](numeric_audit.json) and [final checks](closeout_checks.json).
Protected scientific/state files remain unchanged during this audit. Changes
made by the owner before this follow-up are distinguished from audit mutations.

Retain the calendar-dated run for exploratory comparisons. For event validation,
obtain representative gauge records around August 5–12, resolve the observation
window as far as the evidence permits, and evaluate M3 with measured intensities
on the relevant contributing basin. Investigate the CLI ctime change before
assuming the report's freshness warning is spurious. No code, model parameters,
inputs, accepted results or closed historical work-package files were changed.
