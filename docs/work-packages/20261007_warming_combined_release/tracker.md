# Combined release validation tracker

**Started**: 2026-10-07 20:54 UTC  
**Status**: Closed, research comparison complete (2026-10-07 22:14 UTC)  
**Security impact**: none; dedicated review not required

## Progress

- [x] Verified recut hashes, source call and makefile linkage for both binaries.
- [x] Defined baseline, input scope, metrics and provisional acceptance screen.
- [x] Stage and semantically validate all three fresh cases on forest.
- [x] Execute all three physical cases (2,592 hillslopes and three watersheds).
- [x] Complete combined-release output-mode parity replay.
- [x] Convert native outputs, test metrics and assess all six figures.
- [x] Retain evidence, write results and close research scope.

## Decisions and risks

Use the frozen 6 October native input snapshot to keep this comparison matched
to the preceding studies. Do not modify the live warming-championship project.
Separate daily totalwatsed agreement from routed discharge and ledger checks.
Reject the superseded same-name binary by SHA256, not filename alone.
Local unrelated staged fixture deletion is preserved; local checkouts are not
pulled across pre-existing changes. Execution uses verified forest binaries.

## Disposition

The requested comparison is complete. Totalwatsed is virtually unchanged;
daily and subdaily routed discharge are not equivalent under the provisional
screen. Results and selected-event evidence are in `results.md`. HV-02/HV-05
and the October 1994 discrepancy remain follow-up science, not part of this
completed comparison. Production is unchanged. Changes are not pushed.

## Execution notes

The initial staging attempt selected `pw0.man` alongside 864 hillslope
management files and correctly stopped at the inventory assertion before
executing any model. Restricted the selector to numeric hillslope IDs, matching
the preceding runner. Retained the failed attempt intact at
`/workdir/warming-combined-release-20261007-attempt1-staging-failure`.
Six metric/date tests pass on forest. They cover identity, scale, offset,
undefined constant/zero references, nonfinite/mismatched arrays and incomplete
or disordered dates. The event windows are seven days for both output types.

At 2026-10-07 21:29 UTC the fresh legacy10 watershed was writing outlet
discharge. The parser was independently exercised against retained historical
legacy10 output and reproduced 1,266,448,890.30 m³ sampled integral,
1,272,337,716.46 m³ ledger volume and −0.462835% discrepancy. This is a parser
control, not a fresh-run result. Source-project baseflow settings were read
back and match the frozen settings. Four scoped Markdown files pass lint with
zero errors and warnings; the initial lint invocation outside its target
directory had path-resolution errors, corrected by running from that directory.

Legacy10 completed all 864 hillslopes and its watershed (495.13 seconds).
All 6,056 raw output hashes match the retained legacy baseline exactly.
The old manifest additionally contains three derived interchange files; these
are excluded from raw-binary-output parity and rebuilt with the current common
converter. Combined10 completed all 864 hillslopes and its watershed (502.60
seconds). Legacy17 is running. Native conversion overlaps completed cases
only, while subsequent physical cases execute in separate directories.

Preliminary full-period combined10 outlet readback gives sampled volume
1,258,874,978.04 m³ and channel ledger volume 1,272,337,751.55 m³: a −1.058113%
sampled-integral/ledger discrepancy. This is not a conservation closure claim.
The sampled integral differs from legacy10 by about −0.60%, already exceeding
the provisional 0.1% daily volume screen. Complete fit and event interpretation
remain pending. Both completed cases have native PASS/WAT conversion with all
expected records accepted and zero rejected records.

Legacy17 completed its 864 hillslopes and watershed (502.41 seconds), with
all 6,056 raw files identical to the historical 17 cm case. The combined-release
output-mode parity replay is running. Full totalwatsed agreement is effectively
exact (+0.304762 m³ over 24 years); combined-release daily routed NSE/KGE/R² are
0.995419/0.970290/0.996189. Subdaily NSE is 0.979740. This distinction must lead
the final assessment rather than an unqualified negligible-change claim.

## Final verification at 2026-10-07 22:14 UTC

All 2,596 model executions pass. Seven canonical output files are exactly
equal in the combined-release output-mode control. All three conversions have
the expected PASS/WAT counts and zero rejections. All 18,168 raw-output hashes
match; consumed inputs and the frozen source remain unchanged. Both legacy
cases reproduce all raw historical hashes. Six metric/date tests pass, and
independent standard-library daily NSE/KGE/R² match NumPy within 1e-12. All
six PNGs were manually inspected; paired daily/event data and provenance are
retained. Completed work-package documentation records the mixed scientific
outcome without changing the prospective limits.
