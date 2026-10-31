# Roads parameterization program tracker

Active: [ExecPlan](prompts/active/program_execplan.md).

## Current checkpoint

The native accounting investigation accepts the bounded repairs in `wepp_261029`
artifact revision 2, source `ba9f2ad91`. The frozen U10 panel passes all 840
physical/accounting cases. Parameterization acceptance remains unmet: 719/766
meaningful-reference cases (93.864%) and 30/74 small-reference cases (40.541%)
pass; 749/840 is only a descriptive combined score. Annual exports match U9a at
reported precision. Six withheld materials remain unused; no Roads defaults or UI
have changed. See [U10 scoring](artifacts/U10-magnitude-summary.json) and the
[release integration](../20261030_wepp_261029_rerelease/package.md).

Next: with revision-2 release integration complete, investigate outunrut low-reference and
routing behavior using the frozen development panel and physically justified
controls. Preserve the separate small-load criterion. Do not fit around native
defects, consume withheld materials early or treat accounting success as magnitude
acceptance. UI specification/layout remains human-gated before implementation.

## Chronological evidence

2026-10-30 UTC: operator authorizes one autonomous program with a model-acceptance
stage followed by a user-facing configuration view. Explicit clarification: users
need not edit CSV. Active goal created; no token budget imposed.

Initial checkpoint: acceptance rules and seven-development/six-withheld material split are
snapshotted in `artifacts/design-v1.json`; the full climate/geometry panel remains
to be frozen. Working 95% overall / 90% per group gates were presented for optional
operator steering; no candidates have been selected against them yet.

Runtime diagnostic completed eight runs (`artifacts/mode-diagnostic.json`). All four
mode-off controls reproduced prior native outputs exactly. Adding `wepp_ui.txt`
eliminated the reproduced negative flux in the two source-drainage inputs; all four
UI-mode runs reconciled sediment reports with zero EBE mismatch events. This is a
bounded diagnostic, not evidence that source drainage passes broader validation.

Historical evidence: `20261029_roads_drainage_validation` completed 2,112 native runs,
showed missing runtime sidecars in simplified comparisons and six invalid negative-flux
cases. Its old panels are development data. Current working tree also contains
uncommitted earlier study packages; preserve them and ignore generated docs index drift.

Next: finalize the runtime/composition audit and new panel manifest; execute screening
without per-experiment approval. Canonical parameterization/UX contracts and ADR will
be finalized once the accepted parameter model is concrete, before production edits.

2026-10-30 UTC: launched the frozen 576-run development surface screen with
`artifacts/screen.py`; active scratch batch `surface-screen-v4`. See
`artifacts/surface-screen-rationale.md` for hypotheses, physical context and two
retained preflight failures. V3 then exposed two `HOURLY_WATER_UNMET` failures in
the 3 mm/hour paved/loam/site treatment, which disqualifies that treatment. V4
records failures explicitly and reuses 128 verified completed v3 cases.
Execution log: `/tmp/roads-surface-screen-v4.log`;
incremental records: scratch `surface-screen-v4/partial-results.json`. Read the
live process/output state before resuming; do not rerun into an existing directory.
Focused scope/runtime/negative-flux tests: 14 passed. No candidate selected yet.

2026-10-30 UTC: surface screen completed, 576 cases verified; all six treatments
fail acceptance in UI-only runtime. Twenty-run sidecar diagnostic completed.
Exact-binary debugger trace v7 explains one report discrepancy and reproduces all
seven native outputs byte-for-byte. Evidence and decisions:
`artifacts/surface-screen-results.md`. Seven scoring tests added and passed.

Current execution: `project-runtime-screen-v2`, 288 cases, roles/erosion/rock with
full project shared files. Log `/tmp/roads-project-runtime-screen-v2.log`; scratch
`project-runtime-screen-v2/partial-results.json`. V1 failed worker serialization
before native execution; preserve that preflight. Next: score the completed full
runtime panel, trace remaining accounting discrepancies where justified, and choose
the next supported model experiment. Independent validation soils remain unused.

2026-10-30 UTC: full-runtime panel completed and verified; all three treatments
still fail. Subsequent 18-case fill/buffer lower-boundary diagnostic completed:
changing fill drainage resolves Birmingham/sand, but not Birmingham/clay or
Flagstaff failures. See `artifacts/surface-screen-results.md` for exact counts.
No processes remain needed from these screens. Combined focused tests: 21 passed.
Next mechanism: isolate the 9002 forest saturation-dependent conductivity adjustment
on engineered road/fill roles (`ksatadj`), preserving all source horizons and lower
boundaries. Pinned source audit confirms 9002 ignores the 9001 `ksatfac/ksatrec`
formula. Withheld soils remain untouched; no accepted model or production UI yet.

2026-10-30 UTC: 30 hydraulic-role, 384 engineered-surface, 18 combined-boundary
and 18 initial-state cases completed. Road forest-adjustment removal plus upper
200 mm surface conductivity cap passes the numerical screen (93/96), but two
native stops remain. All four nonnegative accounting discrepancies are explained
by case-specific exact-binary traces with unchanged precision bounds and byte
parity. `artifacts/engineered-surface-results.md` and `candidate-disposition.json`
record the rejection and evidence.

Exact failure trace proves the negative-FIN reset discards 38.576 mm of net local
rainfall. Proposal and portable verified reproducer:
`artifacts/native-water-accounting-decision.md`. User input requested asynchronously:
permit an isolated fix and revised native pin if validated, or retain 261026.
No patched binary built; this is the first pending native-authority decision, not
a completed/blocked goal claim. Independent soils remain unused.

Focused tests: 30 passed. Full sanity suite is running through `wctl run-pytest
tests --maxfail=1`, log `/tmp/roads-program-full-pytest.log`, exec session 23368.
Poll that handle/log before starting any replacement. Documentation lint: ten files
pass. Next independent work is finish the suite and retain its outcome; native build
work depends on the requested scope decision. No production implementation yet.

2026-10-30 UTC: blocked audit reached after repeated goal turns with the same
unanswered native-pin decision. Further scientific acceptance depends on that
decision; no candidate accepted and no production edits made. Full pytest remains
live: session 23368, host PID 2947211, latest observed at 21% in Disturbed soil
artifact checks with no reported failure. Leave this process running and poll its
handle/log on resumption; do not claim a pass or restart from an observation timeout.
The operator decision and the eventual suite outcome are both outstanding.

2026-10-29 local: operator explicitly authorized a WEPP-forest work package to
implement the accounting fix, release wepp_261029, run the Disturbed matrix and
Cedar Creek semantic analysis, and author illustrated release notes. The native-pin
blocker is resolved. Active native plan:
`/workdir/wepp-forest-release-20261009/docs/work-packages/20261029-negative-fin-water-accounting/prompts/completed/implementation_execplan.md`.
261026 remains the historical control; acceptance thresholds and withheld sampling
are unchanged. The new binary may support Roads acceptance only after validation.

The original full WEPPpy suite completed: 12,209 passed, 298 skipped, 5,830 warnings
in 3454.64 seconds. Log `/tmp/roads-program-full-pytest.log`; session 23368 is terminal.
Native U1 full Cedar lanes completed and semantic analysis is available under
`/wc1/ablation/negative-fin-20261029/cedar-U1/semantic-analysis/`. U1 still fails the
Roads full-run gate at a later hourly timing boundary; separate scope question pending.

2026-10-30 timing ablation: the full 16-year Roads fixture now completes.
Timing-only U1 exposes 17 negative Ep records; separate updated-stock ET and
root-integral corrections remove them. Native regression fixture and source
probes added in the canonical WEPP-forest checkout. A PeakRO widening attempt
failed Rust fixed-width interchange and is being replaced with compact overflow
formatting. No production parameterization or binary promotion yet. Broader
96-case Roads, native, Disturbed and Cedar validation is underway.

Timing ablation execution complete: 96/96 frozen development cases meet magnitude
and physical/accounting gates; 663 native tests, 13 watchlist cases, both smokes
and 99 Disturbed tests pass. Full Cedar completes with finite/nonnegative water
records; total outlet volume -0.41035%, sediment +0.13751%, reported maximum peak
-0.13860% versus 261026. Independent scientific review of timing attribution
and shared ET changes remains the native release gate. Detailed review packet:
canonical WEPP-forest `docs/work-packages/20261030-hourly-return-flow-timing/review.md`.


2026-10-30 UTC release promotion: independent AI scientific, implementation and
publication reviews accepted the bounded261029 release; owner read and accepted
the illustrated report. The matched Linux pair is vendored and passes actual
selected-runner/production-reader and host/container checks. The shared native
blocker is repaired; the Roads development treatment passes96/96 frozen cases.
This does not accept Roads defaults or the user-facing editor: withheld-soil and
broader-geometry validation, parameterization contract and UI work remain in
this program. Release work and final repository gates are tracked in
../20261030_wepp_261029_release/package.md.

Release promotion complete: native47183b0fb, WEPPpy7077dc7ca pushed; full
WEPPpy sweep12,210 passed/298 skipped. Independent AI reviews accepted the
bounded engine repair. Continue this program with withheld-soil/geometry gates
and the user-facing parameterization view; no Roads default is accepted yet.


## Human gate for configuration specification and layout

Operator instruction, 2026-10-30: continue the recommended scientific program
with broad authority to use forest, up to a human review of the UI configuration
specification and layout. Prepare concrete fields, units, ranges, applicability,
version/adoption/reset behavior and a static layout proposal. Human approval of
both specification and layout is required before implementing the configuration
view or its production persistence/application wiring. Scientific experiments,
disposable builder/full-project validation and reviewable design documents remain
authorized. Do not treat silence, scientific acceptance or AI review as UI approval.

Continuation executing the revised active plan on261029. First batch: repaired-engine rebaseline of existing development treatments; withheld materials remain unused.


## 2026-10-30 continuation execution

Frozen design-v2 preserves all seven development and six withheld materials and
unchanged gates. Completed 384-case repaired-engine rebaseline: roles 80/96,
erosion-only 77/96 magnitude (80/96 physical), erosion+cap and legacy controls
96/96 on both gates. Expanded cap pilot: 28/28. Exact GDB replay proves an
uncapped full-day shortfall of 5.035662 mm before other sinks, with all seven
outputs byte-identical. Scientific review independently confirms the arithmetic.

Current evidence and commands: [continuation findings](artifacts/continuation-findings.md).
Cap-only ablation, production-builder readback and broader development research
remain in progress. Withheld validation and final parameterization acceptance are
deferred while the daily coupling limitation is unresolved. The owner’s human
specification/layout gate remains in force; no production implementation.


### Continuation closeout: scientific blocker before UI gate

All declared batches finished: rebaseline 384, minimal-rule ablation 96, expanded
pilot 28, broad development 840, exact-legacy control 96; **1,444 native study
cases**, plus diagnostic/independent replays. All 294 production-builder
preparation/readback cases pass. Broad candidate result: 740/840 magnitude,
822/840 physical/accounting. Nine Charleston/material-53949 cases stop and nine
site/material-53949 cases fail sediment reconciliation. Do not accept this candidate.

Independent scientific review confirms the capped Charleston daily shortfall
129.802574 mm before other sinks, with exact output parity; recommends separate
native daily-producer and event-output ablations before further parameter tuning.
Independent implementation review confirms complete denominators, withheld isolation,
all four archived fixture replays, and closure of the legacy normalization control
confound. The 96 exact legacy soil controls also pass and produce identical annual
exports to normalized controls under the same modern runtime. Neither is an
engine-only comparison against the differently configured 2010 runtime.

Authoritative outcome: [continuation findings](artifacts/continuation-findings.md).
Commands and portable diagnostic fixture instructions are retained there and in
[fixture instructions](artifacts/fixture-instructions.md). No released binary,
production runtime/defaults, real project, UI or deployment changed. The six
withheld materials remain unused. Scientific acceptance, actual project execution,
parameter ADR and reviewable UI specification/layout are still pending.


Final validation: scoped Markdown lint passes (13 package files, Roads specification
and project tracker); research Python compilation and whitespace checks pass.
The forest-local evidence archive is retained on network storage; streamed readback
verified all 17,784 declared native input/output files for 936 cases against their
records. Receipt: artifacts/archive-receipt-v1.json. All declared study jobs and
diagnostic replays have exited; no background study remains running.


## Native accounting ablation authorization — 2026-10-30

The operator authorized proceeding with the native accounting ablation addressing
the two continuation failures. The active native package is
`/workdir/wepp-forest-release-20261009/docs/work-packages/20261030-roads-native-accounting/`,
with `prompts/active/implementation_execplan.md`. This authorizes isolated native
source/fixture/behavioral ablation work and validation; installed `wepp_261029`
remains the comparator. Do not silently vendor probes, retune Roads, consume
withheld data or implement the UI. Human approval of UI specification/layout
remains required. The previous native-scope blocker is now cleared for ablation.

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
[261029 revision2 package](../20261030_wepp_261029_rerelease/package.md)
for vendoring/publication only after native scientific acceptance. This scope
amendment supersedes the earlier no-release boundary; Roads parameter defaults,
withheld-panel rules and the human UI configuration/layout gate remain unchanged.
