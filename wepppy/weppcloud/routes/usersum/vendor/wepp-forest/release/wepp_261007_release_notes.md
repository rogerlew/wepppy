# WEPP Forest release `wepp_261007`

Date: 2026-10-07
Branch: `wepp_260430_negmeltfix_comparator`
Source commit: `669ff4106a4158e49dc79e038026e4d63a489923`
Compiler: `/usr/bin/gfortran`

## Artifacts

| Artifact | SHA256 |
| --- | --- |
| `release/wepp_261007` | `ad5ef3e31be7e6da2517567fb211fe350cb7ff0ea9320282368182cb6157127b` |
| `release/wepp_261007_hill` | `cba2927f489a324774180164f1b8065118fb3a1fa6b64737710b46b0f96036df` |
| `release/wepp_261007.json` | `7596787c0eafd75cec2c1287d3ac1b8c9ae21d3a696ff049947c851078e5a214` |
| `release/wepp_261007_hill.json` | `678242f7ab030f5b08e8be49945235dafbb95c8de8888db654141cbe24d6b60b` |

## Changes

- `src/chrqin.for`: preserves valid partial endpoint support in the rectangular branch and normalizes the pointwise exponential branch over the same first sample it publishes.
- `src/wshchr.for`: represents zero-side-surface local channel surplus in `qlat` instead of dropping it, and adds opt-in `WCHQLV` observer logging.
- `src/irs.for` + `src/surpeak.for`: replace the legacy `surdra`/`durre` transfer-duration peak publication for non-contour surface-return events with a component-ledger peak estimator that preserves rainfall-only peak contribution and adds opt-in `SURPK_VOLUME`/`SURPK_PEAK` observer evidence.
- `src/makefile`: links `surpeak.for` into both watershed and hillslope binaries.
- `tools/smoke_wepp_binary_host.sh`: defaults to committed `tests/fixtures/delicate_game_pw0/runs` case `p1`, derives the expected final year from each `.run` file, and leaves `RUNS_DIR`/`CASES` available for optional private fixture smoke.
- Added focused regression tests for the channel hydrograph repair and smoke-helper default.

## Validation

- `pytest tests/test_channel_hydrograph_repair.py tests/test_smoke_wepp_binary_host.py tests/test_dumbfounded_patentee_p962_instability.py`: `7 passed`.
- `pytest`: `92 passed, 2 warnings`.
- `tools/smoke_wepp_binary_host.sh src/wepp`: passed.
- `tools/smoke_wepp_binary_host.sh src/wepp_hill`: passed.
- `tools/smoke_wepp_binary_host.sh release/wepp_261007`: passed.
- `tools/smoke_wepp_binary_host.sh release/wepp_261007_hill`: passed.
- `python tools/run_hillslope_watchlist.py --binary .../src/wepp_hill`: `12/12` passed.
- `python tools/check_ablation_artifact_policy.py`: passed.
- `python -m json.tool` on both release sidecars: passed.
- Sidecar hash/source checks: both sidecars record source commit `669ff4106a4158e49dc79e038026e4d63a489923`, record validation status (`host_smoke=pass`, `hillslope_watchlist=pass`, `same_build_watershed_replay=retired`), and match binary SHA256 hashes.
- ELF interpreter checks: source and release binaries request `/lib64/ld-linux-x86-64.so.2`.
- Symbol check: source and release watershed/hillslope binaries export `surpeak_`.

## Open Items

- The former manual reconciled-condenser watershed replay is no longer a release/vendoring gate.
- HV-02 remains unresolved: positive volume with zero peak, and volume above peak-duration capacity, require scientific review or an explicit producer correction contract.
- HV-05 remains unresolved: native-flow/storage/ledger authority still requires full generated-output reconciliation.
- These artifacts were recut before production deployment of the earlier channel-only `wepp_261007`; WEPPpy vendoring should use this combined cut.
