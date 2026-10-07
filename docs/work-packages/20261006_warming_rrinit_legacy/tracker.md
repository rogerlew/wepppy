# Legacy roughness comparison tracker

## Quick status

Started 2026-10-06 23:45 UTC. Closed research 2026-10-07 00:37 UTC. Security impact none. Requested comparison delivered; hydrograph-conservation investigation remains a follow-up, not a release approval.

## Task board

- [x] Verify original release binary hashes on forest.
- [x] Select frozen source and bounded eight-process execution.
- [x] Stage and verify all matched inputs.
- [x] Complete three original-build lanes and output-mode control.
- [x] Validate outputs and build fresh totalwatsed summaries.
- [x] Compare roughness sensitivity and paired 10 cm builds; review figures.
- [x] Complete results and close research package.

## Decisions

2026-10-06 23:45 UTC: preserve previous package and raw reference outputs. Reuse its runner in a new package and read frozen inputs. Original release, rather than an unpatched rebuild, is the requested comparator; retain source-difference caveats.

## Risks and verification

The corrected and release binaries may differ beyond the return patch; inspect source provenance. The existing approximately 1.3% printed-hydrograph/ledger discrepancy must remain visible. Daily totalwatsed cannot establish within-day timing. Validate printed precision and avoid treating process success as scientific validation. Full application tests are not the primary gate for this offline comparison; no application/model code changes are planned.

## Progress notes

2026-10-06 23:52 UTC: all 864 original 10 cm hillslopes passed; watershed running. Every lane's consumed-input manifest matches the corrected experiment. Native 10 cm PASS/WAT conversion runs concurrently with watershed routing. Source audit compares 485 release source/include/build files against the retained baseline with root sizing includes normalized to the preserved watershed copies: zero differences. Baseline-to-candidate source differences are only `irs.for`, `surpeak.for` and `makefile`. Initial unnormalized audit reported capacity swaps, resolved by inspecting make's stored watershed includes; no source edits were needed.

2026-10-07 00:11 UTC: original 10 and 17 cm lanes each completed 864 hillslopes and the watershed. Native PASS/WAT/totalwatsed prepared for both. At 10 cm, corrected outlet total is 4.25 m³ below original over 1.272 billion m³, but 2,356 daily peaks differ by more than 1%. The printed integral/ledger deficit increases from 0.4628% original to 1.3212% corrected; both exceed a conservative printed-discharge rounding bound. This remains an unresolved hydrograph-validation concern, not a failed job or a license to change model behavior. Two positive-volume/zero-peak H670 days (1985 Julian 324–325) occur in both builds. Original 10→17 cm outlet peak departures range from −18.2345% to +4.8352%, with 26 days exceeding 1%. The 60 cm lane is running.

2026-10-07 00:37 UTC: all 2,596 executions passed, seven canonical output-mode files match, no warnings/stderr or input mismatches, all 98 negative-control files per lane match, and 6,059 output hashes per lane reread successfully. Original project inputs unchanged. Four comparison figures visually reviewed; selection, sign/zero tests, script compilation, links and diff checks passed. Full application suite not run because no application/model code changed. Research closed with the hydrograph-volume shortfall explicitly unresolved; no release or deployment claim. The October 25–29, 1994 ledger is unchanged to 0.29 m³ while its hydrograph deficit increases from 0.83% to 18.30%.
