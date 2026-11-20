# IFX vs Linux Parity Report (Subset Lane: `C013`)

Date: 2026-04-20  
Incident package: `docs/ablation/20260419_operational-berry_pw0_sigfpe-locate-frostn/`

## Scope

This report captures a focused parity comparison between:
- Linux build: `/home/workdir/wepp-forest/src/wepp`
- IFX-compiled Windows executable: `/c/src/wepppy-win-bootstrap/bin/wepppy-win-bootstrap.exe` (host `blarhg`)

Data scope:
- staged `operational-berry` repro case `C013`
- entrypoint: `runs/pw0.run`
- subset horizon observed in both runs: simulation years `1..24`

## Execution Summary

Both binaries completed successfully on the staged case:
- Linux: `rc=0`, `WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY`
- IFX: `rc=0`, `WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY`
- No `SIGFPE` observed in either lane.

## Raw Parity Result

Tool: `tools/compare_wepp_raw_outputs.py` (`output` scope; `*.dat,*.txt,*.out`)

Result summary:
- Files: baseline `237`, candidate `237`, common `237`
- Identical: `233`
- Changed: `4`
- Changed files:
  - `chnwb.txt`
  - `ebe_pw0.txt`
  - `loss_pw0.txt`
  - `soil_pw0.txt`

Representative metrics:
- `chnwb.txt`: `max_abs=35003.708`, `max_rel=1.0`, exceeding values `478456`
- `ebe_pw0.txt`: `max_abs=2171.81`, `max_rel=1.0`, exceeding values `1080`
- `loss_pw0.txt`: `max_abs=58.4`, `max_rel=0.0724346`, exceeding values `915`
- `soil_pw0.txt`: `max_abs=31.53`, `max_rel=1.0`, exceeding values `61946`

## Meaningful Parity Result

Tool: `tools/compare_wepp_meaningful_parity.py` (default thresholds)
- water relative tolerance: `1%`
- erosion relative tolerance: `10%`

Result summary:
- Water lane: `FAIL`
  - `chnwb.txt` exceeded tolerance for `39124 / 17742386` numeric values (`0.2205%`)
- Erosion lane: `FAIL`
  - `ebe_pw0.txt` exceeded tolerance for `103 / 96430` numeric values (`0.1068%`)
  - `loss_pw0.txt` was within erosion tolerance (`max_rel=0.0724346`)

Overall meaningful parity result: `FAIL` under current thresholds.

## Interpretation

Observed divergence is sparse and event-localized, not broad run-wide drift:
- aggregate numeric-sum drift is very small:
  - `chnwb.txt`: relative delta `+1.221901e-05`
  - `ebe_pw0.txt`: relative delta `+1.094741e-06`
  - `loss_pw0.txt`: relative delta `+8.649752e-07`
  - `soil_pw0.txt`: relative delta `-1.498171e-06`

Best-fit hypothesis:
- compiler/runtime floating-point behavior differences are shifting some conditional/event transitions (including zero vs non-zero flips), while preserving near-equal long-horizon aggregate behavior.

## Release Readout

For this subset lane (`C013`), current evidence supports:
- operational stability parity (both complete, no SIGFPE), and
- non-exact event-level parity across compilers.

If shipping on this basis, treat the outcome as:
- contract-acceptable divergence for stability-focused release criteria,
- with explicit documentation that event-level output is not bitwise-identical between IFX and Linux.

## Residual Risk

- Isolated event/day values can differ materially in `chnwb`/`ebe` lanes.
- Workflows sensitive to exact event-level values may observe differences across compiler targets.

## Evidence References

Generated during this parity run:
- `docs/ablation/20260419_operational-berry_pw0_sigfpe-locate-frostn/artifacts/env/ifx_linux_parity_raw_c013.txt`
- `docs/ablation/20260419_operational-berry_pw0_sigfpe-locate-frostn/artifacts/env/ifx_linux_parity_raw_c013.json`
- `docs/ablation/20260419_operational-berry_pw0_sigfpe-locate-frostn/artifacts/env/ifx_linux_parity_meaningful_c013.txt`
- `docs/ablation/20260419_operational-berry_pw0_sigfpe-locate-frostn/artifacts/env/ifx_linux_parity_meaningful_c013.json`
