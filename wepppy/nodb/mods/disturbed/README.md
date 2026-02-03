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

We are keeping `UnDisturbed/Shrub.man` in sync with `Tahoe/Tahoe_Shrub.man` (the file is treated as the canonical shrub baseline for disturbed comparisons).

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
| shrub | `UnDisturbed/Shrub.man` | 0.70 | 0.90 | 0.90 | 2.00 | 400.00 | 0.06 | 0.06 |
| shrub low sev fire | `UnDisturbed/Shrub_Low_Severity_Fire.man` | 0.33 | 0.80 | 0.80 | 2.00 | 400.00 | 0.06 | 0.06 |
| shrub moderate sev fire | `UnDisturbed/Shrub_Moderate_Severity_Fire.man` | 0.27 | 0.55 | 0.55 | 2.00 | 400.00 | 0.06 | 0.06 |
| shrub high sev fire | `UnDisturbed/Shrub_High_Severity_Fire.man` | 0.05 | 0.30 | 0.30 | 2.00 | 400.00 | 0.06 | 0.06 |
| shrub prescribed fire | `UnDisturbed/Prescribed_Fire.man` | 0.85 | 0.85 | 0.85 | 2.00 | 400.00 | 0.06 | 0.06 |

**Plant parameters**

| Disturbed class | rdmax | xmxlai | hmax | cuthgt |
| --- | --- | --- | --- | --- |
| shrub | 0.50 | 10.0 | 2.0 | 4.0 |
| shrub low sev fire | 0.20 | 3.0 | 2.0 | 4.0 |
| shrub moderate sev fire | 0.20 | 2.0 | 2.0 | 4.0 |
| shrub high sev fire | 0.20 | 1.0 | 2.0 | 4.0 |
| shrub prescribed fire | 0.50 | 10.0 | 2.0 | 4.0 |

### Test Matrix Analysis Results (February 2026)

Analysis of 48 hillslope simulations across:
- 4 soil textures (clay loam, loam, sand loam, silt loam)
- 3 vegetation types (forest, shrub, tall grass)
- 4 burn severities (unburned, low, moderate, high)

**Climate**: MC KENZIE BRIDGE RS, OR - 100 years, ~1,194 mm/yr precipitation

**Slope**: 201.68m variable profile (avg ~43% grade)

**Soil format**: 9002 with hydrophobicity parameters

Test script: `tests/disturbed/test_disturbed_matrix.py`
Analysis script: `tests/disturbed/analyze_matrix.py`

#### Runoff Event Counts (Burned vs Unburned)

Event counts compare burned vs unburned runoff by matching day/month/year across
all 4 soil textures. Results aggregated from 100-year simulations (48 total runs).

| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|-------------:|------------------:|------:|------------------:|
| forest | low | 1,308 | 1,122 | 17 | 169 |
| forest | moderate | 1,240 | 966 | 31 | 243 |
| forest | high | 1,202 | 912 | 22 | 268 |
| shrub | low | 1,406 | 1,216 | 3 | 187 |
| shrub | moderate | 1,391 | 1,081 | 65 | 245 |
| shrub | high | 1,380 | 957 | 43 | 380 |
| tall grass | low | 1,493 | 359 | 981 | 153 |
| tall grass | moderate | 1,480 | 746 | 181 | 553 |
| tall grass | high | 1,459 | 773 | 73 | 613 |

#### Sediment Delivery Event Counts (Burned vs Unburned)

| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|-------------:|------------------:|------:|------------------:|
| forest | low | 1,308 | 114 | 1,191 | 3 |
| forest | moderate | 1,240 | 134 | 1,104 | 2 |
| forest | high | 1,202 | 236 | 966 | 0 |
| shrub | low | 1,406 | 51 | 1,191 | 164 |
| shrub | moderate | 1,391 | 86 | 1,170 | 135 |
| shrub | high | 1,380 | 255 | 1,093 | 32 |
| tall grass | low | 1,493 | 80 | 1,405 | 8 |
| tall grass | moderate | 1,480 | 87 | 1,388 | 5 |
| tall grass | high | 1,459 | 278 | 1,181 | 0 |

#### Runoff Descriptive Statistics (mm)

Statistics aggregated across all 4 soil textures for 100-year simulations.

| Veg Type | Severity | Condition | Mean | Std Dev | Median | Total |
|----------|----------|-----------|-----:|--------:|-------:|------:|
| forest | low | burned | 20.26 | 19.00 | 15.03 | 26,344 |
| | | unburned | 18.90 | 17.45 | 14.09 | 24,633 |
| forest | moderate | burned | 20.91 | 19.19 | 15.34 | 25,765 |
| | | unburned | 19.15 | 17.69 | 14.26 | 23,663 |
| forest | high | burned | 21.07 | 19.15 | 15.47 | 25,159 |
| | | unburned | 19.23 | 17.86 | 14.30 | 23,023 |
| shrub | low | burned | 19.82 | 18.52 | 14.53 | 27,638 |
| | | unburned | 19.05 | 18.51 | 13.60 | 26,581 |
| shrub | moderate | burned | 19.85 | 18.48 | 14.60 | 27,393 |
| | | unburned | 19.17 | 18.56 | 13.79 | 26,468 |
| shrub | high | burned | 19.73 | 18.36 | 14.78 | 27,038 |
| | | unburned | 19.24 | 18.60 | 13.93 | 26,366 |
| tall grass | low | burned | 19.00 | 18.29 | 13.51 | 28,191 |
| | | unburned | 18.65 | 18.05 | 13.15 | 27,694 |
| tall grass | moderate | burned | 19.15 | 18.33 | 13.65 | 28,185 |
| | | unburned | 18.77 | 18.07 | 13.35 | 27,658 |
| tall grass | high | burned | 19.29 | 18.35 | 14.16 | 27,972 |
| | | unburned | 19.00 | 18.10 | 13.64 | 27,562 |

#### Sediment Delivery Descriptive Statistics (kg/m)

| Veg Type | Severity | Condition | Mean | Std Dev | Median | Total |
|----------|----------|-----------|-----:|--------:|-------:|------:|
| forest | low | burned | 0.334 | 1.447 | 0.000 | 468.5 |
| | | unburned | 0.021 | 0.129 | 0.000 | 30.6 |
| forest | moderate | burned | 0.888 | 3.366 | 0.000 | 1,229.2 |
| | | unburned | 0.022 | 0.132 | 0.000 | 30.6 |
| forest | high | burned | 4.072 | 12.020 | 0.000 | 5,338.0 |
| | | unburned | 0.023 | 0.134 | 0.000 | 30.6 |
| shrub | low | burned | 0.099 | 0.433 | 0.000 | 149.0 |
| | | unburned | 0.118 | 0.402 | 0.000 | 188.4 |
| shrub | moderate | burned | 0.230 | 1.019 | 0.000 | 350.7 |
| | | unburned | 0.119 | 0.404 | 0.000 | 188.4 |
| shrub | high | burned | 1.874 | 5.836 | 0.000 | 2,775.7 |
| | | unburned | 0.120 | 0.406 | 0.000 | 188.4 |
| tall grass | low | burned | 0.179 | 0.923 | 0.000 | 291.6 |
| | | unburned | 0.149 | 0.775 | 0.000 | 242.7 |
| tall grass | moderate | burned | 0.330 | 1.742 | 0.000 | 537.4 |
| | | unburned | 0.151 | 0.779 | 0.000 | 242.7 |
| tall grass | high | burned | 3.941 | 12.201 | 0.000 | 6,398.5 |
| | | unburned | 0.153 | 0.784 | 0.000 | 242.7 |

#### Key Findings

1. **Runoff increases with burn severity**: For forest and shrub, burned conditions consistently show more runoff events than unburned (e.g., forest low: 86% burned > unburned). Tall grass shows more variable response due to already low cover.

2. **Sediment delivery increases dramatically with high severity fire**: Forest high severity shows 174x more total sediment delivery than unburned (5,338 vs 30.6 kg/m). Shrub and tall grass show similar patterns.

3. **Directional consistency**: High severity fire produces more sediment in 100% of matched events for forest (236 burned > unburned, 0 unburned > burned) and tall grass. Lower severities show more mixed results due to moisture state interactions.

4. **Shrub baseline caveat**: Shrub unburned shows higher sediment than shrub low/moderate severity in some events (164 and 135 respectively), likely due to parameter differences in baseline shrub vs fire recovery management files

#### Runoff Event Counts by Soil Texture

Rows grouped by texture to highlight texture-specific response patterns.

**Clay Loam**

| Veg Type | Severity | Total | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|------:|------------------:|------:|------------------:|
| forest | low | 388 | 322 | 11 | 55 |
| forest | moderate | 368 | 267 | 20 | 81 |
| forest | high | 357 | 256 | 10 | 91 |
| shrub | low | 415 | 363 | 1 | 51 |
| shrub | moderate | 410 | 305 | 22 | 83 |
| shrub | high | 406 | 276 | 16 | 114 |
| tall grass | low | 434 | 94 | 298 | 42 |
| tall grass | moderate | 427 | 204 | 64 | 159 |
| tall grass | high | 421 | 222 | 22 | 177 |

**Loam**

| Veg Type | Severity | Total | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|------:|------------------:|------:|------------------:|
| forest | low | 349 | 301 | 4 | 44 |
| forest | moderate | 332 | 267 | 4 | 61 |
| forest | high | 323 | 253 | 2 | 68 |
| shrub | low | 385 | 336 | 1 | 48 |
| shrub | moderate | 380 | 310 | 15 | 55 |
| shrub | high | 378 | 270 | 13 | 95 |
| tall grass | low | 405 | 95 | 271 | 39 |
| tall grass | moderate | 401 | 200 | 52 | 149 |
| tall grass | high | 397 | 205 | 24 | 168 |

**Sand Loam**

| Veg Type | Severity | Total | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|------:|------------------:|------:|------------------:|
| forest | low | 249 | 219 | 0 | 30 |
| forest | moderate | 235 | 192 | 2 | 41 |
| forest | high | 227 | 181 | 4 | 42 |
| shrub | low | 265 | 223 | 0 | 42 |
| shrub | moderate | 263 | 213 | 4 | 46 |
| shrub | high | 261 | 186 | 5 | 70 |
| tall grass | low | 289 | 79 | 177 | 33 |
| tall grass | moderate | 289 | 154 | 25 | 110 |
| tall grass | high | 281 | 153 | 11 | 117 |

**Silt Loam**

| Veg Type | Severity | Total | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|------:|------------------:|------:|------------------:|
| forest | low | 322 | 280 | 2 | 40 |
| forest | moderate | 305 | 240 | 5 | 60 |
| forest | high | 295 | 222 | 6 | 67 |
| shrub | low | 341 | 294 | 1 | 46 |
| shrub | moderate | 338 | 253 | 24 | 61 |
| shrub | high | 335 | 225 | 9 | 101 |
| tall grass | low | 365 | 91 | 235 | 39 |
| tall grass | moderate | 363 | 188 | 40 | 135 |
| tall grass | high | 360 | 193 | 16 | 151 |

#### Sediment Delivery Event Counts by Soil Texture

**Clay Loam**

| Veg Type | Severity | Total | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|------:|------------------:|------:|------------------:|
| forest | low | 388 | 68 | 319 | 1 |
| forest | moderate | 368 | 78 | 289 | 1 |
| forest | high | 357 | 134 | 223 | 0 |
| shrub | low | 415 | 20 | 265 | 130 |
| shrub | moderate | 410 | 30 | 258 | 122 |
| shrub | high | 406 | 133 | 243 | 30 |
| tall grass | low | 434 | 49 | 381 | 4 |
| tall grass | moderate | 427 | 51 | 373 | 3 |
| tall grass | high | 421 | 195 | 226 | 0 |

**Loam**

| Veg Type | Severity | Total | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|------:|------------------:|------:|------------------:|
| forest | low | 349 | 23 | 324 | 2 |
| forest | moderate | 332 | 32 | 299 | 1 |
| forest | high | 323 | 43 | 280 | 0 |
| shrub | low | 385 | 6 | 351 | 28 |
| shrub | moderate | 380 | 25 | 345 | 10 |
| shrub | high | 378 | 49 | 329 | 0 |
| tall grass | low | 405 | 21 | 381 | 3 |
| tall grass | moderate | 401 | 25 | 374 | 2 |
| tall grass | high | 397 | 53 | 344 | 0 |

**Sand Loam**

| Veg Type | Severity | Total | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|------:|------------------:|------:|------------------:|
| forest | low | 249 | 6 | 243 | 0 |
| forest | moderate | 235 | 6 | 229 | 0 |
| forest | high | 227 | 19 | 208 | 0 |
| shrub | low | 265 | 8 | 257 | 0 |
| shrub | moderate | 263 | 9 | 254 | 0 |
| shrub | high | 261 | 25 | 236 | 0 |
| tall grass | low | 289 | 2 | 287 | 0 |
| tall grass | moderate | 289 | 2 | 287 | 0 |
| tall grass | high | 281 | 12 | 269 | 0 |

**Silt Loam**

| Veg Type | Severity | Total | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|------:|------------------:|------:|------------------:|
| forest | low | 322 | 17 | 305 | 0 |
| forest | moderate | 305 | 18 | 287 | 0 |
| forest | high | 295 | 40 | 255 | 0 |
| shrub | low | 341 | 17 | 318 | 6 |
| shrub | moderate | 338 | 22 | 313 | 3 |
| shrub | high | 335 | 48 | 285 | 2 |
| tall grass | low | 365 | 8 | 356 | 1 |
| tall grass | moderate | 363 | 9 | 354 | 0 |
| tall grass | high | 360 | 18 | 342 | 0 |

#### Texture Pattern Observations

1. **Clay loam** shows the highest sediment response - more events with burned > unburned across all veg types
2. **Sand loam** shows minimal sediment differences - high infiltration capacity reduces erosion even when burned
3. **Shrub anomaly** in clay loam: 130 events where unburned > burned for low severity - suggests baseline shrub parameters produce more erosion than low-severity fire recovery in fine-textured soils
4. **Tall grass runoff** shows high "Equal" counts across all textures at low severity, indicating minimal hydrologic impact from low-severity grass fires

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

## Runoff Events

WEPP computes event runoff from the daily water balance: rainfall intensity and duration drive infiltration, which is limited by effective conductivity (`Keff`) and suction across the wetting front (`Suct`). Surface storage and routing are further adjusted by random roughness (`rrinit`/`Rough`) and cover/residue (`cancov`, `inrcov`, `rilcov`, `sumrtm`, `sumsrm`). These terms evolve with antecedent soil moisture and daily state, so the runoff response is time-varying even with fixed management and soil inputs.

When `ksatadj=1`, WEPP recalculates effective conductivity from saturation fraction (`sat_frac`) and the `ksatfac`/`ksatrec` controls (or enforces `lkeff` for 9003/9005 soils). This makes `Keff` time-varying as soils wet up or dry down. When `ksatadj=0`, `Keff` tracks the surface horizon `ksat` (which is sourced from `avke` in the disturbed lookup).

Suction (`Suct`) is computed from soil texture/porosity and current water content, so it is sensitive to antecedent wetness. Higher `Suct` increases infiltration demand and can suppress runoff; lower `Suct` does the opposite. The event count tables therefore capture not only management/soil differences but also day-to-day moisture state, which is why a minority of events can show undisturbed runoff exceeding burned runoff.

The disturbed parameterization is **directionally correct** at the regime level (burned classes lower cover and typically lower effective conductivity, so runoff and sediment delivery tend to increase), but it does **not guarantee** that every individual event will produce more runoff than the undisturbed case. A dry antecedent state can raise `Suct` and reduce runoff in burned conditions, while a wetter undisturbed state can do the opposite. This is expected behavior in the WEPP hydrology, so comparisons should focus on distributions and seasonal/annual totals rather than a per-event monotonicity assumption.

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

## Testing

The disturbed module has a comprehensive test suite that validates the soil/management parameterization workflow:

```bash
# Run the 48-simulation matrix test (4 textures x 3 veg types x 4 severities)
pytest tests/disturbed/test_disturbed_matrix.py -v

# Analyze results after test completion
python tests/disturbed/analyze_matrix.py
```

Test artifacts:
- `tests/disturbed/test_disturbed_matrix.py` - pytest-based matrix runner
- `tests/disturbed/analyze_matrix.py` - post-run analysis generating event counts and statistics
- `tests/disturbed/conftest.py` - shared fixtures (paths, run directories)
- `tests/disturbed/analysis_results.md` - standalone results summary

### Hillslope ID Manifest

The 48 simulations in the test archive (`disturbed_matrix_results.tar.gz`) map to hillslope IDs as follows.
Files are named `p{id}.sol`, `p{id}.man`, `p{id}.slp`, `p{id}.cli`, `H{id}.ebe.dat`, etc.

ID formula: `texture_idx * 12 + veg_idx * 4 + severity + 1`

| ID | Texture | Veg Type | Severity |
|---:|---------|----------|----------|
| 1 | clay loam | forest | unburned |
| 2 | clay loam | forest | low |
| 3 | clay loam | forest | moderate |
| 4 | clay loam | forest | high |
| 5 | clay loam | shrub | unburned |
| 6 | clay loam | shrub | low |
| 7 | clay loam | shrub | moderate |
| 8 | clay loam | shrub | high |
| 9 | clay loam | tall grass | unburned |
| 10 | clay loam | tall grass | low |
| 11 | clay loam | tall grass | moderate |
| 12 | clay loam | tall grass | high |
| 13 | loam | forest | unburned |
| 14 | loam | forest | low |
| 15 | loam | forest | moderate |
| 16 | loam | forest | high |
| 17 | loam | shrub | unburned |
| 18 | loam | shrub | low |
| 19 | loam | shrub | moderate |
| 20 | loam | shrub | high |
| 21 | loam | tall grass | unburned |
| 22 | loam | tall grass | low |
| 23 | loam | tall grass | moderate |
| 24 | loam | tall grass | high |
| 25 | sand loam | forest | unburned |
| 26 | sand loam | forest | low |
| 27 | sand loam | forest | moderate |
| 28 | sand loam | forest | high |
| 29 | sand loam | shrub | unburned |
| 30 | sand loam | shrub | low |
| 31 | sand loam | shrub | moderate |
| 32 | sand loam | shrub | high |
| 33 | sand loam | tall grass | unburned |
| 34 | sand loam | tall grass | low |
| 35 | sand loam | tall grass | moderate |
| 36 | sand loam | tall grass | high |
| 37 | silt loam | forest | unburned |
| 38 | silt loam | forest | low |
| 39 | silt loam | forest | moderate |
| 40 | silt loam | forest | high |
| 41 | silt loam | shrub | unburned |
| 42 | silt loam | shrub | low |
| 43 | silt loam | shrub | moderate |
| 44 | silt loam | shrub | high |
| 45 | silt loam | tall grass | unburned |
| 46 | silt loam | tall grass | low |
| 47 | silt loam | tall grass | moderate |
| 48 | silt loam | tall grass | high |

Results from the test matrix are summarized in the [Test Matrix Analysis Results](#test-matrix-analysis-results-february-2026) section above.

## Further Reading

- `wepppy/wepp/management/AGENTS.md` (management file conventions)
- `wepppy/wepp/soils/utils/README.md` (soil migration utilities)
- `wepppy/weppcloud/routes/usersum/weppcloud/disturbed-land-soil-lookup.md` (parameter definitions)
- `docs/ui-docs/control-ui-styling/sbs_controls_behavior.md` (SBS control behavior)
- `tests/disturbed/` (disturbed matrix test suite and analysis)
