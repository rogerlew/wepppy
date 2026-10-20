# Consumer Audit Baseline

Recorded 2026-10-20 18:45 UTC from the preceding static analysis and local
reproductions. Source snapshots: WEPPpy `fc67fcad6`, wepppyo3 `0515272`; the
preceding model-side inspection used wepp-forest `375ccc296`. Recheck current
revisions before implementation. Reproduction output was observed in the
session; no persistent project fixture or raw execution log was retained.
Recreate and retain evidence in M1/M5 rather than treating this note as a
candidate validation artifact.

## Numerical Counterexample

| OFE | Area m² | Ep mm | Es mm | Er mm | ET mm | Dp mm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 250 | 1 | 0.5 | 0.5 | 2 | 4 |
| 2 | 750 | 4 | 1 | 1 | 6 | 8 |

Correct daily hill values: ET 5 mm and Dp 7 mm; component values are
Ep 3.25, Es 0.875, Er 0.875 mm. Volumes are ET 5 m³ and Dp 7 m³.

Observed local results:

| Consumer | ET mm | Dp mm | Evidence type |
| --- | ---: | ---: | --- |
| Native hillslope summary | 8 | 12 | Installed native function executed |
| Dashboard event expression | 8 | N/A | Static SQL inspection |
| Features Export, all three temporal modes | 6 | 8 | Materializer executed on one-day fixture |
| Native TotalWatSed | 5 | 7 | Heterogeneous fixture executed |
| Daily hill loader | 5 | 7 | Two hillslopes executed |

The native module resolved to
`/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/wepp_interchange_rust.so`.
The Features Export import emitted local Redis authentication diagnostics, but
the pure materializer calls completed. This does not establish service/browser
acceptance.

## Scoped Failure Boundaries

| ID | Boundary | Defect | Downstream exposure |
| --- | --- | --- | --- |
| MOFE-01 | `wepppyo3/wepp_interchange/src/hillslope_watbal.rs`, `produce` | Sums local depths independently of collected OFE area | Python `HillslopeWatbalReport`, summary cache, average-annual HTML/CSV, report yearly iterator |
| MOFE-02 | `wepppy/weppcloud/static/js/gl-dashboard/data/wepp-data.js`, `refreshWeppEventData` and `loadBaseWeppEventData` | SQL adds `SUM(Ep) + SUM(Es) + SUM(Er)` | Event ET overlays and comparison differences |
| MOFE-03 | `wepppy/nodb/mods/features_export/temporal_wide_materializer.py`, `_collapse_terminal_ofe_rows` | Selects last OFE for local fluxes before temporal processing | Event/yearly/annual-average CSV, Parquet and geospatial export materializations |

For MOFE-03, trace `carrier_layer_materializer.py`,
`service.py`, `layer_catalog.yaml`, and export cache dependencies. The catalog's
WAT entry advertises `ET` although the raw schema exposes Ep/Es/Er; specify
derived ET behavior before wiring it, without adding a raw WAT column.

## Reference and Indirect Consumers

`wepppyo3/wepp_interchange/src/hill_wat.rs` preserves OFE depths/areas;
WEPPpy `hill_wat_interchange.py` is its facade and implements the correctly
weighted daily loader. `totalwatsed.rs` converts all OFE ET/Dp to volumes and
divides by summed area. Its groundwater recurrence uses the weighted Dp depth.
Do not reinterpret TotalWatSed's Ep/Es/Er/Dp volume columns as raw WAT mm.

`TotalWatbalReport`, observed-data comparisons, partitioned DSS exports, and
current R TotalWatSed reports inherit that correct aggregation. Return-period,
flow-duration, streamflow, and AshPost hydrology consumers depend indirectly
on Dp through baseflow. Ash/WATAR loaders use the daily collapse; Neris consumes
Es from that frame. Storm-event WAT queries use snow metrics, not ET/Dp.

RQ post-processing, project/batch/culvert helpers, Roads and AgFields workflows
invoke the same producers; they are wiring checks, not new spatial algorithms.
The three reusable tools `hillslope_daily_closure_audit.py`,
`hillslope_mofe_daily_closure_audit.py`, and
`totalwatsed3_daily_closure_audit.py` correctly account for ET/Dp areas.

## Tests and Legacy R

Native `tests/wepp_interchange/test_hillslope_watbal.py` and WEPPpy
`tests/wepp/reports/test_hillslope_watbal.py` encode unweighted report behavior.
Features Export's terminal-OFE regression uses runoff; it cannot justify
discarding upstream ET/Dp. Dashboard mocks start with already aggregated values.

Default DEVAL uses `new_report.Rmd`, whose raw balance and map were commented
out with a note that Erin requested disabling them. This scaffold deletes
those blocks. The older `weppcloudR/templates/scripts/report.Rmd` still invokes
an unweighted raw residual calculation, and the shared Chinmay helper retains
its duplicate. Their removal or repair is excluded from this package.
