# O6 attribution and U1 continuous-recession trial

O6 locates the original five funding failures at an abrupt QINF regime switch.
An isolated U1 candidate removing that outer switch completes all twelve
16-year decks and removes the observed unfunded demands. **This is a promising
screening result, not an accepted physical repair or release.** One funded
negative local exchange remains and needs a physical interpretation.

## Attribution on released behavior

All 24 O6 off/on replays preserve expected native status and every output hash.
Ten executions reproduce the five original failures; fourteen complete. There
are 185,824 daily states, 185,819 completed, and 4,310 linked QINF states.
In those 4,310 states the raw storm contribution is never negative and never
exceeds available funding. The recession difference creates all five unfunded
states. There are 420 negative incremental recession differences; these are
actual differences, distinct from O4's 425 monotone-shadow conflicts.

The physical-volume identity is `FIN = local net supply + raw upstream runoff -
raw outgoing runoff + outgoing recession loss - upstream recession loss`.
Maximum reconstruction difference is 1.522e-6 m³ from single-precision operands.
The actual accepted upstream handoff matches the previous post-QINF flow exactly.

For simulation year 12/day 190/fill, depths below use the local fill area:

| Material | Raw storm exchange (mm) | Recession difference (mm) | Net FIN (mm) | Starting available water (mm) | Funding deficit (mm) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2711184 loam | 32.362936 | -42.940645 | -10.577716 | 7.753312 | 2.824404 |
| 2711250 silt | 35.764116 | -43.053751 | -7.289637 | 5.943309 | 1.346328 |

Three loam and two silt configurations reproduce these events; they are not five
independent hydrologic mechanisms.

The saved upstream `stold` values match the same day's upstream GRNA starting
snapshot exactly in **4,145/4,145** comparisons. Four additional snapshots lack
a same-day GRNA comparator and remain unclassified. Current upstream stocks can
differ because their water balance has already executed. Do not replace stold
with current stocks on the unsupported assumption that it is stale.

## QINF discontinuity

All 2,941 zero-recession QINF states have positive end infiltration rate but
`tstar < 1`; none is explained by a nonpositive-rate guard. The other 1,369
states enter the recession formula. In the original failures:

| Material | Road tstar | Combined road/fill tstar |
| --- | ---: | ---: |
| 2711184 | 1.119778 | 0.714338 |
| 2711250 | 1.188606 | 0.761237 |

Thus the road assigns recession infiltration while the downstream equivalent
plane assigns none. This is not proof that QINF's equation alone is wrong;
it identifies the discontinuity and its interaction with local ownership.

A seven-point native probe, using released QINF source and fixed rainfall-excess
rate, geometry and infiltration rate, confirms retained runoff fraction jumps
from 1.0 at tstar=0.9999 to 0.622024 at tstar=1.0. The change is far larger than
floating-point noise. The source header documents two formulas separated by
ftest; their scientific validity below one still needs review.

ROCHEK remains a separate path: O6 records 3,008 calls and 2,816 partial wetted
lengths. These are not silently assigned a QINF loss. Existing C3 geometry and
incoming-event counterexamples remain adoption gates; O6 does not revalidate
a changed sediment or routing model.

## U1 single-change candidate and results

The predeclared [U1 contract](native-U1-science-contract.md) removes only QINF's outer
`tstar >= 1` conditional and matching ENDIF. It retains the positive-rate guard,
ftest branches, formulas, coefficients, all geometry and native funding guards.
Builds and runs are isolated; production source and released binaries are intact.
The seven-point candidate probe is continuous across one (retained fractions
0.622062 at 0.9999 and 0.622024 at 1.0).

All **12/12 full 16-year cases complete**. All output hashes are retained and
rechecked; output changes are expected, not parity regressions to hide. Published
WAT contains complete, duplicate-free calendars and no negative/nonfinite data
values in all twelve cases. This is a limited output screen, not full physical
or sediment acceptance.

The candidate records **210,384 completed states** and 4,673 linked QINF stages.
The O5 matching-stage ledger applied to all candidate states closes within
**0.000304 mm** at both hourly-end and post-SWU boundaries; this uses measured
ET/plant stock changes and is not independent validation of those process laws.
There are no observed unfunded daily requests and no negative raw storm
exchanges in the linked stages; hourly guards also complete. The signed partition
reconstructs within 1.701e-6 m³. However, **1,070 negative incremental recession
differences remain**. Funded arithmetic alone does not prove those transfers have
a defensible physical source.

Negative total local FIN among linked stages decreases from 34 released states
to **one candidate state**: delayed_return year 1/day 9/element 2. Its demand is
1.514375 mm, with about 50.23 mm starting available water, so it is funded.
Retain the full operands in U1-remaining-signed-exchanges.json. This unresolved
exchange blocks calling the candidate a complete ownership repair.

## Next continuation and promotion limits

Keep U1 as an experimental candidate. First resolve the physical meaning of
that remaining negative exchange and establish whether QINF's documented
recession formulas apply continuously across the equilibrium threshold. Use
the retained native threshold probe and counterexample as regression fixtures.
Do not turn a funded but unexplained transfer into an accepted rule.

Then run the candidate through matching-stage stock conservation, soil-capacity,
geometry/peak and deposition/event checks, native release/watchlist regressions,
Disturbed and Cedar Creek semantic gates. Only after those pass should the
unchanged 840-case Roads development magnitude gate be compared. An adopted
formula requires an ADR and updated user/release documentation. Withheld
materials and human UI specification/layout approval remain reserved.

No Roads parameter, production default, native guard, released binary or UI was
changed. There is no candidate adoption or magnitude-pass claim.

## Reproducibility

O6 helpers: build_ownership_observer.py, replay_ownership_observer.py,
attribute_ownership.py, classify_recession_branch.py and probe_qinf_threshold.py.
U1 helpers: build_continuous_recession.py, replay_continuous_recession.py,
attribute_continuous_recession.py, probe_continuous_recession.py and
screen_continuous_outputs.py. Compact receipts carry source/patch/binary and
input/output hashes. The first O6 build failed when an inserted marker joined
a Fortran comment line; it was corrected before any model execution and its
build log is retained. No simulation failures were omitted.

The new ownership-v1 archive retains raw logs, inputs, outputs, full signed
attributions, probe executables and build provenance. Prior archives remain
immutable; see ownership-retention-receipt.json. Native source remains clean.

Native helpers/receipts above live in
`/workdir/wepp-forest-release-20261009/docs/work-packages/20261031-roads-open-boundary-funding/artifacts`.

Validation: O6 and U1 host smokes each complete three years. Native incident
finalization, artifact policy, scoped documentation lint and changed-scope diff
checks pass. The repository-wide WEPPpy diff check also reports unrelated
trailing whitespace in wepppy/rq/project_rq_archive.py; that concurrent work was
left untouched. Full scientific/release gates remain pending, not waived.

Retained archive: 1,036 files, all member SHA-256 values verified.
Archive SHA-256: `f0d79d39e7f0284c3059100428d1bf8218e27ebeef240fd3bd8d5a9298c702d1`.
