# Unassigned-Pixel Sentinel Color Analysis

**Date**: 2026-08-24 (revised after independent review)  
**Author**: Claude Code  
**Selected sentinel**: `#800098` = `rgb(128, 0, 152)`  
**Reproduce**: `python3 2026-08-24_palette_baseline.py`,
`python3 2026-08-24_sentinel_search.py`. Both resolve `2026-08-24_cvd_lib.py`
relative to their own path and run from any working directory.

## Purpose

The operator decided that unassigned/missing SBS pixels are their own state,
distinct from masked/NoData, and must be identifiable on the deck.gl map because
users validate their classification there. This analysis selects the sentinel.

## Method

Color-vision deficiency simulated with the Machado, Oliveira & Fernandes (2009)
severity-1.0 dichromat matrices applied in linear RGB. Differences computed as
CIEDE2000 in CIE Lab (D65).

**Operation order.** The browser composites the layer over the basemap, and the
eye then perceives the composited pixel. Compositing therefore happens **before**
CVD simulation. Candidates are composited source-over onto light (`#F2F2F2`) and
dark (`#1A1A1A`) grounds in sRGB space at layer opacity `1.0` and `0.3`
(`SBS_DEFAULT_OPACITY`, `map_gl_shared.js:42`), and the composited result is then
simulated.

> **Correction.** The first version of this analysis simulated foreground and
> ground separately and composited afterwards. That order is wrong and not
> interchangeable, because `simulate()` applies transfer functions, clipping, and
> 8-bit rounding. The error was found by independent review
> (`2026-08-24_revision3_review.md`, finding 3) and confirmed by recomputation.
> Every figure below is from the corrected order. Superseded figures were
> standard `5.04`, shifted `3.48`, and `#7F00FF` at `10.39`.

Caveat: these matrices model full dichromacy, the worst case. Anomalous
trichromats see smaller shifts. Figures are a screening tool, not a prediction of
any individual's perception.

## Finding 1: the bar is the palette's own separation

At `SBS_DEFAULT_OPACITY = 0.3` no color in the search space achieves a
worst-case separation much beyond `12`. Demanding more of the sentinel than the
severity classes achieve among themselves is not meaningful:

| Palette | worst intra-palette dE2000, alpha 1.0 | worst intra-palette dE2000, alpha 0.3 |
| --- | --- | --- |
| Standard (508) | `22.77` (tritanopia, unburned vs low) | `5.32` (protanopia, unburned vs low) |
| Shifted (CVD) | `12.21` (tritanopia, unburned vs low) | `2.83` (deuteranopia, unburned vs high) |

## Finding 2: semantic non-collision is a hard constraint, not a tiebreak

The first two rounds of this analysis scored only perceptual distance. That was
incomplete. On a burn-severity map the hue itself carries meaning, and a sentinel
that lands in an occupied band is disqualified regardless of its dE score:

| Hue band | Meaning already carried on these maps |
| --- | --- |
| Green | Unburned - generation-0 `46,203,24`, generation-A `0,115,74` |
| Teal / cyan | Current unburned and low severity |
| Yellow, orange, red | The severity ramp |
| Blue | Water: channels and watershed layers |
| White | Masked / unmappable |
| **Violet to magenta** | **Unoccupied** |

`#2000E0`, selected in the previous round on a score of `12.08`, sits at hue
`248.6` - inside the blue band. It would read as a hydrographic feature. It is
therefore **rejected on semantics despite being the perceptual optimum**, and the
search is constrained to hue `270`-`330` at saturation `>= 0.55`.

## Finding 3: selected sentinel `#800098`

The operator selected `#800098` after balancing the requested red/magenta
semantics against palette separation. Under the original exploratory scoring it
has a worst-case CIEDE2000 distance of `8.07`; `#5000A0`, not `#800098`, is the
`9.97` candidate. The table below preserves those measurements without treating
the cross-mode, composited ranking as an accessibility conformance proof.

| Candidate | worst dE2000 | hue | semantics | binding constraint |
| --- | --- | --- | --- | --- |
| `#800098` | `8.07` | `290.5` | selected by operator | tritanopia / light / 0.3 / standard high |
| **`#5000A0`** | **`9.97`** | `270.0` | free | tritanopia / dark / 0.3 / basemap |
| `#500090` | `9.82` | `273.3` | free | tritanopia / light / 0.3 / shifted high |
| `#6000C0` | `9.31` | `270.0` | free | tritanopia / light / 0.3 / shifted high |
| `#7F00FF` | `8.64` | `269.9` | free | tritanopia / light / 0.3 / shifted high |
| `#FF00FF` | `5.39` | `300.0` | free | deuteranopia / light / 1.0 / shifted low |
| `#2000E0` | `12.08` | `248.6` | **blue - rejected** | tritanopia / dark / 0.3 / basemap |
| `#0000E0` | `12.08` | `240.0` | **blue - rejected** | tritanopia / dark / 0.3 / basemap |
| `#FF7F00` | `4.41` | `29.8` | **severity ramp - rejected** | deuteranopia / light / 0.3 / shifted moderate |
| `#000000` | `2.32` | n/a | gray / nodata convention | normal / dark / 0.3 / basemap |
| `#FFFFFF` | `0.82` | n/a | **masked - rejected** | normal / light / 0.3 / basemap |

## Finding 4: rejected candidates

**Magenta `#FF00FF`** - `5.39`, binding against shifted low under deuteranopia.
Below the standard palette's own baseline. Rejected.

An earlier claim that magenta also collides with shifted low under *protanopia*
was wrong; that distance is comfortable. The genuine collisions are deuteranopia
against shifted low and tritanopia against shifted high.

**Purple `#7F00FF`** - `8.64`, semantically free but confusability-bound against
shifted high. Superseded by the operator's semantic choice.

**Blue-violet `#2000E0`** - the perceptual optimum at `12.08`, superseded on
semantics. Hue `248.6` reads as water on a map that renders channels and
watershed layers. Recorded so the trade is explicit: roughly two dE points of
separation were given up to keep the sentinel out of an occupied hue band.

**Partial alpha** - withdrawn. Layer opacity multiplies per-pixel alpha, so a
50% sentinel renders at an effective `0.15` at the default and composites toward
the basemap, becoming least visible exactly when a user lowers opacity to
inspect. Full per-pixel alpha is correct.

## RETRACTED: the claimed accessibility finding

An earlier version of this analysis reported that `SBS_DEFAULT_OPACITY = 0.3`
attenuates the palettes to the edge of discriminability - shifted `2.83`,
standard `5.32` - and referred that to DOM-04B as an accessibility defect.

**That finding is withdrawn. It was an artifact of two methodological errors.**

1. Candidates were scored against the **union** of the standard and shifted
   palettes. Those are mutually exclusive display modes; a user sees four
   colors, never eight. Combining them fabricates constraints that no user
   ever experiences.
2. Everything was composited at `0.3` layer opacity. At 30% over a basemap
   *any* set of colors converges. That is a property of the compositing, not of
   the palette, and the opacity slider is the supported control.

Assessed correctly - one palette at a time, full opacity, no compositing - both
palettes are sound:

| Palette | normal | protanopia | deuteranopia | tritanopia |
| --- | --- | --- | --- | --- |
| Shifted (Okabe-Ito members) | `34.69` | `14.07` | `15.54` | `12.21` |
| Standard (USGS 508) | `23.55` | `23.04` | `23.77` | `22.77` |

The shifted palette behaves as an Okabe-Ito derivative should. The standard
palette is in fact the more dichromacy-robust of the two, holding roughly `23`
across all four vision models because it varies strongly in lightness, which
survives color-vision deficiency, where the Okabe-Ito subset leans more on hue.

**Consequences.** No palette change is proposed or warranted. The DOM-04B
referral is withdrawn as erroneous, not closed as won't-fix. The exploratory
ranking is not used as conformance evidence; `#800098` is a single operator-
selected semantic sentinel for both modes, while legends and explicit text carry
the accessible meaning.
