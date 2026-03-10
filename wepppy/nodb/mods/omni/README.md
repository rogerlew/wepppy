# Omni Scenario Orchestration Module

> Compare post-fire treatment strategies and evaluate erosion mitigation effectiveness across multiple "what-if" scenarios—without manually rebuilding your entire WEPPcloud project for each analysis.

> **See also:** [AGENTS.md](../../../../AGENTS.md) for developer patterns and coding conventions.

## Overview

Omni helps land managers and hydrologists answer critical post-fire planning questions:

- **"What if we apply mulch at 1 ton/acre to high-severity burned areas?"**
- **"How does thinning to 65% canopy cover compare to prescribed fire?"**
- **"Which hillslopes contribute the most runoff, and what happens if we treat them?"**

Instead of manually creating separate WEPPcloud projects for each treatment scenario, Omni automates the process: it clones your base project, applies different burn severities or treatments, runs WEPP simulations, and compiles results into side-by-side comparisons.

## Developer Routing Notes

The contrast-build facade/router now keeps responsibilities split by concern:

- `wepppy/nodb/mods/omni/omni_build_router.py`: facade routing for build and dry-run entry points, lock-scoped persistence, and facade contract seams.
- `wepppy/nodb/mods/omni/omni_contrast_status_report_service.py`: contrast status payload assembly and selection-mode-specific report shaping.

### Key Capabilities

| Capability | Description |
|------------|-------------|
| **Scenario modeling** | Create multiple scenarios from a single project: uniform burn severities (low/moderate/high), custom burn severity maps, undisturbed baseline, thinning, mulching, and prescribed fire |
| **Automatic rebuilding** | Omni detects when inputs change and only reruns affected scenarios, saving computation time |
| **Contrast analysis** | Identify your highest-risk hillslopes (by runoff or soil loss) and evaluate targeted treatments |
| **Comparative reports** | Export scenario results to spreadsheet-friendly formats for downstream analysis |

### Who Uses Omni?

- **BAER Teams**: Rapidly evaluate mulching, seeding, or thinning effectiveness after wildfires
- **Forest Service Planners**: Compare pre-fire prescribed burns versus post-fire treatment options
- **Hydrologists**: Analyze how erosion and runoff vary across different burn severity distributions
- **Researchers**: Run sensitivity analyses for treatment timing, coverage, and spatial configuration

## Getting Started (Web Interface)

### Enabling the Omni Module

Omni is an optional module that must be added to your project before use:

1. Open your WEPPcloud project
2. Click the **Mods** dropdown menu in the control panel
3. Select **Omni Scenarios** from the list
4. The Omni Scenarios panel will appear in your project controls

### Creating Scenarios

1. Navigate to the **Omni Scenarios** panel
2. Select scenario types to add:
   - **Uniform Low/Moderate/High**: Apply the same burn severity to all hillslopes
   - **Undisturbed**: Baseline with no fire effects
   - **Thinning**: Pre-fire forest treatment (specify canopy cover and harvest method)
   - **Mulch**: Post-fire ground cover treatment (specify application rate and base scenario)
   - **Prescribed Fire**: Low-intensity burn for mature forests
3. Click **Run Scenarios** to execute all scenarios

### Understanding Scenario Results

After scenarios complete, view results in the **Scenarios Report** (accessible via the report link in the Omni panel or at `/report/omni_scenarios/`).

**Key metrics reported:**

| Metric | Description | Units |
|--------|-------------|-------|
| Soil Loss | Material detached from hillslope surface | kg/ha/year |
| Sediment Yield | Net sediment export after deposition | kg/ha/year |
| Runoff | Surface water depth | mm/year |
| Runoff Volume | Total water volume | m³/year |

Compare scenarios side-by-side to see how treatments affect erosion and runoff at both hillslope and watershed scales.

**Where to find output files:**

Omni stores all scenario data under the `_pups/omni/` directory in your project:

```
your_project/
└── _pups/
    └── omni/
        ├── scenarios/
        │   ├── uniform_low/          # Each scenario is a complete WEPPcloud project
        │   │   ├── wepp/output/      # WEPP simulation outputs
        │   │   ├── landuse/          # Modified landuse files
        │   │   └── soils/            # Modified soil files
        │   ├── uniform_high/
        │   ├── mulch/
        │   └── ...
        ├── contrasts/
        │   ├── 1/                    # Each contrast run directory
        │   ├── 2/
        │   └── ...
        ├── scenarios.out.parquet           # Aggregated scenario metrics
        ├── scenarios.hillslope_summaries.parquet  # Per-hillslope data
        └── contrasts.out.parquet           # Aggregated contrast metrics
```

**Aggregated output files:**

| File | Contents |
|------|----------|
| `scenarios.out.parquet` | Watershed-level metrics for all scenarios (outlet discharge, total soil loss) |
| `scenarios.hillslope_summaries.parquet` | Per-hillslope metrics for all scenarios |
| `contrasts.out.parquet` | Control vs. treatment comparisons with computed differences |

These Parquet files can be opened in Python (pandas), R, or tools like DuckDB for custom analysis. CSV exports are also available through the web reports.

### Running Contrast Analyses

Contrast analysis helps you evaluate targeted treatments on your highest-impact hillslopes:

1. Navigate to the **Omni Contrasts** panel
2. Select a **control scenario** (e.g., uniform high severity—your "worst case")
3. Select a **contrast scenario** (e.g., mulch treatment—your "with treatment" case)
4. Choose how to select hillslopes:
   - **Cumulative contribution**: Automatically select hillslopes that contribute the most runoff or soil loss (up to a threshold you specify)
   - **User-defined areas**: Upload a polygon file (GeoJSON) defining treatment zones
   - **User-defined hillslope groups**: Manually specify hillslope IDs
   - **Stream-order grouping**: Group hillslopes by drainage network structure (WhiteboxTools watersheds only)
5. Click **Run Contrasts** to simulate treating only the selected hillslopes

The contrast report shows how watershed-level erosion and runoff change when you treat specific areas versus leaving them untreated.

## Scenario Types

### Uniform Burn Severity Scenarios

Apply the same soil burn severity (SBS) class to all hillslopes:

| Scenario | Description |
|----------|-------------|
| `uniform_low` | All hillslopes at low severity (litter/duff mostly intact) |
| `uniform_moderate` | All hillslopes at moderate severity (litter consumed, possible water repellency) |
| `uniform_high` | All hillslopes at high severity (organic matter consumed, strong water repellency) |
| `undisturbed` | No fire effects—baseline vegetation and soils |

### Custom Burn Severity Map

Upload your own soil burn severity raster (GeoTIFF or IMG format) to capture spatial variability from BAER field mapping.

### Treatment Scenarios

#### Thinning

Pre-fire mechanical treatment that reduces canopy density and fuel loads. Configure:

- **Target canopy cover**: 40% (aggressive) or 65% (moderate)
- **Ground cover retention**: Depends on harvest equipment
  - 93% = Cable yarding (minimal ground disturbance)
  - 90% = Forwarder
  - 85% = Skidder
  - 75% = Ground-based (maximum disturbance)

*Example*: `thinning_65_90` means reducing canopy to 65% cover using a forwarder, retaining 90% ground cover.

#### Mulch

Post-fire straw or wood chip application to increase ground cover and reduce erosion. Options:

| Treatment | Application Rate | Ground Cover Effect |
|-----------|------------------|---------------------|
| mulch_15 | 0.5 tons/acre | Light—modest cover increase |
| mulch_30 | 1.0 tons/acre | Standard BAER recommendation |
| mulch_60 | 2.0 tons/acre | Heavy—maximum cover increase |

Mulch scenarios require a **base scenario** (typically a burn severity scenario) because mulch is applied *after* fire.

#### Prescribed Fire

Low-intensity burns in mature forests that reduce ladder fuels and understory without triggering high-severity soil heating. Omni applies prescribed fire management only to forest vegetation types.

Prescribed fire scenarios require an **undisturbed** clone context (no SBS map). In Omni, this is enforced by running prescribed fire from the `undisturbed` scenario when needed.

#### Scenario Dependency Behavior

- Mulch scenarios depend on a selected base scenario (`uniform_low`, `uniform_moderate`, `uniform_high`, or `sbs_map`) and run in a later pass after base scenarios are processed.
- Thinning and `prescribed_fire` run in an undisturbed context. If the project base is `sbs_map`, include/run an `undisturbed` Omni scenario so those treatments can clone from it.
- Scenario list order does not control execution order; Omni resolves dependencies internally.

## Contrast Analysis Modes

### Cumulative Contribution

Automatically selects hillslopes that contribute the most to your chosen metric (runoff or soil loss):

1. Hillslopes are ranked by their contribution to watershed totals
2. Selection continues until you reach your specified threshold (e.g., "hillslopes contributing 75% of total runoff")
3. Each selected hillslope becomes a separate contrast run

This mode answers: *"What happens if I treat the hillslopes responsible for most of my erosion problem?"*

### User-Defined Areas (GeoJSON)

Upload a polygon file defining treatment zones:

- Each polygon becomes a treatment area
- Hillslopes are included if at least 50% of their area falls within a polygon
- You can define multiple polygons with different names (via a feature property)
- Overlapping polygons are allowed

This mode answers: *"What happens if I treat these specific areas I've identified?"*

### User-Defined Hillslope Groups

Manually specify hillslope IDs in a text box:

- Enter one group per line
- Separate IDs with commas or spaces
- Each line becomes a contrast run

This mode answers: *"What happens if I treat these exact hillslopes?"*

### Stream-Order Grouping (WhiteboxTools only)

Groups hillslopes based on drainage network structure:

- Specify how many stream orders to prune (simplify the network)
- Hillslopes draining to the same channel segment become a group
- Useful for targeting treatments by subcatchment

This mode answers: *"What happens if I treat entire subcatchments?"*

## Understanding Results

### Scenario Reports

The scenarios report (`/report/omni_scenarios/`) shows WEPP outputs for each scenario:

- **Watershed totals**: Sediment yield and runoff at the outlet
- **Hillslope summaries**: Per-hillslope soil loss, runoff, and contributing area
- **Downloadable data**: Export to CSV or Parquet for analysis in Excel, R, or Python

### Contrast Reports

The contrasts report (`/report/omni_contrasts/`) compares control versus treated outcomes:

| Column | Description |
|--------|-------------|
| Contrast ID | Identifier for the contrast run |
| Control metrics | Erosion/runoff without treatment |
| Treated metrics | Erosion/runoff with treatment applied |
| Difference | Change from control (negative = reduction) |

### Interpreting Treatment Effectiveness

When comparing scenarios:

- **Soil loss reduction**: Lower values after treatment indicate effective erosion control
- **Runoff reduction**: Lower values suggest improved infiltration or water retention
- **Cost-benefit**: Compare treatment costs (from BAER catalogs) against predicted erosion reduction

*Example interpretation*: If uniform high severity predicts 15,000 kg/ha/year soil loss and mulch treatment reduces it to 8,000 kg/ha/year, you've achieved a 47% reduction in hillslope erosion.

## Background: Wildfire Erosion Science

### Why Post-Fire Erosion Matters

Wildfires dramatically increase erosion risk by:
- Consuming protective ground cover (litter, duff, vegetation)
- Creating water-repellent soil layers that prevent infiltration
- Altering soil structure and reducing aggregate stability

First-year post-fire erosion rates can be 10–100× higher than pre-fire conditions, threatening water quality, infrastructure, and aquatic habitat.

### Soil Burn Severity (SBS) Classification

BAER teams classify burn severity using field indicators:

| Class | Field Indicators | Erosion Risk |
|-------|------------------|--------------|
| **Unburned/Low** | Litter and duff mostly intact, minimal water repellency | Low |
| **Moderate** | Litter consumed, some charred duff, water-repellent layer possible | Moderate |
| **High** | All organic matter consumed, altered soil structure, strong water repellency | High |

### Treatment Effectiveness

Post-fire treatments reduce erosion by restoring ground cover:

- **Mulching**: Straw or wood chips protect soil from raindrop impact and slow overland flow. ERMiT guidelines recommend 1 ton/acre (60% cover) as standard.
- **Seeding**: Establishes vegetation for long-term cover (slower than mulch but self-sustaining)
- **Contour-felled logs**: Intercept runoff and trap sediment on steep slopes

Pre-fire treatments reduce fire severity:
- **Thinning**: Removes ladder fuels, reduces crown fire risk
- **Prescribed fire**: Consumes surface fuels under controlled conditions

## Troubleshooting

### Scenarios Won't Run

**Check**: Does your base project have valid climate, watershed, and soils data? Omni clones your project, so missing inputs will cause failures.

**Check**: Look at the scenario status panel for error messages. Common issues include missing soil files or invalid management assignments.

### Contrast Results Missing Hillslopes

**Check**: Your cumulative threshold may be too low. Try increasing the threshold percentage or hillslope limit.

**Check**: For user-defined areas, ensure your polygons overlap with hillslopes in your watershed.

### Results Don't Change Between Scenarios

**Check**: Treatments only apply to appropriate vegetation types. Mulch only affects fire-disturbed areas; thinning only affects forests.

**Check**: Your scenarios may have identical inputs. Review scenario parameters to ensure they differ.

---

## Developer Notes

*This section contains technical implementation details for developers extending or maintaining the Omni module.*

### Architecture

Omni follows the NoDb singleton pattern. The controller persists state in `omni.nodb` and uses Redis DB 13 for 72-hour caching. Contrast mappings are stored as ASCII sidecar TSVs under `omni/contrasts/` to avoid bloating the NoDb payload. All scenario workspaces live under `<parent_wd>/_pups/omni/scenarios/<scenario_name>` and are themselves valid WEPPcloud projects (symlinked climate/watershed directories; copied disturbed/landuse/soils).

### Components

```
wepppy/nodb/mods/omni/
├── omni.py              # Core Omni orchestration facade
├── omni_state_contrast_mixin.py  # Extracted state/contrast facade methods
├── omni.pyi             # Type stubs for IDE/mypy support
├── __init__.py          # Public exports (Omni, OmniScenario, OmniNoDbLockedException)
└── README.md            # This document

wepppy/rq/
└── omni_rq.py           # RQ task orchestration (run_omni_scenarios_rq, run_omni_scenario_rq)

wepppy/weppcloud/routes/nodb_api/
└── omni_bp.py           # Flask routes for scenario CRUD and reporting

wepppy/weppcloud/controllers_js/
├── omni.js              # Frontend controller (scenario builder + contrast runner UI)
└── __tests__/omni.test.js  # Jest unit tests

wepppy/weppcloud/templates/controls/
├── omni_scenarios_pure.htm   # Scenario builder UI (Pure CSS)
└── omni_contrasts_pure.htm   # Contrast configuration UI
```

### Scenario Execution Flow

1. **Definition**: User selects scenarios via UI or programmatically (`omni.parse_scenarios([...])`)
2. **Cloning**: `_omni_clone()` creates `_pups/omni/scenarios/<scenario_name>`, symlinks shared directory inputs, copies mutable state
3. **Treatment Application**: For thinning/mulching/prescribed fire, `Treatments.getInstance(scenario_wd)` modifies landuse/soils
4. **WEPP Execution**: Scenario workspace calls `Wepp.prep_hillslopes()`, `Wepp.run_hillslopes()`, `Wepp.run_watershed()`
5. **Reporting**: `Omni.scenarios_report()` concatenates per-scenario output files into a unified DataFrame
6. **Dependency Updates**: SHA1 hashes of dependency outputs are stored; subsequent runs skip unchanged scenarios

### Contrast Execution Flow

1. **Definition**: User selects control/contrast scenarios, objective parameter, and selection mode
2. **Hillslope Selection**: `build_contrasts()` reads control scenario outputs, sorts hillslopes by objective parameter, selects based on mode
3. **Selection Sidecar**: Each contrast mapping is written to `omni/contrasts/contrast_<id>.tsv`
4. **Clone Assembly**: Creates contrast workspace, merges hillslope outputs from control + contrast scenarios
5. **WEPP Execution**: Runs watershed simulation with mixed hillslope inputs
6. **Reporting**: `contrasts_report()` computes deltas between control and contrast metrics

### Contrast Selection Mode Details

#### Cumulative Objective Parameter

- Sort control-scenario hillslopes by objective parameter
- Select until cumulative fraction threshold reached
- Maximum 100 hillslopes (backend enforced)

#### User-Defined Areas (GeoJSON)

- Users upload GeoJSON polygons with feature property for naming
- Hillslopes included if polygon covers ≥50% of area
- Requires `contrast_pairs` list for N pairs × M polygons expansion
- Contrast IDs stable by signature `control|contrast|area_label`

#### User-Defined Hillslope Groups

- Users paste Topaz IDs in textbox (one group per line)
- Parsing tolerates commas, whitespace, semicolons
- IDs validated against watershed translator
- Requires `contrast_pairs` for N pairs × M groups expansion

#### Stream-Order Pruning (WhiteboxTools Only)

- Uses `_prune_stream_order()` to simplify channel network
- Runs `hillslopes_topaz` on pruned network for subcatchment grouping
- Group IDs scaled (`* 10`) after intersection
- Intermediate files cached in `dem/wbt/`

### Dependency Tracking

Omni uses dependency metadata to detect when scenarios need rebuilding:

- **Scenario signature**: `json.dumps(scenario_def, sort_keys=True)` (stable serialized scenario definition)
- **Dependency target**: `mulch` depends on its declared `base_scenario`; all other scenarios depend on the Omni base scenario
- **Dependency path**: `wepp/output/interchange/loss_pw0.out.parquet` for the dependency target
- **Dependency hash**: SHA1 of that dependency path
- **Match logic**:
  - RQ concurrency path: skip when signature and dependency hash match prior `scenario_dependency_tree`
  - In-process path: same hash/signature check plus year-set parity (`loss_pw0.all_years.class_data.parquet`) with the base scenario

### Python API Usage

```python
from wepppy.nodb.mods.omni import Omni, OmniScenario

# Initialize Omni controller
wd = "/geodata/weppcloud_runs/user/project_name/disturbed9002"
omni = Omni.getInstance(wd)

# Define scenarios
omni.parse_scenarios([
    (OmniScenario.UniformHigh, {"type": "uniform_high"}),
    (OmniScenario.Mulch, {
        "type": "mulch",
        "ground_cover_increase": "30%",
        "base_scenario": "uniform_high"
    })
])

# Run scenarios
omni.run_omni_scenarios()

# Generate report
df_scenarios = omni.scenarios_report()
```

### Contrast API Usage

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

# Generate report
df_contrasts = omni.contrasts_report()
```

### NoDb Persistence (`omni.nodb`)

| Attribute | Type | Description |
|-----------|------|-------------|
| `_scenarios` | `List[Dict]` | Scenario definitions (type, parameters) |
| `_contrast_names` | `List[Optional[str]]` | Contrast identifiers |
| `_control_scenario` | `OmniScenario` | Control scenario for contrast analysis |
| `_contrast_scenario` | `OmniScenario` | Treatment scenario for contrast analysis |
| `_contrast_object_param` | `str` | Objective parameter (e.g., `Runoff_mm`) |
| `_scenario_dependency_tree` | `Dict[str, Dict]` | SHA1 hashes for change detection |
| `_scenario_run_state` | `List[Dict]` | Execution audit log |

### RQ Task Orchestration

- `run_omni_scenarios_rq(runid)`: Dispatches scenario jobs, compiles summaries
- `run_omni_scenario_rq(runid, scenario)`: Executes single scenario
- Runtime-path maintenance locks protect mutable `landuse`/`soils` roots with path-scoped identity (`effective_root_path_compat`) and a 300-second wait window
- Dependency/contrast tree persistence retries NoDb lock acquisition (5 attempts, 1-second backoff)
- Process pool fallback for CPU-heavy operations

### Testing

```bash
# Unit tests
wctl run-pytest tests/nodb/mods/test_omni.py

# Integration tests
wctl run-pytest tests/weppcloud/routes/test_rq_api_omni.py

# Frontend tests
wctl run-npm test -- omni.test.js
```

### Extending Scenario Types

To add a new scenario type (e.g., seeding):

1. Add enum value to `OmniScenario` in `omni.py`
2. Update `OmniScenario.parse()` and `__str__()`
3. Add case to `run_omni_scenario()` with treatment logic
4. Update `SCENARIO_CATALOG` in `omni.js`
5. Add entry to `_scenario_name_from_scenario_definition()`
6. Update this README

### Disk and Memory Considerations

- Each scenario duplicates ~10–50 MB of mutable state
- WEPP outputs add ~5–200 MB per scenario
- 8 scenarios on a 1000-hillslope watershed: 2–5 GB total
- Redis caches NoDb payloads with 72-hour TTL

### Logging

- Per-scenario: `<scenario_wd>/_logs/wepp.log`, `landuse.log`
- Parent: `<parent_wd>/_logs/omni.log`
- Set `WEPPPY_LOG_LEVEL=DEBUG` for detailed diagnostics

---

## Further Reading

### Related Modules

- [Treatments Module](../treatments/README.md) — Mulching, thinning, prescribed fire implementation
- [Disturbed Module](../disturbed/README.md) — Burn severity mapping
- [NoDb README](../../README.md) — Core controller architecture

### External References

- [BAER Treatment Catalog](https://burnedareas.forestry.oregonstate.edu/treatments) — Field guides for treatment implementation
- [ERMiT User Manual (RMRS-GTR-188)](https://www.fs.usda.gov/rm/pubs_series/rmrs/gtr/rmrs_gtr188.pdf) — Treatment effectiveness research
- [WEPP Model Documentation](https://www.ars.usda.gov/pacific-west-area/moscow-id/forest-and-range-ecosystem-science/docs/wepp/) — Erosion model theory

---

## Credits

**Primary Contributors**: Roger Lew (University of Idaho), William Elliot (USDA Forest Service), Pete Robichaud (USDA Forest Service)

**Funding**: USDA Forest Service Rocky Mountain Research Station, National Fire Plan

**License**: BSD-3 Clause (see `license.txt` in repository root)

---

**Last Updated**: 2026-01-30
**Maintainer**: AI Coding Agents (per AGENTS.md authorship policy)
