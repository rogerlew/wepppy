# Warming roughness experiment tracker

## Status

2026-10-06 UTC: closed research experiment. All cases, output-mode control,
post-execution audit, figures, and report complete. No source-run changes.
Security impact none; no deployment or production default changes.

## Task board

- [x] Confirm target: 1,885 initial records at 10 cm; 19 others unchanged.
- [x] Verify corrected binary identities and available disk space on forest.
- [x] Stage and semantically verify all three cases; 1,885 intended changes each
  in rr17/rr60, 19 exceptions unchanged, 14 untouched hillslope controls.
- [x] Stage and validate three cases; execute 2,592 hillslopes and routing.
- [x] Verify output-only parity and source preservation.
- [x] Analyze fresh outputs, inspect figures, document results and caveats.

## Decisions

Use corrected build only, following recommendation and user's instruction to
run the experiment. Keep existing 600-second routing timestep; request full
outlet hydrograph output. Compare full 1980–2003 histories, not selected-year
reruns, preserving antecedent conditions. Dynamic roughness and rill-width
feedback are allowed to evolve normally; only initial rrinit is intervened on.

## Progress notes — 2026-10-06 21:46 UTC

Token mutation self-tests and Python compilation pass; repository diff whitespace
check passes. Two staging-only attempts are retained on forest with suffixes
staging-attempt1 and staging-attempt2. The first was deliberately interrupted
before modeling to tighten initial-record identification. The second semantic
readback correctly rejected an overly restrictive residue-index check on OFE 4.
The selector now accepts integer residue indices beyond 3 and has a regression
test for that case. No model results from either attempt exist or enter analysis.

### Execution progress

Both rr10 and rr17 have 864 successful hillslopes and successful watershed runs.
Each outlet series contains all 8,766 days and 1,262,304 ten-minute samples;
EBE daily volume matches chanwb.out exactly at printed precision. Baseline
reported volume is 1,272,337,712.21 m³ and maximum peak 43.06409 m³/s. rr17 volume
is 1,272,198,063.87 m³ (-0.010976%) and maximum peak 42.77490 m³/s (-0.671534%).
Daily rr17 peaks are lower on 244 days, higher on 413, and equal on 8,109 at report
precision. These were interim results; final acceptance is recorded below.

### Final acceptance — 2026-10-06 UTC

rr60 and the original-output-mode control completed successfully. All 2,596
model executions passed. Seven canonical watershed files are byte-identical
between the observer modes. The 14 negative-control hillslopes retain identical
98-file output sets. All intended rrinit changes were independently checked
at byte boundaries; other management bytes, consumed inputs, and source hashes
remain unchanged. No stderr errors or matching warning lines were found.

Figures 1–3 were generated and visually reviewed. Results and limitations are
in artifacts/results.md; 31 supporting artifacts are fingerprinted in
artifacts/artifact-manifest.json. A matching report bundle is retained at
forest:/workdir/warming-rrinit-20261006/report alongside bulk model evidence.
The approximately 1.3% hydrograph-integral/volume-ledger discrepancy is retained
as a separate unresolved scientific issue. No repair of it is claimed or made.
