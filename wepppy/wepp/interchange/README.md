# WEPP Interchange
> Columnar interchange for WEPP runs: transforms WEPP text reports into analytics-ready Parquet datasets with unit-aware metadata, versioning, and parallel processing.

> **See also:** [AGENTS.md](../../../AGENTS.md) § Module Organization Best Practices, § Performance Optimization

## Overview

The `wepppy.wepp.interchange` package solves a critical data engineering challenge in erosion modeling: **WEPP (Water Erosion Prediction Project) model outputs are fixed-width text files designed for FORTRAN 77 I/O, not modern analytics workflows.** Parsing these reports repeatedly for queries, visualizations, and exports creates performance bottlenecks and maintains tight coupling between analysis code and legacy formats.

This package **transforms WEPP text outputs into Apache Arrow/Parquet tables** with schema versioning, unit metadata, and optimized indexing—enabling instant queries via DuckDB, zero-copy DataFrame construction, and seamless integration with notebook explorers (D-Tale), GIS tools, and hydrologic model chains (HEC-DSS).

**Core Problem Solved**: 
- WEPP hillslope runs generate 6 different report types (`H*.pass.dat`, `H*.ebe.dat`, `H*.element.dat`, `H*.loss.dat`, `H*.soil.dat`, `H*.wat.dat`) × potentially 100+ hillslopes = hundreds of text files requiring custom parsers
- Watershed runs produce 7 additional report formats with different schemas and multi-line continuation patterns
- Downstream tools (query engine, export modules, status dashboards) were repeatedly parsing the same files, wasting CPU and I/O
- Schema changes in WEPP versions broke analytics code unpredictably

**Solution Architecture**:
- **Single parse, multiple reads**: Transform text → Parquet once after simulation, query indefinitely
- **Schema versioning**: Embed `dataset_version_major/minor/patch` metadata; incompatible changes trigger automatic cleanup
- **Unit-aware metadata**: Column metadata includes `units` and `description` for self-documenting datasets
- **Parallel processing**: Process pool fan-out for high-volume hillslope files (respects `NCPU`)
- **Atomic writes**: Temp file pattern ensures partial writes never corrupt the interchange directory

**Primary Users**:
- **Query engine** (`wepppy.query_engine`) executes DuckDB SQL over interchange Parquet for instant loss reports, timeseries, and spatial aggregations
- **Export modules** (`wepppy.wepp.out.dss`, `wepppy.wepp.out.netcdf`) stream tabular data to HEC-DSS, NetCDF, GeoJSON without reparsing
- **D-Tale explorer** (`wepppy.weppcloud.webservices.dtale`) provides interactive data exploration of multi-GB Parquet archives
- **Status dashboards** (`wepppy.weppcloud.routes.query`) surface real-time run progress by scanning `interchange_version.json`
- **Background RQ tasks** (`wepppy.rq.wepp_rq`) invoke interchange pipelines after WEPP completes

**Key Capabilities**:
- **Hillslope interchange**: 6 parsers for PASS, EBE, Element, Loss, Soil, WAT reports (handles multi-line wrapping, fixed-width fields)
- **Watershed interchange**: 7 parsers for watershed PASS, EBE, channel peak, channel water balance, soil, loss, and routing outputs
- **Derived products**: `totalwatsed3` joins PASS + WAT with DuckDB for watershed-wide daily summaries; DSS export tooling for HEC integration
- **Deep dive**: see [README.dss_export.md](README.dss_export.md) for the full DSS export + browse guide (totalwatsed channels and peak-flow records).
- **Documentation generation**: Auto-generate Markdown schema previews with sample rows for human-readable interchange inspection
- **Version management**: Semantic versioning with major/minor/patch compatibility checks and automatic cleanup of stale schemas

## Architecture

### Processing Pipeline

```
WEPP Simulation Completes
    ↓
wepp/output/[H*.dat, *_pw0.txt, chan.out, etc.]
    ↓
run_wepp_hillslope_interchange() ────→ Serial processing
    ├─ remove_incompatible_interchange()  (clean stale schemas)
    ├─ run_wepp_hillslope_pass_interchange()
    ├─ run_wepp_hillslope_ebe_interchange()
    ├─ run_wepp_hillslope_element_interchange()
    ├─ run_wepp_hillslope_loss_interchange()
    ├─ run_wepp_hillslope_soil_interchange()
    └─ run_wepp_hillslope_wat_interchange()
    ↓
run_wepp_watershed_interchange() ────→ Parallel processing (ThreadPoolExecutor)
    ├─ run_wepp_watershed_pass_interchange()
    ├─ run_wepp_watershed_ebe_interchange()
    ├─ run_wepp_watershed_chan_peak_interchange()
    ├─ run_wepp_watershed_chanwb_interchange()
    ├─ run_wepp_watershed_chnwb_interchange()
    ├─ run_wepp_watershed_soil_interchange()
    └─ run_wepp_watershed_loss_interchange()
    ↓
wepp/output/interchange/
    ├─ interchange_version.json  (semantic version manifest)
    ├─ H.pass.parquet
    ├─ H.ebe.parquet
    ├─ H.element.parquet
    ├─ H.loss.parquet
    ├─ H.soil.parquet
    ├─ H.wat.parquet
    ├─ pass_pw0.events.parquet
    ├─ pass_pw0.metadata.parquet
    ├─ ebe_pw0.parquet
    ├─ chan.out.parquet
    ├─ chanwb.parquet
    ├─ chnwb.parquet
    ├─ soil_pw0.parquet
    ├─ loss_pw0.*.parquet (7 tables)
    └─ README.md  (auto-generated schema docs)
```

### Concurrency Model

**Hillslope files**: Processed with `write_parquet_with_pool()` which:
1. Spawns `ProcessPoolExecutor` with `max_workers=NCPU` (or `WEPP_INTERCHANGE_FORCE_SERIAL=1` for debugging)
2. Distributes input files across workers (each worker parses subset of hillslopes)
3. Workers write temp Parquet to `/dev/shm` (or `WEPP_INTERCHANGE_TMP_DIR`)
4. Main process concatenates temp tables and commits atomically
5. Falls back to serial processing on `/dev/shm` mount failures

**Watershed files**: Processed with `ThreadPoolExecutor` because:
- Watershed outputs are single large files (not per-hillslope)
- I/O-bound operations (gzip decompression, file reading) benefit from threads
- Avoids pickle overhead of process pools for large data structures

### Schema Versioning

Every Parquet table includes metadata:
```python
schema = pa.schema([
    pa.field('wepp_id', pa.int32()),
    pa.field('runoff', pa.float64(), metadata={'units': 'm', 'description': 'Runoff depth'}),
    # ...
], metadata={
    'dataset_version_major': '2',
    'dataset_version_minor': '1',
    'dataset_version_patch': '0'
})
```

On each interchange run:
1. Check `interchange_version.json` in target directory
2. If major version differs from current `INTERCHANGE_VERSION`, call `remove_incompatible_interchange()` to purge tables
3. Write new manifest with updated timestamp

This ensures downstream tools never load incompatible schemas after WEPP model updates.

## Pipeline Overview
- `run_wepp_hillslope_interchange()` removes incompatible artifacts, runs the six hillslope writers serially, and returns the refreshed interchange directory.
- `run_wepp_watershed_interchange()` dispatches seven watershed writers in parallel, wiring shared `start_year` handling so truncated simulation years expand to full calendar years.
- `write_parquet_with_pool()` handles fan-out parsing for high-volume hillslope files using a process pool, temp files on `/dev/shm` (overridable), and atomic commits.

### Hillslope Inputs → Outputs
| Input pattern | Writer | Output | Highlights |
| --- | --- | --- | --- |
| `H*.pass.dat` | `run_wepp_hillslope_pass_interchange` | `H.pass.parquet` | Event, sub-event, and no-event runoff plus sediment delivery, particle concentrations, groundwater flux, and water-year indices per hillslope. |
| `H*.ebe.dat` | `run_wepp_hillslope_ebe_interchange` | `H.ebe.parquet` | Storm-scale detachment/deposition metrics with optional `start_year` padding for century-truncated simulation years. |
| `H*.element.dat` | `run_wepp_hillslope_element_interchange` | `H.element.parquet` | Daily element (OFE) hydrology and cover factors; fixed-width parsing backfills missing values with previous-day measurements. |
| `H*.loss.dat` | `run_wepp_hillslope_loss_interchange` | `H.loss.parquet` | Particle class characteristics at the hillslope outlet, including specific gravity and exiting fraction. |
| `H*.soil.dat` | `run_wepp_hillslope_soil_interchange` | `H.soil.parquet` | Daily soil-state variables per OFE (porosity, hydraulic conductivity, water content, saturation). |
| `H*.wat.dat` | `run_wepp_hillslope_wat_interchange` | `H.wat.parquet` | Water balance depths and areas per OFE; includes `load_hill_wat_dataframe()` helper for daily rollups. |

### Watershed Inputs → Outputs
| Input | Writer | Output(s) | Highlights |
| --- | --- | --- | --- |
| `pass_pw0.txt` | `run_wepp_watershed_pass_interchange` | `pass_pw0.events.parquet`, `pass_pw0.metadata.parquet` | Streams PASS events in chunks and captures hillslope metadata (areas, particle diameters, nutrient concentrations). |
| `ebe_pw0.txt` | `run_wepp_watershed_ebe_interchange` | `ebe_pw0.parquet` | Event-by-event runoff, sediment, and pollutant delivery with optional legacy outlet element inference. |
| `chan.out` | `run_wepp_watershed_chan_peak_interchange` | `chan.out.parquet` | Peak discharge timing and magnitude per channel element; feeds `chanout_dss_export()`. |
| `chanwb.out` | `run_wepp_watershed_chanwb_interchange` | `chanwb.parquet` | Daily channel routing balance (inflow, outflow, storage, baseflow, loss, balance). |
| `chnwb.txt` | `run_wepp_watershed_chnwb_interchange` | `chnwb.parquet` | Channel OFE-level water balance, mirroring WAT columns with channel identifiers. |
| `soil_pw0.txt` or `.gz` | `run_wepp_watershed_soil_interchange` | `soil_pw0.parquet` | Watershed soil profile state per OFE (porosity, TSW, hydraulic factors), with transparent gzip support. |
| `loss_pw0.txt` | `run_wepp_watershed_loss_interchange` | `loss_pw0.hill.parquet`, `loss_pw0.chn.parquet`, `loss_pw0.out.parquet`, `loss_pw0.class_data.parquet` plus `all_years` variants | Annual and long-term sediment and pollutant summaries for hillslopes, channels, and outlet along with particle class fractions. |

### Derived and Export Products
- `run_totalwatsed3(interchange_dir, baseflow_opts, wepp_ids=None, *, ash_dir=None)` joins `H.pass.parquet` and `H.wat.parquet` with DuckDB to emit `totalwatsed3.parquet`, computing volumes, depths, baseflow reservoirs, and (when available) ash transport mass totals (including per-type black/white splits) plus ash volumetric concentration and black-ash share.
- `totalwatsed_partitioned_dss_export()` iterates channel tops, filters hillslope WEPP ids via the watershed translator, and writes per-channel DSS time-series files plus derived discharges (`Q (m^3/s)`).
- `chanout_dss_export()` converts `chan.out.parquet` peaks to per-channel DSS records named `peak_chan_{topaz_id}.dss` (optionally tagging Topaz IDs) for hydrologic compatibility with HEC tools; `archive_dss_export_zip()` packages the exports.
- `generate_interchange_documentation()` scans available Parquet tables, renders schema previews with sample rows, and stores a Markdown README alongside the data for consumers.

## Key APIs
| Function | Purpose |
| --- | --- |
| `run_wepp_hillslope_interchange(wepp_output_dir, start_year=None)` | Serial hillslope pipeline; returns `Path` to `interchange/` and writes the version manifest. |
| `run_wepp_watershed_interchange(wepp_output_dir, start_year=None)` | Threaded watershed pipeline; fans out to individual writers and finalizes the manifest. |
| `write_parquet_with_pool(files, parser, schema, target_path, **kwargs)` | Shared fan-out writer that parallelizes parsing, buffers results, and commits atomically (respects `WEPP_INTERCHANGE_FORCE_SERIAL`). |
| `load_hill_wat_dataframe(wepp_output_dir, wepp_id, collapse='daily')` | Convenience accessor returning either daily aggregated or raw OFE-level WAT records via DuckDB. |
| `run_totalwatsed3(interchange_dir, baseflow_opts, wepp_ids=None, *, ash_dir=None)` | Produces watershed-wide daily hydrologic summaries, baseflow diagnostics, and ash transport mass totals from interchange + `ash` parquet files. |
| `totalwatsed_partitioned_dss_export(wd, export_channel_ids=None, status_channel=None)` | Writes one DSS file per channel using `run_totalwatsed3` output and optional status messaging. |
| `chanout_dss_export(wd, status_channel=None)` | Converts channel peak data to per-channel DSS files (`peak_chan_{topaz_id}.dss`), honoring translator lookups and falling back to WEPP IDs as needed. |
| `generate_interchange_documentation(interchange_dir, to_readme_md=True)` | Builds Markdown documentation (schema + previews) for the current interchange directory. |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEPP_INTERCHANGE_FORCE_SERIAL` | `0` | Set to `1` to disable process pool (useful for debugging parsers) |
| `WEPP_INTERCHANGE_TMP_DIR` | `/dev/shm` | Temporary directory for Parquet writes (falls back to target dir if unavailable) |
| `WEPP_INTERCHANGE_MAX_WORKERS` | `NCPU` | Override process pool size (0 = serial, None = use NCPU) |

### Interchange Version Management

The package maintains semantic versioning via `INTERCHANGE_VERSION` (defined in `versioning.py`):

```python
INTERCHANGE_VERSION = (2, 1, 0)  # (major, minor, patch)
```

**Version compatibility rules**:
- **Major version change**: Incompatible schema (column removal, type change) → triggers `remove_incompatible_interchange()`
- **Minor version change**: Backward-compatible addition (new columns with defaults)
- **Patch version change**: Bug fixes, no schema impact

Each interchange run writes `interchange_version.json`:
```json
{
  "major": 2,
  "minor": 1,
  "patch": 0,
  "timestamp": "2025-10-23T22:15:30.123456"
}
```

Downstream tools should check `needs_major_refresh(interchange_dir)` before loading to avoid schema mismatch errors.

### File Naming Conventions

| Pattern | Description | Example |
|---------|-------------|---------|
| `H.{report}.parquet` | Hillslope report (aggregated across all hillslopes) | `H.pass.parquet` |
| `{report}_pw0.parquet` | Watershed report (single file) | `ebe_pw0.parquet` |
| `{report}_pw0.{suffix}.parquet` | Multi-table watershed report | `loss_pw0.hill.parquet` |
| `totalwatsed3.parquet` | Derived daily watershed summary | `totalwatsed3.parquet` |

### Parquet Compression and Encoding

All tables use:
- **Compression**: Snappy (balance between speed and compression ratio)
- **Encoding**: Dictionary encoding for categorical columns (`wepp_id`, `event`, `month`)
- **Row groups**: Default PyArrow settings (~128 MB uncompressed)

Typical size reduction: **10–50× smaller than raw text** (depending on data sparsity and repetition).

## Data Conventions
- Every table carries calendar fields (`year`, `julian`, `month`, `day_of_month`, `water_year`) so temporal joins remain trivial across datasets.
- `schema_with_version()` injects `dataset_version*` metadata fields; readers can assert major compatibility before loading.
- Units and descriptions live in column metadata (e.g., `b"units"`, `b"description"`), enabling automated chart labeling and export tooling.
- Writers default to Snappy-compressed Parquet with dictionary encoding; empty inputs still yield valid empty tables.
- The package cleans incompatible outputs by comparing manifest major versions via `remove_incompatible_interchange()`, ensuring stale schemas never leak forward.

### Standard Column Schema

All interchange tables include these temporal index columns:

| Column | Type | Description |
|--------|------|-------------|
| `wepp_id` | `int32` | Hillslope or channel identifier (lowercase per ID normalization) |
| `year` | `int16` | Calendar year |
| `julian` | `int16` | Day of year (1–366) |
| `month` | `int8` | Month (1–12) |
| `day_of_month` | `int8` | Day of month (1–31) |
| `water_year` | `int16` | Water year (October 1 → September 30) |
| `sim_day_index` | `int32` | 1-indexed day since simulation start (for event ordering) |

Additional columns vary by report type but follow these conventions:

**Units**:
- Depths: `m` (meters)
- Volumes: `m^3` (cubic meters)
- Mass: `kg` (kilograms)
- Concentration: `kg/m^3`
- Discharge: `m^3/s`
- Duration: `s` (seconds) or `h` (hours) or `day`

**Metadata example**:
```python
pa.field('runoff', pa.float64(), metadata={
    b'units': b'm',
    b'description': b'Runoff depth from hillslope',
    b'wepp_report': b'PASS'
})
```

### Handling Missing Data

- **Missing numeric values**: Represented as PyArrow `null` (not NaN or sentinel values)
- **Empty reports**: Produce valid empty Parquet tables (0 rows, correct schema)
- **Partial simulation years**: `start_year` parameter pads truncated years to full calendar years for consistent indexing

### ID Normalization

Per 2025 ID standardization effort:
- All `wepp_id` columns use **lowercase** `Int32` (not `WEPP_ID`, not string)
- Parquet exports, GeoJSON, and DuckDB queries expect lowercase
- Migration CLIs ensure legacy uppercase schemas are converted before interchange runs

## Quick Start

### Example 1: Basic Hillslope Interchange

```python
from pathlib import Path
from wepppy.wepp.interchange import run_wepp_hillslope_interchange

# After running WEPP simulation
wepp_output_dir = Path("/geodata/weppcloud_runs/abc123/CurCond/wepp/output")

# Transform all hillslope text reports → Parquet
interchange_dir = run_wepp_hillslope_interchange(
    wepp_output_dir, 
    start_year=1990  # Optional: pads century-truncated simulation years
)

# Result: wepp_output_dir/interchange/ contains:
#   - H.pass.parquet
#   - H.ebe.parquet
#   - H.element.parquet
#   - H.loss.parquet
#   - H.soil.parquet
#   - H.wat.parquet
#   - interchange_version.json
```

### Example 2: Watershed Interchange with DuckDB Queries

```python
import duckdb
from wepppy.wepp.interchange import run_wepp_watershed_interchange

wepp_output_dir = Path("/geodata/weppcloud_runs/abc123/CurCond/wepp/output")
interchange_dir = run_wepp_watershed_interchange(wepp_output_dir, start_year=1990)

# Query watershed PASS events with DuckDB
con = duckdb.connect()
result = con.execute(f"""
    SELECT 
        wepp_id,
        year,
        month,
        SUM(sed_leave) as monthly_sediment_kg
    FROM read_parquet('{interchange_dir}/pass_pw0.events.parquet')
    WHERE year = 2020
    GROUP BY wepp_id, year, month
    ORDER BY monthly_sediment_kg DESC
    LIMIT 10
""").df()

print(result)
# Output: Top 10 hillslopes by monthly sediment delivery in 2020
```

### Example 3: Generate totalwatsed3 Daily Summaries

```python
from wepppy.wepp.interchange import run_totalwatsed3
from wepppy.nodb.core.wepp import BaseflowOpts

interchange_dir = Path("/geodata/weppcloud_runs/abc123/CurCond/wepp/output/interchange")

# Join H.pass.parquet + H.wat.parquet → daily watershed totals
baseflow_opts = BaseflowOpts(
    gwstorage=100.0,  # mm
    bfcoeff=0.04,     # 1/day
    dscoeff=0.00,     # 1/day
    bfthreshold=1.01
)

total_path = run_totalwatsed3(
    interchange_dir, 
    baseflow_opts,
    wepp_ids=None  # None = all hillslopes
)

# Optional: include first-year ash transport masses if ash runs exist
# total_path = run_totalwatsed3(interchange_dir, baseflow_opts, ash_dir=Path("/geodata/weppcloud_runs/abc123/CurCond/ash"))

# Load result
import pyarrow.parquet as pq
df = pq.read_table(total_path).to_pandas()

print(df[['date', 'precip_mm', 'runoff_mm', 'baseflow_mm', 'sediment_kg']].head(10))
```

### Example 4: Export to HEC-DSS

```python
from wepppy.wepp.interchange import totalwatsed_partitioned_dss_export

wd = Path("/geodata/weppcloud_runs/abc123/CurCond")

# Generate DSS files for each channel (requires pydsstools)
totalwatsed_partitioned_dss_export(
    wd,
    export_channel_ids=None,  # None = all channels
    status_channel=None       # Optional Redis pub/sub channel
)

# Result: wd/export/totalwatsed_{channel_id}.dss files
# Each contains timeseries: precip, runoff, baseflow, sediment, discharge
```

### Example 5: Auto-Generate Documentation

```python
from wepppy.wepp.interchange import generate_interchange_documentation

interchange_dir = Path("/geodata/weppcloud_runs/abc123/CurCond/wepp/output/interchange")

# Scan all Parquet tables and create schema documentation
generate_interchange_documentation(interchange_dir, to_readme_md=True)

# Result: interchange_dir/README.md with:
#   - Table of contents
#   - Schema for each Parquet file (column names, types, units, descriptions)
#   - Sample rows (first 5 records)
```

### Example 6: Query Hillslope Water Balance

```python
from wepppy.wepp.interchange import load_hill_wat_dataframe

wepp_output_dir = Path("/geodata/weppcloud_runs/abc123/CurCond/wepp/output")

# Get daily aggregated water balance for hillslope 42
df_daily = load_hill_wat_dataframe(wepp_output_dir, wepp_id=42, collapse='daily')
print(df_daily[['date', 'prcp', 'runoff', 'et', 'dp']].head())

# Get raw OFE-level (Overland Flow Element) water balance
df_ofe = load_hill_wat_dataframe(wepp_output_dir, wepp_id=42, collapse=None)
print(df_ofe[['date', 'ofe', 'prcp', 'runoff']].head())
```

## Quick Start
```python
from pathlib import Path
import pyarrow.parquet as pq

from wepppy.wepp.interchange import (
    run_wepp_hillslope_interchange,
    run_wepp_watershed_interchange,
    run_totalwatsed3,
    generate_interchange_documentation,
)
from wepppy.nodb.core.wepp import BaseflowOpts

output_dir = Path("/runs/demo/wepp/output")
run_wepp_hillslope_interchange(output_dir, start_year=1990)
run_wepp_watershed_interchange(output_dir, start_year=1990)

# Load watershed PASS events into pandas or Arrow
pass_events = pq.read_table(output_dir / "interchange/pass_pw0.events.parquet")

# Produce watershed-wide daily totals (uses H.pass + H.wat)
total_path = run_totalwatsed3(output_dir / "interchange", BaseflowOpts())
totals = pq.read_table(total_path)

# Ship autogenerated documentation alongside the data
generate_interchange_documentation(output_dir / "interchange")
```

## Integration with WEPPcloud Workflow

The interchange system is invoked automatically after WEPP simulations complete:

```python
# In wepppy/rq/wepp_rq.py
from wepppy.wepp.interchange import (
    run_wepp_hillslope_interchange,
    run_wepp_watershed_interchange
)

@job('default', timeout=3600)
def run_wepp_postprocessing(wd, start_year=None):
    wepp_output_dir = Path(wd) / "wepp/output"
    
    # Transform text → Parquet
    run_wepp_hillslope_interchange(wepp_output_dir, start_year)
    run_wepp_watershed_interchange(wepp_output_dir, start_year)
    
    # Query engine can now access structured data
    from wepppy.query_engine import update_catalog_entry
    update_catalog_entry(wd)
```

Downstream consumers:

1. **Query Engine** (`wepppy/query_engine/`)
   - Executes DuckDB SQL over interchange Parquet
   - Serves `/query/` API endpoints with sub-100ms response times
   - Powers loss reports, timeseries charts, spatial queries

2. **Export Modules** (`wepppy/wepp/out/`)
   - DSS export: `totalwatsed_partitioned_dss_export()` → HEC-HMS/HEC-RAS compatible
   - NetCDF export: Reads interchange Parquet → CF-compliant NetCDF
   - GeoJSON export: Joins spatial topology with interchange loss summaries

3. **D-Tale Explorer** (`wepppy/weppcloud/webservices/dtale.py`)
   - Auto-discovers interchange Parquet tables
   - Provides interactive filtering, charting, correlation analysis
   - Handles multi-GB datasets via Arrow zero-copy

4. **Status Dashboards** (`wepppy/weppcloud/routes/query/`)
   - Checks `interchange_version.json` timestamp for completion status
   - Streams progress via WebSocket during long exports

## Developer Notes
## Developer Notes

### Adding a New Interchange Parser

Follow the established pattern from existing parsers:

1. **Create module**: `wepppy/wepp/interchange/hill_newreport_interchange.py` or `watershed_newreport_interchange.py`

2. **Define schema with versioning**:
```python
from .schema_utils import pa_field
from .versioning import schema_with_version

SCHEMA = schema_with_version(
    pa.schema([
        pa_field("wepp_id", pa.int32()),
        pa_field("year", pa.int16()),
        pa_field("julian", pa.int16()),
        pa_field("new_metric", pa.float64(), units="kg/ha", description="Your new metric"),
        # ...
    ])
)

EMPTY_TABLE = pa.table({name: [] for name in SCHEMA.names}, schema=SCHEMA)
```

3. **Implement parser function**:
```python
def _parse_newreport_line(line: str, start_year: int) -> dict:
    # Parse fixed-width or delimited text
    # Return dict matching schema column names
    pass

def run_wepp_hillslope_newreport_interchange(
    wepp_output_dir: Path,
    start_year: Optional[int] = None
) -> Path:
    pattern = "H*.newreport.dat"
    files = sorted(wepp_output_dir.glob(pattern))
    
    if not files:
        target = wepp_output_dir / "interchange/H.newreport.parquet"
        pq.write_table(EMPTY_TABLE, target)
        return target
    
    # For high-volume: use write_parquet_with_pool
    from .concurrency import write_parquet_with_pool
    
    target = wepp_output_dir / "interchange/H.newreport.parquet"
    write_parquet_with_pool(
        files=files,
        parser=lambda f: _parse_file(f, start_year),
        schema=SCHEMA,
        target_path=target
    )
    return target
```

4. **Add to `__init__.py`**:
```python
from .hill_newreport_interchange import run_wepp_hillslope_newreport_interchange

__all__ = [
    # ...
    "run_wepp_hillslope_newreport_interchange",
]
```

5. **Integrate into pipeline**:
   - Add call in `hill_interchange.py` or `watershed_interchange.py`
   - Update `INTERCHANGE_VERSION` if schema is incompatible

6. **Add tests**:
```python
# tests/wepp/interchange/test_newreport.py
import pytest
from wepppy.wepp.interchange import run_wepp_hillslope_newreport_interchange

@pytest.mark.integration
def test_newreport_interchange(tmp_path):
    # Create fixture files in tmp_path
    # Run parser
    # Assert Parquet schema and row count
    pass
```

### Testing Patterns

- **Use fixtures**: Store sample WEPP output files in `tests/data/wepp/output/`
- **Test empty inputs**: Ensure empty file lists produce valid empty Parquet tables
- **Test schema metadata**: Verify `units` and `description` fields are preserved
- **Test versioning**: Check `dataset_version_major` metadata is correct
- **Benchmark performance**: Use `pytest --benchmark` for large file parsing

Example test:
```python
import pyarrow.parquet as pq
from wepppy.wepp.interchange import run_wepp_hillslope_pass_interchange

def test_pass_interchange_schema(wepp_output_fixture):
    result_path = run_wepp_hillslope_pass_interchange(wepp_output_fixture)
    
    table = pq.read_table(result_path)
    assert 'wepp_id' in table.column_names
    assert 'runoff' in table.column_names
    
    # Check metadata
    runoff_field = table.schema.field('runoff')
    assert runoff_field.metadata[b'units'] == b'm'
    assert b'Runoff depth' in runoff_field.metadata[b'description']
```

### Performance Optimization Tips

1. **Use process pools for high-volume files**:
   - Hillslope reports benefit from parallel parsing (100+ files)
   - Watershed reports are already single-file → use threads or serial

2. **Profile with `/dev/shm`**:
   - Temporary writes to RAM disk avoid I/O bottlenecks
   - Fall back gracefully if `/dev/shm` is unavailable

3. **Batch PyArrow operations**:
   - Build row dicts in lists → create table once
   - Avoid row-by-row table append (very slow)

4. **Use DuckDB for aggregations**:
   - Don't load full Parquet → pandas for simple queries
   - DuckDB can scan 10+ GB Parquet in seconds with SQL

5. **Monitor memory usage**:
   - Large watershed PASS files (100+ MB) can spike memory during parsing
   - Consider streaming or chunked parsing for multi-GB inputs

### Common Pitfalls

- **Fixed-width parsing off-by-one errors**: WEPP reports use FORTRAN column conventions (1-indexed, inclusive ranges). Verify with sample files.
- **Multi-line continuations**: Some WEPP outputs wrap long lines. See `hill_pass_interchange.py` for continuation handling pattern.
- **Missing calendar fields**: Always populate `year`, `julian`, `month`, `day_of_month`, `water_year` for consistency.
- **Unit mismatches**: WEPP uses mixed units (mm, m, kg/ha, kg). Standardize to SI in interchange (m, kg).
- **Leap year handling**: WEPP simulations may truncate to 365-day years. Use `start_year` parameter to expand.
- **Gzip transparency**: Watershed outputs may be gzipped. Use `gzip.open()` or copy to temp file before parsing.
- **ID normalization**: Always use lowercase `wepp_id` (Int32), not `WEPP_ID` or string variants.

### Code Organization

```
interchange/
├── __init__.py                         # Public API exports
├── _utils.py                           # Shared parsing helpers (_parse_float, _julian_to_calendar)
├── concurrency.py                      # write_parquet_with_pool (process pool fan-out)
├── schema_utils.py                     # pa_field helper (adds metadata shorthand)
├── versioning.py                       # INTERCHANGE_VERSION, schema_with_version, manifest I/O
│
├── hill_pass_interchange.py            # Hillslope PASS parser
├── hill_ebe_interchange.py             # Hillslope EBE parser
├── hill_element_interchange.py         # Hillslope Element parser
├── hill_loss_interchange.py            # Hillslope Loss parser
├── hill_soil_interchange.py            # Hillslope Soil parser
├── hill_wat_interchange.py             # Hillslope WAT parser
├── hill_interchange.py                 # Hillslope orchestrator
│
├── watershed_pass_interchange.py       # Watershed PASS parser
├── watershed_ebe_interchange.py        # Watershed EBE parser
├── watershed_chan_peak_interchange.py  # Channel peak (chan.out) parser
├── watershed_chanwb_interchange.py     # Channel water balance (chanwb.out) parser
├── watershed_chnwb_interchange.py      # Channel OFE water balance (chnwb.txt) parser
├── watershed_soil_interchange.py       # Watershed soil (soil_pw0.txt) parser
├── watershed_loss_interchange.py       # Watershed loss (loss_pw0.txt) parser
├── watershed_interchange.py            # Watershed orchestrator
│
├── totalwatsed3.py                     # DuckDB-based daily watershed aggregator
├── watershed_totalwatsed_export.py     # DSS export tooling (HEC integration)
└── interchange_documentation.py        # Auto-generate README.md with schemas
```

### Dependencies

- **PyArrow** (`pyarrow`): Parquet I/O, schema metadata
- **DuckDB** (`duckdb`): SQL queries over Parquet, aggregations
- **NumPy** (`numpy`): Array operations, datetime handling
- **Pandas** (`pandas`): DataFrame construction (for legacy consumers)
- **pydsstools** (optional): HEC-DSS export (not required for core interchange)

### Debugging Tips

1. **Force serial processing**: `export WEPP_INTERCHANGE_FORCE_SERIAL=1` to disable process pool
2. **Inspect raw text**: Compare Parquet output to source `.dat` files line-byline
3. **Use Parquet tools**: `parquet-tools schema H.pass.parquet` or `parquet-tools head H.pass.parquet`
4. **DuckDB shell**: `duckdb` then `SELECT * FROM 'H.pass.parquet' LIMIT 10;`
5. **Check version manifest**: `cat interchange_version.json` to verify compatibility
6. **Enable logging**: Interchange modules log to `wepppy.wepp.interchange` logger

- `write_parquet_with_pool` uses a process pool sized by `wepppy.all_your_base.NCPU`; set `WEPP_INTERCHANGE_FORCE_SERIAL=1` or `max_workers=0` to force single-process parsing when debugging.
- Temporary Parquet writes land in `/dev/shm` by default (`WEPP_INTERCHANGE_TMP_DIR` overrides) and fall back to the target directory on cross-device errors.
- Watershed soil and PASS writers transparently accept gzipped inputs, copying them to temporary plain-text files before parsing.
- DSS exports require `pydsstools`; the import is optional so the interchange core remains usable without HEC tooling.
- The package relies on `pyarrow`, `duckdb`, `numpy`, and `pandas`; ensure these remain in sync with the Docker image and stubbed dependencies.
- Status updates use `StatusMessenger.publish` when available, keeping long-running exports visible in NoDb-driven dashboards.

## Troubleshooting

### "Interchange version mismatch" error
**Symptom**: Query engine or export tools fail with schema compatibility errors.

**Solution**:
1. Check `interchange_version.json` major version
2. Re-run `run_wepp_hillslope_interchange()` and `run_wepp_watershed_interchange()` to regenerate with current schema
3. Major version changes trigger automatic cleanup via `remove_incompatible_interchange()`

### Parquet files are empty (0 rows)
**Symptom**: Valid Parquet schema but no data rows.

**Causes**:
- No matching input files found (check `H*.dat` or `*_pw0.txt` existence)
- WEPP simulation failed before generating reports
- Glob pattern mismatch (verify file naming conventions)

**Solution**: Verify WEPP simulation completed successfully and output files exist in `wepp/output/`.

### Process pool hangs during hillslope interchange
**Symptom**: `run_wepp_hillslope_interchange()` stalls with no progress.

**Solution**:
1. Set `WEPP_INTERCHANGE_FORCE_SERIAL=1` to disable process pool
2. Check `/dev/shm` availability and permissions
3. Inspect individual `.dat` files for malformed content
4. Enable debug logging to identify which file is problematic

### "/dev/shm cross-device link" error
**Symptom**: Temporary file writes fail with `OSError: Invalid cross-device link`.

**Cause**: `/dev/shm` is on a different filesystem than target directory.

**Solution**: Set `WEPP_INTERCHANGE_TMP_DIR` to a path on the same filesystem:
```bash
export WEPP_INTERCHANGE_TMP_DIR=/tmp
```

### DSS export fails with "pydsstools not found"
**Symptom**: `totalwatsed_partitioned_dss_export()` raises ImportError.

**Solution**: Install optional dependency:
```bash
pip install pydsstools
```
Or skip DSS export and use Parquet outputs directly.

### DuckDB queries return wrong units
**Symptom**: Query results have unexpected magnitudes.

**Cause**: Unit metadata is documentation-only; DuckDB doesn't enforce units.

**Solution**: 
- Always check column metadata (`table.schema.field('runoff').metadata[b'units']`)
- Apply conversions explicitly in SQL (e.g., `runoff * 1000` for m → mm)

### Parquet files are much larger than expected
**Symptom**: Interchange directory is 10+ GB for small watershed.

**Causes**:
- Uncompressed Parquet (should use Snappy by default)
- Excessive row duplication (check for parsing bugs)
- String columns instead of dictionary-encoded categoricals

**Solution**:
1. Verify compression: `parquet-tools meta H.pass.parquet | grep -i compression`
2. Check schema types (should use `int32` for IDs, not string)
3. Reprocess with corrected parsers

### "Simulation year truncation" warnings
**Symptom**: Logs show "Padding simulation years from XX to full calendar year".

**Cause**: WEPP simulations configured for <100 years may truncate century digits.

**Solution**: Pass `start_year` parameter to expand truncated years:
```python
run_wepp_hillslope_interchange(output_dir, start_year=1990)
```

## Further Reading
## Further Reading

### Within wepppy Repository

- **AGENTS.md** § Module Organization Best Practices (exports, versioning conventions)
- **AGENTS.md** § Performance Optimization (Rust acceleration, caching strategies)
- `wepppy/wepp/README.md` - WEPP model integration overview
- `wepppy/query_engine/README.md` - DuckDB query layer over interchange
- `wepppy/wepp/out/README.md` - Export modules (DSS, NetCDF, GeoJSON)
- `tests/wepp/interchange/` - Comprehensive test suite with fixtures

### Module Documentation

- [`interchange_documentation.py`](interchange_documentation.py) – Schema renderer that powers autogenerated interchange READMEs
- [`totalwatsed3.py`](totalwatsed3.py) – DuckDB-based watershed aggregator and baseflow computation logic
- [`watershed_totalwatsed_export.py`](watershed_totalwatsed_export.py) – DSS export orchestration and integration with watershed topology translators
- [`versioning.py`](versioning.py) – Manifest helpers, semantic version model, and compatibility checks
- [`concurrency.py`](concurrency.py) – Process pool fan-out implementation with temp file handling
- [`schema_utils.py`](schema_utils.py) – PyArrow schema utilities and metadata helpers

### External Resources

- [Apache Arrow Parquet Format](https://parquet.apache.org/docs/) - Parquet file format specification
- [DuckDB Documentation](https://duckdb.org/docs/) - SQL queries over Parquet files
- [PyArrow Documentation](https://arrow.apache.org/docs/python/) - Python bindings for Arrow/Parquet
- [HEC-DSS](https://www.hec.usace.army.mil/software/hec-dss/) - Hydrologic Engineering Center Data Storage System
- [WEPP Model Documentation](https://www.ars.usda.gov/research/software/download/?softwareid=492) - Official WEPP model reference

### Related Work

- **WEPP Output Formats**: Understanding WEPP text report structures (see `wepppy/wepp/out/` parsers for legacy implementations)
- **Parquet Best Practices**: [Parquet file tips](https://arrow.apache.org/docs/python/parquet.html#finer-grained-writing-and-reading) for optimal compression and performance
- **DuckDB + Parquet Integration**: [DuckDB Parquet guide](https://duckdb.org/docs/data/parquet) for efficient queries

## Credits

**Development**: Roger Lew (University of Idaho, 2015–Present)

**WEPP Model**: USDA Agricultural Research Service (ARS), National Soil Erosion Research Laboratory

**Funding**: 
- NSF Idaho EPSCoR (IIA-1301792)
- USDA Forest Service
- USGS

**Technology Stack**:
- Apache Arrow/Parquet: Wes McKinney, Apache Software Foundation
- DuckDB: Mark Raasveldt, Hannes Mühleisen (CWI Amsterdam)

**License**: BSD-3 Clause (see `license.txt` in repository root)
