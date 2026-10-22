# MC source and publication checkpoint

The reviewed source changes preserve Muskingum-Cunge recurrence and numerical
storage authority. **Promotion is blocked:** the required 100-year execution
gate timed out after 900 seconds at year 16/day 81. Native changes remain an
uncommitted candidate, not an accepted checkpoint or full watershed closure.

## Corrected boundaries

WSHCHR represents positive ordinary-channel local water when no side surface
hydrograph exists, excluding positive side-impoundment releases. It admits deferred
WSHCQI groundwater into qin once and removes the redundant first-call outlet term.
These shared source fixes apply to KW3 and MC4/5. Positive side-hill reconstruction
and the existing signed-loss branch are preserved.

MC daily publication now integrates accepted q1 with its time-zero endpoint;
q0 also participates in peak metadata. The same amount reaches runvol, tmpvol
and downstream daily accounting. Manning geometry remains independently
calculated; its diagnostic residual is exposed instead of being forced to zero.
KW3 publication and all routing recurrences retain their existing conventions.
Public schemas, defaults, capacities and release binaries are unchanged.

## Evidence

All 29 fresh paired replays pass date, finite-output and hillslope transfer checks:
ten portable two-year cases, eighteen supplementary 44-year layouts/networks,
and the 400-year hourly 60/40 case. These checks do not certify channel closure.
Independent QA ran 108 native controls across KW3/MC4/MC5, both source modes,
three upstream placements and separate/combined direct/deferred groundwater.
It confirms 15,660 exact downstream rate samples, 108 exact daily transfers,
and 324 MC publications equal to the rounded accepted integral.

The publication-only experiment independently passes 24 single/cascade controls
and a q0-only export case. A 100 m³/day groundwater-only first call initializes
uniform discharge and exports 100 m³ in MC4/5. Continuations preserve inlet and
outlet boundary carry. An earlier isolated prototype was rejected for duplicate
first-call groundwater and overly broad impoundment eligibility; neither defect
is in the corrected source.

Portable tests in native `tests/test_channel_interfaces.py` execute real
WSHCQI/WSHCHR. They observe every source/outlet sample, verify ordered complete
finite records, one-time admission on every day, inherited source/outlet
endpoints, daily transfer and MC publication. The q0-only case seeds the state
before native routing; it does not fabricate the final flux. Baseline comparison
of the initial 37 tests gives 31 failures and six controls; expanded coverage
also includes legacy source and impoundment cases. See the QA review for mutation
checks that exposed and closed gaps in the first test draft.

Both isolated system-gfortran profiles are built, request the system ELF loader,
and pass host smoke checks. These smoke scripts execute hillslope p1 for each
profile; the paired replays are the actual watershed evidence. Twelve full
100-year watchlist cases pass. The full suite reports 409 passed, one failed (the 900-second execution timeout),
and two existing warnings in 938.70 seconds. Final expanded interface tests pass
55 cases, including reviewed mutation controls. See
`mc-interface-v2-validation-receipt.json`; narrow successes do not override the
failed required gate.

## Open acceptance boundaries

The signed-coupling review demonstrates a mismatch independently of negative MC
coefficients. With fixed positive coefficients, 100 m³ incoming water and a
prescribed producer-consistent 50 m³ daily loss yield approximately 91.519 m³
accepted outlet in the early-pulse control. A late pulse skips 47.396 m³ of the
requested loss before water arrives. WATBAL is not executed in that controlled
experiment; its post-soil runoff identity is prescribed. See
[signed-coupling-review.md](signed-coupling-review.md).

Actual 44-year observation-only replays preserve all scientific output hashes.
Raw-to-export clipping adds 965.556 m³ (daily single OFE), 36.449 m³ (hourly single)
and 58.886 m³ (hourly three OFEs), approximately 0.132%, 0.00477% and 0.00770% of
accepted export respectively. These are numerical interface differences, not
independent estimates of total physical budget error. Positive-lateral cases
also clip, so signed losses cannot explain every occurrence.

A separate adaptive reference-flow case retains interior discharge but selects
zero K and stops propagating it during the retained recession period. That is a
coefficient/propagation boundary, not observed deletion of the discharge profile.
It requires separate diagnosis; a zero recurrence residual does not close it.

Additional actual WATBAL→WSHDRV→WSHCHR observations cover the same three
44-year cases with identical scientific outputs. They retain pre/post available
liquid and frozen soil depths, Dp, lateral release, transpiration/evaporation,
post-soil runoff and requested transmission. Producer and runoff-depth/volume
identities agree within binary32 rounding. These observations are not a complete
soil budget and do not attribute all clipping to transmission loss; a controlled
early/late full-soil case remains next. See `mc-soil-exchange-observation.json`.

## Next repair boundary and rollback

Retain requested, executed, skipped and clipped amounts with soil-side credits.
A complete signed-exchange repair must commit the same accepted withdrawal to
routing and soil, including its effect on percolation, ET and release. Do not
reduce rtrans after WATBAL, normalize outlet rates, impose geometric storage or
silently choose a new temporal/spatial absorption rule. The scientific review
sets out a bounded coupled-exchange prototype and the contract choices it needs.
The work package remains active until those choices are reviewed and tested.

Rollback for this source checkpoint is native `22133f0c9`; the original 261021
release pair remains untouched. Regenerate contributing hillslope/PASS/watershed
artifacts together before using a future release. No push, vendoring, deployment
or switch of defaults is part of this checkpoint.
