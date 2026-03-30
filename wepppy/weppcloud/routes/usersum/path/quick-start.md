# PATH Cost-Effective Quick Start
> How to configure and run a PATH Cost-Effective (PathCE) optimization in WEPPcloud.

## What PATH CE Does

PATH Cost-Effective selects the most cost-effective set of post-fire hillslope
treatments (mulch presets) that meets user-defined sediment-yield and discharge
targets. It uses Omni scenario outputs as the data source and solves a
binary linear program to minimize total treatment cost.

## Prerequisites

Before running PATH CE you need a completed WEPPcloud run with:
- A disturbed-land configuration (fire scenario with SBS map).
- The Omni module enabled (PATH CE provisions its own Omni scenarios
  automatically, but watershed and landuse artifacts must already exist).

## Enabling PATH CE

In the WEPPcloud UI, open the **Mods** dropdown and enable **Path CE**.
This adds the PATH CE configuration panel to your run page.

## Configuration Parameters

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `sddc_threshold` | float | 0.0 | Watershed discharge reduction target. |
| `sdyd_threshold` | float | 0.0 | Per-hillslope sediment yield threshold (tons). |
| `slope_min` / `slope_max` | float | None | Optional slope filter in degrees. |
| `severity_filter` | list | None | Burn severity filter (e.g. `["High", "Moderate"]`). |
| `mulch_costs` | dict | presets at 0.0 | Unit costs keyed by mulch scenario key ($/ha). |

## Running from the UI

1. Open the PATH CE panel on your run page.
2. Set thresholds, slope range, severity filter, and mulch costs.
3. Click the run button.
4. WEPPcloud enqueues an RQ job that provisions Omni scenarios and runs the solver.
5. Poll the status panel until completion.
6. Review results: selected hillslopes, total cost, and reduction metrics.

## Running from the API

### 1. Update configuration

```
POST /runs/{runid}/{config}/api/path_ce/config
Content-Type: application/json

{
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
}
```

### 2. Launch the RQ job

```
POST /runs/{runid}/{config}/tasks/path_cost_effective_run
```

This enqueues the full pipeline: Omni scenario provisioning followed by
the solver.

### 3. Poll status and retrieve results

```
GET /runs/{runid}/{config}/api/path_ce/status
GET /runs/{runid}/{config}/api/path_ce/results
```

The results payload includes `selected_hillslopes`, `treatment_hillslopes`,
`total_cost`, `total_fixed_cost`, `total_sddc_reduction`, `final_sddc`,
and artifact paths.

## Output Artifacts

Artifacts are written under `<working-directory>/path/`:

| File | Contents |
|---|---|
| `analysis_frame.parquet` | Solver-ready merged table with post-fire metrics, treatment reductions, slope, area, and severity. |
| `hillslope_sdyd.parquet` | Per-hillslope final sediment yield (`wepp_id`, `final_Sdyd`). |
| `untreatable_hillslopes.parquet` | Hillslopes whose final sediment yield remains above the threshold. |

## Reading Artifacts

```python
from pathlib import Path
import pandas as pd

wd = Path("/wc1/runs/<runid>/<config>")
analysis = pd.read_parquet(wd / "path" / "analysis_frame.parquet")
sdyd = pd.read_parquet(wd / "path" / "hillslope_sdyd.parquet")
```

## Current Limitations

- Treatment options are limited to the mulch presets defined internally;
  custom treatment catalogs are not yet supported.
- The `sddc_threshold` constraint currently uses NTU-based columns rather
  than outlet sediment discharge columns.
- Burn severity labels are inferred from landuse codes using a default
  mapping. Non-standard landuse coding may cause unexpected severity
  filtering behavior.

## Further Reading

- Module internals: `wepppy/nodb/mods/path_ce/README.md`
- Omni scenario background: `wepppy/nodb/mods/omni/README.md`
- RQ job orchestration: `wepppy/rq/path_ce_rq.py`
- Flask API endpoints: `wepppy/weppcloud/routes/nodb_api/path_ce_bp.py`
