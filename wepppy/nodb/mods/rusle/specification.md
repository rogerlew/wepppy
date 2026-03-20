# RUSLE NoDb Mod Specification

> Working document.
>
> This file captures the current design direction for a gridded `RUSLE` NoDb
> mod based on the `disturbed9002_wbt` workflow. It is not final. Assumptions,
> data-source choices, equations, and implementation details should be revised
> as research, prototyping, and validation progress.

## Purpose

Define an academically defensible path for a gridded `RUSLE` implementation in
WEPPpy using the WBT backend in `/workdir/weppcloud-wbt`, with
`disturbed9002_wbt` as the initial configuration target.

The initial product should provide a spatial representation of long-term
average hillslope sheet-and-rill detachment potential, not event-scale erosion,
not sediment delivery ratio, and not channel erosion.

The first implementation should remain spatially gridded in its outputs, but
use a run-constant, climate-derived `R` rather than an external gridded
erosivity surface.

Practically, this mod is intended to replace legacy heuristic gridded erosion
visualizations with a product that is more explicit, more citable, and more
academically defensible. It should be treated as a visualization and
prioritization layer, not as a regulatory estimate or a substitute for
calibrated hillslope modeling.

## Model Framing

The core equation is:

`A = R * K * LS * C * P`

For this mod:

- `A` will be interpreted as long-term average annual hillslope soil loss or
  detachment potential from sheet-and-rill processes.
- The model will be applied only on hillslope cells.
- Channel cells, open water, wetlands, and urban/developed cells should be
  masked out of the primary output.
- The first public-facing wording should emphasize `detachment potential` or
  `relative long-term detachment hazard`, unless and until factor choices and
  validation support stronger wording.

## Initial Scope

- Target config lineage: `wepppy/nodb/configs/disturbed9002_wbt.cfg`
- Backend: WhiteboxTools fork in `/workdir/weppcloud-wbt`
- Initial geography: United States workflows first
- First `R` delivery: compute a scalar `R` from the run WEPP climate file and
  broadcast it to `r.tif`; do not depend on an external gridded runtime `R`
  source
- Initial output family:
  - `rusle/r.tif`
  - `rusle/k.tif`
  - `rusle/ls.tif`
  - `rusle/c.tif`
  - `rusle/p.tif`
  - `rusle/mask.tif`
  - `rusle/a.tif`
  - `rusle/manifest.json`
  - `rusle/README.md`

## Non-Goals

- Event-based detachment modeling
- Sediment delivery to channels or outlets
- Net erosion-deposition modeling
- Channel erosion or gully erosion
- A full clone of `RUSLE2`

If future work needs deposition, the design should branch toward a
`USPED`-style or other transport-capacity workflow rather than stretching the
plain `RUSLE` label.

## Spatial Masking Rules

Primary masking should combine:

- WBT channel network products, especially `netful`
- NLCD landcover exclusions
- Optional explicit user masks

The initial NLCD exclusions should include:

- `11` open water
- `21`, `22`, `23`, `24` developed
- `90`, `95` woody wetlands and emergent herbaceous wetlands

#### Wetland Masking Rationale

The exclusion of `NLCD 90` and `95` is a model-domain decision, not a claim
that wetlands never erode.

- `RUSLE` is being used here as a hillslope sheet-and-rill detachment model
  for rainfall and overland flow, not as a wetland-process, channel-scour, or
  depositional-marsh model
- woody wetlands and emergent herbaceous wetlands commonly represent saturated,
  ponded, or hydrologically connected environments that sit outside the
  intended upland hillslope domain of this mod
- wetlands often function as sediment-assimilation, storage, or filtering
  environments, so leaving them in the primary detachment map would tend to
  blur the distinction between upland sediment-source areas and downstream
  receiving or depositional areas
- this should be documented as a default scope mask rather than a universal
  scientific statement; if a future workflow needs drained farmed wetlands,
  wet meadows, or other edge cases treated as hillslopes, that should be an
  explicit override with different assumptions

The mask should also stop slope-length growth for `LS`.

## Factor Design

### LS

Recommendation: implement a purpose-built WBT tool instead of reusing
`SedimentTransportIndex` as the canonical `LS`.

#### Rationale

- Whitebox's existing `SedimentTransportIndex` is useful, but it is documented
  as a unit-stream-power substitute that is only sometimes used in place of
  `LS`.
- The mod needs an explicit, auditable `RUSLE` topographic factor, not a nearby
  terrain proxy.
- A dedicated tool makes masking, slope-length truncation, and output
  diagnostics explicit.

#### Reviewed Precedents

The current `LS` decisions are based on both literature and existing open
implementations:

- `Desmet and Govers (1996)` remains the canonical raster `L`-factor basis
- `McCool et al. (1987, 1989)` remains the canonical `RUSLE` basis for `S`
  and the slope-length exponent `m`
- `Tarboton (1997)` provides the scientific basis for default `DInf`
  routing and specific catchment area
- `SAGA` is a useful open implementation precedent because it explicitly
  supports `Desmet and Govers (1996)` and aspect-dependent specific
  catchment area
- `GRASS r.watershed` is a useful open implementation precedent for
  `blocking`, `max_slope_length`, and default multiple-flow routing, but not
  for the canonical equation set because its `LS` output is documented as
  using western-rangelands equations
- Whitebox's existing `SedimentTransportIndex` remains a comparison or
  diagnostic product only, not the canonical `LS`

#### Proposed WBT Tool

Tool name: `RusleLsFactor`

Proposed inputs:

- `dem`
- optional precomputed `sca`
- optional precomputed `slope_deg`
- optional `channel_mask`
- optional `blocking_mask`
- optional `max_slope_length_m`
- routing mode selector, default `DInf`

Proposed outputs:

- `ls.tif`
- `l.tif`
- `s.tif`
- `sca.tif`
- `effective_slope_length.tif`

#### Locked v1 Method

`RusleLsFactor` should implement one canonical v1 `LS` path rather than ship
multiple competing `LS` equations.

##### `L` Subfactor

- Use the `Desmet and Govers (1996)` raster formulation
- Drive `L` from upslope contributing area per unit contour width, not from a
  stream-power surrogate
- Include the standard aspect-dependent contour-width correction from
  `Desmet and Govers (1996)` rather than assuming contour width always equals
  cell size
- Use the `RUSLE` slope-length exponent:
  - `m = beta / (1 + beta)`
  - `beta = (sin(theta) / 0.0896) / (3.0 * sin(theta)^0.8 + 0.56)`
- Treat `theta` as the local slope angle; if `slope_deg` is supplied, convert
  it internally to radians before applying the equations

##### `S` Subfactor

- Use the standard `McCool/RUSLE` steepness equations based on local slope
  angle:
  - `S = 10.8 * sin(theta) + 0.03` when `tan(theta) < 0.09`
  - `S = 16.8 * sin(theta) - 0.50` when `tan(theta) >= 0.09`
- Use local slope only in v1, not distance-weighted average catchment slope
- Do not substitute the `Nearing (1997)` continuous steep-slope form in v1;
  staying with the standard `McCool/RUSLE` form keeps the tool closer to USDA
  `RUSLE` practice and the most common raster `LS` implementations
- Do not implement the short-slope interrill-only branch from `McCool et al.
  (1987)` in v1; that is an explicit scale assumption for a 30 m gridded
  product rather than a claim that the branch is scientifically invalid

##### Routing and DEM Assumptions

- Default routing mode: `DInf`
- Default flow input: specific catchment area from a hydrologically
  conditioned DEM
- The `RusleLsFactor` tool should assume the DEM has already been conditioned
  upstream; it should not silently fill or breach pits inside the tool
- If `sca` is supplied, it must already be a same-grid specific catchment area
  raster in `m^2/m`
- If `slope_deg` is supplied, it must already be a same-grid local slope raster
  in degrees
- `FD8` may be supported as an alternate multiple-flow sensitivity path
- `D8` may be supported as a comparison path only, not as the default

##### Slope-Length Termination and Masking

- Stop slope-length growth at channel cells
- Stop slope-length growth at masked `NLCD` water, urban, and wetland cells
- Stop slope-length growth at explicit `blocking_mask` cells such as roads,
  skid trails, treatment breaks, or other known barriers when those inputs are
  intentionally supplied
- Do not treat disturbance itself as an `LS` input. Disturbance affects the
  final map through `C`, the joint hillslope mask, and scenario framing, not by
  changing the topographic factor equations
- Do not apply an arbitrary global hard cap by default. `Panagos et al.
  (2015)` explicitly applied `Desmet and Govers (1996)` with a multiple-flow
  algorithm and noted that they did not impose arbitrary slope lengths
- Support `max_slope_length_m` as an explicit optional operational control. If
  a run uses it, record that choice in `rusle/manifest.json` and treat it as a
  visualization-stabilization assumption rather than canonical `RUSLE` science

##### Output and Interpretation Assumptions

- The tool should output diagnostic rasters for `L`, `S`, `LS`, `SCA`, and
  effective slope length so the result can be audited rather than treated as a
  black box
- The target interpretation is broad hillslope pattern and relative detachment
  potential at the run cell size, not microtopographic truth
- `SedimentTransportIndex` may still be exported as an auxiliary comparison
  layer, but not substituted for canonical `LS`

The first implementation should still favor transparency and diagnostic outputs
over micro-optimization.

### R

Initial runtime direction: use the run WEPP climate file to compute a static,
non-gridded `R` for the area of interest. For the first implementation, `R`
should therefore be spatially uniform within a run unless and until a separate
gridded-climate extension is intentionally added.

#### Key Constraint

`RUSLE` rainfall erosivity is not just precipitation total. It requires a
long-term annual sum of storm `EI30`, which in turn requires storm energy and
maximum 30-minute intensity.

#### Canonical `RUSLE` Definition of `R`

For this specification, the canonical definition of `R` is the USDA
`USLE/RUSLE` definition, not an app-specific adaptation:

- `R` is a long-term average annual erosivity index for a location
- annual `R` is the average annual sum of erosivity values for individual
  storms from historical weather records
- individual-storm erosivity is based on storm kinetic energy times maximum
  30-minute intensity, commonly written as `EI30`

That distinction matters. A single precipitation-frequency design value, even
if converted through a storm energy equation, is not by itself the same thing
as canonical annual `RUSLE R`.

#### Preferred Runtime Mode: `cligen_static`

- Preferred first shipping mode and expected default
- Use the run WEPP climate file as the source of truth for rainfall erosivity
- Compute one scalar `R` for the full run climate record, then broadcast that
  value over the unmasked AOI
- Treat `PRISM`, `NOAA Atlas 14`, and similar external precipitation products
  as upstream climate-generation inputs only, not as runtime `R` inputs for
  the `Rusle` mod

#### Required Computation Path

This path should be a requirement, not an optimization preference.

- Parse the run climate file, or an equivalent storm table carrying the same
  storm parameters, including `year`, `prcp`, `dur`, `tp`, and `ip`
- Reconstruct each storm using WEPP hyetograph segments
- Compute storm kinetic energy `E` from the reconstructed WEPP hyetograph
  segments
- Compute `I30` from the same reconstructed storm
- Compute event `EI30`
- Sum event `EI30` within each simulation year
- Average annual `EI30` totals across the available simulation years
- Output a scalar run-level `R`, then materialize `r.tif` as a constant raster
  on the DEM grid for unmasked hillslope cells

The important guardrail is explicit: `E` must come from reconstructed WEPP
hyetograph segments. A shortcut that uses precipitation total, a single
exported peak-intensity field, or an external design-storm intensity without
segment-based energy reconstruction is not acceptable as the canonical
`cligen_static` path.

#### Existing Local Basis

The repository already has the core ingredients needed for a shared hyetograph
implementation and for parity testing against existing Python behavior:

- `wepppy.climates.cligen.cligen._wepp_hyetograph_segments(...)` reconstructs
  WEPP storm segments as `(start_hr, end_hr, intensity_mm_hr)`
- `wepppy.climates.cligen.cligen.wepp_peak_intensities_from_hyetograph(...)`
  already computes peak intensities from that reconstructed hyetograph
- `climate/wepp_cli.parquet` is already exported with storm parameters and
  derived intensities, including `prcp`, `dur`, `tp`, `ip`, and
  `peak_intensity_30`

`climate/wepp_cli.parquet` is therefore the right audit and interchange
artifact. It should not be treated as the canonical computational input for
`cligen_static R`. The `.cli` file should remain the source of truth, both
because it is the native WEPP climate representation and because breakpoint
climate support is not guaranteed to round-trip through the parquet export.
The required scientific path still runs through segment-based `E` from the
reconstructed WEPP storm shape.

#### Implementation Direction

The first production implementation should do two related things in
`wepppyo3.climate`:

1. add a reusable Rust WEPP hyetograph reconstruction helper
2. build the `cligen_static R` routine on top of that shared helper

Recommended direction:

- Add a reusable Rust WEPP hyetograph reconstruction helper so existing
  callsites can adopt the Rust path over time
- Where callsites already have working Python hyetograph logic, allow Python
  fallback during migration; do not invent new Python fallback paths where none
  already exist
- Add a `wepppyo3.climate` routine to calculate run-level static `R` from a
  WEPP `.cli` file
- Reuse the existing Rust climate-file parser in `wepppyo3` rather than
  round-tripping large storm tables through Python
- Keep the source of truth as the WEPP `.cli` file; `wepp_cli.parquet` remains
  an audit artifact rather than an alternate static-`R` input
- Do not add a production Python fallback for `cligen_static R`; implement it
  directly in Rust once the shared hyetograph helper exists
- Return at least the mean annual `R` and per-year annual erosivity totals for
  manifesting and QA
- Regression-test the Rust hyetograph helper against the existing
  `cligen.py` behavior where comparable, and test static `R` from `.cli`
  inputs directly in Rust

The exact function name can be decided during implementation, but the target is
something equivalent to `rust_cli_calculate_rusle_r(...)` or
`rust_cli_calculate_static_r(...)`.

#### Runtime Scope Boundary

- `legacy_r_grid` is out of the initial runtime path
- `mrms_ei30` is out of the initial runtime path
- `prism_atlas_regression` is out of the initial runtime path
- `PRISM` and `NOAA Atlas 14` may still matter upstream when building or
  revising climate inputs, but they are not direct `R`-factor dependencies for
  the first `Rusle` delivery

#### Explicit Review Basis

The current interpretation of event-style `R` approaches in this working
document is based on an explicit review of:

- the local `/workdir/Culvert_web_app` implementation, especially
  `culvert_app/utils/subroutine_rusle_analysis.py`
- `Panda et al., 2022` full text
- `Mukherjee et al., 2025` full text
- USDA-ARS `RUSLE1.06c` and `RUSLE2` documentation describing how `R` is
  defined in canonical `USLE/RUSLE`

#### Comparison Note: `Panda et al.`, `Mukherjee et al.`, and `Culvert_web_app`

The reviewed culvert-vulnerability literature and codebase are useful
precedent, but they should be described carefully.

What was reviewed:

- `Panda et al., 2022` states that `R` was developed separately using a
  `NOAA PFDS I30 raster`, defines `I30` as `30-min rainfall intensity for a
  100-yr storm`, and uses `R = KE * I30`
- `Mukherjee et al., 2025` states that `R` was developed separately using a
  `NOAA-Atlas14 30-min 100-yr precipitation intensity (PI30) raster` and uses
  `Ri = KEi * PI30i`
- the local `Culvert_web_app` implementation follows the same general pattern:
  intersecting `NOAA Atlas 14` `30 min / 100 yr` rasters are extracted,
  resampled to the DEM grid, converted to `mm/hr`, and passed through a storm
  energy relation to compute `R`

What those sources do not appear to say:

- neither `Panda et al., 2022` nor `Mukherjee et al., 2025` appears to call
  that method a `design-storm erosivity surrogate` in those words
- neither source appears to claim that the resulting raster is the canonical
  long-term annual `RUSLE R` factor derived from historical storm `EI30` sums

Working interpretation for this NoDb spec:

- the label `design-storm erosivity surrogate` is our characterization of that
  method, not wording attributed to Panda or Mukherjee
- that characterization is justified because the reviewed method substitutes a
  single precipitation-frequency design raster, or a field derived directly
  from it, for the canonical annual `RUSLE R` index
- the rainfall kinetic energy equations used in those papers are storm
  energy-intensity relations from `USLE/RUSLE` erosivity work; they are not
  annual `R`-surface fitting equations and they are not themselves a proof
  that a `100-yr / 30-min` design raster is equivalent to annual `R`

Conclusion:

- the `Panda/Mukherjee/CULVERT` approach is best treated here as precedent for
  a separate event-oriented or design-storm-oriented visualization mode
- it should not be adopted as the default `R` path for this NoDb mod if the
  output is presented as long-term detachment potential under standard
  `RUSLE` wording

### K

#### Reviewed Precedents

The current `K` decisions are based on both primary model references and open
implementation precedents:

- `RUSLE` and NRCS `kwfact` or `kffact` define the canonical U.S. soil
  erodibility target for comparison
- the `Wischmeier` nomograph-style path remains the closest conceptual match to
  canonical `RUSLE K`, but it needs inputs that gridded products often do not
  supply directly, especially very fine sand, structure class, and profile
  permeability class
- `SWAT+` documents the `Williams (1995)` `EPIC` alternative, which is widely
  used when only texture and organic carbon are available
- `Shojaeezadeh et al. (2024)` provide direct CONUS precedent for deriving
  `K` from `POLARIS` plus ancillary datasets, but also show the approximation
  burden: structure and permeability must be inferred, and their textural term
  uses gridded sand and silt rather than a directly observed very-fine-sand
  field
- `Rossiter et al. (2022)` remain the key caution that fine-gridded digital
  soil maps are not automatically truer than survey-based products

#### Locked Mode Strategy

The design should explicitly support three `K` paths:

1. `polaris_nomograph`

- Preferred default for the main `Rusle` map product
- Target a fine-earth, `kffact`-like `K` estimate from `POLARIS`
- Best fit when the goal is a spatially informative detachment-potential map
  that still speaks the language of `RUSLE` and NRCS `K`

2. `polaris_epic`

- Supported as a secondary `POLARIS` mode, not the default
- Use the `Williams (1995)` `EPIC` texture-carbon approximation as documented
  in `SWAT+`
- Best fit as a lower-assumption fallback, sensitivity test, or reproducibility
  path for users coming from `SWAT`, `MUSLE`, or global gridded erosion
  studies

3. `gnatsgo_kffact`, `gnatsgo_kwfact`, `gssurgo_kffact`, or `gssurgo_kwfact`

- Reference or benchmark modes using NRCS soil-survey `K` fields
- Expected to be less spatially variable within soil map units, but more
  directly tied to official NRCS `K` interpretations
- Should remain available for comparison, quality review, and sensitivity
  testing

#### Interpretation Note

- The practical objective here is a visually interpretable detachment-potential
  map with academic backing, not a claim that every sub-map-unit variation in
  `POLARIS` is truer than NRCS survey `K`
- `Rossiter et al. (2022)` explicitly caution that digital soil mapping
  products, including `POLARIS`, can smooth real soil geography or introduce
  local artifacts relative to field survey products
- Because of that tradeoff, runs should be able to compare
  `polaris_nomograph` and `polaris_epic` against NRCS `K` products over the
  same area of interest
- Most end users are unlikely to have a strong prior preference between
  `nomograph` and `EPIC`; that is an inference from the product goal here, not
  a cited survey result. The stronger preference is likely to come from
  technically literate reviewers:
  - `RUSLE` or NRCS-oriented users will usually prefer the nomograph-facing
    path
  - `SWAT`, `MUSLE`, or large-area gridded-model users may prefer the `EPIC`
    path
- Because of that, `polaris_nomograph` should remain the default and
  `polaris_epic` should be treated as an advanced or sensitivity option rather
  than a first-choice UI decision

#### POLARIS Extension Plan

Recent CONUS-scale erosion work has already derived soil erodibility from
`POLARIS` and related ancillary layers, so the general approach is precedented
and does not need to be invented from scratch.

The current `disturbed9002_wbt` Polaris fetch was intentionally minimal for
testing. The mod should extend the request set.

Minimum added Polaris properties:

- `sand`
- `silt`
- `clay`
- `om`
- `bd`
- `ksat`

Recommended depths:

- `0_5`
- `5_15`

The mod should compute a weighted near-surface value rather than relying only
on `0_5`. Both `polaris_nomograph` and `polaris_epic` should use the same
thickness-weighted near-surface aggregation so comparisons are about the
equation family, not mismatched horizons.

#### Locked Assumptions by Mode

##### `polaris_nomograph`

- This is the preferred first-shipping `POLARIS` mode
- It should be described as a `nomograph-like` or `RUSLE-facing` emulation, not
  as a literal reproduction of NRCS `kffact`
- The main reason is data availability: the canonical particle-size term uses
  silt plus very fine sand, while `POLARIS` does not provide a directly
  observed very-fine-sand field
- For v1, estimate very fine sand using the `RUSLE2 User Reference Guide`
  fallback equation when only sand, silt, and clay are known:
  - `f_vfs = 0.74 * f_sand - 0.62 * f_sand^2`
  - equivalently, in percent units:
    `vfs_pct = 0.74 * sand_pct - 0.0062 * sand_pct^2`
- Clamp the result to `[0, sand_pct]` before using it in the nomograph
  particle-size term
- Use that `RUSLE2` equation rather than a PSD interpolation or hydraulic
  pedotransfer back-calculation because it is the only primary-source,
  `RUSLE`-native fallback we identified for missing very fine sand
- This also fits the product goal better than a more elaborate PSD model:
  it keeps the approximation inside the `RUSLE2` semantics users are already
  likely to trust, and it is easier to audit against SSURGO `sandvf_r`
  or `vfsand_wtavg`
- `Shojaeezadeh et al. (2024)` show one defensible way to proceed: retain the
  nomograph family, infer structure and permeability classes from ancillary
  datasets, and accept a gridded texture approximation in place of literal
  survey terms
- The tool should therefore make the approximation explicit in metadata and
  documentation instead of implying that `POLARIS` can reproduce NRCS `K`
  exactly
- Manifest metadata should record that `vfs` is `rusle2_estimated_from_sand`,
  not an observed `POLARIS` field
- Structure and permeability classes should be inferred from gridded covariates
  and documented as modeled classes, not observed survey descriptors
- If no profile coarse-fragment ancillary is supplied, the output should be
  labeled and interpreted as a fine-earth, `kffact`-like estimate
- If a profile coarse-fragment adjustment is applied later, comparisons should
  shift toward `kwfact`

##### `polaris_epic`

- This mode should implement the `Williams (1995)` alternative equation as
  documented by `SWAT+`
- It should use `POLARIS` `sand`, `silt`, `clay`, and `om`, converting organic
  matter to organic carbon where required by the equation
- It should not require structure classes, permeability classes, or very fine
  sand
- That lower input burden is its main advantage
- Its main limitation is conceptual rather than computational: it is less
  directly comparable to NRCS `kwfact` or `kffact` and less obviously aligned
  with canonical `RUSLE K`
- For this project, it should therefore be treated as a secondary estimator for
  fallback, sensitivity, or reproducibility rather than the main default

##### Rock Fragments and Surface Rock

- First derive a fine-earth, `kffact`-like `K` estimate from `POLARIS`
- Then handle profile rock fragments explicitly rather than letting stoniness
  silently distort the high-resolution texture signal
- Treat surface rock as a cover effect, not as a direct replacement for soil
  erodibility
- Comparisons should be matched accordingly:
  - compare fine-earth `POLARIS` estimates to `kffact` where available
  - compare profile-fragment-adjusted estimates to `kwfact` where available

Likely ancillary needs beyond the current Polaris request:

- coarse-fragment or rock-fragment fraction
- a defensible structure-class mapping
- a defensible permeability-class mapping derived from `ksat` and profile
  conditions

#### Product Decision

Support both `polaris_nomograph` and `polaris_epic`, but do not treat them as
co-equal defaults.

- `polaris_nomograph` is the default because it is closer to `RUSLE` and NRCS
  `K` semantics, which better fits the academic-backing goal of this mod
- `polaris_epic` is worth supporting because it is substantially easier to
  compute from gridded soil products, is precedented in open modeling systems,
  and provides a useful sensitivity or fallback path when ancillary class
  mappings are weak or unavailable
- For the first user-facing release, the primary UX should not ask ordinary
  users to choose between them unless there is a concrete reason. The default
  should simply be `polaris_nomograph`, with `polaris_epic` available through
  advanced config or analyst workflows

#### Important Distinction

Do not substitute WEPP `Ki` or `Kr`, or values from
`wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv`, for `RUSLE`
`K`. They are not the same parameter.

### C

The `C` factor needs two source modes that share one common calculation engine.

#### Common Engine

Initial `C` should be a simplified `RUSLE`-style cover-management factor driven
by:

- canopy protection
- surface protection
- optional roughness and consolidation terms later

The first implementation should use:

- canopy term from live cover and landuse-specific defaults
- surface term from bare ground, litter, rock, and low vegetation cover
- roughness, biomass, and consolidation set to neutral defaults unless separate
  data are introduced

#### Mode 1: `observed_rap`

Use observed RAP fractional cover as the main condition source.

Best fit:

- current condition
- recent post-fire condition
- monitoring mode

Interpretation cautions:

- post-fire RAP vegetation recovery should not automatically imply a strongly
  protective `C`
- litter and bare ground must remain first-class controls

#### Mode 2: `scenario_sbs`

Use explicit lookup values keyed by:

- landuse class
- SBS class
- optionally years since disturbance

Best fit:

- counterfactual pre-fire versus post-fire comparisons
- planning mode
- cases where observed RAP does not represent the scenario being compared

#### Lookup Recommendation

Do not overload `disturbed_landsoil_lookup.csv` for `RUSLE C`.

Create a dedicated lookup, for example:

- `wepppy/nodb/mods/rusle/data/rusle_c_lookup.csv`

Suggested fields:

- `landuse_class`
- `sbs_class`
- `years_since_disturbance`
- `canopy_cover`
- `ground_cover`
- `litter_cover`
- `rock_cover`
- `effective_fall_height`
- `c_override`
- `notes`

### P

Initial default:

- `P = 1.0`

Only vary `P` when explicit support-practice or treatment data exist. Avoid
invented `P` values.

Potential future `P` inputs:

- contouring
- terracing
- skid-trail treatment classes
- road drainage or hydrologic disconnection treatments

## Controller Design

Proposed controller: `Rusle`

Responsibilities:

- validate required run products and factor source availability
- acquire or align factor inputs to the run DEM grid
- build hillslope mask
- compute factor rasters
- compute final `A` raster
- persist run-scoped artifacts under `<wd>/rusle/`
- expose metadata and summaries through NoDb and catalog entry updates

Likely dependencies:

- `Ron`
- `Watershed`
- `Landuse`
- `Climate`
- `Disturbed`
- `POLARIS`
- `RAP`
- `wepppyo3.climate` static `R` routine

## Config Direction

Initial config should likely branch from `disturbed9002_wbt` rather than change
it in place.

Possible config additions:

```ini
[nodb]
mods = ["disturbed", "debris_flow", "ash", "treatments", "polaris", "rap", "rusle"]

[rusle]
enabled = true
ls_mode = "wbt_rusle"
ls_routing = "dinf"
r_mode = "cligen_static"
k_mode = "polaris_nomograph"
c_mode = "observed_rap"
p_mode = "default"
mask_nlcd_water = true
mask_nlcd_urban = true
mask_nlcd_wetlands = true
mask_channels = true
max_slope_length_m = None
```

The scientific defaults above are the current working position. Optional
operational controls such as `max_slope_length_m` should only change with
explicit validation or documented visualization needs.

## Source Precedence

Recommended initial precedence:

- `LS`
  - purpose-built WBT `RusleLsFactor`
- `R`
  - `cligen_static` from the run WEPP climate file
  - no external gridded runtime source in the first implementation
- `K`
  - `polaris_nomograph` for default visualization mode
  - `polaris_epic` for advanced fallback or sensitivity mode
  - `gnatsgo_kffact`, `gnatsgo_kwfact`, `gssurgo_kffact`, or `gssurgo_kwfact`
    for benchmark or reference mode
- `C`
  - `observed_rap`
  - or `scenario_sbs`
- `P`
  - `1.0` unless explicit treatment/practice inputs exist

## Validation Expectations

At minimum, validation should include:

- factor sanity checks by landscape position
- masked-versus-unmasked comparison review
- parity checks between the shared Rust hyetograph helper and the existing
  Python hyetograph behavior where comparable
- static-`R` regression tests from `.cli` inputs, including breakpoint-climate
  coverage if supported by the Rust parser path
- annual `EI30` distribution review for representative climates
- known hotspot comparison against field or mapped observations
- `polaris_nomograph` versus `polaris_epic` comparison on representative areas
  of interest
- `polaris_nomograph` or `polaris_epic` versus NRCS `kffact` or `kwfact`
  comparison on representative areas of interest, matched to the fragment
  assumption actually used
- pre-fire/post-fire directional checks
- sensitivity checks for `LS`, `R`, and `C`
- sensitivity checks across `K` estimators where the differences materially
  affect the map pattern

Longer term, the mod should be checked against:

- post-fire erosion monitoring plots
- sediment fence or trap datasets
- independent erosivity references where appropriate
- known disturbed hillslope inventories

## Open Questions

- Which exact storm kinetic-energy equation and unit convention should be
  encoded in the first `wepppyo3` static-`R` routine?
- What is the preferred public API shape for the shared `wepppyo3` hyetograph
  helper: segments only, or segments plus derived peak-intensity windows?
- What is the preferred initial `C` formula for translating RAP fractions into
  a defensible cover-management factor?
- Should `scenario_sbs` support a time axis from day one, or only static
  low/moderate/high severity lookups?
- Which ancillary source should provide the optional profile coarse-fragment
  adjustment for `POLARIS`-derived `K`, if any?
- Which operational datasets, if any, should populate the optional
  `blocking_mask` for roads, skid trails, and treatment features in early
  deployments?

## Initial Milestones

1. Create the WBT `RusleLsFactor` tool with `Desmet-Govers` `L`,
   `McCool/RUSLE` `S`, `DInf` default routing, and diagnostic outputs; then
   validate outputs on representative disturbed terrain.
2. Add a reusable Rust WEPP hyetograph reconstruction helper to
   `wepppyo3.climate` and validate it against existing Python behavior where
   comparable.
3. Implement a `wepppyo3.climate` static-`R` routine from WEPP `.cli` inputs
   using that helper, with no production Python fallback.
4. Extend Polaris acquisition for `polaris_nomograph` and `polaris_epic`,
   starting with the nomograph-facing path and paired NRCS `K` benchmark
   support.
5. Define the shared `C` engine and the two source modes.
6. Implement the `Rusle` NoDb controller and run-scoped artifact layout.
7. Add validation runs using `disturbed9002_wbt`-style workflows.

## Related Local Files

- `wepppy/nodb/configs/disturbed9002_wbt.cfg`
- `wepppy/nodb/mods/polaris/polaris.py`
- `wepppy/nodb/mods/rap/rap.py`
- `wepppy/nodb/core/landuse.py`
- `wepppy/climates/cligen/cligen.py`
- `wepppy/wepp/interchange/_utils.py`
- `wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv`
- `/workdir/wepppyo3/cli_revision/src/lib.rs`
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/terrain_analysis/sediment_transport_index.rs`

## References and Data Sources

These references are the current basis for academic defensibility in this
working specification. Upstream climate-source products may still matter when
building WEPP climate files, but they are intentionally not treated as direct
runtime `R` inputs in the current `Rusle` design.

### Core `RUSLE` Basis

- Renard, K. G., Foster, G. R., Weesies, G. A., McCool, D. K., and Yoder,
  D. C., coordinators, 1997. *Predicting Soil Erosion by Water: A Guide to
  Conservation Planning with the Revised Universal Soil Loss Equation
  (RUSLE)*. USDA Agriculture Handbook No. 703.
  Canonical `RUSLE1` reference for factor definitions and standard practice.
- USDA-ARS. *RUSLE2 Science Documentation*.
  https://www.ars.usda.gov/ARSUserFiles/60600505/rusle/rusle2_science_doc.pdf
  Primary science reference for `RUSLE2`, especially the cover-management
  factor and its canopy and ground-cover subfactors.
- USDA-NRCS. *RUSLE2 Handbook*.
  https://www.nrcs.usda.gov/sites/default/files/2022-10/RUSLE2%20Handbook_0.pdf
  Operational guidance on factor selection, application limits, and hillslope
  profile framing.
- USDA-NRCS. *National Agronomy Manual*.
  https://www.nrcs.usda.gov/sites/default/files/2022-10/National-Agronomy-Manual.pdf
  NRCS planning context for `RUSLE`-family use and conservation practice
  interpretation.

### `LS` Factor and Rasterization

- Desmet, P. J. J., and Govers, G., 1996. *A GIS procedure for automatically
  calculating the USLE LS factor on topographically complex landscape units*.
  *Journal of Soil and Water Conservation*, 51(5), 427-433.
  Canonical raster `L`-factor reference for upslope-area-based `LS`
  calculation.
- McCool, D. K., Brown, L. C., Foster, G. R., Mutchler, C. K., and Meyer,
  L. D., 1987. *Revised Slope Steepness Factor for the Universal Soil Loss
  Equation*. *Transactions of the ASAE*, 30(5), 1387-1396.
  https://doi.org/10.13031/2013.30576
  Canonical `S`-factor reference for the two-segment `RUSLE` steepness
  relationship and the separate short-slope branch that is intentionally not
  used in this 30 m gridded v1 design.
- McCool, D. K., Foster, G. R., Mutchler, C. K., and Meyer, L. D., 1989.
  *Revised slope length factor for the universal soil loss equation*.
  *Transactions of the ASAE*, 32(5), 1571-1576.
  https://doi.org/10.13031/2013.31192
  Canonical `RUSLE` reference for the slope-length exponent formulation used
  with rasterized `L`.
- Nearing, M. A., 1997. *A Single, Continuous Function for Slope Steepness
  Influence on Soil Loss*. *Soil Science Society of America Journal*, 61(3),
  917-919.
  https://doi.org/10.2136/sssaj1997.03615995006100030029x
  Continuous steep-slope alternative reviewed for this specification but not
  adopted in the v1 `LS` method.
- Tarboton, D. G., 1997. *A new method for the determination of flow
  directions and upslope areas in grid digital elevation models*.
  *Water Resources Research*, 33(2), 309-319.
  https://doi.org/10.1029/96WR03137
  Scientific basis for `D-infinity` routing and specific catchment area.
- Panagos, P., Borrelli, P., and Meusburger, K., 2015.
  *A New European Slope Length and Steepness Factor (LS-Factor) for Modeling
  Soil Erosion by Water*. *Geosciences*, 5(2), 117-126.
  https://doi.org/10.3390/geosciences5020117
  Open-access precedent for implementing `Desmet and Govers (1996)` with a
  multiple-flow algorithm at continental scale and for avoiding arbitrary
  global slope-length caps.
- Benavidez, R., Jackson, B., Maxwell, D., and Norton, K., 2018.
  *A review of the (Revised) Universal Soil Loss Equation ((R)USLE): with a
  view to increasing its global applicability and improving soil loss
  estimates*. *Hydrology and Earth System Sciences*, 22, 6059-6086.
  https://doi.org/10.5194/hess-22-6059-2018
  Review of `RUSLE` factor choices, limitations, and common rasterized `LS`
  implementations in complex terrain.

### Open-Source `LS` Implementation Precedents

- GRASS GIS. *r.watershed manual*.
  https://grass.osgeo.org/grass-stable/manuals/r.watershed.html
  Useful open implementation precedent for default multiple-flow routing,
  `blocking`, and `max_slope_length` controls. The manual also makes clear that
  its `LS` equations are not the exact canonical `Desmet and Govers (1996)`
  raster path adopted here.
- SAGA GIS. *Tool Library Documentation: LS-Factor, Field Based*.
  https://saga-gis.sourceforge.io/saga_tool_doc/9.9.2/ta_hydrology_25.html
  Useful open implementation precedent for exposing `Desmet and Govers (1996)`
  as a named method and for handling aspect-dependent specific catchment area.

### `R` Factor and Precipitation Data

- Wischmeier, W. H., and Smith, D. D., 1978. *Predicting Rainfall Erosion
  Losses: A Guide to Conservation Planning*. USDA Agriculture Handbook No. 537.
  Canonical `USLE` reference for erosivity and the storm energy-intensity
  basis of `EI30`.
- USDA-ARS. *Revised Universal Soil Loss Equation 1.06c: Description of
  RUSLE1.06c*.
  https://www.ars.usda.gov/southeast-area/oxford-ms/national-sedimentation-laboratory/watershed-physical-processes-research/docs/revised-universal-soil-loss-equation-106-description-of-rusle106c/
  Useful USDA summary of `R` as the average annual sum of individual storm
  erosivity values.
- USDA-ARS. *General Description of the CLIGEN Model and its History*.
  https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/cligen/cligendescription.pdf
  Official description of `CLIGEN` as the WEPP stochastic weather generator and
  of its storm-parameter outputs, including storm duration, time to peak, and
  peak intensity.
- Panda, S. S., Amatya, D. M., Grace, J. M., Caldwell, P., and Marion, D. A.,
  2022. *Extreme precipitation-based vulnerability assessment of road-crossing
  drainage structures in forested watersheds using an integrated environmental
  modeling approach*. *Environ. Model. Softw.*, 155, 105413.
  https://doi.org/10.1016/j.envsoft.2022.105413
  Important precedent for an event-oriented `R` workflow using a `NOAA PFDS
  I30` raster rather than a canonical annual erosivity surface.
- Mukherjee, S., Grushecky, S., Aust, W. M., Wang, J. J., Amatya, D. M.,
  Caldwell, P. V., Marion, D. A., Grace, J. M., and Panda, S. S., 2025.
  *Hydro-geomorphological assessment of culvert vulnerability to flood-induced
  soil erosion using an ensemble modeling approach*. *Environ. Model. Softw.*,
  183, 106243.
  https://doi.org/10.1016/j.envsoft.2024.106243
  Follow-on paper that states the `NOAA-Atlas14 30-min 100-yr` `PI30` workflow
  and the piecewise kinetic-energy relation used in the culvert-model lineage.

### `K` Factor and Soil Data

- Chaney, N. W., Minasny, B., Herman, J. D., Nauman, T. W., Brungard,
  C. W., Morgan, C. L. S., McBratney, A. B., Wood, E. F., and Yimam, Y.,
  2019. *POLARIS Soil Properties: 30-m Probabilistic Maps of Soil Properties
  Over the Contiguous United States*. *Water Resources Research*, 55(4),
  2916-2938.
  https://doi.org/10.1029/2018WR022797
  Primary reference for what `POLARIS` is, how it was built, and why it can
  supply finer spatial variability than polygon soil-survey products.
- USDA-NRCS. *Gridded Soil Survey Geographic (gSSURGO) Database*.
  https://www.nrcs.usda.gov/resources/data-and-reports/gridded-soil-survey-geographic-gssurgo-database
  Preferred U.S. gridded soil product when `kwfact` or `kffact` coverage is
  suitable.
- USDA-NRCS. *Gridded National Soil Survey Geographic Database (gNATSGO)*.
  https://www.nrcs.usda.gov/resources/data-and-reports/gridded-national-soil-survey-geographic-database-gnatsgo
  U.S. national gridded soil product and likely broad-coverage fallback to
  `gSSURGO`.
- USDA-NRCS. *Soil Data Access Related Tables: Table Column Descriptions*.
  https://sdmdataaccess.nrcs.usda.gov/documents/TableColumnDescriptionsReport.pdf
  Official definitions for `kwfact` and `kffact`, including the distinction
  that `kwfact` includes rock-fragment adjustment.
- SWAT+ Documentation. *Soil Erodibility Factor*.
  https://swatplus.gitbook.io/io-docs/theoretical-documentation/section-4-erosion/sediment/musle/soil-erodibility-factor
  Official open documentation for both the `Wischmeier` nomograph-style
  equation and the `Williams (1995)` `EPIC` alternative used here as the
  secondary `POLARIS` estimator.
- USDA-ARS. *RUSLE2 User Reference Guide*.
  https://www.ars.usda.gov/ARSUserFiles/60600505/RUSLE/RUSLE2_User_Ref_Guide.pdf
  Primary source for the fallback very-fine-sand estimation equation used here
  when only sand, silt, and clay are available for the `polaris_nomograph`
  path.
- Rossiter, D. G., Poggio, L., Beaudette, D., and Libohova, Z., 2022.
  *How well does digital soil mapping represent soil geography? An
  investigation from the USA*. *SOIL*, 8, 559-586.
  https://doi.org/10.5194/soil-8-559-2022
  Important caution that `POLARIS` and other digital soil mapping products can
  smooth local soil geography or introduce artifacts relative to field-survey
  products.
- Shojaeezadeh, S. A., Al-Wardy, M., Nikoo, M. R., Ghorbani Mooselu, M.,
  Alizadeh, M. R., Adamowski, J. F., Moradkhani, H., Alamdari, N., and
  Gandomi, A. H., 2024. *Soil erosion in the United States: Present and future
  (2020-2050)*. *Catena*, 242, 108074.
  https://doi.org/10.1016/j.catena.2024.108074
  Open preprint with method detail:
  https://opus.lib.uts.edu.au/bitstream/10453/167179/2/2207.06579v1.pdf
  Recent CONUS-scale precedent for deriving soil erodibility from `POLARIS`
  and ancillary soil datasets rather than relying only on polygon-based NRCS
  `K` values. The preprint method details are also useful because they show the
  practical approximation burden of a `POLARIS` nomograph path, including
  inferred structure and permeability classes and the lack of a directly
  observed very-fine-sand field.

### `C` Factor, Cover Data, and Masking

- Allred, B. W., Bestelmeyer, B. T., Boyd, C. S., Brown, C., Davies, K. W.,
  Duniway, M. C., Ellsworth, L. M., Erickson, T. A., Fuhlendorf, S. D.,
  Griffiths, T. V., Jansen, V., Jones, M. O., Karl, J. W., Knight, A. C.,
  Maestas, J. D., Maynard, J. J., McCord, S. E., Naugle, D. E., Starns, H. D.,
  Twidwell, D., and Uden, D. R., 2021. *Improving Landsat predictions of
  rangeland fractional cover with multitask learning and uncertainty*.
  *Methods in Ecology and Evolution*.
  https://doi.org/10.1111/2041-210X.13564
  Primary reference for the RAP fractional-cover product used in the
  `observed_rap` `C` mode. The publication also cautions that RAP should be
  interpreted alongside local data and expert knowledge.
- Multi-Resolution Land Characteristics Consortium. *National Land Cover
  Database Class Legend and Description*.
  https://www.mrlc.gov/sites/default/files/NLCDclasses.pdf
  Official land-cover class definitions supporting water, developed, and
  wetland masking decisions.
- U.S. Environmental Protection Agency. *National Guidance: Water Quality
  Standards for Wetlands*.
  https://www.epa.gov/cwa-404/national-guidance-water-quality-standards-wetlands
  Useful reference for the point that wetlands often have important sediment
  assimilation, storage, and water-quality functions, which supports treating
  them as outside the primary upland detachment domain of this mod.

### Notes on Evidence Hierarchy

- Prefer peer-reviewed model papers, USDA handbooks, and official agency data
  documentation over tertiary web summaries.
- Treat live operational status pages or current product indexes as
  date-stamped evidence, not permanent truths.
- When implementation starts, each factor builder should record its exact data
  source, version, retrieval date, and any local transformations in
  `rusle/manifest.json`.
