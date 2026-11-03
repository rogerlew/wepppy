# Current project v1: failed workflow and bounded native evidence

Reviewer: `mipa_qa`, 2026-11-03 UTC. This additive outcome review preserves the
pre-execution review and all v1 evidence. **The complete v1 workflow failed.**
Successful native simulation does not clear the subsequent postprocessing failure.

## Confirmed harness omission

`baseline-run.log`, SHA256
`84fc8592bb042b5434cfbcdec470d43e7fbc330fd6faf12d1143bf67f290ad57`,
shows all 66 hillslopes and the watershed completing before `make_loss_grid`
raises a GDAL error creating `wepp/plots/loss.tif`: its parent directory is absent.
`baseline-native-completed.json` was never written. Watershed interchange at the
end of `run_watershed` was not reached, so existing hill/loss interchange files
cannot establish complete watershed postprocessing.

The experiment harness created runs/output directories but omitted canonical
`Wepp.clean`, which also creates plot, stats and flowpath run/output directories
(`wepppy/nodb/core/wepp.py:2037`). The normal RQ path calls this before preparation
(`wepppy/rq/wepp_rq.py:799`). The earlier pre-execution review did not catch that
workflow initialization gap. This is a confirmed harness omission, not evidence
of a failing native engine or authorization to alter production behavior.

The smallest repair is a fresh disposable v2 with canonical cleaning before
complete preparation, followed by the already required hill interchange and
watershed workflow. Preserve failed v1 without adding its missing directories or
resuming it in place. Full v2 results need their own artifact and reader review.

## Independent retained-output readback

Read-only helper `read_current_r7_native_v1.py`, SHA256
`33a74045d4b97089cb76d6608524766922ed6421d277c39c270c07e8726af20f`,
ran through `wctl exec -T weppcloud python`. It invoked no native executable or
converter. Its exclusive receipt is
`resumption-r7-current-project-v1-native-readback.json`, SHA256
`8c227aa8e6c6ab271219cfa1f6534c7eb35f6e27ca6b92fd8c31e77211849f3e`.

- All 67 runner traces identify the exact declared role binary and contain native
  success banners, UI/groundwater/PMET activation markers and simulation years
  1–16. No later retry is present. The execution-start receipt binds the reviewed
  v3 declaration; all 344 declared model inputs remain byte-identical.
- All seven ordinary output families exist for each of 66 hills, totaling 462
  hill files, plus eight raw watershed files. All 413 run artifacts and 487
  output/interchange artifacts are individually hash-bound in the receipt.
- Raw PASS records cover every daily date from 2000-01-01 through 2015-12-31 for
  all 66 hills: 385,704 records, comprising 11,756 EVENT, 256,356 SUBEVENT and
  117,592 NO EVENT records. The reviewed format/record-width parser verifies
  finite daily fields and required component trailers.
- Existing installed WAT interchange contains 1,127,892 rows: every one of 193
  OFEs has exactly 5,844 unique expected dates. All available floating WAT fields
  are finite. `InterceptionStorage` is unavailable for all rows, retained as null
  rather than invented zero.
- Existing ELEMENT interchange contains 112,125 rows with nonnegative SedLeave.
  Raw channel WAT contains 157,788 finite rows covering complete daily calendars
  for 27 channels. Existing annual outlet-loss interchange covers 2000–2015.
- Before/after inventories are identical. QA did not modify any accepted inputs,
  traces, outputs or interchange files during readback.

These are bounded artifact findings, not a full water/particle closure audit,
field-validity claim, coefficient-ownership discrimination or workflow pass.
Snow has no dynamic consumption trace in this run. The earlier uniform PMET
coefficient limitation also remains.

## Native notice retained

Only `pw0.err` reports that channel management crop `Fallow m` is absent from the
PMET default data and that the engine selects `loam-forest`. The receipt preserves
the exact notice. Hill traces have no corresponding notice. This fallback is
separate from the missing plot directory and must not be described as explicit
channel PMET identity coverage merely because the PMET activation marker appears.
Any later acceptance claim must disclose or separately resolve its intended
channel semantics; this review makes no parameter change.

No r4/r7 panel conclusion or withheld-material outcome is inferred from this
failed workflow. Current-project v2 remains a separate experiment, and all frozen
panel declarations, scoring inputs and prelaunch reviews remain unchanged.
