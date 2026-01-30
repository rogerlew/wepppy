# Treatments NoDb Controller

> Manages post-fire and forest treatment application for WEPPcloud runs, including mulch, prescribed fire, and thinning operations.

> **See also:** [AGENTS.md](../../AGENTS.md) for locking and cache refresh semantics.

## Overview

The Treatments module enables land managers and hydrologists to apply rehabilitation treatments to fire-affected or forest landscapes within WEPPcloud. Treatments modify the landuse management and soil properties of selected hillslopes, allowing users to model erosion and runoff under various post-fire intervention scenarios.

This module fits into the WEPPcloud workflow after burn severity assessment (BAER/SBS) and before WEPP model execution. It operates as an optional modification layer—users can skip treatments entirely or apply them selectively to specific hillslopes.

**Primary use cases:**
- Modeling mulch application effects on ground cover recovery
- Simulating prescribed fire as a pre-emptive treatment
- Evaluating forest thinning impacts on hillslope erosion

**Key capabilities:**
- Two application modes: individual hillslope selection or raster-based treatment maps
- Mulch treatment with calibrated ground cover response model
- Prescribed fire and thinning treatments with disturbed-class-specific management files
- Automatic soil property modifications based on treatment type and soil texture

## Key Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `mode` | `TreatmentsMode` | Current application mode (UserDefinedSelection=1 or UserDefinedMap=4) |
| `treatments_domlc_d` | `Dict[str, str]` | Maps topaz hillslope IDs to treatment keys |
| `treatments_dir` | `str` | Path to treatments storage directory |
| `treatments_map` | `str` | Path to aligned treatment raster (when using map mode) |
| `treatments_lookup` | `Dict[str, str]` | Valid treatment options from landuse mapping |

## Usage

### Basic Treatment Application

```python
from wepppy.nodb.mods.treatments import Treatments, TreatmentsMode

# Get the singleton instance for a working directory
treatments = Treatments.getInstance(wd)

# Set application mode
treatments.mode = TreatmentsMode.UserDefinedSelection

# Define which hillslopes receive which treatments
# Keys are topaz hillslope IDs, values are treatment keys from disturbed.json
treatments.treatments_domlc_d = {
    '11': '140',   # mulch_30
    '21': '141',   # mulch_60
    '31': '142'    # prescribed_fire
}

# Apply treatments to landuse and soils
treatments.build_treatments()
```

### Using Treatment Maps (Mode 4)

```python
treatments = Treatments.getInstance(wd)
treatments.mode = TreatmentsMode.UserDefinedMap

# Validate and process uploaded treatment raster
# The raster is reprojected to align with the watershed
treatments.validate('my_treatment_map.tif')

# Build treatments using the extracted hillslope-treatment mapping
treatments.build_treatments()
```

### Querying Valid Treatments

```python
treatments = Treatments.getInstance(wd)

# Get list of treatment keys marked IsTreatment=True in disturbed.json
valid_keys = treatments.get_valid_treatment_keys()
# e.g., ['115', '116', '117', '124', '125', '126', '127', '128',  # thinning variants
#        '139', '140', '141', '142']                              # mulch + prescribed_fire

# Get lookup dictionary for UI display (DisturbedClass -> Key)
lookup = treatments.treatments_lookup
# e.g., {'mulch_15': '139', 'mulch_30': '140', 'mulch_60': '141',
#        'prescribed_fire': '142', 'thinning_40_90': '116', ...}
```

## Preparing Treatment Maps for Upload

This section provides guidance for GIS users preparing treatment rasters for Mode 4 (Upload Treatment Map).

### Raster Requirements

| Requirement | Details |
|-------------|---------|
| **Format** | GeoTIFF (`.tif`) or ERDAS Imagine (`.img`) |
| **Data type** | Integer (Int16, Int32, or UInt16 recommended) |
| **Spatial reference** | Any valid CRS (will be reprojected to match watershed) |
| **Pixel values** | Must match treatment keys from the table below |
| **NoData** | Use 0 or any non-treatment value for untreated areas |

### Valid Treatment Pixel Values (US Interface)

The following pixel values are recognized as treatments when using the default `disturbed.json` mapping. Encode your raster with these integer values where treatments should be applied:

**Mulch Treatments:**

| Pixel Value | Treatment | Application Rate | Description |
|-------------|-----------|------------------|-------------|
| `139` | mulch_15 | 0.5 tons/acre | Light mulch application |
| `140` | mulch_30 | 1.0 tons/acre | Moderate mulch application |
| `141` | mulch_60 | 2.0 tons/acre | Heavy mulch application |

Mulch application increases ground cover using a **saturating Hill-type response model**. The relationship is non-linear—initial mulch applications produce large gains in ground cover, but returns diminish as cover approaches 100%.

**Expected ground cover (%) after mulch application:**

| Initial Ground Cover | mulch_15 (0.5 t/ac) | mulch_30 (1.0 t/ac) | mulch_60 (2.0 t/ac) |
|----------------------|---------------------|---------------------|---------------------|
| 0% (bare) | 18% | 43% | 71% |
| 10% | 27% | 49% | 74% |
| 30% | 43% | 60% | 80% |
| 60% | 67% | 77% | 89% |
| 85% | 88% | 91% | 96% |

*Example*: A high-severity burn area with 10% residual ground cover treated with `mulch_30` (1.0 tons/acre) would increase to approximately 49% ground cover.

> **Note**: Mulch treatments only modify hillslopes currently classified as fire-disturbed (high/moderate/low severity). Non-fire hillslopes are skipped even if included in your treatment map.

**Prescribed Fire:**

| Pixel Value | Treatment | Description |
|-------------|-----------|-------------|
| `142` | prescribed_fire | Applies vegetation-appropriate prescribed fire management |

**Thinning Treatments:**

| Pixel Value | Treatment | Target Canopy | Ground Cover | Harvest Method |
|-------------|-----------|---------------|--------------|----------------|
| `115` | thinning_40_93 | 40% | 93% | Cable yarding |
| `116` | thinning_40_90 | 40% | 90% | Forwarder |
| `117` | thinning_40_85 | 40% | 85% | Skidder |
| `124` | thinning_40_75 | 40% | 75% | Ground-based (max disturbance) |
| `125` | thinning_65_75 | 65% | 75% | Ground-based (max disturbance) |
| `126` | thinning_65_85 | 65% | 85% | Skidder |
| `127` | thinning_65_90 | 65% | 90% | Forwarder |
| `128` | thinning_65_93 | 65% | 93% | Cable yarding |

### Treatment Naming Conventions

#### Mulch Treatments (`mulch_15`, `mulch_30`, `mulch_60`)

The number indicates the **application rate in lbs/acre ÷ 30**, which converts to tons/acre:

| Name | Calculation | Application Rate |
|------|-------------|------------------|
| `mulch_15` | 15 ÷ 30 = 0.5 | 0.5 tons/acre |
| `mulch_30` | 30 ÷ 30 = 1.0 | 1.0 tons/acre |
| `mulch_60` | 60 ÷ 30 = 2.0 | 2.0 tons/acre |

Mulch treatments only apply to **fire-disturbed hillslopes**. If a hillslope's current disturbed class is not one of the fire severity classes (e.g., `forest high sev fire`, `shrub moderate sev fire`, `grass low sev fire`), the mulch treatment will be skipped for that hillslope.

#### Thinning Treatments (`thinning_XX_YY`)

The naming convention is `thinning_{target_canopy}_{ground_cover}`:

- **First number (XX)**: Target canopy cover percentage after thinning
  - `40` = Aggressive thinning to 40% canopy cover
  - `65` = Moderate thinning to 65% canopy cover

- **Second number (YY)**: Ground cover retention percentage, determined by harvest method
  - `93` = Cable yarding (logs suspended, minimal ground disturbance)
  - `90` = Forwarder (logs carried on machine, low ground disturbance)
  - `85` = Skidder (logs dragged, moderate ground disturbance)
  - `75` = Ground-based with maximum soil disturbance

Higher ground cover retention (93%) means less soil disturbance and lower erosion potential. Choose based on terrain and equipment constraints:

| Terrain | Recommended Method | Ground Cover |
|---------|-------------------|--------------|
| Steep slopes (>35%) | Cable yarding | 93% |
| Moderate slopes | Forwarder | 90% |
| Gentle slopes | Skidder | 85% |
| Flat, accessible | Ground-based | 75% |

### Step-by-Step Map Preparation

#### Using QGIS (untested, according to Claude)

1. **Create or load your treatment area polygon layer**
   ```
   Layer → Create Layer → New Shapefile Layer
   - Geometry type: Polygon
   - Add field: "treatment" (Integer)
   ```

2. **Digitize treatment areas and assign pixel values**
   - Draw polygons for each treatment zone
   - Set the `treatment` attribute to the appropriate pixel value (e.g., 140 for mulch_30)

3. **Rasterize the vector layer**
   ```
   Raster → Conversion → Rasterize (Vector to Raster)
   - Input layer: your treatment polygons
   - Field to use for burn-in: treatment
   - Output raster size: Match your DEM or use ~10m resolution
   - NoData value: 0
   - Output format: GeoTIFF
   ```

4. **Verify the output**
   - Check that pixel values match the treatment key table
   - Ensure the raster has a valid CRS (check Layer Properties → Information)

#### Using ArcGIS Pro (untested, according to Claude)

1. **Create treatment polygons with integer field**
   ```
   Analysis → Tools → Create Feature Class
   - Add field "TreatmentCode" (Short Integer)
   ```

2. **Assign treatment codes to polygons**
   - Edit the attribute table
   - Enter pixel values from the treatment key table

3. **Convert to raster**
   ```
   Analysis → Tools → Polygon to Raster
   - Value field: TreatmentCode
   - Cell size: Match watershed resolution or ~10m
   ```

4. **Export as GeoTIFF**
   ```
   Right-click layer → Data → Export Raster
   - Format: TIFF
   - Ensure CRS is defined
   ```

### Processing Behavior

When you upload a treatment map:

1. **Reprojection**: The raster is automatically reprojected and resampled to align with the watershed boundary (`subwta` raster)

2. **Hillslope assignment**: For each hillslope, the **modal (most common)** treatment pixel value within that hillslope becomes its assigned treatment

3. **Filtering**: Pixel values that don't match valid treatment keys are ignored—those hillslopes receive no treatment

4. **Mixed treatments**: If a hillslope contains multiple treatment types, only the dominant one applies. Consider subdividing complex treatment areas into separate hillslopes during watershed delineation if precise treatment boundaries are needed.

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Not a valid gdal raster file" | Missing CRS or corrupt file | Re-export with explicit CRS assignment |
| Treatments not applying | Pixel values don't match keys | Verify values against treatment key table |
| Wrong hillslopes treated | Raster misaligned | Ensure raster covers watershed extent |
| Mulch skipped | Hillslope not fire-disturbed | Mulch only applies to fire severity classes |

## Treatment Types

### Valid Treatment Keys

Treatment keys are defined in `wepppy/wepp/management/data/disturbed.json` with `IsTreatment=true`:

| Key | DisturbedClass | Description |
|-----|----------------|-------------|
| `139` | `mulch_15` | Mulch 15 |
| `140` | `mulch_30` | Mulch 30 |
| `141` | `mulch_60` | Mulch 60 |
| `142` | `prescribed_fire` | Prescribed Fire |
| `115` | `thinning_40_93` | Thinning 40/93 Cover (Cable) |
| `116` | `thinning_40_90` | Thinning 40/90 Cover (Forwarder) |
| `117` | `thinning_40_85` | Thinning 40/85 Cover (Skidder) |
| `124` | `thinning_40_75` | Thinning 40/75 Cover |
| `125` | `thinning_65_75` | Thinning 65/75 Cover |
| `126` | `thinning_65_85` | Thinning 65/85 Cover (Skidder) |
| `127` | `thinning_65_90` | Thinning 65/90 Cover (Forwarder) |
| `128` | `thinning_65_93` | Thinning 65/93 Cover (Cable) |

### Mulch Application

Mulch treatments modify the initial ground cover (inrcov) and rill cover (rilcov) values in management files using a calibrated Hill-type saturation model:

```
G(m) = L - (L - G0) / (1 + (a*m)^b)
```

Where:
- `G0` = initial ground cover (%)
- `m` = mulch application (tons/acre) — see [naming conventions](#mulch-treatments-mulch_15-mulch_30-mulch_60) for rate calculation
- `L` = 100% (saturation limit)
- `a` = 0.847, `b` = 1.737 (calibrated parameters)

**Predicted ground cover (%) by mulch application rate:**

| Initial Cover (%) | mulch_15 (0.5 t/ac) | mulch_30 (1.0 t/ac) | mulch_60 (2.0 t/ac) |
|-------------------|---------------------|---------------------|---------------------|
| 0 | 18.4 | 42.9 | 71.4 |
| 30 | 42.9 | 60.0* | 80.0* |
| 60 | 67.3 | 77.1 | 88.6 |
| 85 | 87.8 | 91.4 | 95.7 |

*Calibration points

**Applicability**: Mulch treatments only apply to fire-disturbed hillslopes with these disturbed classes:
- `grass high sev fire`, `grass moderate sev fire`, `grass low sev fire`
- `shrub high sev fire`, `shrub moderate sev fire`, `shrub low sev fire`
- `forest high sev fire`, `forest moderate sev fire`, `forest low sev fire`

Hillslopes without fire disturbance are silently skipped.

### Prescribed Fire

Prescribed fire treatments replace the existing management with fire-adapted versions based on vegetation type:
- Forest → forest_prescribed_fire
- Shrub → shrub_prescribed_fire
- Grass → grass_prescribed_fire

### Thinning

Thinning treatments apply to forest-type landuses (`disturbed_class = 'forest'`) and substitute specialized management files that model post-harvest conditions.

See [thinning naming conventions](#thinning-treatments-thinning_xx_yy) for detailed explanation of the `thinning_XX_YY` format (target canopy % and ground cover retention by harvest method).

**Applicability**: Only hillslopes with `disturbed_class = 'forest'` will receive thinning treatments. Other vegetation types are skipped.

## Integration Points

### Dependencies

- **Landuse** (`wepppy.nodb.core.landuse.Landuse`): Provides landuse mapping, management registry, and hillslope assignments
- **Soils** (`wepppy.nodb.core.soils.Soils`): Manages soil files and hillslope-soil assignments
- **Disturbed** (`wepppy.nodb.mods.disturbed.Disturbed`): Supplies disturbed class lookups and soil replacement rules
- **Watershed** (`wepppy.nodb.core.watershed.Watershed`): Provides raster alignment for treatment maps

### Consumers

- **Flask Blueprint**: `/runs/<runid>/<config>/tasks/set_treatments_mode/`
- **FastAPI Router**: `/api/runs/{runid}/{config}/build-treatments`
- **UI Template**: `templates/controls/treatments_pure.htm`

### RQ Tasks

Treatment building is typically enqueued via `build_landuse_rq` for background processing with progress tracking.

## Persistence

| Property | Value |
|----------|-------|
| Filename | `treatments.nodb` |
| Format | JSON (jsonpickle serialized) |
| Redis cache | DB 13, 72-hour TTL |
| Locking | Required for all mutations |

The treatments directory (`{wd}/treatments/`) stores:
- Uploaded treatment rasters (original)
- Aligned treatment map (`treatments.tif`)

## Web Interface

The treatments control panel (`treatments_pure.htm`) provides:

1. **Mode Selection**: Radio buttons for "Specify Hillslopes" (Mode 1) or "Upload Treatment Map" (Mode 4)
2. **Hillslope Selection Panel** (Mode 1): Dropdown to select treatment type for highlighted hillslopes
3. **Map Upload Panel** (Mode 4): File input accepting `.tif` or `.img` rasters, with collapsible reference table of valid treatment class values
4. **Build Button**: Triggers treatment application with lock indicator
5. **Job Hint**: Displays progress messages during background processing

## Developer Notes

### Code Organization

```
wepppy/nodb/mods/treatments/
├── __init__.py           # Public API exports
├── treatments.py         # Main Treatments class (525 lines)
├── mulch_application.py  # Ground cover response model (92 lines)
└── README.md             # This file
```

### Key Patterns

- **Singleton per working directory**: `Treatments.getInstance(wd)` returns cached instance
- **@nodb_setter decorator**: Wraps property setters with automatic locking, logging, and persistence
- **Context manager locking**: Use `with treatments.locked():` for manual transaction control
- **Strategy dispatch**: `_apply_treatment()` routes to `_apply_mulch()`, `_apply_prescribed_fire()`, or `_apply_thinning()`

### Transient vs Persisted Fields

| Field | Persisted | Notes |
|-------|-----------|-------|
| `_mode` | Yes | Stored as integer |
| `_treatments_domlc_d` | Yes | Treatment assignments |
| `_treatments` | Yes | (Reserved for future use) |
| `treatments_dir` | No | Computed from `wd` |
| `treatments_map` | No | Computed from `treatments_dir` |

### Testing

Tests are located at `tests/weppcloud/routes/test_treatments_bp.py`. Key test scenarios:
- Mode setting via Flask blueprint
- Treatment dictionary validation
- Mulch ground cover calculations
- Raster validation and alignment

### Known Limitations

- Mulch treatments only apply to fire-disturbed hillslopes; non-disturbed areas are silently skipped
- Treatment map mode requires the watershed `subwta` raster to exist for alignment
- The module is marked "Experimental" in the UI

## Further Reading

- [NoDb README](../../README.md) - Core NoDb controller architecture
- [Disturbed Module](../disturbed/) - Fire severity and disturbed class handling
- [Landuse Core](../../core/) - Landuse management and mapping system
- [disturbed.json](../../../wepp/management/data/disturbed.json) - Treatment key definitions and mappings
- [Ground Cover Model](https://chatgpt.com/share/689688e1-f3b4-8009-bc94-ffdcdca8e71f) - Derivation of mulch response parameters
