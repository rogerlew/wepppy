# RUSLE NoDb Mod

> Gridded RUSLE (Revised Universal Soil Loss Equation) implementation for
> WEPPcloud runs, producing spatially explicit long-term average hillslope
> sheet-and-rill detachment potential rasters from the classic
> `A = R * K * LS * C * P` equation.

> **See also:** [specification.md](specification.md) for the full design
> rationale, factor equations, locked method contracts, and scientific
> references.

## Overview

This mod replaces legacy heuristic gridded erosion visualizations with a
product that is more explicit, more citable, and more academically defensible.
It is treated as a visualization and prioritization layer, not as a regulatory
estimate or a substitute for calibrated hillslope modeling.

The initial target configuration is `disturbed9002_wbt`. The mod requires the
WBT (WhiteboxTools) delineation backend; TOPAZ runs are not supported. Uses
US-only datasets (POLARIS for K; RAP for `observed_rap` C mode only).

Key characteristics:

- Spatially gridded outputs aligned to the run DEM
- Run-constant scalar `R` factor sourced by explicit `r_mode`:
  `cligen_static`, `momm2025_county_region`, or `canonical_rusle2`
- POLARIS-derived soil erodibility (K) with nomograph and EPIC estimators
- Two C-factor modes: observed RAP fractional cover and scenario-based
  disturbed/SBS lookup
- Masking scope varies by factor — see [Spatial Masking](#spatial-masking)

### What this mod is not

- Not event-based detachment modeling
- Not sediment delivery to channels or outlets
- Not net erosion-deposition modeling
- Not channel or gully erosion
- Not a full clone of RUSLE2

See [specification.md § Non-Goals](specification.md#non-goals) for the full
boundary statement.

## Workflow

A RUSLE build orchestrates five factor computations and assembles the final
`A` raster. The `Rusle` controller (`rusle.py`) coordinates the entire
pipeline:

1. **R** — Parse the run WEPP climate file, compute a scalar mean annual R
   via `cli_calculate_static_r` (`cligen_static`) or select a scalar planning
   climatology R from the vendored Momm 2025 county dataset or canonical
   official RUSLE2 polygon dataset; broadcast as `rusle/r.tif`
2. **LS** — Invoke the WBT `RusleLsFactor` tool on the conditioned DEM
   (prefers `dem/wbt/relief.tif`, falls back to `watershed.relief`), passing
   `netful` as the channel stop mask and a generated blocking mask for cells
   outside the watershed boundary, producing `ls.tif`, `l.tif`, `s.tif`,
   `sca.tif`, and `effective_slope_length.tif`
3. **K** — Load POLARIS near-surface soil layers, compute depth-weighted
   averages, and derive K rasters via one or both estimators
   (`k_polaris_nomograph.tif`, `k_polaris_epic.tif`)
4. **C** — Compute cover-management factor from either observed RAP bare
   ground (`observed_rap`) or disturbed-family/SBS lookup (`scenario_sbs`)
5. **P** — Write a constant support-practice raster (default `P = 1.0`)
6. **A** — Multiply `R * K * LS * C * P` cell-by-cell into the final
   mode-specific output

All artifacts are written under `<wd>/rusle/` with machine-readable
provenance in `rusle/manifest.json` and a human-readable `rusle/README.md`
per build.

## Components

### Factor Modules

| Module | Factor | Description |
|--------|--------|-------------|
| [ls_integration.py](ls_integration.py) | LS | WBT `RusleLsFactor` runner; Desmet-Govers L, McCool/RUSLE S |
| [k_integration.py](k_integration.py) | K | POLARIS nomograph and EPIC estimators with optional benchmark harness |
| [k_nomograph.py](k_nomograph.py) | K | Nomograph-style K from sand/silt/clay/OM/Ksat |
| [k_epic.py](k_epic.py) | K | Williams (1995) EPIC K from texture and organic carbon |
| [k_compare.py](k_compare.py) | K | Benchmark comparison against reference K sources |
| [k_reference.py](k_reference.py) | K | Reference point sampling for K validation |
| [k_manifest.py](k_manifest.py) | K | Manifest writing for K artifacts |
| [c_integration.py](c_integration.py) | C | `observed_rap` and `scenario_sbs` C-factor runners |
| [c_formula.py](c_formula.py) | C | Shared math: `C = exp(-b * fg)` |
| [c_lookup.py](c_lookup.py) | C | Static lookup table for `scenario_sbs` mode |
| [c_manifest.py](c_manifest.py) | C | Manifest writing for C artifacts |

### Controller

[rusle.py](rusle.py) — The `Rusle` NoDb controller facade. Orchestrates
end-to-end builds, manages configuration state, and writes final `A` rasters
and provenance artifacts.

### Data

| File | Purpose |
|------|---------|
| [data/rusle_c_lookup.csv](data/rusle_c_lookup.csv) | Static C-factor lookup for `scenario_sbs` mode, keyed by disturbed family and SBS class |

### Reference Documents

[docs/](docs/) — Local cache of primary open PDFs used by the specification.
See [docs/README.md](docs/README.md) for the full inventory.

## Key Concepts

### R-Factor Modes

Rainfall erosivity (`R`) is a long-term annual erosivity index, not annual
precipitation, storm depth, or a design-storm intensity. In `USLE`/`RUSLE`/
`RUSLE2` science, `R` is built from storm `EI30`: storm kinetic energy times
maximum 30-minute intensity, summed by year and averaged over a climate
record. This mod currently materializes every supported `r_mode` as one
run-constant scalar broadcast into `rusle/r.tif`; select the mode by the
scientific question, not by which value is larger.

**`cligen_static`** (default) — Computes mean annual `R` from the run WEPP
`.cli` climate record using reconstructed WEPP hyetographs. This is the
recommended mode for normal WEPPcloud products, comparisons against WEPP
outputs, and disturbed-scenario maps where the question is "what does this
modeled run imply?" It is the most internally consistent choice because the
same generated climate record drives both WEPP and the RUSLE visualization.
Do not describe it as an official RUSLE2 planning climatology; it inherits the
run's CLIGEN station, scenario, and simulation-record choices.

**`canonical_rusle2`** — Selects the vendored official RUSLE2 climate database
and climate-zone polygon at the watershed centroid, then converts official
English-unit `R` to the SI units used by this mod. Prefer this mode when the
product needs NRCS/RUSLE2 planning comparability, official climate-zone
semantics, or a baseline that should be interpretable outside the WEPP run.
It is not a replay of the run's WEPP storm record, and v1 supports only
polygon-backed official records with deterministic centroid selection.

**`momm2025_county_region`** — Selects the published Momm et al. (2025)
monthly RUSLE2 erosivity climatology by watershed-centroid county, resolving
split-county `REGION` rows with localized annual precipitation. Prefer this
mode for CONUS planning and sensitivity checks where the desired reference is
the newer reproducible RUSLE2 isoerodent workflow rather than the legacy
official climate database or the run-specific WEPP climate. It is not a
sub-county gridded erosivity surface, does not cover Alaska or Hawaii, and can
still change abruptly at county or public `REGION` boundaries.

Opinionated selection rule:

- Start with `cligen_static` for run-specific WEPPcloud interpretation.
- Use `canonical_rusle2` when official RUSLE2 planning comparability matters
  more than matching the run's generated weather.
- Use `momm2025_county_region` for CONUS work when the purpose is an updated,
  published planning-climatology reference or a sensitivity comparison against
  `canonical_rusle2`.
- Do not substitute PRISM, NOAA Atlas 14, or a 30-minute design-storm raster
  for these long-term annual `R` modes. Those sources may be valid upstream
  climate inputs or separate event/design-storm products, but they are not the
  same contract as canonical annual `RUSLE R`.

See [specification.md § R](specification.md#r),
[data/rusle2/README.md](data/rusle2/README.md), and
[data/momm2025/README.md](data/momm2025/README.md) for the full scientific
basis, source data, and runtime selection contracts.

### C-Factor Modes

**`observed_rap`** (default) — Uses observed RAP (Rangeland Analysis Platform)
fractional cover for a selected year. Bare ground drives net ground cover
(`fg = clamp(100 - bare_ground_pct, 0, 100)`), and the C factor is computed
as `C = exp(-0.04 * fg)`. Supports `rock_fraction_of_rap_bare` to partition
RAP bare into exposed mineral soil versus protective surface rock. Best fit for
current condition, recent post-fire, and monitoring workflows.

**`scenario_sbs`** — Uses explicit lookup values keyed by canonical disturbed
family (forest, shrub, tall_grass) and SBS (Soil Burn Severity) class
(unburned, low, moderate, high). Restricted to runs with the Disturbed module
active. Supports `rock_fraction_of_sbs_bare` to partition lookup-derived bare
fraction into exposed mineral soil versus protective surface rock. Best fit for
counterfactual pre-fire/post-fire comparisons and planning mode.

#### Surface-Rock Partition Controls

These controls implement canonical `RUSLE2` treatment used by this mod:
surface rock fragments are a cover-management (`C`) effect, while profile
coarse fragments are handled in erodibility/permeability (`K`) logic.

- `rock_fraction_of_rap_bare`:
  fraction of RAP bare interpreted as protective surface rock (`[0,1]` or
  `auto`)
- `rock_fraction_of_sbs_bare`:
  fraction of lookup SBS bare interpreted as protective surface rock (`[0,1]`
  or `auto`)

`observed_rap` equations:

- `bare_rap_0_1 = clamp(bare_ground_pct / 100, 0, 1)`
- `r_bare = clamp(rock_fraction_of_rap_bare, 0, 1)`
- `bare_exposed = bare_rap_0_1 * (1 - r_bare)`
- `fg = 100 * (1 - bare_exposed)`
- `C = exp(-0.04 * fg)`

`scenario_sbs` equations:

- `fg_lookup_0_1 = clamp(fg_lookup_pct / 100, 0, 1)`
- `bare_lookup_0_1 = 1 - fg_lookup_0_1`
- `r_sbs_bare = clamp(rock_fraction_of_sbs_bare, 0, 1)`
- `bare_exposed = bare_lookup_0_1 * (1 - r_sbs_bare)`
- `fg_effective_pct = 100 * (1 - bare_exposed)`
- `C = exp(-0.04 * fg_effective_pct)`

`auto` data-source precedence and normalization for both controls:

- primary proxy: run-scoped SSURGO surface-fragment fields in
  `soils/soils.parquet` (`cosurffrags_cover_pct`, `surface_rock_cover_pct`,
  `surface_rock_cover_percent`, `sfragcov`), area-weighted mean when `area` is
  available
- fallback proxy: aligned top-horizon coarse-fragment raster
  (`polaris/cfvo_mean_0_5.tif` or `soils/cfvo_0-5cm_Q0.5.tif`)
- final fallback: `0.0`
- convert proxy total-surface cover into fraction-of-bare control space:
  - RAP control: `clamp(surface_rock_cover_proxy_0_1 / bare_rap_mean_0_1, 0, 1)`
  - SBS control: `clamp(surface_rock_cover_proxy_0_1 / bare_lookup_mean_0_1, 0, 1)`

Operational guidance:

- `auto` is a proxy prior, not field truth
- users should verify local surface rock cover and set these fractions
  accordingly
- when uncertain, run sensitivity checks (`0.0`, `auto`, field-informed value)

See [specification.md § C](specification.md#c) for the full formula
derivation, static matrix values, and non-burnable class policy.

### K-Factor Modes

**`polaris_nomograph`** (default) — Nomograph-like RUSLE-facing emulation
using POLARIS sand, silt, clay, OM, and Ksat. Very fine sand is estimated via
the RUSLE2 User Reference Guide fallback equation. Closest to canonical
NRCS K semantics. When run-scoped `cfvo` depth layers are available, this mode
also applies a conservative profile-fragment permeability-class adjustment
(`cfvo <25%`: no shift, `25-<60%`: +1 class, `>=60%`: +2 classes; clamped to
class `6`).

**`polaris_epic`** — Williams (1995) EPIC alternative using only texture and
organic carbon. Lower input burden but less directly comparable to NRCS K.
Best fit as a sensitivity or reproducibility path.

See [specification.md § K](specification.md#k) for locked assumptions,
rock-fragment handling, and comparison guidance.

`cfvo` layer discovery is run-scoped and optional:

- reuse aligned `polaris/cfvo_mean_0_5.tif` and `polaris/cfvo_mean_5_15.tif`
  when present;
- otherwise, if `soils/cfvo_0-5cm_Q0.5.tif` and
  `soils/cfvo_5-15cm_Q0.5.tif` exist, align them to the POLARIS grid and stage
  aligned copies under `polaris/`;
- otherwise, skip `cfvo` adjustment and record explicit `not_applied` metadata.

POLARIS nodata handling for `K` uses a conservative two-stage interior-hole
fill before near-surface aggregation:

- stage-1 fills interior components `1-64` px (`<=10%` candidate fraction,
  search distance `6` px)
- stage-2 fills residual interior components `65-4096` px (`<=5%` candidate
  fraction, search distance `12` px)
- edge-connected and oversized gaps remain nodata by design
- policy and per-property outcomes are recorded in `rusle/manifest.json`
  (`k.gap_fill_policy`, `k.gap_fill_summary`)

### POLARIS Soil Layers

The mod automatically acquires POLARIS near-surface soil property rasters
(sand, silt, clay, OM, bulk density, Ksat) at depths 0-5 cm and 5-15 cm,
with thickness-weighted averaging to a single near-surface value. The
internal `Polaris` NoDb controller handles retrieval, alignment, and
caching.

### Spatial Masking

Masking behavior varies by factor and C mode in the current implementation:

- **LS** — The `channel_mask` (`netful`) is passed as a stop mask to WBT
  `RusleLsFactor`, terminating slope-length growth at channel cells. The
  controller does not auto-generate an outside-watershed blocking mask; LS
  applies across the full conditioned DEM/map extent by default unless an
  explicit blocking mask is supplied by caller wiring.
- **C (`observed_rap`)** — No NLCD-family masking is applied; validity is
  determined by RAP-band finite-value masks after DEM alignment.
- **C (`scenario_sbs`)** — NLCD-family masking is applied via the disturbed
  class mapping: water, developed, and wetland families produce `C = nodata`.
- **A** — Cells where any input factor is `NaN`/nodata produce `A = NaN`.

The specification defines a broader masking contract (NLCD water `11`,
developed `21-24`, wetlands `90`/`95`, channel mask, optional blocking mask,
optional user masks) that is not yet fully wired into all factor paths. See
[specification.md § Spatial Masking Rules](specification.md#spatial-masking-rules)
for the full design rationale, including the wetland masking decision.

## Configuration

The `Rusle` controller reads its configuration from the run `.cfg` file under
the `[rusle]` section:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `r_mode` | `cligen_static` | R-factor source: `cligen_static`, `momm2025_county_region`, or `canonical_rusle2` |
| `c_mode` | `observed_rap` | C-factor source: `observed_rap` or `scenario_sbs` |
| `rap_year` | latest available | RAP observation year for `observed_rap` mode |
| `rock_fraction_of_rap_bare` | `auto` | Fraction of RAP bare treated as protective surface rock (`[0,1]` or `auto`) |
| `rock_fraction_of_sbs_bare` | `auto` | Fraction of scenario SBS bare treated as protective surface rock (`[0,1]` or `auto`, used in `scenario_sbs`) |
| `k_modes` | `polaris_nomograph` | Comma-separated K estimators to compute |
| `default_k_mode` | first in `k_modes` | Which K raster feeds the final A product |
| `max_slope_length_m` | `304.8` | LS effective slope-length cap in meters (1000 ft handbook basis); override only for explicit sensitivity analysis |
| `p_value` | `1.0` | Constant support-practice factor |

See [specification.md § Config Direction](specification.md#config-direction)
for the full config surface including advanced LS controls.

## Build Artifacts

A standard build writes mode-specific artifacts under `<wd>/rusle/`:

**Shared outputs:**
`r.tif`, `ls.tif`, `l.tif`, `s.tif`, `sca.tif`, `effective_slope_length.tif`,
`p.tif`, `manifest.json`, `README.md`

**Mode-specific outputs:**
`c_observed_rap.tif` or `c_scenario_sbs.tif`,
`a_<c_mode>_<default_k_mode>.tif`,
`k_polaris_nomograph.tif` and/or `k_polaris_epic.tif`

**Mode-support artifacts:**
`c_fg.tif` (observed_rap), `disturbed_class.tif` (scenario_sbs),
`c_lookup_used.csv` (scenario_sbs), optional `sbs_4class.tif`

Factor rasters are single-band GeoTIFF on the DEM-aligned grid. Controller-
generated factor products use `float32` with nodata `-9999.0`. Classification
artifacts (`disturbed_class.tif`, `sbs_4class.tif`) use `uint8` with nodata
`0` or `255` respectively.

## Integration Points

- **Depends on**: `Ron`, `Watershed`, `Climate`, `Landuse`, `Disturbed`, `Polaris`
- **External tools**: WBT `RusleLsFactor` (Rust, in `/workdir/weppcloud-wbt`),
  `wepppyo3.climate.compute_static_r_from_cli` (Rust PyO3)
- **Data sources**: POLARIS soil grids, RAP fractional cover, NLCD landcover
- **Used by**: gl-dashboard raster overlays, preflight system, query-engine catalog
- **RQ tasks**: Build is enqueued as an RQ job rather than running inline

## Persistence

- **Filename**: `rusle.nodb`
- **Redis cache**: DB 13, 72-hour TTL
- **Locking**: Required for all mutations (standard NoDb pattern)
- **Provenance**: `rusle/manifest.json` is the canonical machine-readable record

## Further Reading

- [specification.md](specification.md) — Full design specification, method
  contracts, and scientific references
- [docs/pdfs/rusle2_handbook.pdf](docs/pdfs/rusle2_handbook.pdf) — Canonical
  RUSLE2 handbook guidance used for surface-rock-in-`C` and profile-fragment-in-`K`
  separation
- [docs/pdfs/rusle2_user_reference_guide.pdf](docs/pdfs/rusle2_user_reference_guide.pdf) —
  RUSLE2 user-reference equations and implementation guidance informing
  the cover-management mapping
- [docs/](docs/) — Reference PDF bundle
- [../../README.md](../../README.md) — NoDb framework documentation
- [../disturbed/README.md](../disturbed/README.md) — Disturbed module
  (provides SBS and management context)
- [../polaris/](../polaris/) — POLARIS NoDb substrate
