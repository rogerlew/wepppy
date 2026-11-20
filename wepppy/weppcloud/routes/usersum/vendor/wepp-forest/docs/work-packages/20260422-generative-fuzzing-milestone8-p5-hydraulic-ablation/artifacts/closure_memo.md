# Closure Memo - Milestone 8 P5 Hydraulic Ablation

## 1. Executive Summary

- Open P5 slices at start: `3`.
- Frozen closure gate enforced exactly:
  - rerun #1 and rerun #2 each `executed >=200`
  - rerun #1 and rerun #2 each `composite_non_pass = 0` to claim `patched`
- Lane outcomes:
  - `L0..L4` produced no measurable improvement under matched seeds,
  - `L5` retained rollback baseline (minimal accepted patch set is empty).
- Per-slice final status counts:
  - `patched=0`
  - `accepted_upstream=3`
  - `deferred=0`

## 2. Per-Slice Final Disposition

Evidence convention:
`/home/workdir/wepp-forest/generative-inputs-fuzzing/results/milestone8_p5_hydraulic_ablation/targeted/{pre_patch,post_patch_rerun1,post_patch_rerun2}/<slug>/{campaign_summary.json,composite_case_disposition.csv}`

| Slice ID | Final Status | Pre (exec/non-pass) | Rerun #1 (exec/non-pass) | Rerun #2 (exec/non-pass) | Patch Reference | Residual Risk |
| --- | --- | --- | --- | --- | --- | --- |
| `wet:moderate:P5_SLOPE_RESPONSE_AMPLIFICATION` | `accepted_upstream` | `200/30` | `200/25` | `200/26` | None retained (L1-L4 rolled back). | Persistent `TRAP_SIGFPE` and `RUNTIME_ERROR` signatures under deterministic reruns. |
| `wet:steep:P5_SLOPE_RESPONSE_AMPLIFICATION` | `accepted_upstream` | `200/31` | `200/32` | `200/28` | None retained (L1-L4 rolled back). | Dominant `TRAP_SIGFPE` remains after all bounded lane attempts. |
| `wet:gradual:P5_SLOPE_RESPONSE_AMPLIFICATION` | `accepted_upstream` | `200/26` | `200/22` | `200/27` | None retained (L1-L4 rolled back). | Elevated `RUNTIME_ERROR` signatures repeatedly point to `stmget.for:122` EOF-read path. |

## 3. Lane Findings Summary

- L0 observe-only baseline on `wet:steep:P5`:
  - `executed=120`, `non-pass=21` (`TRAP_SIGFPE=20`, `RUNTIME_ERROR=1`)
- L1 route denominator/guard (`route.for` / `qostar` boundary arithmetic):
  - no effect (`120/21`)
- L2 `irdgrd` denominator/guard (`sloss.for` / `irdgdx` denominator paths):
  - no effect (`120/21`)
- L3 kinematic-wave slope-coupled arithmetic (`unifor.for` / `sqrt(slope)` path):
  - no effect (`120/21`)
- L4 Manning-path arithmetic (`mann.for` / `sqrt(slp)/chnn` paths):
  - no effect (`120/21`)
- L5 rollback/narrow:
  - accepted patch set is empty; baseline restored.

## 4. Campaign Comparison Summary (M7 Final vs M8 Final)

- Baseline campaign reference (M7 final artifact):
  - `/home/workdir/wepp-forest/docs/work-packages/20260422-generative-fuzzing-milestone7-single-ofe-open-slice-closure/artifacts/pre_post_metrics_comparison.json`
  - Uses `post` section as M7 final baseline (`campaign_root` string: `/home/workdir/wepp-forest/generative-inputs-fuzzing/results/milestone7_single_ofe_campaign_post_patch`).
- M8 campaign root:
  - `/home/workdir/wepp-forest/generative-inputs-fuzzing/results/milestone8_single_ofe_campaign_post_patch`
- Comparison artifact:
  - `/home/workdir/wepp-forest/docs/work-packages/20260422-generative-fuzzing-milestone8-p5-hydraulic-ablation/artifacts/pre_post_metrics_comparison.json`
- Overall:
  - executed: `1008 -> 1008`
  - composite non-pass: `41 -> 91` (delta `+50`)
  - oracle flags: `41 -> 0` (delta `-41`, metric caveat below)
- Per-bin composite non-pass deltas:
  - `dry:gradual +15`
  - `dry:moderate +7`
  - `dry:steep +5`
  - `mesic:gradual +2`
  - `mesic:moderate +8`
  - `mesic:steep +6`
  - `wet:gradual +4`
  - `wet:moderate +9`
  - `wet:steep -6`
- Priority-profile deltas:
  - `P5_SLOPE_RESPONSE_AMPLIFICATION: 11 -> 17` (delta `+6`)
  - `P2_EVENT_EDGE: 4 -> 16` (delta `+12`)
  - `P4_TEXTURE_DENSITY_DISCONTINUITY: 8 -> 7` (delta `-1`)
- Sensitivity gate:
  - M7 baseline: `true`
  - M8 full campaign: `true` (controls `5/5`)
- Oracle-flag caveat:
  - M8 classifier outputs are signature-dominant and carry `oracle_flag=0` while
    composite non-pass remains non-zero; compare composite non-pass as the
    primary closure metric.

## 5. Required Gates Summary

Completed:
- Rosetta host parity: pass.
- Rosetta container parity: pass after bringing `weppcloud` service up.
- wepppy required pytest gates: pass (`28`, `51`, `110` tests).
- wepp-forest classifier gates: pass (`3` tests + milestone0 enforce gate pass).
- Binary-change smoke/replay gates: host smokes pass, full `pytest` pass (`43`).
- Manual reconciled watershed replay gate: success marker found, runtime-error grep gate pass.

Observed risk signal:
- ELF interpreter check is mixed:
  - `/workdir/wepp-forest/src/wepp` requests `/home/linuxbrew/.linuxbrew/lib/ld.so`
  - `/workdir/wepp-forest/src/wepp_hill` requests `/lib64/ld-linux-x86-64.so.2`
- No vendoring action is taken in Milestone 8; interpreter mismatch remains a follow-on binary-release risk.

Completed:
- Markdown lint gate for changed M8 docs passed (`8` files, `0` errors, `0` warnings).

## 6. Recommendation

- Milestone 8 P5 closure: **complete with accepted-upstream disposition** for all frozen P5 open slices.
- Follow-on recommendation for P2/P4:
  - execute a dedicated P2/P4 sibling ablation package using the same frozen two-rerun closure contract,
  - preserve fail-fast/parity semantics,
  - prioritize targeted observability around known event-edge (`P2`) and texture-density (`P4`) signatures before bounded arithmetic edits.
