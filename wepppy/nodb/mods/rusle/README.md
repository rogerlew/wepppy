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

### C-Factor Modes

**`observed_rap`** (default) — Uses observed RAP (Rangeland Analysis Platform)
fractional cover for a selected year. Bare ground drives net ground cover
(`fg = clamp(100 - bare_ground_pct, 0, 100)`), and the C factor is computed
as `C = exp(-0.04 * fg)`. Best fit for current condition, recent post-fire,
and monitoring workflows.

**`scenario_sbs`** — Uses explicit lookup values keyed by canonical disturbed
family (forest, shrub, tall_grass) and SBS (Soil Burn Severity) class
(unburned, low, moderate, high). Restricted to runs with the Disturbed module
active. Best fit for counterfactual pre-fire/post-fire comparisons and
planning mode.

See [specification.md § C](specification.md#c) for the full formula
derivation, static matrix values, and non-burnable class policy.

### K-Factor Modes

**`polaris_nomograph`** (default) — Nomograph-like RUSLE-facing emulation
using POLARIS sand, silt, clay, OM, and Ksat. Very fine sand is estimated via
the RUSLE2 User Reference Guide fallback equation. Closest to canonical
NRCS K semantics.

**`polaris_epic`** — Williams (1995) EPIC alternative using only texture and
organic carbon. Lower input burden but less directly comparable to NRCS K.
Best fit as a sensitivity or reproducibility path.

See [specification.md § K](specification.md#k) for locked assumptions,
rock-fragment handling, and comparison guidance.

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
  controller also passes a generated blocking mask that stops routing outside
  the watershed boundary. NLCD and user stop masks are not currently wired
  into the LS call.
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
- [docs/](docs/) — Reference PDF bundle
- [../../README.md](../../README.md) — NoDb framework documentation
- [../disturbed/README.md](../disturbed/README.md) — Disturbed module
  (provides SBS and management context)
- [../polaris/](../polaris/) — POLARIS NoDb substrate
