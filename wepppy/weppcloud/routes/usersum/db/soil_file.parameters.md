# WEPP Soil File Parameters
Derived from `soil-file.spec.md` and `wepppy/wepp/soils/utils/yamlizer.py`. The heading line is the default `usersum <parameter>` description; bullets expand on extended context or units.

## Header
#### `datver` — Soil file version code (real)
- **Context**: header
- **Extended**: Determines how subsequent records are parsed (e.g., 97.5 base format, 2006.2 restrictive layer, 7777/7778 horizon properties, 9002/9003/9005 disturbed/revegetation formats).

#### `solcom` — Soil file comment line (text)
- **Context**: header
- **Extended**: Free-form line (80 characters) carried into generated output for documentation.

#### `ntemp` — Number of OFEs or channels (integer)
- **Context**: header
- **Extended**: Count of overland flow elements or channels described in the file; governs how many OFE records follow.

#### `ksflag` — Internal hydraulic conductivity adjustment flag (integer)
- **Context**: header
- **Extended**: `0` keeps conductivity fixed; `1` allows WEPP to apply internal adjustments during simulation.

## OFE Records (Line 4)
#### `slid` — Soil identifier for the OFE (text)
- **Context**: OFE base
- **Extended**: Name of the soil series/profile applied to the element or channel.

#### `texid` — Soil texture description (text)
- **Context**: OFE base
- **Extended**: Textural class label (e.g., "silt loam") associated with the soil profile.

#### `nsl` — Number of soil layers (integer)
- **Context**: OFE base
- **Extended**: Controls how many horizon records follow for the OFE.

#### `salb` — Bare-soil albedo (real)
- **Context**: OFE base
- **Extended**: Albedo of the dry soil surface used for energy balance calculations.

#### `sat` — Initial porosity saturation (m³/m³, real)
- **Context**: OFE base
- **Extended**: Fraction of total porosity considered filled at the simulation start; defaults to 0.75 if unspecified.

#### `ki` — Baseline interrill erodibility (kg·s/m⁴, real)
- **Context**: OFE base
- **Extended**: Governs raindrop-driven soil detachment for interrill (sheet) areas.

#### `kr` — Baseline rill erodibility (s/m, real)
- **Context**: OFE base
- **Extended**: Governs flow-driven detachment within rills.

#### `shcrit` — Baseline critical shear stress (N/m², real)
- **Context**: OFE base
- **Extended**: Minimum hydraulic shear required to initiate soil detachment in rills.

#### `avke` — Surface effective hydraulic conductivity (mm/h, real)
- **Context**: OFE base
- **Extended**: Only present in version ranges > 94.1 and < 2006.2; represents the effective conductivity of the surface layer.

## Disturbed / 9000-Series OFE Extensions
#### `ksatadj` — Hydrophobicity / conductivity adjustment flag (integer)
- **Context**: OFE 9000-series
- **Extended**: `0` disables saturation-based adjustments; `1` triggers WEPP's internal hydrophobicity or burn-severity logic.

#### `luse` — Disturbed land-use classification (text)
- **Context**: OFE 9000-series
- **Extended**: Descriptor of the disturbed class (e.g., "forest high sev"); influences burn severity coding and conductivity adjustments.

#### `stext` — Simplified soil texture class (text)
- **Context**: OFE 9000-series
- **Extended**: One of clay loam, loam, sand loam, or silt loam; paired with `texid_enum` in 9005.

#### `ksatfac` — Lower bound on effective conductivity (mm/h, real)
- **Context**: OFE 9002 and earlier formats
- **Extended**: Defines the minimum effective hydraulic conductivity used in exponential recovery formulations.

#### `ksatrec` — Conductivity recovery coefficient (1/day, real)
- **Context**: OFE 9002 and earlier formats
- **Extended**: Exponential recovery rate toward pre-disturbance conductivity following hydrophobic events.

#### `burn_code` — Encoded burn severity class (integer)
- **Context**: OFE 9003/9005
- **Extended**: Combines land cover and severity (100 agriculture, 200 shrub, 300 forest, etc.), adding 1/2/3 for low/moderate/high severity.

#### `lkeff` — Lower limit on effective conductivity (mm/h, real)
- **Context**: OFE 9003/9005
- **Extended**: Caps the downward adjustment of effective conductivity; `-9999` disables the limit.

#### `texid_enum` — Simplified texture enumeration (integer)
- **Context**: OFE 9005
- **Extended**: Maps `stext` to 1 = clay loam, 2 = loam, 3 = sand loam, 4 = silt loam.

#### `uksat` — Upper limit on effective conductivity (mm/h, real)
- **Context**: OFE 9005
- **Extended**: WEPPcloud-specific parameter used to bound conductivity during revegetation scenarios; consult future documentation for refinements.

## Horizon Records (Layer Data)
#### `solthk` — Depth to bottom of layer (mm, real)
- **Context**: Horizon all versions
- **Extended**: Monotonically increasing depth defining soil layer thickness.

#### `sand` — Sand fraction by volume (%)
- **Context**: Horizon all versions
- **Extended**: Percentage of sand in the layer; combined with clay to estimate silt.

#### `clay` — Clay fraction by volume (%)
- **Context**: Horizon all versions
- **Extended**: Used alongside sand to infer texture and hydrologic properties.

#### `orgmat` — Organic matter fraction by volume (%)
- **Context**: Horizon all versions
- **Extended**: Volume percentage of organic material in the layer.

#### `cec` — Cation exchange capacity (meq/100 g, real)
- **Context**: Horizon all versions
- **Extended**: Influences nutrient exchange and is used in empirical conductivity estimates.

#### `rfg` — Rock fragment volume fraction (%)
- **Context**: Horizon all versions
- **Extended**: Fraction of coarse fragments affecting storage and infiltration.

### Additional Properties (≥ 7777)
#### `bd` — Bulk density (g/cm³, real)
- **Context**: Horizon ≥ 7777
- **Extended**: Mass density of the soil layer; defaults to 1.4 g/cm³ if missing during conversions.

#### `ksat` — Saturated hydraulic conductivity (mm/h, real)
- **Context**: Horizon ≥ 7777
- **Extended**: Vertical saturated conductivity used in infiltration computations.

#### `fc` — Field capacity (m³/m³, real)
- **Context**: Horizon ≥ 7777
- **Extended**: Volumetric water content at field capacity; estimated via Rosetta when absent.

#### `wp` — Wilting point (m³/m³, real)
- **Context**: Horizon ≥ 7777
- **Extended**: Volumetric water content at permanent wilting; estimated via Rosetta when absent.

### Additional Properties (≥ 7778)
#### `anisotropy` — Conductivity anisotropy ratio (real)
- **Context**: Horizon ≥ 7778
- **Extended**: Ratio of horizontal to vertical saturated conductivity; defaults to 10 for very shallow layers when derived.

### Rosetta-Derived Parameters (9002+ Horizons)
#### `theta_r` — Residual volumetric water content (m³/m³, real)
- **Context**: Horizon ≥ 9002
- **Extended**: Pedotransfer estimate from Rosetta appended after the primary horizon fields.

#### `theta_s` — Saturated volumetric water content (m³/m³, real)
- **Context**: Horizon ≥ 9002
- **Extended**: Rosetta-derived value representing saturated storage.

#### `alpha` — van Genuchten alpha parameter (1/cm, real)
- **Context**: Horizon ≥ 9002
- **Extended**: Controls capillary pressure head response in the van Genuchten model.

#### `npar` — van Genuchten pore-size exponent (dimensionless)
- **Context**: Horizon ≥ 9002
- **Extended**: Governs the slope of the soil water retention curve.

#### `ks` — Rosetta saturated hydraulic conductivity (cm/day, real)
- **Context**: Horizon ≥ 9002
- **Extended**: Pedotransfer prediction (different units from `ksat`); WEPP may convert internally for hydraulic calculations.

#### `wp_ros` — Rosetta-derived wilting point (m³/m³, real)
- **Context**: Horizon ≥ 9002
- **Extended**: Appended after the base horizon record; WEPP retains both measured and pedotransfer estimates.

#### `fc_ros` — Rosetta-derived field capacity (m³/m³, real)
- **Context**: Horizon ≥ 9002
- **Extended**: Pedotransfer estimate appended alongside `theta_r`/`theta_s`.

## Restrictive Layer (Line 6)
#### `slflag` — Restrictive layer presence flag (integer)
- **Context**: Restrictive layer
- **Extended**: `0` indicates no restricting layer; `1` activates the restricting-layer parameters.

#### `ui_bdrkth` — Restrictive layer thickness or depth (mm, real)
- **Context**: Restrictive layer
- **Extended**: Depth to bedrock or restricting layer where runoff/percolation properties change.

#### `kslast` — Restrictive layer hydraulic conductivity (mm/h, real)
- **Context**: Restrictive layer
- **Extended**: Saturated conductivity assigned to the bottom layer or bedrock interface; often derived from the last horizon (`ksat/100`).
