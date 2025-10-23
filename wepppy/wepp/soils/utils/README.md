# WEPP Soil File Utilities
> Parsing, transforming, and exporting WEPP soil input files

> **See also:** [AGENTS.md](../../../../AGENTS.md) for coding conventions and [soil file specification](../../../weppcloud/routes/usersum/input-file-specifications/soil-file.spec.md) for WEPP format details.

## Overview

The `wepppy.wepp.soils.utils` package provides utilities for working with WEPP soil input files (`.sol`). These tools enable parsing existing WEPP soil files, transforming parameters, migrating between file format versions, and composing multi-OFE (Overland Flow Element) soil definitions.

**Key Capabilities:**
- Parse WEPP soil files (versions 97.5, 2006.2, 7777, 7778, 9001-9005)
- Modify soil parameters (saturation, conductivity, erodibility)
- Migrate between WEPP file format versions
- Apply parameter replacements for scenario modeling
- Compose multi-OFE soil files from single-OFE components
- Export to WEPP `.sol`, YAML, or BSON formats

**Primary Users:**
- NoDb controllers transforming soils for disturbed lands, BAER analysis, treatments
- Wildfire analysts applying burn severity adjustments
- Researchers modifying hydraulic parameters for sensitivity analysis
- WEPP model integrators reading soil properties from existing files

**Package Organization:**
```
wepppy/wepp/soils/utils/
├── __init__.py              # Package exports
├── wepp_soil_util.py        # WeppSoilUtil class (primary interface)
├── multi_ofe.py             # SoilMultipleOfeSynth for multi-OFE composition
└── utils.py                 # Texture classification and lookup helpers
```

## WeppSoilUtil Class

The primary interface for WEPP soil file manipulation. Loads a soil file into a structured dictionary, provides methods to transform parameters, and writes modified files back to disk.

### Basic Usage

```python
from wepppy.wepp.soils.utils import WeppSoilUtil

# Load a WEPP soil file
soil = WeppSoilUtil('/path/to/soil.sol')

# Access properties
print(f"Clay: {soil.clay}%, Sand: {soil.sand}%")
print(f"Texture: {soil.simple_texture}")
print(f"Soil depth: {soil.soil_depth} mm")

# Modify parameters
soil.modify_initial_sat(0.85)  # Set 85% saturation
soil.modify_kslast(0.5)         # Adjust restrictive layer conductivity

# Write modified soil
soil.write('/path/to/modified_soil.sol')
```

### Constructor

```python
WeppSoilUtil(
    fn: str,
    compute_erodibilities: bool = False,
    compute_conductivity: bool = False
)
```

**Parameters:**
- `fn` - Path to `.sol`, `.yaml`, or `.bson` file
- `compute_erodibilities` - Recalculate interrill/rill/shear from texture (first horizon)
- `compute_conductivity` - Recalculate hydraulic conductivity using WEPP formulas

**Supported File Formats:**
- `.sol` - Native WEPP soil files (all versions)
- `.yaml` - YAML serialization of soil structure
- `.bson` - Binary JSON serialization

### Key Properties

#### Texture and Composition

```python
soil.clay          # Clay percentage (first horizon)
soil.sand          # Sand percentage (first horizon)
soil.bd            # Bulk density (g/cm³)
soil.rock          # Rock fragment percentage
soil.simple_texture # Coarse classification: 'silt loam', 'loam', 'sand loam', 'clay loam'
soil.simple_texture_enum # Integer enum for texture (1-4)
```

#### Soil Profile

```python
soil.soil_depth    # Total soil depth (mm) from last horizon
soil.avke          # Effective hydraulic conductivity (mm/h)
soil.datver        # WEPP file format version (7778, 9002, etc.)
```

### Modification Methods

#### Adjust Initial Saturation

```python
soil.modify_initial_sat(initial_sat: float) -> None
```

Set the initial saturation level across all OFEs. Saturation is the fraction of pore space filled with water (0.0 - 1.0).

**Example:**
```python
# Set to 75% saturation (typical field capacity)
soil.modify_initial_sat(0.75)
```

#### Adjust Restrictive Layer Conductivity

```python
soil.modify_kslast(kslast: float, pars: Optional[Dict[str, Any]] = None) -> None
```

Update the hydraulic conductivity of the restrictive layer below the soil profile. Skips developed land use soils.

**Parameters:**
- `kslast` - Conductivity in mm/h
- `pars` - Optional parameter dict for provenance tracking

**Example:**
```python
# Reduce restrictive layer conductivity to simulate bedrock
soil.modify_kslast(0.1)
```

#### Clip Soil Depth

```python
soil.clip_soil_depth(max_depth: float) -> None
```

Limit cumulative soil depth while preserving horizon ordering. Horizons exceeding `max_depth` are truncated or removed.

**Example:**
```python
# Limit soil profile to 1 meter
soil.clip_soil_depth(1000.0)  # mm
```

### Version Migration Methods

#### Migrate to Version 7778

```python
soil.to7778(hostname: str = '') -> WeppSoilUtil
```

Returns a new `WeppSoilUtil` instance migrated to version 7778 format (full parameterization with anisotropy). Missing parameters estimated via Rosetta pedotransfer functions.

**Example:**
```python
# Migrate old soil file to modern format
soil_7778 = soil.to7778(hostname='analysis.server.edu')
soil_7778.write('/path/to/upgraded_soil.sol')
```

**Estimation Applied:**
- `bd` (bulk density): Default 1.4 g/cm³ if missing
- `fc` (field capacity): Rosetta prediction from texture
- `wp` (wilting point): Rosetta prediction from texture
- `ksat`: Rosetta prediction, converted cm/day → mm/h
- `anisotropy`: 10.0 for shallow layers (<50mm), 1.0 for deeper layers

#### Migrate to Disturbed Land Formats

```python
soil.to9001(replacements, h0_min_depth=None, h0_max_om=None, hostname='') -> WeppSoilUtil
soil.to9002(replacements, h0_min_depth=None, h0_max_om=None, hostname='') -> WeppSoilUtil
soil.to9003(replacements, h0_min_depth=None, h0_max_om=None, hostname='') -> WeppSoilUtil
soil.to9005(replacements, h0_min_depth=None, h0_max_om=None, hostname='') -> WeppSoilUtil
```

Migrate to disturbed land formats (9001-9005) with burn severity and hydrophobicity adjustments.

**Parameters:**
- `replacements` - Dict of parameter overrides (see below)
- `h0_min_depth` - Minimum depth for first horizon (mm)
- `h0_max_om` - Maximum organic matter for first horizon (filter if exceeded)
- `hostname` - Server name for provenance tracking

**Replacement Parameters:**
```python
replacements = {
    'ki': 5000000,              # Interrill erodibility
    'kr': 0.005,                # Rill erodibility
    'shcrit': 3.0,              # Critical shear stress
    'ksat': 10.0,               # Saturated conductivity (mm/h)
    'ksflag': 1,                # Enable WEPP internal adjustments
    'ksatadj': 1,               # Enable keff adjustments
    'ksatfac': 2.0,             # Lower bound for keff (9001)
    'ksatrec': 0.02,            # Recovery rate (9001)
    'lkeff': 1.0,               # Lower limit on keff (9003, 9005)
    'uksat': 50.0,              # Upper limit on keff (9005)
    'kslast': 0.01,             # Restrictive layer conductivity
    'luse': 'forest high sev',  # Disturbed class
    'stext': 'loam',            # Simple texture
}
```

**Multiplicative Replacements:**
Use `*` prefix to multiply existing values:
```python
replacements = {
    'ksat': '*0.5',  # Reduce conductivity by 50%
    'kr': '*2.0',    # Double rill erodibility
}
```

**Example - High Severity Burn:**
```python
burn_replacements = {
    'luse': 'forest high sev',
    'stext': 'loam',
    'ksatadj': 1,
    'lkeff': 1.0,     # Minimum keff = 1 mm/h
    'ki': '*1.5',     # Increase interrill erodibility
    'kr': '*2.0',     # Increase rill erodibility
}

burned_soil = soil.to9003(
    replacements=burn_replacements,
    h0_min_depth=100.0,  # Ensure first horizon ≥ 100mm
    hostname='fire-analysis.usda.gov'
)
burned_soil.write('/soils/burned_high_sev.sol')
```

**Version Differences:**
- **9001**: Exponential keff recovery (`ksatfac`, `ksatrec`)
- **9002**: Saxton & Rawls keff calculation with Rosetta van Genuchten parameters
- **9003**: Burn severity codes, lower keff limit (`lkeff`)
- **9005**: Revegetation modeling with upper keff limit (`uksat`), texture enum

### Internal Structure

The `WeppSoilUtil.obj` dictionary contains the parsed soil structure:

```python
{
    'header': [                 # Comment lines from file
        'WEPPcloud v.0.1.0',
        'Build Date: 2025-10-23',
        ...
    ],
    'datver': 7778.0,           # File format version
    'solcom': 'Any comments:',  # User comment line
    'ntemp': 1,                 # Number of OFEs
    'ksflag': 1,                # Conductivity adjustment flag
    'ofes': [                   # List of OFE definitions
        {
            'slid': 'Palouse',  # Soil name
            'texid': 'silt loam',
            'nsl': 4,           # Number of soil layers
            'salb': 0.23,       # Albedo
            'sat': 0.75,        # Initial saturation
            'ki': 2940000,      # Interrill erodibility
            'kr': 0.0041,       # Rill erodibility
            'shcrit': 3.5,      # Critical shear
            'avke': 14.58,      # Effective conductivity
            'luse': None,       # Disturbed class (9001+)
            'stext': None,      # Simple texture (9001+)
            'ksatadj': 0,       # keff adjustment flag (9001+)
            'horizons': [       # Soil layers
                {
                    'solthk': 210.0,   # Depth (mm)
                    'bd': 1.32,        # Bulk density
                    'ksat': 14.58,     # Conductivity
                    'anisotropy': 10.0,
                    'fc': 0.289,       # Field capacity
                    'wp': 0.132,       # Wilting point
                    'sand': 8.5,
                    'clay': 19.0,
                    'orgmat': 3.5,     # Organic matter
                    'cec': 18.6,
                    'rfg': 0.0,        # Rock fragments
                },
                # ... more horizons
            ],
            'res_lyr': {         # Restrictive layer
                'slflag': 1,
                'ui_bdrkth': 10000.0,
                'kslast': 0.00325,
            },
        },
    ],
    'res_lyr': {...},  # Redundant restrictive layer reference
}
```

### Serialization Methods

#### YAML Export

```python
soil.dump_yaml(dst: str) -> None
```

Export soil structure to YAML format for human-readable inspection or version control.

**Example:**
```python
soil.dump_yaml('/path/to/soil.yaml')
```

#### BSON Export

```python
soil.dump_bson(dst: str) -> None
```

Export to binary JSON for efficient storage or transmission.

**Example:**
```python
soil.dump_bson('/path/to/soil.bson')
```

#### WEPP File Output

```python
soil.write(fn: str) -> None
# or use str() for content without writing
content = str(soil)
```

Write WEPP-formatted `.sol` file. The `__str__()` method generates the exact WEPP format.

### Advanced Examples

#### Batch Transform for Wildfire Scenarios

```python
from glob import glob
from wepppy.wepp.soils.utils import WeppSoilUtil

# Process all soils in watershed
for soil_fn in glob('/watershed/soils/*.sol'):
    soil = WeppSoilUtil(soil_fn)
    
    # Determine burn severity from filename
    if 'high_sev' in soil_fn:
        severity = 'high sev'
        lkeff = 1.0  # Very low keff limit
    else:
        severity = 'low sev'
        lkeff = 5.0
    
    # Apply burn transformations
    burned = soil.to9003(
        replacements={
            'luse': f'forest {severity}',
            'stext': soil.simple_texture,
            'ksatadj': 1,
            'lkeff': lkeff,
            'ki': '*1.2',
            'kr': '*1.5',
        },
        h0_min_depth=100.0,
    )
    
    # Save to burn scenario directory
    out_fn = soil_fn.replace('/soils/', '/burn_soils/')
    burned.write(out_fn)
```

#### Sensitivity Analysis - Vary Conductivity

```python
soil = WeppSoilUtil('/base/soil.sol')

for multiplier in [0.5, 0.75, 1.0, 1.25, 1.5]:
    variant = soil.to7778()
    
    # Multiply all horizon conductivities
    for ofe in variant.obj['ofes']:
        for horizon in ofe['horizons']:
            horizon['ksat'] *= multiplier
    
    # Write scenario file
    variant.write(f'/scenarios/soil_ksat_{multiplier:.2f}.sol')
```

#### Migrate Legacy Soil Database

```python
from pathlib import Path

legacy_dir = Path('/legacy/soils')
modern_dir = Path('/modern/soils')
modern_dir.mkdir(exist_ok=True)

for sol_file in legacy_dir.glob('*.sol'):
    soil = WeppSoilUtil(str(sol_file))
    
    # Skip if already 7778
    if soil.datver == 7778.0:
        continue
    
    # Migrate to modern format
    modern = soil.to7778(hostname='migration-server')
    
    # Write with same filename
    modern.write(str(modern_dir / sol_file.name))
    
    print(f"Migrated {sol_file.name}: v{soil.datver} → v7778")
```

#### Extract Soil Properties for Reporting

```python
import csv
from wepppy.wepp.soils.utils import WeppSoilUtil

soils = [WeppSoilUtil(fn) for fn in soil_files]

with open('soil_summary.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['File', 'Texture', 'Clay%', 'Sand%', 'Depth(mm)', 'Albedo'])
    
    for soil in soils:
        writer.writerow([
            soil.fn,
            soil.simple_texture,
            f'{soil.clay:.1f}',
            f'{soil.sand:.1f}',
            f'{soil.soil_depth:.0f}',
            f'{soil.obj["ofes"][0]["salb"]:.3f}',
        ])
```

## SoilMultipleOfeSynth

Utility class for composing multi-OFE (Overland Flow Element) WEPP soil files from multiple single-OFE soil definitions.

### Purpose

WEPP models can have multiple OFEs representing different soil types along a hillslope profile. `SoilMultipleOfeSynth` combines individual soil files into a single multi-OFE file while ensuring format version consistency.

### Usage

```python
from wepppy.wepp.soils.utils import SoilMultipleOfeSynth

# Create synthesis object with stack of soil files
synthesis = SoilMultipleOfeSynth([
    '/soils/top_slope.sol',      # OFE 1
    '/soils/mid_slope.sol',      # OFE 2
    '/soils/bottom_slope.sol',   # OFE 3
])

# Write combined multi-OFE file
synthesis.write(
    dst_fn='/combined/hillslope.sol',
    ksflag=1  # Enable WEPP conductivity adjustments
)
```

### Methods

```python
SoilMultipleOfeSynth(stack: Optional[Iterable[str]] = None)
```

**Constructor Parameters:**
- `stack` - Iterable of soil file paths (one per OFE), ordered top to bottom

**Properties:**
- `num_ofes` - Number of OFEs in the stack
- `stack_of_fns` - Boolean indicating if all files exist

**Methods:**
- `write(dst_fn: str, ksflag: int = 0)` - Write multi-OFE file

### Example - Variable Soil Hillslope

```python
from wepppy.wepp.soils.utils import SoilMultipleOfeSynth

# Define soils for each hillslope segment
stack = [
    '/soils/ridge_top_sandy.sol',     # Well-drained ridge
    '/soils/backslope_loam.sol',      # Transitional slope
    '/soils/footslope_clayey.sol',    # Poorly-drained toe
]

synthesis = SoilMultipleOfeSynth(stack)
print(f"Combining {synthesis.num_ofes} soils")

# Write multi-OFE file
synthesis.write('/watershed/hillslope_001.sol', ksflag=1)
```

**Validation:**
All input soils must have the same WEPP file version. Mixing versions will raise an assertion error:
```
AssertionError: Soils must be of the same version ({7778.0, 2006.2})
```

## Utility Functions

### Texture Classification

```python
from wepppy.wepp.soils.utils import simple_texture, simple_texture_enum

# Classify texture from clay and sand percentages
texture = simple_texture(clay=25.0, sand=35.0)
# Returns: 'loam'

# Get integer enum (1-4)
enum = simple_texture_enum(clay=25.0, sand=35.0)
# Returns: 2
```

**Classification Logic:**
- `clay loam` (enum=1): High clay or low sand
- `loam` (enum=2): Balanced clay/sand
- `sand loam` (enum=3): High sand
- `silt loam` (enum=4): Low clay+sand

### Detailed Texture Classification

```python
from wepppy.wepp.soils.utils import soil_texture

# USDA texture class
texture = soil_texture(clay=25.0, sand=35.0)
# Returns: 'loam'
```

Returns full USDA soil texture classification (sand, loamy sand, sandy loam, loam, silt loam, silt, sandy clay loam, clay loam, silty clay loam, sandy clay, silty clay, clay).

### Soil Specialization Checks

```python
from wepppy.wepp.soils.utils import soil_specialization, soil_is_water

# Check for special soil types
spec = soil_specialization(soil_name='Urban_1')
# Returns: 'urban'

spec = soil_specialization(soil_name='Water')
# Returns: 'water'

# Quick water check
is_water = soil_is_water(soil_name='water_7778_2')
# Returns: True
```

### Modify Restrictive Layer Conductivity

```python
from wepppy.wepp.soils.utils import modify_kslast

# Update kslast in existing file
modify_kslast(
    fn='/path/to/soil.sol',
    kslast=0.5,
    datver=7778
)
```

## Integration with NoDb Controllers

The `WeppSoilUtil` class is heavily used by NoDb controllers for soil transformations:

### Soils Controller

```python
from wepppy.nodb.core import Soils
from wepppy.wepp.soils.utils import WeppSoilUtil

soils = Soils.getInstance(wd)

# Inspect generated soil properties
for mukey, summary in soils.soils.items():
    soil = WeppSoilUtil(summary.path)
    print(f"{mukey}: {soil.simple_texture}, depth={soil.soil_depth}mm")
```

### Disturbed Lands Controller

```python
from wepppy.nodb.mods import Disturbed

disturbed = Disturbed.getInstance(wd)

# Controller automatically transforms base soils using WeppSoilUtil
# to apply burn severity adjustments via to9002() or to9003()
disturbed.build_disturbed_soils()
```

### BAER Analysis

```python
from wepppy.nodb.mods import Baer

baer = Baer.getInstance(wd)

# Applies SoilReplacements using WeppSoilUtil transformations
baer.apply_soil_replacements()
```

## Developer Notes

### Adding New WEPP File Versions

To support a new WEPP file version (e.g., 9006):

1. **Update `_parse_sol()` to recognize the version:**
   ```python
   elif solwpv == 9006:
       ksatadj, luse, new_param, stext, lkeff = line
       line = shlex.split(lines[i])
       i += 1
   ```

2. **Add migration method:**
   ```python
   def to9006(self, replacements, ...) -> 'WeppSoilUtil':
       return self.to_over9000(replacements, ..., version=9006)
   ```

3. **Update `__str__()` and `__repr__()` to output new format:**
   ```python
   elif datver == 9006.0:
       _new_param = ofe['new_param']
       s.append(f"{_ksatadj}\t '{_luse}'\t {_new_param}\t ...")
   ```

4. **Update horizon line parsing if layer structure changes**

5. **Add tests in `tests/wepp/soils/utils/test_wepp_soil_util.py`**

### Testing Soil Transformations

```python
import pytest
from wepppy.wepp.soils.utils import WeppSoilUtil

def test_migration_to_7778():
    # Load legacy soil
    soil = WeppSoilUtil('tests/data/legacy_2006.sol')
    assert soil.datver == 2006.2
    
    # Migrate
    modern = soil.to7778()
    assert modern.datver == 7778.0
    
    # Verify all horizons have required parameters
    for ofe in modern.obj['ofes']:
        for horizon in ofe['horizons']:
            assert horizon['bd'] is not None
            assert horizon['ksat'] is not None
            assert horizon['anisotropy'] is not None

def test_parameter_replacement():
    soil = WeppSoilUtil('tests/data/base.sol')
    
    # Apply multiplicative replacement
    modified = soil.to9002(replacements={'ksat': '*0.5'})
    
    # Verify conductivity halved
    original_ksat = soil.obj['ofes'][0]['horizons'][0]['ksat']
    modified_ksat = modified.obj['ofes'][0]['horizons'][0]['ksat']
    assert modified_ksat == pytest.approx(original_ksat * 0.5)
```

### Provenance Tracking

All transformations append to the `header` list for full provenance:

```python
soil = WeppSoilUtil('base.sol')
soil.modify_initial_sat(0.80)
soil.to9003(replacements={'luse': 'forest high sev'})

# Header now contains:
# wepppy.wepp.soils.utils.WeppSoilUtil::modify_initial_sat(initial_sat=0.8)
# wepppy.wepp.soils.utils.WeppSoilUtil::9003migration
#   Build Date: 2025-10-23 14:32:15
#   Source File: server:/base.sol
#   Replacements
#   --------------------------
#   luse -> 'forest high sev'
```

These headers appear as comments in the output `.sol` file, providing audit trail for parameter modifications.

### Performance Considerations

**Parsing:** Typical `.sol` file (4-8 horizons) parses in <10ms.

**Migration:** `to7778()` with Rosetta predictions takes ~50-100ms per soil due to pedotransfer calculations.

**Batch Processing:** For large soil databases (>1000 files), consider:
- Pre-parsing to YAML/BSON for faster repeated access
- Multiprocessing for parallel transformations
- Caching `WeppSoilUtil` instances if reused

**Example - Parallel Migration:**
```python
from concurrent.futures import ProcessPoolExecutor
from wepppy.wepp.soils.utils import WeppSoilUtil

def migrate_soil(fn):
    soil = WeppSoilUtil(fn)
    modern = soil.to7778()
    modern.write(fn.replace('/old/', '/new/'))
    return fn

soil_files = glob('/old/soils/*.sol')

with ProcessPoolExecutor(max_workers=8) as executor:
    results = executor.map(migrate_soil, soil_files)
    
for result in results:
    print(f"Migrated {result}")
```

## Known Limitations

### Version Mixing

Multi-OFE files cannot mix WEPP versions. All component soils must be the same version before using `SoilMultipleOfeSynth`.

**Workaround:** Migrate all soils to target version first:
```python
soils = [WeppSoilUtil(fn).to7778() for fn in soil_files]
for i, soil in enumerate(soils):
    soil.write(f'/temp/soil_{i}.sol')

stack = [f'/temp/soil_{i}.sol' for i in range(len(soils))]
synthesis = SoilMultipleOfeSynth(stack)
synthesis.write('/final/multi_ofe.sol')
```

### Rosetta Dependency

Version migration methods (`to7778()`, `to9002()`, etc.) require the `rosetta` package for pedotransfer functions. Ensure it's installed:

```bash
pip install rosetta-soil
```

### Parameter Override Logic

The `_replace_parameter()` helper treats `None`, empty strings, and "none" (case-insensitive) as "do not replace." This prevents accidental nullification but may surprise users expecting explicit `None` to clear values.

### Organic Matter Filtering

The `h0_max_om` parameter in migration methods filters out the first horizon if organic matter exceeds the threshold. This is irreversible - the horizon is removed from the output. Use cautiously.

## Further Reading

### WEPP Documentation
- [Soil File Specification](../../../weppcloud/routes/usersum/input-file-specifications/soil-file.spec.md) - Complete WEPP format specification
- [WEPP Soil Parameters](../README.md) - Parameter descriptions and version history
- [WEPP User Summary](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum.pdf) - Official WEPP model documentation

### Related Modules
- [wepppy.soils.ssurgo](../../../soils/README.md) - SSURGO data acquisition and WEPP file generation
- [wepppy.wepp.soils.horizon_mixin](../horizon_mixin.py) - Erodibility and conductivity calculations
- [wepppy.wepp.soils.soilsdb](../soilsdb/) - Pre-built WEPP soil library
- [wepppy.nodb.core.soils](../../../nodb/core/README.md#soils-controller) - Soils NoDb controller

### Scientific References
- Saxton, K.E., Rawls, W.J. (2006). "Soil Water Characteristic Estimates by Texture and Organic Matter for Hydrologic Solutions." *Soil Science Society of America Journal*, 70(5), 1569-1578.
- Schaap, M.G., Leij, F.J., van Genuchten, M.Th. (2001). "ROSETTA: a computer program for estimating soil hydraulic parameters with hierarchical pedotransfer functions." *Journal of Hydrology*, 251(3-4), 163-176.

## Credits

**Development:**
- Roger Lew (rogerlew@gmail.com) - Primary developer
- University of Idaho - Institutional support

**Funding:**
- NSF Idaho EPSCoR Program (Award IIA-1301792)
- National Science Foundation

**License:** BSD-3-Clause (see [license.txt](../../../../license.txt))
