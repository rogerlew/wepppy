# Deciduous and Mixed Forest Management Types

**Status**: Implemented; targeted QA passed. Authored by Claude Code 2026-06-26.
**Timezone**: UTC
**Requires ADR**: yes (parameterization change — `ADR-0002`).

## Overview

WEPPcloud currently models **all three NLCD forest classes with one
management file**. In `wepppy/wepp/management/data/disturbed.json`, keys
`41` (Deciduous Forest), `42` (Evergreen Forest), and `43` (Mixed Forest) all
resolve to `UnDisturbed/Old_Forest.man` — a static evergreen Tahoe-conifer
perennial (`Tah_4899`, "With no Senescence or decomposition", all phenology
dates `0`). The canopy therefore never drops, so deciduous and mixed forest are
simulated with a **persistent winter canopy** they do not physically have.

This package creates and installs **distinct deciduous and mixed forest
management types** whose defining difference from the evergreen baseline is
their **seasonal (leaf-off) canopy phenology**, parameterized from cited
scientific authority and recorded in a parameterization ADR.

### Why this matters now (cross-repo driver)

The openWEPP melt-modernization program (SNOWDENSITY-05E→05G,
`snow-frost-fidelity-strategy.md`) found that the WEPP Corps-of-Engineers
snowmelt energy balance attenuates radiation and turbulent melt by canopy cover:
`amelt = 0.0607·hrad·(1-cancov)`, `cmelt = 0.0188·U·(1-0.8·cancov)·…`. The
SNOWDENSITY-05G representative rerun showed that at a realistic evergreen
`cancov ≈ 0.9` the radiation term is ~90% attenuated, so canopy structure is a
**first-order control on modeled snowmelt and snow-season insulation**. The
deciduous/mixed regime — low, seasonal winter `cancov` (~0.1–0.4) — is exactly
where canopy and the modernized melt physics behave differently, and it is
currently un-representable because every forest is evergreen. Producing
physically distinct winter-canopy trajectories here is the prerequisite for the
mixed-forest snow fixtures that program needs (Marcell EF, Harvard Forest,
Hubbard Brook, Sleepers River).

This is a **wepppy-scoped** package. It does not modify openWEPP; it provides the
managements those fixtures will select.

## Objectives

1. Author two new WEPP management files under
   `wepppy/wepp/management/data/UnDisturbed/`:
   - `Deciduous_Forest.man` — seasonal leaf-on/leaf-off northern-hardwood canopy.
   - `Mixed_Forest.man` — intermediate canopy blending evergreen retention and
     deciduous leaf-off.
2. Install them in `wepppy/wepp/management/data/disturbed.json` so NLCD `41`
   maps to deciduous and `43` to mixed, while `42` remains evergreen.
3. Determine and document whether
   `wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv` requires new
   rows / plant-override values for the new classes (it carries the
   `xmxlai`, `plant.data.decfct`, `plant.data.dropfc`, `rdmax`, `pmet_kcb`
   canopy/plant override columns).
4. Ground every non-trivial parameter in cited scientific authority
   (research artifact) and record the decision in a parameterization ADR.
5. Verify the new managements produce the **intended winter (snow-season)
   canopy-cover trajectory** — low for deciduous, intermediate for mixed, high
   for evergreen.

## Scope

### Included

- New `Deciduous_Forest.man` and `Mixed_Forest.man` in `UnDisturbed/`, authored
  to the WEPP 98.4 management format and parseable by
  `wepppy.wepp.management.read_management`.
- `disturbed.json` remap of keys `41`/`43` (and review of the `young forest`
  classes `44`/`61` and the wetland/woody classes for consistency), with
  `DisturbedClass` values assigned coherently with the lookup `luse` column.
- A determination (with evidence) on `disturbed_land_soil_lookup.csv`: which
  rows/columns the new classes need, distinguishing **soil-hydraulic** params
  (`ki`, `kr`, `shcrit`, `avke`, `ksatadj`, `ksatfac`, …) — which may legitimately
  remain shared "forest" values — from **plant-canopy** overrides (`xmxlai`,
  `plant.data.decfct`, `plant.data.dropfc`, `rdmax`, `pmet_kcb`) — which should
  differ by canopy phenology.
- A research/parameterization-justification artifact (authority + values).
- A parameterization ADR under `docs/adrs/` (`ADR-0009`).
- Regression coverage that the new managements parse, build valid WEPP inputs,
  and round-trip through the disturbed lookup/override path.

### Excluded

- No openWEPP changes (the snow/melt consumer is a separate repo/program).
- No new soil files unless the determination in Objective 3 requires them.
- No change to the evergreen `Old_Forest.man` physics beyond optional renaming /
  documentation for clarity (if renamed, update all `disturbed.json` references).
- No fire/thinning/disturbance forest variants (out of scope here).
- No calibration to specific observation sites — parameters are
  literature-defensible defaults, not site fits.

## Parameterization Requirements

The three forest types must be **physically distinct in their canopy phenology**,
which is what the downstream snow/melt and interception physics consume. Map each
target to the exact WEPP plant/management parameters (see "Parameter mapping"
below) and justify the value against authority.

### Evergreen (baseline — `Old_Forest.man`, `Tah_4899`)
- Persistent, near-constant canopy all year; **winter cancov high (~0.85–0.95)**.
- High max LAI (lookup `xmxlai = 14`), no senescence, no leaf drop.
- Keep as the class-`42` reference; clarify naming/comments only.

### Deciduous (`Deciduous_Forest.man`) — target behavior
- **Strong seasonal canopy cycle**: spring leaf-out, full summer canopy, autumn
  leaf-off, **bare-to-low winter canopy (winter cancov ~0.1–0.3, stems/branches
  only)**.
- Lower peak LAI than old-growth conifer (northern hardwood peak LAI commonly
  ~3–6; confirm and cite).
- Real **senescence / leaf-drop** in autumn and **growth-start (leaf-out)** in
  spring — the WEPP phenology dates that are `0` in `Old_Forest.man` must be set.
- Litter **decomposition** of dropped foliage represented (`decfct`/`dropfc`).

### Mixed (`Mixed_Forest.man`) — target behavior
- **Intermediate**: partial evergreen retention + partial deciduous leaf-off, so
  **winter cancov intermediate (~0.4–0.6)** and a damped seasonal LAI swing.
- Decide and document the representation: a single perennial with intermediate
  LAI seasonality and a partial leaf-drop fraction is the simplest defensible
  approach; justify the conifer:deciduous blend assumption (e.g., ~50/50) against
  NLCD's mixed-forest definition (neither type >75%).

### Parameter mapping (Codex must resolve precisely)
Do **not** guess parameter positions. Map each target to the WEPP plant/management
parameters by reading the authoritative parser and WEPP plant documentation, then
justify values:
- Parser/authority: `wepppy.wepp.management.read_management` and the WEPP plant
  parameter definitions (WEPP User Summary / NSERL plant database / `plant.for`).
- Likely-relevant levers (confirm names/positions): maximum LAI (`xmxlai`/
  `tmxlai`), canopy-cover coefficient driving `cancov = 1 - exp(-bb·biomass)`,
  the Yearly-section **senescence / perennial-growth-start / stop-growth dates**
  (lines that are `0` in `Old_Forest.man`), leaf-drop fraction and decomposition
  (`plant.data.dropfc` / `plant.data.decfct`), canopy height, and root depth
  (`rdmax`).
- The wepppy canopy override path also scales canopy via
  `wepp_prep_service.py` (`plant_data.ln *= cancov_override`) and
  `management_overrides.resolve_disturbed_scalar_replacements`
  (`rdmax`/`ln`, `plant.data.*`). Document how the new managements interact with
  this path so a downstream `cancov_override` composes correctly.

### Validation target (the snow-relevant output)
For each of the three managements, **verify the per-day canopy-cover trajectory
across a full year** (e.g., via a single-OFE WEPP run or the management/plant
growth output) and confirm:
- evergreen winter cancov high and ~flat,
- deciduous winter cancov low with a clear leaf-off drop and spring recovery,
- mixed winter cancov intermediate.
This is the acceptance evidence that the parameterization achieves its physical
purpose, and it is what the openWEPP melt work consumes. Report the winter-month
mean cancov for each type.

## Integration Points

1. **`UnDisturbed/*.man`** — add `Deciduous_Forest.man`, `Mixed_Forest.man`.
   (`dump_to_json.py` writes per-management `*.man.json`; regenerate if that
   sidecar convention is in use.)
2. **`disturbed.json`** — remap key `41` → `UnDisturbed/Deciduous_Forest.man`
   (`DisturbedClass: "deciduous forest"`), key `43` →
   `UnDisturbed/Mixed_Forest.man` (`DisturbedClass: "mixed forest"`); leave `42`
   evergreen. Keep valid JSON; verify no other consumer hard-codes the old
   mapping.
3. **`disturbed_land_soil_lookup.csv`** — the lookup keys on `(luse, stext)` and
   `luse` must match the JSON `DisturbedClass`. If new `DisturbedClass` values
   are introduced, the lookup **needs matching rows** for each soil texture, or
   the prep/override path will fall back or fail. Determine whether deciduous/
   mixed share the existing `forest` soil-hydraulic values (likely yes — same
   soil, different canopy) but receive **distinct plant-canopy overrides**
   (`xmxlai`, `dropfc`, `decfct`, possibly `rdmax`/`pmet_kcb`). Trace the
   consumer (`wepppy/nodb/core/wepp_prep_service.py`,
   `wepppy/nodb/core/management_overrides.py`,
   `wepppy/nodb/mods/disturbed/`) and document the exact rows added or the
   justification for sharing.

## Scientific Research Mandate

Parameter values must be **defensible from cited authority**, not invented.
Produce `artifacts/parameterization-research.md` capturing sources and the
justification for every non-default value. Required evidence base:
- **WEPP plant-parameter semantics**: WEPP User Summary / NSERL plant database /
  `plant.for` — the authoritative definition of each parameter changed.
- **FS-WEPP / Disturbed-WEPP forest lineage**: the W. Elliot / Robichaud
  parameterization the existing `.man` files derive from (authorship stamps are
  "W. Elliot 05/10"); align with that convention and cite it.
- **Deciduous vs conifer phenology and LAI**: leaf-out/leaf-off timing and
  seasonal LAI for northern hardwood vs conifer — peer-reviewed forest ecology /
  remote-sensing phenology (e.g., USA-NPN, MODIS LAI/phenology), with values for
  the canopy-cover seasonal cycle.
- **Canopy–snow interaction authority** (shared with the openWEPP references):
  Lundquist et al. 2013 (the ~1 °C DJF net-canopy sign-flip), Varhola et al. 2010
  (canopy effects on accumulation/ablation). These motivate *why* the winter
  canopy distinction matters and bound plausible cover values.
- Conform to `docs/standards/parameterization-adr-standard.md`.

## ADR Requirement

Per `ADR-0002` (parameterization changes require an ADR), author
`docs/adrs/ADR-0009-deciduous-mixed-forest-managements.md`
recording: the decision to differentiate deciduous/mixed/evergreen forest
managements; the parameter changes and their cited basis; the
`disturbed_land_soil_lookup.csv` determination; the winter-cancov validation
evidence; and backward-compatibility / regression notes (existing projects that
selected forest classes will now resolve deciduous/mixed differently — state the
impact). Follow `docs/standards/parameterization-adr-standard.md`.

## Acceptance Gates

- Both new `.man` files parse via `wepppy.wepp.management.read_management` and
  build valid WEPP inputs in a single-hillslope run.
- `disturbed.json` is valid JSON; `41`/`43`/`42` resolve to deciduous/mixed/
  evergreen respectively; no consumer regresses.
- The `disturbed_land_soil_lookup.csv` determination is implemented (rows added)
  or explicitly justified (shared), and the override path
  (`wepp_prep_service` / `management_overrides`) resolves the new classes without
  fallback error.
- **Winter-cancov validation**: documented per-day/winter-mean canopy trajectory
  for all three types showing the intended low/intermediate/high ordering.
- `artifacts/parameterization-research.md` present with cited authority for every
  non-default parameter.
- Parameterization ADR authored and conformant to the standard.
- Repo test/QA gates pass; regression coverage added for the new classes.

## Deliverables

- `wepppy/wepp/management/data/UnDisturbed/Deciduous_Forest.man`
- `wepppy/wepp/management/data/UnDisturbed/Mixed_Forest.man`
- Updated `wepppy/wepp/management/data/disturbed.json`
- Updated/justified `wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv`
- `docs/adrs/ADR-00NN-deciduous-mixed-forest-managements.md`
- `artifacts/parameterization-research.md` (sources + value justification)
- `artifacts/winter-cancov-validation.md` (the trajectory evidence)
- Tests/regression coverage

## Cross-Repo Coordination Note

The winter-cancov targets here are the inputs the openWEPP melt program validates
against (mixed-forest snow fixtures: Marcell, Harvard Forest, Hubbard Brook,
Sleepers River). Keep the deciduous/mixed winter-cancov values and the
phenology window consistent with what those fixtures will assume; surface the
chosen winter-mean cancov per type so the openWEPP side can align its
`cancov`-driven melt validation. Coordination only — no openWEPP code changes in
this package.
