# Correctness and user-experience review — M3 Run preparation

Date: 2026-09-15. Independent reviewer: source_contract_review. Contract ancestor
e8c40adda; authority is production_m3_runtime.md, Run-preparation amendment.
Outcome: normal Run M3 prepares missing sources and produces current numerical
results without a manual operator preparation step.

## Runtime states and evidence

| State | Required outcome | Evidence |
| --- | --- | --- |
| Absent pointer | Automatic preparation and calculation | Fresh-basin native test on two grids/keys; real overpriced-sprawl Run |
| Empty/legacy pointer | Local-only explicit unavailable result | Unit tests for {}, schema-v1 and null entries; native zero-support test |
| Populated | Reuse, no reacquisition | Fresh-basin rerun and retry call counts |
| Malformed/dangling pointer | Explicit failure without network | Unit tests for zero bytes, schema, populated-empty and symlink |
| Input/attempt change | Reject promotion or rebase | Real owners, activation and files; attempt/model/frequency/SBS/WAL/pointer tests |
| Acquisition failure | Retain diagnostics and prior result | Timeout regression with real preparation receipt |
| Calculation failure after promotion | Keep pointer/prior result, reuse on retry | Expanded fresh-basin regression with genuine prior accepted result |

Input dimensions include two spatial grids and mapunit keys, M3 with CLI test
rainfall and NOAA live rainfall, available and unavailable support. No claim of
exhaustive geographies or all remote-service failure modes is made.

## Error policy and findings

Optional source absence is a valid first-use state and now creates inputs.
Malformed metadata is exceptional and fails strict existing parsing. Remote
failure fails the attempt with retained logs and existing retry guidance.
Concurrent changes supersede the attempted input binding; no stale publication.
Genuine prepared zero support remains an unavailable scientific result.

No concrete implementation correctness finding remained. The reviewer identified
one missing recovery test (automatic promotion then calculation failure); it was
added before closeout. Tests mock remote delivery only; activation, owners,
NoDb persistence, rasters and native numerical composition remain real.

## Verdict

Bounded implementation reviewed; real first-use acceptance produces all 27,450
event probabilities, 12 design and 3 inverse results with exact-mask and
independent arithmetic checks. See [live evidence](20260915_live_acceptance.md).
Final independent focused suite: 44 passed, 8 warnings in 119.47 seconds.
Full-suite results are recorded in tracker.
No remaining medium/high finding. Security is reviewed separately.

Final test-only follow-up: the older prepared-run worker-error fixture now supplies
valid empty metadata rather than unintentionally testing first-use acquisition.
Independent reviewer approved the five-line correction; all original failure,
saved-preference and retained-diagnostic assertions remain. Production module:
56 passed. Canonical archive/restore regression: 1 passed (21 deselected).
