# Experiment Note: Temperature-Driven (GDD/`dlai`) Leaf-Off

Status: proposed follow-up (not yet run). Authored by Claude Code 2026-06-26,
review phase.

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

WEPP already supports this. Per `grow.for`: `gdd = tave - btemp`,
`sumgdd` accumulates, `fphu = sumgdd / gddmax`, and **senescence begins when
`fphu >= dlai`**, after which canopy cover declines at the `delcc` rate. Leaf-out
already tracks spring warming via the `crit` heat-unit emergence threshold, so
the asymmetry to fix is leaf-*off*.

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
recorded in ADR-0009) are the accepted, documented trade-off rather than an
unexplored gap.

## Scope

This is an **investigation**, not a mandate to change the shipped files. Decide
based on the two-climate evidence whether the GDD/`dlai` leaf-off is adopted. If
adopted, update the `.man` files, `winter-cancov-validation.md`, and ADR-0009
(including the hemisphere note, which then narrows to the engine winter-cycle
constraint only).
