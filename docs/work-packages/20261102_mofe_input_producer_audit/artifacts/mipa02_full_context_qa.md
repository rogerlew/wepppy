# MIPA-02 supplementary full-context QA

Reviewer: `mipa_qa`, 2026-11-03 UTC. **PASS for the complete configured copied-project
workflow and its bounded r5/r6 comparison.** This supplements the earlier reviews;
it does not change the frozen PDF, native source, binaries, or original project.
Evidence root: `/wc1/holdouts/mipa-native-r6-20261102`.

## Correction to the earlier project evidence

The original `actual-project-v1` preparation copied 361 model inputs but omitted
`gwcoeff.txt` and `wepp_ui.txt`, although the copied project enabled baseflow and
the UI seepage path. Its successful execution, reader results, and exact r5/r6
parity remain valid only for that partial input context. They did not establish
the complete configured workflow.

The complete `Wepp.prep_hillslopes` invocation now retains 363 model inputs.
QA independently rehashed all of them: the original 361 bytes are unchanged,
and the two additional companions match the saved settings. Adding those
companions changes **433 of 504** r6 output files relative to partial preparation.
That difference concerns execution context, not a change of WEPP revision.

QA rehashed the preserved 361 inputs and both preserved sets of 504 partial-run
outputs under `actual-project-full-v1/prior-partial-preparation` and
`prior-output-at-execution`. They match the original receipts. The initial
435-file pre-execution listing included 72 old `.err` logs; it remains preserved
as `pre-execution-files-including-logs.json`. The corrected `inputs.json` excludes
those mutable logs, and its remaining 363 entries exactly match that listing.
The preparation helper now excludes `.err` files.

## Configured execution and installed consumers

The saved settings agree with the copied NoDb state: `run_baseflow`,
`run_wepp_ui`, `run_pmet`, and `multi_ofe` are true; frost and snow are false.
`gwcoeff.txt` contains groundwater storage 0, baseflow coefficient 0.04,
deep-seepage coefficient 0, and threshold area 1, matching `baseflow_opts`.
The empty `wepp_ui.txt` is the native presence flag. `pmetpara.txt` is retained;
disabled frost/snow companions are absent.

All 72 r6 hill logs contain both native consumption markers:
`->Gwcoeff parameters set` and
`->WEPP hourly water seepage update set (UI code)`.
They identify the installed-name resolution
`/workdir/wepppy/wepp_runner/bin/wepp_261029_hill`, with the expected r6 hash,
35 simulation years, and successful completion without runtime errors.
The receipt records service UID 1000/GID 993. QA independently rehashed all
504 newly generated raw outputs.

QA rehashed all six Parquet datasets against `readback.json`, checked their
metadata row counts, and reconstructed the installed `HillslopeWatbalReport`
through `wctl exec weppcloud`. It reports 72 hills, area 5,493,585.58 square meters,
and WaterYears 1986–2021. Those 36 water-year bins cover the 35 calendar-year
simulation; they are not an extra simulated year.

| Dataset | Rows |
| --- | ---: |
| `H.ebe.parquet` | 8,158 |
| `H.pass.parquet` | 920,448 |
| `H.wat.parquet` | 3,004,240 |
| `H.element.parquet` | 230,117 |
| `H.soil.parquet` | 3,004,240 |
| `H.loss.parquet` | 360 |

All 22 emitted floating water columns are finite and non-null across every row.
The optional `InterceptionStorage` column is entirely null because this native
25-column water format does not emit it; the interchange schema explicitly
allows that omission. This readback does not establish full water-budget closure.

## Same-input revision comparison

`actual-project-full-r5-v1` copies the same 363 model inputs into a fresh root.
QA rehashed those inputs and both binaries, checked every r5 execution log for
the retained r5 path/hash, both companion-consumption markers, and 35 successful
years, and independently compared all 504 raw output hashes with installed r6.
**Every output is byte-identical.** The comparison receipt joins the verified
input and output manifests and records zero differences in Q, Ep, Es, Er, Dp,
latqcc, and terminal printed soil-water storage for all 235 OFEs, each with
12,784 rows.

This project is a non-discriminating control for the ownership repair. The
distinct-material S01 histories remain the discriminating defect evidence.
Exact parity here does not establish watershed-outlet behavior, conservation,
field validity, or compatibility beyond the declared release scope.

## Verified identities and report disposition

Paths below are relative to the evidence root unless otherwise stated. Receipt
hashes bind the independently verified per-file input/output/Parquet hashes.

| Artifact | SHA256 |
| --- | --- |
| `actual-project-full-v1/settings.json` | `70f81a44ed4940b9b6731ea1c335e6b88a63ce86094560ece24e103c09aa18b3` |
| `actual-project-full-v1/inputs.json` | `c0e25e361dfe20af0a0edc96e51917a6639f95c259a764d0759f7ae7296770ee` |
| `actual-project-full-v1/receipt.json` | `7bfb76923261862af25ee18e4ca80bc0834317fa772af1d2a3fb9c9a9d4ace57` |
| `actual-project-full-v1/readback.json` | `6d5a29dd1c12a92178854dcb372925e71cffd926ea01ca3951dad66c544cfb29` |
| `actual-project-full-r5-v1/receipt.json` | `b6fb666e6908bbf2feb823cd4c6f115a752fb7250c2ca357937ccb832e951991` |
| `baseline-r5/vendored-wepp_261029_hill` | `a031713759b3bed0412a9a2b7413d1fbabe9869f66d7611d7c4684042589a933` |
| Installed r6 hillslope binary | `ef8a23f494b595fba48208c196b3f673f6834feea90d3a024179c7028eecea31` |

The three terminal logs are `actual-project-full-v1.log`,
`actual-project-full-readback-v1.log`, and `actual-project-full-r5-v1.log`.
The replay helpers are `run_native_actual_full_context.py`,
`read_native_actual_project.py`, and `compare_native_actual_project.py` beside
this review. The comparator now says “comparison completed”; its optional
`--expect-identical` asserts zero output and water differences when parity is
the intended gate. This resolves the earlier misleading unconditional PASS text.

The frozen `main-r6.pdf` still has SHA256
`247176029b2537f3a1676cd5fa6ff2797793839dc361240cfcdbe24ae938aa66`.
Its bounded statement that a copied 72-hill/235-OFE project completes 35 years,
produces 504 outputs, and passes installed interchange/report readback is now
supported by the complete configured workflow. No PDF wording correction is
required for that statement. The active package must retain this correction
and these supplementary identities rather than attributing configured-workflow
acceptance to partial v1 evidence. Earlier reviews and the PDF remain unchanged.

No blocking QA finding remains for this supplement. Residual limits are the
fixed-cohort nature of the replay helpers, optional interception storage absent
from this output format, and the broader validation/compatibility gates tracked
separately. This review does not approve deployment or claim a full-suite pass.
