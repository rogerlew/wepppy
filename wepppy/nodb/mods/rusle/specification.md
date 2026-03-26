# RUSLE NoDb Mod Specification

> Living specification and implementation record.
>
> This file captures both current shipped behavior and forward-looking design
> direction for a gridded `RUSLE` NoDb mod based on the
> `disturbed9002_wbt` workflow.
>
> Tense convention:
>
> - present tense = behavior implemented in the current stack
> - future/modal language (`should`, `may`) = planned or optional extensions

## Purpose

Define an academically defensible path for a gridded `RUSLE` implementation in
WEPPpy using the WBT backend in `/workdir/weppcloud-wbt`, with
`disturbed9002_wbt` as the initial configuration target.

The initial product provides a spatial representation of long-term
average hillslope sheet-and-rill detachment potential, not event-scale erosion,
not sediment delivery ratio, and not channel erosion.

The first implementation remains spatially gridded in its outputs, but
uses a run-constant, climate-derived `R` rather than an external gridded
erosivity surface.

Practically, this mod is intended to replace legacy heuristic gridded erosion
visualizations with a product that is more explicit, more citable, and more
academically defensible. It is treated as a visualization and
prioritization layer, not as a regulatory estimate or a substitute for
calibrated hillslope modeling.

## Model Framing

The core equation is:

`A = R * K * LS * C * P`

For this mod:

- `A` is interpreted as long-term average annual hillslope soil loss or
  detachment potential from sheet-and-rill processes.
- The model is applied only on hillslope cells.
- Channel cells, open water, wetlands, and urban/developed cells are treated
  as out-of-domain in the default hillslope interpretation.
- Channel cells, open water, wetlands, and urban/developed cells are
  masked out of the primary output.
- The first public-facing wording emphasizes `detachment potential` or
  `relative long-term detachment hazard`, unless and until factor choices and
  validation support stronger wording.

## Initial Scope

- Target config lineage: `wepppy/nodb/configs/disturbed9002_wbt.cfg`
- Backend: WhiteboxTools fork in `/workdir/weppcloud-wbt`
- Initial geography: United States workflows first
- First `R` delivery: compute a scalar `R` from the run WEPP climate file and
  broadcast it to `r.tif`; do not depend on an external gridded runtime `R`
  source
- Current output family in standard `Rusle` builds:
  - shared outputs:
    - `rusle/r.tif`
    - `rusle/ls.tif`
    - `rusle/l.tif`
    - `rusle/s.tif`
    - `rusle/sca.tif`
    - `rusle/effective_slope_length.tif`
    - `rusle/p.tif`
    - `rusle/manifest.json`
    - `rusle/README.md`
  - mode-specific outputs:
    - `rusle/c_observed_rap.tif` or `rusle/c_scenario_sbs.tif`
    - `rusle/a_<c_mode>_<default_k_mode>.tif`
    - selected `rusle/k_polaris_nomograph.tif` and/or `rusle/k_polaris_epic.tif`
  - mode-support artifacts:
    - `rusle/c_fg.tif` (`observed_rap`)
    - `rusle/disturbed_class.tif` (`scenario_sbs`)
    - `rusle/c_lookup_used.csv` (`scenario_sbs`)
    - optional `rusle/sbs_4class.tif` when an SBS raster is provided
- Historical generic aliases remain documented design references:
  - `rusle/k.tif` is available from the K integration helper when
    `write_default_k=True`, but is not written by the standard `Rusle` build
  - `rusle/a.tif` and `rusle/mask.tif` are not emitted by the current
    standard controller path

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

Primary masking combines:

- WBT channel network products, especially `netful`
- NLCD landcover exclusions
- Optional explicit user masks

The initial NLCD exclusions include:

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
- this is documented as a default scope mask rather than a universal
  scientific statement; if a future workflow needs drained farmed wetlands,
  wet meadows, or other edge cases treated as hillslopes, that should be an
  explicit override with different assumptions

The mask also stops slope-length growth for `LS`.

## Factor Design

### LS

Implementation status: a purpose-built WBT tool (`RusleLsFactor`) now exists
and is the canonical `LS` path; `SedimentTransportIndex` remains comparison-only.

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

#### Implemented WBT Tool

Tool name: `RusleLsFactor`

Current inputs:

- `dem`
- optional precomputed `sca`
- optional precomputed `slope_deg`
- optional `channel_mask`
- optional `blocking_mask`
- optional `max_slope_length_m`
- routing mode selector, default `DInf`

Current outputs:

- `ls.tif`
- `l.tif`
- `s.tif`
- `sca.tif`
- `effective_slope_length.tif`

Implementation locations:

- `weppcloud-wbt/whitebox-tools-app/src/tools/terrain_analysis/rusle_ls_factor.rs`
- registered via:
  - `weppcloud-wbt/whitebox-tools-app/src/tools/terrain_analysis/mod.rs`
  - `weppcloud-wbt/whitebox-tools-app/src/tools/mod.rs`
- Python wrappers:
  - `weppcloud-wbt/whitebox_tools.py`
  - `weppcloud-wbt/WBT/whitebox_tools.py`
- WEPPpy integration entrypoint:
  - `wepppy/nodb/mods/rusle/ls_integration.py`

#### Locked v1 Method

`RusleLsFactor` implements one canonical v1 `LS` path rather than ship
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

###### Implementable Near-`RUSLE2` Alternative (Non-Default)

The locked v1 default remains the moderate-condition `McCool (1989)` `m`
relationship above. A closer, still implementable bridge toward `RUSLE2`
behavior is to support an optional non-default rill/interrill regime control
for sensitivity analysis:

- `m_regime = slight | moderate | high_rill`
- compute `beta_base` using the locked v1 equation
- apply `beta = 0.5 * beta_base` for `slight`
- apply `beta = 1.0 * beta_base` for `moderate` (v1 default)
- apply `beta = 2.0 * beta_base` for `high_rill`

This is still not full dynamic `RUSLE2` daily `m` behavior, but it is
implementable in raster workflows and scientifically closer than a single
hard-coded moderate regime.

##### Routing and DEM Assumptions

- Default routing mode: `DInf`
- Default flow input: specific catchment area from a hydrologically
  conditioned DEM
- The `RusleLsFactor` tool should assume the DEM is already hydrologically
  sound upstream; it should not silently fill or breach pits inside the tool
- The tool should fail fast with an explicit, actionable error when interior
  no-flow artifacts indicate a likely unconditioned DEM
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
- Define `ls_stop_mask` as the union of:
  - channel mask
  - non-hillslope land masks used by the `Rusle` controller (`NLCD` water,
    urban, wetlands by default)
  - optional explicit `blocking_mask`
- `blocking_mask` raster semantics are fixed for v1:
  - same extent, resolution, and grid alignment as `dem`
  - value `> 0` means stop cell
  - value `0` means pass-through cell
  - `NoData` in `blocking_mask` is treated as pass-through unless another
    stop-mask component marks the cell as stop
- Routing behavior at stop cells should be explicit and consistent across
  routing modes:
  - stop cells are terminal sinks with zero outflow for `LS` routing purposes
  - for multi-flow routing (`DInf`, `FD8`), any routed fraction entering a stop
    cell is terminated and should not be renormalized onto nonstop receivers
  - stop-mask cells are excluded from primary hillslope `L`, `S`, and `LS`
    outputs
- Do not treat disturbance itself as an `LS` input. Disturbance affects the
  final map through `C`, the joint hillslope mask, and scenario framing, not by
  changing the topographic factor equations
- Apply a handbook-based default slope-length cap:
  - `max_slope_length_m = 304.8` (1000 ft)
  - basis: `RUSLE2 Handbook` guidance that slope lengths longer than 1000 ft
    should generally not be used
- Allow `max_slope_length_m` override for explicit sensitivity analysis only.
  If a run changes this value, record both the value and rationale in
  `rusle/manifest.json`
- The cap is part of the canonical v1 operational science contract, not a
  hidden visualization fallback

##### Output and Interpretation Assumptions

- Required v1 outputs from `RusleLsFactor`:
  - `ls.tif`
  - `l.tif`
  - `s.tif`
  - `sca.tif`
  - `effective_slope_length.tif`
- Required metadata in output rasters and `rusle/manifest.json` for `LS`:
  - `tool = RusleLsFactor`
  - `tool_version`
  - `l_method = desmet_govers_1996`
  - `s_method = mccool_rusle_piecewise`
  - `m_method` and `m_regime`
  - `routing_mode`
  - `dem_hydrologically_sound_assumed = true`
  - `max_slope_length_m`
  - `max_slope_length_basis = rusle2_handbook_1000ft`
  - `stop_mask_components`
  - `stop_mask_routing_behavior = terminal_sink_no_renormalization`
  - `sca_source = derived | input`
  - `slope_source = derived | input`
- Required v1 metadata typing and enum spellings (for Rust/Python parity):
  - `tool` and `tool_version`: string
  - `l_method`: enum, must be `desmet_govers_1996`
  - `s_method`: enum, must be `mccool_rusle_piecewise`
  - `m_method`: enum, must be `mccool_1989_beta_moderate_base`
  - `m_regime`: enum, one of `slight`, `moderate`, `high_rill`
  - `routing_mode`: enum, one of `dinf`, `fd8`, `d8`
  - `dem_hydrologically_sound_assumed`: boolean, must be `true`
  - `max_slope_length_m`: float (`304.8` default)
  - `max_slope_length_basis`: enum, must be `rusle2_handbook_1000ft`
  - `stop_mask_components`: string list subset of
    `channel_mask`, `nlcd_water`, `nlcd_urban`, `nlcd_wetlands`,
    `blocking_mask`
  - `stop_mask_routing_behavior`: enum, must be
    `terminal_sink_no_renormalization`
  - `sca_source`: enum, one of `derived`, `input`
  - `slope_source`: enum, one of `derived`, `input`
  - `blocking_mask_source`: enum, one of `none`, `input_raster`
- The target interpretation is broad hillslope pattern and relative detachment
  potential at the run cell size, not microtopographic truth
- `SedimentTransportIndex` may still be exported as an auxiliary comparison
  layer, but not substituted for canonical `LS`

The first implementation favors transparency and diagnostic outputs
over micro-optimization.

### R

Current runtime direction: use the run WEPP climate file to compute a static,
non-gridded `R` for the area of interest. In the current implementation, `R`
is spatially uniform within a run unless and until a separate gridded-climate
extension is intentionally added.

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

- Preferred first shipping mode and current default
- Use the run WEPP climate file as the source of truth for rainfall erosivity
  when the product goal is to approximate the erosivity used by WEPP in the
  same run
- Compute one scalar `R` for the full run climate record, then broadcast that
  value over the unmasked AOI
- Treat `PRISM`, `NOAA Atlas 14`, and similar external precipitation products
  as upstream climate-generation inputs only, not as runtime `R` inputs for
  the `Rusle` mod

Interpretation note:

- `cligen_static` is the WEPP-aligned approximation path in this spec
- it is not the only academically defensible long-term erosivity climatology
  that the mod may eventually support
- the planned `momm2025` mode below is complementary rather than contradictory:
  it targets published RUSLE2 planning climatology, not replay of the run's
  WEPP storm sequence

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
  derived intensities, including `prcp`, `dur`, `tp`, `ip`,
  `peak_intensity_10`, `peak_intensity_15`, `peak_intensity_30`, and
  `peak_intensity_60`

`climate/wepp_cli.parquet` is therefore the right audit and interchange
artifact. It should not be treated as the canonical computational input for
`cligen_static R`. The `.cli` file should remain the source of truth, both
because it is the native WEPP climate representation and because breakpoint
climate support is not guaranteed to round-trip through the parquet export.
The required scientific path still runs through segment-based `E` from the
reconstructed WEPP storm shape.

#### Implementation Direction

The first production implementation did two related things in
`wepppyo3.climate`:

1. added a reusable Rust WEPP hyetograph reconstruction helper
2. built the `cligen_static R` routine on top of that shared helper

Delivered direction:

- Added a reusable Rust WEPP hyetograph reconstruction helper so existing
  callsites can adopt the Rust path over time
- Where callsites already have working Python hyetograph logic, Python fallback
  remained available during migration; new fallback paths were not added where
  none already existed
- Treated breakpoint-climate hyetograph/intensity support as Rust-first:
  if no legacy Python fallback path already exists for a breakpoint use case,
  no new Python fallback was added as part of this package
- Added a `wepppyo3.climate` routine to calculate run-level static `R` from a
  WEPP `.cli` file
- Reused the existing Rust climate-file parser in `wepppyo3` rather than
  round-tripping large storm tables through Python
- Kept the source of truth as the WEPP `.cli` file; `wepp_cli.parquet` remains
  an audit artifact rather than an alternate static-`R` input
- Did not add a production Python fallback for `cligen_static R`; it is
  implemented directly in Rust once the shared hyetograph helper exists
- For this package, cross-repo release synchronization remains limited to the
  canonical WEPPpy runtime target:
  `/workdir/wepppyo3/release/linux/py312/`
- Returned at least the mean annual `R` and per-year annual erosivity totals
  for manifesting and QA
- Regression-tested the Rust hyetograph helper against the existing
  `cligen.py` behavior where comparable, and tested static `R` from `.cli`
  inputs directly in Rust

Implementation status (2026-03-21):

- This scope is completed in
  `docs/work-packages/20260320_rusle_r_static_hyetograph_api/`.
- `wepppyo3.climate` now ships:
  - `build_hyetograph_non_breakpoint(...)`
  - `build_hyetograph_breakpoint(...)`
  - `compute_peak_intensities_from_hyetograph(...)`
  - `compute_peak_intensities_non_breakpoint(...)`
  - `compute_peak_intensities_breakpoint(...)`
  - `compute_static_r_from_cli(...)`
- WEPPpy callsites in `cligen.py`, climate artifact export, interchange, and
  return-period staging are migrated to canonical `peak_intensity_*` outputs.

#### Static-`R` v1 Storm Kinetic Energy Contract (Resolved)

For `cligen_static` v1, storm kinetic energy is fixed to a WEPP/AH537-aligned
SI convention:

- segment intensity `i_mm_hr` comes from reconstructed WEPP hyetograph segments
- segment unit energy:
  - `e = 0` when `i_mm_hr <= 0`
  - `e = min(0.119 + 0.0873 * log10(i_mm_hr), 0.283)` when `i_mm_hr > 0`
- `e` units: `MJ ha^-1 mm^-1`
- segment depth `delta_v_mm` units: `mm`
- storm energy `E_event = sum(e * delta_v_mm)` units: `MJ ha^-1`
- `I30_event` units: `mm hr^-1` from the max continuous 30-minute window over
  the same reconstructed storm
- event erosivity `EI30_event = E_event * I30_event` units:
  `MJ mm ha^-1 h^-1`

Annual and run-level aggregation:

- `R_year = sum(EI30_event)` over qualifying storms in a simulation year
- `R_mean = mean(R_year)` across available simulation years
- v1 reported run-level `R` uses `R_mean` in `MJ mm ha^-1 h^-1`

Qualifying-storm convention for v1:

- include storms with depth `>= 12.5 mm` (`0.5 in`)
- storms below `12.5 mm` are excluded until the canonical high-intensity
  exception path is explicitly implemented

Rationale:

- keeps static `R` aligned with WEPP storm-shape energy behavior for this
  stack (`/workdir/wepp-forest/src/idat.for`)
- avoids introducing a second erosivity-energy convention in the same runtime
  workflow
- `RUSLE2` Eq. 6.2 (`e = 0.29 * (1 - 0.72 * exp(-0.082 * i))`) remains a
  future optional mode, not the v1 default

#### Resolved Contract: Hyetograph API and Breakpoint Artifact Compatibility

The shared `wepppyo3.climate` public contract is resolved as:

- ship both low-level segment builders and peak-intensity helpers
- treat peak-intensity helpers as the canonical WEPPpy callsite surface
- keep segment helpers public for static `R` (`EI30`) and parity testing

Preferred public function shape:

- `build_hyetograph_non_breakpoint(...)`
- `build_hyetograph_breakpoint(...)`
- `compute_peak_intensities_from_hyetograph(...)`
- convenience wrappers:
  - `compute_peak_intensities_non_breakpoint(...)`
  - `compute_peak_intensities_breakpoint(...)`

Canonical peak-intensity output keys:

- `peak_intensity_10`
- `peak_intensity_15`
- `peak_intensity_30`
- `peak_intensity_60`

Backward-compatibility contract for `climate/wepp_cli.parquet`:

- always emit: `dur`, `tp`, `ip`, `storm_duration_hours`, `storm_duration`,
  `peak_intensity_10`, `peak_intensity_15`, `peak_intensity_30`,
  `peak_intensity_60`
- breakpoint rows must carry real `peak_intensity_*` values (no `-1` sentinel)
- breakpoint rows keep `tp` and `ip` as nullable (`NULL`/`NaN`), not
  synthesized
- breakpoint `dur` and `storm_duration_*` derive from breakpoint intervals
  using WEPP-consistent duration semantics
- zero-rain rows keep `peak_intensity_* = 0.0`

Migration compatibility policy:

1. dual-write canonical snake_case intensity columns and legacy labeled
   intensity columns during migration
2. canonical snake_case becomes producer source of truth
3. reader alias tolerance remains until explicit deprecation cleanup

#### Runtime Scope Boundary

- `legacy_r_grid` is out of the initial runtime path
- `mrms_ei30` is out of the initial runtime path
- `prism_atlas_regression` is out of the initial runtime path
- `PRISM` and `NOAA Atlas 14` may still matter upstream when building or
  revising climate inputs, but they are not direct `R`-factor dependencies for
  the first `Rusle` delivery

#### Planned Additional Runtime Mode: `momm2025_county_region`

This mode is implemented in the runtime controller.

Purpose:

- give the mod a second `R` path tied to the public Momm et al. (2025)
  RUSLE2 isoerodent update for the continental US
- keep `cligen_static` as the WEPP-aligned path when the goal is to approximate
  the erosivity used by WEPP for the run
- let users opt into a published planning-climatology source without treating
  it as the same thing as the run's WEPP climate history

Vendored data assets:

- `wepppy/nodb/mods/rusle/data/momm2025/momm2025_county_region_monthly_r.parquet`
- `wepppy/nodb/mods/rusle/data/momm2025/momm2025_counties_conus_2010_500k.geoparquet`

Academic highlights to preserve in implementation notes and manifests:

- the paper updates operational RUSLE2 isoerodent generation for the
  continental US
- the published workflow is reproducible and updatable rather than dependent on
  older hand-built surfaces
- the supplement distributes monthly erosivity values because RUSLE2 consumes
  monthly climate inputs
- the paper highlights small-event handling, spatially varying recurrence
  intervals, and weighted interpolation
- the improvement claim is mainly smoother spatial and temporal behavior while
  staying broadly aligned with official RUSLE2 practice, not a claim that every
  location's absolute `R` changes dramatically

Availability boundary:

- dataset coverage is CONUS plus DC, not Alaska or Hawaii
- the public supplement is county or `REGION` tabular data, not a complete
  polygonal sub-county map
- the county geometry companion in this repo uses the 2010 Census county
  vintage because the public dataset still uses FIPS `46113` (Shannon County,
  SD) and `51515` (Bedford city, VA)

Why it can be better:

- it offers a published and reproducible RUSLE2 planning climatology for CONUS
- it should improve smoothness and updateability relative to older manual or
  zone-built surfaces
- it is likely most useful near county or climate-zone seams and in areas where
  the older surface-construction workflow depended more heavily on manual
  adjustments or sparse-station interpolation

Shortcomings and caveats:

- it is not a WEPP run-specific erosivity reconstruction
- the public supplement does not ship sub-county `REGION` polygons
- the available public files appear to be final tabular outputs, not the full
  station-processing pipeline or cleaned storm archive
- any implementation that collapses monthly values to a single annual scalar
  must record that aggregation explicitly

Locked v1 decisions (2026-03-25):

- `momm2025_county_region` remains on the current scalar-`R` controller
  contract rather than invent a gridded erosivity surface from county data
- the runtime should select the source county by watershed centroid
- the runtime should sum the selected row's monthly values to annual `R` for
  the scalar controller contract while preserving the monthly values in
  manifest provenance
- user-facing provenance wording should stay explicit:
  - `cligen_static` label: `WEPP Climate-Derived R`
  - `cligen_static` help text:
    `Approximates the erosivity used by WEPP from this run's .cli climate record.`
  - `momm2025_county_region` label: `Momm 2025 County Climatology`
  - `momm2025_county_region` help text:
    `Uses the published Momm et al. (2025) RUSLE2 monthly erosivity climatology for the watershed centroid county.`
- provenance fields written by the eventual runtime should include enough
  detail to audit the selection, for example:
  - `r_mode`
  - `r_source_label`
  - `r_source_purpose`
  - `r_selection_method = watershed_centroid`
  - `r_selected_fips`
  - `r_selected_county`
  - `r_selected_region`
  - `r_dataset_doi`
  - `r_scalar_units`

Resolved runtime contract (2026-03-26):

- counties with multiple public `REGION` rows are resolved by matching the
  run-localised annual precipitation (inches/year) against the numeric public
  `REGION` interval labels
- there is no silent fallback to another `R` mode when the annual
  precipitation reference is unavailable or does not map to exactly one
  published `REGION` row
- this keeps the mode truthful to the public data limitation (no shipped
  sub-county `REGION` polygons) while preserving deterministic centroid-county
  behavior for both single-row and split-row counties

#### Planned Additional Runtime Mode: `canonical_rusle2`

This mode is implemented in the runtime controller.

Purpose:

- give the mod a planning-climatology path tied to the vendored official
  RUSLE2 climate-database release rather than only the newer Momm 2025 update
- expose the official RUSLE2 climate-zone polygons and climate records as a
  first-class `R` source rather than leaving them as reference-only data
- keep `cligen_static` as the WEPP-aligned path when the goal is to approximate
  the erosivity used by WEPP for the run

Vendored data assets:

- `wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_climate_records.parquet`
- `wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_climate_zones.geoparquet`
- `wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_source_files.parquet`

Why it matters:

- it is the vendored official RUSLE2 planning-climatology baseline, not a
  post-processed local fit or an indirect proxy
- it provides a broader official coverage footprint than the Momm 2025 CONUS
  update
- it allows future comparisons between the official baseline and the newer
  Momm 2025 update without leaving the repo

Shortcomings and caveats:

- it is not a WEPP run-specific erosivity reconstruction
- the official polygon bundle does not cover every official climate-table row
- the official distribution is legacy and required normalization into Parquet
  or GeoParquet for repo-native use
- some rows expose official `R_MONTHLY`, while others require monthly values to
  be derived from official precipitation and erosivity-density fields
- duplicate official climate rows can share one polygon `REC_LINK`, so the
  vendored GeoParquet intentionally carries deterministic selected-record and
  duplicate-diagnostic fields

Working v1 position:

- `canonical_rusle2` should remain on the current scalar-`R` controller
  contract
- the runtime should select the official climate zone by watershed centroid
  against the vendored GeoParquet
- the runtime should use the vendored deterministic selected record for the
  matched official `REC_LINK` and preserve enough provenance to audit the
  selection
- the user-facing label should be `Canonical RUSLE2`
- suggested help text:
  `Uses the vendored official RUSLE2 climate database and climate-zone polygons at the watershed centroid.`

Resolved runtime contract (2026-03-26):

- v1 is limited to polygon-backed official links selected by watershed
  centroid against the vendored GeoParquet
- centroid hits that resolve to polygons without a climate record are rejected
  explicitly; there is no silent fallback to table-only rows
- centroid hits that ambiguously intersect multiple `REC_LINK` polygons are
  rejected explicitly to preserve deterministic provenance
- runtime manifest provenance records at least:
  - `selected_rec_link`
  - `selected_record_name`
  - `selected_record_variant`
  - `selected_source_zip`

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
- For v1, the optional profile coarse-fragment ancillary should be the ISRIC
  SoilGrids `cfvo` layer
- That recommendation is pragmatic rather than perfect:
  - `POLARIS` does not provide a directly observed coarse-fragment raster
  - SoilGrids `cfvo` is a documented coarse-fragment property with standard
    depth layers and broad availability
  - it is suitable as a broad profile-stoniness ancillary for the high-
    resolution `POLARIS` workflow
- SoilGrids `cfvo` should be interpreted as volumetric coarse fragments in
  `cm^3/dm^3` (`vol‰`), with conversion to `vol%` by dividing stored values
  by `10`
- The current SoilGrids FAQ table should be treated as ambiguous for `cfvo`
  conversion because it lists mapped units `cm^3/dm^3 (vol‰)` but also lists
  conversion factor `100`; those two statements are inconsistent
- For this mod, prefer the unit-algebra-consistent interpretation (`/10`) and
  cross-check against live service metadata before changing scale assumptions
- It should not be described as a literal `RUSLE2` nomograph coarse-fragment
  input:
  - SoilGrids `cfvo` is a volumetric whole-soil coarse-fragment property
  - the strict `RUSLE2` nomograph coarse-fragment input is not the same
    variable definition
- Because of that mismatch, `cfvo` should only support an explicitly labeled
  approximate profile-fragment adjustment, not a claim of exact `kwfact`
  reproduction
- The ISRIC `cfvo` raster should be reprojected, resampled, and depth-aligned
  to match the `POLARIS` grid before use:
  - same CRS
  - same extent
  - same cell alignment
  - same target depth support used by the `POLARIS` near-surface aggregation
  - use the matching SoilGrids depth intervals where available, then aggregate
    onto the same near-surface support as the `POLARIS` inputs
- Metadata should retain the native SoilGrids resolution and note that the
  aligned `cfvo` layer is an upscaled ancillary, not a true 30 m observation
- Comparisons should be matched accordingly:
  - compare fine-earth `POLARIS` estimates to `kffact` where available
  - compare `cfvo`-adjusted estimates to `kwfact` where available, while
    noting the variable-definition mismatch
  - for direct coarse-fragment plausibility checks, compare against
    `SSURGO chfrags.fragvol_r` (`vol%`, whole-soil basis), not only against
    weight-based fragment fields (`fraggt10_r`, `frag3to10_r`,
    `sieveno10_r`)

Likely ancillary needs beyond the current Polaris request:

- optional ISRIC SoilGrids `cfvo` profile coarse-fragment fraction, aligned to
  the `POLARIS` grid before use
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
- In the current first user-facing release, the control exposes both options,
  with `polaris_nomograph` as the default selection and `polaris_epic`
  available as an analyst/sensitivity option

#### Important Distinction

Do not substitute WEPP `Ki` or `Kr`, or values from
`wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv`, for `RUSLE`
`K`. They are not the same parameter.

### C

The `C` factor needs two source modes that share one common calculation engine.

#### Common Engine

Initial `C` is a simplified `RUSLE`-style cover-management factor driven
by:

- surface protection
- optional canopy, roughness, and consolidation terms later

The first implementation uses:

- a `RUSLE2`-style surface-cover subfactor driven by RAP bare ground
- canopy set to a neutral default in `observed_rap` v1
- roughness, biomass, and consolidation set to neutral defaults unless separate
  data are introduced

#### Resolved Contract: Initial `observed_rap` Formula

The preferred initial `observed_rap` formula is a simplified `RUSLE2` ground-
cover path, not an `NDVI -> C` regression and not a land-cover lookup table.

Use:

- `fg = clamp(100 - bare_ground_pct, 0, 100)` as net ground cover percent
- `C = exp(-b * fg)` with `b = 0.04` for the initial implementation
- `canopy = 1.0`, `roughness = 1.0`, `biomass = 1.0`, and
  `consolidation = 1.0` in `observed_rap` v1

Rationale:

- `RUSLE2` defines the ground-cover subfactor as an exponential reduction in
  erosion with increasing net ground cover, and explicitly notes that net
  ground cover is effectively `100 - bare ground`
- RAP directly observes `bare_ground`, `litter`, and live fractional-cover
  components, but it does not directly observe the `RUSLE2` canopy inputs
  needed for a more defensible canopy subfactor, especially effective fall
  height and the split between above-ground canopy and live ground cover
- using RAP bare ground as the primary control keeps litter and exposed
  interspace as first-class drivers, which is especially important for
  post-fire and semiarid rangeland conditions
- `NDVI -> C` transforms are a weaker fit here because RAP already provides
  more physically relevant cover fractions than a greenness index, and review
  literature notes that broad `NDVI` formulas can behave unrealistically for
  grassland and woodland classes

Use RAP fractions as follows in `observed_rap` v1:

- `bare_ground` is the direct input to `fg`
- `litter`, `annual_forb_and_grass`, `perennial_forb_and_grass`, `shrub`, and
  `tree` are retained for QA, masking interpretation, and future canopy or
  roughness extensions
- do not sum RAP fractional bands into a separate surface-cover term; `RUSLE2`
  wants net ground cover rather than a potentially double-counted component sum

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

Restrict this mode to runs where the `Disturbed` module is active.

Use explicit lookup values keyed by:

- canonical `disturbed_class` family from the disturbed workflow
- SBS class

Initial implementation choice:

- static low/moderate/high severity lookups only
- no time axis in v1
- add a time axis later only if a separate recovery-trajectory package defines
  and validates it against observations

Resolved contract:

- `scenario_sbs` is a disturbed-only mode; do not expose it for generic runs
  that do not have the disturbed/SBS workflow active
- use the disturbed workflow's canonical vegetation family instead of generic
  `landuse_class`
- normalize disturbed classes before lookup so the key space stays small and
  stable:
  - `forest` and `young forest` -> `forest`
  - shrub classes -> `shrub`
  - grass classes -> `tall_grass`
- do not key the lookup by severity-specific or treatment-suffixed raw
  `disturbed_class` strings such as `forest moderate sev fire`,
  `forest high sev fire-mulch_15`, or `thinning`; severity remains the
  separate `sbs_class` dimension

#### Required Raster Preprocessing

`Rusle` is raster/cell based, so `scenario_sbs` needs a gridded
`disturbed_class` product on the run DEM grid.

- create `rusle/disturbed_class.tif` as a DEM-aligned raster of canonical
  disturbed-class family labels or integer codes
- do not reuse the hillslope-level disturbed assignment directly; the existing
  `Disturbed` workflow maps classes to hillslopes, which is sufficient for WEPP
  input generation but not for raster `RUSLE C`
- build the gridded disturbed-class raster from the same landuse-to-disturbed
  semantics used by `wepppy/wepp/management/data/disturbed.json`
- normalize to canonical families before applying SBS:
  - `forest` and `young forest` -> `forest`
  - `shrub` -> `shrub`
  - `tall grass` -> `tall_grass`
- only apply SBS burn remapping to these three canonical families
- leave all other classes unchanged by SBS severity and handle them according
  to the non-burnable-class policy table below

#### Initial `scenario_sbs` Static Matrix

The first `scenario_sbs` implementation ships with an explicit static
matrix for the burnable canonical disturbed classes. These values are initial
defaults for `rusle_c_lookup.csv`, derived from the same simplified
`RUSLE2`-style form used elsewhere in this spec:

- `C = exp(-0.04 * fg)`
- `fg` taken from the static disturbed management ground-cover defaults

| Canonical disturbed class | Unburned | Low | Moderate | High | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| `forest` | `0.0183` | `0.0334` | `0.0907` | `0.3010` | includes `young forest`; initial `fg` = `100`, `85`, `60`, `30` |
| `shrub` | `0.0273` | `0.0408` | `0.1108` | `0.3010` | initial `fg` = `90`, `80`, `55`, `30` |
| `tall_grass` | `0.0907` | `0.0907` | `0.2466` | `0.6703` | initial `fg` = `60`, `60`, `35`, `10` |

Rationale for these initial defaults:

- the values are not arbitrary lookup guesses; each row is computed directly
  from the existing static disturbed management defaults already documented in
  `wepppy/nodb/mods/disturbed/README.md`
- for this initial `scenario_sbs` path, `fg` is taken from the static
  near-surface cover state (`inrcov` / `rilcov`) rather than canopy cover
  because the v1 `C` contract in this spec is intentionally a simplified
  `RUSLE2` ground-cover formulation
- the severity progression follows the existing disturbed management templates:
  - forest ground cover declines `1.00 -> 0.85 -> 0.60 -> 0.30`
  - shrub ground cover declines `0.90 -> 0.80 -> 0.55 -> 0.30`
  - tall-grass ground cover declines `0.60 -> 0.60 -> 0.35 -> 0.10`
- those cover fractions are converted to percent (`100`, `85`, `60`, `30`,
  etc.) and then mapped through `C = exp(-0.04 * fg)`
- this means the matrix is anchored to the same disturbed scenario semantics
  that already drive WEPP management behavior, which keeps the first raster
  `scenario_sbs` implementation directionally consistent with the existing
  disturbed package rather than introducing a second, unrelated burn-severity
  interpretation
- the forest and shrub rows show monotonic erosion-protection loss from
  unburned to high severity because the underlying disturbed management
  templates already reduce near-surface cover that way
- the `tall_grass` unburned and low-severity rows are intentionally identical
  in v1 because the current disturbed management defaults assign the same
  ground-cover state (`0.60`) to both classes; if future validation shows that
  low-severity grass should diverge, the lookup table can be revised without
  changing the runtime contract
- `young forest` is folded into the canonical `forest` family to keep the
  lookup key space small and because `scenario_sbs` is keyed by canonical
  disturbed family plus severity, not by every management variant

These values are defaults, not permanent calibration truth. The matrix should
live in `rusle_c_lookup.csv` so future package work can revise it without
changing the runtime contract.

#### Non-Burnable NLCD / Disturbed-Class Policy

The classes below do not participate in the SBS burn matrix even when
`scenario_sbs` is active.

| NLCD classes | Disturbed mapping / family | SBS handling | `C` handling |
| --- | --- | --- | --- |
| `11`, `21`, `22`, `23`, `24`, `90`, `95` | water, developed, wetlands | no burn | masked; `C = nodata` |
| `12` | perennial ice/snow / no disturbed class | no burn | treat as out-of-domain and mask in `scenario_sbs` |
| `31` | `bare` | no burn | static row only; initial default `C = 1.0` |
| `73`, `74` | `short_grass` | no burn | static row only; initial default `C = 0.2019` |
| `81`, `82` | `agriculture_crops` | no burn | require explicit unburned lookup rows; do not infer wildfire severity effects |
| any other unmasked class not normalized to `forest`, `shrub`, or `tall_grass` | class-specific | no burn | require explicit unburned lookup row or fail fast |

Best fit:

- counterfactual pre-fire versus post-fire comparisons
- planning mode
- cases where observed RAP does not represent the scenario being compared

#### Lookup Recommendation

Do not overload `disturbed_landsoil_lookup.csv` for `RUSLE C`.

Create a dedicated lookup, for example:

- `wepppy/nodb/mods/rusle/data/rusle_c_lookup.csv`

Suggested fields:

- `disturbed_class`
- `sbs_class`
- `nlcd_class`
- `canopy_cover`
- `ground_cover`
- `litter_cover`
- `rock_cover`
- `effective_fall_height`
- `c_override`
- `notes`
- optional future field: `years_since_disturbance`

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

Controller: `Rusle`

Responsibilities:

- validate required run products and factor source availability
- acquire or align factor inputs to the run DEM grid
- build hillslope mask
- compute factor rasters
- compute final `A` raster
- persist run-scoped artifacts under `<wd>/rusle/`
- expose metadata and summaries through NoDb and catalog entry updates

Current dependencies:

- `Ron`
- `Watershed`
- `Landuse`
- `Climate`
- `Disturbed`
- internal `Polaris` NoDb substrate for aligned soil-property rasters
- internal single-year RAP raster retrieval built on the RAP dataset access
  layer, but not on the `rap` or `rap_ts` NoDb mods
- `wepppyo3.climate` static `R` routine

## Config Direction

Initial development branched from `disturbed9002_wbt` rather than changing it
in place.

Possible extended config additions (beyond the currently consumed runtime
options):

```ini
[nodb]
mods = ["disturbed", "debris_flow", "ash", "treatments", "polaris", "rusle"]

[rusle]
enabled = true
ls_mode = "wbt_rusle"
ls_routing = "dinf"
r_mode = "cligen_static"
# additional planning-climatology modes:
# r_mode = "momm2025_county_region"  # watershed-centroid county + annual-precip REGION bin
# r_mode = "canonical_rusle2"  # watershed-centroid official polygon (polygon-backed only)
k_mode = "polaris_nomograph"
c_mode = "observed_rap"
rap_year = "auto"
p_mode = "default"
mask_nlcd_water = true
mask_nlcd_urban = true
mask_nlcd_wetlands = true
mask_channels = true
max_slope_length_m = 304.8
```

The scientific defaults above remain the current working position. Optional
operational controls such as `max_slope_length_m` should still only change with
explicit validation and documented rationale.

Because `polaris` currently exists only to support `rusle`, its runtime default
request is shifted to the `Rusle K` layer set rather than the earlier minimal
test request:

- properties: `sand`, `silt`, `clay`, `om`, `bd`, `ksat`
- statistics: `mean`
- depths: `0_5`, `5_15`

## User Specification

### Availability and Activation

- `Rusle` is a user-toggleable optional mod in the run-header `Mods` menu for
  disturbed projects
- eligibility uses the presence of the `disturbed` mod and the WBT delineation
  backend; `Rusle` is not presented as a generic mod for unrelated run types
- enabling `rusle` ensures the internal `polaris` substrate is available for
  the run
- enabling `rusle` does not auto-add `rap` or `rap_ts`
- `disturbed` is already treated as non-removable for this project class, so
  `rusle` does not need a separate `disturbed` removal guard
- `polaris` does not have its own user-facing mods toggle or dedicated run-page
  section in this workflow
- enabling `rusle` only registers/reveals the workflow; it does not trigger a
  background build automatically
- disabling `rusle` removes only `rusle`; cleanup of internal `polaris` state
  remains an implementation detail rather than a user-facing contract

### Run-Page Placement

- includes a dedicated `RUSLE` navigation entry and control section on the run
  page
- appears after `WEPP`
- follows the standard `control_shell` pattern:
  - status area
  - stacktrace area
  - job hint
  - build/refresh action
  - concise method summary
- target UX still includes showing prerequisite readiness for at least:
  - DEM/watershed
  - landuse
  - climate
  - disturbed

### Required v1 Controls

- build/refresh button for the run-scoped `RUSLE` artifacts
- build/refresh enqueues an RQ job rather than running inline in the request
  cycle
- `C` mode selector:
  - `observed_rap`
  - `scenario_sbs`
- default `C` mode in the first user-facing release is `observed_rap`
- `RAP` year selector shown only when `c_mode = observed_rap`
  - single year only
  - valid year choices come from the same RAP implementation surface used by
    [rap.py](../rap/rap.py), which remains the source of truth for supported
    single-year RAP availability
  - default is the latest available completed RAP year unless a saved
    `rusle.rap_year` already exists
- `K` mode selector:
  - `polaris_nomograph` default
  - `polaris_epic` supported sensitivity option

### Additional v1 Controls Worth Exposing

- `LS` routing selector in an advanced section:
  - `dinf` default
  - `fd8` optional sensitivity path
  - keep `d8` out of the ordinary UI unless it is intentionally added as a
    comparison-only analyst mode
- `max_slope_length_m` numeric input in an advanced section, default `304.8`
- masking toggles in an advanced section:
  - `mask_nlcd_water`
  - `mask_nlcd_urban`
  - `mask_nlcd_wetlands`
  - `mask_channels`

### Fixed or Read-Only Method Rows

These should be shown as method summary rows rather than user-editable fields
in the first release:

- `LS mode = wbt_rusle`
- `R mode = cligen_static`
- `R mode = momm2025_county_region` (split counties resolved by annual-precip REGION bin)
- `R mode = canonical_rusle2` (polygon-backed official links only in v1)
- `P mode = default` (`1.0`)

### `scenario_sbs` User-Facing Contract

- `scenario_sbs` consumes the disturbed workflow's SBS state; do not add
  a second SBS upload control inside the `Rusle` panel
- `scenario_sbs` stays fixed to the canonical RUSLE disturbed-family policy and
  does not inherit optional Disturbed runtime knobs such as
  shrub/grass burn toggles
- when a disturbed/BAER SBS map exists, use it
- when no SBS map exists, `scenario_sbs` remains allowed and uses
  `unburned` lookup parameters everywhere
- the UI surfaces that state explicitly, for example:
  `No SBS map detected; using unburned parameters.`
- the gridded `disturbed_class` raster remains required and must still be
  derived on the DEM grid from the disturbed mapping; do not substitute the
  hillslope-only disturbed assignment

### `observed_rap` User-Facing Contract

- `Rusle` retrieves the selected single-year RAP raster directly for the
  run
- reuse the low-level RAP dataset access layer, but do not require the `rap` or
  `rap_ts` NoDb modules to be enabled or instantiated
- store the retrieved RAP raster under the run-scoped `rusle/` tree and record
  the selected year in manifest/catalog metadata
- reuse an existing aligned RAP artifact only when the saved artifact matches
  the requested year and the current run extent/alignment contract; otherwise
  refresh it explicitly

### Internal `polaris` Acquisition Contract

- there is no separate `POLARIS` UI for `Rusle` users in v1
- when a `Rusle` build needs `K` inputs, the controller checks whether the
  aligned required `POLARIS` layers already exist for the run
- if required aligned layers are missing, `Rusle` calls the existing
  `Polaris` NoDb controller automatically
- the automatic request targets the `Rusle K` substrate layer set:
  - properties: `sand`, `silt`, `clay`, `om`, `bd`, `ksat`
  - statistics: `mean`
  - depths: `0_5`, `5_15`
- even if `Polaris` defaults are changed to match the `Rusle K` request, the
  `Rusle` controller still passes an explicit acquisition payload so the
  build remains deterministic and self-describing in manifest history
- if the existing `polaris/manifest.json` does not satisfy the required layer
  set or alignment contract, `Rusle` refreshes the missing or drifted
  layers explicitly rather than assuming the current `polaris/` tree is valid
- this remains idempotent:
  - if the required aligned layers already exist and satisfy the request,
    `Rusle` reuses them without re-fetching

### Build Scope Contract

- the standard `Rusle` build writes only the selected active-mode outputs
  for user-facing factors, not every alternate estimator
- specifically:
  - selected `K` mode outputs only
  - selected `C` mode output only
  - active `LS`, `R`, `P`, and final `A` outputs
- inactive comparison artifacts are reserved for explicit future
  comparison/debug workflows so ordinary users are less likely to browse or
  download the wrong raster by mistake

### Artifact Naming Contract

- user-facing factor artifacts use mode-specific filenames rather than
  only generic names, so browsing/downloading makes the active estimator
  obvious
- generic aliases may still exist for internal convenience, but mode-specific
  names should be the primary auditable outputs

### GL-Dashboard Output Visualization Contract

- `Rusle` outputs are discoverable in the run `gl-dashboard` as raster
  overlays when corresponding run artifacts exist
- the layer list includes a dedicated `RUSLE` section under
  subcatchment overlays, placed after `WEPP`
- `RUSLE` layer discovery is artifact-driven (only show rasters that are
  present), with mode-specific filenames as the primary selectors:
  - `A`: `a_observed_rap_polaris_nomograph.tif`,
    `a_observed_rap_polaris_epic.tif`,
    `a_scenario_sbs_polaris_nomograph.tif`,
    `a_scenario_sbs_polaris_epic.tif`
  - `C`: `c_observed_rap.tif`, `c_scenario_sbs.tif`
  - `K`: `k_polaris_nomograph.tif`, `k_polaris_epic.tif`
- colormap and legend contract:
  - `A` uses `jet2`, units `t/ha/yr`, and a dynamic legend range derived from
    finite raster values for the active artifact
  - `C` uses `viridis`, units `unitless`, and fixed legend range `[0, 1]`
  - `K` uses `plasma`, units `t*ha*h/(ha*MJ*mm)`, and current fixed range
    `[0, 0.7]` pending future validation updates
- raster NoData behavior in `gl-dashboard` is transparent; NoData and
  non-finite cells render with `alpha = 0` so they do not mask valid outputs
- raster tooltips use the standard raster pattern (layer path plus
  sampled pixel value) with no custom one-off tooltip contract

### Preflight and Staleness Contract

- `Rusle` integrates with the preflight system as its own checklist item
- a dedicated `TaskEnum` entry exists for the main `Rusle` build and uses the
  `🔱` emoji in TOC/preflight surfaces
- initial stale/invalidating events include:
  - climate rebuild
  - SBS map removal
  - SBS map replacement or modification
- stale `Rusle` state clears its preflight-complete indicator until the
  user rebuilds

### Failure UX Contract

- follows the existing control pattern for asynchronous failures:
  - concise status message in the control
  - stacktrace/details panel for deeper error information
  - no custom one-off error presentation for `Rusle`

### Inputs Explicitly Out of Scope for v1 UI

- `m_regime`
- NRCS benchmark/reference `K` modes
- explicit `cfvo` coarse-fragment adjustment controls
- raw `POLARIS` property/statistic/depth selection controls
- custom `scenario_sbs` lookup-table editing inside the `Rusle` panel

## Source Precedence

Recommended initial precedence:

- `LS`
  - purpose-built WBT `RusleLsFactor`
- `R`
  - current shipped mode: `cligen_static` from the run WEPP climate file when
    the goal is to approximate the erosivity used by WEPP
  - additional mode: `canonical_rusle2` from the vendored official
    RUSLE2 climate zones and climate records when the goal is the canonical
    official planning-climatology baseline
  - additional mode: `momm2025_county_region` from the vendored CONUS
    county or `REGION` monthly climatology when the goal is a published RUSLE2
    planning-climatology reference
  - no external gridded runtime source should be implied until the
    split-county `REGION` spatialization contract is explicitly resolved
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
- `canonical_rusle2` centroid-selection and `REC_LINK` provenance tests if
  that mode is enabled
- explicit canonical table-only acceptance or rejection tests for unsupported
  official rows
- `momm2025` county-selection and multi-county aggregation tests if that mode
  is enabled
- explicit split-county `REGION` acceptance or rejection tests for the public
  Momm 2025 mode
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
- `cfvo`-adjusted versus fine-earth `POLARIS` `K` comparison where the profile
  rock-fragment option is enabled

Longer term, the mod should be checked against:

- post-fire erosion monitoring plots
- sediment fence or trap datasets
- independent erosivity references where appropriate
- known disturbed hillslope inventories

## Resolved Open Questions

- The preferred initial `C` formula for `observed_rap` is the simplified
  `RUSLE2` surface-cover form `C = exp(-0.04 * fg)` where
  `fg = clamp(100 - bare_ground_pct, 0, 100)`.
- `scenario_sbs` supports static low/moderate/high severity lookups in
  v1, with no time axis until recovery trajectories are defined and validated.
- `scenario_sbs` is restricted to disturbed runs and keyed by canonical
  `disturbed_class` family plus `sbs_class`, not generic `landuse_class`.

### Resolved Implementation Choices

- `LS` uses a handbook-based default `max_slope_length_m = 304.8`
- DEM input is assumed hydrologically sound; `RusleLsFactor` fails fast
  rather than condition DEMs internally
- Stop-mask routing semantics are fixed: terminal sinks, no renormalization of
  terminated multi-flow fractions
- `R` static-`cligen` storm energy uses the WEPP/AH537-aligned SI convention:
  `e(i) = min(0.119 + 0.0873*log10(i_mm_hr), 0.283)` with `e = 0` for `i <= 0`
- Shared hyetograph API surface is dual-layer: segment builders plus
  peak-intensity helpers, with peak helpers as canonical WEPPpy callsite
  surface
- Breakpoint climate artifact compatibility is fixed: real `peak_intensity_*`
  values, nullable `tp/ip`, derived breakpoint `dur`, and no sentinel `-1`
  intensities
- Initial `observed_rap` `C` uses the simplified `RUSLE2` surface-cover form
  `C = exp(-0.04 * fg)` with `fg = clamp(100 - bare_ground_pct, 0, 100)` and
  neutral canopy/roughness/biomass/consolidation terms in v1
- `scenario_sbs` v1 uses static severity lookups only; no time axis until a
  separate recovery-trajectory path is defined and validated
- `scenario_sbs` is restricted to disturbed runs and uses canonical
  `disturbed_class` family plus `sbs_class` as its lookup key
- `scenario_sbs` requires a DEM-aligned gridded `disturbed_class` raster and
  only applies SBS burn remapping to canonical `forest`, `shrub`, and
  `tall_grass` families
- user-facing `scenario_sbs` remains available when no SBS map is present;
  that case must use explicit `unburned` parameters everywhere rather than
  failing or silently changing modes
- `Rusle` retrieves single-year RAP internally for `observed_rap` and does not
  depend on the `rap` or `rap_ts` NoDb mods
- enabling `rusle` from the UI auto-adds `polaris` when needed
- first-release `Rusle` UI eligibility is keyed to the presence of the
  `disturbed` mod
- enabling `rusle` reveals/registers the workflow but does not trigger
  a build automatically
- default first-release user selection remains `c_mode = observed_rap`
- `scenario_sbs` remains independent of optional Disturbed runtime burn
  toggles and uses the fixed canonical RUSLE disturbed-family policy
- `Rusle` passes an explicit `Polaris` acquisition payload even if the
  underlying `Polaris` defaults match the same layer set
- valid `observed_rap` year choices are sourced from the RAP
  implementation surface used by `rap.py`, with latest available completed year
  as the default when the user has not saved an override
- standard user-facing builds emit only selected active-mode outputs, so
  inactive estimator rasters are not surfaced by default
- the `Rusle` control appears after `WEPP` on the run page
- `Rusle` builds run through RQ
- `Rusle` integrates with preflight using a dedicated `TaskEnum` entry
  and `🔱` emoji
- initial `Rusle` staleness invalidators are climate rebuild plus SBS removal or
  change
- user-facing artifacts prefer mode-specific filenames
- `scenario_sbs` without an SBS map does not emit a synthetic all-unburned
  `sbs_4class.tif` artifact by default
- `Rusle` failure UX follows the standard status-plus-stacktrace control
  pattern
- `gl-dashboard` exposes run-scoped `RUSLE` `A/C/K` rasters in a dedicated
  section after `WEPP`, using factor-specific colormaps (`A=jet2`,
  `C=viridis`, `K=plasma`)
- `gl-dashboard` `RUSLE` `A` legends auto-range from the active raster's
  finite values, while `C` and `K` use fixed validated ranges
- `gl-dashboard` raster NoData cells render transparent for `RUSLE`
  overlays

## Initial Milestones

Status update (2026-03-21):

- Milestone 1 completed in
  `docs/work-packages/20260320_rusle_ls_factor_wbt/`.
- Milestones 2-3 completed in
  `docs/work-packages/20260320_rusle_r_static_hyetograph_api/`.
- Milestone 4 completed in
  `docs/work-packages/20260321_rusle_k_polaris_implementation/`.
- Milestone 5 completed in
  `docs/work-packages/20260321_rusle_c_modes_implementation/`.
- Milestones 6-7 completed in
  `docs/work-packages/20260321_rusle_nodb_ui/`.

1. Created the WBT `RusleLsFactor` tool with `Desmet-Govers` `L`,
   `McCool/RUSLE` `S`, `DInf` default routing, and diagnostic outputs; then
   validated outputs on representative disturbed terrain.
2. Added a reusable Rust WEPP hyetograph reconstruction helper to
   `wepppyo3.climate` and validated it against existing Python behavior where
   comparable.
3. Implemented a `wepppyo3.climate` static-`R` routine from WEPP `.cli` inputs
   using that helper, with no production Python fallback.
4. Extended Polaris acquisition for `polaris_nomograph` and `polaris_epic`,
   starting with the nomograph-facing path, paired NRCS `K` benchmark
   support, and optional aligned SoilGrids `cfvo` support for profile-
   fragment adjustment.
5. Defined the shared `C` engine and the two source modes.
6. Implemented the `Rusle` NoDb controller and run-scoped artifact layout.
7. Added validation runs using `disturbed9002_wbt`-style workflows.

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
- Momm, H. G., McGehee, R. P., and coauthors, 2025.
  *Isoerodent surfaces of the continental US for conservation planning with the
  RUSLE2 water erosion model*. *Catena*, 249, 108879.
  https://doi.org/10.1016/j.catena.2025.108879
  Primary reference for the planned `momm2025` mode: monthly CONUS RUSLE2
  isoerodent update with reproducible interpolation workflow and smoother
  operational surfaces.
- USDA ARS Agricultural Data Commons. *Data from: Isoerodent surfaces of the
  continental US for conservation planning with the RUSLE2 water erosion
  model*.
  https://doi.org/10.15482/USDA.ADC/28821569.v1
  Public dataset reference for the vendored `momm2025` Parquet and GeoParquet
  inputs used in this repo.
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
- ISRIC. *SoilGrids FAQs*.
  https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html
  Primary reference for SoilGrids property semantics and standard depth layers.
  Note: the current `cfvo` row is internally ambiguous (`cm^3/dm^3 (vol‰)` is
  listed with conversion factor `100`), so conversion assumptions should be
  cross-checked against live service metadata.
- ISRIC. *SoilGrids `cfvo` WMS capabilities*.
  https://maps.isric.org/mapserv?map=/map/cfvo.map&SERVICE=WMS&REQUEST=GetCapabilities
  Live metadata reference used to verify `cfvo` layer naming and volumetric
  unit semantics (`cm^3/dm^3` / `vol‰`).
- ISRIC. *FAQ - WoSIS*.
  https://docs.isric.org/globaldata/wosis/faq-wosis.html
  Official definition reference for `CFVO` as volumetric coarse fragments in
  the whole soil.
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
- USDA-NRCS. *National Range and Pasture Handbook, Chapter 7: Rangeland and
  Pastureland Hydrology and Erosion*.
  https://www.nrcs.usda.gov/sites/default/files/2022-09/Chapter%207%20-%20Grazing%20Lands%20Hydrology.pdf
  Useful NRCS synthesis for why litter, vegetation, and exposed interspace are
  first-order controls on runoff and erosion in rangeland settings.
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
- During implementation, each factor builder should record its exact data
  source, version, retrieval date, and any local transformations in
  `rusle/manifest.json`.
