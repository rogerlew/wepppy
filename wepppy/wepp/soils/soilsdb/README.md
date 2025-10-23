# WEPP Soil Library (soilsdb)
> Pre-built WEPP soil files for standardized erosion modeling

> **See also:** [AGENTS.md](../../../../AGENTS.md) for coding conventions and [WeppSoilUtil](../utils/README.md) for soil file manipulation.

## Overview

The `wepppy.wepp.soils.soilsdb` package provides a curated library of pre-built WEPP soil files representing standard soil types, land covers, and disturbance conditions. These soils are ready-to-use references for WEPP modeling when detailed SSURGO data is unavailable or when standardized parameters are required for comparative studies.

**Key Capabilities:**
- Browse 50+ state-specific soil series from USDA NRCS databases
- Access 32 pre-defined forest, rangeland, and disturbed land soils
- Retrieve wildfire-adjusted soils by texture and burn severity
- Load legacy WEPP 2006.2 format soils for backward compatibility

**Primary Users:**
- Researchers needing standardized soil parameters for scenario modeling
- Wildfire analysts applying uniform burn severity adjustments
- Model calibrators comparing against reference soil properties
- Developers building soil selection interfaces

**Library Structure:**
```
wepppy/wepp/soils/soilsdb/
├── __init__.py              # Library API
└── data/
    ├── Database/            # State-specific NRCS soil series (50+ states)
    │   ├── ak/              # Alaska soils
    │   ├── ca/              # California soils
    │   ├── id/              # Idaho soils
    │   └── ...              # (all 50 states)
    ├── Forest/              # Modern forest/rangeland/disturbed soils (7778)
    │   ├── Forest loam.sol
    │   ├── High sev fire-loam.sol
    │   ├── Skid-loam.sol
    │   └── ...              # 32 total files
    └── Forest2006/          # Legacy forest soils (2006.2 format)
        ├── Forest loam.sol
        ├── Forest Soils Summary.csv
        └── ...              # 32 total files
```

## API Reference

### Browse Library

```python
from wepppy.wepp.soils.soilsdb import load_db

# Get list of all available soils
soils = load_db()
# Returns: ['Database/id/PALOUSE(SIL).sol', 'Forest/Forest loam.sol', ...]

# Filter by category
forest_soils = [s for s in soils if 'Forest/' in s]
database_soils = [s for s in soils if 'Database/' in s]
```

**Returns:** List of relative paths from `data/` directory.

**Note:** Only files directly under state directories are included. Nested subdirectories are excluded.

### Get Soil Path

```python
from wepppy.wepp.soils.soilsdb import get_soil

# Get absolute path to soil file
path = get_soil('Forest/Forest loam.sol')
# Returns: '/path/to/wepppy/wepp/soils/soilsdb/data/Forest/Forest loam.sol'

# Use with WeppSoilUtil
from wepppy.wepp.soils.utils import WeppSoilUtil
soil = WeppSoilUtil(get_soil('Forest/Forest loam.sol'))
print(f"Clay: {soil.clay}%, Texture: {soil.simple_texture}")
```

**Parameters:**
- `sol` - Relative path from `load_db()` output

**Returns:** Absolute path to `.sol` file.

**Raises:** `AssertionError` if file does not exist.

### Retrieve Wildfire Soil Parameters

```python
from wepppy.wepp.soils.soilsdb import read_disturbed_wepp_soil_fire_pars

# Get OFE dictionary for high severity burn on loam
ofe = read_disturbed_wepp_soil_fire_pars(
    simple_texture='loam',
    fire_severity='high'
)

# Access parameters
print(f"Interrill erodibility: {ofe['ki']}")
print(f"Rill erodibility: {ofe['kr']}")
print(f"Conductivity: {ofe['avke']} mm/h")
print(f"Initial saturation: {ofe['sat']}")
```

**Parameters:**
- `simple_texture` - One of: `'loam'`, `'silt loam'`, `'sand loam'`, `'clay loam'`
- `fire_severity` - One of: `'high'`, `'low'`

**Returns:** Dictionary containing single OFE structure from matching soil file (see [OFE Structure](#ofe-structure) below).

**Supported Combinations:**
| Texture | High Severity | Low Severity |
|---------|--------------|--------------|
| loam | ✓ | ✓ |
| silt loam | ✓ | ✓ |
| sand loam | ✓ | ✓ |
| clay loam | ✓ | ✓ |

**Example - Apply to Existing Soil:**
```python
from wepppy.wepp.soils.utils import WeppSoilUtil
from wepppy.wepp.soils.soilsdb import read_disturbed_wepp_soil_fire_pars

# Load base soil
soil = WeppSoilUtil('/watershed/base_soil.sol')

# Get fire-adjusted parameters
fire_pars = read_disturbed_wepp_soil_fire_pars(
    simple_texture=soil.simple_texture,
    fire_severity='high'
)

# Replace OFE parameters
soil.obj['ofes'][0]['ki'] = fire_pars['ki']
soil.obj['ofes'][0]['kr'] = fire_pars['kr']
soil.obj['ofes'][0]['avke'] = fire_pars['avke']

# Write burned soil
soil.write('/watershed/burned_soil.sol')
```

## Library Collections

### Database Collection

**Source:** USDA NRCS soil series database, exported to WEPP format.

**Coverage:** 50+ U.S. states and territories.

**Naming Convention:** `<STATE>/<SERIES>(<TEXTURE>).sol`
- Example: `Database/id/PALOUSE(SIL).sol` - Palouse silt loam from Idaho

**File Count:** Varies by state (Idaho: ~200, California: ~150, etc.)

**WEPP Version:** Mixed (97.5, 2006.2, 7778 depending on export date)

**Use Cases:**
- Region-specific erosion modeling using local soil series
- Validation against NRCS soil survey data
- Comparative analysis of soil properties across states

**Example - Browse Idaho Soils:**
```python
from wepppy.wepp.soils.soilsdb import load_db

soils = load_db()
id_soils = [s for s in soils if s.startswith('Database/id/')]

for soil_path in sorted(id_soils)[:5]:
    print(soil_path)
# Database/id/BLACKWELL(SIL).sol
# Database/id/BOTHWELL(SIL).sol
# Database/id/BROADHEAD(SIL).sol
# Database/id/CHATCOLET(SIL).sol
# Database/id/PALOUSE(SIL).sol
```

### Forest Collection (Modern)

**Source:** WEPP forest disturbance research, calibrated 2008-2022.

**File Count:** 32 soils (4 textures × 8 land cover classes)

**WEPP Version:** 7778 (migrated from 2006.2 with Rosetta predictions)

**Textures:**
- `loam` - Balanced clay/sand
- `silt loam` - Low clay+sand
- `sand loam` (sandy loam) - High sand
- `clay loam` - High clay

**Land Cover Classes:**
1. **Forest** - Mature forest with high infiltration
   - `Forest loam.sol`
   - `Forest silt loam.sol`
   - `Forest sandy loam.sol`
   - `Forest clay loam.sol`

2. **Young Forest** - Regenerating forest, intermediate infiltration
   - `Young forest loam.sol`
   - `Young forest silt loam.sol`
   - `Young forest sandy loam.sol`
   - `Young forest clay loam.sol`

3. **Shrub** - Shrubland, moderate ground cover
   - `Shrub loam.sol`
   - `Shrub silt loam.sol`
   - `Shrub sandy loam.sol`
   - `Shrub clay loam.sol`

4. **Tall Grass** - Tallgrass prairie, deep roots
   - `Tall Grass loam.sol`
   - `Tall Grass silt loam.sol`
   - `Tall Grass sandy loam.sol`
   - `Tall Grass clay loam.sol`

5. **Short Grass** - Shortgrass prairie, shallow roots
   - `Short Grass loam.sol`
   - `Short Grass-silt-Loam.sol`
   - `Short Grass sandy loam.sol`
   - `Short Grass clay loam.sol`

6. **Skid** - Skid trails, compacted by logging equipment
   - `Skid-loam.sol`
   - `Skid-silt loam.sol`
   - `Skid sandy loam.sol`
   - `Skid-clay loam.sol`

7. **High Severity Fire** - High burn severity, hydrophobic layer
   - `High sev fire-loam.sol`
   - `High sev fire-silt loam.sol`
   - `High sev fire-sandy loam.sol`
   - `High sev fire-clay loam.sol`

8. **Low Severity Fire** - Low burn severity, minimal hydrophobicity
   - `Low sev fire-loam.sol`
   - `Low sev fire-silt loam.sol`
   - `Low sev fire-sandy loam.sol`
   - `Low sev fire-clay loam.sol`

**Characteristic Parameters by Land Cover:**

| Land Cover | Albedo | Initial Sat | Depth (mm) | Notes |
|------------|--------|-------------|------------|-------|
| Forest | 0.06 | 0.5 | 800 | High infiltration, deep profile |
| Young Forest | 0.06 | 0.5 | 600 | Intermediate depth |
| Shrub | 0.15 | 0.75 | 500 | Moderate infiltration |
| Tall Grass | 0.15 | 0.75 | 400 | Deep roots, good structure |
| Short Grass | 0.15 | 0.75 | 400 | Shallow roots |
| Skid | 0.20 | 0.75 | 300 | Compacted, reduced conductivity |
| High Sev Fire | 0.10 | 0.75 | 400 | Low conductivity, high erodibility |
| Low Sev Fire | 0.15 | 0.75 | 400 | Moderate adjustments |

**Example - Compare Forest vs. Burned:**
```python
from wepppy.wepp.soils.utils import WeppSoilUtil
from wepppy.wepp.soils.soilsdb import get_soil

forest = WeppSoilUtil(get_soil('Forest/Forest loam.sol'))
burned = WeppSoilUtil(get_soil('Forest/High sev fire-loam.sol'))

print(f"Forest: ki={forest.obj['ofes'][0]['ki']:,.0f}, "
      f"avke={forest.avke:.1f} mm/h")
print(f"Burned: ki={burned.obj['ofes'][0]['ki']:,.0f}, "
      f"avke={burned.avke:.1f} mm/h")

# Output:
# Forest: ki=400,000, avke=50.0 mm/h
# Burned: ki=1,000,000, avke=15.0 mm/h
```

### Forest2006 Collection (Legacy)

**Source:** Original WEPP 2006.2 format forest soils (Elliot et al., 2008).

**File Count:** 32 soils (same land cover classes as Forest/)

**WEPP Version:** 2006.2 (original format)

**Purpose:** 
- Backward compatibility with legacy WEPP models
- Comparison with modern 7778 format soils
- Historical research replication

**Summary CSV:** `Forest Soils Summary.csv` provides tabular overview of all parameters.

**CSV Columns:**
```
slid, texid, landcover, burn_class, salb, sat, ki, kr, shcrit, avke,
sand, clay, orgmat, cec, rfg, solthk
```

**Example - Load Legacy Format:**
```python
from wepppy.wepp.soils.utils import WeppSoilUtil
from wepppy.wepp.soils.soilsdb import get_soil

# Load 2006.2 format soil
legacy = WeppSoilUtil(get_soil('Forest2006/Forest loam.sol'))
print(f"Version: {legacy.datver}")  # 2006.2

# Migrate to modern format
modern = legacy.to7778()
print(f"Upgraded version: {modern.datver}")  # 7778.0

# Compare parameters
print(f"Legacy ksat: {legacy.obj['ofes'][0]['horizons'][0].get('ksat', 'N/A')}")
print(f"Modern ksat: {modern.obj['ofes'][0]['horizons'][0]['ksat']:.2f}")
```

## OFE Structure

The `read_disturbed_wepp_soil_fire_pars()` function returns a dictionary representing a single WEPP Overland Flow Element (OFE):

```python
{
    'slid': 'High sev fire-loam',        # Soil ID
    'texid': 'loam',                     # Texture class
    'nsl': 1,                            # Number of soil layers
    'salb': 0.10,                        # Soil albedo
    'sat': 0.75,                         # Initial saturation
    'ki': 1000000,                       # Interrill erodibility (kg·s/m⁴)
    'kr': 0.0001,                        # Rill erodibility (s/m)
    'shcrit': 1.0,                       # Critical shear stress (Pa)
    'avke': 15.0,                        # Effective hydraulic conductivity (mm/h)
    'luse': None,                        # Disturbed land use (7778 only)
    'stext': None,                       # Simple texture (7778 only)
    'ksatadj': 0,                        # keff adjustment flag (9001+ only)
    'horizons': [                        # Soil layers
        {
            'solthk': 400.0,             # Depth (mm)
            'bd': 1.4,                   # Bulk density (g/cm³)
            'ksat': 12.24,               # Saturated conductivity (mm/h)
            'anisotropy': 1.0,           # Anisotropy ratio
            'fc': 0.2558,                # Field capacity (vol/vol)
            'wp': 0.1341,                # Wilting point (vol/vol)
            'sand': 45.0,                # Sand percentage
            'clay': 20.0,                # Clay percentage
            'orgmat': 5.0,               # Organic matter percentage
            'cec': 20.0,                 # Cation exchange capacity
            'rfg': 20.0,                 # Rock fragment percentage
        },
    ],
    'res_lyr': {                         # Restrictive layer
        'slflag': 1,                     # Layer present flag
        'ui_bdrkth': 10000.0,            # Depth to bedrock (mm)
        'kslast': 0.00036,               # Conductivity (mm/h)
    },
}
```

## Usage Examples

### Scenario 1: Populate Watershed with Library Soils

```python
from wepppy.wepp.soils.soilsdb import load_db, get_soil
from wepppy.wepp.soils.utils import WeppSoilUtil

# Browse library
soils = load_db()
forest_soils = [s for s in soils if 'Forest/' in s and 'fire' not in s]

# Select soils by texture for different hillslopes
hillslope_map = {
    'ridge': 'Forest/Forest sandy loam.sol',    # Well-drained
    'backslope': 'Forest/Forest loam.sol',      # Typical
    'toeslope': 'Forest/Forest clay loam.sol',  # Poorly-drained
}

# Copy to watershed directory
for position, soil_rel in hillslope_map.items():
    src = get_soil(soil_rel)
    dst = f'/watershed/soils/{position}.sol'
    
    soil = WeppSoilUtil(src)
    soil.write(dst)
    print(f"{position}: {soil.simple_texture}, ksat={soil.avke:.1f} mm/h")
```

### Scenario 2: Build Fire Scenario Soils

```python
from wepppy.wepp.soils.soilsdb import read_disturbed_wepp_soil_fire_pars
from wepppy.wepp.soils.utils import WeppSoilUtil

# Map of subcatchments to texture
subcatchments = {
    'sub1': 'loam',
    'sub2': 'silt loam',
    'sub3': 'sand loam',
}

# Generate pre/post fire soils
for sub_id, texture in subcatchments.items():
    # Pre-fire (library soil)
    from wepppy.wepp.soils.soilsdb import get_soil
    pre_fire = WeppSoilUtil(get_soil(f'Forest/Forest {texture}.sol'))
    pre_fire.write(f'/scenario/pre_fire/{sub_id}.sol')
    
    # Post-fire (high severity parameters)
    fire_ofe = read_disturbed_wepp_soil_fire_pars(
        simple_texture=texture,
        fire_severity='high'
    )
    
    # Build burned soil from OFE
    burned = WeppSoilUtil(get_soil(f'Forest/High sev fire-{texture}.sol'))
    burned.write(f'/scenario/post_fire/{sub_id}.sol')
```

### Scenario 3: Calibrate Against Library Reference

```python
from wepppy.wepp.soils.soilsdb import get_soil
from wepppy.wepp.soils.utils import WeppSoilUtil

# Load field-derived soil
field_soil = WeppSoilUtil('/field_data/measured_soil.sol')

# Load closest library reference
ref_soil = WeppSoilUtil(get_soil('Forest/Forest loam.sol'))

# Compare erodibility
print("Parameter Comparison:")
print(f"{'Param':<10} {'Field':<12} {'Reference':<12} {'Ratio':<8}")
print("-" * 45)

ki_field = field_soil.obj['ofes'][0]['ki']
ki_ref = ref_soil.obj['ofes'][0]['ki']
print(f"{'ki':<10} {ki_field:<12,.0f} {ki_ref:<12,.0f} {ki_field/ki_ref:<8.2f}")

kr_field = field_soil.obj['ofes'][0]['kr']
kr_ref = ref_soil.obj['ofes'][0]['kr']
print(f"{'kr':<10} {kr_field:<12.6f} {kr_ref:<12.6f} {kr_field/kr_ref:<8.2f}")

ksat_field = field_soil.avke
ksat_ref = ref_soil.avke
print(f"{'ksat':<10} {ksat_field:<12.2f} {ksat_ref:<12.2f} {ksat_field/ksat_ref:<8.2f}")
```

### Scenario 4: Extract Summary Statistics

```python
from wepppy.wepp.soils.soilsdb import load_db, get_soil
from wepppy.wepp.soils.utils import WeppSoilUtil
import csv

# Load all forest soils
soils = load_db()
forest_files = [s for s in soils if 'Forest/' in s and s.endswith('.sol')]

# Extract parameters
data = []
for soil_path in forest_files:
    soil = WeppSoilUtil(get_soil(soil_path))
    ofe = soil.obj['ofes'][0]
    
    data.append({
        'file': soil_path,
        'texture': soil.simple_texture,
        'clay': soil.clay,
        'sand': soil.sand,
        'albedo': ofe['salb'],
        'ki': ofe['ki'],
        'kr': ofe['kr'],
        'avke': soil.avke,
        'depth': soil.soil_depth,
    })

# Write summary
with open('forest_soils_summary.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

print(f"Exported {len(data)} soils to forest_soils_summary.csv")
```

### Scenario 5: Migrate Legacy Database to Modern Format

```python
from wepppy.wepp.soils.soilsdb import load_db, get_soil
from wepppy.wepp.soils.utils import WeppSoilUtil
from pathlib import Path

# Load legacy collection
soils = load_db()
legacy_soils = [s for s in soils if 'Forest2006/' in s and s.endswith('.sol')]

# Create output directory
out_dir = Path('/migration/forest_7778')
out_dir.mkdir(parents=True, exist_ok=True)

# Migrate each soil
for soil_rel in legacy_soils:
    soil = WeppSoilUtil(get_soil(soil_rel))
    
    # Skip if already modern
    if soil.datver == 7778.0:
        print(f"Skipping {soil_rel} (already 7778)")
        continue
    
    # Migrate to 7778
    modern = soil.to7778(hostname='migration.server.edu')
    
    # Write with same filename
    out_fn = out_dir / Path(soil_rel).name
    modern.write(str(out_fn))
    
    print(f"Migrated {soil_rel}: v{soil.datver} → v7778")
```

## Integration with NoDb Controllers

### Soils Controller

The Soils controller references library soils when SSURGO data is unavailable:

```python
from wepppy.nodb.core import Soils
from wepppy.wepp.soils.soilsdb import load_db, get_soil

soils = Soils.getInstance(wd)

# Browse library for fallback soils
available = load_db()
print(f"Library contains {len(available)} reference soils")

# Use library soil when SSURGO query fails
if soils.ssurgo_status == 'unavailable':
    fallback_path = get_soil('Forest/Forest loam.sol')
    # Apply to all subcatchments...
```

### Disturbed Lands Controller

The Disturbed controller uses `read_disturbed_wepp_soil_fire_pars()` to apply standardized burn severity adjustments:

```python
from wepppy.nodb.mods import Disturbed
from wepppy.wepp.soils.soilsdb import read_disturbed_wepp_soil_fire_pars

disturbed = Disturbed.getInstance(wd)

# Retrieve reference fire parameters for high severity loam
fire_pars = read_disturbed_wepp_soil_fire_pars(
    simple_texture='loam',
    fire_severity='high'
)

# Parameters used to guide burn severity transformations
# (actual implementation applies via WeppSoilUtil.to9003())
```

## Developer Notes

### Adding New Library Soils

To add new pre-built soils to the library:

1. **Choose appropriate directory:**
   - `Database/<state>/` - For NRCS soil series
   - `Forest/` - For standardized forest/rangeland/disturbed soils (7778)
   - `Forest2006/` - Only for legacy compatibility (do not extend)

2. **Validate WEPP format:**
   ```python
   from wepppy.wepp.soils.utils import WeppSoilUtil
   
   soil = WeppSoilUtil('/path/to/new_soil.sol')
   assert soil.datver in [7778.0, 2006.2, 9001, 9002, 9003, 9005]
   print(f"Validated: {soil.obj['ofes'][0]['slid']}")
   ```

3. **Add to version control:**
   ```bash
   git add wepppy/wepp/soils/soilsdb/data/<category>/<soil_name>.sol
   git commit -m "Add <soil_name> to soilsdb library"
   ```

4. **Update CSV summaries if extending Forest collection:**
   ```bash
   # Regenerate Forest Soils Summary.csv from .sol files
   python tools/regenerate_forest_summary.py
   ```

5. **Test library loading:**
   ```python
   from wepppy.wepp.soils.soilsdb import load_db, get_soil
   
   soils = load_db()
   assert '<category>/<soil_name>.sol' in soils
   
   path = get_soil('<category>/<soil_name>.sol')
   assert os.path.exists(path)
   ```

### Extending `read_disturbed_wepp_soil_fire_pars()`

To add new texture or severity combinations:

1. **Add soil files to `Forest/` collection:**
   ```
   Forest/High sev fire-<texture>.sol
   Forest/Low sev fire-<texture>.sol
   ```

2. **Update function logic in `__init__.py`:**
   ```python
   elif simple_texture == 'new_texture':
       if fire_severity == 'high':
           fn = _join(_data_dir, 'Forest', 'High sev fire-new_texture.sol')
       else:
           fn = _join(_data_dir, 'Forest', 'Low sev fire-new_texture.sol')
   ```

3. **Add assertion for new texture:**
   ```python
   valid_textures = ['silt loam', 'loam', 'sand loam', 'clay loam', 'new_texture']
   assert simple_texture in valid_textures, f"Unsupported texture: {simple_texture}"
   ```

4. **Add tests:**
   ```python
   def test_new_texture_fire_pars():
       ofe = read_disturbed_wepp_soil_fire_pars('new_texture', 'high')
       assert ofe['texid'] == 'new_texture'
       assert ofe['ki'] > 0
   ```

### Database Organization

**State Directory Naming:**
- Use lowercase 2-letter state abbreviations: `ak`, `ca`, `id`, etc.
- U.S. territories: `pr` (Puerto Rico), `vi` (Virgin Islands), etc.

**File Naming Convention:**
```
<SERIES_NAME>(<TEXTURE_ABBREV>).sol
```

**Texture Abbreviations:**
- `SIL` - Silt loam
- `L` - Loam
- `SL` - Sandy loam
- `CL` - Clay loam
- `SICL` - Silty clay loam
- `SC` - Sandy clay
- `C` - Clay
- `S` - Sand
- `LS` - Loamy sand

**Example:**
```
Database/id/PALOUSE(SIL).sol     # Palouse silt loam
Database/ca/YOLO(L).sol          # Yolo loam
Database/mt/BOZEMAN(SICL).sol    # Bozeman silty clay loam
```

### Testing Library Access

```python
import pytest
from wepppy.wepp.soils.soilsdb import load_db, get_soil, read_disturbed_wepp_soil_fire_pars
from wepppy.wepp.soils.utils import WeppSoilUtil

def test_load_db():
    soils = load_db()
    assert len(soils) > 0
    assert any('Forest/' in s for s in soils)
    assert any('Database/' in s for s in soils)

def test_get_soil_valid():
    path = get_soil('Forest/Forest loam.sol')
    assert os.path.exists(path)
    assert path.endswith('Forest loam.sol')

def test_get_soil_invalid():
    with pytest.raises(AssertionError):
        get_soil('nonexistent/soil.sol')

def test_read_fire_pars():
    for texture in ['loam', 'silt loam', 'sand loam', 'clay loam']:
        for severity in ['high', 'low']:
            ofe = read_disturbed_wepp_soil_fire_pars(texture, severity)
            assert ofe['texid'] == texture
            assert ofe['ki'] > 0
            assert ofe['kr'] > 0
            assert len(ofe['horizons']) >= 1

def test_library_soil_loading():
    soil = WeppSoilUtil(get_soil('Forest/Forest loam.sol'))
    assert soil.simple_texture in ['loam', 'silt loam', 'sand loam', 'clay loam']
    assert soil.soil_depth > 0
    assert soil.datver in [7778.0, 2006.2]
```

### Performance Considerations

**Library Loading:** `load_db()` performs filesystem glob operations. For applications accessing many soils, cache the result:

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def cached_load_db():
    from wepppy.wepp.soils.soilsdb import load_db
    return load_db()

# Use cached version
soils = cached_load_db()
```

**Soil File Loading:** Each `WeppSoilUtil()` call parses the `.sol` file. For batch operations, consider:

1. **Pre-load to YAML/BSON:**
   ```python
   # One-time conversion
   soil = WeppSoilUtil(get_soil('Forest/Forest loam.sol'))
   soil.dump_yaml('/cache/forest_loam.yaml')
   
   # Faster subsequent loads
   soil = WeppSoilUtil('/cache/forest_loam.yaml')
   ```

2. **Multiprocessing for batch migration:**
   ```python
   from concurrent.futures import ProcessPoolExecutor
   
   def process_soil(soil_path):
       from wepppy.wepp.soils.soilsdb import get_soil
       from wepppy.wepp.soils.utils import WeppSoilUtil
       soil = WeppSoilUtil(get_soil(soil_path))
       # Process...
       return result
   
   with ProcessPoolExecutor(max_workers=8) as executor:
       results = executor.map(process_soil, soil_list)
   ```

## Known Limitations

### State Coverage

Not all U.S. states have comprehensive Database collections. Coverage depends on NRCS data availability and historical WEPP exports.

**Well-Covered States:** Idaho, Montana, Wyoming, Oregon, Washington, California, North Carolina

**Limited Coverage:** Some Eastern and Southern states

### Texture Gaps

`read_disturbed_wepp_soil_fire_pars()` only supports 4 texture classes:
- loam
- silt loam
- sand loam
- clay loam

Soils with other USDA textures (clay, sandy clay, etc.) will raise `AssertionError`.

**Workaround:** Map to nearest supported texture or extend library (see [Developer Notes](#developer-notes)).

### Version Consistency

Database collection contains mixed WEPP versions (97.5, 2006.2, 7778). Applications requiring consistent versions should:

1. Filter by version:
   ```python
   from wepppy.wepp.soils.utils import WeppSoilUtil
   from wepppy.wepp.soils.soilsdb import load_db, get_soil
   
   soils_7778 = []
   for soil_path in load_db():
       soil = WeppSoilUtil(get_soil(soil_path))
       if soil.datver == 7778.0:
           soils_7778.append(soil_path)
   ```

2. Migrate to target version:
   ```python
   soil = WeppSoilUtil(get_soil('Database/id/PALOUSE(SIL).sol'))
   if soil.datver != 7778.0:
       soil = soil.to7778()
   ```

### Nested Directory Exclusion

`load_db()` excludes files in nested subdirectories within state folders. Only files directly under `Database/<state>/` are included.

**Current Behavior:**
```
Database/id/PALOUSE(SIL).sol        ✓ Included
Database/id/subset/ANOTHER(L).sol   ✗ Excluded
```

This is intentional to avoid including temporary or experimental files. To include nested files, modify the glob pattern in `load_db()`.

## Further Reading

### Related Modules
- [wepppy.wepp.soils.utils](../utils/README.md) - WeppSoilUtil for soil file manipulation
- [wepppy.soils.ssurgo](../../../soils/README.md) - SSURGO data acquisition
- [wepppy.nodb.core.soils](../../../nodb/core/README.md#soils-controller) - Soils NoDb controller
- [wepppy.wepp.soils.horizon_mixin](../horizon_mixin.py) - Erodibility calculations

### WEPP Documentation
- [Soil File Specification](../../../weppcloud/routes/usersum/input-file-specifications/soil-file.spec.md) - WEPP format reference
- [WEPP User Summary](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum.pdf) - Official WEPP documentation

### Scientific References
- Elliot, W.J., Miller, I.S., Glaza, L. (2008). "Disturbed WEPP (Draft 2/08) WEPP FuME, FS WEPP, and WEPP:Road - Forest Service Interfaces for the WEPP Model for Disturbed Forest and Range Runoff, Erosion and Sediment Delivery." U.S. Forest Service.
- Robichaud, P.R., Elliot, W.J., Pierson, F.B., Hall, D.E., Moffet, C.A. (2007). "Predicting postfire erosion and mitigation effectiveness with a web-based probabilistic erosion model." *Catena*, 71(2), 229-241.

## Credits

**Development:**
- William Elliot (USFS Rocky Mountain Research Station) - Forest soils calibration
- Roger Lew (rogerlew@gmail.com) - Library packaging and API

**Data Sources:**
- USDA Natural Resources Conservation Service - Soil survey database
- USFS Rocky Mountain Research Station - Forest disturbance parameters

**Funding:**
- U.S. Forest Service
- NSF Idaho EPSCoR Program (Award IIA-1301792)

**License:** BSD-3-Clause (see [license.txt](../../../../license.txt))
