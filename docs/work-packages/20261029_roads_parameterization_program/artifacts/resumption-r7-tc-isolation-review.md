# Roads time-of-concentration diagnostic isolation: independent review

**Verdict: PASS for the minimal conformance repair and fresh five-context trial, with native outcome acceptance still pending.** No unresolved correctness finding blocks this bounded repair. The prior v1 context remains a failed baseline-preservation attempt; its native completion does not make it an accepted workflow.

## Confirmed defect and repair

**R7-TC-01 — High, baseline diagnostic corruption; repaired.** `_prepare_roads_runs_workspace()` linked baseline `wepp/runs/tc_out.txt` into the Roads workspace. The selected native source opens `tc.txt` to enable the diagnostic, then opens and writes `tc_out.txt` in its working directory (`src/wshdrv.for:353–361`). A Roads watershed run therefore wrote through the symlink into the copied baseline.

I independently rehashed the failed `current-roads-v1/inslope_bd` context against its `validation-baseline-before.json`: exactly `wepp/runs/tc_out.txt` changed. The Roads path remains a symlink to that baseline file. The baseline diagnostic changed from SHA256 `02a434a67f75cfd33d85a2b224aae536784e9a9a02ffa76a9b4750a7aad04ec3` to `4761c5fd127642ada46e984b2254958a67ecb4cc79aaf26070f30b1642987830`; the linked Roads path has the latter hash. This is direct artifact evidence, not an inference from controller status.

The change at `wepppy/nodb/mods/roads/roads.py:3575` excludes only the generated `tc_out.txt` alongside the existing `pw0.run`/`pw0.err` exclusions. The `tc.txt` input remains available. Native diagnostic generation, parameters, thresholds, error handling, locks, and report formulas are unchanged. Every Roads design uses this shared workspace boundary, so the repair covers all four declared positive designs and the negative context without separate design-specific behavior.

This restores the unchanged [preparation lifecycle contract](../../../schemas/roads-preparation-lifecycle-contract.md#consumer-behavior-and-acceptance), which requires the baseline to remain intact. It does not require a new behavioral contract or parameterization ADR. The Roads README records the exact input/diagnostic distinction. No production source was edited by this reviewer.

## Failure-class assessment

| Writer or alias | Evidence and disposition |
| --- | --- |
| `tc_out.txt` | Confirmed actual overwrite. Present in the successful public-controller baseline; native rewrites it when `tc.txt` exists. Excluding the generated diagnostic closes this path. |
| `pw0.run`, `pw0.err` | Existing exclusions already isolate the Roads watershed deck and runner log. Their handling is unchanged. |
| `chan.out`, `chanwb.out` | Native writers exist (`wshinp.for:496–499`), but the canonical public controller moves `*.out` from runs to output before baseline completion (`wepp_run_service.py:291–294`). Both are absent from the declared baseline runs. No additional ordinary completed-baseline alias defect was demonstrated. |
| `chntyp.txt`, optional `ch-detailed-out.txt` | Native code closes with `status='delete'` and recreates the working-directory path before writing (`wshdrv.for:515–520,542–548`). The observed baseline `chntyp.txt` remained unchanged; the resulting Roads file is independent. These do not follow the observed write-through path. |
| Baseline hill run/error names | Current baseline IDs are 1–66; Roads synthetic segment IDs start above 900000. The observed run did not overwrite a baseline hill deck or log. No new ID policy is introduced. |
| Opt-in `wepp_observe.log`, native scratch/impoundment diagnostics | The source includes additional conditional writers, including append to `wepp_observe.log` when `wepp_observe.on` exists. These markers/files are absent from the declared ordinary baseline. Such instrumented or specially configured workspaces remain a conditional alias-risk class; this repair does not certify them or claim a universal native filename inventory. They need a separate concrete inventory/reproduction before such a lane is admitted. |

The last row is an explicit coverage limit, not a reason to silently expand this routine repair into a new staging policy. No other file in the failed baseline's protected native inputs/outputs changed. Existing source/baseline invariance checks stay enabled for the fresh trial; no changed file is exempted from those checks.

## Regression evidence

The new `test_roads_workspace_preserves_baseline_time_of_concentration` uses real temporary files and the real workspace/link helper. It writes a Roads diagnostic and asserts the baseline bytes remain unchanged, while separately checking the retained `tc.txt` input. This tests the filesystem effect rather than mirroring the exclusion set.

The retained pre-fix run fails exactly on the baseline assertion (`/tmp/roads-tc-regression-before.log`, SHA256 `4195126e5ca077b19b2176beae0dd4f8b99dc849780828b51cd67de0b89ab933`). I independently ran the focused test through `wctl`: **1 passed**. The author's retained full controller-module log reports **50 passed** (`/tmp/roads-tc-regression-after.log`). Existing unrelated dependency deprecation warnings remain. Full repository validation and the fresh native controller trial remain separate acceptance evidence.

Reviewed production source SHA256: `7aa5cd95f17b493e1f3543b607b2d67b717edced1fb8c574c5c516ebb2fa74df`. Reviewed test module SHA256: `e0b253340db2004cf12bec03f0bc695047aae4bbbf5b3a848531756d15c3e149`. Selected native writer `wshdrv.for` SHA256: `179fa57c1aa64dd07281e92dbea58556daf8c2dfad838bda956f2a995bab492e`.

## Fresh declaration and remaining gate

The new `current-roads-v2/declaration.json` has SHA256 `d66eb2edd76242fce7515ff9179c089180b37fb4977b2cfd30153b10bddd4196`. Its helper, [current_r7_roads_v2.py](current_r7_roads_v2.py), has SHA256 `7ac93e3d7ce0385ffa4d139ada2d54fabfa896262115843b374d3aa213146c54`. The source remains the independently reviewed `current-project-v2/baseline`; the failed v1 Roads copy is preserved separately.

Independent Compose readback verifies all 1,176 dependencies and the exact 3,537-entry source inventory through the actual driver's read-only preflight functions. The source inventory equals the pre-failure v1 declaration exactly, the same five cases remain declared, both installed r7 binary hashes match, and UID/GID remains 1000/993. No new execution-start receipt was present during review. Only the new declaration/root may execute with the repaired source; the original frozen v1 declaration must not be reused.

Postexecution review must still establish unchanged baseline `tc_out.txt` and all other protected baseline files, fresh independent Roads diagnostics, four successful positive contexts, the exact two expected negative geometry failures, and installed accounting/report artifact correctness. This review does not grant deployment, RQ/browser/catalog parity, a particle-audit waiver, generated-soil parameter acceptance, or global scientific acceptance.
