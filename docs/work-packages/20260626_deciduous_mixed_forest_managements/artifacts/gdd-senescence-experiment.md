# Experiment Note: Temperature-Driven (GDD/`dlai`) Leaf-Off

Status: completed negative investigation, 2026-06-26. Authored by Claude Code
2026-06-26, review phase; executed by Codex 2026-06-26.

Result: do **not** adopt GDD/`dlai` leaf-off for the shipped deciduous and mixed
forest managements. The fixed-date `jdharv=286` representation remains the
documented tradeoff.

## Why

The shipped deciduous/mixed managements trigger leaf-off with a **fixed Julian
senescence date** (`286`, ~Oct 13) and disable WEPP's heat-unit senescence
(`gddmax=0`). That meets the winter-cancov ordering target, but it is **not
climate-adaptive**: every site drops leaves on the same calendar day regardless
of elevation/climate, and it is Northern-Hemisphere-locked. Because the snow
fixtures this work feeds span Minnesota, Vermont, Colorado, and Appalachian
climates — where real leaf-off ranges from late September to early November — and
**leaf-off timing relative to snow onset is the snow-relevant signal**, a
temperature-driven leaf-off is the more faithful representation.

The hypothesis was that WEPP already supported this. Per `grow.for`:
`gdd = tave - btemp`, `sumgdd` accumulates, `fphu = sumgdd / gddmax`, and
senescence can begin when `fphu >= dlai`, after which canopy cover declines at a
derived `delcc` rate. Leaf-out already tracks spring warming via the `crit`
heat-unit emergence threshold, so the asymmetry to test was leaf-*off*.

## Goal

Replace the fixed-date leaf-off with the `gddmax>0` + `dlai` heat-unit
senescence so that leaf-off **timing varies with local climate** (and the leaf
phenology becomes hemisphere-robust), while preserving the winter-cancov ordering
(deciduous < mixed < evergreen) and avoiding the first-year-planting reset.

## Procedure

Use the established parameter mapping from `parameterization-research.md` (do not
re-guess positions). Names below are WEPP plant/management parameters.

1. **Enable heat-unit phenology**: set `gddmax > 0` (heat units to maturity) for
   the deciduous and mixed plants, instead of `0`. Choose a value that places
   maturity in the local growing season for a representative climate; this is the
   parameter to derive, not assume.
2. **Set the senescence-onset fraction `dlai`** to the `fphu` value at which
   leaf-off should begin (late in the heat-unit cycle for autumn onset). Confirm
   `dlai` and its position via `grow.for` (line ~245: "total growing degree days
   expected at senescence (0-1)") and the parser.
3. **Set the senescence decline `delcc`** (and any `dropfc`) so the canopy falls
   to the low deciduous winter target after onset — not abruptly, matching a
   multi-week leaf-off.
4. **Remove the calendar trigger**: set the Yearly-section senescence date back to
   `0` so the heat-unit path is the sole leaf-off driver (or keep it only as an
   explicit backstop and document that).
5. **Keep `jdplt=0`** (established perennial). The `jdplt=126` failure was a
   planting/leaf-out reset and is unrelated to leaf-off; leaf-out should continue
   to track spring warming via `crit`.
6. **Verify the leaf-out path still works** with `gddmax>0` (the prior trajectory
   leafed out Jun–Jul; confirm `gddmax>0` does not distort it).

## Acceptance

Run the single-hillslope winter-cancov validation (same method as
`winter-cancov-validation.md`) across **at least two contrasting climates** drawn
from the snow fixtures — e.g. a cold/high-elevation site (Niwot/Fraser CO or
Marcell MN) and a warmer/lower one (Harvard Forest MA or an Appalachian site).
Pass requires all three:

- **Climate-adaptive leaf-off**: the cold site senesces meaningfully **earlier**
  (in calendar days) than the warm site — i.e. leaf-off timing tracks
  temperature, which a fixed date cannot do. This is the decisive new evidence.
- **Winter-cancov ordering preserved**: deciduous low, mixed intermediate,
  evergreen high, with deciduous winter mean in the intended low range
  (consider a small bare-branch floor ~0.1 rather than 0%, per the ADR
  consequences).
- **No establishment reset**: no zero-canopy collapse; established perennial
  behavior intact.

## Fallback / honest-negative path

If the WEPP perennial GDD path cannot produce a clean full leaf-off (e.g. the
canopy does not decline far enough, or the regrowth cycle destabilizes),
**document the specific WEPP behavior** as a tried alternative in ADR-0009's
Alternatives section, and the fixed-date representation stands — but then the
Northern-Hemisphere scope and the non-climate-adaptive limitation (already
recorded in ADR-0009) are the accepted, documented tradeoff rather than an
unexplored gap.

## Scope

This is an **investigation**, not a mandate to change the shipped files. Decide
based on the two-climate evidence whether the GDD/`dlai` leaf-off is adopted. If
adopted, update the `.man` files, `winter-cancov-validation.md`, and ADR-0009
(including the hemisphere note, which then narrows to the engine winter-cycle
constraint only).

## Execution

Date: 2026-06-26.

Harness:

- Slope: `tests/disturbed/data/canonical_slope.slp`.
- Soil: `tests/disturbed/disturbed_matrix0/runs/p1.sol` (disturbed harness
  forest clay loam).
- Run template: `wepp_runner.make_hillslope_run(..., reveg=True)`, six
  simulation years.
- Managements: current `UnDisturbed/Deciduous_Forest.man` and
  `UnDisturbed/Mixed_Forest.man`, expanded with
  `Management.build_multiple_year_man(6)`.
- WEPP binary: `wepp_runner` `latest`.

Climate contrast:

| Label | Source climate | Station | Latitude | Elevation |
|-------|----------------|---------|----------|-----------|
| Cold/high elevation | `tests/omni/fixtures/honeyed_marathoner_sediment_inversion/run_root/wepp/runs/p118.cli` | MORAN WY | `43.87` | `2054 m` |
| Warmer/lower elevation | `tests/disturbed/data/test_climate.cli` | MC KENZIE BRIDGE RS OR | `44.17` | `420 m` |

Screened parameter grid:

- `gddmax`: `800`, `1200`, `1600`, `2400`, `3200`.
- `dlai`: `0.65`, `0.75`, `0.85`, `0.95`.
- Yearly-section senescence date (`jdharv` / WEPP `jdsene`): `0`, `1`, `120`,
  `180`, `240`, `286`.
- Both deciduous and mixed managements were run for both climates for each grid
  point.

Screening criteria:

- no negative or greater-than-100 percent `Cancov`;
- a detected fall decline in both climates;
- cold-site leaf-off at least 10 days earlier than warm-site leaf-off;
- plausible winter/summer canopy ordering.

## Results

Grid summary:

| Result class | Count | Interpretation |
|--------------|-------|----------------|
| Correct-direction candidates | `0` | No grid point made the cold site senesce earlier than the warm site while retaining valid canopy. |
| Wrong or equal direction | `100` | Senescence occurred, but the warmer site senesced earlier or at about the same time. |
| No leaf-off | `109` | Canopy stayed high into autumn/winter in at least one climate. |
| Invalid canopy | `31` | WEPP emitted impossible negative `Cancov` in at least one climate. |

Representative evidence:

| Management | `gddmax` | `dlai` | `jdharv` | Cold leaf-off DOY | Warm leaf-off DOY | Outcome |
|------------|----------|--------|----------|-------------------|-------------------|---------|
| Deciduous | `1600` | `0.85` | `0` | none | none | Exact GDD-only request: no leaf-off; October/December canopy stayed near `100%`. |
| Deciduous | `1200` | `0.75` | `120` | `288` | `214` | Wrong direction; warm site senesced `74` days earlier. |
| Deciduous | `800` | `0.75` | `120` | `244` | `214` | Wrong direction; warm site senesced `30` days earlier. |
| Mixed | `800` | `0.65` | `286` | `319` | `306` | Wrong direction; warm site senesced `13` days earlier. |
| Deciduous | `1600` | `0.85` | `1` | n/a | n/a | Invalid canopy; warm-site `Cancov` reached about `-300%`. |

The observed direction is consistent with the WEPP mechanism: `fphu` is the
fraction of accumulated heat units. With the same management parameters, a
warmer climate reaches the heat-unit threshold earlier, so GDD maturity tends
to make the warm site senesce earlier, not later. That is opposite the desired
fall leaf-off signal, where colder/high-elevation sites should lose leaves
earlier because autumn cooling arrives sooner.

## WEPP Behavior Determined

1. `jdharv=0` is not a pure "remove calendar trigger" setting for cropland
   perennials. In `grow.for`, the growth branch remains true when
   `jdsene == 0`, so the perennial senescence branch does not fire even after
   `fphu >= dlai`.
2. A nonzero `jdharv` is an earliest-date gate, not a backstop. Senescence starts
   only after both `sdate >= jdsene` and `fphu >= dlai`.
3. The `delcc` decline rate is not an input field in the `.man` file. WEPP
   derives it from canopy at senescence, `decfct`, and `spriod`.
4. Some early-gate combinations emitted impossible negative canopy cover in the
   warmer climate, so the pathway is not robust enough to ship as a default
   management representation.

## Decision

The GDD/`dlai` path failed the decisive acceptance test. The cold site never
senesced meaningfully earlier than the warm site across the screened grid, and
the exact `jdharv=0` GDD-only variant produced no leaf-off. The shipped
`.man` files and lookup rows are unchanged.

The fixed Julian senescence date remains the accepted default, with the
Northern-Hemisphere and non-climate-adaptive limitations recorded in ADR-0009.
Future work would need a different phenology mechanism, likely one based on
fall cooling, day length, or site-specific calibrated dates rather than WEPP's
single accumulated-heat-unit maturity trigger.
