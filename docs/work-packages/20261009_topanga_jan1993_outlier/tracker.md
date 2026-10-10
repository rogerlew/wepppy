# Topanga January 1993 Outlier Tracker

## Progress

- [x] Complete authorized wepp_261010 release/vendoring and retire undeployed
  261009 from WEPPpy. Production deployment remains separate.
- [x] Rerun Marta's Cedar project with fresh candidate and release hillslopes;
  compare totalwatsed yield and full outlet discharge against 261009 and 260803.
- [x] Run requested candidate mutation census and paired canonical disturbed
  ranking matrix; preserve candidate evidence separately from release reports.
- [x] Roger authorized output-only replay capture after the opening review.
- [x] Stage exact inputs and pinned binaries in an isolated parent/Omni layout.
- [x] Regenerate removed text PASS files and verify retained scalar PASS parity.
- [x] Reproduce original watershed EBE in peak-only control lanes.
- [x] Capture full time-step outlet output and verify observer neutrality.
- [x] Preserve event plots, series and the bounded interpretation.

- [x] 2026-10-10 02:05 UTC: open on Roger's explicit outlier-not-defect basis.
- [x] Link preserved before-investigation watershed output snapshots.
- [x] Extract and verify the January 10-24 hillslope/channel/state window.
- [x] Read back input-source metrics, timing fields and their units.
- [x] Record what existing outputs establish and what they cannot establish.
- [x] Propose the smallest additional observation if causal attribution needs it.
- [x] Complete the authorized isolated, output-only replay.
- [x] Complete the paired nine-channel lower-network trace and observer audit.
- [x] Inspect incoming channels/state; the observer localizes source inflation upstream.
- [x] Reproduce the CHRQIN indexing defect with unchanged production routine objects.
- [x] Implement conditional time-zero subtraction and demonstrate red/green tests.
- [x] Complete fresh candidate-build Topanga/Rattlesnake comparisons and review departures.
- [x] Roger explicitly authorized promotion after the documented follow-up studies.

## Decision Log

Subsequent authorization: output-only replay is now permitted. Regenerate
missing text PASS with original binaries and unchanged inputs, then compare
output modes 1 and 3 at the same 600-second routing interval. Preserve full
45-year antecedent history and stop on unexplained baseline/observer drift.
This supersedes the opening-phase no-rerun boundary, not the no-repair boundary.

Roger's starting position governs classification: investigate an outlier,
not a presumed defect. Keep physical/model explanations and implementation
issues as competing possibilities. No new simulations or patches in the opening
read-only phase. Do not reopen comprehensive conservation or routing redesign.

## Current Disposition

**Released and vendored as wepp_261010.** See [handoff](release-handoff.md).
Required gates, fresh release matrix and exact-build integration checks pass;
the unavailable optional fixture attempt is separately documented. Roger requested
wepp_261010 and removal of never-deployed 261009 from WEPPpy. This supersedes
the earlier hold below; the measurements and limitations remain unchanged.
See [ADR-0084](../../adrs/ADR-0084-chrqin-source-normalization-release.md).

[Cedar verification complete](cedar-results.md): 1728 fresh hills and two
full 1980-2003 watersheds complete. Totalwatsed is identical to 261009 and
only +0.393 m3 versus 260803. Sampled outlet volume is +0.001008% versus
260803 and -0.049858% versus 261009. The remaining integral-ledger gap is
slightly smaller than 260803's, but larger than 261009's. Event/timing and
annual evidence support Cedar water preservation; this does not adjudicate
the separate Rattlesnake sediment consequences or authorize promotion.

**Candidate validation complete; promotion held.** See
[hillslope studies](hillslope-studies.md): all 1368 mutation cases plus ten
observer controls complete, with exact release-ledger and standard-output parity.
All 96 disturbed cases per build complete with 768 byte-identical output files;
runoff/sediment/maximum-peak ordering remains 23/24, 24/24 and 18/24.
Fresh Figures 1-3 and candidate ranking tables are retained separately.

For watershed consequences, see
[candidate results](candidate-results.md). All 714 freshly regenerated hills
and four full-record watersheds completed. Target peak: 707.63910 to 12.50683
m3/s. Ordinary burned Rattlesnake peaks and event sediment materially change;
unchanged hillslope sediment inputs and near-identical total volume do not
establish event-level acceptability. No release, vendoring or deployment.

### Historical Dispositions (Superseded)

Candidate underway: source correction is limited to the CHRQIN denominator.
45 focused checks and 163 maintained Forest tests pass. Correct-profile builds
pass smoke and all 12 watchlist cases. Initial parallel mixed-profile build was
invalid and is retained as a failed build attempt, not hydrological evidence;
separate builds and fresh regeneration are used for the accepted comparison lane.

[Mechanism located](mechanism-findings.md): CHRQIN's pointwise normalization
subtracts the first valid sample when `nt0=1`, then adds it with an inflated
scale factor. Actual production-routine probes reproduce approximately 796
and 185 m3/s source pulses from H101/H234. The observer is byte-neutral across
293 outputs and locates the pulses before channel routing/state carry.
The smallest candidate is correcting sample accounting, not replacing MIXPEAK
or routing. No behavioral patch or corrected watershed validation has run yet.

Confirmed defect by Roger's site-specific judgment: the 707.64 m3/s peak is
not physically acceptable here. Mechanism and responsible release interaction
remain unresolved. The previous outlier-first premise is superseded, not erased.
Next diagnostic: paired old/new same-build traces across the inputs to 406.

[Same-input 260803 comparison](260803-comparison.md): the user-supplied fork
has verified matching physical inputs and 568 successful old-build hillslope
logs. January 18 undisturbed peak is 27.85154 m3/s in 260803 versus 707.63910
in 261009 (25.41 times), with volume -0.482%. This is now a release-dependent
outlier/regression candidate; no individual patch or defective mechanism is
yet identified. Both old and new snapshots are retained.

[Lower-network trace](upstream-findings.md): the undisturbed pulse is already
621.86023 m3/s at WEPP element 406, growing to 707.63910 at outlet 412.
Small neighboring branches do not contain a comparable pulse. Outlet rows
remain exactly unchanged by expanded output selection. The earliest observed
large pulse is at 406; its incoming channels 402/403 were not yet traced.
Identifier correction: WEPP element 412 maps to Topaz 24, channel ordinal 128.

[Output-only capture complete](output-replay.md): 568 regenerated hillslopes
match retained PASS fields; both 45-year controls reproduce original outlet
results. Both full-series runs have 292 comparable files byte-identical to
controls, excluding the intentionally changed channel series. The January 18
undisturbed trace shows an early 435/708 m3/s pulse and repeated rebounds.
Cause remains unclassified. Live inputs and model source are unchanged.

[Opening findings](opening-findings.md): the undisturbed published hillslope
peak inputs are smaller, not larger, than burned on January 18; PASS products
agree. Existing channel output is peak-only, so full time-step outlet output
was the proposed next observation and has now been captured. No cause is established.

Open. The peak is present in two output products, but its physical or numerical
origin is not established. A 9.3-fold scenario difference at similar daily
volume is a reason to inspect timing and source contributions, not a proof of
incorrectness. Preserve earlier favorable return-period comparisons separately.

Validation: 25 artifact hashes and 8,520 hillslope/date PASS comparisons verified;
frozen January 18 outlet values reproduced. Scoped documentation lint and diff
checks pass. No model source edits, reruns, deployment or defect declaration.
