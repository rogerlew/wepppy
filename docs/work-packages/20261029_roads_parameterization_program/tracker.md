# Roads parameterization program tracker

Active: [ExecPlan](prompts/active/program_execplan.md).

2026-10-30 UTC: operator authorizes one autonomous program with a model-acceptance
stage followed by a user-facing configuration view. Explicit clarification: users
need not edit CSV. Active goal created; no token budget imposed.

Current: acceptance rules and seven-development/six-withheld material split are
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
