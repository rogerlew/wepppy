# Disturbed NoDb Controller

> Orchestrates wildfire/logging disturbance scenarios by remapping landuse and regenerating WEPP management/soil artifacts from burn-severity rasters.

> **See also:** [AGENTS.md](../../../AGENTS.md) for Working with NoDb Controllers.

## Overview

Disturbed is the NoDb controller that turns a disturbance raster (typically Soil Burn Severity) into WEPP-ready inputs for a run. It owns the run-scoped `disturbed/` directory, manages the land/soil lookup table, and coordinates landuse remapping, management selection, soil regeneration, and PMET parameter export.

Primary users are WEPPcloud operators and BAER analysts who need repeatable post-fire parameterization tied to a geospatial raster. The controller is built to run inside a WEPPcloud run, emit progress via Redis, and persist state to `disturbed.nodb`.

## Workflow

1. **Load and normalize the disturbance raster**
   - Reprojects the raster into the run DEM grid and builds a `SoilBurnSeverityMap` (classes 130-133).
   - Tracks coverage statistics (`noburn`, `low`, `moderate`, `high`) for UI summaries.

2. **Remap landuse to disturbed classes**
   - Uses the current landuse mapping (typically `wepppy/wepp/management/data/disturbed.json`) to swap management keys based on burn class and the existing `disturbed_class`.
   - Forest and young-forest are always eligible; shrubs and grass are controlled by `burn_shrubs` and `burn_grass`.
   - Rebuilds management summaries after remap so downstream steps use the disturbed management files.

3. **Optionally override canopy cover from Treecanopy**
   - If the Treecanopy mod is present, `cancov_override` is set per hillslope for forest/young forest classes.

4. **Generate PMET parameters**
   - Writes `pmetpara.txt` using `pmet_kcb` and `pmet_rawp` from the lookup table (or defaults for unclassified/developed land).

5. **Regenerate soils**
   - For each hillslope (and for each MOFE if enabled), computes a simplified texture from clay/sand and looks up replacement parameters.
   - Writes disturbed `.sol` files via `WeppSoilUtil` (`to_7778disturbed` or `to_over9000` based on `sol_ver`).
   - For MOFE runs, stacks OFE-specific disturbed soils into a synthesized `.mofe.sol` using `SoilMultipleOfeSynth`.

## Management and Soil File Modifications

### Landuse remap and management selection

- `remap_landuse()` and `remap_mofe_landuse()` map SBS classes 131/132/133 to low/mod/high severity management keys.
- The mapping is driven by the active landuse map (default is `wepppy/wepp/management/data/disturbed.json`).
- Forest and young-forest burn classes map to:
  - `UnDisturbed/Low_Severity_Fire.man`
  - `UnDisturbed/Moderate_Severity_Fire.man`
  - `UnDisturbed/High_Severity_Fire.man`
- Shrub burn classes map to:
  - `UnDisturbed/Shrub_Low_Severity_Fire.man`
  - `UnDisturbed/Shrub_Moderate_Severity_Fire.man`
  - `UnDisturbed/Shrub_High_Severity_Fire.man`
- Grass burn classes map to:
  - `UnDisturbed/Grass_Low_Severity_Fire.man`
  - `UnDisturbed/Grass_Moderate_Severity_Fire.man`
  - `UnDisturbed/Grass_High_Severity_Fire.man`

If a management entry defines `SoilFile`/`sol_path`, the controller copies that soil directly instead of regenerating a disturbed soil from the lookup table.

### Soil regeneration and parameter replacements

- The run-scoped lookup table lives at `disturbed/disturbed_land_soil_lookup.csv` (copied from `wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv`).
- Each row maps `(disturbed class, texture)` to replacement values used by `WeppSoilUtil`:
  - `ki`, `kr`, `shcrit` (erodibility and critical shear)
  - `avke` (effective hydraulic conductivity, written to the soil header)
  - `ksatadj`, `ksatfac`, `ksatrec` (hydrophobicity adjustments for 9001/9002 soils)
  - `lkeff` (lower bound on effective K for 9003/9005 soils)
- For fire treatments that append suffixes (`-mulch_15`, `-thinning`, etc.), the soil lookup uses the base disturbed class (e.g., `forest moderate sev fire`).
- If a class is missing from the lookup during MOFE processing and `sol_ver` requires 9002+, defaults are injected so the soil can still be synthesized.

### Static management overrides (added February 2, 2026)

To keep undisturbed vs. disturbed comparisons strictly "static to static," the lookup table now supports `plant.data.decfct` and `plant.data.dropfc` overrides. For all landuses except `agriculture crops`, these are set to `1` in the default lookup so management files do not decay or drop plant material during the comparison window. This avoids unintended differences in residue/root mass (and therefore `kr` adjustment factors) that would otherwise arise from differing growth/decay timing between management templates.

As part of this static-alignment work, `UnDisturbed/Shrub.man` was updated to match the Tahoe shrub template by setting `hmax=2.0` and `ini.data.sumrtm`/`ini.data.sumsrm` to `0.30`.

We also switched NLCD key `72` (Sedge/Herbaceous) to `UnDisturbed/Tall_Grass.man` in `wepppy/wepp/management/data/disturbed.json` to keep tall grass comparisons aligned with the static template.
## Landuse Parameterization (Forest, Shrub, Grass)

The tables below capture the initial conditions (`IniLoopCropland`) and plant parameters (`PlantLoopCropland`) for the management files used by disturbed classes. Values are from the `.man` files under `wepppy/wepp/management/data/` and are shown here because Disturbed remaps hillslopes directly to these classes.

### Forest and Young Forest

**Initial conditions**

| Disturbed class | Management file | cancov | inrcov | rilcov | rspace | rfcum | rhinit | rrinit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| forest | `UnDisturbed/Old_Forest.man` | 0.90 | 1.00 | 1.00 | 0.00 | 400.00 | 0.10 | 0.10 |
| young forest | `UnDisturbed/Young_Forest.man` | 0.80 | 0.96 | 0.96 | 0.00 | 400.00 | 0.08 | 0.08 |
| forest low sev fire | `UnDisturbed/Low_Severity_Fire.man` | 0.75 | 0.85 | 0.85 | 0.00 | 400.00 | 0.04 | 0.04 |
| forest moderate sev fire | `UnDisturbed/Moderate_Severity_Fire.man` | 0.60 | 0.60 | 0.60 | 0.00 | 400.05 | 0.04826 | 0.06 |
| forest high sev fire | `UnDisturbed/High_Severity_Fire.man` | 0.40 | 0.30 | 0.30 | 0.00 | 400.00 | 0.06 | 0.06 |
| forest prescribed fire | `UnDisturbed/Prescribed_Fire.man` | 0.85 | 0.85 | 0.85 | 2.00 | 400.00 | 0.06 | 0.06 |

**Plant parameters**

| Disturbed class | rdmax | xmxlai | hmax | cuthgt |
| --- | --- | --- | --- | --- |
| forest | 2.00 | 14.0 | 20.0 | 20.0 |
| young forest | 0.60 | 12.0 | 4.0 | 20.0 |
| forest low sev fire | 0.30 | 4.0 | 0.30 | 0.30 |
| forest moderate sev fire | 0.29998 | 3.0 | 0.2794 | 0.29998 |
| forest high sev fire | 0.30 | 2.0 | 0.20 | 0.30 |
| forest prescribed fire | 0.50 | 10.0 | 2.0 | 4.0 |

### Shrub

**Initial conditions**

| Disturbed class | Management file | cancov | inrcov | rilcov | rspace | rfcum | rhinit | rrinit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| shrub | `UnDisturbed/Shrub.man` | 0.40 | 0.85 | 0.85 | 0.00 | 1000.00 | 0.10 | 0.10 |
| shrub low sev fire | `UnDisturbed/Shrub_Low_Severity_Fire.man` | 0.33 | 0.80 | 0.80 | 2.00 | 400.00 | 0.06 | 0.06 |
| shrub moderate sev fire | `UnDisturbed/Shrub_Moderate_Severity_Fire.man` | 0.27 | 0.55 | 0.55 | 2.00 | 400.00 | 0.06 | 0.06 |
| shrub high sev fire | `UnDisturbed/Shrub_High_Severity_Fire.man` | 0.05 | 0.30 | 0.30 | 2.00 | 400.00 | 0.06 | 0.06 |
| shrub prescribed fire | `UnDisturbed/Prescribed_Fire.man` | 0.85 | 0.85 | 0.85 | 2.00 | 400.00 | 0.06 | 0.06 |

**Plant parameters**

| Disturbed class | rdmax | xmxlai | hmax | cuthgt |
| --- | --- | --- | --- | --- |
| shrub | 0.40 | 2.0 | 1.0 | 1.2 |
| shrub low sev fire | 0.20 | 3.0 | 2.0 | 4.0 |
| shrub moderate sev fire | 0.20 | 2.0 | 2.0 | 4.0 |
| shrub high sev fire | 0.20 | 1.0 | 2.0 | 4.0 |
| shrub prescribed fire | 0.50 | 10.0 | 2.0 | 4.0 |

### Grass (Tall and Short)

**Initial conditions**

| Disturbed class | Management file | cancov | inrcov | rilcov | rspace | rfcum | rhinit | rrinit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tall grass | `UnDisturbed/Tall_Grass.man` | 0.40 | 0.60 | 0.60 | 0.00 | 400.00 | 0.02 | 0.02 |
| short grass | `GIS/Poor grass.man` | 0.60 | 0.40 | 0.40 | 0.00 | 400.00 | 0.04 | 0.04 |
| grass low sev fire | `UnDisturbed/Grass_Low_Severity_Fire.man` | 0.30 | 0.60 | 0.60 | 0.00 | 400.00 | 0.02 | 0.02 |
| grass moderate sev fire | `UnDisturbed/Grass_Moderate_Severity_Fire.man` | 0.25 | 0.35 | 0.35 | 0.00 | 400.00 | 0.02 | 0.02 |
| grass high sev fire | `UnDisturbed/Grass_High_Severity_Fire.man` | 0.041 | 0.10 | 0.10 | 0.00 | 400.00 | 0.02 | 0.02 |
| grass prescribed fire | `UnDisturbed/Grass_Low_Severity_Fire.man` | 0.30 | 0.60 | 0.60 | 0.00 | 400.00 | 0.02 | 0.02 |

**Plant parameters**

| Disturbed class | rdmax | xmxlai | hmax | cuthgt |
| --- | --- | --- | --- | --- |
| tall grass | 0.60 | 6.0 | 0.60 | 1.0 |
| short grass | 0.40 | 9.0 | 1.0 | 4.0 |
| grass low sev fire | 0.40 | 3.0 | 0.40 | 1.0 |
| grass moderate sev fire | 0.30 | 2.0 | 0.30 | 1.0 |
| grass high sev fire | 0.20 | 1.0 | 0.20 | 1.0 |
| grass prescribed fire | 0.40 | 3.0 | 0.40 | 1.0 |

### Soil lookup examples (loam texture)

These rows come from `disturbed_land_soil_lookup.csv` for `stext=loam`. Other textures (clay loam, sand loam, silt loam) are defined in the same table.

| Disturbed class | ki | kr | shcrit | avke | ksatadj | ksatfac | ksatrec | rdmax | xmxlai | lkeff |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| forest low sev fire | 1000000 | 8.00E-05 | 1 | 20 | 0 | 1.3 | 0.3 | 0.3 | 4 | 10 |
| forest moderate sev fire | 1000000 | 8.00E-05 | 1 | 20 | 0 | 1.3 | 0.3 | 0.3 | 4 | 1 |
| forest high sev fire | 1000000 | 0.0001 | 1 | 15 | 1 | 100 | 0.3 | 0.3 | 2 | 0.1 |
| forest prescribed fire | 1000000 | 8.00E-05 | 1 | 20 | 0 | 1.3 | 0.3 | 0.5 | 10 | 10 |
| shrub low sev fire | 1000000 | 8.00E-05 | 1 | 20 | 0 | 1.3 | 0.3 | 0.2 | 2 | 10 |
| shrub moderate sev fire | 1000000 | 8.00E-05 | 1 | 20 | 0 | 1.3 | 0.3 | 0.2 | 2 | 1 |
| shrub high sev fire | 1000000 | 0.0001 | 1 | 15 | 1 | 100 | 0.3 | 0.2 | 1 | 1 |
| shrub prescribed fire | 1000000 | 8.00E-05 | 1 | 20 | 0 | 1.3 | 0.3 | 0.3 | 4 | 10 |
| grass low sev fire | 1000000 | 6.00E-05 | 1 | 30 | 0 | 1.5 | 0.3 | 0.4 | 5 | -9999 |
| grass moderate sev fire | 1000000 | 6.00E-05 | 1 | 30 | 0 | 1.5 | 0.3 | 0.4 | 5 | -9999 |
| grass high sev fire | 1000000 | 6.00E-05 | 1 | 30 | 0 | 1.5 | 0.3 | 0.4 | 5 | -9999 |
| grass prescribed fire | 1000000 | 6.00E-05 | 1 | 30 | 0 | 1.5 | 0.3 | 0.4 | 5 | -9999 |

## Model Effects in WEPP-forest (trace)

Disturbed updates parameters that are consumed directly by the WEPP-forest Fortran kernels. Key linkages:

- **Canopy/interrill/rill cover** (`cancov`, `inrcov`, `rilcov`) drive hydraulic friction and rainfall interception.
  - `frcfac.for` uses `inrcov` and `rilcov` to build Darcy friction factors, and `cancov` to add canopy friction.
  - `idat.for` uses `cancov` with live biomass to compute rainfall interception (`plaint`).
- **Rill spacing and width** (`rspace`, `width`) control rill area and scale interrill detachment.
  - `frcfac.for` computes rill area as `width / rspace` to blend rill/interrill friction.
  - `param.for` scales interrill detachment by `rspace / width`.
- **Erodibility and critical shear** (`ki`, `kr`, `shcrit`) feed the erosion terms.
  - `param.for` uses `ki` in interrill detachment, `kr` in rill erodibility (`eata`), and `shcrit` to compute critical shear (`tauc`).
- **Hydraulic conductivity adjustments** (`avke`, `ksatadj`, `ksatfac`, `ksatrec`, `lkeff`).
  - `input.for` reads these fields from the soil file (9001+ and 9003+ formats).
  - `infpar.for` applies the hydrophobicity logic when `ksatadj=1`, computing effective K from saturation fraction and enforcing `lkeff` lower bounds for 9003/9005.

## Quick Start

```python
import shutil
from os.path import join as _join

from wepppy.nodb.mods import Disturbed

wd = "/wc1/runs/ab/abcdef12345"
disturbed = Disturbed.getInstance(wd)

src = "/path/to/sbs.tif"
dst = _join(disturbed.disturbed_dir, "sbs.tif")
shutil.copyfile(src, dst)

disturbed.validate("sbs.tif")
disturbed.remap_landuse()
disturbed.modify_soils()
```

## Configuration

Values are read from the `disturbed` section of the run config.

| Parameter | Default | Description |
| --- | --- | --- |
| `disturbed.land_soil_lookup` | `wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv` | Source lookup copied into `disturbed/disturbed_land_soil_lookup.csv`. |
| `disturbed.h0_max_om` | `None` | Optional cap on first-horizon OM for fire classes. |
| `disturbed.sol_ver` | `7778.0` | Soil file version for output (`7778`, `9001`, `9002`, `9003`, `9005`). |
| `disturbed.fire_date` | `None` | Fire date string used by downstream reporting. |
| `disturbed.burn_shrubs` | `True` | Whether shrub classes are remapped to burn severities. |
| `disturbed.burn_grass` | `False` | Whether grass classes are remapped to burn severities. |

## Developer Notes

- `build_extended_land_soil_lookup()` is a helper for exporting a merged lookup (management + soil parameters); it is not part of the default run workflow.
- `lookup_disturbed_class()` strips treatment suffixes (mulch/thinning) so soils are keyed by burn severity, not treatment type.
- For MOFE runs, each OFE gets its own disturbed soil file and is reassembled into a `.mofe.sol` via `SoilMultipleOfeSynth`.

## Further Reading

- `wepppy/wepp/management/AGENTS.md` (management file conventions)
- `wepppy/wepp/soils/utils/README.md` (soil migration utilities)
- `wepppy/weppcloud/routes/usersum/weppcloud/disturbed-land-soil-lookup.md` (parameter definitions)
- `docs/ui-docs/control-ui-styling/sbs_controls_behavior.md` (SBS control behavior)
