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
- [ ] Finish revision 2 release integration before further tuning.
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
