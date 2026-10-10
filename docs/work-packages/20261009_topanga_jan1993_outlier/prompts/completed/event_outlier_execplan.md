# Investigate the Topanga January 18, 1993 Outlier

This living plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose

Locate the mechanism of the confirmed unrealistic undisturbed outlet peak.
The opening outlier-first premise is historical: Roger subsequently judged
700 m3/s physically unacceptable at this site, supported by the same-input
old-release comparison. Distinguish evidence from inference and pursue a
bounded diagnosis without presuming which release component is responsible.

## Progress

- [x] 2026-10-10: Roger authorized wepp_261010 release and vendoring, removing
  never-deployed wepp_261009 from WEPPpy. Build from committed default-branch
  source, verify candidate equivalence and required committed-resource gates,
  refresh canonical rankings with the release build, update sidecars and
  documentation, and commit/push the release handoff. No production deployment.
- [x] 2026-10-10: Roger requested Marta's Cedar rerun. Execute
  `run_cedar_candidate.py` for paired candidate/261009 full 1980-2003 runs,
  864 freshly regenerated hills per build, unchanged frozen 10 cm RRINIT
  inputs and full 600-second outlet output. Recompute standard totalwatsed
  from fresh PASS/WAT; compare daily, annual and full-record yield, channel
  ledger and sampled discharge integral to each other and retained 260803.
  Preserve plots, timing/event departures and accounting gaps without new
  closure tolerances or source changes. No release or live project mutation.
- [x] 2026-10-10: Roger requested candidate mutation and disturbed-ranking
  studies. Run the frozen 280 controls plus 1088 mutations using
  `run_candidate_mutation.py prepare` then `execute`, including neutral
  observer checks and Figures 1-3. Run the 96-case canonical disturbed matrix
  for candidate and release in the same container with current defaults.
  Preserve separate reports and compare outputs; do not replace published
  release reports. These hillslope studies do not adjudicate channel sediment.

- [x] Roger authorized the bounded correction. Add captured-input regression
  tests, show baseline failure, apply only conditional time-zero subtraction,
  and build an isolated candidate pair. Run fresh candidate hillslopes and
  full-record Topanga/Rattlesnake burned/undisturbed simulations. Assess changes
  versus both 261009 and 260803; do not release, vendor or deploy.

- [x] Complete 714 same-build hillslopes and four full-record watersheds.
  Preserve target correction and ordinary-event consequences in
  [candidate results](../../candidate-results.md). Maintained suite: 163 passed;
  focused checks: 45 passed; smoke and 12 watchlist cases pass. Bare root
  pytest collection fails in archived experiments and is not called passed.
- [x] Roger authorized promotion after review: burned Rattlesnake year 40 May 15 peak
  falls 54.6%; year 41 May 28 outlet sediment increases 480857 kg. No further
  physical patch was added. Release/vendoring is approved; no deployment is included.

This decision supersedes earlier pending-implementation statements below.

- [x] Add observer-only records in an isolated copy of released Fortran source:
  January 16-18, 1993 incoming maxima, initial/carry state and routing
  coefficients. Keep arithmetic/state updates unchanged; require frozen
  outlet parity before interpreting the trace. No production source edits.

- [x] Same-build version trace: regenerate the old undisturbed PASS inputs,
  verify them against retained old outputs, and compare selected channels
  394-403, 406 and 412 in both releases over all 45 years. Reuse verified
  new-version PASS files. Keep physical inputs and 600-second routing unchanged.
  Read outlet rows back against frozen controls before using the traces.

- [x] Verify and preserve the user-supplied `eighty-five-synthetic` 260803 fork:
  matching effective inputs and 568 successful old-build hillslope executions.
  Compare January 18 and return periods against frozen 261009 outputs.

- [x] Continued investigation: capture full-series output for WEPP elements
  404-412, the outlet and its nearby lower-network branches, in both scenarios.
  Reuse validated PASS files and unchanged 45-year inputs at 600 s. Change
  only the output selection list; run two isolated watershed replays.
  Compare non-diagnostic outputs and the unchanged outlet trace with prior lanes.

- [x] Roger authorized output-only replay capture. Stage isolated copies,
  regenerate missing text PASS files with the original hillslope binary and
  unchanged inputs, and validate against retained PASS/EBE. Run peak-only and
  full-series watershed lanes over 1980-2024, changing only `chan.inp` selector
  1 -> 3. Preserve 600-second routing and all physical parameters. Compare
  non-channel-series outputs to establish observer neutrality.

- [x] 2026-10-10 02:05 UTC: open the investigation and record its neutral premise.
- [x] Verify live outputs against the frozen pre-investigation EBE hashes.
- [x] Capture the January 10-24 window and compare hillslope peaks, volumes,
  source durations, soil-water/snow context and outlet timing.
- [x] Document initial findings and observability limits; retain open hypotheses.
- [x] Validate retained artifacts and report the next bounded decision.

## Context and Orientation

WEPPpy is `/home/workdir/wepppy`. Live GridMET projects are
`/wc1/runs/sc/scrawny-relay` (burned) and its
`_pups/omni/scenarios/undisturbed` child. Both run the same `wepp_261009`
watershed binary, SHA256
`e1b1c244107216ca9edf4ccbaeb8d390e98440418d87beac2d5153b98191c7cc`.
They cover 1980-2024. Outlet WEPP element 412 maps to Topaz 24 and channel 128
(corrected from the opening notes' mistaken Topaz label).
The EBE daily event output reports 707.6391 m3/s undisturbed and 76.03957 m3/s
burned on January 18, 1993. Channel peak output reports rounded matching
values at times of 1,200 and 1,800 seconds; verify the time convention before
interpreting these as absolute event times.

Before-investigation snapshots and their hashes are under
`docs/investigations/2026-10-09-watershed-return-period-comparisons/artifacts/snapshot`.
Do not overwrite that evidence or mix later reruns into it. New window extracts
belong to this package's `artifacts/` directory. Live projects are read-only.

Hillslope PASS records specify channel-source inputs; watershed EBE and
`chan.out` contain reported outlet metrics. `H.wat` contains daily water state,
not a calculated event hydrograph. `tc_out` contains timing diagnostics whose
consumers must be traced before attributing causality. A scalar volume divided
by a scalar peak is an equivalent duration, not an observed recession or a
reconstructed hydrograph. A sum of noncoincident source peaks is not an actual
simultaneous inlet discharge.

## Milestones

First, verify output identities and extract the January 10-24 neighborhood
using the existing Parquet readers. Preserve schema units and record counts.
Read back paired hillslope PASS volumes/peaks/durations and daily water state,
outlet EBE/channel output and timing diagnostics. Do not alter dates, discard
outliers or regenerate reports in the live directories.

Second, localize what is known. Ask whether the large outlet peak is accompanied
by large hillslope peak inputs, unusual source support or timing, wet antecedent
conditions, snowmelt or other substantial state differences. Compare adjacent
days and the burned counterpart. Inspect existing source only as needed to
understand units and consumers. Preserve hydrological, parameterization,
reporting and numerical explanations as hypotheses until observations separate
them. Legacy parity and strict burned/unburned ranking are not acceptance tests.

Third, stop at a bounded decision. Existing output may support a mechanism or
may lack intra-day routing observations. In the latter case, specify the
smallest read-only/observer measurement needed, with replay context and cost;
do not launch a routing rewrite, instrumentation build or simulation campaign
by inference. Any subsequent run must retain same-build hillslope PASS files,
complete shared context and unchanged baseline artifacts. Source behavior
edits require a separate evidence-backed decision.

## Validation

Check SHA256 identities, parse extracted Parquet files back, and verify their
selected date/ID ranges against the source window. Reproduce the known EBE
January 18 values from frozen evidence. Run scoped `wctl doc-lint` and
`git diff --check`. No required test depends on a private live project: preserve
the records needed for analysis in the repository. This phase is evidence
capture and interpretation, not implementation or a model repair claim.

## Recovery and Scope

Use additive output folders and refuse overwriting retained extracts. Ignore
unrelated worktree edits. Keep all live projects and Forest source/binaries
unchanged. If a needed record is absent, record the gap rather than fabricate
timing from scalar metrics. No new dependencies or infrastructure are needed.

## Surprises & Discoveries

Cedar's normalization correction preserves all 6048 hillslope files and
daily totalwatsed exactly versus 261009, but reduces sampled outlet volume
0.049858%. Its apparent accounting-gap improvement is therefore partly lost:
the candidate gap remains close to 260803, not zero. Large first-maximum
time shifts can select different near-equal crests/rounded plateaus; the
worst baseline-relative shift is 1220 minutes while centroid changes less
than a minute. Those distinctions are retained in the timing audit.

The requested hillslope studies show exact isolation: both mutation ledgers
and all 1378 runs' standard outputs match wepp_261009; all 768 disturbed
output files match the paired same-container release run. The only physical
input-file byte differences in the matrices are generated soil date comments.
Channel-event consequences cannot be adjudicated by these hillslope checks.

The same peak appearing in two output products is not independent physical
validation: both use the routed maximum. Published undisturbed hillslope peaks
are smaller than burned on January 18, and both PASS products agree on the
selected fields. The existing channel record is peak-only at configured
600-second spacing; it cannot establish pulse width. See ../../opening-findings.md.

## Decision Log

2026-10-10: Explicit release authorization supersedes the prior promotion
hold. ADR-0084 preserves the normalization rule, rationale and disclosed
ordinary-event consequences. Remove only the undeployed WEPPpy binary pair
and sidecars, not historical evidence or Forest release archives.
2026-10-10: Cedar uses unchanged frozen 10 cm RRINIT inputs, two fresh
same-build lanes and the original positive-time sampled integration
convention. Keep totalwatsed, reported channel volume and sampled integral
distinct. Cedar water results support the bounded objective, not universal
closure or global release acceptance. No additional model patch is needed
for this verification.

2026-10-10: Preserve the new candidate studies separately from published
release reports. Mutation inputs retain their historical frozen defaults;
disturbed rankings use current adopted defaults. Do not conflate the designs
or treat identical hillslope results as channel acceptance.

Candidate authorization: Roger said proceed after the localized mechanism was
reported. Production-source change is limited to CHRQIN's denominator sample
accounting. Regression fixtures are repository-contained; external watershed
runs are supplementary acceptance evidence, not required private-resource gates.
No estimator, routing state, timestep or parameter changes are included.

Observer scope: source diff identifies new day-to-day channel state carry as
one candidate alongside mixed-flow source handling. Record state before/after
carry, incoming/source maxima, coefficients and end-of-day internal state for
the three-day event context. Restrict logging by date; do not perturb timestep
or disable features. This is observability, not a behavioral ablation or fix.

2026-10-10: Roger explicitly classifies the peak as a defect on physical
site-specific grounds. Continue bounded investigation under that classification.
First compare the two released binary pairs at the inputs to 406. No mixing
PASS formats, no numerical threshold tuning, no production fix before mechanism
evidence. Any further observation must be justified by the trace, not a new
general conservation or routing-reconstruction objective.

Old-release control: Roger supplied a fork run with `wepp_260803`. Verified
same-build hillslope regeneration and matching effective inputs. The January
18 undisturbed peak is 25.41 times larger in 261009 at almost unchanged daily
volume. Treat this as a release-dependent regression candidate needing causal
explanation, not proof that a specific estimator or routing patch is defective.

Continuation authorization: Roger requested further investigation. Select nine
of 128 channels in the lower network, not a watershed-wide instrumentation
campaign. Static topology and existing output selectors are sufficient for
the next observation. WEPP element 412 maps to Topaz 24 and channel ordinal
128; earlier notes incorrectly called 412 a Topaz identifier. Numeric output
selection was correct and historical artifacts are preserved with this correction.

Replay authorization: Roger requested output-only replay capture. Original text
PASS files were removed after interchange; same-build regeneration from exact
staged inputs is a prerequisite, not a parameter experiment. Use the WEPPcloud
container runtime. Bound this to 568 hillslope regenerations and four watershed
runs (two scenarios, output modes 1 and 3), all 45 years. Stop on unexplained
baseline or observer divergence. No source change, timestep change or repair.

2026-10-10 02:05 UTC: Roger explicitly requested an investigation treating the
event as an outlier, not a defect. Adopt this as the starting scientific contract.
The earlier comparison record remains intact; this separate package owns
subsequent inquiry. Broad defect repair and conservation closure are out of scope.

## Outcomes & Retrospective

Release handoff complete: wepp_261010 replaces undeployed 261009 in WEPPpy,
with verified source identity, executable equivalence, required gates and
fresh published rankings. Supplemental plain/Roads/AgFields replays complete
all 45 years. An optional committed-fixture replay is unavailable because its
topology files were never included; the failure is retained, not called passed
or replaced with a mandatory private gate. No production deployment occurred.
See [handoff](../../release-handoff.md) for scope, hashes and limitations.

[Cedar verification](../../cedar-results.md) is complete: all 1728 hillslopes
and both 24-year watersheds succeeded; native conversion accepts every
record. Yield matches 261009; sampled volume is +0.001008% versus 260803.
322 retained screening windows range -0.154% to +0.619% in volume versus
260803, with examined peak-time ambiguities. Accounting discrepancies and
the incremental reduction versus 261009 remain disclosed. No release follows.

Requested follow-up studies are complete; see [results](../../hillslope-studies.md).
Mutation: 1368 study cases plus ten neutrality controls, zero failures,
identical full ledgers and standard outputs. Disturbed: 96 cases per build,
99 pytest checks each, identical outputs and rankings. Fresh figures and
reports are archived. No model code changed in this follow-up. Promotion
remains held for the separately documented watershed-event review.

Mechanism located: the initialized CHRQIN path subtracts `qin0(1)` from the
normalizer but still adds it to the source. Small isolated rainfall components
expose this legacy indexing error. Production-object probes reproduce H101
795.732666 and H234 184.997849 m3/s source maxima. Observer-only watershed run
matches 293 uninstrumented output files byte-for-byte. The extreme source
inputs form before channel state carry; all event-day channels have one segment
and no observed initial-state change from carry at printed precision.
Correcting denominator sample accounting is the next bounded candidate, not
forcing `nt0=0` or changing routing. No behavioral patch has been implemented.
See ../../mechanism-findings.md.

The paired lower-network trace is complete. The pulse is already large at 406,
before the final three trunk reaches; it grows another 13.79% downstream.
Expanded EBE output required partition-aware auditing rather than whole-file
comparison. Both runs retain exactly unchanged outlet EBE, ledger and series
rows, plus 290 byte-identical common files. The cause remains open; inputs
from 402/403 and state at 406 are the next bounded observation. No physics
or timestep changes. See ../../upstream-findings.md.

Authorized output-only replay completed: 568 hillslope regenerations, two
peak-only controls and two full-series watershed runs, all covering 45 years.
Controls match original EBE exactly; all 292 common files except `chan.out`
match byte-for-byte in each observer pair. All 16,437 printed daily maxima
also match. January 18 has a large early undisturbed pulse with uneven rebounds.
The next decision is a narrow upstream/source trace, not a presumed repair.
See ../../output-replay.md and its archived plots/series/receipts.

Investigation opened and the first read-only window captured. No causal
conclusion, model change or rerun. An isolated same-build replay using the
existing full-series output selector is the proposed next observation, subject
to complete context staging and observer-neutrality review. Do not interpret
this suggestion as authorization for broader reconstruction or a repair campaign.

Validation: 25 retained artifact hashes verified; January 18 outlet values
reproduced exactly; 8,520 hillslope/date comparisons match across the two PASS
products. Scoped documentation lint and diff checks pass. No production code
was changed and no model/test-suite campaign was run.
