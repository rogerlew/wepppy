# Disturbed Lands Module

> Translates wildfire burn-severity maps into WEPP-ready soil and vegetation inputs so erosion models reflect post-fire conditions.

> **See also:** [ENDUSER.md](./ENDUSER.md) for the user-facing workflow guide. [AGENTS.md](../../../../AGENTS.md) for coding conventions. [Disturbed Land Soil Lookup](../../../weppcloud/routes/usersum/weppcloud/disturbed-land-soil-lookup.md) for the end-user parameter reference. [SBS Map Utilities](../baer/README.sbs_map.md) for raster classification details. [Soil File Specification](../../../weppcloud/routes/usersum/input-file-specifications/soil-file.spec.md) for WEPP soil format reference.

## What This Module Does

After a wildfire, hillslope soils and vegetation change dramatically. Burned soils become water-repellent (hydrophobic), ground cover disappears, and erosion rates can increase by orders of magnitude. The Disturbed module automates the translation of a **Soil Burn Severity (SBS) map** into the specific soil and management parameters that the WEPP erosion model needs.

The core logic is:

1. **Read the burn severity map** — a GeoTIFF classifying each pixel as unburned, low, moderate, or high severity
2. **For each hillslope**, determine its dominant burn severity and existing vegetation type (forest, shrub, or grass)
3. **Look up replacement parameters** from a table keyed by `(vegetation type + severity, soil texture)` — this produces new erodibility values, hydraulic conductivity, cover fractions, and plant parameters
4. **Write new WEPP input files** (`.sol` and `.man`) that reflect the post-fire state

The result is a complete set of WEPP inputs that model how a burned watershed will respond to rainfall — more runoff, more erosion, faster peak flows — compared to the undisturbed baseline.

### Who Uses This

- **BAER specialists** building rapid post-fire erosion assessments
- **Incident hydrologists** evaluating debris-flow and flooding risk
- **Researchers** comparing treatment scenarios (mulch, seeding, prescribed fire) against burned baselines
- **WEPPcloud operators** running standard disturbed-land projects

## Key Inputs

### Soil Burn Severity (SBS) Map

The primary input. Users either:
- **Upload a raster** (`.tif` or `.img`) — typically from BARC or RAVG products
- **Generate a uniform severity** — applies one severity level across the entire watershed (useful for scenario analysis)

The module reprojects the raster to match the watershed DEM, classifies pixels into four severity classes (unburned=130, low=131, moderate=132, high=133), and computes per-hillslope dominant severity.

### Disturbed Land Soil Lookup Table

A CSV lookup that maps disturbed class and soil texture to WEPP parameters. Each project gets a run-scoped copy that can be edited through the PowerUser panel.

The Disturbed module supports two lookup table schemes:

| Lookup variant | Runtime file | Key columns | Scalar plant keys | Notes |
|-----------|-----------|-----------|-----------|-----------|
| Base lookup | `disturbed/disturbed_land_soil_lookup.csv` | `luse`, `stext` | `rdmax`, `xmxlai` | Canonical calibration table for soil and PMET values. Also carries static override fields like `plant.data.decfct` and `plant.data.dropfc`. |
| Extended lookup | `disturbed/disturbed_land_soil_lookup_extended.csv` | `disturbed_class`, `stext` (plus `landuse`, `sev_enum`) | `plant.data.rdmax`, `plant.data.xmxlai` | Derived table that merges base lookup values with management-file fields (`ini.data.*`, `plant.data.*`). |

Scalar normalization contract:

- `build_extended_land_soil_lookup()` always normalizes base scalar keys `rdmax` and `xmxlai` into `plant.data.rdmax` and `plant.data.xmxlai` in the extended table.
- Treat `rdmax` and `xmxlai` as base-table keys only. Treat `plant.data.rdmax` and `plant.data.xmxlai` as extended-table keys only.

Key parameters in the base lookup:

| Parameter | What It Controls | Units |
|-----------|-----------------|-------|
| `ki` | Interrill erodibility (raindrop/sheet-flow detachment) | kg·s/m⁴ |
| `kr` | Rill erodibility (concentrated-flow detachment) | s/m |
| `shcrit` | Critical shear stress to initiate rill erosion | N/m² |
| `avke` | Effective hydraulic conductivity of surface soil | mm/h |
| `ksatadj` | Enable hydrophobicity adjustment (0=no, 1=yes) | flag |
| `lkeff` | Lower limit on effective conductivity (hydrophobicity floor) | mm/h |
| `rdmax` | Maximum rooting depth | m |
| `xmxlai` | Maximum leaf area index | — |
| `pmet_kcb` | Basal crop coefficient for ET calculation | — |

### Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `sol_ver` | `7778.0` | Soil file version to generate (7778, 9001, 9002, 9003, 9005) |
| `burn_shrubs` | `True` | Apply burn severity to shrub vegetation classes |
| `burn_grass` | `False` | Apply burn severity to grass vegetation classes |
| `fire_date` | `None` | Fire date for downstream reporting |
| `h0_max_om` | `None` | Optional cap on first-horizon organic matter for fire classes |

## How It Works

### Step 1: Landuse Remapping

When a hillslope has forest vegetation and the SBS map shows high severity fire at that location, the module replaces the management file:

- `UnDisturbed/Old_Forest.man` → `UnDisturbed/High_Severity_Fire.man`

This changes canopy cover from 90% to 40%, interrill cover from 100% to 30%, and maximum LAI from 14.0 to 2.0 — reflecting a severely burned forest floor.

The same logic applies to shrub and grass classes when `burn_shrubs` / `burn_grass` are enabled:

- `UnDisturbed/Shrub.man` → `UnDisturbed/Shrub_High_Severity_Fire.man`
- `UnDisturbed/Tall_Grass.man` → `UnDisturbed/Grass_High_Severity_Fire.man`

### Step 2: Soil Regeneration

For each hillslope, the module:
1. Determines the simplified soil texture (clay loam, loam, sand loam, or silt loam) from clay/sand percentages
2. Looks up replacement erodibility and conductivity parameters from the lookup table
3. Writes a new `.sol` file with the disturbed parameters, using `WeppSoilUtil` for version-aware serialization

For soil versions 9003+, the `lkeff` parameter enforces a lower bound on hydraulic conductivity to simulate persistent water repellency. High severity burns typically use `lkeff=0.1 mm/h` (strong hydrophobicity), while low severity uses `lkeff=10 mm/h` (minimal effect).

### Step 3: PMET Parameters

Writes `pmetpara.txt` with basal crop coefficient (`pmet_kcb`) and readily-available water (`pmet_rawp`) values from the lookup table, used for ET calculations.

## Vegetation Parameters by Burn Severity

### Forest

**Initial conditions (cover and roughness)**

| Disturbed class | Management file | cancov | inrcov | rilcov |
|----------------|----------------|--------|--------|--------|
| forest | `Old_Forest.man` | 0.90 | 1.00 | 1.00 |
| young forest | `Young_Forest.man` | 0.80 | 0.96 | 0.96 |
| forest low sev fire | `Low_Severity_Fire.man` | 0.75 | 0.85 | 0.85 |
| forest moderate sev fire | `Moderate_Severity_Fire.man` | 0.60 | 0.60 | 0.60 |
| forest high sev fire | `High_Severity_Fire.man` | 0.40 | 0.30 | 0.30 |
| forest prescribed fire | `Prescribed_Fire.man` | 0.85 | 0.85 | 0.85 |

**Plant parameters**

| Disturbed class | rdmax | xmxlai | hmax | cuthgt |
|----------------|-------|--------|------|--------|
| forest | 2.00 | 14.0 | 20.0 | 20.0 |
| young forest | 0.60 | 12.0 | 4.0 | 20.0 |
| forest low sev fire | 0.30 | 4.0 | 0.30 | 0.30 |
| forest moderate sev fire | 0.30 | 3.0 | 0.28 | 0.30 |
| forest high sev fire | 0.30 | 2.0 | 0.20 | 0.30 |
| forest prescribed fire | 0.50 | 10.0 | 2.0 | 4.0 |

### Shrub

**Initial conditions**

| Disturbed class | Management file | cancov | inrcov | rilcov |
|----------------|----------------|--------|--------|--------|
| shrub | `Shrub.man` | 0.70 | 0.90 | 0.90 |
| shrub low sev fire | `Shrub_Low_Severity_Fire.man` | 0.33 | 0.80 | 0.80 |
| shrub moderate sev fire | `Shrub_Moderate_Severity_Fire.man` | 0.27 | 0.55 | 0.55 |
| shrub high sev fire | `Shrub_High_Severity_Fire.man` | 0.05 | 0.30 | 0.30 |

**Plant parameters**

| Disturbed class | rdmax | xmxlai | hmax | cuthgt |
|----------------|-------|--------|------|--------|
| shrub | 0.50 | 10.0 | 2.0 | 4.0 |
| shrub low sev fire | 0.20 | 3.0 | 1.5 | 4.0 |
| shrub moderate sev fire | 0.20 | 2.0 | 1.0 | 4.0 |
| shrub high sev fire | 0.20 | 1.0 | 0.5 | 4.0 |

### Grass

**Initial conditions**

| Disturbed class | Management file | cancov | inrcov | rilcov |
|----------------|----------------|--------|--------|--------|
| tall grass | `Tall_Grass.man` | 0.40 | 0.60 | 0.60 |
| short grass | `Poor grass.man` | 0.60 | 0.40 | 0.40 |
| grass low sev fire | `Grass_Low_Severity_Fire.man` | 0.30 | 0.60 | 0.60 |
| grass moderate sev fire | `Grass_Moderate_Severity_Fire.man` | 0.25 | 0.35 | 0.35 |
| grass high sev fire | `Grass_High_Severity_Fire.man` | 0.04 | 0.10 | 0.10 |

**Plant parameters**

| Disturbed class | rdmax | xmxlai | hmax | cuthgt |
|----------------|-------|--------|------|--------|
| tall grass | 0.60 | 6.0 | 0.60 | 1.0 |
| short grass | 0.40 | 9.0 | 1.0 | 4.0 |
| grass low sev fire | 0.40 | 3.0 | 0.40 | 1.0 |
| grass moderate sev fire | 0.30 | 2.0 | 0.30 | 1.0 |
| grass high sev fire | 0.20 | 1.0 | 0.20 | 1.0 |

### Soil Lookup Example (Loam Texture)

These rows from `disturbed_land_soil_lookup.csv` show how soil parameters change with severity for loam soils. Other textures (clay loam, sand loam, silt loam) follow similar patterns with texture-appropriate values.

| Disturbed class | ki | kr | shcrit | avke | ksatadj | lkeff |
|----------------|-----|------|--------|------|---------|-------|
| forest low sev fire | 1,000,000 | 8.0e-5 | 1 | 20 | 0 | 10 |
| forest moderate sev fire | 1,000,000 | 8.0e-5 | 1 | 20 | 0 | 1 |
| forest high sev fire | 1,000,000 | 1.0e-4 | 1 | 15 | 1 | 0.1 |
| shrub low sev fire | 1,000,000 | 8.0e-5 | 1 | 20 | 0 | 10 |
| shrub moderate sev fire | 1,000,000 | 8.0e-5 | 1 | 20 | 0 | 1 |
| shrub high sev fire | 1,000,000 | 1.0e-4 | 1 | 15 | 1 | 1 |
| grass low sev fire | 1,000,000 | 6.0e-5 | 1 | 30 | 0 | -9999 |
| grass moderate sev fire | 1,000,000 | 6.0e-5 | 1 | 30 | 0 | -9999 |
| grass high sev fire | 1,000,000 | 6.0e-5 | 1 | 30 | 0 | -9999 |

Note: `lkeff=-9999` means no hydrophobicity adjustment is applied (grass fires typically do not produce significant water repellency).

## How Parameters Affect WEPP Simulations

The disturbed parameterization feeds directly into the WEPP-forest Fortran kernels:

- **Cover fractions** (`cancov`, `inrcov`, `rilcov`) reduce rainfall interception and hydraulic friction. Lower cover → more water reaches the soil surface → more runoff and erosion.

- **Erodibility** (`ki`, `kr`) and **critical shear** (`shcrit`) control how easily soil detaches. Burned soils are more erodible because organic binding agents are destroyed and soil structure collapses.

- **Hydraulic conductivity** (`avke`, `lkeff`) controls infiltration capacity. The `lkeff` lower bound simulates hydrophobic layers — waxy residues from burned organic matter that repel water. When `ksatadj=1`, WEPP dynamically adjusts conductivity based on soil saturation, allowing recovery as cumulative precipitation breaks down the hydrophobic layer.

- **Plant parameters** (`rdmax`, `xmxlai`, `hmax`) control vegetation recovery. In extended lookup exports, these scalars are represented as `plant.data.rdmax` and `plant.data.xmxlai`. Burned hillslopes start with reduced root depth, leaf area, and canopy height, which limits transpiration and interception.

The parameterization is **directionally correct at the regime level**: burned conditions produce more runoff and sediment than undisturbed across seasonal and annual totals. Individual storm events may occasionally show the opposite due to antecedent moisture state — a dry burned soil can still infiltrate more than a saturated undisturbed soil. This is expected WEPP hydrology behavior; compare distributions and totals rather than individual events.

### Static Management Overrides

To keep undisturbed vs. disturbed comparisons strictly "static to static," the lookup table sets `plant.data.decfct` and `plant.data.dropfc` to `1` for all landuses except agriculture crops. This prevents management files from decaying or dropping plant material during the comparison window, avoiding unintended differences in residue/root mass between templates.

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

## Developer Notes

- `remap_landuse()` and `remap_mofe_landuse()` map SBS classes 131/132/133 to low/mod/high severity management keys using `wepppy/wepp/management/data/disturbed.json`.
- If a management entry defines `SoilFile`/`sol_path`, the controller copies that soil directly instead of regenerating from the lookup table.
- For treatment suffixes (`-mulch_15`, `-thinning`, etc.), `lookup_disturbed_class()` strips the suffix so soils are keyed by burn severity, not treatment type.
- For MOFE runs, each OFE gets its own disturbed soil file, reassembled into a `.mofe.sol` via `SoilMultipleOfeSynth`.
- MOFE disturbed soil regeneration now follows the canonical NoDb process-pool contract: try `createProcessPoolExecutor(..., prefer_spawn=True)`, retry with `prefer_spawn=False` on `BrokenProcessPool`, then fall back to sequential generation only if both pools break.
- Non-`BrokenProcessPool` MOFE worker failures propagate immediately (no silent fallback), and in-memory `soils.domsoil_d` / `soils.soils` mutations are applied in a separate locked serial phase after file generation completes.
- For MOFE `sol_ver=9002` lookup misses, the controller creates class-specific fallback `9002` soils (`mukey-texid-disturbed_class`) with explicit neutral metadata replacements (`luse`, `stext`, `ksatfac=0.0`, `ksatrec=0.0`) so MOFE stacks remain same-version; single-OFE lookup misses still return base `mukey`.
- `build_extended_land_soil_lookup()` exports the extended scheme (management + soil parameters) and normalizes scalar plant keys to `plant.data.rdmax` / `plant.data.xmxlai`; it is not part of the default run workflow.
- All mutations must occur inside `with disturbed.locked():` blocks to respect Redis-backed locking.

## Validation Results (48-Simulation Matrix)

A 48-simulation matrix test (4 soil textures × 3 vegetation types × 4 burn severities, 100-year climate) validates the parameterization. Key findings:

1. **Runoff increases with burn severity**: Forest burned conditions show more runoff events than unburned in 86% of matched events (low severity) through 76% (high severity).

2. **Sediment delivery increases dramatically at high severity**: Forest high severity produces 174× more total sediment than unburned (5,338 vs 30.6 kg/m). Shrub high severity shows 23×. At high severity, 100% of matched events show burned > unburned for forest.

3. **Texture matters**: Clay loam shows the highest sediment response; sand loam shows minimal differences due to high infiltration capacity even when burned.

4. **Grass response is muted at low severity**: Tall grass shows high "equal" event counts at low severity (66% of events), indicating minimal hydrologic impact from low-severity grass fires.

Full results: `tests/disturbed/analysis_results.md`
Test suite: `tests/disturbed/test_disturbed_matrix.py`

## Further Reading

- [Disturbed Land Soil Lookup](../../../weppcloud/routes/usersum/weppcloud/disturbed-land-soil-lookup.md) — end-user parameter reference
- [SBS Map Utilities](../baer/README.sbs_map.md) — raster classification and color-table contracts
- [SBS Controls Behavior](../../../../docs/ui-docs/control-ui-styling/sbs_controls_behavior.md) — UI upload/uniform mode documentation
- [WEPP Soil Files](../../../wepp/soils/README.md) — soil file format versions and parameter definitions
- [Management File Conventions](../../../wepp/management/AGENTS.md) — management file structure
- [Soil Migration Utilities](../../../wepp/soils/utils/README.md) — WeppSoilUtil API
