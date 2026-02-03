# Disturbed WEPP Test Matrix Implementation Plan

## Overview

This document describes the implementation plan for a comprehensive test script that exercises the disturbed/WEPP nodb code by running the full matrix of:

- **4 soil textures**: clay loam, loam, sand loam, silt loam
- **4 burn severities**: unburned, low, moderate, high
- **3 vegetation types**: forest, shrub, tall grass

**Total combinations**: 4 × 4 × 3 = **48 pseudo-hillslopes**

## Test Objectives

1. Exercise the `Disturbed` module's soil modification workflow via `disturbed_land_soil_lookup.csv`
2. Generate **9002 format** disturbed soils using `WeppSoilUtil.to_over9000()`
3. Verify management file selection for each disturbance class
4. Run WEPP hillslope simulations with **graphical output enabled**
5. Compare erosion/runoff outputs across the severity gradient for each veg/texture pair

---

## Configuration

### Soil Version: 9002

This test uses the **disturbed9002** configuration, which sets `sol_ver = 9002`.

**Key 9002 features over 7778:**
- OFE header includes: `ksatadj`, `luse`, `stext`, `ksatfac`, `ksatrec`
- Tracks disturbance class (`luse`) and texture (`stext`) in the soil file
- Supports hydrophobicity adjustments via `ksatadj` flag
- Van Genuchten hydraulic parameters in horizon data

**Reference config**: `wepppy/nodb/configs/disturbed9002.cfg`
```ini
[disturbed]
sol_ver = 9002

[wepp]
wepp_ui = true
snow = true
```

---

## Architecture

### High-Level Approach

The test will use the **Disturbed module** directly to exercise the soil/management modification workflow:

1. **Use `read_disturbed_land_soil_lookup()`** to load the lookup table
2. **Generate 9002 soils** using `WeppSoilUtil.to_over9000(replacements, version=9002)`
3. **Copy management files** from the UnDisturbed templates
4. **Create custom hillslope.template** with graphical output enabled
5. **Execute WEPP** via `wepp_runner.run_hillslope()`
6. **Analyze graphical and pass file outputs**

### Directory Structure

```
tests/disturbed/
├── PLAN.md                      # This document
├── test_disturbed_matrix.py     # Main test script
├── conftest.py                  # pytest fixtures
├── data/
│   ├── canonical_slope.slp      # From /wc1/runs/ca/caller-footwork/.../hill_232.slp
│   ├── test_climate.cli         # From /wc1/runs/ho/hopped-up-titillation/climate/wepp.cli
│   └── hillslope_graph.template # Custom template with graphics enabled
└── output/                      # Generated during test runs (gitignored)
    └── run_<timestamp>/
        ├── runs/
        │   ├── p1.slp, p1.man, p1.sol, p1.cli, p1.run
        │   ├── ...
        │   └── output/
        │       ├── H1.pass.dat, H1.loss.dat, H1.wat.dat
        │       ├── H1.graph.dat  # Graphical output
        │       └── ...
```

---

## Test Matrix Definition

### Soil Textures (from `simple_texture()`)

| Enum | Texture    | Representative Clay% | Representative Sand% | Canonical Soil File |
|------|------------|---------------------|---------------------|---------------------|
| 1    | clay loam  | 30.0                | 25.0                | `Forest/Forest clay loam.sol` |
| 2    | loam       | 20.0                | 45.0                | `Forest/Forest loam.sol` |
| 3    | sand loam  | 10.0                | 65.0                | `Forest/Forest sandy loam.sol` |
| 4    | silt loam  | 15.0                | 25.0                | `Forest/Forest silt loam.sol` |

**Source**: `wepppy/wepp/soils/soilsdb/data/Forest/`

### Burn Severities

| Code | Severity   | Disturbed Class Suffix | SBS Class |
|------|------------|------------------------|-----------|
| 0    | unburned   | (base class name)      | 130       |
| 1    | low        | `low sev fire`         | 131       |
| 2    | moderate   | `moderate sev fire`    | 132       |
| 3    | high       | `high sev fire`        | 133       |

### Vegetation Types

| Veg Type   | Base Disturbed Class | Unburned Management File | Burn Management Pattern |
|------------|---------------------|-------------------------|------------------------|
| forest     | `forest`            | `UnDisturbed/Old_Forest.man` | `UnDisturbed/{Low,Moderate,High}_Severity_Fire.man` |
| shrub      | `shrub`             | `UnDisturbed/Shrub.man` | `UnDisturbed/Shrub_{Low,Moderate,High}_Severity_Fire.man` |
| tall grass | `tall grass`        | `UnDisturbed/Tall_Grass.man` | `UnDisturbed/Grass_{Low,Moderate,High}_Severity_Fire.man` |

### Full Disturbed Class Matrix

| Veg Type   | Unburned      | Low Severity              | Moderate Severity              | High Severity              |
|------------|---------------|---------------------------|--------------------------------|----------------------------|
| forest     | `forest`      | `forest low sev fire`     | `forest moderate sev fire`     | `forest high sev fire`     |
| shrub      | `shrub`       | `shrub low sev fire`      | `shrub moderate sev fire`      | `shrub high sev fire`      |
| tall grass | `tall grass`  | `grass low sev fire`      | `grass moderate sev fire`      | `grass high sev fire`      |

---

## Canonical Hillslope Slope Profile (200m)

Based on analysis of `/wc1/runs/` slope files, a **representative 200m hillslope** was selected.

### Source: `/wc1/runs/ca/caller-footwork/watershed/slope_files/hillslopes/hill_232.slp`

**Copy this file to `tests/disturbed/data/canonical_slope.slp`**

```
2023.3
1
201.6836 102.4 1163.4
6 87.9
0.0000, 0.4249 0.1667, 0.4848 0.3333, 0.4893 0.5000, 0.4522 0.8333, 0.2435 1.0000, 0.1671
```

**Parameters**:
- **Format version**: 2023.3
- **OFEs**: 1 (single overland flow element)
- **Length**: 201.68 m
- **Field width**: 102.4 m
- **Elevation**: 1163.4 m (reference)
- **Segments**: 6 profile points
- **Slope profile**: Variable, steeper in middle (42-49%), gentler at ends (17-24%)
- **Vertical rise**: 87.9 m
- **Average slope**: ~43% (0.43 rise/run) - steep forested mountain terrain

---

## WEPP Graphical Output Configuration

The default `hillslope.template` has graphical output disabled (line 17: `No`). We need a custom template with graphics enabled.

### Custom Template: `hillslope_graph.template`

```
m                               # metric units
Yes                             # not watershed option
1                               # storm option
1                               # hillslope version
Yes                             # pass file output
../output/H{wepp_id}.pass.dat   #
1                               # abbreviated annual soil loss output
No                              # initial condition scenario output
../output/H{wepp_id}.loss.dat   #
Yes                             # water balance output
../output/H{wepp_id}.wat.dat    #
No                              # crop output
Yes                             # soil output
../output/H{wepp_id}.soil.dat   #
Yes                             # distance and sediment loss
../output/H{wepp_id}.plot.dat   #
Yes                             # large graphics output <<< CHANGED
../output/H{wepp_id}.graph.dat  # <<< ADDED
Yes                             # event by event output
../output/H{wepp_id}.ebe.dat    #
Yes                             # element output
../output/H{wepp_id}.element.dat    #
No                              # final summary output
No                              # daily winter output
No                              # plant yield output
{man_relpath}p{wepp_id}.man     # management filepath
{slp_relpath}p{wepp_id}.slp     # slope filepath
{cli_relpath}p{wepp_id}.cli     # climate filepath
{sol_relpath}p{wepp_id}.sol     # soil filepath
0                               # irrigation option
{sim_years}                     # years to simulate
0                               # erosion calculation
```

**Key change**: Line 17 changed from `No` to `Yes` and added graph output path on line 18.

---

## Climate File

### Selected Climate: MC KENZIE BRIDGE RS, OR

**Source**: `/wc1/runs/ho/hopped-up-titillation/climate/wepp.cli`

**Copy this file to `tests/disturbed/data/test_climate.cli`**

**Climate Characteristics**:
- **Station**: MC KENZIE BRIDGE RS, OR
- **CLIGEN Version**: 5.32300
- **Location**: 44.17°N, -122.17°W, Elevation 420m
- **Simulation Period**: 100 years (2020-2119)
- **Annual Precipitation**: 1,193.7 mm/year (moderately wet)
- **Winter Conditions**: Regular freezing (-1.2°C Jan avg min, -7.8°C observed min)

**Monthly Average Temperatures (°C)**:
| Month | Max | Min |
|-------|-----|-----|
| Jan   | 5.9 | -1.2 |
| Feb   | 8.8 | -0.6 |
| Mar   | 12.6 | 0.6 |
| Dec   | 5.1 | -1.1 |

**Monthly Precipitation (mm)**:
```
Jan: 157.7  Feb: 117.4  Mar: 130.2  Apr: 119.4
May:  77.7  Jun:  59.5  Jul:  21.9  Aug:  33.0
Sep:  49.9  Oct:  89.6  Nov: 154.1  Dec: 183.3
```

This climate provides:
- 100 years of continuous simulation data
- Moderately wet Pacific Northwest conditions
- Regular below-freezing winter days for freeze-thaw testing
- Seasonal precipitation pattern (wet winters, dry summers)

---

## Implementation Components

### 1. Soil Parameter Lookup (via Disturbed module)

**File**: `wepppy/nodb/mods/disturbed/disturbed.py`

```python
from wepppy.nodb.mods.disturbed import read_disturbed_land_soil_lookup

# Load the lookup table
lookup_path = 'wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv'
lookup_d = read_disturbed_land_soil_lookup(lookup_path)

# Key format: (texture, disturbed_class)
# Example: ('loam', 'forest high sev fire')
key = ('loam', 'forest high sev fire')
replacements = lookup_d.get(key)

# Returns dict with:
# {
#     'ki': '1000000', 'kr': '0.0001', 'shcrit': '1', 'avke': '15',
#     'ksatadj': '1', 'ksatfac': '100', 'ksatrec': '0.3',
#     'pmet_kcb': '0.95', 'pmet_rawp': '0.8',
#     'rdmax': '0.3', 'xmxlai': '2',
#     'keffflag': '1', 'lkeff': '0.1',
#     'plant.data.decfct': '1', 'plant.data.dropfc': '1'
# }
```

### 2. Soil File Generation (9002 format)

**File**: `wepppy/wepp/soils/utils/wepp_soil_util.py`

```python
from wepppy.wepp.soils.utils import WeppSoilUtil

# Load base soil
base_soil_path = 'wepppy/wepp/soils/soilsdb/data/Forest/Forest loam.sol'
soil_u = WeppSoilUtil(base_soil_path)

# Get texture for lookup
texid = soil_u.simple_texture  # e.g., 'loam'

# Get replacements from lookup table
disturbed_class = 'forest high sev fire'
key = (texid, disturbed_class)
replacements = lookup_d.get(key, {})

# Add 9002-specific metadata
replacements['luse'] = disturbed_class
replacements['stext'] = texid

# Generate 9002 disturbed soil
disturbed_soil = soil_u.to_over9000(
    replacements=replacements,
    h0_max_om=None,
    version=9002
)

# Write to destination
disturbed_soil.write('output/runs/p1.sol')
```

### 3. Management File Preparation

```python
from wepppy.wepp.management import Management
from pathlib import Path
import shutil

MAN_DATA_DIR = Path('wepppy/wepp/management/data')

MANAGEMENT_FILES = {
    # Unburned (severity=0)
    ('forest', 0):     'UnDisturbed/Old_Forest.man',
    ('shrub', 0):      'UnDisturbed/Shrub.man',
    ('tall grass', 0): 'UnDisturbed/Tall_Grass.man',

    # Low severity (severity=1)
    ('forest', 1):     'UnDisturbed/Low_Severity_Fire.man',
    ('shrub', 1):      'UnDisturbed/Shrub_Low_Severity_Fire.man',
    ('tall grass', 1): 'UnDisturbed/Grass_Low_Severity_Fire.man',

    # Moderate severity (severity=2)
    ('forest', 2):     'UnDisturbed/Moderate_Severity_Fire.man',
    ('shrub', 2):      'UnDisturbed/Shrub_Moderate_Severity_Fire.man',
    ('tall grass', 2): 'UnDisturbed/Grass_Moderate_Severity_Fire.man',

    # High severity (severity=3)
    ('forest', 3):     'UnDisturbed/High_Severity_Fire.man',
    ('shrub', 3):      'UnDisturbed/Shrub_High_Severity_Fire.man',
    ('tall grass', 3): 'UnDisturbed/Grass_High_Severity_Fire.man',
}

def prepare_management(veg_type: str, severity: int, dst_path: Path, sim_years: int):
    """Prepare management file for simulation."""
    man_relpath = MANAGEMENT_FILES[(veg_type, severity)]
    man_path = MAN_DATA_DIR / man_relpath

    # Load and build multi-year management
    man = Management.load(str(man_path))
    multi_year = man.build_multiple_year_man(years=sim_years)

    with open(dst_path, 'w') as fp:
        fp.write(str(multi_year))
```

### 4. WEPP Execution with Custom Template

```python
from wepp_runner import run_hillslope
from pathlib import Path

def make_hillslope_run_with_graphics(wepp_id: int, sim_years: int, runs_dir: Path):
    """Create .run file with graphical output enabled."""
    template = '''m
Yes
1
1
Yes
../output/H{wepp_id}.pass.dat
1
No
../output/H{wepp_id}.loss.dat
Yes
../output/H{wepp_id}.wat.dat
No
Yes
../output/H{wepp_id}.soil.dat
Yes
../output/H{wepp_id}.plot.dat
Yes
../output/H{wepp_id}.graph.dat
Yes
../output/H{wepp_id}.ebe.dat
Yes
../output/H{wepp_id}.element.dat
No
No
No
p{wepp_id}.man
p{wepp_id}.slp
p{wepp_id}.cli
p{wepp_id}.sol
0
{sim_years}
0
'''
    run_content = template.format(wepp_id=wepp_id, sim_years=sim_years)
    run_path = runs_dir / f'p{wepp_id}.run'
    run_path.write_text(run_content)

# Execute WEPP
success, wepp_id, elapsed = run_hillslope(
    wepp_id=1,
    runs_dir=str(runs_dir),
    wepp_bin='latest',
    timeout=120
)
```

---

## Disturbed Class Mapping

```python
DISTURBED_CLASSES = {
    # Unburned
    ('forest', 0):     'forest',
    ('shrub', 0):      'shrub',
    ('tall grass', 0): 'tall grass',

    # Low severity
    ('forest', 1):     'forest low sev fire',
    ('shrub', 1):      'shrub low sev fire',
    ('tall grass', 1): 'grass low sev fire',

    # Moderate severity
    ('forest', 2):     'forest moderate sev fire',
    ('shrub', 2):      'shrub moderate sev fire',
    ('tall grass', 2): 'grass moderate sev fire',

    # High severity
    ('forest', 3):     'forest high sev fire',
    ('shrub', 3):      'shrub high sev fire',
    ('tall grass', 3): 'grass high sev fire',
}
```

---

## Expected Behavior and Validation

### Soil Parameter Scaling (from lookup CSV)

For **loam** texture:

| Parameter | Forest (unburned) | Forest Low | Forest Moderate | Forest High |
|-----------|-------------------|------------|-----------------|-------------|
| ki        | 400000           | 1000000    | 1000000         | 1000000     |
| kr        | 3e-05            | 8e-05      | 8e-05           | 0.0001      |
| shcrit    | 1                | 1          | 1               | 1           |
| avke      | 50               | 20         | 20              | 15          |
| ksatadj   | 0                | 0          | 0               | 1           |
| ksatfac   | 1.5              | 1.3        | 1.3             | 100         |
| lkeff     | -9999            | 10         | 1               | 0.1         |

**Expected trends**:
- `ki` (interrill erodibility) increases with severity
- `kr` (rill erodibility) increases with severity
- `avke` (effective conductivity) decreases with severity → more runoff
- `ksatadj=1` for high severity enables hydrophobicity effects
- `lkeff` decreases dramatically for high severity (more runoff)

### Output Validation

1. **WEPP completes successfully** for all 48 combinations
2. **Soil loss increases** with burn severity for each veg type
3. **Runoff increases** with burn severity (due to lower avke/lkeff)
4. **Graphical output files** (`H*.graph.dat`) are produced
5. **No negative values** in erosion/runoff outputs

---

## Implementation Phases

### Phase 1: Infrastructure Setup
- [ ] Create `tests/disturbed/data/` directory
- [ ] Copy slope: `/wc1/runs/ca/caller-footwork/watershed/slope_files/hillslopes/hill_232.slp` → `data/canonical_slope.slp`
- [ ] Copy climate: `/wc1/runs/ho/hopped-up-titillation/climate/wepp.cli` → `data/test_climate.cli`
- [ ] Create `hillslope_graph.template` with graphics enabled
- [ ] Create pytest fixtures (`conftest.py`)

### Phase 2: Core Test Implementation
- [ ] Implement soil lookup via `read_disturbed_land_soil_lookup()`
- [ ] Implement 9002 soil generation with `WeppSoilUtil.to_over9000()`
- [ ] Implement management file preparation
- [ ] Implement WEPP run file generation with graphics
- [ ] Implement WEPP execution via `wepp_runner`

### Phase 3: Matrix Testing
- [ ] Parametrize tests across all 48 combinations
- [ ] Add output parsing for soil loss, runoff, and graphics
- [ ] Implement severity gradient validation tests

### Phase 4: Reporting and Analysis
- [ ] Generate summary report of all runs
- [ ] Compare graphical outputs across severity levels
- [ ] Document any unexpected behaviors

---

## Dependencies

### Required wepppy Modules

```python
from wepppy.wepp.soils.utils import WeppSoilUtil, simple_texture
from wepppy.wepp.management import Management
from wepppy.nodb.mods.disturbed import read_disturbed_land_soil_lookup
from wepp_runner import run_hillslope
```

### External Requirements

- **WEPP binary**: Available via `wepp_runner` module (use `wepp_bin='latest'`)
- **Climate data**: From test fixtures or CLIGEN-generated
- **pytest**: For test orchestration

---

## Related Documentation

- [Disturbed README](../../wepppy/nodb/mods/disturbed/README.md)
- [WeppSoilUtil](../../wepppy/wepp/soils/utils/README.md)
- [Management files](../../wepppy/wepp/management/AGENTS.md)
- [wepp_runner](../../wepp_runner/wepp_runner.py)
- [disturbed9002.cfg](../../wepppy/nodb/configs/disturbed9002.cfg)

---

## Appendix A: Full Lookup Table Reference

The `disturbed_land_soil_lookup.csv` defines soil parameters for each (disturbed_class, texture) combination.

**Key columns for 9002 soils:**

| Column | Description | Used in 9002 |
|--------|-------------|--------------|
| `luse` | Disturbed land-use class | Yes (OFE header) |
| `stext` | Soil texture | Yes (OFE header) |
| `ki` | Interrill erodibility (kg·s/m⁴) | Yes |
| `kr` | Rill erodibility (s/m) | Yes |
| `shcrit` | Critical shear stress (Pa) | Yes |
| `avke` | Effective hydraulic conductivity (mm/h) | Yes |
| `ksatadj` | Hydrophobicity adjustment flag | Yes (OFE header) |
| `ksatfac` | Ksat factor for hydrophobic soils | Yes (OFE header) |
| `ksatrec` | Ksat recovery rate | Yes (OFE header) |
| `keffflag` | Effective K flag | Yes |
| `lkeff` | Lower bound on effective K | Yes |

---

## Appendix B: Representative Slope Files from /wc1/runs/

Slope files analyzed from production runs:

| File | Length (m) | Profile |
|------|-----------|---------|
| `caller-footwork/hill_232.slp` | 201.68 | Variable (0.17-0.49) |
| `addressable-projector/hill_582.slp` | 220.81 | Variable (0.12-0.42) |
| `blighted-boundary/hill_222.slp` | 222.10 | Variable (0.25-0.66) |

Typical hillslope lengths range from 50-250m with most around 150-200m.
