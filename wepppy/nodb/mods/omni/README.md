# Omni Scenario Orchestration Module

> Manages scenario cloning, treatment application, and contrast analyzes for WEPPcloud wildfire response modeling. Omni enables land managers and hydrologists to evaluate multiple post-fire mitigation strategies (mulching, thinning, prescribed fire) and compare their erosion, runoff, and sediment transport outcomes without manually rerunning the entire WEPP stack.

> **See also:** [AGENTS.md](../../../../AGENTS.md) for NoDb controller patterns, scenario management workflows, and RQ orchestration guidance.

## Overview

The Omni mod orchestrates erosion prediction scenarios by cloning a parent WEPPcloud project, applying burn severities or treatments, rebuilding soil/landuse inputs, executing WEPP hillslope and watershed runs, and aggregating loss metrics into DuckDB-backed parquet outputs. It answers questions like:

- **What if we apply mulch at 1 ton/acre to high-severity burned areas?**
- **How does thinning to 65% canopy cover compare to prescribed fire?**
- **Which hillslopes contribute the most runoff under uniform moderate severity, and what happens if we treat them?**

Omni snapshots the working directory into `_pups/omni/scenarios/<scenario_name>`, symlinks shared inputs (climate, watershed topology), copies mutable state (disturbed, landuse, soils), applies treatments via the `Treatments` mod, reruns WEPP, and stores outputs in per-scenario directories. Contrast analyzes identify high-risk hillslopes from one scenario (the "control") and substitute treated hillslopes from another (the "contrast"), enabling targeted mitigation evaluation.

### Key Capabilities

- **Scenario Types**: Uniform burn severities (low/moderate/high), custom SBS maps, undisturbed baseline, thinning (canopy/ground cover reduction), mulching (ground cover increase), prescribed fire
- **Dependency Tracking**: SHA1-based hashing detects when upstream scenarios change and skips redundant rebuilds
- **Contrast Analysis**: Select hillslopes by cumulative objective parameter (runoff, soil loss, phosphorus) up to a threshold fraction; contrast runs blend control and treatment outputs
- **Concurrency Options**: Run scenarios serially (`run_omni_scenarios()`) or dispatch to RQ workers (`run_omni_scenarios_rq()`) with lock retry and process pool fallback for CPU-heavy soil preparation
- **Parquet Reporting**: Aggregates scenario outputs into `scenarios.out.parquet`, `scenarios.hillslope_summaries.parquet`, and `contrasts.out.parquet` for downstream analytics (D-Tale, dashboards, R scripts)

### Who Uses Omni?

- **BAER Teams**: Rapid evaluation of mulching/seeding/thinning effectiveness post-wildfire
- **Forest Service Planners**: Pre-fire prescribed burn vs. post-fire treatment tradeoffs
- **Hydrologists**: Calibration and uncertainty quantification across burn severity distributions
- **Researchers**: Sensitivity analyzes for treatment timing, coverage, and spatial configuration

## Architecture

Omni follows the NoDb singleton pattern. The controller persists state in `omni.nodb` (scenarios, contrasts, dependency trees, run states) and uses Redis DB 13 for 72-hour caching. All scenario workspaces live under `<parent_wd>/_pups/omni/scenarios/<scenario_name>` and are themselves valid WEPPcloud projects (symlinked climate/watershed, copied disturbed/landuse/soils).

### Components

```
wepppy/nodb/mods/omni/
├── omni.py              # Core Omni controller and scenario/contrast logic
├── omni.pyi             # Type stubs for IDE/mypy support
├── __init__.py          # Public exports (Omni, OmniScenario, OmniNoDbLockedException)
└── old_readme.md        # Historical notes (superseded by this document)

wepppy/rq/
└── omni_rq.py           # RQ task orchestration (run_omni_scenarios_rq, run_omni_scenario_rq)

wepppy/weppcloud/routes/nodb_api/
└── omni_bp.py           # Flask routes for scenario CRUD and reporting

wepppy/weppcloud/controllers_js/
├── omni.js              # Frontend controller (scenario builder, contrast definitions)
└── __tests__/omni.test.js  # Jest unit tests

wepppy/weppcloud/templates/controls/
├── omni_scenarios_pure.htm   # Scenario builder UI (Pure CSS)
└── omni_contrasts_pure.htm   # Contrast configuration UI
```

### Scenario Execution Flow

1. **Definition**: User selects scenarios via UI or programmatically (`omni.parse_scenarios([...])`)
2. **Cloning**: `_omni_clone()` creates `_pups/omni/scenarios/<scenario_name>`, symlinks shared inputs, copies mutable state
3. **Treatment Application**: For thinning/mulching/prescribed fire, `Treatments.getInstance(scenario_wd)` modifies landuse/soils
4. **WEPP Execution**: Scenario workspace calls `Wepp.prep_hillslopes()`, `Wepp.run_hillslopes()`, `Wepp.run_watershed()` with symlinked climate/slope inputs
5. **Reporting**: `Omni.scenarios_report()` concatenates per-scenario `loss_pw0.out.parquet` files into a unified DataFrame
6. **Dependency Updates**: SHA1 hashes of `loss_pw0.txt` are stored in `scenario_dependency_tree`; subsequent runs skip unchanged scenarios

### Contrast Execution Flow

1. **Definition**: User selects control/contrast scenarios, objective parameter (runoff, soil loss), and cumulative threshold
2. **Hillslope Selection**: `build_contrasts()` queries the control scenario's GeoPackage, sorts hillslopes by objective parameter, and selects top contributors up to threshold
3. **Clone Assembly**: For each selected hillslope, `_run_contrast()` creates a contrast clone that symlinks most hillslopes from the control but substitutes the treated hillslope from the contrast scenario
4. **WEPP Execution**: Contrast clone runs watershed model with hybrid inputs
5. **Reporting**: `contrasts_report()` joins control and contrast loss metrics, computes deltas, and persists `contrasts.out.parquet`

### Dependency Tree Persistence

Omni maintains two bookkeeping structures in `omni.nodb`:

- **`scenario_dependency_tree`**: Maps scenario name → `{ dependency_target, dependency_path, dependency_sha1, signature, timestamp }`. Used to skip reruns when upstream data unchanged.
- **`scenario_run_state`**: List of `{ scenario, status, reason, dependency_target, dependency_path, dependency_sha1, timestamp }` entries. Audit trail for debugging and downstream tools.

Contrast execution follows the same hashing approach via `contrast_dependency_tree`.

## Scenario Run Slugs and Routing

- **Filesystem layout:** `_pups/omni/scenarios/<name>` under the parent run root.
- **Run slug for web/UI:** `omni;;<parent_runid>;;<scenario_name>` (for example `omni;;walk-in-obsessive-compulsive;;undisturbed`).
- **Canonical URLs:** `/weppcloud/runs/omni;;<parent_runid>;;<scenario>/<config>/...` — no `?pup=` query parameters are used. All controllers and templates should rely on `url_for_run` (JS) or Flask `url_for` with the provided `runid/config` to keep grouped slugs intact.
- **Browse/Reports:** The header Browse/README/FORK/ARCHIVE links and GL dashboard now honor grouped slugs; avoid hardcoding base runids when deep-linking Omni scenarios.
- **Legacy pup query:** Disabled for Omni; grouped slugs replace `?pup=...` access.

## Scenario Types and Parameters

### OmniScenario Enum

| Value | String Representation | Description |
|-------|----------------------|-------------|
| `UniformLow` | `uniform_low` | All hillslopes burned at low soil burn severity |
| `UniformModerate` | `uniform_moderate` | All hillslopes burned at moderate soil burn severity |
| `UniformHigh` | `uniform_high` | All hillslopes burned at high soil burn severity |
| `SBSmap` | `sbs_map` | Custom soil burn severity raster (GeoTIFF/IMG) |
| `Undisturbed` | `undisturbed` | No burn; baseline vegetation/soils |
| `PrescribedFire` | `prescribed_fire` | Low-intensity fire applied to mature forests |
| `Thinning` | `thinning` | Canopy/ground cover reduction pre-fire |
| `Mulch` | `mulch` | Post-fire straw/wood mulch application |

### Scenario Parameters

#### Thinning

```python
{
    'type': 'thinning',
    'canopy_cover': '65%',       # Reduce canopy to 40% or 65%
    'ground_cover': '85%'        # Post-harvest ground cover (75%, 85%, 90%, 93%)
}
```

#### Mulching

```python
{
    'type': 'mulch',
    'ground_cover_increase': '30%',  # 15% (½ ton/acre), 30% (1 ton/acre), 60% (2 tons/acre)
    'base_scenario': 'uniform_high'  # Scenario to which mulch is applied
}
```

#### SBS Map

```python
{
    'type': 'sbs_map',
    'sbs_file_path': '/path/to/uploaded.tif'  # Must align with project DEM
}
```

## Usage

### Defining and Running Scenarios

```python
from wepppy.nodb.mods.omni import Omni, OmniScenario

# Initialize Omni controller
wd = "/geodata/weppcloud_runs/user/project_name/disturbed9002"
omni = Omni.getInstance(wd)

# Define scenarios
omni.parse_scenarios([
    (OmniScenario.UniformHigh, {"type": "uniform_high"}),
    (OmniScenario.UniformModerate, {"type": "uniform_moderate"}),
    (OmniScenario.Thinning, {
        "type": "thinning",
        "canopy_cover": "65%",
        "ground_cover": "85%"
    }),
    (OmniScenario.Mulch, {
        "type": "mulch",
        "ground_cover_increase": "30%",
        "base_scenario": "uniform_high"
    })
])

# Run all scenarios serially (development/testing)
omni.run_omni_scenarios()

# Or dispatch to RQ workers for concurrency
from wepppy.rq.omni_rq import run_omni_scenarios_rq
job = run_omni_scenarios_rq(runid="user-project-disturbed9002")
```

### Generating Scenario Reports

```python
import pandas as pd

# Aggregate scenario outputs
df_scenarios = omni.scenarios_report()
print(df_scenarios[['scenario', 'key', 'v', 'units']].head(20))

# Access parquet directly
parquet_path = os.path.join(omni.wd, '_pups/omni/scenarios.out.parquet')
df = pd.read_parquet(parquet_path)
```

### Building and Running Contrasts

```python
# Define contrast analysis
omni.build_contrasts(
    control_scenario_def={"type": "uniform_high"},
    contrast_scenario_def={"type": "mulch", "ground_cover_increase": "30%", "base_scenario": "uniform_high"},
    obj_param="Runoff_mm",
    contrast_cumulative_obj_param_threshold_fraction=0.75,
    contrast_hillslope_limit=10
)

# Execute contrasts
omni.run_omni_contrasts()

# Generate contrast report
df_contrasts = omni.contrasts_report()
print(df_contrasts[['contrast', 'key', 'control_v', 'v', 'control-contrast_v']].head())
```

### Checking Dependency State

```python
# Inspect which scenarios were skipped vs. executed
print(omni.scenario_run_state)
# [{'scenario': 'uniform_high', 'status': 'executed', 'reason': 'dependency_changed', ...}, ...]

# View dependency tree
print(omni.scenario_dependency_tree)
# {'uniform_high': {'dependency_target': 'undisturbed', 'dependency_sha1': 'abc123...', ...}, ...}
```

## Configuration

### Omni Persistence (`omni.nodb`)

| Attribute | Type | Description |
|-----------|------|-------------|
| `_scenarios` | `List[Dict[str, Any]]` | Scenario definitions (type, parameters) |
| `_contrasts` | `List[Dict[int \| str, str]]` | Per-hillslope path mappings for contrasts |
| `_contrast_names` | `List[str]` | Human-readable contrast identifiers |
| `_control_scenario` | `OmniScenario` | Control scenario for contrast analysis |
| `_contrast_scenario` | `OmniScenario` | Treatment scenario for contrast analysis |
| `_contrast_object_param` | `str` | Objective parameter for hillslope selection (e.g., `Runoff_mm`) |
| `_contrast_cumulative_obj_param_threshold_fraction` | `float` | Stop selecting hillslopes after reaching this cumulative fraction (0–1) |
| `_scenario_dependency_tree` | `Dict[str, Dict]` | SHA1 hashes and timestamps for change detection |
| `_scenario_run_state` | `List[Dict]` | Audit log of scenario execution (status, reason, timestamp) |
| `_use_rq_job_pool_concurrency` | `bool` | Enable multi-scenario concurrency in RQ pool (default `True`) |

### Environment Variables (RQ Execution)

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis server for RQ job queue |
| `REDIS_DB_RQ` | `9` | Redis database for job metadata |
| `OMNI_MAX_WORKERS` | `cpu_count()` | Max workers per scenario task (soil prep, hillslope runs) |

## Developer Notes

### Cloning Internals

`_omni_clone()` creates scenario workspaces under `_pups/omni/scenarios/<scenario_name>`:

1. Symlinks shared inputs: `climate/`, `dem/`, `watershed/`, `*.nodb` (climate, watershed, dem)
2. Copies mutable state: `disturbed/`, `landuse/`, `soils/`, `rap/`
3. Copies and rewrites `.nodb` files to update `wd` and `_parent_wd` attributes
4. Removes `READONLY` marker if present (production runs stamp this file)
5. Calls `_clear_nodb_cache_and_locks()` to flush Redis cache and locks

`_omni_clone_sibling()` overlays another scenario's disturbed/landuse/soils when dependencies require it (e.g., mulching built on `uniform_low`).

**Gotcha**: If you skip the cache-clearing step or forget to rewrite `.nodb` metadata, NoDb singletons continue pointing at the parent run and all subsequent path lookups fail.

### Dependency Tracking

Omni uses SHA1 hashing of `loss_pw0.txt` to detect when scenarios need rebuilding:

- **Scenario signature**: `json.dumps(scenario_def, sort_keys=True)` identifies parameter changes
- **Dependency hash**: SHA1 of the base scenario's `loss_pw0.txt` detects upstream reruns
- **Match logic**: If both signature and dependency hash unchanged, skip rebuild

Contrast tracking works the same way but hashes both control and contrast scenarios' loss files.

### Concurrency and Locking

- **Serial execution**: `run_omni_scenarios()` calls `run_omni_scenario()` in a loop, updating `scenario_dependency_tree` after each success. Safe for development but slow for large watersheds.
- **RQ execution**: `run_omni_scenarios_rq()` dispatches each scenario as a separate job. Each job calls `_locked_with_retry()` to acquire the Omni lock (30-second timeout). If soil prep crashes the spawn pool, retry with fork; if that fails, fall back to sequential execution.
- **Stale state**: Always reload `Omni.getInstance(wd)` inside `locked()` before writing dependency trees or run states, or the last writer clobbers previous updates.

### Testing

- **Unit tests**: `tests/nodb/mods/test_omni.py` covers scenario parsing, dependency hashing, cloning, and report generation
- **Integration tests**: `tests/weppcloud/routes/test_rq_api_omni.py` exercises RQ task orchestration and job lifecycle
- **Frontend tests**: `wepppy/weppcloud/controllers_js/__tests__/omni.test.js` validates scenario builder UI and event emission

Run integration tests inside the Docker dev container:

```bash
wctl run-pytest tests/nodb/mods/test_omni.py
wctl run-pytest tests/weppcloud/routes/test_rq_api_omni.py
```

### Type Hints

`omni.pyi` provides comprehensive type annotations:

```python
from typing import Dict, List, Optional, Tuple, Any

class Omni(NoDbBase):
    def parse_scenarios(self, parsed_inputs: Iterable[Tuple[OmniScenario, ScenarioDef]]) -> None: ...
    def run_omni_scenario(self, scenario_def: ScenarioDef) -> Tuple[str, str]: ...
    def scenarios_report(self) -> pd.DataFrame: ...
    def build_contrasts(
        self,
        control_scenario_def: ScenarioDef,
        contrast_scenario_def: ScenarioDef,
        obj_param: str = 'Runoff_mm',
        ...
    ) -> None: ...
```

Run `mypy wepppy/nodb/mods/omni/` to validate.

### Extending Scenario Types

To add a new scenario (e.g., seeding):

1. Add enum value to `OmniScenario` in `omni.py`
2. Update `OmniScenario.parse()` and `OmniScenario.__str__()`
3. Add case to `run_omni_scenario()` with treatment logic
4. Update `SCENARIO_CATALOG` in `omni.js` with UI controls
5. Add entry to `_scenario_name_from_scenario_definition()`
6. Update `old_readme.md` → this README with new scenario docs

## Integration Points

### NoDb Controllers

- **Depends on**: `Ron` (mod registration), `Watershed` (translator, topaz IDs), `Climate` (symlinked inputs), `Landuse` (domlc_d, managements), `Soils` (build), `Wepp` (prep, run, report_loss), `Disturbed` (sbs validation, uniform sbs builder)
- **Used by**: `Treatments` (applies mulch/thinning/prescribed fire), `RangelandCover` (future seeding scenarios)

### RQ Tasks

- `run_omni_scenarios_rq(runid)`: Dispatches `run_omni_scenario_rq` jobs for each scenario, then calls `_finalize_omni_scenarios_rq` to compile reports
- `run_omni_scenario_rq(runid, scenario, ...)`: Executes single scenario, updates dependency tree, publishes `OMNI_SCENARIO_RUN_TASK_COMPLETED` event
- `_finalize_omni_scenarios_rq(runid)`: Calls `compile_hillslope_summaries()` and `scenarios_report()`, publishes `END_BROADCAST` to disconnect WebSocket streams

### Flask Routes

- `GET /api/omni/get_scenarios`: Returns `Omni.scenarios` as JSON
- `GET /api/omni/get_scenario_run_state`: Returns `scenario_dependency_tree` and `scenario_run_state`
- `GET /tasks/omni_migration`: Adds `omni` and `treatments` to `Ron._mods`, bootstraps controllers
- `GET /report/omni_scenarios/`: Renders scenario summary table using `scenarios_report()` DataFrame

### Frontend Controllers

- `Omni.getInstance()`: Singleton controller managing scenario builder UI
- Events: `omni:scenarios:loaded`, `omni:scenario:added`, `omni:scenario:removed`, `omni:scenario:updated`, `omni:run:started`, `omni:run:completed`, `omni:run:error`
- Methods: `run_omni_scenarios()`, `load_scenarios_from_backend()`, `report_scenarios()`, `serializeScenarios()`

## Domain Context: Wildfire Response Modeling

### Post-Fire Treatment Effectiveness

Omni addresses BAER (Burned Area Emergency Response) planning questions:

1. **Mulching**: Straw/wood chips increase ground cover, reducing raindrop impact and overland flow velocity. ERMiT guidelines recommend 1 ton/acre (60% cover) as standard; Omni applies percentage increases to existing post-fire covers.
2. **Thinning**: Pre-fire mechanical treatment reduces canopy density (40–65%) and surface fuel loads. Ground cover post-harvest depends on equipment (cable 93%, forward 90%, skidder 85%).
3. **Prescribed Fire**: Low-intensity burns in mature forests reduce ladder fuels and understory without triggering high-severity soil heating. Omni applies prescribed fire only to forest managements (excludes young stands).

### Soil Burn Severity (SBS) Classification

BAER teams map SBS using field indicators (ash color, soil structure, water repellency):

- **Unburned/Low**: Litter/duff intact, minimal hydrophobicity
- **Moderate**: Litter consumed, some duff charred, water-repellent layer possible
- **High**: All organic matter consumed, soil structure altered, strong hydrophobicity

Omni's uniform scenarios set all hillslopes to one SBS class; SBS map scenarios respect spatial variability captured by BAER mapping.

### Erosion and Runoff Metrics

WEPP outputs aggregated by Omni:

- **Soil Loss (kg/ha)**: Detachment from hillslope surface
- **Sediment Yield (kg/ha)**: Net export after deposition
- **Runoff (mm)**: Surface water depth over hillslope area
- **Runoff Volume (m³)**: `Runoff (mm) × Hillslope Area (ha) × 10`
- **NTU (g/L)**: Turbidity proxy, `Sediment Yield (t) × 1000 / (Runoff (m³) + Baseflow (m³))`

Land managers use these to prioritize treatment locations (highest sediment contributors) and estimate post-fire water quality impacts.

## Troubleshooting

### Scenario Clone Failures

**Symptom**: `FileNotFoundError: 'climate' not found` or `NoDb controller points to wrong wd`

**Cause**: Symlinks or `.nodb` metadata rewriting failed during `_omni_clone()`

**Fix**: Verify parent project has valid `climate/`, `watershed/`, `dem/` directories. Check `omni.log` for permission errors. If Redis cache stale, restart scenario run—dependency hashing should detect changes.

### Contrast Runs Missing Hillslopes

**Symptom**: Contrast output excludes some hillslopes

**Cause**: `build_contrasts()` filters by objective parameter threshold and optional constraints (slope, burn severity, topaz IDs)

**Fix**: Increase `contrast_cumulative_obj_param_threshold_fraction` or raise `contrast_hillslope_limit`. Check `_pups/omni/contrasts/build_report.ndjson` for selection audit trail.

### Dependency Tree Not Updating

**Symptom**: Scenarios always rerun even when inputs unchanged

**Cause**: SHA1 hashing relies on `loss_pw0.txt` presence. If WEPP run fails, hash is `None` and never matches.

**Fix**: Inspect `scenario_dependency_tree` for `None` hashes. Rerun upstream scenario to generate valid output. If using RQ, ensure lock acquisition succeeded (check `scenario_run_state` for timeout errors).

### RQ Job Pool Crashes

**Symptom**: Soil preparation jobs fail with `BrokenProcessPool` or hang indefinitely

**Cause**: Spawn context incompatible with Rosetta-translated binaries or large memory mappings

**Fix**: `omni_rq.py` already retries with fork context. If still fails, set `OMNI_MAX_WORKERS=1` to disable process pool. Check `wepp.log` in scenario workspace for Fortran segfaults.

## Operational Notes

### Disk Usage

Each scenario duplicates `disturbed/`, `landuse/`, `soils/` (~10–50 MB depending on watershed size) and generates `wepp/output/` (~5–200 MB). A project with 8 scenarios and 1000 hillslopes can consume 2–5 GB. Monitor `/geodata/weppcloud_runs` quotas and purge `_pups/omni` directories for abandoned runs.

### Redis Cache Behavior

Omni payloads cached in DB 13 with 72-hour TTL. If run inactive for 3 days, next access triggers disk deserialization. Heavy scenario runs (100+ scenarios) can exhaust Redis memory; consider eviction policies or dedicated instance for large projects.

### Logging

- **Per-scenario logs**: `<scenario_wd>/_logs/<controller>.log` (e.g., `wepp.log`, `landuse.log`)
- **Parent logs**: `<parent_wd>/_logs/omni.log` for clone operations, dependency updates
- **RQ worker logs**: Check RQ dashboard or `rq-worker.log` for job failures

Set `WEPPPY_LOG_LEVEL=DEBUG` in `docker/.env` to capture detailed cloning/hashing diagnostics.

## Further Reading

### Core Documentation

- [AGENTS.md](../../../../AGENTS.md) — NoDb patterns, RQ orchestration, testing conventions
- [Treatments Module](../treatments/README.md) — Mulching, thinning, prescribed fire implementation details
- [Disturbed Module](../disturbed/README.md) — Burn severity mapping and validation
- [WEPP Reports](../../../wepp/reports/README.md) — Loss metric aggregation and parquet schemas

### External References

- [BAER Treatment Catalog](https://burnedareas.forestry.oregonstate.edu/treatments) — Field guides for mulching rates, seeding mixes, contour-felled logs
- [ERMiT User Manual](https://www.fs.usda.gov/rm/pubs_series/rmrs/gtr/rmrs_gtr188.pdf) — Empirical basis for treatment effectiveness assumptions
- [WEPP Model Documentation](https://www.ars.usda.gov/pacific-west-area/moscow-id/forest-and-range-ecosystem-science/docs/wepp/) — Hillslope/watershed model theory

### Development Notes

- `docs/dev-notes/omni_development.md` — Historical design decisions, mulching cover model revisions
- `docs/dev-notes/redis_dev_notes.md` — Redis database allocation and pub/sub streaming
- `docs/work-packages/omni_contrast_refactor.md` — Planned Pure UI migration for contrast builder (Q2 2025)

## Credits

**Primary Contributors**: Roger Lew (University of Idaho), William Elliot (USDA Forest Service), Pete Robichaud (USDA Forest Service)

**Funding**: USDA Forest Service Rocky Mountain Research Station, National Fire Plan

**License**: BSD-3 Clause (see `license.txt` in repository root)

---

**Last Updated**: 2025-10-24  
**Maintainer**: AI Coding Agents (per AGENTS.md authorship policy)
