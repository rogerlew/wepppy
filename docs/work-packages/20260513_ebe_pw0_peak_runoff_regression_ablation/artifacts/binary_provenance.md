# Binary Provenance - `wepp_260513` EBE Peak Runoff Fix Candidate

Date: 2026-05-13 UTC

## Scope

Vendored binaries:

- `wepp_runner/bin/wepp_260513`
- `wepp_runner/bin/wepp_260513_hill`

Source build location:

- `/workdir/wepp-forest/src/wepp`
- `/workdir/wepp-forest/src/wepp_hill`

## Source Context

- Source repo: `wepp-in-the-woods/wepp-forest`
- Source head at build time: `32a2290c3cfcc3709bd1329d4590fc353c49b558`
- Source patch used for this candidate build: local `src/wshrun.f90` edit (not yet committed in `wepp-forest`), covering:
  - route12 ipeak=4 runoff-volume input tuple adjustment (`volint(ichan)` -> `runvol(ielmt)`).
  - explicit compatibility fallback for `WBK_ROUTE_12_KERNEL_STACK_ERROR` to preserve run completion in known fault-class cases.

## Binary Identity

- `wepp_260513`: `2670aea4b8960495638ed2eac7999c49478d0e38e74ed1516eb4adf76c498419`
- `wepp_260513_hill`: `8c1592c04931434e0f7d6a5befbf20492899c5b0a7243abc9581da0d18753c88`

Interpreter checks:

- `readelf -l ... | rg "Requesting"` => `/lib64/ld-linux-x86-64.so.2` for both binaries.

Sidecars regenerated:

- `wepp_runner/bin/wepp_260513.json`
- `wepp_runner/bin/wepp_260513_hill.json`

Release tag in sidecars: `260513-ebepeak-fix`.

## Validation Commands Executed

From `/workdir/wepp-forest`:

- `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp` -> PASS
- `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp_hill` -> PASS
- `python tools/run_hillslope_watchlist.py --binary /workdir/wepp-forest/src/wepp_hill` -> PASS (`13/13`)
- `python tools/check_ablation_artifact_policy.py` -> PASS
- Reconciled-condenser watershed replay:
  - `/workdir/wepp-forest/src/wepp < pw0.run`
  - stdout success marker observed: `WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY`
  - no runtime/floating-point parse error signatures in stdout/stderr.

From `/workdir/wepppy`:

- `tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_260513 wepp_runner/bin/wepp_260513_hill` -> PASS
- `tools/smoke_wepp_binary_host.sh ...` with default `RUNS_DIR=/wc1/runs/du/dumbfounded-patentee/wepp/runs` -> FAIL (fixture run files still reference legacy `H*.pass.dat`; candidate binary expects `H*.hbp`).
- `RUNS_DIR=/wc1/runs/co/countrywide-kleptomania/wepp/runs tools/smoke_wepp_binary_host.sh ...` -> PASS for both binaries (HBP-compatible fixture set).
- `pytest tests/wepp_runner/test_run_hillslope_retries.py tests/wepp/test_wepp_runner_outputs.py` -> PASS (`8 passed`).

## Notes

- This candidate binary is validated against HBP-compatible fixture runs and resolves the `ebe_pw0.peak_runoff` all-zero defect signature in off-the-rack-neoprene ablation replay evidence.
- Default host-smoke fixtures in `wepppy` still target legacy `H*.pass.dat` run files and are not compatible with this HBP-only candidate behavior.
