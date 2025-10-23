# SSURGO to WEPP Soil File Conversion
> Technical Documentation for WEPP Soil File Generation from SSURGO Database

## Overview

This document describes the technical process by which WEPPcloud translates USDA NRCS Soil Survey Geographic Database (SSURGO) and STATSGO2 data into WEPP model soil input files. The conversion pipeline handles data acquisition, validation, parameter estimation, and file formatting while maintaining transparency through extensive logging and build notes.

**Key Capabilities:**
- Query SSURGO/STATSGO2 via SOAP web service or local SQLite cache
- Build WEPP soil files (versions 7778, 2006.2) from map unit keys (mukeys)
- Apply Rosetta pedotransfer functions for missing hydraulic parameters
- Estimate erodibility parameters using WEPP baseline equations
- Handle restrictive layers and rock content adjustments
- Parallel processing of large soil collections
- Cache management to minimize web service calls

**Module Location:** `wepppy/soils/ssurgo/ssurgo.py`

**Dependencies:**
- `rosetta` - Rosetta2/Rosetta3 pedotransfer models
- `wepppy.wepp.soils` - Horizon parameter computation utilities
- Local SQLite databases for SSURGO/STATSGO2 data caching

## Architecture

### Data Flow Pipeline

```
SSURGO Web Service / STATSGO2 Database
            ↓
    SurgoSoilCollection
      (fetches & caches)
            ↓
     Local SQLite DB
      (/dev/shm cache)
            ↓
  Component Selection
   (major component)
            ↓
    Horizon Building
  (validation & defaults)
            ↓
 Parameter Estimation
  (Rosetta, erodibility)
            ↓
      WeppSoil Object
            ↓
  WEPP Soil File (.sol)
```

### Core Classes

#### `SurgoSoilCollection`
Main orchestrator that manages SSURGO data acquisition and caching.

**Responsibilities:**
- Query SSURGO web service for component, horizon, and texture data
- Maintain local SQLite cache to avoid redundant web requests
- Build `WeppSoil` objects for each mukey
- Parallel processing via `ProcessPoolExecutor`
- Track valid/invalid soil builds

**Key Methods:**
- `__init__(mukeys, use_statsgo=False)` - Initialize collection with map unit keys
- `makeWeppSoils(...)` - Build WeppSoil objects concurrently
- `writeWeppSoils(wd, version='7778')` - Write soil files to disk
- `get_components(mukey)` - Retrieve soil components for map unit
- `get_layers(cokey)` - Retrieve horizons for component

#### `WeppSoil`
Represents a single WEPP soil file built from SSURGO data.

**Responsibilities:**
- Select major component (highest `comppct_r`)
- Validate and filter horizons
- Apply defaults for missing parameters
- Compute restrictive layer properties
- Format output for WEPP versions 7778, 2006.2

**Key Attributes:**
- `mukey` - SSURGO map unit key
- `majorComponent` - Selected component with highest coverage
- `horizons` - List of `Horizon` objects
- `horizons_mask` - Boolean mask of valid horizons
- `res_lyr_i` - Index of restrictive layer (or None)
- `num_layers` - Count of valid layers

#### `Horizon`
Individual soil layer with computed WEPP parameters.

**Inherits:** `HorizonMixin` (provides erodibility, conductivity, anisotropy calculations)

**Responsibilities:**
- Parse SSURGO horizon data
- Apply Rosetta pedotransfer functions
- Compute rock content
- Calculate hydraulic and erodibility parameters
- Track parameter estimation methods in build notes

**Key Computed Properties:**
- `ksat_r` - Saturated hydraulic conductivity (mm/h)
- `field_cap` - Field capacity (m³/m³)
- `wilt_pt` - Wilting point (m³/m³)
- `dbthirdbar_r` - Bulk density (g/cm³)
- `interrill` - Interrill erodibility (kg·s/m⁴)
- `rill` - Rill erodibility (s/m)
- `shear` - Critical shear stress (N/m²)
- `anisotropy` - Hydraulic anisotropy ratio

#### `_SurgoCollectionWorkerView`
Immutable, picklable data view for multiprocessing.

**Purpose:**
- Pre-load all SSURGO data before forking worker processes
- Eliminate database connections in child processes
- Provide read-only interface to components, layers, textures

**Design Pattern:** Built by `SurgoCollectionWorkerViewFactory`, passed to workers as a single serialized object containing all necessary SSURGO data for the mukey set.

## SSURGO Data Schema

### Key SSURGO Tables

**component** - Soil component information (linked by `mukey`)
```
mukey, cokey, compname, comppct_r, albedodry_r, 
hydricrating, drainagecl, muname, taxclname, etc.
```

**chorizon** - Horizon/layer properties (linked by `cokey`)
```
cokey, chkey, hzname, hzdepb_r, hzdept_r, hzthk_r,
dbthirdbar_r, ksat_r, sandtotal_r, claytotal_r,
om_r, cec7_r, fraggt10_r, frag3to10_r, desgnmaster,
sieveno10_r, wthirdbar_r, wfifteenbar_r, sandvf_r, ll_r
```

**chfrags** - Horizon rock fragments (linked by `chkey`)
```
chkey, fragvol_r
```

**chtexturegrp** - Horizon texture classification (linked by `chkey`)
```
chkey, texture
```

**corestrictions** - Restrictive layer information (linked by `cokey`)
```
cokey, reskind
```

### SSURGO to WEPP Parameter Mapping

| SSURGO Field | WEPP Parameter | Units | Notes |
|--------------|----------------|-------|-------|
| `hzdepb_r` | `solthk` | mm | Multiplied by 10 (cm → mm) |
| `dbthirdbar_r` | `bd` | g/cm³ | Estimated if missing |
| `ksat_r` | `ksat` | mm/h | Convert cm/day → mm/h × 3.6 |
| `wfifteenbar_r` | `wp` | m³/m³ | Adjusted for rock content |
| `wthirdbar_r` | `fc` | m³/m³ | Adjusted for rock content |
| `sandtotal_r` | `sand` | % | Direct mapping |
| `claytotal_r` | `clay` | % | Direct mapping |
| `om_r` | `orgmat` | % | Direct mapping |
| `cec7_r` | `cec` | meq/100g | Direct mapping |
| `fraggt10_r` + `frag3to10_r` + `sieveno10_r` | `rfg` | % | Computed from fragments |
| `albedodry_r` | `salb` | - | From component or computed |

## Soil Building Process

### 1. Component Selection

The `WeppSoil.build()` method selects the **major component** for a given mukey:

**Selection Criteria:**
1. Components ordered by `comppct_r` (percent coverage) descending
2. First component with valid horizons is selected
3. If no valid components, check for urban/water classification
4. Urban/water soils use hardcoded default parameters

**Code Reference:**
```python
components = ssurgo_c.get_components(mukey)
for c in components:
    cokey = c['cokey']
    horizons, mask = self._get_horizons(cokey)
    if sum(mask) > 0:
        self.majorComponent = MajorComponent(c)
        self.horizons = horizons
        self.horizons_mask = mask
        return 1
```

### 2. Horizon Validation

Each horizon must pass validation to be included in the WEPP soil file:

**Validation Requirements** (`Horizon.valid()`):
- Not an organic layer (`desgnmaster` does not start with "O")
- `hzdepb_r` (depth) is numeric and > 0
- `sandtotal_r` is numeric and > 0
- `claytotal_r` is numeric and > 0
- `om_r` (organic matter) is numeric
- `cec7_r` is numeric and > 0
- `sandvf_r` (very fine sand) is numeric
- `ksat_r` (conductivity) is numeric
- `dbthirdbar_r` (bulk density) is numeric

**Invalid horizons are masked but retained for diagnostics.**

### 3. Parameter Estimation

When SSURGO data is missing or incomplete, WEPPcloud applies estimation methods in this order of preference:

#### Bulk Density Estimation
**When:** `dbthirdbar_r` is missing

**Method:** Weighted average by texture using `estimate_bulk_density()`
```python
# Mid-point densities by texture
sand_density = 1.6   # g/cm³
silt_density = 1.4
clay_density = 1.2
remainder_density = 1.4  # assumed loamy

bd = (sand% × 1.6 + silt% × 1.4 + clay% × 1.2 + remainder% × 1.4) / 100
```

**Build Note:** `"bd estimated from sand, vfs, and clay"`

#### Hydraulic Conductivity (Ksat)
**When:** `ksat_r` is missing

**Method:** Rosetta pedotransfer function
- **Rosetta3** if bulk density is available → uses sand, silt, clay, BD
- **Rosetta2** if bulk density missing → uses sand, silt, clay only

**Conversion:** Rosetta returns cm/day, converted to mm/h
```python
ksat_r = rosetta_ks × 10.0 / 24.0  # cm/day → mm/h
```

**Build Note:** `"ksat_r estimated from rosetta2"` or `"rosetta3"`

#### Field Capacity and Wilting Point
**Preference Order:**

1. **SSURGO data with rock adjustment** (preferred)
   - If `wthirdbar_r` and rock content available:
     ```python
     field_cap = (0.01 × wthirdbar_r) / (1.0 - min(50.0, rock) / 100.0)
     ```
   - If `wfifteenbar_r` and rock content available:
     ```python
     wilt_pt = (0.01 × wfifteenbar_r) / (1.0 - min(50.0, rock) / 100.0)
     ```
   - **Build Note:** `"field_cap estimated from wthirdbar_r and rock"`

2. **Rosetta pedotransfer** (fallback)
   - Uses Rosetta2 or Rosetta3 predicted values
   - **Build Note:** `"field_cap estimated from rosetta2"`

**Rock Adjustment Rationale:** SSURGO water content values represent the fine earth fraction. Rock fragments reduce the effective pore space, so values are adjusted upward to represent volumetric water content of the whole soil.

#### Rock Content Calculation
**Source Fields:**
- `fraggt10_r` - Fragments > 10mm
- `frag3to10_r` - Fragments 3-10mm  
- `sieveno10_r` - Percent passing #10 sieve

**Calculation:**
```python
rocks_soil = fraggt10_r + frag3to10_r
rock = (100.0 - rocks_soil) / 100.0 × (100.0 - sieveno10_r) + rocks_soil
```

**Special Cases:**
- Organic horizons (`desgnmaster` starts with "O"): use default rock content
- Missing `sieveno10_r`: use default rock content
- Rock content capped at 50% for FC/WP adjustments

#### Albedo Estimation
**When:** `albedodry_r` missing from component

**Method:** Empirical equation from WEPP documentation
```python
albedodry_r = 0.6 / exp(0.4 × om_r)
```

**Build Note:** `"albedo estimated from om_r (X%)"`

**Reference:** [WEPP User Summary, Equation 15](http://milford.nserl.purdue.edu/weppdocs/usersummary/BaselineSoilErodibilityParameterEstimation.html#Albedo)

### 4. Erodibility Parameter Calculation

WEPP requires three baseline erodibility parameters computed from texture and organic matter using equations from the [WEPP User Summary](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum.pdf).

**Computed by:** `HorizonMixin._computeErodibility()` → `compute_erodibilities()`

#### Interrill Erodibility (Ki)
**Units:** kg·s/m⁴

**For sandy soils (sand ≥ 30%):**
```python
Ki = 2,728,000 + 192,100 × vfs
```
where `vfs` is very fine sand % (capped at 40%)

**For fine-textured soils (sand < 30%):**
```python
Ki = 6,054,000 - 55,130 × clay
```
where `clay` is capped at minimum 10%

**Reference:** WEPP User Summary, Equations 6 and 9

#### Rill Erodibility (Kr)
**Units:** s/m

**For sandy soils (sand ≥ 30%):**
```python
Kr = 0.00197 + 0.00030 × vfs + 0.03863 × exp(-1.84 × om)
```
where `om` is organic matter % (minimum 0.35% applied if lower)

**For fine-textured soils (sand < 30%):**
```python
Kr = 0.0069 + 0.134 × exp(-0.20 × clay)
```

**Reference:** WEPP User Summary, Equations 7 and 10

#### Critical Shear Stress (τc)
**Units:** N/m²

**For sandy soils (sand ≥ 30%):**
```python
τc = 2.67 + 0.065 × clay - 0.058 × vfs
```
where `clay` is capped at 42%

**For fine-textured soils (sand < 30%):**
```python
τc = 3.5  (constant)
```

**Reference:** WEPP User Summary, Equations 8 and 11

**Note:** These are the first horizon's values; they appear once in the WEPP soil file header (Line 4).

### 5. Hydraulic Conductivity Calculation

WEPP uses effective hydraulic conductivity for infiltration modeling. WEPPcloud computes this using texture and CEC.

**Computed by:** `HorizonMixin._computeConductivity()` → `compute_conductivity()`

**For clay ≤ 40%:**
```python
if CEC > 1.0:
    Ke = -0.265 + 0.0086 × sand^1.8 + 11.46 × CEC^-0.75
else:
    Ke = 11.195 + 0.0086 × sand^1.8
```

**For clay > 40%:**
```python
Ke = 0.0066 × exp(244.0 / clay)
```

**Units:** mm/h

**Reference:** WEPP User Summary, Equations 1 and 2

**Note:** This is the `avke` value in the WEPP soil file (Line 4i). It is distinct from layer-specific `ksat` values.

### 6. Anisotropy Ratio Calculation

Anisotropy represents the ratio of horizontal to vertical hydraulic conductivity.

**Computed by:** `HorizonMixin._computeAnisotropy()`

**Rules:**
```python
if depth > 50 mm:
    anisotropy = 1.0   # isotropic
else:
    anisotropy = 10.0  # surface layer, preferential lateral flow
```

**Justification:** Surface horizons often exhibit preferential lateral flow due to macropores, roots, and structural features.

### 7. Restrictive Layer Analysis

WEPP models subsurface flow impedance via a restrictive layer below the soil profile.

**Detection Method:** `WeppSoil._analyze_restrictive_layer()`

**Algorithm:**
1. Iterate through valid horizons in depth order
2. Track minimum `ksat_r` encountered
3. If `ksat_r < res_lyr_ksat_threshold` (default 2.0 mm/h), mark as restrictive layer
4. Truncate horizon list at restrictive layer

**WEPP File Encoding (Line 6):**
```
slflag  ui_bdrkth  kslast

slflag: 1 if restrictive layer exists, 0 otherwise
ui_bdrkth: 10000 mm (fixed thickness, effectively infinite)
kslast: minimum ksat encountered, converted to m/h (ksat_min × 3.6 / 1000)
```

**Purpose:** Restrictive layers limit drainage depth and promote lateral subsurface flow, affecting hydrograph shape and baseflow.

### 8. Horizon Depth Adjustments

WEPP requires soil profiles ≥ 200 mm deep. Adjustments are applied to the last valid horizon:

**Rules:**
1. Convert SSURGO depth from cm to mm (`hzdepb_r × 10`)
2. If last horizon depth < 210 mm, extend to 210 mm
3. Round last horizon depth up to nearest 200 mm increment

**Example:**
```
SSURGO depth: 18 cm → 180 mm
Adjusted:     210 mm (minimum threshold)

SSURGO depth: 45 cm → 450 mm  
Adjusted:     600 mm (rounded to nearest 200)
```

**Justification:** Ensures WEPP has sufficient rooting depth and subsurface storage for water balance calculations.

## Default Parameters

When horizon data is incomplete, defaults can be supplied via the `horizon_defaults` parameter:

**Standard Defaults** (used by `SurgoSoilCollection.makeWeppSoils()`):
```python
horizon_defaults = OrderedDict([
    ('sandtotal_r', 66.8),  # %
    ('claytotal_r', 7.0),   # %
    ('om_r', 7.0),          # %
    ('cec7_r', 11.3),       # meq/100g
    ('sandvf_r', 10.0),     # %
    ('smr', 55.5),          # % rock content
])
```

**Application:** Defaults are only used when the SSURGO field is missing or non-numeric. Existing SSURGO values always take precedence.

**Horizon Build Notes:** Each default application is logged:
```
"using default rock content of 55.5%"
```

## Special Soil Types

### Urban Soils
**Detection:** Component name contains "urban" (case-insensitive)

**WEPP File:** Uses hardcoded urban soil template
```
7778
# [description]
1  1
'Urban_1'  'Urban'  1  0.16  0.75  4649000  0.0140  2.648  0.0000
210  1.4  100.8  10  0.242  0.1145  66.8  7  3  11.3  55.5
1  10000  100.8
```

**Properties:**
- High interrill erodibility (4,649,000 kg·s/m⁴)
- Low rill erodibility (0.014 s/m)
- High conductivity (100.8 mm/h)
- Single 210 mm layer

### Water Bodies
**Detection:** Component name contains "water" (case-insensitive)

**WEPP File:** Uses hardcoded water template
```
7778
# [description]
1  1
'water_7778_2'  'Water'  1  0.1600  0.7500  1.0000  0.0100  999.0000  0.1000
210.0  0.8  100.0  10.0  0.242  0.115  66.8  7.0  3.0  11.3  0.0
1  10000  100
```

**Properties:**
- Minimal erodibility
- Very high conductivity (999 mm/h)
- Low bulk density (0.8 g/cm³)

**Purpose:** Prevents erosion calculations on water features while maintaining model compatibility.

## WEPP Soil File Formats

### Version 7778 (Default)

**Line 1:** Version identifier
```
7778
```

**Line 2:** Comment block with disclaimer and metadata
```
# WEPPcloud v.0.1.0 (c) University of Idaho
# Build Date: 2025-10-23 ...
# Source Data: Surgo
# Mukey: 2485028
# Major Component: 12345678 (comppct_r = 85.0)
# Texture: silt loam
# [Horizon details table]
# [Restrictive layer info]
# [Defaults applied]
# [Build notes]
# [Disclaimer text]
```

**Line 3:** Number of OFEs and conductivity adjustment flag
```
1  1

nofes: 1 (single hillslope element)
ksflag: 1 (enable internal conductivity adjustments)
```

**Line 4:** Soil identification and surface properties
```
'Mukey_Name'  'Texture'  nlayers  albedo  init_sat  Ki  Kr  τc  [Ke]

Example:
'Palouse silt loam'  'silt loam'  4  0.23  0.75  2940000  0.0041  3.5
```

**Line 5 (repeated for each layer):** Horizon properties
```
depth  bd  ksat  aniso  fc  wp  sand  clay  om  cec  rock

Example:
  210.000    1.32   14.5820   10.0   0.2890   0.1320    8.5    19.0     3.5     18.6     0.0
  580.000    1.38    7.4190    1.0   0.2710   0.1380   10.2    21.5     1.8     17.2     0.0
  900.000    1.42    4.9870    1.0   0.2580   0.1410   12.8    23.0     0.9     15.8     0.0
 1200.000    1.45    3.2450    1.0   0.2490   0.1440   15.6    24.2     0.5     14.5     0.0
```

**Line 6:** Restrictive layer
```
slflag  thickness  kslast

Example:
1  10000.0  0.00325  (restrictive layer present, ksat = 3.25 mm/h)
1  10000.0  0.01000  (restrictive layer, default ksat)
0  0  0.0           (no restrictive layer)
```

### Version 2006.2 (Simplified)

**Differences from 7778:**
- Line 4 includes `avke` (effective conductivity) in the header
- Line 5 omits `bd`, `ksat`, `aniso`, `fc`, `wp` (only texture/OM/CEC)
- Fewer parameters per layer (6 values instead of 11)

**Example:**
```
2006.2
# [comments]
1  1
'Palouse silt loam'  'silt loam'  4  0.23  0.75  2940000  0.0041  3.5  14.58
  210.0     8.5    19.0     3.5     18.6     0.0
  580.0    10.2    21.5     1.8     17.2     0.0
  900.0    12.8    23.0     0.9     15.8     0.0
 1200.0    15.6    24.2     0.5     14.5     0.0
1  10000.0  0.00325
```

**Use Case:** Legacy WEPP versions that compute hydraulic parameters internally.

## Build Logging and Transparency

### Build Notes
Each `WeppSoil` object maintains a `build_notes` list tracking parameter estimation decisions:

**Example Build Notes:**
```
albedo estimated from om_r (3.5%)
2485028::ksat_r estimated from rosetta3
2485028::wilt_pt estimated from rosetta3
2485028::field_cap estimated from wthirdbar_r and rock
2485028::bd estimated from sand, vfs, and clay
res_lyr_i None
```

**Inclusion in File:** Build notes appear in the comment header, providing full provenance for each soil file.

### Verbose Logging
The `WeppSoil.log` attribute captures the complete build sequence:

**Example Log:**
```
mukey: 2485028
found 3 components
looping over components
analyzing cokey 12345678
found 5 layers
analyzing chkey 23456789
analyzing chkey 23456790
...
horizons mask: [True, True, True, True, False]
identified 4 layers, ksat_min=2.45
Validity: all checks passed
```

**Output:** Use `WeppSoil.write_log(wd)` to write logs to disk for diagnostics.

## Parallel Processing

### Design Philosophy
WEPP soil building is CPU-intensive (Rosetta predictions, erodibility calculations). The `SurgoSoilCollection.makeWeppSoils()` method uses concurrent processing to maximize throughput.

### Implementation

**Worker View Pattern:**
1. `SurgoCollectionWorkerViewFactory` pre-loads all SSURGO data into an in-memory `_SurgoCollectionWorkerView` object
2. This immutable, picklable object is serialized and sent to each worker process
3. Workers build `WeppSoil` objects without any database I/O

**Advantages:**
- No database connections in child processes
- Eliminates SQLite locking contention
- Single serialization overhead (shared data view)
- Worker processes are truly independent

**Configuration:**
```python
ssc.makeWeppSoils(
    initial_sat=0.75,
    horizon_defaults=None,
    ksflag=True,
    logger=None,
    max_workers=None  # Defaults to CPU count, capped at 20
)
```

**Progress Monitoring:**
- Completed task count logged every 60 seconds
- Invalid soils logged with exceptions
- Results collected via `concurrent.futures.wait()`

**Error Handling:**
- Worker exceptions propagate to main process
- Failed mukeys added to `invalidSoils` with `None` value
- Partial success allowed (some mukeys valid, others invalid)

## Caching Strategy

### SQLite Local Cache
**Location:** `/dev/shm/surgo_tabular.db` (in-memory tmpfs) or fallback to module directory

**Purpose:** Minimize SSURGO web service calls by caching previously fetched data.

**Tables:**
- `component` - Indexed on `(mukey, cokey)`
- `chorizon` - Indexed on `(cokey, chkey)`
- `chfrags`, `chtexturegrp`, `corestrictions` - Indexed on primary keys
- `bad_*` tables - Track failed fetch attempts to avoid retries

**Sync Process** (`SurgoSoilCollection._sync()`):
1. Query local cache for existing data
2. Identify mukeys/cokeys/chkeys not in cache
3. Exclude previously failed keys (in `bad_*` tables)
4. Fetch missing data from SSURGO web service
5. Insert into cache
6. Update `bad_*` tables with failed keys

**Cache Lifetime:** Persists across runs. Manual deletion required to force re-fetch.

### Web Service Queries
**Endpoint:** `https://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx`

**Protocol:** SOAP 1.2 with XML payload

**Fetch Functions:**
- `_fetch_components(mukeys)` - Component data
- `_fetch_chorizon(cokeys)` - Horizon data
- `_fetch_chfrags(chkeys)` - Fragment volumes
- `_fetch_chtexturegrp(chkeys)` - Texture classifications
- `_fetch_corestrictions(cokeys)` - Restrictive layer info

**Error Handling:**
- Non-200 status codes raise `SsurgoRequestError`
- Failed fetches recorded in `bad_*` tables
- Warnings issued for sync errors

## Data Quality and Validation

### Component Selection Edge Cases

**No Valid Components:**
- Check for urban/water classification
- If neither, mark soil as invalid

**Multiple Components:**
- Select highest `comppct_r` with valid horizons
- Ignore components without buildable horizons

### Horizon Validation Edge Cases

**Organic Horizons:**
- Identified by `desgnmaster` starting with "O"
- Excluded from WEPP profile (mask = False)
- Skip rock content calculations

**Missing Critical Fields:**
- Horizon fails validation
- Build attempts next component
- If all components fail, soil marked invalid

**Zero Values:**
- Sand = 0, Clay = 0, or CEC = 0 → fails validation
- Ensures erodibility equations have valid inputs

### Rock Content Limits

**Adjustment Cap:** Rock content capped at 50% for FC/WP calculations
```python
field_cap = (0.01 × wthirdbar_r) / (1.0 - min(50.0, rock) / 100.0)
```

**Rationale:** Extremely high rock content (>50%) would produce unrealistic volumetric water contents. Capping limits physical impossibilities while maintaining conservative estimates.

### Depth Continuity

**WEPP Requirement:** Horizons must be sequential without gaps.

**SSURGO Reality:** Sometimes horizons have discontinuities (e.g., 0-20 cm, 30-50 cm).

**Current Handling:** No gap-filling logic; relies on SSURGO data completeness. Invalid profiles rejected.

**Future Enhancement:** Could interpolate properties across small gaps.

## Usage Examples

### Basic Usage - Single Mukey
```python
from wepppy.soils.ssurgo import SurgoSoilCollection

# Query SSURGO and build soil
ssc = SurgoSoilCollection([2485028])
ssc.makeWeppSoils(initial_sat=0.75, ksflag=True)

# Write WEPP soil file
soil_summaries = ssc.writeWeppSoils(
    wd='./soils',
    version='7778',
    overwrite=True
)

# Access soil properties
for mukey, summary in soil_summaries.items():
    print(f"{mukey}: {summary.desc}")
    print(f"  Texture: {summary.simple_texture}")
    print(f"  Clay: {summary.clay}%, Sand: {summary.sand}%")
```

### Batch Processing with Defaults
```python
from collections import OrderedDict

# Custom defaults for data-poor regions
defaults = OrderedDict([
    ('sandtotal_r', 45.0),
    ('claytotal_r', 20.0),
    ('om_r', 2.5),
    ('cec7_r', 15.0),
    ('sandvf_r', 12.0),
    ('smr', 35.0),
])

mukeys = [2485028, 2485029, 2485030]
ssc = SurgoSoilCollection(mukeys)
ssc.makeWeppSoils(
    horizon_defaults=defaults,
    verbose=True,
    max_workers=4
)

print(f"Valid: {len(ssc.weppSoils)}")
print(f"Invalid: {len(ssc.invalidSoils)}")

# Write both files and logs
ssc.writeWeppSoils(wd='./soils', write_logs=True)
ssc.logInvalidSoils(wd='./soils')
```

### STATSGO2 (Coarse Resolution)
```python
# Use STATSGO2 for national/continental scale
ssc = SurgoSoilCollection(
    mukeys=[123456],
    use_statsgo=True
)
ssc.makeWeppSoils()
ssc.writeWeppSoils(wd='./soils')
```

### Version 2006.2 Output
```python
ssc = SurgoSoilCollection([2485028])
ssc.makeWeppSoils()

# Write simplified format
ssc.writeWeppSoils(
    wd='./soils',
    version='2006.2'
)
```

### Accessing Soil Metadata
```python
ssc = SurgoSoilCollection([2485028])
ssc.makeWeppSoils()

# Access WeppSoil object
ws = ssc.weppSoils[2485028]

# Inspect major component
print(ws.majorComponent.muname)
print(ws.majorComponent.albedodry_r)

# Inspect horizons
for i, (h, mask) in enumerate(zip(ws.horizons, ws.horizons_mask)):
    if mask:
        print(f"Layer {i}: {h.depth} mm, ksat={h.ksat_r} mm/h")

# Check restrictive layer
if ws.res_lyr_i is not None:
    print(f"Restrictive layer at index {ws.res_lyr_i}")
    print(f"Minimum ksat: {ws.res_lyr_ksat} mm/h")
```

### Parallel Processing with Logging
```python
import logging

logger = logging.getLogger('ssurgo_build')
logger.setLevel(logging.INFO)

mukeys = range(2485000, 2485100)  # 100 mukeys
ssc = SurgoSoilCollection(mukeys)
ssc.makeWeppSoils(
    logger=logger,
    max_workers=8
)

# Logger will output:
# Starting makeWeppSoils...
# Building in-memory soil data view...
# In-memory data view built successfully.
# (1/100) completed mukey 2485000 -> True
# (2/100) completed mukey 2485001 -> True
# ...
# Completed makeWeppSoils: 95 valid, 5 invalid
```

## Known Limitations and Tradeoffs

### SSURGO Web Service Dependency
**Issue:** NRCS web service can be slow or unavailable.

**Mitigation:** Local SQLite cache reduces frequency of web requests.

**Future:** Consider distributing pre-built cache databases or using offline SSURGO downloads.

### Organic Horizon Exclusion
**Issue:** O horizons excluded from WEPP profiles.

**Justification:** WEPP erodibility equations not calibrated for organic materials.

**Impact:** Reduces soil depth for forested sites with thick organic layers.

### Restrictive Layer Simplification
**Issue:** WEPP models a single restrictive layer below the profile; SSURGO may have multiple restrictive features within the profile.

**Current:** First restrictive layer (ksat < 2.0 mm/h) truncates profile.

**Tradeoff:** Simplifies hydrology but may miss perched water tables above deeper restrictive layers.

### Gap Handling
**Issue:** Horizon depth discontinuities not filled.

**Impact:** Some valid SSURGO soils rejected as invalid.

**Future:** Interpolate properties across small gaps.

### Urban/Water Hardcoding
**Issue:** Urban and water soils use template values, not site-specific data.

**Justification:** These land uses rarely have meaningful SSURGO parameterization.

**Tradeoff:** Reduces flexibility for urban hydrology studies.

### Rosetta Model Selection
**Issue:** Rosetta3 (with bulk density) preferred over Rosetta2, but BD may be estimated, introducing circularity.

**Current:** If BD missing, estimate it, then use Rosetta3.

**Alternative:** Use Rosetta2 when BD is estimated rather than measured.

**Impact:** Minimal; Rosetta models are statistically similar for most textures.

### Parallel Processing Overhead
**Issue:** Small mukey sets (<10) may be slower with multiprocessing due to serialization overhead.

**Recommendation:** Use `max_workers=1` for small jobs.

## Developer Notes

### Adding New SSURGO Fields
1. Update table schemas in `_initialize_cache_db()`
2. Modify fetch functions (`_fetch_chorizon()`, etc.)
3. Add field to `Horizon.__init__()` or `MajorComponent`
4. Update `Horizon.valid()` if field is required
5. Document in build notes if estimated

### Custom Estimation Methods
To add a custom parameter estimation:
1. Add method to `Horizon` class (e.g., `_computeCustomParam()`)
2. Call from `Horizon.__init__()` after Rosetta predictions
3. Append build note tracking estimation source
4. Update `build_file_contents()` to include in WEPP file

### Testing New Mukeys
```python
# Test single mukey with verbose output
ssc = SurgoSoilCollection([MUKEY])
ssc.makeWeppSoils(verbose=True)
ws = ssc.weppSoils[MUKEY]

# Inspect build log
print('\n'.join(ws.log))

# Inspect build notes
print('\n'.join(ws.build_notes))

# Write file and compare to reference
ws.write('./test_soils')
```

### Debugging Invalid Soils
```python
ssc = SurgoSoilCollection([INVALID_MUKEY])
ssc.makeWeppSoils(verbose=True)

# Check if mukey in invalidSoils
if INVALID_MUKEY in ssc.invalidSoils:
    ws = ssc.invalidSoils[INVALID_MUKEY]
    if ws is not None:
        print('\n'.join(ws.log))  # See why it failed
    else:
        print("Worker exception occurred")
```

## Further Reading

### SSURGO/STATSGO2 Documentation
- [SSURGO 2.2 Data Model](https://www.nrcs.usda.gov/Internet/FSE_DOCUMENTS/nrcs142p2_050900.pdf) - Schema and table relationships
- [Table Column Descriptions](https://sdmdataaccess.nrcs.usda.gov/documents/TableColumnDescriptionsReport.pdf) - Field definitions
- [SSURGO Metadata Tables](http://www.anslab.iastate.edu/Class/AnS321L/soil%20view%20Marshall%20county/data/metadata/SSURGO%20Metadata%20Tables.pdf) - Table-level metadata
- [SDM Data Access Portal](https://sdmdataaccess.nrcs.usda.gov/Query.aspx) - Test SOAP queries

### WEPP Model Documentation
- [WEPP User Summary](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum.pdf) - Soil parameter estimation equations (Chapters 3-4)
- [Baseline Soil Erodibility Parameters](http://milford.nserl.purdue.edu/weppdocs/usersummary/BaselineSoilErodibilityParameterEstimation.html) - Online reference
- [Soil File Specification](../../../weppcloud/routes/usersum/input-file-specifications/soil-file.spec.md) - WEPP input format details

### Rosetta Pedotransfer Functions
- [Rosetta Model Documentation](https://www.ars.usda.gov/pacific-west-area/riverside-ca/agricultural-water-efficiency-and-salinity-research-unit/docs/model/rosetta-model/) - USDA-ARS Rosetta home
- Schaap, M.G., Leij, F.J., van Genuchten, M.Th. (2001). "ROSETTA: a computer program for estimating soil hydraulic parameters with hierarchical pedotransfer functions." *Journal of Hydrology*, 251(3-4), 163-176.

### WEPPcloud Internal Docs
- [AGENTS.md](../../../AGENTS.md) - Coding conventions and architecture overview
- [wepppy/wepp/soils/horizon_mixin.py](../../wepp/soils/horizon_mixin.py) - Erodibility and conductivity computation source code
- [wepppy/nodb/soils.py](../../nodb/core/soils.py) - NoDb Soils controller that orchestrates SSURGO queries

## Credits

**Development:**
- Roger Lew (rogerlew@gmail.com) - Primary developer
- University of Idaho - Institutional support
- USDA NRCS - SSURGO/STATSGO2 data stewardship

**Funding:**
- NSF Idaho EPSCoR Program (Award IIA-1301792)
- National Science Foundation

**License:** BSD-3-Clause (see [license.txt](../../../license.txt))

**Version:** v.0.1.0

**Last Updated:** 2025-10-23
