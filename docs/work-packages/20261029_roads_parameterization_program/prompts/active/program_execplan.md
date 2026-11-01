# Validate modern Roads parameters and prepare a human-reviewed configuration design

This living plan follows docs/prompt_templates/codex_exec_plans.md. The current
turn is authorized through scientific acceptance and a concrete UI specification
and static layout proposal. Human approval is required before product implementation.


## Current: whole-hillslope design reviewed; prepare fresh execution

Current [candidate ledger v19](../../artifacts/candidate-ledger-v19.json) preserves the failed isolation and completed localization.

The roughness counterfactual remains failed on upstream isolation; its remaining
32 runs are stopped. Four observation-only replays now establish native coupling:
terminal flow duration changes upstream peaks and persistent rill widths, then
width-dependent friction changes runoff in the next storm. All 28 ordinary
outputs and four full-period state traces reproduce the retained modes exactly.
Both independent reviews pass. The fresh [nine-pair whole-hillslope response study](../../artifacts/buffer-roughness-hillslope-response-r4-plan.md)
has scientific and implementation design approval; execution requires the fresh
runner and four-run preflight gates. Physical correctness of the routing
approximation and initial 100 mm roughness remains unvalidated. Revision 4 is delivered; no parameter
candidate is accepted. See the [executed coupling findings](../../artifacts/buffer-roughness-coupling-localization-r4/findings.md).

The exact combined U12 native pair is scientifically accepted. The
[acceptance receipt](../../artifacts/param-u12-scientific-acceptance.json) binds the
completed evidence: 1,253 native tests, 28 watchlist cases, 99 Disturbed cases,
840 Roads and 348 downstream physical checks, and a fresh 864-hillslope,
24-year Cedar simulation. All 1,187 successful panel baselines retain identical
water and soil outputs. Cedar outlet sediment changes +1.20 kg over 24 years
against revision 3; its water/soil outputs are identical.

Two strict fraction predicates remain failed but have exact arithmetic
certificates. All 40,006 observed negative raw-capacity calls have quantified
terminal support; no unexplained support class remains. These are bounded
explanations, not changed tolerances or universal numerical guarantees. The
[mixed-reconstruction clarification](../../artifacts/param-u12-mixed-reconstruction-clarification.md)
defines the local error equation precisely without changing frozen evidence.

The authorized same-name `wepp_261029` revision-4 repository delivery is complete
in pushed WEPPpy commit `a5c40031a`; see the [delivery receipt](../../artifacts/revision4-delivery-complete.json). Native release commit is `1959d8f61`, with
source `b01a739957bef5aacf35b4a89bc13eddc9d94804`, watershed hash
`2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48`,
hillslope hash `9ef6b62677407a66255a2b95becc9f350c87ef8e4cf67ab4e543ddb89ed4a010`.
All 489 frozen build inputs match committed source. The build preceded that
commit; promotion preserves the exact tested bytes. Report approval and
application delivery are separate gates. No production deployment is implied.

Roads parameterization remains unaccepted: 713/766 meaningful references and
31/74 small references pass, unchanged from revision 3. The hydraulic factorial
is complete and rejected; paired event supply/retention analysis now tests which
physical process needs the next controlled experiment.
The six withheld materials and human UI specification/layout gate remain intact.

## Latest continuation findings

The 928-cell factorial is complete; no parameter candidate is accepted. All
116 exact-revision-4 legacy-soil anchors also completed. Their 91 apparent
particle/bulk mismatches were a research-audit fixed-width parsing defect:
independent replay clears all 91 in both revision 3 and revision 4, with unchanged
bounds (5,887 EVENT records per generation). See the
[independent parser disposition](../../artifacts/review-legacy-particle-disposition.md). Preserve original evidence;
the corrected v2 auditor now covers all 2,348 overlapping panel records,
with zero mass flags and unchanged strict fraction findings. The third factorial
fraction flag has a new exact-state arithmetic certificate; its strict predicate
remains failed. The paired event ledger is complete and independently accepted for observational
use: 116 cases, 232 lanes, 4,067,424 independently checked lane/OFE-day rows and
8,352 annual flux comparisons. All 43 small-reference misses export more with
the conditioned generated profile; 28 have less incoming sediment at the buffer.
On 115 printing-separated case-days, generated buffer surface outflow is higher;
legacy surface outflow is zero on 101. These are 19 distinct climate/date pairs.
The same annual pattern occurs in 13/18 meaningful passing controls, while all
48 meaningful underpredictions have lower generated export. No uniform parameter
correction is justified. See [findings](../../artifacts/event-supply-ledger-r4/findings.md).

The nine-pair buffer-process study is complete and independently accepted for
bounded observational interpretation. All 18 full-period O3 runs preserve all
126 ordinary output files byte-for-byte; physical, strict particle and trace-coverage gates
pass. Independent readback covers 133,468 trace rows, 90 present sediment rows,
108 water rows, 2,592 hourly REAL accumulations and 21 runoff additions. See
[findings and paired figure](../../artifacts/buffer-process-interpretation-r4/findings.md).

Two Denver contrasts have no GRNA excess in either lane, yet generated hourly
surface return accounts for all outlet surface water (14.653 and 39.034 m³).
Generated outgoing bulk sediment equals incoming mass there; legacy deposits
it. Six generated buffer histories reach 6 mm roughness while their legacy
controls retain 100 mm. The three underprediction controls retain equal
roughness across lanes and still diverge in storage and exchange. Whole-profile
confounding remains; neither a universal adjustment nor a new defect is proven.

The subsequent counterfactual failed upstream isolation, and four diagnostic
replays established native coupling. Next use a fresh whole-hillslope response
declaration on the same pairs, holding other inputs and bulk-density handling
fixed. Preserve both discrepancy directions and passing controls. This remains
a model-sensitivity experiment, not a depression-storage-only intervention or
an accepted parameter rule.

The O1 missing-calendar build and O2 lazy-reader dependency failure remain
retained; O2 includes one completed legacy run, not an accepted pair. The O3
correction eagerly binds existing reader modules and reuses the same observer
binary. [Retention coverage](../../artifacts/buffer-process-observation-r4-retention-coverage.json)
verifies 3,983 raw files across the original archive and a two-file reviewer-failure
supplement. The original archive was not rewritten. The core design covers
outsloped/unrutted roads plus one rutted control, not all four design mechanisms.

Application coverage is complete: 12,533 passed and 422 skipped across all
12,955 unique test IDs. Retained failures identify a preexisting Redis test-order
defect and a Roads concurrency test deadline exceeded under load. Neither invokes
the native binary. Independent review recommends the scoped native release
handoff; do not claim one clean original suite or closure of the order defect.

## Purpose / Big Picture

Produce a physically defensible generated-soil Roads parameterization within an
order of magnitude of FSWEPP2 Roads/WEPP2010, using the released 261029 engine.
Then present the exact supported configuration fields and layout for human review.
The eventual product is a run-scoped edit/save/reset workflow, not a CSV editor.
This execution stops at the explicit human specification/layout gate.

## Progress

- [x] Draft the [roughness-persistence counterfactual](../../artifacts/buffer-roughness-counterfactual-r4-plan.md): 18 off controls and 18 persistence runs, full periods, unchanged profiles and fixed nine pairs. Retain mature-forest management metadata provenance separately.
- [x] Freeze the scientific and implementation preparation-design reviews. Density/porosity have exact source-supported invariants; ridge height and residue-dependent decay remain observed endogenous responses. No source implementation or execution is accepted by those design receipts.
- [x] Complete exact source/build/runner reviews and four full-period u1b preflight executions. Individual runtime/accounting gates pass, but modern upstream outputs differ: the paired isolation gate fails and the remaining 32 runs stay unexecuted.
- [x] Execute and independently review all four [coupling localization replays](../../artifacts/buffer-roughness-coupling-localization-r4-plan.md): 28 ordinary outputs and four full-state traces exact; executed duration/peak/width/friction/runoff path established. Original isolation remains failed.
- [x] Predeclare and independently review the fresh nine-pair whole-hillslope response experiment, permitting observed endogenous coupling while preserving exact off/null/density/input and physical gates.
- [ ] Bind and independently review the fresh runner, complete four-run preflight, then execute the remaining 32 only if all declared gates pass. Retain all outcomes; stop after this single rule.
- [x] Read and independently verify all 315,576 published SOIL rows for the nine frozen pairs; fresh v3 conversion binds the actual Rust library and preserves source artifacts. Archive all three attempts with all 65 members verified.
- [x] Accept exact U12 native pair after complete scientific, source, residual and Cedar review.
- [x] Verify all 489 retained build inputs against committed source b01a73995; retain complete verified final candidate archive.
- [x] Complete independent revision-4 PDF/manifest approval, exact-byte delivery, host/container smokes and actual selected hill/PASS/watershed/reader checks.
- [x] Complete all 12,955 unique application test IDs through declared shards/replays; retain original failures and baseline test-order defect.
- [x] Commit/push reviewed WEPPpy revision-4 delivery as a5c40031a; no production deployment.
- [x] Predeclare and independently verify the 928-cell hydraulic factorial, all 11,136 inputs, 3,248 reused native outputs and 70 effective dependencies.
- [x] Complete all 928 factorial cells and fresh log/runtime/accounting verification; independent paired contrast review rejects parameter promotion.
- [x] Complete versioned particle audit repair, 20 regression controls and 2,348-case readback; preserve all frozen evidence and unavailable diagnostic values.
- [x] Complete 116 exact-R4 legacy-soil anchors; diagnose 91 false particle flags as fixed-width audit parsing.
- [x] Complete and independently review all 116 paired event ledgers; archive v1/v2 failures and verified v3.
- [x] Predeclare nine paired buffer-process cases and independently reproduce seed eligibility/selection.
- [x] Freeze and independently review actual variable-unit map, private observer patch and 977 baseline inputs; 103 observation tags across 11 source files accepted for isolated build.
- [x] Complete O2 isolated build and runner review with all 978 build inputs bound. O1 stopped before compilation because staging omitted the required sibling calendar source; retain both attempts.
- [x] Complete O3 pair preflight with 547 stable dependency bindings. Retain O2's one successful legacy run and blocked generated lane as an incomplete pair; the correction eagerly binds nine lazily imported audit modules without changing the observer binary.
- [x] Execute all 18 O3 full-period runs: 126 ordinary output files exactly match revision 4; all physical, strict particle and trace-coverage gates pass.
- [x] Complete independent full runtime and scientific review, bounded process reconciliation and raw retention; no parameter ablation in this observation study.
- [x] Complete independent source-free publication and actual documented reproduction checks; retain 34 interpretation/replay files in a separate verified archive. The regenerated PNG is byte-identical; rerunning into existing destinations fails without changing them.
- [x] Predeclare/review the full-period roughness counterfactual with fixed other inputs and density handling. Its first-pair isolation gate failed; broader validation is not authorized under that failed gate.

- [x] Clean candidate broad native/Disturbed/Roads gates executed; all physical checks pass, magnitude target remains unmet.
- [x] Complete Cedar watershed semantic/particle/source review and revision-3 delivery.
- [x] Recompute final revision-3 road/fill/buffer attribution for all 840 cases.
- [x] Execute 116 same-engine whole-legacy-soil controls:79/96 misses recovered;
  all 20 passing controls retained. All 116 native audits recomputed; 3,037 retained files rehashed.
- [x] Execute the 16-input runtime bridge: 112 new runs, 107 physical passes and five explicit native guard failures.
- [x] Complete the generated/legacy by hourly/daily comparison: 196 new runs, all 464 labeled cells physically verified; reject global hourly-off (26/96 recovered, two control regressions).
- [x] Read back seven generated role profiles and first-day native states; retain source density/retention coupling as a hypothesis.
- [x] Complete seven-material/21-role/96-horizon source audit and 14 exact-parity initialization observations.
- [x] Execute 348 predeclared incremental road-pore/conductivity runs; fresh physical audits all pass, 24/25 misses recovered and all 20 controls retained. Seven coupled observation replays have exact output parity.
- [x] Attempt legacy format bridge: seven physical passes, zero exact output matches; reject representation and do not execute mixed-role substitution.
- [x] Execute and freshly verify 348 same-format downstream conductivity controls: 347 physical passes, reject standalone treatments on regressions.
- [x] Retain DEPEND full-run fixture, exact failed-output replay, GDB locals and two scalar reproductions with independent interior-root reference.
- [x] Execute DEPEND G1 source repair and independent reviews; 1142 native, 28 watchlist, 99 Disturbed and 840+348 prior physical audits pass. Expanded particle closure fails on baseline discrepancies; withhold promotion.
- [x] Complete six exact-output-parity particle/source observations; identify omitted EROD intervals before the next grid point.
- [x] Execute separate EROD/RUNGE/capacity/inflow/wet-domain ablations; retain independent counterexamples and rejected lanes.
- [x] Freeze U11 source/binary pair after209 targeted tests, four full-period seeds and independent reviews.
- [x] U11:1238 native,28 watchlist,99 Disturbed and840+348 prior physical gates pass; fresh Cedar complete, water unchanged, sediment+1.20kg/24years.
- [x] Confirm real PARAM sign defect with five exact-output-parity producer observations.
- [x] Execute U12:15 scalar controls, three separate four-seed lanes, four exact-parity observations; material negative capacity removed.
- [x] Complete exact-U12 broad gates; retain quantified terminal residual and exact fraction arithmetic certificates before promotion.
- [x] Explain original residual fraction-sum flags and quantify negative varying-capacity exposure; preserve strict predicates and exact certificates.

- [x] D2 geometry/recession repair accepted and delivered as revision 3;
  permanent regression coverage and accepted ADR-0119 retained.
- [x] Complete native, Disturbed, Roads and Cedar gates; exact revision-3 pair
  released. No Roads parameter defaults adopted.

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
belong under /wc1/runs/ro/roads-parameterization-program-20261031; new batch roots
must not overwrite earlier studies. Canonical native checkout is
/workdir/wepp-forest-release-20261009. Current compiled inputs match source
`b01a739957bef5aacf35b4a89bc13eddc9d94804`; native delivery is `1959d8f61`,
WEPPpy release delivery `a5c40031a`. The accepted undeployed artifact revision is 4.
Installed watershed SHA256 is `2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48`;
hill SHA256 is `9ef6b62677407a66255a2b95becc9f350c87ef8e4cf67ab4e543ddb89ed4a010`.
The current acceptance and application-coverage limitations are recorded above.
Prior revisions remain historical controls; never mix their PASS/output artifacts.
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

- Executed localization closes the native feedback: day 233 buffer runoff disappears under the intervention, changing the terminal flow plane from buffer to fill. IRS assigns the terminal duration upstream; changed peaks alter persistent widths. On day 243 those exact widths change friction and routing ALPHA; all other observed upstream QINF operands are bit-identical. This proves model coupling, not physical correctness of shared-duration routing or the roughness treatment.

- The modern off/on pair has real upstream peak/duration/width changes on year 4/day 233, before water and residue differences. Density, porosity and upstream RRC/RH remain exact. IRS has an explicit connected-group upstream duration/peak assignment; persistent rill width can feed the next storm's friction and recession calculation. At the failed-preflight stage this was only a source-supported mechanism; the subsequent localization above establishes its execution. Neither result demonstrates a new defect or physical realism.
- The first counterfactual preflight ran only legacy O4, with seven exact ordinary outputs and a passing physical audit, then stopped on a coverage error: friction calls also occur inside IRS, so their global count cannot equal PARAM entries. Retain that attempt and the frozen first independent reader; use a versioned, source-backed phase-window check with a regression for legitimate additional hydrology calls. No U1 outcome or model defect follows from this harness failure.
- The RRC intervention reaches crust/effective conductivity, critical shear, friction, interrill delivery, depression storage and snow/thermal readers. At this panel's configured initial roughness, the existing interrill roughness factor is zero. A successful persistence counterfactual therefore would not prove a retention-only explanation or validate that roughness as a production default.
- Two Denver target contrasts have no GRNA excess in either lane, but hourly surface return supplies all generated outlet water. Equal-roughness underprediction controls still diverge in storage/runoff/exchange. Roughness also affects derived erosion corrections, so a roughness-only intervention cannot be described as depression-storage-only causality. The complete profile comparisons do not identify a single correct coefficient.

- The nine fixed observer pairs have legacy buffer roughness of 100 mm throughout. Six conditioned generated profiles decline to 6 mm; the three selected underprediction profiles retain 100 mm. This is post hoc descriptive context, not causal evidence. The SOIL consolidation branch and IRS depression-storage operands require native observation. See artifacts/buffer-published-soil-context-r4.json.

- Exact-R4 paired outputs shift the next question toward buffer runoff support: all 115 printing-separated lower-incoming-sediment/higher-export case-days have higher generated surface outflow, including 101 with zero legacy outflow. Higher printed Keff does not isolate layerwise infiltration or storage; whole profiles differ. The modern lane is the conditioned U12 erosion_road_cap candidate, not raw SSURGO output.

- The legacy anchors expose an audit parser defect: adjacent F7.3/F6.3 ELEMENT fields can merge under whitespace splitting. This aliases QRain as SedLeave. Source-defined fixed widths clear all 91 false mass flags in both engine generations; production interchange already uses fixed widths.


Final review clarified the terminal error equation: it compares the mixed clipped-capacity/raw-rate reconstruction with the consistent clipped solution, not two ordinary raw/clipped ODE solutions. The bound and engine remain unchanged; the clarification is retained separately so frozen acceptance hashes remain valid.

U11 is held: PARAM loses a small positive continuity quantity in REAL arithmetic,
then selects the wrong sign for its zero denominator. Retained operands and
U12 predeclaration are in artifacts/erod-subgrid-ablation-plan.md.


Actual ROUTE fixtures prove that small nonzero inflow used a no-inflow
approximation, single capacity evaluation lost precision across consumers,
and DEPEQS changed caller-owned wet coordinates. U11 closes209 targeted
references; broad acceptance remains separate. A raw-versus-clipped deposition
forcing mismatch needs actual exposure/variation evidence, not assumptions
from negative coefficients alone.

EROD U1 independent review exposed shared transition errors: initial equality
is not immediate deposition, and legacy RUNGE can return inaccurate stiff
loads. U2 corrects nine of15 expanded scalar failures; six stiff cases remain.

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

- 2026-10-31: both independent actual readbacks accept the four-run localization for bounded interpretation. Proceed to a fresh, reviewed whole-hillslope sensitivity declaration because native feedback makes the original upstream-isolation criterion incompatible with this intervention. Keep that original campaign failed and all global magnitude/physical criteria unchanged; do not promote 100 mm roughness or call the observed routing behavior a defect.

- 2026-10-31: retain u1b as a failed upstream-isolation experiment and stop its remaining 32 runs. Authorize four separately predeclared observation-only full-period replays at the first changed storm and next runoff, with exact same-mode output parity. Do not silently relax the failed criterion; a subsequent whole-hillslope-response campaign requires a new reviewed declaration.
- 2026-10-31: proceed with the recommended counterfactual under the operator's continued authorization. Change only the declared buffer roughness-conditioning path; preserve density handling, generated profile lineage, reference comparisons, withheld materials and the UI human gate. Review the insertion point before execution so all dependent hydraulic and erosion calculations see a consistent state.
- 2026-10-31: accept O3 for bounded observational interpretation after exact output parity and independent runtime, boundary and scientific review. Choose a separately declared roughness-conditioning-only counterfactual next; preserve density, other inputs, both error directions and passing controls. Do not manipulate density to force the roughness branch or treat legacy behavior as the physical target.

- 2026-10-31: add published SOIL history as supplemental context without changing frozen seeds or execution design. Preserve v1/v2 provenance attempts and use a fresh v3 conversion binding the actual native callable module; facade identity alone does not identify the Rust reader.

- Accept the 116-case ledger for observational accounting only. Before further tuning, observe actual storm-time buffer hydrology and sediment processes in paired profiles, with passing controls and both discrepancy directions. The pattern also occurs in passing controls and meaningful underpredictions move oppositely, so a blanket buffer correction is unsupported. Preserve the original FSWEPP2/WEPP2010 criteria; same-engine legacy controls are diagnostic anchors, not replacement targets.

- Preserve the frozen v1 particle audit and its acceptance/dependency hashes. Introduce a versioned corrected audit with an adjacent-field regression and append verification; do not rewrite historical evidence or patch the native engine for an audit defect.


2026-10-31: Accept the exact U12 numerical repair within its declared scope and promote the already tested bytes as undeployed revision 4. Do not rebuild merely to change provenance: all 489 build inputs match committed source, and metadata explicitly records the earlier research build. Numerical acceptance does not accept Roads parameters.

- Decision: advance combined U12 to broad validation after separate-lane seed attribution and independent sign/terminal-support review.
  Rationale: the observed producer error is closed, water/soil unchanged; bounded terminal roundoff and fraction-sum flags remain explicit acceptance items. See ADR-0124 and the active ablation plan.
  Date/Author: 2026-10-31, Codex.


2026-10-31: freeze U11 for broad validation after independent source/seed
review. Keep its raw/clipped capacity exposure question and earlier two
fraction-sum flags open; use exact-parity observations before additional
solver changes. Do not change scientific or magnitude thresholds.

2026-10-31: reject U1 promotion despite broad execution passes. Separate U2
anchored transition search from proposed U3 stable integration so numerical
changes remain attributable. Keep strict particle flags visible.

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

- Roughness isolation failed after four corrected preflight runs; an earlier single legacy run stopped on harness coverage. All five runs are retained. Four additional observation-only replays reproduce their corresponding modes exactly and establish executed native upstream coupling. This changes the next experimental question to whole-hillslope response, without accepting a parameter or changing the released engine.

- Buffer observation is complete: 18 accepted full-period runs, 126 exact ordinary outputs and independently reconciled process observations. O1/O2 staging/inventory failures and the separate review summation-order failure remain retained. Bind external make prerequisites and load existing lazy audit modules before freezing execution dependencies. The findings support a controlled surface-conditioning test, not a default change or a new engine repair.

- WEPPpy revision-4 delivery is pushed as a5c40031a. The 116-case ledger has independent scientific and implementation acceptance, complete raw retention and a source-free reproduction packet. No model/parameter change follows from this observational result; the next bounded source study is predeclared separately.

- The completed hydraulic factorial does not support parameter promotion. Exact-R4 legacy anchors remove the engine confound; event boundary accounting will guide the next physical hypothesis. Complete segmented application coverage supports scoped native release handoff; WEPPpy repository delivery is complete as a5c40031a; no production deployment.


U12 scientific investigation is complete. Two retained fraction flags and terminal-capacity precision have source-derived explanations; no threshold was relaxed. Revision-4 application/report delivery is active, followed by combined physical parameter experiments. The magnitude classifications remain unchanged.

U12 is implemented as an isolated matched pair and now undergoing broad
validation. No release promotion or parameter default change has occurred.
Source-executed regressions and exact-parity observations distinguish the
material PARAM sign error from residual REAL accumulation/terminal precision.


Current U11 milestone: targeted and seed gates pass; broad validation is
running. Shipped revision3 and ledger v15 remain authoritative until all
scientific/release gates pass. UI implementation remains human gated.

EROD continuation: missing support is confirmed and mass closure improves,
but scalar review prevents premature release. Shipped revision3 is unchanged.

Current: artifact revision 3 delivery is complete; ledger v12 records the current baseline and completed resumption studies.
All 840 physical cases pass; 713/766 meaningful and 31/74 small references pass
magnitude criteria. There are 48 meaningful underpredictions, five meaningful
overpredictions and 43 small-load exceedances. Of 96 misses, 71 are outunrut.
No parameterization is accepted. Cedar scientific review is complete; no native
release prerequisite remains open. Earlier entries below are historical checkpoints.

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

## Revision-3 parameterization resumption — 2026-10-31

Execute `artifacts/role_boundary_assessment_r3.py` against the retained final dated
840-case matrix, checking binary identity, native output hashes and matched
climate/management/slope inputs. Read boundaries through the canonical Rust reader;
compare signed road/fill/buffer net exchanges with frozen FSWEPP2/WEPP2010 outputs.
This readback performs no new model runs and does not establish particle provenance
or parameter causality. Preserve old studies rather than treating revision-2
control results as revision-3 evidence. Use the new attribution to declare a
bounded role-specific hydraulic/transport contrast with passing controls before
any parameter search. No global erosion reduction, withheld-material access or UI
implementation is authorized by the readback. Existing scientific thresholds stand.

Decision: close completed native-release prerequisites and refresh role attribution
on the exact accepted pair before choosing the next experiment. This avoids tuning
against superseded engine behavior and keeps opposing magnitude errors visible.

### Declared immediate control: whole legacy soil on revision 3

The completed final-pair role readback places the largest net-exchange difference
at the buffer for all five meaningful high cases and downstream for 42/43 small
exceedances. Low misses span all three roles. Legacy templates use format 98.4,
whereas generated decks use 9002: do not splice role blocks or assume a conversion
is semantically neutral. First execute `artifacts/legacy_soil_control_r3.py` on
all 96 current misses plus the first passing case per climate/design (20 controls):
116 runs, changing only the entire `p1.sol` to its hash-verified legacy reference.
Freeze the declaration before execution. All climate, geometry, management, runtime
sidecars and final binary bytes remain exact. Retain every failure and native
physical audit. This refreshes the prior whole-soil diagnostic on the repaired
engine; legacy substitution is not a generated-soil candidate. Subsequent role
contrasts require a source-supported, representation-preserving intervention.

### Resumption decision and outcome

See `artifacts/revision3-resumption-findings.md`. The refreshed whole-soil control
recovers79/96 misses, but 17 residuals (11 distinct inputs) remain, all outunrut. Execute
`artifacts/runtime-bridge-r3-design.json` next, retaining five passing controls.
Reason: a soil-only explanation is incomplete, and prior runtime findings precede
the shared recession correction. Do not tune generated hydraulic parameters to
compensate for unseparated engine/runtime effects. No change to acceptance,
withheld material, regional-runtime validation or the human UI gate.

## Runtime bridge execution — 2026-10-31

User: proceed with the designed 112-run comparison. Execute the frozen design with
`artifacts/runtime_bridge_r3.py --declare`, then without `--declare`. The declaration
binds binary, driver and direct audit dependencies plus all 16 source records. Each
of seven new sidecar combinations is run for each selected input; retain the 16
all-present baseline cells. Rehash every retained input and recompute all 128 native
physical audits, including failures. Classify outcomes with unchanged magnitude
criteria; summarize three-way interactions rather than selecting a global switch
from the 11 preselected residuals. No production code/defaults or withheld data change.

### Conditional completion of generated-soil runtime interaction

The 112-run bridge completes with 107 physical passes and five negative-demand
stops in hourly/original-Penman configurations. Daily/PMET with either snow setting
recovers 10/11 legacy residuals and retains 5/5 controls; this does not establish a
generated-soil recommendation. Complete the four-cell generated/legacy ×
hourly/daily panel on the same 116 cases, retaining PMET/snow. `soil_hourly_r3.py`
declares 196 unique new runs (116 generated, 80 legacy) for 464 labeled cells. Reuse 232
hourly baselines and 22 daily bridge cells; 14 additional labels alias new legacy
runs by exact complete input signature. Retain all 464 cells and report aliases.
No parameter/default change, withheld inspection or new acceptance criterion.
This conditional expansion is necessary to test transfer to the intended generated
soils before selecting hydraulic changes; previous revision-2 interaction results
are historical rather than current-engine validation.

## Runtime/soil completion checkpoint — 2026-10-31

### Surprises & Discoveries

- The legacy anchors expose an audit parser defect: adjacent F7.3/F6.3 ELEMENT fields can merge under whitespace splitting. This aliases QRain as SedLeave. Source-defined fixed widths clear all 91 false mass flags in both engine generations; production interchange already uses fixed widths.


Daily mode recovers 93/96 legacy-soil misses but only 26/96 generated-soil misses;
two generated passing controls regress. The 464 PMET-retained cells all pass
physical checks. Separately, five hourly/original-Penman bridge runs stop at the
native negative-demand guard and remain failed configurations. The seven
source profiles retain equal input density and organic matter across roles;
first-day native state confirms this is a useful audit target, not proof that
a compaction rule will repair the discrepancies.

### Decision Log

- Preserve the frozen v1 particle audit and its acceptance/dependency hashes. Introduce a versioned corrected audit with an adjacent-field regression and append verification; do not rewrite historical evidence or patch the native engine for an audit defect.


Reject global hourly-off promotion. Keep current runtime, source soils, 200 mm
normalization and deeper horizons fixed while tracing coupled role density,
retention and conductivity. Require physical source support before declaring
parameter ranges. No climate-specific fitting, withheld outcomes or UI changes.
The normative next scope and rationale are in
[the hydraulic audit plan](../../artifacts/generated-role-hydraulic-audit-r3-plan.md).

### Outcomes & Retrospective

- The completed hydraulic factorial does not support parameter promotion. Exact-R4 legacy anchors remove the engine confound; event boundary accounting will guide the next physical hypothesis. Complete segmented application coverage supports scoped native release handoff; WEPPpy repository delivery is complete as a5c40031a; no production deployment.


This checkpoint adds 308 native executions with persisted declarations and
fresh output/hash/physical readbacks. No generated parameterization is accepted;
the full 840-case magnitude score is unchanged. Ledger v13 supersedes v12;
prior designs remain immutable records of their pre-execution decisions.
See the [soil/runtime findings](../../artifacts/soil-hourly-r3-findings.md).

Archive retention is complete: every member was rehashed against its manifest;
see [retention receipt](../../artifacts/runtime-soil-r3-v1-retention.json).
Documentation lint: 31 files, zero errors or warnings.

## Generated-role hydraulic audit execution — 2026-10-31

Execute `hydraulic_init_probe_r3.py` build/declare/run: isolated archive of compiled
source 6112b68bc, observation-only stdout at SCON completion and WATBAL initialization.
Fourteen full-period replays (first retained legacy-panel case per development
material, generated and legacy) must exactly match all released raw outputs.
No native checkout or released binary changes. Inventory all emitted horizons and
source dependencies; distinguish native inferred legacy values from supplied modern
values. Physical literature must justify the next bounded contrast independently
of its sediment response. Withheld/UI/default gates remain unchanged.

### Declared conditional road-pore sensitivity

Initialization observation passes 14/14 exact raw-output comparisons. Execute
`road_pore_screen_r3.py declare/run`: three incremental road-only lanes on the
frozen 96 misses plus 20 passing controls (348 new runs). Pore lane reduces raw
porosity by 0.02 through density and scales FC/WP at fixed normalized retention
shape; conductivity lane divides existing capped K by 2.4; coupled lane combines
them. Appended VG scale values follow the same factors, though this native
revision reads but does not consume those arrays downstream. Preserve every
non-target line and all non-soil input bytes. The native density clamp is applied
before computing the perturbation. The source is Martin et al. 2024,
https://doi.org/10.1186/s13595-024-01265-4. This is a bounded sensitivity, with
explicit model gaps: skid-trail to constructed-road transfer, uniform 0–200 mm
instead of measured depth bands, and fixed-shape retention translation. It is
not a calibrated road rule. Do not tune its constants after seeing sediment.
Require all physical checks and report control regressions; no default promotion.

## Hydraulic audit and sensitivity outcome — 2026-10-31

### Surprises & Discoveries

- The legacy anchors expose an audit parser defect: adjacent F7.3/F6.3 ELEMENT fields can merge under whitespace splitting. This aliases QRain as SedLeave. Source-defined fixed widths clear all 91 false mass flags in both engine generations; production interchange already uses fixed widths.


Generated role density/retention preservation is confirmed, with all 200 mm
breaks present. Initialization—not day-one weather output—shows the substantial
legacy/generated state difference. Nevertheless, a modest pore/retention treatment
recovers only one miss. Conductivity-only recovers 24/96 and coupled recovers
25/96; all 20 passing controls remain. All 348 treatment runs pass recomputed
physical audits. The 14 baseline and seven coupled observation replays have
exact full-period raw-output parity. Native corrected porosity falls by about
0.019, rather than the raw input target 0.02, because entrapped-air corrections
and initialization/tillage apply; observation preserves this distinction.

### Decision Log

- Preserve the frozen v1 particle audit and its acceptance/dependency hashes. Introduce a versioned corrected audit with an adjacent-field regression and append verification; do not rewrite historical evidence or patch the native engine for an audit defect.


No standalone parameterization accepted. Forty-two small-load misses remain,
already preventing the full small-reference gate; do not spend a new 840-case
sweep on these standalone treatments. Retain conductivity as a component
hypothesis, without tuning the frozen 2.4 divisor or adding unsupported fill
compaction. Establish exact same-format legacy equivalence before isolating
whole fill/buffer role contributions. The research coefficient rationale and
non-production scope are durable in ADR-0120. The next normative scope is
[role-isolation-r3-plan.md](../../artifacts/role-isolation-r3-plan.md).

### Outcomes & Retrospective

- The completed hydraulic factorial does not support parameter promotion. Exact-R4 legacy anchors remove the engine confound; event boundary accounting will guide the next physical hypothesis. Complete segmented application coverage supports scoped native release handoff; WEPPpy repository delivery is complete as a5c40031a; no production deployment.


369 native executions: 348 treatment runs and 21 observation replays. No binary,
shared soil writer, default, withheld or UI changes. Ledger v14 supersedes v13.
The source audit did not establish a production defect. Research-only field
transfer assumptions remain explicit; numerical improvement does not validate
constructed-road compaction or the fixed normalized-retention translation.
See [results](../../artifacts/road-pore-screen-r3-findings.md) and
[archive receipt](../../artifacts/hydraulic-role-r3-v1-retention.json).

Retention complete: 10,323 archived files individually verified (3,170,098,899
uncompressed bytes). Documentation lint passed for all 34 package Markdown files,
ADR-0120 and the ADR index; spelling preview and whitespace checks are clean.

## Legacy format equivalence execution — 2026-10-31

Execute the seven-material preflight in `legacy_format_bridge_r3.py` before the
full 116-case bridge or any role substitution. Preserve inferred legacy fields
with diagnostic zero sentinels, supply top-200-mm legacy `avke`, and retain the
native-added lower layer with its original estimation behavior. A duplicate
terminal 200 mm road boundary is forensic input only: native extension makes it
positive thickness; never allow this through production soil validation.
Require exact initialized observations and full output inventories/bytes. If
failed, trace format-selected branches rather than relax parity or proceed to
mixed roles. No source/default/UI changes; existing observation binary only.

### Equivalence preflight disposition and same-format continuation

All seven bridge runs complete, but zero pass exact output parity. Four match
initialized states with only a deterministic extended-format caution in LOSS;
three have conductivity drift from the INPUT harmonic-remap numerator versus
legacy TILAGE direct `avke` assignment. Do not waive metadata/numeric differences
or proceed to whole-role substitutions. The equivalent-role bridge is rejected.

Continue a narrower generated-only 348-run panel with `downstream_hydraulics_r3.py`:
fill `ksatadj=0`; buffer upper-200-mm K capped at configuration-matched legacy
buffer `avke`; both together. All original generated road and other soil state
remain fixed. These are diagnostic component hypotheses, not legacy equivalents
or physically accepted candidate values. No new road divisor, material swapping,
per-case fitting, production defaults or withheld/UI changes. Declare and read
back all inputs before execution; recompute every physical audit and compare
all 96 misses and 20 controls. Source format parity remains failed, not bypassed.

### DEPEND failure observation

The downstream fill-only case exposes SIGFPE at DEPEND's unbounded Newton step.
`capture_depend_failure_r3.py` repeats the failure on the released binary with
identical partial outputs and retains a portable input fixture plus GDB locals.
`depend_scalar_repro_r3.py` reproduces it in actual source and observation-only
scalar lanes; an independent 80-digit closed-form solution lies at
0.050115891779652795 inside the physical interval. No native behavior changed.
The next required ablation is `depend-root-ablation-r3-plan.md`; resolve the
solver domain/step contract before further parameter sweeps. Whole-role
substitution stays unexecuted because format equivalence failed.

## Downstream diagnostic checkpoint — 2026-10-31

### Surprises & Discoveries

- The legacy anchors expose an audit parser defect: adjacent F7.3/F6.3 ELEMENT fields can merge under whitespace splitting. This aliases QRain as SedLeave. Source-defined fixed widths clear all 91 false mass flags in both engine generations; production interchange already uses fixed widths.


The strict format bridge fails despite equal rounded annual sediment for all
seven preflights. Four differ only by a deliberate report warning; three also
have one-to-two-ULP conductivity-state differences through native remapping.
Keep this distinction explicit; it does not establish another sediment defect.
The generated-only buffer cap recovers 47 low-load misses but regresses three
passing controls and no small-load misses. Fill-only recovers eight small-load
misses but regresses one control and exposes a true native solver overflow.

### Decision Log

- Preserve the frozen v1 particle audit and its acceptance/dependency hashes. Introduce a versioned corrected audit with an adjacent-field regression and append verification; do not rewrite historical evidence or patch the native engine for an audit defect.


Reject all standalone downstream treatments and the exact-equivalence bridge.
Do not relax parity, copy legacy role material, tune the road multiplier, or
assemble unvalidated parameter combinations. Prioritize DEPEND's finite interior
root with an out-of-domain Newton sequence. Require a bounded search with
independent reference coverage, not guard suppression or soil tuning. The next
normative scope is [the root-search plan](../../artifacts/depend-root-ablation-r3-plan.md).
The same-format experimental rationale/disposition is durable in ADR-0120.

### Outcomes & Retrospective

- The completed hydraulic factorial does not support parameter promotion. Exact-R4 legacy anchors remove the engine confound; event boundary accounting will guide the next physical hypothesis. Complete segmented application coverage supports scoped native release handoff; WEPPpy repository delivery is complete as a5c40031a; no production deployment.


Completed seven bridge runs and 348 downstream runs (347 physical passes), plus
two full-model failure replays and two scalar failure reproductions. Recomputed
physical audits and rehashed all input/output artifacts; the full native fixture
is portable and retained in git. No production native/soil/default/UI change.
The user-authorized undeployed same-name release preference applies only after
future repair gates; this checkpoint does not release a new binary. Ledger v15
supersedes v14. See [findings](../../artifacts/downstream-hydraulics-r3-findings.md)
and [retention receipt](../../artifacts/downstream-hydraulics-r3-v1-retention.json).

Retention complete: 9,320 archive members individually rehashed; 2,970,545,552
uncompressed bytes. Documentation lint passed for 37 package Markdown files and
ADR-0120, with clean spelling preview and whitespace checks.

## DEPEND bounded-search ablation — active execution

Executing `artifacts/depend-root-ablation-r3-plan.md` in the native default
branch checkout `/workdir/wepp-forest-release-20261009`. Baseline regression
reproduces SIGFPE. The candidate preserves legacy convergent searches and
positive-flow endpoint returns, but uses interval bisection when a Newton step
leaves the physical segment, a derivative vanishes, or ten iterations expire.
Bisection ends at adjacent float32 coordinates and returns the non-depositing
side; there is no fitted deposition tolerance. Decreasing-flow overflow checks
precede conversion, retaining its existing terminal and no-root conventions.

Progress: scalar regression and 100 deposition/reference tests pass; matched
native build and full-model gates are underway. Release pair unchanged. Candidate
is unaccepted pending full fixture, Roads 840 + downstream 348, native regression,
watchlist, Disturbed, Cedar, and independent review. Withheld soils and UI gate
remain untouched. Native incident: `docs/ablation/20261031_roads_depend_bounded_root`.

Decision: keep the first candidate bounded to the confirmed search failure;
retain the governing DEPVAL equation and existing successful convergence behavior.
Surprise: positive-flow searches have no upper bound, whereas decreasing-flow
searches clamp only after division, leaving a separate overflow exposure.
Outcome so far: reproduction and scalar repair only; no scientific promotion.

## EROD interval-support continuation

Current scientific findings are in `artifacts/particle-erod-observation.json`;
execute `artifacts/erod-subgrid-ablation-plan.md`. No release promotion or
parameter combination is accepted while particle accounting remains unexplained.
Cedar G1 execution completed all24years; conversion/semantic checks are ongoing.

Decision: trace and repair missing bulk support before changing particle
normalization. Rationale: exact-parity observations show EROD returns without
integrating a nonempty interval that contains no grid point. The following
interval starts downstream using an unchanged load. This is independent of the
DEPEND search defect and requires a separate behavioral lane.

## EROD U1 rejection and U2 transition result — 2026-10-31

U1 completed840 Roads,348 downstream,99 Disturbed,28 watchlist and the full
Cedar864-hillslope/24-year watershed execution. The initial1160-test native
suite passed, but expanded independent scalar references reject promotion.
All135765 EVENT class-versus-bulk mass comparisons pass; two strict fraction
sum flags remain unresolved. Magnitude classifications are unchanged.

U2 replaces the shared transition search with a fixed upstream coordinate/load
and strict initial excess; RUNGE remains unchanged. Expanded34-test comparison:
U1 has15 failures; U2 has6 failures, all stiff constant-coefficient roots.
The nine corrected cases include six initial-equality/later-crossing cases
and three constant-source transitions after the first grid. Thus the shared
grid/partial path is confirmed affected, not only the newly supported interval.
Raw evidence: out/roads-parameterization-program-20261031/erod-root-u2.
Next: independently review the stable integration lane, close stiff scalar
references, then repeat physical/full-period gates. Neither candidate is released.

## Stiff integration and boundary review — U3 through U5

U3 passes43 scalar cases and four full-period seeds but is rejected for missing
short positive-capacity tails. U4 partitions capacity zeros and passes48 cases
but is rejected for continuing detachment to a closing zero-capacity endpoint
despite an earlier deposition transition. U5 establishes a prefix-supply
bracket first;55 scalar cases and four full-period seeds pass. Review rejects
U5 because capacity can close and reopen inside an interval, hiding the first
transition from an endpoint-only check. No numerical candidate is promoted.

Raw source/pairs: out/roads-parameterization-program-20261031/erod-stable-u3,
erod-capacity-u4 (scalar-only), and erod-boundary-u5. Reproduction commits
are3c226ce55 and167e421d3 in /workdir/wepp-forest-release-20261009.
U3 broad execution completed840+348 prior physical checks; expanded particle
review is separate. U1 Cedar analysis is complete: unchanged water metrics,
outlet sediment+1.18kg over24 years, finite/nonnegative PASS fields.
That audit does not certify full particle normalization. Two small strict
fraction-sum flags and unsafe tiny-capacity arithmetic remain open.

Next lane design: locate the first supported transition within an interval,
partitioning capacity zeros and residual-forcing turning points. Independent
scientific review must establish the interval contract before implementation.
No magnitude thresholds, soils, withheld materials, shipped binary, or UI
human-approval gate have changed.

## Combined U9 candidate — active validation

Actual-source review extends the failure class beyond EROD: small nonzero
positive/negative inflows used the zero-inflow boundary approximation; DEPOS
reconstructed capacity with cancellation; and DU0 at a finite-coordinate
transition changed the actual boundary load. These are independently
reproduced, separately ablated mechanisms, not Roads calibration changes.
U7 closes four actual-chain failures; U8 removes6.4% cancellation; U9 closes
the residual30ppm boundary jump. All15 actual-chain controls and65 scalar
references pass in the isolated prototype.

The native working tree now matches combined U9 source under
out/roads-parameterization-program-20261031/erod-handoff-u9/probe/src, plus
DEPEND G1. Matched binaries are under that candidate's bin directory; source
manifests name exact overrides. Source commits3c226ce55,167e421d3,890f1c891,
d3705c48b and5c92f2633 retain reproductions before new release gates. Native
U5 previously passed1197 tests but remains rejected for independent failures.
U9 source gates, full-period seeds and independent reviews are now active.

No scientific/release acceptance is implied. Next complete matched broad
Roads/downstream, particle, native/watchlist, Disturbed and fresh Cedar gates;
resolve the two strict fraction-sum flags and any real wet/dry boundary
failures. Only then revisit release promotion and parameter comparisons.
See ADR-0122 and ADR-0123 for numerical/caller contracts and rationale.

## U11 frozen broad validation checkpoint

Candidate root: out/roads-parameterization-program-20261031/erod-wet-domain-u11.
Watershed SHA256a4b9e7de28e3ebc813e844124547248da99f664c76613d5ef5d0b37b753edf38;
matched hill identity and exact source overrides are in build.json/source.json.
Native checkout /workdir/wepp-forest-release-20261009 now matches these sources.
Full regression uses the matched pair copied to src/wepp and src/wepp_hill.
All shipped wepppy artifacts remain unchanged.

Active observer: artifacts/observe_particle_capacity_u11.py and
replay_particle_capacity_u11.py; raw root particle-capacity-observe-u11.
It traces selected ENRICH/SLOSS dates for earlier rounding flags and records
negative raw capacity on actual wet DEPOS support, with PARAM denominator
context. Require exact output parity before using observations. Constant
negative capacity has zero raw-derivative mismatch; varying negative support
requires quantitative scientific disposition. No production prevalence is
inferred from a scalar or source hypothesis.

## U12 accepted native pair: revision-4 promotion sequence

Independent scientific acceptance binds watershed SHA2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48
and hill SHA9ef6b62677407a66255a2b95becc9f350c87ef8e4cf67ab4e543ddb89ed4a010.
The owner previously authorized another same-name replacement of the undeployed
261029 pair. This sequence does not change Roads defaults, withholdings, deployment
or the explicit human UI specification/layout gate.

Commit the reviewed native source/fixtures/docs on the verified default branch,
retaining the exact tested binaries. Verify all compiled source/include/math
inputs against that commit and record pinned system-toolchain provenance. Promote
those identical bytes as artifact revision4 with matched sidecars; do not silently
rebuild or strip them. A different executable requires renewed exact-pair gates.
Preserve revision3 identities and evidence for rollback.

Author a revision4 release report explaining bounded root search, integration
support/first transitions, stiff integration, shared capacity, actual inflow/wet
coordinates and PARAM sign correction. Include original numerical figures,
unchanged magnitude outcomes, Cedar effects and the certified residual precision
limits. Preserve earlier PDF revisions. Independent publication review must
approve the public report/manifest; raw legacy source remains private. Eight
mixed-context artifacts have already been retained privately with source-free
public entry points and explicit container-safe research paths.

After scientific/publication gates, vendor the exact pair and sidecars through
wepp_runner's canonical provenance/smoke/application checks, run required WEPPpy
sanity tests, and verify the report download/navigation path. Update ADRs and both
active plan/tracker with actual source/binary/PDF hashes and validation outcomes.
Only after delivery is recorded may generated-soil parameter experiments resume
against the new frozen engine. The current713/766 meaningful and31/74 small
magnitude score remains scientifically insufficient; no parameter rule is adopted.

## Revision-4 parameter continuation: complete hydraulic factorial

After focused actual-workflow delivery gates, execute the predeclared
[hydraulic factorial](../../artifacts/combined-hydraulics-r4-plan.md) under amended
ADR-0120. Its eight cells combine existing road, fill and buffer factors without
coefficient fitting: 464 exact-U12 cells reused with fresh verification and 464
new executions on the same 116 cases. Preserve all 96 misses and 20 controls,
report physical and strict particle checks separately, and retain the six withheld
materials. A diagnostic pass cannot substitute for fresh 840-case confirmation,
physical justification or the human UI-design gate.

The full application suite can run concurrently with the direct-native factorial:
its focused actual-workflow checks already pass, and all model/dependency bytes
are frozen. No full-suite acceptance or release handoff is claimed until the
suite completes. This scheduling decision does not change scientific gates.

### Factorial staging correction

The first factorial attempt omitted audit-required `reference.sol` and reused
`stdout`/`stderr`, although its model-consumed inputs matched. The runtime auditor
correctly rejected staging; nine native executions completed but zero results
were accepted. Preserve that directory and `combined-hydraulics-r4-attempt1-failure.json`.
The independently reviewed v2 uses separate directories, hashes these auxiliary
artifacts, and requires one actual reused/fresh preflight before the broad pool.
Both passed. Final verification must rehash fresh logs and rerun the runtime
validator on every case, including cached preflight records. Do not modify the
frozen execution source while the batch runs. This exposes a repeatability lesson:
model input manifests alone do not describe the complete audit replay contract.

## Event supply/retention continuation

The completed 928-cell factorial does not close magnitude acceptance. All 43
small-reference misses are outsloped/unrutted and 35 fail every tested combination;
several controls regress under downstream treatments. Final artifact/runtime
verification passes all 928 cases, with three strict fraction flags retained
(two previously certified reused cases, one new unresolved flag in a rejected lane).
No new parameters are promoted. Execute the
[event comparison plan](../../artifacts/event-supply-retention-r4-plan.md): first
rebaseline the full existing 116 whole-legacy-soil controls on exact revision 4,
then compare event supply and retention at each OFE boundary. This avoids using
revision-3 legacy results to assign a revision-4 soil mechanism.

Revision note, 2026-10-31: the current sections now record completed paired-event
and O3 buffer-process studies, independent reviews and retained failed attempts.
The next question is a separately declared roughness-conditioning counterfactual,
because observed storage/return/exchange differences do not identify a universal
parameter adjustment. Corrected stale revision-3 identities in Context and
Orientation to the delivered revision-4 inputs; earlier entries remain history.

Continuation note, 2026-10-31: the operator authorized the next diagnostic study.
The 36-run persistence design and its independent preparation reviews are frozen
before implementation. Exact patch, build, runner and execution gates remain;
the tested intervention retains all natural roughness-dependent responses and
does not assert that the configured initial roughness is physically correct.

2026-10-31 continuation update: retained the failed roughness-isolation campaign
(4,564 files) and independently accepted four-replay coupling localization
(1,409 files). Ledger v19 binds the separate dispositions and exact archives.
The next experiment requires a fresh whole-hillslope declaration because the
executed routing feedback contradicts the original isolation expectation.
