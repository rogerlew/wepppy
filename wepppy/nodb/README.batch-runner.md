# Batch Runner

> Orchestrates parallel WEPPcloud runs across a collection of watershed features, cloning a canonical base project for each and tracking progress through Redis-backed task state.

> **See also:** [AGENTS.md](../../AGENTS.md) for Working with NoDb Controllers and RQ Background Tasks sections; [routes/batch_runner/README.md](../weppcloud/routes/batch_runner/README.md) for the Pure UI blueprint specification.

## Overview

The batch runner lets admins prepare a single "base" WEPPcloud project, upload a GeoJSON of watershed polygons, and execute the full WEPP pipeline for every feature in parallel. Each watershed gets its own run directory cloned from the base, with the DEM fetched for that feature's bounding box, outlet snapped to the feature geometry, and the rest of the standard pipeline (channels, soils, landuse, climate, WEPP) executed autonomously.

**Where it fits:** The batch runner sits between the NoDb controller layer and the RQ job system. It reuses every existing NoDb singleton (Ron, Watershed, Landuse, Soils, Climate, Wepp) rather than introducing new data models. The `BatchRunner` controller manages batch-level state while individual runs behave identically to interactive WEPPcloud runs.

**Primary users:**
- Admins configuring batch projects through the WEPPcloud UI
- RQ workers executing per-watershed jobs on the `batch` queue
- AI agents and scripts automating multi-watershed campaigns

**Key capabilities:**
- Upload a GeoJSON FeatureCollection defining watershed boundaries
- Template-driven run ID generation with safe expression evaluation
- Configurable run directives (toggle individual pipeline stages)
- Optional soil burn severity (SBS) map upload, auto-cropped per run
- LPT (largest-polygon-first) scheduling for better resource utilization
- Per-run file logging and emoji-based progress reporting
- Fault isolation: individual watershed failures do not abort the batch

## Workflow

```
Create Batch          Upload GeoJSON         Validate Template
    │                      │                       │
    ▼                      ▼                       ▼
BatchRunner()      register_geojson()      validate_template()
scaffolds _base/   analyzes features       evaluates {properties["name"]}
with base config   persists metadata       checks for duplicates/errors
    │                      │                       │
    └──────────────────────┴───────────────────────┘
                           │
                    Run Batch (RQ)
                           │
                    run_batch_rq()
                    enqueues N jobs on "batch" queue
                           │
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
      run_batch_        run_batch_       run_batch_
      watershed_rq()   watershed_rq()   watershed_rq()
      (largest first)                   (smallest last)
              │            │                │
              └────────────┼────────────────┘
                           ▼
                  _final_batch_complete_rq()
                  emits BATCH_RUN_COMPLETED
```

Each `run_batch_watershed_rq` call:
1. Clones `_base/` into `runs/<runid>/`
2. Patches `.nodb` files with the new working directory
3. Saves the feature geometry as `dem/target_watershed.geojson`
4. Walks the pipeline stages gated by run directives and `RedisPrep` timestamps

## Key Concepts

### Run ID Semantics

Batch runs use prefixed run IDs: `batch;;<batch_name>;;<feature_runid>`. The base project resolves to `batch;;<batch_name>;;_base`. This prefix scheme keeps existing `/weppcloud/<runid>/<config>` routes working without special casing.

### Run Directives

Each pipeline stage can be toggled on or off. The default set:

| Directive | Default | Description |
|-----------|---------|-------------|
| `fetch_dem` | on | Fetch DEM for the feature's bounding box |
| `build_channels` | on | Extract channel network from DEM |
| `find_outlet` | on | Snap outlet to feature geometry |
| `build_subcatchments` | on | Delineate subcatchments |
| `abstract_watershed` | on | Abstract watershed topology |
| `build_landuse` | on | Build landuse from configured source |
| `build_soils` | on | Build soils from configured source |
| `build_climate` | on | Build climate inputs |
| `fetch_rap_ts` | on | Fetch RAP time series (if mod enabled) |
| `fetch_openet_ts` | on | Fetch OpenET time series (if mod enabled) |
| `run_wepp_hillslopes` | on | Run WEPP hillslope simulations |
| `run_wepp_watershed` | on | Run WEPP watershed simulation |
| `run_omni_scenarios` | on | Run OMNI scenario analysis |
| `run_omni_contrasts` | on | Run OMNI contrast analysis |
| `rmtree` | **off** | Remove existing run directory before starting |

### Template Evaluation

Run IDs are generated from GeoJSON feature properties using safe expressions:

```
{properties["name"]}                     → "Leech"
{slug(properties["Site Name"])}          → "cedar-grove"
{properties["basin"]}-{index:03d}        → "sooke-004"
{zfill(one_based_index, 3)}              → "001"
{upper(properties["code"])}              → "GOLD"
{replace(properties["name"], " ", "-")}  → "Blue-Creek"
```

**Available context variables:** `properties`, `feature`, `index` (0-based), `one_based_index` (1-based)

**Built-in functions:** `slug`, `lower`, `upper`, `title`, `zfill`, `replace`

Templates are validated before runs can start. Validation checks for evaluation errors, empty results, and duplicate run IDs.

### GeoJSON Requirements

- Must be a valid GeoJSON `FeatureCollection`
- Features should be `Polygon` or `MultiPolygon` geometries (for watershed boundary masking) or `Point` geometries (for outlet-based delineation)
- Each feature must have properties referenced by the run ID template
- Maximum upload size: 10 MB (configurable via `BATCH_GEOJSON_MAX_MB`)
- CRS should be WGS84 (EPSG:4326) for the WGS version; UTM projections also supported

### LPT Scheduling

Features are sorted by area (largest polygon first) before enqueueing. This Longest Processing Time heuristic improves parallel utilization by starting expensive jobs early.

## Directory Structure

```
<batch_root>/<batch_name>/
├── batch_runner.nodb          # BatchRunner state (JSON)
├── _base/                     # Canonical project scaffold
│   ├── ron.nodb               # Ron controller (config, DEM source, etc.)
│   ├── watershed.nodb         # Watershed controller
│   ├── landuse.nodb           # Landuse controller
│   ├── soils.nodb             # Soils controller
│   ├── climate.nodb           # Climate controller
│   ├── wepp.nodb              # WEPP controller
│   └── ...                    # Other NoDb singletons
├── runs/                      # Per-watershed run directories
│   ├── Leech/                 # Cloned from _base/, DEM fetched for Leech bbox
│   ├── Deception/
│   └── ...
├── resources/                 # User uploads
│   ├── watersheds.geojson     # Uploaded watershed collection
│   └── sbs_map.tif            # Optional soil burn severity map
└── logs/                      # Per-run log files
    ├── batch_runner_Leech.log
    └── ...
```

## Usage

### Creating a Batch (UI)

1. Navigate to `/batch/create/` (admin-only, feature-flagged)
2. Enter a batch name and select a base config (e.g., `canada-wbt`)
3. Configure the base project parameters (DEM source, climate, landuse, soils)
4. Upload a watershed GeoJSON under "Watershed GeoJSON"
5. Set the run ID template (e.g., `{properties["name"]}`)
6. Validate the template and review the preview table
7. Adjust run directives if needed
8. Click "Run Batch"

### Creating a Batch (Python)

```python
from wepppy.nodb.batch_runner import BatchRunner

# Create
batch = BatchRunner('/path/to/batch/Victoria', 'canada-wbt', 'canada-wbt')

# Register GeoJSON
from wepppy.topo.watershed_collection import WatershedCollection
wc = WatershedCollection('/path/to/batch/Victoria/resources/watersheds.geojson')
batch.register_geojson(wc)

# Validate template
wc = batch.get_watershed_collection()
result = wc.validate_template('{properties["name"]}')
print(result['summary'])  # {'is_valid': True, 'unique_run_ids': 32, ...}

# Set template state
batch.runid_template_state = result

# Check progress
print(batch.generate_runstate_cli_report())
```

### Enqueuing via RQ

```python
from wepppy.rq.batch_rq import run_batch_rq

# Enqueue on the "batch" queue (normally done via rq-engine API)
run_batch_rq('Victoria')
```

### Preparing Watershed GeoJSON from Pourpoints

When watershed polygons don't already exist, the `tools/batch_prep_from_pourpoints.py` tool delineates them from pourpoints using an existing WBT workspace. It requires a WEPPcloud run that has already been processed through the DEM/WBT stage (i.e., `flovec.tif` and `netful.tif` exist).

**Pipeline:**
1. Snap each pourpoint to the nearest stream cell (`find_outlet`)
2. Deduplicate pourpoints that snap to the same cell
3. Combine snapped points into a single GeoJSON
4. Run WBT `watershed` to delineate drainage basins
5. Polygonize, dissolve, and reproject to WGS84

**From a CSV file:**

```bash
python -m tools.batch_prep_from_pourpoints \
    --wbt-wd /wc1/runs/my-run/dem/wbt \
    --pourpoints pourpoints.csv \
    --output-dir ./batch_watersheds
```

CSV format (`name,lon,lat` header required):

```
name,lon,lat
Leech,-123.714644,48.494946
Deception,-123.715526,48.517161
```

**From inline arguments:**

```bash
python -m tools.batch_prep_from_pourpoints \
    --wbt-wd /wc1/runs/my-run/dem/wbt \
    --pourpoint "Leech,-123.714644,48.494946" \
    --pourpoint "Deception,-123.715526,48.517161" \
    --output-dir ./batch_watersheds
```

**From JSON or GeoJSON:**

```bash
python -m tools.batch_prep_from_pourpoints \
    --wbt-wd /wc1/runs/my-run/dem/wbt \
    --pourpoints pourpoints.json \
    --output-dir ./batch_watersheds
```

**CLI options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--wbt-wd` | (required) | WBT working directory containing `flovec.tif` and `netful.tif` |
| `--pourpoints` | — | Path to CSV, JSON, or GeoJSON file with pourpoints |
| `--pourpoint` | — | Inline `"name,lon,lat"` (repeatable) |
| `--output-dir` | `<wbt-wd>/batch_watersheds` | Output directory |
| `--flovec` | `flovec.tif` | Flow direction raster filename |
| `--streams` | `netful.tif` | Streams raster filename |
| `--verbose` | off | Enable verbose WBT output |

**Output files:**

| File | Description |
|------|-------------|
| `watersheds.WGS.geojson` | Dissolved watershed polygons in WGS84 — upload this to the batch runner |
| `watersheds.geojson` | Same polygons in the DEM's native CRS (UTM) |
| `pourpoints_snapped.geojson` | Combined snapped pourpoints (native CRS) |
| `watersheds.tif` | Raw watershed raster |
| `outlet_<name>.geojson` | Per-pourpoint snapped outlet (one per input) |

**Prerequisites:** The WBT workspace must belong to a run that has completed DEM processing. The tool locates the WhiteboxTools binary via `$WBT_BIN_DIR` or the default path `/workdir/weppcloud-wbt/target/release`.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BATCH_RUNNER_ENABLED` | `false` | Feature flag gating batch creation in the UI |
| `BATCH_GEOJSON_MAX_MB` | `10` | Maximum GeoJSON upload size in megabytes |
| `RQ_REDIS_URL` | `redis://localhost:6379/9` | Redis connection for RQ job queue |

### Base Config

The base config (e.g., `canada-wbt`) determines DEM source, landuse mapping, soils database, climate options, and WEPP binary for all runs in the batch. See `wepppy/nodb/configs/` for available configurations.

### Docker Worker

The `rq-worker-batch` service processes jobs on the `batch` queue. See [docker/prod-worker-deploy-guide.md](../../docker/prod-worker-deploy-guide.md) for scaling workers across machines.

```yaml
# docker-compose.prod.worker.yml (excerpt)
rq-worker-batch:
  environment:
    - RQ_QUEUES=batch
    - RQ_WORKER_COUNT=4
```

## Integration Points

- **Depends on:** `Ron`, `Watershed`, `Landuse`, `Soils`, `Climate`, `Wepp` (all NoDb singletons); `RedisPrep` for task state; `WatershedCollection` for GeoJSON handling; `StatusMessenger` for real-time events
- **Used by:** `batch_runner_bp` (Flask routes), `batch_runner.js` (frontend controller), `rq_engine` batch routes
- **RQ tasks:** `run_batch_rq` (orchestrator), `run_batch_watershed_rq` (per-feature), `_final_batch_complete_rq` (finalizer)
- **Status channel:** `<batch_name>:batch` (Redis pub/sub for real-time updates)

## Persistence

- **Filename:** `batch_runner.nodb`
- **Redis cache:** DB 13, 72-hour TTL (standard NoDb caching)
- **Locking:** Required for all mutations via `nodb_setter` decorator
- **Run directives:** Serialized with string keys (TaskEnum values), deserialized back to TaskEnum on load

## Developer Notes

### Code Organization

| File | Responsibility |
|------|----------------|
| `wepppy/nodb/batch_runner.py` | `BatchRunner` NoDb controller — state, directives, GeoJSON registration |
| `wepppy/rq/batch_rq.py` | RQ job functions — orchestration, per-watershed execution, finalizer |
| `wepppy/topo/watershed_collection/` | `WatershedCollection`, `WatershedFeature` — GeoJSON parsing, template evaluation |
| `wepppy/nodb/redis_prep.py` | `RedisPrep`, `TaskEnum` — per-task progress tracking |
| `wepppy/weppcloud/routes/batch_runner/` | Flask blueprint — create, manage, validate, runstate |
| `wepppy/microservices/rq_engine/batch_routes.py` | RQ engine — run-batch endpoint (JWT-authenticated) |
| `wepppy/weppcloud/controllers_js/batch_runner.js` | Frontend controller — uploads, validation, polling |
| `tools/batch_prep_from_pourpoints.py` | CLI tool — delineate watershed polygons from pourpoints via WBT |

### Testing

```bash
pytest tests/nodb/test_batch_runner.py
pytest tests/weppcloud/test_batch_runner_endpoints.py
pytest tests/weppcloud/routes/test_batch_runner_snapshot.py
pytest tests/microservices/test_rq_engine_batch_routes.py
```

Test fixture: `tests/data/batch_runner/simple.geojson` (3 Point features).

### Error Handling

- Per-watershed failures are caught and logged to `runs/<runid>/run_metadata.json` with error type, message, and timing
- Failures emit `EXCEPTION_JSON` on the status channel but do not abort sibling jobs
- The finalizer job (`_final_batch_complete_rq`) runs after all watershed jobs complete (including failed ones) via RQ `depends_on`

### Known Limitations

- Progress reporting is coarse-grained (emoji per task stage); per-run failure details require inspecting `run_metadata.json` or the status stream
- `rmtree` directive defaults to off — re-running a batch without enabling it will skip stages that already have `RedisPrep` timestamps
- Template evaluation uses AST whitelisting; attribute access (e.g., `properties.name`) is not supported — use bracket notation (`properties["name"]`)

## Further Reading

- [routes/batch_runner/README.md](../weppcloud/routes/batch_runner/README.md) — Pure UI blueprint and request lifecycle
- [docker/prod-worker-deploy-guide.md](../../docker/prod-worker-deploy-guide.md) — Deploying `rq-worker-batch` to production
- [docker/README.md](../../docker/README.md) — Docker Compose guide including batch worker scaling
- [wepppy/rq/job-dependencies-catalog.md](../rq/job-dependencies-catalog.md) — RQ job dependency catalog and NFS considerations
- [docs/mini-work-packages/completed/20260124_batch_runner_run_batch_ux.md](../../docs/mini-work-packages/completed/20260124_batch_runner_run_batch_ux.md) — Run Batch UX work package
