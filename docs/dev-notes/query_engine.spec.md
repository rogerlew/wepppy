# Query Engine Specification

> **See also:** [AGENTS.md](../../AGENTS.md) for Python Stack and duckdb_agents.py section.

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
  - `DuckDBExecutor` (`executor.py`): runs parametrized SQL/Arrow queries with optional spatial extension loading.
  - `QueryRequest`/`QueryPlan` (`payload.py`): dataclasses defining the payload and compiled plan.
  - `format_table` (`formatter.py`): converts Arrow tables to Python records + optional schema metadata (unit conversion deferred to a final presentation step).
- Starlette façade (`query_engine/app`): `create_app()` exposes routes for human/browser discovery (`GET /query/runs/{runid}`), catalog activation (`GET|POST /query/runs/{runid}/activate`), schema downloads (`GET /query/runs/{runid}/schema`), an interactive query console (`GET /query/runs/{runid}/query`), and JSON query execution (`POST /query/runs/{runid}/query`). Templates live under `query_engine/app/templates` and render catalog summaries as well as the in-browser console.

### Recent Enhancements (2025-10)
- Added `_resolve_run_path` helper so all routes honor WEPPcloud storage conventions via `get_wd`.
- Introduced an interactive “query console” HTML view that allows users to paste/edit POST payloads, trigger queries, and view responses directly in the browser. The console renders example dataset paths, provides JSON formatting/reset helpers, and now offers a preset selector backed by `query_engine/app/query_presets.py`.
- Updated `/query/runs/{runid}/query` POST handling to include defensive catalog checks, improved error status codes (422 for invalid payloads, 404 for missing datasets), and stack traces in JSON responses for debugging—mirroring the rich error feedback approach used by the browse microservice.
- Activation endpoint now surfaces full stack traces on failure for easier diagnosis in web UIs.
- Route table simplified so GET and POST handlers share the same path while ensuring the GET console is registered ahead of the POST handler.
- `QueryRequest` now normalizes dataset descriptors (path + alias), join definitions, aggregation specs, and flexible filter clauses. The planner can join multiple Parquet assets (e.g., `landuse` ↔ `soils` on `topaz_id`), apply type-aware filters (supporting `=`, `IN`, `BETWEEN`, `IS NULL`, etc. with automatic casting like `'43'` → `INT64`), compute grouped aggregations (e.g., daily WEPP interchange sums across `wepp_id`), order results, and optionally echo the generated DuckDB SQL.
- Added `update_catalog_entry(wd, rel_path)` helper for incremental catalog refreshes and a read-only sentinel check so activation fails fast when a run directory is locked.
- Added unit coverage for join/aggregation planners (`tests/query_engine/test_core.py::test_run_query_join`, `test_run_query_aggregation`).

## Activation & Catalog Workflow
1. `activate_query_engine` recurses the run (and scenarios) collecting known extensions (`.parquet`, `.csv`, `.tsv`, `.tif`, `.json`, `.geojson`, `.nodb`).
2. Missing canonical outputs can trigger regeneration (interchange exporters, documentation, Parquet dumps).
3. The manifest is written to `<wd>/_query_engine/catalog.json`; derived artifacts land in `<wd>/_query_engine/cache/`.
4. Subsequent runs load the manifest and skip regeneration unless assets change.
5. Batch scenarios can reuse the same activation logic per child run.

## Dataset Inventory Highlights
- `watershed/hillslopes.parquet`: hillslope geometry + slope metrics (`topaz_id`, `wepp_id`, centroids, fp_longest*).
- `watershed/channels.parquet`: channel summaries (`topaz_id`, `chn_enum`, area, slope, aspect).
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
- Present implementation handles single-dataset projections as well as multi-dataset joins driven by alias-based join specs, with optional grouping/aggregation clauses (including per-day/month/year rollups for interchange datasets). Filters, ranking/windowing, spatial predicates, and preferred unit conversions remain future work.
- Unit conversions will be applied as a presentation layer via `Unitizer` without mutating the underlying Parquet assets.

## Output Formats
- JSON (default) via Arrow → Python records.
- Parquet / Arrow IPC / CSV / GeoJSON to be layered onto the formatter.
- Timeseries responses (e.g., for dashboards) can expose `{dates: [...], series: {...}}` shapes.
- GIS exports (GPKG, FileGDB, KML, SHP) will stream through GDAL/OGR when requested, caching generated artifacts per normalized query hash.

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

# join soils on topaz_id
payload = QueryRequest(
    datasets=[
        {"path": "landuse/landuse.parquet", "alias": "landuse"},
        {"path": "soils/soils.parquet", "alias": "soils"},
    ],
    joins=[{"left": "landuse", "right": "soils", "on": ["topaz_id"]}],
    columns=[
        "landuse.topaz_id AS topaz_id",
        "landuse.landuse AS landuse_desc",
        "soils.texture AS soil_texture",
    ],
)
print(run_query(ctx, payload).records[:2])

# aggregate WEPP interchange outputs to daily sums across all hillslopes
payload = QueryRequest(
    datasets=[{"path": "wepp/output/interchange/H.pass.parquet", "alias": "pass"}],
    columns=[
        "pass.year AS year",
        "pass.month AS month",
        "pass.sim_day_index AS sim_day_index",
    ],
    group_by=["year", "month", "sim_day_index"],
    aggregations=[
        {"fn": "sum", "column": "pass.runoff", "alias": "runoff_sum"},
        {"fn": "sum", "column": "pass.sediment", "alias": "sediment_sum"},
    ],
)
print(run_query(ctx, payload).records[:1])

# same aggregation but include the generated SQL text
payload.include_sql = True
sql_result = run_query(ctx, payload)
print(sql_result.sql)

# filter landuse by key and canopy coverage (string 43 coerces to INT64)
payload = QueryRequest(
    datasets=[{"path": "landuse/landuse.parquet", "alias": "landuse"}],
    columns=[
        "landuse.TopazID AS topaz_id",
        "landuse.key",
        "landuse.cancov",
    ],
    filters=[
        {"column": "landuse.key", "operator": "=", "value": "43"},
        {"column": "landuse.cancov", "operator": "<", "value": 0.6},
    ],
    include_sql=True,
)
print(run_query(ctx, payload).records[:2])
```

## Benchmark & Integration Tests
Located in `tests/query_engine/`:
- `test_core.py`: unit smoke tests using synthetic Parquet assets (catalog round-trip, schema echo).
- `test_benchmarks.py` (requires real run directories):
  1. `test_landuse_dict_payload` replicates the `/runs/<runid>/query/landuse/subcatchments` behavior by materializing a `{topaz_id: row_dict}` map from `landuse/landuse.parquet`.
  2. `test_totalwatsed_aggregate_cache` parses native `H*.wat.dat` files, joins with `interchange/H.pass.parquet`, aggregates daily totals, and writes `_query_engine/cache/totalwatsed3.parquet` for downstream reuse.
  These tests are marked `@pytest.mark.benchmark` and skipped automatically when the expected run directories are absent.

## Future Work
- Query planner extensions: filter predicates, parameter binding, ranking/window functions, spatial predicates (point-in-polygon, bounding boxes, hillslope groups), and join graphs beyond simple star joins.
- Expanded formatter support (CSV/Parquet streaming, GeoJSON, GDAL-backed GIS formats).
- Preferred unit conversion via `Unitizer` hooks.
- Batch querying that unions results across multiple run contexts.
- API wiring (Starlette/FastAPI routes) building on the reusable core modules.

### Near-Term Planner Roadmap
1. **Query ergonomics**
   - Extend filter expressiveness (`IN`, `BETWEEN`, null checks, spatial predicates) and support parameter binding so clients can narrow result sets without constructing raw SQL.
   - Support join graphs that re-use aliases (e.g., landuse ↔ soils ↔ disturbances) and expose explicit join ordering controls.

2. **Aggregation helpers**
   - Provide shorthand aggregators for common WEPP metrics (e.g., `total_runoff`, `sediment_mass`) and automate cache keys for expensive rollups.
   - Allow multiple aggregation levels in a single request (daily + monthly) via window functions.

3. **Validation & optimization**
   - Enhance catalog validation with column existence/type checks before generating SQL, returning expressive error messages.
   - Surface estimated costs / row counts for large queries and optionally leverage DuckDB's persistent caches for repeated workloads.
