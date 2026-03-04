# Benchmark Plan

## Shortlist Source

The benchmark shortlist is constrained to overlap rows only (`raster_tools` support status `direct` or `partial`) and then filtered to matrix priorities `high|medium` from:
`docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/capability_crosswalk_matrix.md`.

Shortlisted IDs: `BW-01`, `BW-02`, `BW-03`, `BW-04`, `BW-05`.

### Shortlist Traceability to Cross-Walk Rows

| Case ID | Operation family row in matrix | Overlap status | Priority |
|---|---|---|---|
| `BW-01` | DEM reprojection / warp / VRT prep | `direct` | `high` |
| `BW-02` | Raster clipping / masking for culvert and watershed masks | `direct` | `medium` |
| `BW-03` | Geometry-to-raster conversion / rasterization | `direct` | `medium` |
| `BW-04` | Terrain derivatives (slope/aspect) | `direct` | `medium` |
| `BW-05` | Extent-window raster intersection (`sub_intersection`) | `partial` | `medium` |

Excluded from shortlist as non-comparable (`none` + `exclude` in matrix):

- Watershed/channel delineation and outlet snapping
- Sub-field abstraction for ag fields
- WEPPcloud browser map rendering and GeoTIFF decode

## Milestone 3 Harness Implementation Notes

Implemented harness:

- Script: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/benchmark_harness_bw01_bw02.py`
- Raw outputs: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/bench_outputs/`
- Run summary JSON: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/benchmark_runs_bw01_bw02.json`

Environment model used by harness:

- Current stack commands run with system Python: `/usr/bin/python3`
- `raster_tools` commands run in dedicated venv: `/tmp/raster-tools-bench-venv/bin/python`
- `raster_tools` source import path supplied by `PYTHONPATH=/home/workdir/raster_tools`

Timing scope note:

- Each measured run executes a fresh subprocess (`python -c ...`) for both current and candidate variants.
- Reported runtimes therefore include interpreter/import/startup overhead in addition to core raster operation time.

Reason for split environment:

- System Python has WEPPpy GDAL bindings but initially lacked `geopandas` for `raster_tools`.
- A dedicated venv was created and populated from `/home/workdir/raster_tools/requirements/default.txt`.

## Case Specifications

| Case ID | Dataset(s) | Current command path | Candidate command path | Warmup + measured runs | Parity contract |
|---|---|---|---|---|---|
| `BW-01` | `/home/workdir/raster_tools/tests/data/raster/dem_small.tif` | GDAL Warp to `EPSG:5070` (`gdal.Warp`) | `raster_tools.warp.reproject(..., 'EPSG:5070')` + `save()` | `1 + 3` | Comparable-grid precondition required (`same projection + shape + geotransform`), then `RMSE <= 1.0` on non-nodata cells |
| `BW-02` | Raster: `/home/workdir/raster_tools/tests/data/raster/dem.tif`; Vector: `/home/workdir/raster_tools/tests/data/vector/pods_first_10.shp` | GDAL cutline clip (`gdal.Warp` with `cutlineDSName`, `cropToCutline=True`) | `raster_tools.clipping.clip(open_vectors(...), Raster(...))` + `save()` | `1 + 3` | Comparable-grid precondition required (`same projection + shape + geotransform`), then non-zero footprint ratio `>= 0.85`; otherwise mark non-comparable |
| `BW-03` | Planned: raster/vector pair for rasterization | Planned GDAL/rasterio rasterization path | Planned `raster_tools.rasterize.rasterize` path | Planned `1 + 3` | Planned class-count + pixel-count parity checks |
| `BW-04` | Planned DEM slope/aspect dataset | Planned WBT/GDAL derivative path | Planned `raster_tools.surface.slope/aspect` path | Planned `1 + 3` | Planned tolerance for slope/aspect numeric deltas |
| `BW-05` | Planned bbox intersection dataset/window | Planned WEPPpy bbox-ID extraction proxy | Planned `raster_tools` clip-box + unique-value proxy | Planned `1 + 3` | Planned sorted-ID set parity or explicit non-comparable mark |

## Deferred Cases in This Draft

`BW-03`, `BW-04`, and `BW-05` remain planned but were not executed in this draft run.
They stay in scope and are carried forward as deferred benchmark executions in Milestone 4 notes.

## Execution Commands (Implemented Cases)

Run from `/workdir/wepppy`:

    python docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/benchmark_harness_bw01_bw02.py

Preparation command used once for candidate environment:

    python -m venv /tmp/raster-tools-bench-venv
    /tmp/raster-tools-bench-venv/bin/python -m pip install --upgrade pip
    /tmp/raster-tools-bench-venv/bin/python -m pip install -r /home/workdir/raster_tools/requirements/default.txt
