# Comparator outcome implementation review

Disposition: **fail-closed checkpoint; defer all twelve new-observer processes.** One real native comparator failure prevents acceptance of the complete factorial panel. No observer build/execution, model guard change, numerical tolerance change or production promotion is approved. This reviewer performed read-only inspections and no model rerun.

## Actual outcomes and failure location

All twelve comparator model processes have retained results: eleven return zero with completion markers; 84543461 candidate KS1 returns one without completion. Independently verified every case's declared input hashes and stdout/stderr hashes and all 998 prepared dependency bindings. Independently parsed daily water keys: the eleven completed processes each contain all 17,532 expected unique sixteen-year OFE/day keys. The failed case has 9,830 keys, ending at year 9/day 355/OFE 2; it does not provide a complete history.

The failed stdout locates HOURLY_WATER_UNMET at year 9, day 355, OFE 3, hour 1. It prints signed demand -2.42531928e-12 and available positive relative storage zero. The pinned source assigns hrfin=xfin immediately before this branch, with no intervening mutation; the printed hrfin therefore represents the consumed REAL withdrawal, within stdout precision. The guard tests whether -dble(xfin) exceeds the sum of max(0,ST) across active computational layers and executes STOP 1. Stderr reports STOP 1 plus underflow/denormal status flags; this is not evidence of a SIGFPE as the terminating mechanism.

Available zero refers to positive relative ST, not proof that absolute liquid water or total soil water is zero. The small printed withdrawal does not itself establish its upstream arithmetic origin, conservation significance or a defensible tolerance. Hourly source/return components at this event are not supplied by the suppressed BPO window. Do not silently clamp it, change the guard, call it harmless roundoff, or infer a unique causal effect of frost from this outcome. KS1 also changes conductivity behavior.

The corresponding moderate baseline KS1 and candidate KS0 histories complete. This localizes the observed failure to the candidate/KS1 cell in this finite panel; it does not identify the failing upstream producer or establish universal behavior. Zero/high cases and earlier selected baseline exposure windows cannot substitute for acceptance of the failed cell.

## Stop decision and unused observer work

The failed comparator gate justifies retaining this checkpoint and deferring all twelve observer processes. The new observer was not built or invoked, so its prepared source and controls are draft research artifacts, not native domain/flux evidence. Keep the failed process, partial outputs, incomplete trace and original declaration intact. Any future failure-localization experiment needs a new bounded declaration and unchanged-model comparator evidence; no new repair is authorized here.

The v5 draft logger closes the previously identified nonfinite path by writing/flushing an N record and returning before floating comparisons/extrema. Retained compiled quiet-NaN/Infinity controls at O0/O2 exercise that path and the reader rejects it as incomplete accounting. Selected frozen/bad-count reconciliation and four-/nine-layer support controls are also retained. These controls improve the draft; they do not override the failed comparator gate or approve the unused observer runner.

## Bound evidence

SHA-256:

- Prepared comparator declaration: `742f6964e5cd23385fc2673a58e526d22efb20c49bfe6e65761df0396d220485`.
- Failed process-result.json: `2825b630fed005215f360d55e8049476d9c9940b8c749b34f11ea7343f7ce3aa`.
- Failed case receipt.json: `ff272759bddcc490af23d878913c1da65f63843d664efd13b3c833e19bd81fb8`.
- Failed stdout: `262351a5d14c193d0e7c7a4c7f2a6626d5dadd66f8b2770597b3e0cc8e086c76`.
- Failed stderr: `84caf851125a860cf4bd6128d8582ed0240682fbc4a1fb4acb5c8f1cff8edd7a`.
- Pinned watbal_hourly.for: `b9405810a972dfbaefdd2996aec0c02612fd99dcd9a70e516edaf9dba62ad611`.
- Draft domain-controls-v5 receipt: `389c4f38bb617e1df1dd8090ac550d523cf90545470393d2f0165afa49e74e04`.

Final aggregate receipt independently verifies twelve exact per-case receipt joins: eleven accepted complete histories and one failed native process. Its passed=false status correctly preserves the failed gate; the final high-rock candidate KS1 history is accepted with 249,204 observed frost calls. Aggregate SHA-256: `edf610a1757bbb03a87a72ab9e9a6e42ab4eca7cd95c230206a02e6da492ad9b`. The findings consistently defer the observer, distinguish available relative ST from absolute water, and leave upstream cause unresolved. No raw or prior-root files were written. Reviewer writers are clear after scoped lint.
