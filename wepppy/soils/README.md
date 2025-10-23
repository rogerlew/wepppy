# Soils Package
> Soil data acquisition, processing, and WEPP soil parameter file generation

> **See also:** [AGENTS.md](../../AGENTS.md#soil-integration) for soil integration patterns and [ssurgo/ssurgo.md](ssurgo/ssurgo.md) for SSURGO-to-WEPP conversion details.

## Overview

The `wepppy.soils` package provides soil data integration for the WEPP erosion model, bridging USDA soil databases (SSURGO, STATSGO2) with WEPP's soil parameterization requirements. The package handles spatial soil data acquisition, dominant soil type extraction per watershed element, hydraulic property estimation via Rosetta pedotransfer functions, and generation of WEPP-formatted soil input files.

**Key Capabilities:**
- Query USDA SSURGO (Soil Survey Geographic Database) and STATSGO2 (State Soil Geographic Database)
- Extract dominant soil types from spatial maps (raster or vector)
- Apply Rosetta pedotransfer functions for missing hydraulic parameters
- Generate WEPP soil files (versions 7778, 2006.2, 9002, 9003, 9005)
- Compute baseline erodibility parameters (interrill, rill, critical shear)
- Cache soil data locally to minimize web service calls

**System Integration:**
This package is consumed by the `Soils` NoDb controller (`wepppy.nodb.core.soils`), which orchestrates soil assignment across watershed elements. The controller determines which soil database to use (SSURGO vs STATSGO2), manages spatial overlays, and invokes the appropriate builder classes.

**Primary Users:**
- WEPPcloud run orchestration (via Soils NoDb controller)
- Hydrologists and land managers configuring watershed models
- Developers extending soil data sources or parameter estimation methods

## Components

### SSURGO Integration (`ssurgo/`)

The SSURGO subpackage is the primary interface to USDA soil databases:

**Core Classes:**
- `SurgoSoilCollection` - Manages SSURGO data acquisition, caching, and WEPP soil file generation for multiple map unit keys (mukeys)
- `WeppSoil` - Represents a single WEPP soil file built from SSURGO component and horizon data
- `Horizon` - Individual soil layer with computed WEPP parameters (erodibility, conductivity, anisotropy)
- `SurgoMap` - Spatial soil map interface for extracting mukeys from geographic queries
- `StatsgoSpatial` - STATSGO2 spatial map interface (coarse resolution, national coverage)

**See:** [ssurgo/ssurgo.md](ssurgo/ssurgo.md) for comprehensive technical documentation on SSURGO-to-WEPP conversion.

### Spatial Soil Maps

**SurgoMap** - High-resolution soil polygons
- Data source: USDA NRCS SSURGO web services
- Resolution: 1:12,000 to 1:63,360 (field scale)
- Coverage: County-level, varies by region
- Use case: Detailed watershed modeling in surveyed areas

**StatsgoSpatial** - Coarse-resolution soil grids
- Data source: STATSGO2 database
- Resolution: 1:250,000 (regional scale)
- Coverage: Complete CONUS, Alaska, Hawaii, Puerto Rico
- Use case: Large watersheds, unsurveyed regions, national-scale analysis

## Workflow

### 1. Spatial Soil Query
Extract dominant soil types for each watershed subcatchment:

```python
from wepppy.soils.ssurgo import SurgoMap

# Query SSURGO for watershed extent
surgo_map = SurgoMap(extent=[xmin, ymin, xmax, ymax])

# Extract dominant mukey per subcatchment polygon
dominant_mukeys = surgo_map.get_dominant_mukeys_for_subcatchments(
    subcatchment_polygons
)
```

### 2. Soil Data Acquisition
Fetch SSURGO component and horizon data for identified mukeys:

```python
from wepppy.soils.ssurgo import SurgoSoilCollection

# Build soil collection from mukeys
ssc = SurgoSoilCollection(mukeys=[2485028, 2485029, 2485030])

# Query SSURGO web service and build WeppSoil objects
ssc.makeWeppSoils(
    initial_sat=0.75,      # Initial saturation (75%)
    ksflag=True,            # Enable WEPP conductivity adjustments
    max_workers=4           # Parallel processing
)
```

### 3. WEPP Soil File Generation
Write WEPP-formatted soil input files:

```python
# Generate .sol files
soil_summaries = ssc.writeWeppSoils(
    wd='./wepp/soils',
    version='7778',         # WEPP file format version
    overwrite=True
)

# Access soil properties
for mukey, summary in soil_summaries.items():
    print(f"{mukey}: {summary.desc}")
    print(f"  Texture: {summary.simple_texture}")
    print(f"  Clay: {summary.clay}%, Sand: {summary.sand}%")
    print(f"  Erodibility: Ki={summary.avke}")
```

### 4. NoDb Controller Integration
The `Soils` NoDb controller orchestrates this workflow:

```python
from wepppy.nodb.core import Soils, SoilsMode

# Initialize soils controller
soils = Soils.getInstance('/weppcloud/runs/my-run')

# Configure soil data source
with soils.locked():
    soils.mode = SoilsMode.SSURGO
    soils.dump_and_unlock()

# Build soil files for all hillslopes
soils.build_soils()

# Query dominant soil per subcatchment
dominant_soil = soils.domsoil_d  # Dict[topaz_id, mukey]
```

## SSURGO-to-WEPP Conversion

The core technical process is documented in [ssurgo/ssurgo.md](ssurgo/ssurgo.md). Key steps:

### Component Selection
- Select **major component** (highest coverage percentage) from SSURGO map unit
- Validate component has usable horizons (non-organic, complete texture data)
- Fallback to urban/water templates for non-soil features

### Horizon Validation
Each horizon must pass validation criteria:
- Not organic layer (`desgnmaster` ≠ "O")
- Depth, sand, clay, organic matter, CEC all numeric and > 0
- Very fine sand percentage available
- Conductivity or texture data for estimation

### Parameter Estimation

**When SSURGO data is missing:**
- **Bulk density**: Estimated from texture using weighted average (sand=1.6, silt=1.4, clay=1.2 g/cm³)
- **Hydraulic conductivity**: Rosetta2 or Rosetta3 pedotransfer functions
- **Field capacity / Wilting point**: SSURGO values adjusted for rock content, or Rosetta predictions
- **Albedo**: `0.6 / exp(0.4 × organic_matter)`

**Erodibility Parameters** (computed from texture and OM):
- **Interrill erodibility (Ki)**: WEPP User Summary Equations 6, 9
- **Rill erodibility (Kr)**: WEPP User Summary Equations 7, 10
- **Critical shear (τc)**: WEPP User Summary Equations 8, 11

**See:** [ssurgo/ssurgo.md#parameter-estimation](ssurgo/ssurgo.md#3-parameter-estimation) for complete equations and logic.

### WEPP File Formats

**Version 7778** (default):
- Full parameterization: bulk density, ksat, anisotropy, field capacity, wilting point
- Layer-specific hydraulic properties
- Restrictive layer support

**Version 2006.2** (legacy):
- Simplified format: texture, OM, CEC only
- WEPP computes hydraulic properties internally
- Compatible with older WEPP versions

**Version 9002/9003/9005** (disturbed lands):
- Additional parameters for wildfire modeling and revegetation
- Burn severity codes, hydrophobicity adjustments
- Time-dependent hydraulic conductivity recovery

**See:** [Soil File Specification](../weppcloud/routes/usersum/input-file-specifications/soil-file.spec.md) for detailed format documentation.

## Configuration

### Soil Data Source Selection

The `Soils` NoDb controller (`wepppy.nodb.core.soils`) supports multiple data sources:

| Mode | Description | Resolution | Coverage |
|------|-------------|------------|----------|
| `SoilsMode.SSURGO` | USDA SSURGO database | 1:12,000-1:63,360 | County-level (varies) |
| `SoilsMode.STATSGO` | USDA STATSGO2 database | 1:250,000 | Complete CONUS |
| `SoilsMode.SINGLE` | Uniform soil across watershed | N/A | User-specified |
| `SoilsMode.GRIDDED` | Custom gridded soil data | User-defined | User-specified |

### Horizon Defaults

Default values applied when SSURGO data is incomplete:

```python
from collections import OrderedDict

horizon_defaults = OrderedDict([
    ('sandtotal_r', 66.8),   # % sand
    ('claytotal_r', 7.0),    # % clay
    ('om_r', 7.0),           # % organic matter
    ('cec7_r', 11.3),        # meq/100g
    ('sandvf_r', 10.0),      # % very fine sand
    ('smr', 55.5),           # % rock content
])
```

Defaults only apply when SSURGO fields are missing or non-numeric. Existing SSURGO values always take precedence.

### Restrictive Layer Detection

Restrictive layers (hardpan, bedrock) limit subsurface drainage:

```python
res_lyr_ksat_threshold = 2.0  # mm/h
```

Horizons with `ksat < 2.0 mm/h` trigger restrictive layer encoding in WEPP soil files, truncating the profile at that depth.

## Key Concepts

### Map Unit Key (Mukey)
SSURGO's primary spatial identifier. Each mukey represents a map unit polygon with associated soil components. WEPPcloud extracts the dominant mukey per subcatchment polygon.

### Component vs Horizon
- **Component**: Soil type within a map unit (e.g., "Palouse silt loam, 7-25% slopes")
- **Horizon**: Vertical layer within a soil profile (e.g., "Ap horizon, 0-20 cm")
- WEPP soil files represent horizons from a single component (the major component)

### Rosetta Pedotransfer Functions
Statistical models that predict soil hydraulic properties from texture:
- **Rosetta2**: Uses sand, silt, clay percentages
- **Rosetta3**: Uses sand, silt, clay, bulk density (more accurate)
- Outputs: saturated conductivity, field capacity, wilting point, van Genuchten parameters

**Reference:** [Rosetta Model Documentation](https://www.ars.usda.gov/pacific-west-area/riverside-ca/agricultural-water-efficiency-and-salinity-research-unit/docs/model/rosetta-model/)

### Erodibility Parameters

**Interrill erodibility (Ki)**: Detachment by raindrop impact (kg·s/m⁴)
- Higher values → more erosion from raindrop splash
- Sandy soils: `Ki = 2,728,000 + 192,100 × vfs`
- Fine-textured soils: `Ki = 6,054,000 - 55,130 × clay`

**Rill erodibility (Kr)**: Detachment by concentrated flow (s/m)
- Higher values → more erosion from rills and gullies
- Influenced by organic matter, texture

**Critical shear stress (τc)**: Threshold for rill erosion (N/m²)
- Flow shear must exceed τc to initiate rill erosion
- Clay content increases resistance

**Reference:** [WEPP User Summary](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum.pdf), Chapters 3-4

### Anisotropy Ratio
Ratio of horizontal to vertical hydraulic conductivity:
- **Surface layers (<50 mm)**: anisotropy = 10.0 (preferential lateral flow)
- **Deeper layers (≥50 mm)**: anisotropy = 1.0 (isotropic)

Reflects macropores, root channels, and structural features in surface horizons.

## Usage Examples

### Build Soils via NoDb Controller
```python
from wepppy.nodb.core import Soils, SoilsMode

# Initialize controller
soils = Soils.getInstance('/weppcloud/runs/my-run')

# Configure SSURGO mode
with soils.locked():
    soils.mode = SoilsMode.SSURGO
    soils.dump_and_unlock()

# Build soil files (uses watershed topology from Ron controller)
soils.build_soils()

# Access results
print(f"Dominant soils: {soils.domsoil_d}")
print(f"Soil summaries: {soils.soils}")
```

### Query SSURGO Directly
```python
from wepppy.soils.ssurgo import SurgoSoilCollection

# Fetch soil data for specific mukeys
ssc = SurgoSoilCollection([2485028, 2485029])
ssc.makeWeppSoils(initial_sat=0.75, ksflag=True)

# Write WEPP soil files
summaries = ssc.writeWeppSoils(
    wd='./soils',
    version='7778',
    write_logs=True
)

# Inspect soil properties
for mukey, ws in ssc.weppSoils.items():
    print(f"Mukey {mukey}:")
    print(f"  Component: {ws.majorComponent.muname}")
    print(f"  Layers: {ws.num_layers}")
    print(f"  Restrictive layer: {ws.res_lyr_i}")
    
    # Horizon details
    for i, (h, mask) in enumerate(zip(ws.horizons, ws.horizons_mask)):
        if mask:
            print(f"  Layer {i}: {h.depth} mm, ksat={h.ksat_r:.2f} mm/h")
```

### Use STATSGO2 for Large Watersheds
```python
from wepppy.soils.ssurgo import SurgoSoilCollection

# STATSGO2 provides coarser data but complete coverage
ssc = SurgoSoilCollection(
    mukeys=[123456],
    use_statsgo=True
)
ssc.makeWeppSoils()
ssc.writeWeppSoils(wd='./soils')
```

### Custom Horizon Defaults
```python
from collections import OrderedDict

# Override defaults for data-poor regions
defaults = OrderedDict([
    ('sandtotal_r', 45.0),
    ('claytotal_r', 20.0),
    ('om_r', 2.5),
    ('cec7_r', 15.0),
    ('sandvf_r', 12.0),
    ('smr', 35.0),
])

ssc = SurgoSoilCollection([2485028])
ssc.makeWeppSoils(horizon_defaults=defaults)
```

### Inspect Build Logs
```python
ssc = SurgoSoilCollection([2485028])
ssc.makeWeppSoils(verbose=True)

# Access detailed build log
ws = ssc.weppSoils[2485028]
print('\n'.join(ws.log))

# Build notes show parameter estimation methods
print('\n'.join(ws.build_notes))
# Example output:
# albedo estimated from om_r (3.5%)
# ksat_r estimated from rosetta3
# field_cap estimated from wthirdbar_r and rock
```

## Developer Notes

### Package Structure
```
wepppy/soils/
├── __init__.py           # Empty package initializer
└── ssurgo/               # SSURGO/STATSGO2 integration
    ├── __init__.py       # Exports SurgoMap, SurgoSoilCollection, etc.
    ├── ssurgo.py         # Core SSURGO-to-WEPP conversion
    ├── ssurgo.md         # Technical documentation
    ├── surgo_map.py      # Spatial soil map interface
    ├── statsgo_spatial.py # STATSGO2 spatial interface
    ├── spatializer.py    # Spatial analysis utilities
    ├── county_db/        # County-level SSURGO lookups
    └── data/             # Cached SSURGO/STATSGO2 tables
```

### Extending Soil Data Sources

To add a new soil data source:

1. **Create spatial map interface** (analogous to `SurgoMap`):
   ```python
   class CustomSoilMap:
       def get_dominant_mukeys_for_subcatchments(self, polygons):
           # Return dict mapping polygon_id -> mukey
           pass
   ```

2. **Implement soil collection builder** (analogous to `SurgoSoilCollection`):
   ```python
   class CustomSoilCollection:
       def makeWeppSoils(self, **kwargs):
           # Build WeppSoil objects from custom data source
           pass
       
       def writeWeppSoils(self, wd, version='7778'):
           # Generate WEPP .sol files
           pass
   ```

3. **Add to SoilsMode enum** in `wepppy.nodb.core.soils`:
   ```python
   class SoilsMode(IntEnum):
       CUSTOM = 5
   ```

4. **Update Soils controller** `build_soils()` method to handle new mode.

### Testing SSURGO Conversion

```python
import pytest
from wepppy.soils.ssurgo import SurgoSoilCollection

def test_ssurgo_build():
    # Use known-good mukey
    ssc = SurgoSoilCollection([2485028])
    ssc.makeWeppSoils()
    
    assert 2485028 in ssc.weppSoils
    ws = ssc.weppSoils[2485028]
    
    # Validate structure
    assert ws.valid()
    assert ws.num_layers > 0
    assert ws.majorComponent is not None
    
    # Validate parameters
    h0 = ws.getFirstHorizon()
    assert h0.clay > 0
    assert h0.sand > 0
    assert h0.ksat_r > 0
```

### Caching Behavior

**SQLite Cache:** `/dev/shm/surgo_tabular.db` (in-memory tmpfs)
- Components, horizons, textures, fragments cached locally
- Avoids redundant SSURGO web service calls
- Persists across runs (manual deletion required to force re-fetch)

**Cache Sync Logic:**
1. Query local cache for existing data
2. Identify missing mukeys/cokeys/chkeys
3. Exclude previously failed keys (tracked in `bad_*` tables)
4. Fetch missing data from SSURGO web service
5. Insert into cache, update failure tables

### Parallel Processing

`SurgoSoilCollection.makeWeppSoils()` uses `ProcessPoolExecutor`:
- Pre-loads all SSURGO data into immutable `_SurgoCollectionWorkerView`
- Workers build `WeppSoil` objects without database I/O
- Default `max_workers = CPU count` (capped at 20)
- Progress logged every 60 seconds

**Performance:** ~100 mukeys/minute on 8-core system (varies by data completeness).

### Known Limitations

**SSURGO Coverage Gaps:**
- Not all US regions have complete SSURGO data
- Fallback to STATSGO2 for unsurveyed areas

**Organic Horizon Exclusion:**
- O horizons excluded from WEPP profiles
- Reduces depth for forested sites with thick organic layers
- WEPP erodibility equations not calibrated for organic materials

**Restrictive Layer Simplification:**
- WEPP models single restrictive layer below profile
- SSURGO may have multiple restrictive features within profile
- First restrictive layer (ksat < 2.0 mm/h) truncates profile

**Horizon Gaps:**
- Depth discontinuities not filled (e.g., 0-20 cm, 30-50 cm)
- Some valid SSURGO soils rejected as invalid
- Future: interpolate properties across small gaps

**Urban/Water Templates:**
- Use hardcoded values, not site-specific data
- Reduces flexibility for urban hydrology studies

## Operational Notes

### SSURGO Web Service Dependencies

**Endpoint:** `https://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx`

**Failure Modes:**
- Service downtime: Use local cache or STATSGO2 fallback
- Timeout errors: Retry with smaller mukey batches
- Rate limiting: Implement exponential backoff

**Monitoring:** Track `SsurgoRequestError` exceptions and cache hit rates.

### Disk Space Requirements

**Cache Database:** ~500 MB for regional runs, ~5 GB for national-scale
**Soil Files:** ~10 KB per mukey (varies by number of horizons)

### Performance Tuning

**For large mukey sets (>100):**
- Increase `max_workers` to available CPU cores
- Pre-warm cache with regional SSURGO download
- Use STATSGO2 for initial runs, SSURGO for refinement

**For small mukey sets (<10):**
- Set `max_workers=1` to avoid serialization overhead
- Consider in-memory processing without cache

### Troubleshooting

**Invalid Soils:**
```python
# Inspect why a mukey failed validation
ssc = SurgoSoilCollection([INVALID_MUKEY])
ssc.makeWeppSoils(verbose=True)

if INVALID_MUKEY in ssc.invalidSoils:
    ws = ssc.invalidSoils[INVALID_MUKEY]
    if ws is not None:
        print('\n'.join(ws.log))  # Build failure reason
```

**Missing SSURGO Data:**
- Check NRCS Web Soil Survey for data availability
- Verify extent overlaps SSURGO coverage area
- Fallback to STATSGO2 if SSURGO unavailable

**Rosetta Prediction Errors:**
- Validate texture percentages sum to ≤100%
- Check for extreme values (clay >60%, sand >95%)
- Ensure bulk density in realistic range (0.8-2.0 g/cm³)

## Further Reading

### Technical Documentation
- [ssurgo/ssurgo.md](ssurgo/ssurgo.md) - SSURGO-to-WEPP conversion technical specification
- [Soil File Specification](../weppcloud/routes/usersum/input-file-specifications/soil-file.spec.md) - WEPP input format details
- [WEPP Soil Parameters](../wepp/soils/README.md) - WEPP soil file format versions

### SSURGO/STATSGO2 Resources
- [SSURGO 2.2 Data Model](https://www.nrcs.usda.gov/Internet/FSE_DOCUMENTS/nrcs142p2_050900.pdf) - Schema and relationships
- [Table Column Descriptions](https://sdmdataaccess.nrcs.usda.gov/documents/TableColumnDescriptionsReport.pdf) - Field definitions
- [SDM Data Access Portal](https://sdmdataaccess.nrcs.usda.gov/Query.aspx) - Test SOAP queries
- [Web Soil Survey](https://websoilsurvey.nrcs.usda.gov/) - Interactive SSURGO browser

### WEPP Model Documentation
- [WEPP User Summary](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum.pdf) - Official WEPP documentation
- [Baseline Soil Erodibility](http://milford.nserl.purdue.edu/weppdocs/usersummary/BaselineSoilErodibilityParameterEstimation.html) - Parameter equations

### Rosetta Model
- [Rosetta Documentation](https://www.ars.usda.gov/pacific-west-area/riverside-ca/agricultural-water-efficiency-and-salinity-research-unit/docs/model/rosetta-model/) - USDA-ARS Rosetta home
- Schaap, M.G., Leij, F.J., van Genuchten, M.Th. (2001). "ROSETTA: a computer program for estimating soil hydraulic parameters with hierarchical pedotransfer functions." *Journal of Hydrology*, 251(3-4), 163-176.

### Related WEPPcloud Modules
- [wepppy.nodb.core.soils](../nodb/core/README.md#soils-controller) - Soils NoDb controller
- [wepppy.wepp.soils](../wepp/soils/README.md) - WEPP soil file handling
- [wepppy.nodb.duckdb_agents](../nodb/duckdb_agents.py) - Soil summary queries

## Credits

**Development:**
- Roger Lew (rogerlew@gmail.com) - Primary developer
- University of Idaho - Institutional support

**Data Sources:**
- USDA Natural Resources Conservation Service (NRCS) - SSURGO/STATSGO2 databases
- USDA Agricultural Research Service (ARS) - Rosetta pedotransfer models

**Funding:**
- NSF Idaho EPSCoR Program (Award IIA-1301792)
- National Science Foundation

**License:** BSD-3-Clause (see [license.txt](../../license.txt))
