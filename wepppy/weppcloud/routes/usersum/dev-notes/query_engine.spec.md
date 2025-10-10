# Query Engine Specification

Goal: provide near real-time access to geo-spatial-temporal data from WEPPcloud run directories using a common query engine that can power API routes, batch jobs, dashboards, and developer tooling.

## High-Level Objectives
- Replace bespoke REST endpoints with a declarative query layer grounded in DuckDB.
- Support joins and aggregations across canonical Parquet assets (hillslopes, landuse, soils, RAP, WEPP output).
- Roll up daily outputs to yearly or categorical summaries (e.g., landuse class, hillslope groups).
- Feed downstream dashboards and interchange exporters without duplicating asset wiring.
- Remain aware of Omni scenarios and batch groups.
- Provide a predictable activation pipeline so legacy runs can opt into the query experience.

## Core Modules (`wepppy/query_engine`)
- `activate_query_engine(wd, run_interchange=True)`: walk a run directory, emit `<wd>/_query_engine/catalog.json`, cache derived artifacts, and optionally run WEPP interchange/documentation when missing. The start year is inferred from `Climate` when present.
- `resolve_run_context(runid, scenario=None)`: resolve filesystem paths, auto-activate if necessary, and hydrate a `RunContext` (base directory + catalog handle).
- `run_query(run_context, QueryRequest)`: build and execute a DuckDB plan, returning a `QueryResult(records, schema, row_count)`.
- Support utilities:
  - `DatasetCatalog` (`catalog.py`): lightweight manifest loader with lookup helpers.
  - `DuckDBExecutor` (`executor.py`): runs parametrised SQL/Arrow queries with optional spatial extension loading.
  - `QueryRequest`/`QueryPlan` (`payload.py`): dataclasses defining the payload and compiled plan.
  - `format_table` (`formatter.py`): converts Arrow tables to Python records + optional schema metadata (unit conversion deferred to a final presentation step).
- Starlette façade (`query_engine/app`): `create_app()` exposes routes for human/browser discovery (`GET /query/runs/{runid}`), schema downloads (`GET /query/runs/{runid}/schema`), and JSON query execution (`POST /query/runs/{runid}/query`). Templates live under `query_engine/app/templates` and render catalog summaries.

## Activation & Catalog Workflow
1. `activate_query_engine` recurses the run (and scenarios) collecting known extensions (`.parquet`, `.csv`, `.tsv`, `.tif`, `.json`, `.geojson`, `.nodb`).
2. Missing canonical outputs can trigger regeneration (interchange exporters, documentation, Parquet dumps).
3. The manifest is written to `<wd>/_query_engine/catalog.json`; derived artifacts land in `<wd>/_query_engine/cache/`.
4. Subsequent runs load the manifest and skip regeneration unless assets change.
5. Batch scenarios can reuse the same activation logic per child run.

## Dataset Inventory Highlights
- `watershed/hillslopes.parquet`: hillslope geometry + slope metrics (`TopazID`, `wepp_id`, centroids, fp_longest*).
- `watershed/channels.parquet`: channel summaries (`TopazID`, `chn_enum`, area, slope, aspect).
- `watershed/flowpaths.parquet`: individual flowpath metrics (`fp_id`, length, slope, aspect).
- `landuse/landuse.parquet`: dominant management metadata per hillslope (`key`, `_map`, coverage, canopy fractions, disturbed_class).
- `soils/soils.parquet`: dominant soil properties per hillslope (`mukey`, texture, hydraulic properties, coverage).
- `rap/rap_ts.parquet`: RAP band/year landcover time series (`band`, `year`, `topaz_id`, `value`).
- `wepp/output/totwatsed2.parquet`: watershed daily hydrology & sediment balance (mm, volumetric measures, phosphorus when available).
- `wepp/output/interchange/*.parquet`: hillslope & watershed interchange exports (PASS, WAT, EBE, channel summaries, etc.).
- `disturbed/disturbed_land_soil_lookup.csv`: disturbance lookup table for cross-walking soils/landuse adjustments.

## Query Planner Architecture (current state)
```
Client payload (QueryRequest)
    └── RunContext (catalog + base dir)
            └── Catalog validation (datasets, column checks)
                    └── QueryPlan (SQL, params, spatial flag)
                            └── DuckDBExecutor (Arrow table)
                                    └── Formatter (records, optional schema)
```
- Present implementation supports single-dataset projections with optional column selection, `LIMIT`, and schema echoing. Future work will flesh out joins, filters, groupings, ranking/windowing, spatial filters, and preferred unit conversions.
- Unit conversions will be applied as a presentation layer via `Unitizer` without mutating the underlying Parquet assets.

## Output Formats
- JSON (default) via Arrow → Python records.
- Parquet / Arrow IPC / CSV / GeoJSON to be layered onto the formatter.
- Timeseries responses (e.g., for dashboards) can expose `{dates: [...], series: {...}}` shapes.
- GIS exports (GPKG, FileGDB, KML, SHP) will stream through GDAL/OGR when requested, caching generated artifacts per normalised query hash.

## Example Usage
```python
from wepppy.query_engine import activate_query_engine, resolve_run_context, run_query
from wepppy.query_engine.payload import QueryRequest

runid = "/wc1/runs/ri/riddled-headmaster"
activate_query_engine(runid, run_interchange=False)
ctx = resolve_run_context(runid, auto_activate=False)
payload = QueryRequest(datasets=["landuse/landuse.parquet"], limit=5)
result = run_query(ctx, payload)
print(result.records[:2])
```

## Benchmark & Integration Tests
Located in `tests/query_engine/`:
- `test_core.py`: unit smoke tests using synthetic Parquet assets (catalog round-trip, schema echo).
- `test_benchmarks.py` (requires real run directories):
  1. `test_landuse_dict_payload` replicates the `/runs/<runid>/query/landuse/subcatchments` behaviour by materialising a `{TopazID: row_dict}` map from `landuse/landuse.parquet`.
  2. `test_totalwatsed_aggregate_cache` parses native `H*.wat.dat` files, joins with `interchange/H.pass.parquet`, aggregates daily totals, and writes `_query_engine/cache/totalwatsed3.parquet` for downstream reuse.
  These tests are marked `@pytest.mark.benchmark` and skipped automatically when the expected run directories are absent.

## Future Work
- Full SQL planner: dataset aliasing, join graphs, filter predicates, group/aggregate operators, ranking/window functions, spatial predicates (point-in-polygon, bounding boxes, hillslope groups).
- Expanded formatter support (CSV/Parquet streaming, GeoJSON, GDAL-backed GIS formats).
- Preferred unit conversion via `Unitizer` hooks.
- Batch querying that unions results across multiple run contexts.
- API wiring (Starlette/FastAPI routes) building on the reusable core modules.
