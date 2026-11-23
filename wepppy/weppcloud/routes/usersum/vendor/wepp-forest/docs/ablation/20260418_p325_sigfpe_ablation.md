# 2026-04-18 p325 SIGFPE Ablation Record

## Problem statement

Run `srivas42-claustrophobic-shortcut` intermittently failed at hillslope `p325`
with:

- `Program received signal SIGFPE: Floating-point exception`
- backtrace including `param_ -> contin_ -> MAIN__`
- worker return code `-8`

Captured failure artifact:

- `/geodata/wc1/runs/sr/srivas42-claustrophobic-shortcut/wepp/runs/p325.err`

## Baseline signature

Required baseline markers from captured `p325.err`:

- `SIMULATION YEAR =           6`
- `Program received signal SIGFPE: Floating-point exception`
- `param_`
- `contin_`
- `[run_hillslope] attempt 1/4 finished without success marker returncode=-8`

## Hypotheses

- `H1`: numeric singularity in `param` continuity ratio around `shrati` can
  produce divide-by-zero/near-zero arithmetic under certain state combinations.
- `H2`: failure is flaky/non-deterministic and may not reproduce on clean replay
  despite historical production occurrence.

## Ablation matrix and results

### Local isolated replay (`/tmp/p325_ablation_20260418`)

Each iteration used a fresh temp run directory with only:
`p325.run`, `p325.man`, `p325.slp`, `p325.cli`, `p325.sol`.

| lane | binary | change group | iterations | SIGFPE | nonzero rc | missing success marker | outcome |
|---|---|---|---:|---:|---:|---:|---|
| lane0 | `release/wepp_260417_hill` | none | 120 | 0 | 0 | 0 | resolved |
| lane1 | `release/wepp_260418_hill` | none (current release) | 120 | 0 | 0 | 0 | resolved |
| lane2 | `release/wepp_260418_p325guard_hill` | `param.for` guard around `shrati` denominator | 120 | 0 | 0 | 0 | resolved |
| lane_obs | `release/wepp_260417_hill` | observe-only lane | 1 | 0 | 0 | 0 | resolved |

### Remote production-host sample (`wepp1`)

Host preflight:

- host: `wepp1`
- run path exists:
  `/geodata/wc1/runs/sr/srivas42-claustrophobic-shortcut/wepp/runs`

Fresh-temp-dir remote sample:

| lane | binary | iterations | SIGFPE | nonzero rc | missing success marker | outcome |
|---|---|---:|---:|---:|---:|---|
| remote0 | `/workdir/wepppy/wepp_runner/bin/wepp_260417_hill` | 60 | 0 | 0 | 0 | resolved |
| remote1 | `/tmp/wepp_260418_p325guard_hill` | 60 | 0 | 0 | 0 | resolved |

## Source edits and rationale

Edited file:

- `src/param.for`

Edit summary:

- Added a guard around `shrati = 1.0 / ((sterm1/sterm2)-1.0)` to avoid
  divide-by-zero and near-zero denominator collapse.
- Logic mirrors existing defensive pattern already used for `tcrati`.

Rationale:

- Historical failing stack points to `param_`.
- The guarded expression is a plausible singular boundary in that routine.
- Guard is minimal and localized to the failing numerical continuity path.

## Keep / rollback decision

- Keep decision: **keep** the minimal `param.for` guard.
- Reason: historically observed production SIGFPE in this call path plus no
  regression observed in local and remote replay lanes.

## Numerical consistency note (non-`ffpe-trap` flow)

- The fix is programmatically consistent with legacy non-trap flow for normal
  (non-singular) cases: when `sratio` is well-conditioned, `shrati` is computed
  exactly as before.
- At the singular boundary, legacy non-trap behavior could continue with
  `Inf/NaN` artifacts after divide-by-zero; the fix replaces that undefined path
  with bounded epsilon-guarded values.
- This matches existing defensive style already used for `tcrati` and the
  downstream denominator guards in `param`, improving trap/no-trap alignment in
  control flow while intentionally avoiding IEEE artifact dependence.

## Fixture and regression artifacts

- Fixture root:
  `tests/fixtures/srivas42_claustrophobic_shortcut_p325/`
- Captured failing error log:
  `tests/fixtures/srivas42_claustrophobic_shortcut_p325/logs/p325.err`
- Ablation summary JSON:
  `tests/fixtures/srivas42_claustrophobic_shortcut_p325/logs/ablation_summary_20260418.json`
- Regression test:
  `tests/test_srivas42_claustrophobic_shortcut_p325_sigfpe_fixture.py`

## Residual risks and follow-up

- Flake remains non-reproducible in clean replay, so root-cause certainty is
  bounded by historical evidence and code-path plausibility.
- Continue collecting `*.err` plus observe logs for future `param_` failures to
  confirm or refine guard placement.
