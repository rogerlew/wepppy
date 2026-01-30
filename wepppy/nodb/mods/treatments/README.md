# Treatments Module

> Apply post-fire rehabilitation and forest management treatments to WEPPcloud watersheds.

## Overview

The Treatments module enables land managers and hydrologists to model how rehabilitation treatments affect erosion and runoff in fire-affected or forested landscapes. Treatments modify the landuse management and soil properties of selected hillslopes before WEPP model execution.

**Who uses this:**
- **BAER Teams**: Evaluate mulch application effectiveness after wildfires
- **Forest Service Planners**: Compare thinning strategies and prescribed fire options
- **Hydrologists**: Model erosion changes under different treatment scenarios

**What you can do:**
- Apply mulch at different application rates to reduce post-fire erosion
- Simulate prescribed fire as a pre-emptive forest treatment
- Evaluate forest thinning with various harvest methods
- Upload custom treatment maps to apply treatments spatially

## Getting Started (Web Interface)

### Enabling the Treatments Module

Treatments is an optional module that must be added to your project:

1. Open your WEPPcloud project
2. Click the **Mods** dropdown menu in the control panel
3. Select **Treatments** from the list
4. The Treatments panel will appear in your project controls

### Choosing an Application Mode

The Treatments panel offers two ways to apply treatments:

| Mode | Best For |
|------|----------|
| **Specify Hillslopes** | Applying a single treatment to selected hillslopes interactively |
| **Upload Treatment Map** | Applying different treatments across the watershed using a prepared GIS raster |

### Mode 1: Specify Hillslopes

1. Select **Specify Hillslopes** in the Treatments panel
2. On the map, click hillslopes you want to treat (they will highlight)
3. Choose a treatment from the dropdown menu
4. Click **Build Treatments**

This mode is useful for quick analyses or when you want to treat a small number of specific hillslopes.

### Mode 4: Upload Treatment Map

1. Select **Upload Treatment Map** in the Treatments panel
2. Click the file upload button and select your treatment raster (`.tif` or `.img`)
3. Click **Build Treatments**

The system will:
- Reproject your raster to align with the watershed
- Assign treatments to hillslopes based on the most common pixel value within each hillslope
- Apply the appropriate management and soil changes

See [Preparing Treatment Maps](#preparing-treatment-maps-for-upload) for detailed instructions on creating treatment rasters.

## Understanding Treatment Types

### Mulch Treatments

Mulch application increases ground cover to reduce erosion on burned hillslopes. Three application rates are available:

| Treatment | Application Rate | Typical Use |
|-----------|------------------|-------------|
| mulch_15 | 0.5 tons/acre | Light application, cost-effective |
| mulch_30 | 1.0 tons/acre | Standard BAER recommendation |
| mulch_60 | 2.0 tons/acre | High-priority areas, steep slopes |

**How ground cover changes:**

Mulch increases ground cover following a saturating response—initial applications produce large gains, but returns diminish as cover approaches 100%.

| Initial Ground Cover | mulch_15 (0.5 t/ac) | mulch_30 (1.0 t/ac) | mulch_60 (2.0 t/ac) |
|----------------------|---------------------|---------------------|---------------------|
| 0% (bare) | 18% | 43% | 71% |
| 10% | 27% | 49% | 74% |
| 30% | 43% | 60% | 80% |
| 60% | 67% | 77% | 89% |

*Example*: A high-severity burn area with 10% residual ground cover treated with mulch_30 (1.0 tons/acre) would increase to approximately 49% ground cover.

> **Important**: Mulch treatments only apply to hillslopes classified as fire-disturbed (high, moderate, or low severity). Non-fire hillslopes are skipped even if selected or included in your treatment map.

### Thinning Treatments

Thinning removes trees to reduce fuel loads and improve forest health. Treatments are named `thinning_{canopy}_{ground_cover}`:

- **First number**: Target canopy cover after thinning (40% = aggressive, 65% = moderate)
- **Second number**: Ground cover retention based on harvest method

| Treatment | Canopy | Ground Cover | Harvest Method | Best For |
|-----------|--------|--------------|----------------|----------|
| thinning_40_93 | 40% | 93% | Cable yarding | Steep slopes (>35%) |
| thinning_40_90 | 40% | 90% | Forwarder | Moderate slopes |
| thinning_40_85 | 40% | 85% | Skidder | Gentle slopes |
| thinning_40_75 | 40% | 75% | Ground-based | Flat, accessible |
| thinning_65_93 | 65% | 93% | Cable yarding | Steep slopes (>35%) |
| thinning_65_90 | 65% | 90% | Forwarder | Moderate slopes |
| thinning_65_85 | 65% | 85% | Skidder | Gentle slopes |
| thinning_65_75 | 65% | 75% | Ground-based | Flat, accessible |

Higher ground cover retention means less soil disturbance from equipment. Choose based on your terrain and available equipment.

> **Important**: Thinning treatments only apply to hillslopes classified as forest. Other vegetation types are skipped.

### Prescribed Fire

Prescribed fire applies low-intensity burns appropriate for the vegetation type:

| Treatment | Description |
|-----------|-------------|
| prescribed_fire | Vegetation-appropriate prescribed burn management |

The system automatically selects the correct fire intensity based on whether the hillslope is forest, shrub, or grass.

## Preparing Treatment Maps for Upload

This section guides GIS users through creating treatment rasters for Mode 4.

### Raster Requirements

| Requirement | Details |
|-------------|---------|
| **Format** | GeoTIFF (`.tif`) or ERDAS Imagine (`.img`) |
| **Data type** | Integer (Int16, Int32, or UInt16 recommended) |
| **Spatial reference** | Any valid CRS (will be reprojected to match watershed) |
| **Pixel values** | Must match treatment codes from the table below |
| **NoData** | Use 0 or any non-treatment value for untreated areas |

### Treatment Pixel Values

Encode your raster with these integer values where treatments should apply:

**Mulch:**

| Pixel Value | Treatment | Application Rate |
|-------------|-----------|------------------|
| `139` | mulch_15 | 0.5 tons/acre |
| `140` | mulch_30 | 1.0 tons/acre |
| `141` | mulch_60 | 2.0 tons/acre |

**Prescribed Fire:**

| Pixel Value | Treatment |
|-------------|-----------|
| `142` | prescribed_fire |

**Thinning:**

| Pixel Value | Treatment | Canopy | Ground Cover |
|-------------|-----------|--------|--------------|
| `115` | thinning_40_93 | 40% | 93% (Cable) |
| `116` | thinning_40_90 | 40% | 90% (Forwarder) |
| `117` | thinning_40_85 | 40% | 85% (Skidder) |
| `124` | thinning_40_75 | 40% | 75% (Ground-based) |
| `125` | thinning_65_75 | 65% | 75% (Ground-based) |
| `126` | thinning_65_85 | 65% | 85% (Skidder) |
| `127` | thinning_65_90 | 65% | 90% (Forwarder) |
| `128` | thinning_65_93 | 65% | 93% (Cable) |

### Creating a Treatment Map in QGIS

*(These instructions are provided as guidance; your workflow may vary)*

1. **Create a polygon layer for treatment areas**
   ```
   Layer → Create Layer → New Shapefile Layer
   - Geometry type: Polygon
   - Add field: "treatment" (Integer)
   ```

2. **Draw treatment areas and assign pixel values**
   - Digitize polygons around areas you want to treat
   - Set the `treatment` attribute to the pixel value from the table above (e.g., 140 for mulch_30)

3. **Convert to raster**
   ```
   Raster → Conversion → Rasterize (Vector to Raster)
   - Input layer: your treatment polygons
   - Field to use for burn-in: treatment
   - Output raster size: ~10m resolution (or match your DEM)
   - NoData value: 0
   - Output format: GeoTIFF
   ```

4. **Verify the output**
   - Check that pixel values match your intended treatments
   - Confirm the raster has a valid coordinate system (Layer Properties → Information)

### Creating a Treatment Map in ArcGIS Pro

*(These instructions are provided as guidance; your workflow may vary)*

1. **Create polygon feature class with treatment field**
   ```
   Analysis → Tools → Create Feature Class
   - Add field "TreatmentCode" (Short Integer)
   ```

2. **Draw polygons and assign treatment codes**
   - Edit the attribute table to enter pixel values from the treatment table

3. **Convert to raster**
   ```
   Analysis → Tools → Polygon to Raster
   - Value field: TreatmentCode
   - Cell size: ~10m (or match watershed resolution)
   ```

4. **Export as GeoTIFF**
   ```
   Right-click layer → Data → Export Raster
   - Format: TIFF
   ```

### How Treatment Maps Are Processed

When you upload a treatment map:

1. **Reprojection**: Your raster is automatically reprojected and resampled to align with the watershed
2. **Hillslope assignment**: For each hillslope, the most common (modal) treatment pixel value becomes that hillslope's treatment
3. **Filtering**: Pixel values that don't match valid treatment codes are ignored
4. **Application**: Treatments are applied based on vegetation type (mulch requires fire disturbance, thinning requires forest)

> **Tip**: If a hillslope contains multiple treatment types, only the dominant one applies. For precise treatment boundaries, consider refining your watershed delineation.

## Troubleshooting

| Problem | Likely Cause | Solution |
|---------|--------------|----------|
| "Not a valid gdal raster file" | Missing coordinate system | Re-export your raster with an explicit CRS |
| Treatments not appearing | Pixel values don't match codes | Verify your values against the treatment table |
| Wrong hillslopes treated | Raster misaligned | Ensure your raster covers the watershed extent |
| Mulch not applying | Hillslope not fire-disturbed | Mulch only works on fire severity classes |
| Thinning not applying | Hillslope not forest | Thinning only works on forest vegetation |

## Where Treatment Data Is Stored

Treatment files are stored in the `treatments/` directory within your project:

```
your_project/
└── treatments/
    ├── [uploaded raster]     # Your original treatment map
    └── treatments.tif        # Aligned treatment map (after processing)
```

Treatment assignments are saved in the project and will persist when you reopen it.

---

## Developer Notes

The following sections contain technical details for developers working with the Treatments module programmatically.

### Key Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `mode` | `TreatmentsMode` | Current application mode (UserDefinedSelection=1 or UserDefinedMap=4) |
| `treatments_domlc_d` | `Dict[str, str]` | Maps topaz hillslope IDs to treatment keys |
| `treatments_dir` | `str` | Path to treatments storage directory |
| `treatments_map` | `str` | Path to aligned treatment raster (when using map mode) |
| `treatments_lookup` | `Dict[str, str]` | Valid treatment options from landuse mapping |

### Python API Usage

**Basic treatment application:**

```python
from wepppy.nodb.mods.treatments import Treatments, TreatmentsMode

# Get the singleton instance for a working directory
treatments = Treatments.getInstance(wd)

# Set application mode
treatments.mode = TreatmentsMode.UserDefinedSelection

# Define hillslope-treatment assignments
# Keys are topaz hillslope IDs, values are treatment keys from disturbed.json
treatments.treatments_domlc_d = {
    '11': '140',   # mulch_30
    '21': '141',   # mulch_60
    '31': '142'    # prescribed_fire
}

# Apply treatments to landuse and soils
treatments.build_treatments()
```

**Using treatment maps (Mode 4):**

```python
treatments = Treatments.getInstance(wd)
treatments.mode = TreatmentsMode.UserDefinedMap

# Validate and process uploaded treatment raster
treatments.validate('my_treatment_map.tif')

# Build treatments using the extracted hillslope-treatment mapping
treatments.build_treatments()
```

**Querying valid treatments:**

```python
treatments = Treatments.getInstance(wd)

# Get list of treatment keys marked IsTreatment=True in disturbed.json
valid_keys = treatments.get_valid_treatment_keys()
# e.g., ['115', '116', '117', '124', '125', '126', '127', '128',
#        '139', '140', '141', '142']

# Get lookup dictionary for UI display (DisturbedClass -> Key)
lookup = treatments.treatments_lookup
# e.g., {'mulch_15': '139', 'mulch_30': '140', ...}
```

### Mulch Ground Cover Model

Mulch treatments modify ground cover using a calibrated Hill-type saturation model:

```
G(m) = L - (L - G0) / (1 + (a*m)^b)
```

Where:
- `G0` = initial ground cover (%)
- `m` = mulch application (tons/acre)
- `L` = 100% (saturation limit)
- `a` = 0.847, `b` = 1.737 (calibrated parameters)

Implementation: `mulch_application.py`

### Integration Points

**Dependencies:**
- `wepppy.nodb.core.landuse.Landuse` - Landuse mapping and management registry
- `wepppy.nodb.core.soils.Soils` - Soil files and hillslope-soil assignments
- `wepppy.nodb.mods.disturbed.Disturbed` - Disturbed class lookups and soil rules
- `wepppy.nodb.core.watershed.Watershed` - Raster alignment for treatment maps

**API Endpoints:**
- Flask: `/runs/<runid>/<config>/tasks/set_treatments_mode/`
- FastAPI: `/api/runs/{runid}/{config}/build-treatments`
- UI Template: `templates/controls/treatments_pure.htm`

### Persistence

| Property | Value |
|----------|-------|
| Filename | `treatments.nodb` |
| Format | JSON (jsonpickle serialized) |
| Redis cache | DB 13, 72-hour TTL |
| Locking | Required for all mutations |

### Code Organization

```
wepppy/nodb/mods/treatments/
├── __init__.py           # Public API exports
├── treatments.py         # Main Treatments class
├── mulch_application.py  # Ground cover response model
└── README.md             # This file
```

### Key Patterns

- **Singleton per working directory**: `Treatments.getInstance(wd)` returns cached instance
- **@nodb_setter decorator**: Wraps property setters with automatic locking, logging, and persistence
- **Context manager locking**: Use `with treatments.locked():` for manual transaction control
- **Strategy dispatch**: `_apply_treatment()` routes to `_apply_mulch()`, `_apply_prescribed_fire()`, or `_apply_thinning()`

### Testing

Tests: `tests/weppcloud/routes/test_treatments_bp.py`

### Known Limitations

- Mulch treatments only apply to fire-disturbed hillslopes
- Treatment map mode requires the watershed `subwta` raster for alignment
- The module is marked "Experimental" in the UI

## Further Reading

- [NoDb README](../../README.md) - Core NoDb controller architecture
- [AGENTS.md](../../AGENTS.md) - Locking and cache refresh semantics
- [Disturbed Module](../disturbed/) - Fire severity and disturbed class handling
- [disturbed.json](../../../wepp/management/data/disturbed.json) - Treatment key definitions
- [Ground Cover Model](https://chatgpt.com/share/689688e1-f3b4-8009-bc94-ffdcdca8e71f) - Derivation of mulch response parameters
