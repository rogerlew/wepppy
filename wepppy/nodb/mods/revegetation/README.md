# Revegetation (Cover Transform) NoDb Mod

> Manages post-fire revegetation “cover transform” CSVs that rescale RAP fractional cover time series before WEPP (and related) runs.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb locking/cache expectations and debugging hooks.

## Overview

The `Revegetation` mod is a small NoDb-backed controller used to apply scenario-based vegetation recovery assumptions after a disturbance (for example, wildfire).

When enabled alongside `disturbed` and `rap_ts`, the model workflow can:
- Select a built-in cover-transform scenario (for example, a 20-year recovery curve), or accept a user-uploaded transform CSV.
- Persist the selected transform into the run working directory for reproducibility.
- Provide a parsed `cover_transform` mapping that `RAP_TS` uses to generate transformed `.cov` time series used by WEPP preparation.

This mod does **not** directly run WEPP/RHEM; it supplies metadata and transforms used by other controllers during prep.

## Workflow

1. **User selects a scenario (or uploads a CSV).**
   - UI sends `reveg_scenario` as one of:
     - `""` (Observed / no transform)
     - `"20-yr_Recovery.csv"` (built-in)
     - `"20-yr_PartialRecovery.csv"` (built-in)
     - `"user_cover_transform"` (user upload mode)
2. **Controller stages the transform file under the run working directory.**
   - Built-ins are copied from `data/cover_transforms/` into `<wd>/revegetation/`.
   - User uploads are saved into `<wd>/revegetation/` and then “activated” by recording the filename.
3. **`RAP_TS.prep_cover()` decides whether to transform.**
   - If both `Disturbed.fire_date` and `Revegetation.cover_transform` are present, RAP cover is rescaled relative to the fire-year cover and written to `p*.cov` via `RAP_TS._prep_transformed_cover()`.
   - Otherwise, RAP cover is written without transformation.

## Core API

Primary entry point: `wepppy.nodb.mods.revegetation.revegetation.Revegetation`.

| Member | Type | Purpose |
|---|---|---|
| `Revegetation.getInstance(wd)` | classmethod | Returns the run-scoped singleton (hydrated from `<wd>/revegetation.nodb`). |
| `load_cover_transform(reveg_scenario)` | method | Activates a built-in scenario by copying it into `<wd>/revegetation/` and setting `cover_transform_fn`. No-op for `"user_cover_transform"`. Clears selection when passed `""`. |
| `validate_user_defined_cover_transform(fn)` | method | Marks an already-saved file in `<wd>/revegetation/` as the active transform and sets `user_defined_cover_transform=True`. |
| `cover_transform_fn` | `str` property | Filename of the active CSV in `<wd>/revegetation/` (empty string means “Observed”). |
| `user_defined_cover_transform` | `bool` property | Indicates whether the active transform was user-supplied. |
| `cover_transform` | `Optional[CoverTransform]` property | Parsed scale-factor mapping, or `None` when no valid CSV is active. |
| `revegetation_dir` | `str` property | `<wd>/revegetation`. |
| `clean()` | method | Deletes and recreates `<wd>/revegetation/`. Called during controller initialization. |

### `CoverTransform` shape

`CoverTransform` is a mapping:

```python
CoverTransform = dict[tuple[str, str], numpy.ndarray[numpy.float32]]
```

Keys are `(burn_class, vegetation_label)` pairs (for example, `("High", "Tree")`), and values are 1-D arrays of per-year multiplicative scale factors.

## Cover Transform CSV format

The controller expects a headerless CSV where:
- **Row 0**: soil burn severity labels (repeated across columns)
- **Row 1**: vegetation labels (one per column)
- **Rows 2..**: scale factors for year 0, year 1, … relative to the **fire year**

Example (two header rows plus year-0 scale factors):

```text
High,High,Moderate,Moderate
Tree,Shrub,Tree,Shrub
0.30,0.30,0.50,0.50
```

Notes:
- `RAP_TS` currently looks up transform keys for the labels: `Tree`, `Shrub`, `Perennial`, `Annual`, `Litter`, `Bare`. If a key is missing, that band is left untransformed.
- If the RAP time series extends beyond the number of scale-factor rows, `RAP_TS` uses the **last** scale factor.
- Years *before* the fire year are not transformed.

## Outputs

This mod writes (or causes downstream prep to write) the following run-scoped artifacts:

- **NoDb state**: `<wd>/revegetation.nodb` (managed by `NoDbBase`)
- **Staged transform CSV**: `<wd>/revegetation/<scenario>.csv` (copied from the library or uploaded by a user)
- **Downstream WEPP inputs (via `RAP_TS`)**:
  - `<wd>/runs/*/p*.cov` (time-varying cover)
  - `<wd>/runs/*/simfire.txt` and `<wd>/runs/*/firedate.txt` (fire timing metadata)

## Integration points

- **Upstream / prerequisites**
  - `Disturbed.fire_date` enables “post-fire” timing used by `RAP_TS` transforms.
  - `Landuse.identify_burn_class(...)` provides burn class labels used as transform keys.
- **Downstream consumers**
  - `wepppy.nodb.mods.rap.rap_ts.RAP_TS.prep_cover()` reads `Revegetation.cover_transform` when present.
  - `wepppy.nodb.core.wepp.Wepp._prep_revegetation()` triggers `RAP_TS.prep_cover()` and writes fire metadata.
- **WEPPcloud / rq-engine plumbing**
  - `wepppy/microservices/rq_engine/wepp_routes.py` reads `reveg_scenario` and calls `Revegetation.load_cover_transform(...)`.
  - `wepppy/microservices/rq_engine/upload_disturbed_routes.py` handles user CSV upload and calls `Revegetation.validate_user_defined_cover_transform(...)`.
  - `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/revegetation.htm` renders the UI selector and upload control.

## Quick start / examples

### Load a built-in scenario

```python
from wepppy.nodb.mods.revegetation import Revegetation

reveg = Revegetation.getInstance("/path/to/run-wd")
reveg.load_cover_transform("20-yr_Recovery.csv")

transform = reveg.cover_transform
assert transform is not None
print(transform[("High", "Tree")][:5])  # year-0..year-4 scale factors
```

### Activate a user-uploaded scenario

```python
from pathlib import Path
from wepppy.nodb.mods.revegetation import Revegetation

wd = "/path/to/run-wd"
reveg = Revegetation.getInstance(wd)

# Save a CSV under <wd>/revegetation/ (the rq-engine upload route does this step).
csv_name = "my_transform.csv"
Path(reveg.revegetation_dir, csv_name).write_text("High\\nTree\\n0.3\\n")

reveg.validate_user_defined_cover_transform(csv_name)
assert reveg.user_defined_cover_transform is True
```

## Data assets in this directory

- `data/cover_transforms/*.csv`: Built-in cover-transform scenarios.
  - `20-yr_Recovery.csv` and `20-yr_PartialRecovery.csv` are also duplicated at the package root for convenience (identical content).
  - `data/cover_transforms/cover_transform.xlsx` is the spreadsheet source for those CSVs.
- `data/revegetation_land_soil_lookup.csv`: Landuse/soil-texture lookup used by revegetation-oriented run configs (for example, `wepppy/nodb/configs/reveg*.cfg`) to select parameter sets.

## Developer notes / caveats

- `Revegetation.clean()` deletes the entire `<wd>/revegetation/` directory; it is called during controller initialization.
- `validate_user_defined_cover_transform(...)` only checks that the file exists under `<wd>/revegetation/` and records its name; it does not parse/validate the CSV schema beyond what `cover_transform` will later attempt to load.
- `cover_transform` treats the first two rows as headers and does not enforce numeric types until converting values to `float32`.

## Further reading

- `wepppy/nodb/mods/revegetation/revegetation.py`
- `wepppy/nodb/mods/rap/rap_ts.py`
- `wepppy/nodb/core/wepp.py`
- `wepppy/microservices/rq_engine/wepp_routes.py`
- `wepppy/microservices/rq_engine/upload_disturbed_routes.py`
- `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/revegetation.htm`
