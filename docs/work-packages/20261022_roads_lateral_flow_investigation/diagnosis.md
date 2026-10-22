# UM1 roads water-report diagnosis

**Date**: 2026-10-22 UTC  
**Disposition**: Diagnosis validated by isolated native replay; no repair implemented.

## Findings

The reported zero lateral flow is a report-input assembly defect. The roads
workspace contains WAT water-balance files for 34 road segments but none of the
66 baseline hillslopes. All segment WAT lateral values are zero. The roads
aggregate consequently omits the watershed's hillslope lateral contribution.
This does not demonstrate that the watershed simulation lost its lateral flow.

Runoff has two distinct reporting errors. The native aggregate sums PASS runoff
from all 100 IDs but divides by the area represented by segment-only WAT:
4,127.15 m² instead of the baseline watershed's 441,820.29 m² (about 107 times
smaller). Additionally, those 100 IDs include 34 standalone road-segment PASS
records whose volumes were already added into 14 of the 66 hillslope PASS files.

Baseflow is a separate consequence of the WAT population: it is calculated from
road-only percolation depths and the configured groundwater reservoir, rather
than watershed percolation. It is not inflated by summing duplicate PASS runoff.
For 2001, road-only percolation is 1,401.14 mm versus watershed 60.48 mm.
Stored groundwater options are 200 mm initial storage, 0.04 baseflow coefficient,
and zero deep-seepage coefficient. The same options were used in every replay.

## First divergent boundary and source trace

`wepppy/nodb/mods/roads/roads.py::_prepare_roads_output_workspace` clears the
roads output workspace. Segment execution writes segment WAT/PASS there.
The staging loop near line 5978 copies or links only baseline `H*.pass.dat`.
The following additive loop calls `_combine_target_hillslope_pass`, adding road
PASS contributions into target hillslope PASS files; the standalone segment
files remain in the same directory. No baseline WAT staging accompanies this.

`_regenerate_roads_report_resources` near line 3974 runs hillslope interchange
on that mixed workspace, then calls `run_totalwatsed3` without an ID subset.
`hill_wat_interchange.py` discovers `H*.wat.dat`; `hill_pass_interchange.py`
discovers `H*.pass.dat`. The resulting 34-WAT/100-PASS population exactly matches
the raw-file inventory. This is upstream of report rendering.

In `/workdir/wepppyo3/wepp_interchange/src/totalwatsed.rs`, `aggregate_pass`
(near line 595) sums all selected PASS IDs independently of WAT availability;
`aggregate_hill` (near line 627) supplies WAT area and fluxes. `finish_row`
(near line 971) computes runoff depth from PASS volume divided by WAT area.
The reservoir recurrence near line 1127 uses WAT percolation depth. Current
source checkout revision is `3b630643ba06bd40262285f206112c9d3ee32b21`.
Native binary path and SHA-256 are retained in the replay evidence; checkout
revision alone is not claimed to identify that binary's build provenance.

## Unmocked replay

Four native `totalwatsed3_to_parquet` calls used the retained Parquet inputs,
writing only to `/workdir/wepppy-scratch/roads-lateral-aol7fv82`.
All 5,844 daily rows and all 16 calendar years were processed. Optional soil,
element, and ash extensions were omitted because these experiments isolate
water quantities; their outputs are not substitutes for complete report products.

Calendar-year 2001 values in mm:

| Experiment | Lateral flow | Runoff | Baseflow |
| --- | ---: | ---: | ---: |
| Baseline inputs | 1,021.10 | 183.02 | 60.11 |
| Original roads inputs | 0 | 20,082.37 | 1,273.25 |
| Roads PASS with baseline WAT | 1,021.10 | 187.59 | 60.11 |
| Combined hillslope PASS only, baseline WAT | 1,021.10 | 185.31 | 60.11 |

The original roads replay matches retained Area, Lateral Flow, Runoff,
Percolation, Baseflow, and runvol exactly across every day. Baseline replay
matches within floating-point roundoff (maximum volume difference 7.28e-12 m³).
The source-population hypothesis therefore reproduces the symptom with current
native execution; stale rendering is not needed to explain it.

Across the full record, standalone segments contribute 16,129.0383 m³ of runoff.
Combined hillslope PASS adds 16,129.0315 m³ above baseline. Their maximum daily
residual is 0.004573 m³, consistent with limited-precision combined PASS output;
exact equality is not claimed. Source assembly plus this volume comparison
confirms the segment contribution is represented twice in the unfiltered report.

## Smallest repair recommendation

Define an explicit report-input population independently of the segment output
archive and routing workspace. For this additive `inslope_rd` case, the bounded
candidate is the canonical 66 combined hillslope PASS records with corresponding
watershed WAT support, retaining segment diagnostics separately. The diagnostic
replay demonstrates why this removes the reported errors, but baseline WAT alone
omits any explicitly desired road contribution to ET/percolation/storage.
The authoritative Roads contract must decide that accounting treatment before
shipping a repair; the diagnostic 185.31 mm result is not a certified final model
result. Do not silently equate additive road area with extra watershed footprint.

Do not apply a baseline-WAT copy universally: replacement modes must use their
replacement hillslope water balances and correct physical area, rather than
reintroducing the replaced baseline hydrology. ID selection must come from the
translator/execution manifest, not a numeric cutoff such as 900000. Preserve
standalone segment loss products and required optional report resources.

Regression acceptance should cover additive and replacement modes, absent and
empty WAT/PASS, missing contributing IDs, ordinary and synthetic ID overlap,
zero-road controls, area normalization, no double counting, baseline isolation,
and all affected yearly/daily exports. Rebuild on an isolated real-project copy
through the normal orchestration and inspect the consumed inputs and displayed
results before claiming a repair. Any changed scientific formula or area policy
requires the parameterization ADR; correctness review is required for the fix.

## Impact and limits

The demonstrated impact is UM1 roads totalwatsed and reports consuming it,
including yearly water balance and daily streamflow. Average hillslope reports
also consume the segment-only WAT population and need explicit validation.
Other runs with the same staging pattern are at risk; no production-wide census
was performed. This investigation does not establish corruption of watershed
routing results or baseline reports. The actual case has 34 additive inslope
segments and no replacement targets; other designs remain acceptance risks.

Six original Parquet hashes were rechecked and unchanged. No runtime code,
production files, NoDb state, or run outputs were modified. No deployment,
run repair, or incident-resolution claim is made.

## Reproduction and retained evidence

From `/workdir/wepppy`:

    .venv/bin/python docs/work-packages/20261022_roads_lateral_flow_investigation/artifacts/replay.py

Each invocation creates a new scratch directory and emits JSON. See
[replay results](artifacts/replay-results.json),
[replay script](artifacts/replay.py),
[raw inventory and source verification](artifacts/source-verification.json), and
[initial inventory](artifacts/initial-inputs.json).
