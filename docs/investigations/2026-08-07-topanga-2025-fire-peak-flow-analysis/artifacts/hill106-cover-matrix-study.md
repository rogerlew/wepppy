# Hill 106 Canopy- and Ground-Cover Matrix

## Question

Does the counter-intuitive peak-flow response in the undisturbed Hill 106 run
follow smoothly from increasing canopy or ground cover, or does a cover input
move WEPP across a discontinuous peak-flow regime?

## Design

We started from the undisturbed, no-restrictive-layer Hill 106 input with PMET
`Kcb = 1.20`. We held climate, slope, soil, first-horizon Ksat (`35 mm/h`),
anisotropy, rooting, maximum LAI (`5`), PMET, and every other management value
constant. The only mutations were:

- initial canopy cover (`cancov`): `0.30`, `0.55`, `0.70`, `0.80`, `0.90`, or
  `0.95`; and
- initial ground cover: the same six levels assigned together to `inrcov` and
  `rilcov`.

This produced 36 full 45-year runs with `wepp_260803` (SHA-256
`4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5`).
The original undisturbed management is the `c70_g90` cell. We examined the ten
previously selected watershed comparison dates plus February 14, 1980 and the
known February 15, 1986 outlier.

## Results

There is no general monotone relationship in which more cover produces a
larger peak. Seven of the 12 selected events have less than a 10% difference
between the smallest and largest peak anywhere in the matrix. Four dates have
larger but event-specific changes: November 30, 1982 (`1.10x`), January 10,
1995 (`1.41x`), January 9, 2005 (`1.62x`), and December 30, 2021 (`1.25x`).
The February 15, 1986 event is qualitatively different, spanning `3.52` to
`323.03 mm/h` (`91.9x`) while runoff spans only `42.83` to `44.12 mm`.

| Event | Original cell peak | Matrix minimum | Matrix maximum | Maximum/minimum |
| --- | ---: | ---: | ---: | ---: |
| 1980-02-14 | 96.11 mm/h | 95.57 mm/h | 97.08 mm/h | 1.02x |
| 1982-11-30 | 109.35 mm/h | 102.90 mm/h | 112.78 mm/h | 1.10x |
| 1983-03-01 | 114.12 mm/h | 113.29 mm/h | 114.46 mm/h | 1.01x |
| 1986-02-15 | 3.56 mm/h | 3.52 mm/h | 323.03 mm/h | 91.87x |
| 1995-01-03 | 135.56 mm/h | 133.16 mm/h | 144.02 mm/h | 1.08x |
| 1995-01-10 | 115.28 mm/h | 81.84 mm/h | 115.55 mm/h | 1.41x |
| 1996-02-20 | 85.45 mm/h | 85.22 mm/h | 85.55 mm/h | 1.00x |
| 2005-01-09 | 157.62 mm/h | 97.43 mm/h | 157.87 mm/h | 1.62x |
| 2005-02-21 | 81.38 mm/h | 80.05 mm/h | 81.57 mm/h | 1.02x |
| 2019-01-16 | 77.02 mm/h | 76.77 mm/h | 77.28 mm/h | 1.01x |
| 2021-12-29 | 96.10 mm/h | 94.54 mm/h | 107.11 mm/h | 1.13x |
| 2021-12-30 | 133.03 mm/h | 108.89 mm/h | 135.92 mm/h | 1.25x |

### The 1986 Boundary Is Ground-Cover Controlled

At the original canopy value (`cancov = 0.70`), raising paired ground cover
from `0.80` to `0.90` changes the peak from `312.29` to `3.56 mm/h`. Runoff
increases slightly from `43.41` to `43.47 mm`; effective rainfall intensity is
identical at `39.12 mm/h`; and pre-event soil water decreases from `211.45` to
`211.10 mm`. The reported effective duration changes from `0.139` to `12.20 h`
because WEPP calculates it after the peak as runoff divided by peak rate.

The boundary persists at every canopy level. Ground cover at `0.80` produces
peaks of `296` to `323 mm/h`, whereas ground cover at `0.90` produces peaks of
only `3.52` to `3.61 mm/h`. Changing canopy cover by itself therefore does not
explain the previously observed 82-fold baseline-versus-dense-management
result. That earlier screen also changed maximum LAI, and its high-ground-cover
case moved in the opposite direction. Taken together, the screens establish a
strong interaction among the evolving vegetation, cover-dependent hydraulic
state, and peak solver; they do not yet identify a single cover variable as
the unique cause.

### Other Events Also Show Regime-Like Steps

January 9, 2005 stays near `97–112 mm/h` through most cells and then jumps to
about `157–158 mm/h` at high ground cover. January 10, 1995 rises from roughly
`82–103 mm/h` to `115 mm/h` near the same end of the ground-cover range.
December 30, 2021 contains the opposite step: peak falls from about `133` to
`109 mm/h` at `0.95` ground cover when canopy is at least `0.80`. These shapes
are inconsistent with a single smooth physical cover effect. They indicate
that cover-dependent roughness and geometry can move individual events among
different numerical peak-response regimes.

### Annual Water Balance Does Not Explain the Peak Steps

Across the matrix, 2020 surface runoff ranges from `5.90` to `9.75 mm`, lateral
flow from `1.03` to `3.22 mm`, and ET from `239.87` to `299.13 mm`. The original
`c70_g90` cell has `8.60 mm` surface runoff, `1.44 mm` lateral flow, and
`295.01 mm` ET. Canopy cover strongly changes ET and antecedent storage, but
the extreme selected-event peak changes occur with almost unchanged event
runoff. The matrix therefore reinforces the separation between the long-term
ET/water-balance problem and the subdaily peak-flow solver defect.

## Interpretation

This study does **not** support the physical claim that increasing cover
generally increases peak flow. It shows that paired initial interrill/rill
cover is an effective switch for several event-specific peak solutions. The
smoking gun is February 1986: a `0.10` ground-cover change moves the result by
two orders of magnitude despite effectively unchanged runoff, rainfall
intensity, and antecedent soil water. The exact internal operand or branch
responsible still requires the instrumented OpenWEPP reproducer; the matrix
localizes the transition and supplies compact bracketing cases (`c70_g80` and
`c70_g90`).

## Artifacts

- [`hill106-cover-matrix-selected-events.csv`](hill106-cover-matrix-selected-events.csv):
  event-level response and state fields for all 432 combinations.
- [`hill106-cover-matrix-summary.csv`](hill106-cover-matrix-summary.csv): 2020
  water balance and full-period peak summaries for all 36 runs.
- [`hill106-cover-matrix-selected-events.svg`](hill106-cover-matrix-selected-events.svg):
  selected-event peak-response surfaces.
- [`run_hill106_cover_matrix.py`](run_hill106_cover_matrix.py) and
  [`plot_hill106_cover_matrix.py`](plot_hill106_cover_matrix.py): reproducible
  runner and plotter.
