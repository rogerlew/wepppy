# Validate modern Roads parameters and prepare a human-reviewed configuration design

This living plan follows docs/prompt_templates/codex_exec_plans.md. The current
turn is authorized through scientific acceptance and a concrete UI specification
and static layout proposal. Human approval is required before product implementation.

## Purpose / Big Picture

Produce a physically defensible generated-soil Roads parameterization within an
order of magnitude of FSWEPP2 Roads/WEPP2010, using the released 261029 engine.
Then present the exact supported configuration fields and layout for human review.
The eventual product is a run-scoped edit/save/reset workflow, not a CSV editor.
This execution stops at the explicit human specification/layout gate.

## Progress

- [x] Clean candidate broad native/Disturbed/Roads gates executed; all physical checks pass, magnitude target remains unmet.
- [ ] Complete Cedar watershed semantic/particle/source review and candidate disposition.

- [x] D2 confirms EPLANE array-origin defect; U2/U3 physical panels and clean-output parity pass. Native candidate implemented with 13 permanent tests and proposed ADR-0119.
- [x] Complete native, Disturbed and Roads development gates; Cedar review remains separately tracked. No released binary or parameter adoption.

- [x] Reconcile native release: source 631aed1d1, matched 261029 pair reviewed and pushed.
- [x] Existing road-cap candidate passes 96/96 development cases with physical audits.
- [x] Record human UI specification/layout gate and unchanged scientific criteria.
- [x] Freeze continuation manifests and verify seven-development/six-withheld split.
- [x] Rebaseline generated-role, erosion and road-cap treatments on 261029 (384 cases).
- [x] Complete minimal-rule ablation (cap-only fails loam group) and 294 production-builder readbacks.
- [x] Execute the 840-case five-climate development matrix; reject candidate (740 magnitude, 822 physical passes).
- [x] Retain and independently replay fixtures for daily-water and sediment-output failures.
- [x] Operator authorized native accounting ablation; released engine remains the comparator.
- [x] Complete bounded native remediation and independent scientific acceptance (U10).
- [x] Finish revision 2 release integration: WEPPpy c28e30351, native 0df4c9227; exact pair frozen.
- [x] Recompute all 840 paired boundary budgets through Rust; matched inputs/output hashes and net-exchange identities pass.
- [x] Execute declared 111-case same-engine legacy-soil control: all physical checks pass; 76/91 original misses meet magnitude criteria with legacy control soil.
- [x] Execute 333 fill/buffer erosion-anchor runs and 98 runtime factorial runs; verify all recorded hashes and soil changes independently.
- [x] Complete 111-case soil/hourly factorial: 208 new runs, 236 reused cells; all 444 native audits reproduced. Reject hourly-off as a standalone candidate.
- [x] Trace all seven source restrictions; execute 52 no-detected boundary-flag cases and independently verify paired artifacts. Reject: zero recovered misses, five native funding failures.
- [x] Reproduce and instrument the five PMET-on no-boundary failures and controls: 70 exact status/output comparisons; daily requests already exceed initial stock.
- [x] Execute O4 shadow ledger: 26 exact-parity replays, 185,824 states, reject 179 negative outflows.
- [x] O5 reconciles matching-stage stocks; declare O6 attribution specification.
- [x] O6 attribution isolates QINF discontinuity; predeclare and execute U1 continuity screen, 12/12 full-period completions.
- [x] D1 supports scalar domain; local source audit rejects U1 as standalone multi-OFE repair.
- [x] D2 narrowed to confirmed EPLANE origin correction; U2/U3 controls and broad development gates executed. Cascade redesign deferred.
- [ ] Complete additional native geometry/routing stress validation after accounting repairs;
  core five-climate/four-design/surface/traffic/seven-material research panel is complete.
- [ ] Freeze successful rules, then execute six-material withheld validation.
- [ ] Complete disposable full-project native/output validation and scientific review.
- [ ] Draft parameterization ADR, configuration specification and static layout.
- [ ] Present concrete specification/layout for human approval; do not implement.

## Context and Orientation

Work in /workdir/wepppy on the existing master branch. Large native artifacts
belong under /wc1/runs/ro/roads-parameterization-program-20261030; new batch roots
must not overwrite earlier studies. Canonical native checkout is
/workdir/wepp-forest-release-20261009. Final native repair source is `ba9f2ad91b5165d5cd2954bd64b5df608798541e`;
independent acceptance is retained in the native accounting package. The owner
explicitly authorized replacing undeployed 261029 with artifact revision 2.
Installed watershed SHA256 is `819b91721f67c4a86a5ecea14c5beb840e9a705025da2a2cedf2b97a5e067715`;
hill SHA256 is `21d8480041d2efed942abb8471271ce1a11c5f72190d45c0c42dbe0028c019ed`.
Original identities remain in the reissue package. Regenerate matched outputs;
the shared release filename is not evidence of byte compatibility.
Legacy 2010 SHA256 is a12976166deb2b2d7c9adc0e0f23bac24d54057031a5072b4bb0a176c7c730b8.
Keep historical 261026 results as controls; do not relabel them as current.

Original declared materials are artifacts/design-v1.json: seven development and
six withheld profiles, distinguished by semantic material hashes. Withheld IDs
are 1718472,53975,1718476,665770,2711196,658566. Do not inspect their native outcomes
before freezing final candidate rules. Prior five climates are development data:
site, Birmingham, Denver, Flagstaff and Charleston.

Existing experiments are under /wc1/runs/ro/roads-parameterization-program-20261029.
project-runtime-screen-v2 contains roles/erosion/rock decks;
engineered-surface-screen-v1 contains the road-cap deck. The native timing package
retains the successful 261029 96-case replay. These are three-OFE research profiles,
not proof of production builder or full-project parity. Production builders remain
legacy-template based; no generated-soil default has been implemented.

Use tests/roads/roads_matrix.py production builders and tests/roads/roads_project.py
full-project precedent. The source specification is
wepppy/nodb/mods/roads/specification.md. FSWEPP2 source/reference resources are in
/workdir/fswepp2 and the earlier frozen benchmark; inspect hashes before reuse.
The old program plan and experiment history remain in Git at af33b72b8 and the
immutable experiment artifacts. This plan supersedes its obsolete blocked status.

## Milestone 1: frozen continuation and repaired-engine rebaseline

Write a new design version preserving old manifests. Hash rules, engine, source
soils, runtime settings and script. Record existing no-UI/default behavior as
controls, never as candidates. Reexecute the 96 known configurations on 261029
with generated roles only, road erosion coefficients only, road-cap candidate
and matched legacy-soil control. This isolates whether the engine repair removes
the need for some parameter changes. Compare to hash-verified 2010 reference
outputs and inspect every failure; do not repeat the entire earlier search.

## Milestone 2: production preparation and development confirmation

Build real road/direct/buffer/rutted/unrutted configurations through existing
production methods in disposable contexts. Experimental generated-soil replacement
may happen only in the isolated study adapter, with strict before/after readback.
Preserve road/fill/buffer ordering, surface/traffic/ditch distinctions, management,
area and outlet identity. Generated material, deeper horizons, restriction provenance
and 200 mm normalization remain intact. Reuse generated bare/forest role preparation
with explicit erosion/cap transformations; do not silently copy legacy soils.

Use small paired checks before expanding to five climates, all four road designs,
both surfaces, all three traffic levels and seven development profiles. Declare
geometry stress cases before running them. FSWEPP-matched geometry and production
geometry are separate evidence layers; unequal outlets/areas are not numerical
comparison failures to fit away. Verify runtime sidecars and climate settings; a
fixed site PMET bundle across climates is only a controlled sensitivity experiment,
not climate-specific calibration. Resolve configuration-sensitive material issues
before the full panel. Keep failed cases in denominators and retain raw artifacts.

## Milestone 3: independent validation and physical acceptance

Freeze the simplest successful rule set and exact candidate before using the six
withheld materials or withheld geometry combinations. Apply acceptance.md unchanged:
95% overall and 90% per major group within 0.1–10 for references above 1 kg/year;
small loads use max(1kg/year,10*reference) without a lower ratio bound. Declare
area-aware small-load thresholds before changing geometric scale. Weight material
groups equally and report all intersections, bias and worst cases. No native stop,
negative sediment, nonfinite/incomplete output or unexplained accounting mismatch
is acceptable. If holdout outcomes guide revision, consume that holdout and choose
new reserved material before independent retest. No per-climate/case correction.

Audit rainfall/runoff, saturation and deep/lateral flow partitions, annual/event
sediment and output definitions. Successful numerical agreement is not field
calibration or universal watershed closure. Complete a disposable real-project
preparation/run/report case and independent scientific review of concrete evidence.

## Milestone 4: reviewable configuration design and human gate

Only after scientific acceptance, draft an ADR and exact configuration specification:
fields, units, applicability by role/design/surface/traffic, allowed ranges, defaults,
overrides, version adoption, save/reload/reset, readonly/authorization/CSRF, stale
results and provenance. Prepare a static layout using familiar WEPPcloud controls.
Label custom values separately from validated defaults. Document migration/rollback
and proposed contracts without implementing production behavior. Preserve existing
projects until explicit adoption. Obtain technical reviews where authorized, then
present specification and layout to the human owner. Stop dependent implementation
until explicit approval; this is an owner-required gate, not inferred caution.

## Concrete Steps and Validation

Use wctl exec weppcloud python for native study drivers and wctl run-pytest for
focused checks. Drivers must refuse existing roots or verify complete hashes before
resuming. Retain executed source, inputs, binary identities and physical readback.
Add each actual command/result to tracker.md. Test transformations for nonmutation,
role/deeper-layer preservation and configuration semantics. Run appropriate broad
regressions when substantive executable/harness changes are complete, not after
every unchanged batch. Use wctl doc-lint for changed documentation.

## Surprises & Discoveries

D2: EPLANE received a zero-based length array as one-based, shifting lengths relative to coefficients. Homogeneous probes hid the error. Corrected integral probes pass 8/8 versus released 2/8.

D1 confirms uniform-plane continuous formula independently but finds 0.027406 m³
unsupported Hortonian source in U1. Soil funding alone cannot justify that flux.

O6 rules out stale stold in 4,145 comparisons and locates five failures in
recession differences. U1 continuity trial completes all twelve cases but retains
one funded negative exchange; completion alone does not establish physicality.

O5 identifies O4 bookkeeping error: potential plant use subtracted before SWU
withdrawal. Matched stages reconcile to 0.000312 mm; original native stops remain.

O4 rejects monotone recession ownership (179 negative outflows). The stock/sink
diagnostic remains unreconciled, with maximum residual 2.400805 m³; this is not
evidence of a new native defect. See `artifacts/native-shadow-ledger-findings.md`.

Native observers prove the five failing daily requests exceed stock before
hourly spending. Upstream recession reduces actual incoming runoff; connected
equivalent-plane output does not receive the same reduction on these events.
O0/O1/O2/O3 preserve exact native outputs and statuses across 70 replays.


The seven materials separate into two lithic-metadata, two low-Ksat mineral and
three no-detected classes. All emit an enabled 10 m boundary; /1000 is a documented
heuristic. Disabling only the flag for the 52 no-detected cases recovers zero
misses and triggers five native funding stops, with 0.131–0.180 mm deficits.
These are materially larger than the earlier Penman roundoff-scale failures.


The complete soil/hourly factorial needs 208 new runs, correcting the earlier
111-run estimate (only 14 legacy-off cells existed). Generated hourly-off recovers
21/91 misses and loses one control; legacy-off passes 108/111 (three remaining
labels alias one input). All 444 cell audits reproduce. Generated lateral-flow
responses are much larger; all seven materials emit an enabled lower boundary
with a 10 m thickness term. This is a hypothesis driver, not proof of bad geology.


The completed role/runtime panel recovers only 10/91 misses using both-role
erosion anchors, despite exact WAT parity in all 333 runs. Hourly-off recovers
8/9 distinct legacy residuals with PMET/snow fixed. Six hourly-on/Penman runs
stop at tiny negative `HOURLY_WATER_UNMET` demands; all remain failures.


2026-10-31: three of six excessive meaningful-load cases have zero road export
in both models; downstream exchange is the largest difference in all six. The
same-engine full legacy-soil control brings 76/91 original misses within criteria,
but leaves nine distinct failing inputs. Neither uniform road scaling nor a
soil-only explanation covers the remaining evidence.

2026-10-30 continuation: 16 uncapped cases per lane stop at the water inventory
guard. Exact replay establishes a 5.035662 mm full-day deficit before other sinks
in the Birmingham sand fill OFE, so retiming alone cannot repair it. Cap and
legacy controls pass 96/96; expanded cap pilot passes 28/28. At that checkpoint the independent
scientific reviewer required a daily-coupling explanation before acceptance;
the subsequent native ablation identified and repaired equivalent-melt support. See
artifacts/continuation-findings.md and artifacts/unmet-budget-v1.json.

The prior best treatment was blocked by native local-input/timing/ET defects, now
repaired. Passing 96 insloped cases does not cover outslopes, low traffic, all five
climates or independent material. Earlier labeled holdouts duplicated material;
only the reserved six distinct material hashes are withheld. Several active docs
still described 261026 and a pending native decision; the explicit release amendment
and this continuation supersede those statements without altering old evidence.

## Decision Log

D2, 2026-10-31: defer cascade redesign in favor of confirmed minimal array-origin repair plus independently supported scalar continuity. Advance U3 as an unreleased source candidate; retain origin-only control. See proposed ADR-0119.

D1: reject standalone U1 promotion; retain supported scalar component and
continue D2 local surface ownership before broad adoption gates.

O6/U1: retain isolated U1 as experimental, with model gap/scientific review
disposition. No source promotion, parameter adoption or released binary change.

O5: retain released behavior. Proceed to O6 storm/recession attribution per
`artifacts/native-joint-ownership-experiment.md`; accounting closure does not
validate a new infiltration law.

2026-10-31 O4: reject recession-only shadow correction. Reconcile observation
boundaries before a joint GRNA/QINF behavior contract; no guard/default change.

2026-10-31 native observation: retain the guard and released engine. Proceed to
a shadow GRNA/QINF ownership ledger, preserving geometry and event support,
before a single scientifically contracted behavior lane. Do not restore water
already assigned to upstream infiltration. No parameter retuning around failures.


2026-10-31 restriction audit: retain current soil and runtime defaults; reject
the no-detected flag endmember. Prioritize an isolated native funding trace on
the retained five-deck panel before further boundary tuning. No guard relaxation
or automatic binary adoption. Current ledger: `artifacts/candidate-ledger-v4.json`.


2026-10-31 soil/hourly completion: reject a global runtime switch. Trace source
restriction classes, missing-information defaults and native bottom conductance
before choosing hydraulic parameters. Preserve all restrictions pending evidence;
do not fit them to sediment. Current ledger is `artifacts/candidate-ledger-v3.json`.


2026-10-31: Reject legacy erosion anchors as a standalone candidate; retain
current runtime defaults. Prioritize the generated-soil/hourly-mode interaction
with PMET/snow fixed before hydraulic calibration. Preserve alternate-runtime
failures for separate native guard investigation; do not relax physical gates.


2026-10-31, diagnostic decision: retain the generated-soil goal and current engine.
Prioritize downstream role-specific erosion/hydraulic separation, with runtime
controls for residual legacy mismatches. Reject treating legacy substitution as
a successful candidate; its purpose is causal separation of full soil treatment.

2026-10-30, owner: reissue the undeployed 261029 identity with the accepted native
repairs. Preserve original identities, report revision 1, project defaults and
the human UI gate. Final native acceptance does not relax magnitude criteria.

2026-10-30, operator: continue recommended validation, with broad forest authority
through a human-gated UI specification/layout. No product implementation before
that review. Existing acceptance thresholds, generated-soil normalization and
deployment boundary remain unchanged.
2026-10-30, Codex: rebaseline on repaired engine before broad tuning to avoid
retaining unnecessary parameter adjustments; keep withheld materials untouched
until final rules are frozen.

2026-10-30, continuation disposition: do not promote the candidate or consume
withheld data after broad failures. Retain the strict inventory guard and pinned
release. A separate native daily-runoff and event-output ablation is the next
scientific scope decision; no posterior material/climate exclusions or tolerance
changes. Independent implementation review closed the normalized-legacy control
confound with 96 exact-deck controls and corrected attribution.

## Outcomes & Retrospective

Native gates: 1073 tests and 18 watchlist cases pass; Disturbed 99 pass. Roads physical gate 840/840; magnitude 713/766 meaningful and 31/74 small, two recoveries and seven regressions. All 864 Cedar hillslopes complete; watershed and semantic/particle audit pending. No release or parameter adoption.

Current: ledger v10 and `artifacts/native-D2-geometry-findings.md`. Both twelve-case lanes complete with zero negative linked FIN and unfunded requests; clean candidate exactly matches all U3 outputs. Native full gates running; Disturbed/Cedar/Roads magnitude rebaselining remains. Earlier D1/U1 rejection remains historical evidence.

Previous D1 checkpoint: ledger v9 and `artifacts/native-domain-review-findings.md`. D1 completes
63 reference solves, 42 scalar calls, zero new full WEPP runs. No adoption.

Current: ledger v8, O6/U1 findings in `artifacts/native-ownership-findings.md`.
24 observation parity runs and 12 candidate full-period completions. Physical
formula domain and one signed exchange remain unresolved before broader gates.

Current: O5 complete, ledger v7; 24 additional exact-parity executions and
185,819 completed states reconciled. See `artifacts/native-stage-ledger-findings.md`.
No scientific candidate adopted; UI and withheld gates remain.

O4 completed and rejected; current ledger is `artifacts/candidate-ledger-v6.json`.
All 26 added native runs preserve expected statuses and outputs. Magnitude
acceptance remains unmet, withheld materials unused, and UI implementation gated.

Native observation milestone completed in the new 20261031 native package;
self-contained ten-case fixture and raw archive retained. See
`artifacts/native-funding-observation-findings.md`. No native remedy or release
is established; prior C3 rejection remains relevant to the next lane.


Restriction audit and bounded flag control complete: 47/52 native cases pass
physical checks, 0/51 misses recover, one passing control remains passing. All
52 paired artifact inventories and exact soil changes independently verified.
See `artifacts/restriction-provenance-findings.md`; canonical provenance wording
is clarified in `wepppy/soils/ssurgo/ssurgo.md`. No production parameter changed.


The four-cell soil/hourly comparison is complete and independently re-audited.
See `artifacts/soil-hourly-interaction-findings.md` for paired sediment/water
results, figure, source context, corrected run count and continuation rationale.
Acceptance remains unmet; no default or withheld/UI gate changed.


Role/runtime diagnostic completed: 333/333 erosion runs and 92/98 runtime
runs passed physical checks; all 431 input/output inventories and soil changes
were independently verified. See `artifacts/role-runtime-ablation-findings.md`
for contrasts, limitations, failure disposition and the next bounded study.
No candidate accepted; full matrix, withheld and human UI gates remain open.


Resumed after release: completed 840 paired native boundary readbacks and 111
declared legacy-soil controls (90 distinct input sets). All 111 physical audits
pass; 76/91 original misses meet magnitude limits only in the diagnostic control.
Full generated-soil acceptance remains unmet. Retained 3,346 verified artifacts;
see `artifacts/role-attribution-findings.md` and the archive receipt. The next
experiments isolate downstream coefficients/hydraulics and nine residual runtime
comparisons. Withheld materials and product implementation remain untouched.

The bounded native accounting defects are repaired and independently accepted in
261029 artifact revision 2. The final U10 development panel passes all 840 physical
cases. Magnitude acceptance remains unmet: 719/766 meaningful-reference cases and
30/74 small-reference cases pass. Neither withheld evaluation nor a production
parameter default is accepted. The next justified study separates road production
from fill/buffer delivery for the retained high, low and small-reference misses.
The release pair and reviewed report are integrated; final operational suite and
retention checks belong to the companion reissue package.

The earlier 740/840 magnitude and 822/840 physical screen was a failed diagnostic
checkpoint. It led to committed native reproductions, not parameter changes that
concealed failures. All 294 builder readbacks remain limited preparation evidence.
Scientific model repair is not equivalent to completing this parameterization
program. The configuration specification/layout still requires human approval
before product implementation.

## Historical experimental checkpoints

The following records describe execution-time decisions. Current source selection,
acceptance and next steps are governed by the Progress, Context and Outcomes
sections above; old holds and unreleased-candidate labels are retained as history.

### Native ablation disposition — 2026-10-30

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

Native C4 diagnostic finished: 56 full simulations confirm C3 introduces
homogeneous-hill subdivision sensitivity (first-storm runoff 52.254→66.440 mm,
peak about 221→512–517 mm/h for 2/4 OFEs). Water changes are rolled back; the
separate event repair remains experimental. See native findings and C4 review.

Final native handoff: clean retained U2c build passes 669 native tests, both
host smokes and 13 watchlist cases. C3 water changes are rolled back; water repair
and Roads acceptance remain open. Archive receipts are retained in
artifacts/native-accounting-archive-receipts.json. No release/default/UI change.

2026-10-30: operator renewed broad authority to continue native ablation and
remediate. Canonical native active plan resumes with observation and isolated
forcing/storage attribution; production release and human UI gate unchanged.

### Native remediation continuation — U5c validation

Direct native tracing refuted the broad upstream-soil snapshot hypothesis on
the original failures. Two narrower defects were proved: equivalent daily melt
was fitted to the receiving OFE's shorter hourly support, and GRNA counted
nearer upstream storage repeatedly across three or more elements. The combined
C5a candidate completes 840/840 development cases, passes 837 accounting audits,
685 native tests and 99 Disturbed tests. Three remaining negative-sediment cases
expose cancellation in the legacy deposition equation near PHI=-2.

U5c carries the boundary derivative through the same analytic sediment equation,
with stable PHI=-1/-2 limits and a proved terminal root-search limit. Original
full-period inputs and independent producer/endpoint controls were committed
before candidate acceptance. The exact negative event becomes positive while
water output remains byte-identical in the isolated replay. Final U5c native,
840-case, Disturbed and fresh matched Cedar validation is underway.

See ADR-0114 and ADR-0115 and native package
`/workdir/wepp-forest-release-20261009/docs/work-packages/20261030-roads-native-accounting/`.
U3/C5a magnitude scoring is 749/840 under the frozen reference criterion; it is
diagnostic, below the program acceptance gate, and does not authorize changing
Roads defaults. Installed `wepp_261029` is unchanged. Configuration specification
and layout still require explicit human approval before UI implementation.

### Native U6 validation milestone (2026-10-30)

The native continuation now passes all 840 development accounting cases,
824 native tests, 99 Disturbed tests, 18 permanent hillslope watchlist cases and
both executable smoke checks. Stable bulk deposition and ENRICH particle sorting
repair confirmed cancellation/singularities without sediment parameter tuning.
All 840 water/soil output pairs match C5a; annual Roads sediment matches U5c.

Fresh U6 Cedar regenerates 864 hillslopes and all 24 watershed years. Converted
WAT fields and all 7,573,824 PASS particle records pass finite/nonnegative audits.
Outlet water changes +0.00002475%, sediment +2.749%; individual days change more.
R4 restoration of legacy channel storage is null for all 8,766 daily records.
R2 restoration of released event lifecycle remains in progress to distinguish
late-event timing from equivalent-melt duration effects before final disposition.

The magnitude gate is still unmet: 749/840 (89.17%), versus required 95% overall
and 90% per major stratum. No withholding split, acceptance threshold, Roads
parameter/default, installed binary or UI gate changed. Native source decisions
are recorded in ADR-0114 and ADR-0115; final evidence lives in the native
20261030-roads-native-accounting package. Finish scientific attribution and
archive verification before choosing the Roads continuation candidate.

### Native channel continuation: U9a validation

Independent Cedar attribution found a preexisting channel source amplification
and constant-discharge deposition defect after U6 passed the Roads physical
audits. The native package implements bounded U7/U8/U9a repairs with committed
red fixtures and 155 focused green tests. U9a completes 840/840 physical cases,
99 Disturbed tests and 18 watchlist cases; all seven Roads outputs, inputs,
metrics, soils and audits exactly match U6 across the 840 cases. Magnitude
therefore remains 749/840 (89.17%), below the unchanged acceptance thresholds.

Cedar scientific acceptance remains open: U7 source-only reduces outlet sediment
3.217%; diagnostic U9 increases it 179.765% relative to U6 while water remains
identical. Final U9a and independent channel attribution must distinguish
recovered sediment transport from any remaining defect before acceptance.
See native `20261030-roads-native-accounting/prompts/active/implementation_execplan.md`
and ADR-0116/0117. Preserve installed wepp_261029, withheld cases, Roads defaults
and the human gate on UI configuration specification/layout.

### Authorized release integration

The owner confirms261029 is undeployed and requests reissuing that identity with
updated release notes. Execute the active
[261029 revision2 package](../../../20261030_wepp_261029_rerelease/package.md)
for vendoring/publication only after native scientific acceptance. This scope
amendment supersedes the earlier no-release boundary; Roads parameter defaults,
withheld-panel rules and the human UI configuration/layout gate remain unchanged.

### Revision 2 checkpoint and continuation

The native accounting investigation accepts the bounded repairs in `wepp_261029`
artifact revision 2, source `ba9f2ad91`. The frozen U10 panel passes all 840
physical/accounting cases. Parameterization acceptance remains unmet: 719/766
meaningful-reference cases (93.864%) and 30/74 small-reference cases (40.541%)
pass; 749/840 is only a descriptive combined score. Annual exports match U9a at
reported precision. Six withheld materials remain unused; no Roads defaults or UI
have changed. See [U10 scoring](../../artifacts/U10-magnitude-summary.json) and the
[release integration](../../../20261030_wepp_261029_rerelease/package.md).

Next: with revision-2 release integration complete, investigate outunrut low-reference and
routing behavior using the frozen development panel and physically justified
controls. Preserve the separate small-load criterion. Do not fit around native
defects, consume withheld materials early or treat accounting success as magnitude
acceptance. UI specification/layout remains human-gated before implementation.

The next attribution study is specified in
[the U10 continuation recommendation](../../artifacts/U10-continuation-recommendation.md):
separate road production from fill/buffer delivery for high, low and small-reference
misses. The retained case inventory contains 41 meaningful underpredictions, six
meaningful overpredictions and 44 small-reference exceedances; a global multiplier
would move the opposing failures in incompatible directions. No new parameter
candidate or acceptance threshold is introduced by this assessment.

## Resumption after release — 2026-10-31 UTC

Execute this active program plan after completed revision-2 delivery. First use
`artifacts/role_boundary_assessment.py` to read the frozen 840 development cases
and their FSWEPP2/WEPP2010 references through the canonical Rust ELEMENT reader.
Verify native output hashes and matching climate, management and slope inputs.
Separate road-boundary export from fill and buffer net boundary exchange; group
by meaningful low/high, small-load exceedance and passing controls. This is
bookkeeping attribution, not tagged sediment provenance or a causal parameter
experiment. Do not change defaults, criteria, material split or native binary.

The next ablation must distinguish road production, fill contribution and buffer
retention, including same-modern-engine legacy-soil controls to separate engine
and soil effects. Keep the existing fixed-site sidecar limitation explicit;
regional climate runtime and broader geometry validation remain required. This
update closes the stale release prerequisite and resumes the scientific program
without implying magnitude acceptance or human approval of UI implementation.

The completed boundary readback places the largest net-exchange difference
downstream in all six meaningful high cases and 43/44 small-load exceedances.
Median defined road-boundary ratios are 0.899 (3 cases) and 0.584 (27 cases),
respectively; the other cases have zero road export in both models. This does not support
a uniform road-erosion reduction. Declare `legacy-soil-control-r2-declaration-v2.json`
before executing `legacy_soil_control_r2.py`: every development miss plus one
passing control per climate/design, replacing only the whole soil deck while
retaining exact modern engine/runtime inputs. Legacy soils are diagnostic controls,
not a proposed modern-soil default. No withheld data or threshold change.

### Completed resumption outcome

The 840-case role readback and 111-run same-engine control are complete; see
`artifacts/role-attribution-findings.md`. The control has 90 distinct consumed
input sets and all 111 physical checks pass. It brings 76/91 original misses
within their unchanged criteria; 15 failures map to nine distinct inputs. This
is diagnostic evidence for soil-role and runtime investigation, not acceptance
of legacy soils or a new generated parameter set. All 3,346 raw artifacts are
archived with verified member hashes. Updated decision: prioritize downstream
role-specific erosion/hydraulic separation, with explicit runtime controls for
the residual legacy comparisons; retain all existing broad/withheld/UI gates.

## Declared role and runtime ablations — 2026-10-31 UTC

Execute `artifacts/role_runtime_ablation.py` under this active plan. The erosion
study declares 333 runs: all 111 previous diagnostic cases with fill-only,
buffer-only and both-role legacy erosion anchors (ki, kr, critical shear).
Generated hydraulic properties, horizons, 200 mm normalization, restrictions and
road settings remain exact. Require unchanged native WAT hashes as a negative
control, alongside physical and magnitude readback. Anchors are diagnostic, not
new validated defaults; their actual role-wise bounds are frozen in the declaration.

The runtime study declares 98 runs: nine distinct residual legacy-soil inputs
plus one passing control per climate, crossed with seven nonbaseline combinations
of hourly mode, PMET and snow sidecar presence. Existing all-present baselines
complete the factorial. Source `infile.for` confirms absent PMET selects original
Penman, not merely a different coefficient; absent snow uses a 0 C threshold
rather than the fixture -2 C. Preserve soil and all other inputs. This separates
three mechanisms and interactions; absence is a controlled diagnostic, not a
climate-specific or production recommendation. No withheld material is consumed.

### Completed role/runtime outcome

The declared 431-run panel is complete and retained with verified archive member
hashes (`artifacts/role-runtime-archive-v1.json`). This revision records failed
alternate runtimes as failures and rejects coefficient-only promotion; see
`artifacts/role-runtime-ablation-findings.md` for the evidence and continuation.

## Declared soil-by-hourly interaction — 2026-10-31 UTC

Execute `artifacts/soil_hourly_interaction.py`: complete all four cells for the
111 existing diagnostic cases, holding PMET/snow present. Correct the previous
run estimate: only 14 legacy hourly-off cases exist, so 208 new runs are required
(111 generated, 97 legacy), with 236 verified cells reused. Removing only
`wepp_ui.txt` preserves all soil files and other inputs. Freeze declaration and
helper hashes before execution; retain failures and unchanged physical criteria.
Report grouped magnitude recovery/regression and paired signed sediment/water
interactions. No default change, new material selection or withheld inspection.
This is a selected diagnostic panel, not the full acceptance matrix.

### Soil/hourly completion

208/208 new runs completed and passed physical checks; 444/444 paired cells
independently reproduced from native outputs. Archive receipt:
`artifacts/soil-hourly-archive-v1.json`. This update records the rejected runtime
candidate and moves investigation to source-supported lower-boundary semantics.

## Lower-boundary provenance and no-detected-restriction control

2026-10-31: trace only seven development materials through frozen source headers,
SSURGO writer and native input/drainage code. Separate lithic metadata, low-Ksat
mineral truncation and no detected horizon. Preserve source hashes and explicitly
label header provenance as generated source evidence, not independent field data.
The documented /1000 bedrock proxy is a historical heuristic, not an inferred
unit bug. Keep existing 200 mm horizon normalization.

Declare a bounded 52-case diagnostic for the three no-detected materials
2711184, 2711250 and 1718494 already present in the 111-case panel. Change only
`res_lyr.slflag` from 1 to 0 in all three OFEs, leaving the stored thickness and
conductivity fields, all horizons/erosion properties, hourly/PMET/snow and native
binary exact. Native initialization ignores/zeros boundary inputs when flag=0.
This tests the imposed lower-boundary endmember, not proof of unrestricted
geology or a new default. Never apply it to mineral or lithic classes. Compare
paired water/sediment and unchanged physical criteria; retain all failures.
Prior boundary studies varied conductivity and encountered now-repaired native
failures; this is an explicit no-detected-class flag contrast, not a new fitted
conductivity multiplier. No withheld outcomes or production changes.

### Restriction audit completion

Completed and archived the source audit, 52-case flag contrast and independent
readback. This revision rejects another boundary-only remedy and records the
new substantive native funding failure class rather than treating stopped runs
as zero sediment. Receipt: `artifacts/restriction-boundary-archive-v1.json`.

## Active native funding trace — 2026-10-31

Executing native package
`/workdir/wepp-forest-release-20261009/docs/work-packages/20261031-roads-open-boundary-funding/`
and its `prompts/active/implementation_execplan.md`. Five failing plus five
passing self-contained fixtures reproduce all released output hashes. Isolated
O1/O2 observer builds preserve all outputs with observation off/on; daily
withdrawal exceeds start-of-day storage before percolation/lateral losses. O3
uses existing IRS markers to trace producer/runoff-basis differences. No native
behavior, released binary, parameters, withheld outcomes or UI changes.

Native observation handoff: `artifacts/candidate-ledger-v5.json` records the prior
ledger; `artifacts/native-funding-observation-archive-v1.json` verifies 1,669
retained files. Scientific milestone remains open; no repair/parameter adoption.

## O4 shadow ledger handoff — 2026-10-31

See `artifacts/native-shadow-ledger-findings.md` and v6 ledger. The next bounded
experiment reconciles actual stock/sink observation stages before a joint
GRNA/QINF local ownership contract. Shadow funding success is insufficient when
outflow is negative. No native behavior or release artifacts changed.

### 2026-10-31 final revision-3 scientific checkpoint

The user explicitly authorizes the same-name undeployed 261029 re-release.
[Delivery plan](../../../20261031_wepp_261029_rerelease_r3/prompts/active/rerelease_execplan.md)
tracks final metadata, vendoring and reviewed publication. Native scientific
acceptance binds the final dated pair: 1,095 native tests, 28 watchlist cases,
99 Disturbed tests, 840 physical Roads cases and 6,057 exact Cedar outputs.
Magnitude remains 744/840, so this acceptance does not promote a parameterization.
Resume exploration only after release delivery; preserve the existing success
criteria, withheld-material boundary and human UI specification/layout gate.
