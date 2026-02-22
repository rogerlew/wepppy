# PATH Cost-Effective (PathCE) NoDb Module

> Select the most cost-effective set of post-fire hillslope treatments (currently mulch presets) that meets user-defined sediment-yield and discharge targets, using Omni scenario outputs as the data source.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb locking, persistence, and debugging conventions.

## Overview

PATH Cost-Effective (“PathCE”) is a NoDb-backed optimization workflow used in WEPPcloud to rank candidate hillslope treatments by cost while enforcing sediment reduction targets.

At a high level:

- Omni runs a fixed scenario package (baseline SBS, mulch intensities, undisturbed).
- `data_loader.py` reads Omni Parquet summaries + watershed metadata and builds a solver-ready table.
- `path_ce_solver.py` solves a binary linear program (PuLP) to select, per hillslope, at most one treatment option.
- `PathCostEffective` persists the results to `<wd>/path/*.parquet` and stores a small JSON summary in `path_ce.nodb` for fast API/UI access.

## Workflow

1. **Enable the mod** for a run (WEPPcloud “Mods” → “Path CE”).
2. **Configure thresholds and mulch costs** (web UI or API).
3. **Launch the RQ task** (web UI button → enqueue).
4. **RQ task provisions and runs Omni scenarios**, then calls `PathCostEffective.run()`.
5. **Controller writes artifacts** under `<wd>/path/` and stores `results/status/progress` in `path_ce.nodb`.

## Inputs / Outputs

### Required inputs (working directory artifacts)

PathCE expects these artifacts to exist under the run working directory (`wd`):

| Artifact | Required | Produced by |
|---|---:|---|
| `omni/scenarios.hillslope_summaries.parquet` | yes | Omni scenarios |
| `omni/contrasts.out.parquet` | no (best-effort) | Omni contrasts |
| `watershed/hillslopes.parquet` | yes | watershed build |

If required inputs are missing or malformed, the loader raises `PathCEDataError`.

### Configuration payload

The controller stores a normalized config dict (unknown keys are ignored):

| Key | Type | Default | Meaning |
|---|---|---|---|
| `post_fire_scenario` | `str` | `sbs_map` | Omni scenario key treated as the post-fire baseline. |
| `undisturbed_scenario` | `str \| None` | `undisturbed` | Optional reference scenario key. |
| `sddc_threshold` | `float` | `0.0` | Watershed discharge threshold (see caveat below). |
| `sdyd_threshold` | `float` | `0.0` | Per-hillslope sediment yield threshold (tons). |
| `slope_range` | `[min,max]` | `[None, None]` | Optional slope filter in degrees. |
| `severity_filter` | `list[str] \| None` | `None` | Optional burn severity filter (e.g. `["High","Moderate"]`). |
| `mulch_costs` | `dict[str,float]` | presets → `0.0` | Unit costs keyed by mulch scenario key (UI supplies `$/ha`). |
| `treatment_options` | `list[dict]` | derived | Derived from `mulch_costs` + preset scenarios (not user-extensible today). |

### Outputs (artifacts + NoDb state)

Artifacts written under `<wd>/path/`:

| Path | Contents |
|---|---|
| `path/analysis_frame.parquet` | Solver-ready merged table including post-fire metrics, post-treatment metrics, reductions, slope/area, severity. |
| `path/hillslope_sdyd.parquet` | Per-hillslope final sediment yield (`wepp_id`, `final_Sdyd`). |
| `path/untreatable_hillslopes.parquet` | Subset of hillslopes whose `final_Sdyd` remains above `sdyd_threshold`. |

NoDb file:

| Path | Contents |
|---|---|
| `path_ce.nodb` | `config`, `results`, `status`, `status_message`, `progress`. |

The controller result payload (returned by `run()` and exposed via `/api/path_ce/results`) includes:
`selected_hillslopes`, `treatment_hillslopes`, `total_cost`, `total_fixed_cost`,
`total_sddc_reduction`, `final_sddc`, `used_secondary`, plus artifact paths relative to `wd`.

## Quick Start / Examples

### Web/API (typical production path)

Configure and launch a run through the WEPPcloud endpoints (exact base URL depends on your deployment):

```bash
# Update config (thresholds/costs). Replace RUNID and CONFIG.
curl -sS -X POST \
  "/runs/RUNID/CONFIG/api/path_ce/config" \
  -H "Content-Type: application/json" \
  -d '{
    "sddc_threshold": 10.0,
    "sdyd_threshold": 0.5,
    "slope_min": 10,
    "slope_max": 45,
    "severity_filter": ["High", "Moderate"],
    "mulch_costs": {
      "mulch_15_sbs_map": 250,
      "mulch_30_sbs_map": 400,
      "mulch_60_sbs_map": 700
    }
  }'

# Enqueue the RQ job (runs Omni + solver).
curl -sS -X POST "/runs/RUNID/CONFIG/tasks/path_cost_effective_run"

# Poll status/results.
curl -sS "/runs/RUNID/CONFIG/api/path_ce/status"
curl -sS "/runs/RUNID/CONFIG/api/path_ce/results"
```

### Python (direct controller usage)

This is useful for local debugging when Omni artifacts already exist:

```python
from wepppy.nodb.mods.path_ce import PathCostEffective

wd = "/wc1/runs/<runid>/<config>"
controller = PathCostEffective.getInstance(wd)

controller.config = {
    "sdyd_threshold": 0.5,
    "sddc_threshold": 10.0,
    "slope_range": [10, 45],
    "severity_filter": ["High", "Moderate"],
    "mulch_costs": {
        "mulch_15_sbs_map": 250.0,
        "mulch_30_sbs_map": 400.0,
        "mulch_60_sbs_map": 700.0,
    },
}

result = controller.run()
print(result["total_cost"], result["selected_hillslopes"][:10])
```

### Reading parquet artifacts

```python
from pathlib import Path
import pandas as pd

wd = Path("/wc1/runs/<runid>/<config>")
analysis = pd.read_parquet(wd / "path" / "analysis_frame.parquet")
sdyd = pd.read_parquet(wd / "path" / "hillslope_sdyd.parquet")
```

## Integration Points

- **RQ orchestration**: `wepppy/rq/path_ce_rq.py` provisions required Omni scenarios (via `build_path_omni_scenarios`) and then runs the controller.
- **Flask API/task endpoints**: `wepppy/weppcloud/routes/nodb_api/path_ce_bp.py` exposes `/api/path_ce/*` and `/tasks/path_cost_effective_run`.
- **UI panel**: `wepppy/weppcloud/templates/controls/path_cost_effective_pure.htm` (threshold/cost form, unit expectations).
- **Upstream data dependency**: Omni scenario outputs; see `wepppy/nodb/mods/omni/README.md`.

## Developer Notes

### Code organization

- `path_cost_effective.py`: `PathCostEffective` NoDb controller (config/status/results, persistence to `<wd>/path/`).
- `data_loader.py`: validates and prepares `SolverInputs` from Omni + watershed Parquet artifacts.
- `path_ce_solver.py`: PuLP-based optimization and post-processing (`SolverResult`).
- `presets.py`: scenario keys and mulch presets (`PATH_CE_MULCH_PRESETS`, `build_path_omni_scenarios`).

### Solver model (what is optimized)

- Decision variables: binary `x[treatment,hillslope]` (apply treatment or not), plus binary `B[treatment]` to activate fixed costs.
- Objective (primary): minimize total cost = `area * unit_cost * quantity` + fixed costs.
- Constraints:
  - At most one treatment per hillslope (primary model).
  - Total “water quality” reduction meets a threshold derived from `sddc_threshold`.
  - Each hillslope meets `sdyd_threshold` if possible; otherwise it is forced to its maximum achievable reduction.

### Caveats / current limitations

- `sddc_threshold` is currently enforced using the `NTU post-fire` / `NTU reduction *` columns (see `path_ce_solver.py`). The loader also computes outlet sediment discharge (`Sddc *`) columns, but the solver does not consume them yet.
- `treatment_options` are effectively limited to the mulch presets in `presets.py`; custom treatment catalogs are not supported through `PathCostEffective.config` today.
- Burn severity labels are inferred from landuse codes using `DEFAULT_SEVERITY_MAP` in `data_loader.py`. If your landuse coding differs, severity filtering may not behave as expected.

## Further Reading

- Design notes: `integration_plan.md`, `implementation_plan.md`
- Preset scenarios: `presets.py`
- Omni background: `../omni/README.md`

