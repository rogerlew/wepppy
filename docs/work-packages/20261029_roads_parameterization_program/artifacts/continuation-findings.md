# Released-engine continuation: evidence and decision boundary

Status: declared continuation batches complete; candidate rejected for promotion.
Scientific acceptance is blocked by native accounting failures and numerical misses. The six
withheld materials have not been simulated or used for candidate selection.
The owner requires human approval of the configuration specification and layout
before implementing the editor or production parameter persistence/application.

## Rebaseline

Executed `wctl exec weppcloud python
/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts/continuation.py`.
Frozen design: [design-v2.json](design-v2.json), preserving the version-1 material
split and numerical thresholds. Released watershed binary SHA256:
`53628775e0e97d03f3f8c12e0d99b0f25842efa429d3ce869bf37ee382974461`.

| Treatment | Cases | Magnitude pass | Physical/accounting pass |
|---|---:|---:|---:|
| Generated bare/bare/forest roles | 96 | 80 | 80 |
| Roles plus road erosion coefficients | 96 | 77 | 80 |
| Erosion plus road conductivity cap | 96 | 96 | 96 |
| Normalized legacy soil, modern runtime | 96 | 96 | 96 |
| Exact frozen-2010 soil, modern runtime (follow-up) | 96 | 96 | 96 |
| Conductivity treatment without erosion overrides (follow-up) | 96 | 92 | 96 |

Each lane includes all failures in its denominator. The 16 uncapped failures per
lane are native water-availability stops, not missing data to discard. All four
lanes retain the frozen geometry, management and climate inputs; modern lanes use
the same project runtime bundle. This is a three-OFE controlled comparison, not
production-project or climate-specific calibration evidence. Raw artifacts:
`/wc1/runs/ro/roads-parameterization-program-20261030/rebaseline-v1`.

The follow-up pilot crosses seven development materials and all four designs in
Birmingham, gravel, high traffic: **28/28** complete and pass both numerical and
physical/accounting checks. See [pilot receipt](development-pilot-v1-summary.json).
This supports broader development exploration; it does not resolve the native
failure found in the controls.

## Confirmed daily-budget limitation

Birmingham sand, inbare, gravel/high, generated roles: year 7, day 6, receiving
fill OFE 2 stops at hour 21. Erosion-coefficient changes leave this failure
unchanged. The soil contains the normalized 200 mm break. An independent scientific
review found no basis to label the source soil physically invalid.

The exact released binary was replayed under GDB without modifying state. All
seven output files are byte-identical to the original failed run. The retained
[budget receipt](unmet-budget-v1.json) reconstructs these receiving-OFE depths:

| Quantity | mm |
|---|---:|
| Initial mobile liquid storage | 66.627616 |
| Net full-day withdrawal after upstream return and all lateral inputs | 71.663278 |
| Unavoidable deficit before any other sinks | 5.035662 |
| Additional depletion through first 20 hours | 4.144095 |
| Of that depletion, deep seepage | 0.026183 |
| Hour-21 request | 2.933055 |
| Hour-21 available mobile stock | 2.555187 |

Frozen storage is zero. ET is evaluated at hour 24, after the failure. Rescheduling
the same daily totals cannot supply the missing water. This establishes an
unsupported daily runoff/soil coupling state; the erroneous producer has not yet
been identified. Do not suppress the inventory guard, loosen accounting gates,
call capped success proof that uncapped soils are invalid, or claim this is merely
the previously repaired source-time return attribution case.

Raw debugger evidence is under `unmet-trace-v1` and `unmet-trace-v3` in the same
study root. Version 2 was intentionally interrupted because hourly conditional
breakpoints made tracing unnecessarily slow; version 3 enables hourly probes only
after reaching the selected day. The completed version-3 output parity receipt
is authoritative. Independent AI scientific review confirmed the arithmetic and
byte equality, and recommended retaining the pinned engine and withholding final
parameterization acceptance pending explanation of this daily coupling state.

## Expanded development result and disposition

The complete five-climate × seven-material × four-design × two-surface ×
three-traffic matrix contains **840 cases**. All failures remain in denominators:

- Magnitude: **740/840 (88.10%)**, below the frozen 95% requirement.
- Meaningful reference loads: **710/766 (92.69%)**; small reference loads:
  **30/74 (40.54%)**. Both fail their separate gates.
- Physical/accounting: **822/840**. Nine native water-availability stops and nine
  completed cases with sediment-output reconciliation failures are hard blockers.
- Outslope-unrutted magnitude: **137/210 (65.24%)**; Denver: **123/168 (73.21%)**.
  The numerical issue is broader than the native-stop cases.

See [stratified results](development-matrix-v1-stratified.json) for all groups,
intersections, raw ratios, zero outcomes, signed log bias and failure membership.
Material groups are balanced at 120 cases each, so raw and equal-material-weight
pass fractions agree. These remain matched FSWEPP three-OFE sensitivity results
with fixed site runtime sidecars, not climate-specific production validation.

The conductivity-only ablation is not an acceptable simplification: although
92/96 exceeds 95% overall, its loam group passes only 20/24 (83.33%). Four
Birmingham/Flagstaff loam/gravel/high cases severely underpredict. Retain this
negative result; do not quietly remove the erosion overrides based on the total.

All **294 production-builder readback cases** passed: seven materials × seven
routing arrangements × two surfaces × three traffic levels. Road location and
untreated material/roles survive generated-soil injection exactly. Native and
full-project execution for these arrangements remain unperformed; this is a
preparation bridge, not an end-to-end product claim.

### Candidate water failure, not only a rejected control

Nine Charleston/material-53949/gravel cases (inbare, inveg, outrut × all traffic)
stop at the inventory guard. The high-traffic inbare case stops at year 16, day 54,
OFE 2, hour 11. An exact-binary trace reproduces all seven native outputs:
initial liquid storage **118.079187 mm**, net daily withdrawal after all incoming
return/lateral water **247.881761 mm**, leaving **129.802574 mm unfunded before
other sinks**. Frozen storage is zero. See
[Charleston budget](charleston-cap-budget-v1.json). This rules out treating the
native limitation as merely an uncapped-control curiosity.

### Separate sediment-output discrepancy

Nine site/material-53949/gravel cases complete but fail both ELEMENT/EBE and
ELEMENT/annual-report reconciliation. Representative date 2005-01-19 has outlet
ELEMENT sediment **3.734 kg/m** versus EBE **0.0 kg/m**. ELEMENT repeats the
previous day's sediment and peak/duration despite zero precipitation and only
0.166 mm outlet flow. This supports investigating stale event-output state; it
does not yet establish which output or producer is wrong. The annual discrepancy
is 0.925403 kg/year against the predeclared 0.176702 kg/year precision bound.
Do not widen the bound, drop the event or merge this issue with the water deficit.

### Matched capped/uncapped attribution

The Birmingham cap trace has essentially identical fill stock and identical
incoming hourly surface/lateral arrays, but a smaller daily runoff-derived debit.
The treatment raises road effective infiltration from **5.5114 to 10.0000 mm/h**
in this event, despite capping upper-horizon conductivity, because it also disables
the forest adjustment. Equivalent-plane infiltration rises from 5.3150 to
9.4906 mm/h. The same 47.9957 mm equivalent-plane snowmelt input produces different
runoff before WATBAL; the capped fill has a net positive daily input of 2.88856 mm.
A 0.011054 mm interception difference closes the previously unexplained FIN term;
remaining arithmetic discrepancy is 0.0000088 mm. All capped replay outputs match.
See [paired attribution](paired-daily-coupling-v1.json). Do not describe this result
as proof that increased compaction alone corrected runoff.

### Control comparability correction

Independent implementation review identified that the original `legacy_soil`
lane used normalized 200/300 mm fill/buffer layers, while the frozen 2010 deck had
single 300 mm layers. It therefore includes normalization as well as engine/runtime
differences. The added `legacy_exact` lane copies the frozen 2010 soil bytes exactly
and passes 96/96. All non-soil inputs are identical between these two modern lanes;
[paired controls](legacy-normalization-comparison.json) isolate normalization under
modern runtime. Neither comparison against 2010 is engine-only because the modern
project runtime bundle is explicitly different. No normalization was reverted.

## Reproducible failure fixtures and validation

The original paired failure/control inputs are retained in
[daily-coupling-fixture/manifest.json](daily-coupling-fixture/manifest.json).
The candidate Charleston water stop and site sediment discrepancy are retained in
[broad-failure-fixture/manifest.json](broad-failure-fixture/manifest.json).
Both archives reproduce all expected native output hashes under the pinned engine.
A successful diagnostic replay means reproduction of a known failure, not model
acceptance. Raw inputs include climate and sidecars; no private run path is needed
to reconstruct the fixture. See [fixture instructions](fixture-instructions.md).

Scripts used `wctl exec weppcloud python` with the artifact driver path:
`continuation.py`, `cap_only.py`, `development_pilot.py`, `development_matrix.py`,
`builder_bridge.py`, `exact_legacy_control.py`, and `continuation_report.py`.
Fresh batch roots and input/binary hashes fail closed. Completed output parsing,
calendar/finite checks, sediment reconciliation, water transfers and exact native
fixture replay provide the validation for these isolated research drivers. No
production Python, controller or frontend logic changed; a repeated full repository
suite was not used as a substitute for these native artifact checks.

The forest-local raw trees also have a network-storage archive at
`/wc1/runs/ro/roads-parameterization-program-20261030/forest-local-evidence-v1.tar.gz`.
The [archive receipt](archive-receipt-v1.json) records its SHA256 and successful
streamed verification of **17,784 declared native input/output files** across all
840 broad cases and 96 exact-legacy controls. The other study batches remain in
the original network-storage root. Independent review dispositions are retained
in [continuation reviews](continuation-reviews.md). Markdown checks pass for the
package, canonical Roads specification and project tracker; artifact Python files
compile successfully and the change set passes whitespace validation.

## Next scientific decision

Reject the current candidate for promotion, keep the six withheld materials unused,
and preserve the engine, inventory guard and acceptance criteria. The next bounded
work package should investigate the native daily runoff producer separately from
stale sediment output, using the retained fixtures before further Roads tuning:

1. Trace equivalent-plane snowmelt/source aggregation and infiltration averages in
   `irs.for`, then GRNA/ROCHEK, QINF and the `runsav`/`runtmp` handoff to WATBAL.
   Reconcile actual incoming water and mobile stock before any proposed change.
2. Independently trace ELEMENT/EBE state initialization on the site return-flow
   event; require agreement without hiding a real sediment flux.
3. Test a physically justified, conservative native repair in an isolated ablation;
   retain source-time partition, ET fixes, portability and the inventory guard.
   Changing the adopted engine needs its own explicit scientific/release disposition
   under this program's pinned-binary charter; do not silently substitute a probe.
4. Re-run these fixtures and the full development matrix before renewed parameter
   search. Any proposed shared native repair also needs native regression/Disturbed
   and Cedar Creek assessment before promotion. Revisit the separate magnitude
   failures after valid outputs, then freeze rules and consume withheld data once.

The present UI gate has **not** been reached. Neither a default nor a safe editable
hydraulic envelope is established; drafting an apparently validated configuration
view now would misrepresent the evidence. The human specification/layout approval
requirement remains in the canonical Roads specification and active plan.

## Preparation correction and remaining scope

The first builder bridge attempt failed before native execution because the
Disturbed detailed texture `sand loam` was incorrectly passed as a legacy Roads
four-class lookup key. Version 2 explicitly separates the declared legacy
comparison class from generated-material preparation texture. No production
resolver was changed. Material-to-reference assignments preserve earlier studies;
they are comparison choices, not claims of identical material composition.

Final withheld validation, parameterization ADR, configuration specification and
layout remain downstream of scientific acceptance. No production defaults, native
binary, project state, UI or deployment were changed by this continuation.

## Native ablation disposition — 2026-10-30

Canonical native package: `/workdir/wepp-forest-release-20261009/docs/work-packages/20261030-roads-native-accounting/`.
The separate U2c stale-event repair is retained for validation. C3 water changes
are rejected and rolled back despite 840/840 output-accounting passes: independent
controls demonstrate lost connected hydraulic support, inconsistent peak-area
normalization and skipped deposition when runon fully infiltrates. Cedar peak
+42.64% and sediment +35.05% with water +0.00212% require this hold.
C3 magnitude is 719/840, while literal-legacy attribution is 96/96. Neither is a
Roads default acceptance. Frozen inputs, candidates, review probes and Cedar figures
are retained in the native package. The water mechanism remains unresolved;
C4 diagnostic controls define the next geometry/accounting contract before another
behavioral patch. Keep wepp_261029 pinned, withheld materials unused, and parameter
tuning paused. The human gate on configuration specification/layout still applies.
