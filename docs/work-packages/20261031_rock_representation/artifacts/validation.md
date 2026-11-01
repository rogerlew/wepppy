# Development validation and reproducibility

## Implemented boundary

Contract ancestor `b2011d9fb` precedes the two dimensional repairs. The [correctness review](correctness-review.md) binds the three production files and three test files. The [scientific review](final-science-review.md) binds the investigation and independently replays quantitative and native interpretation evidence. The [roadmap review](roadmap-science-review.md) covers future acceptance gates separately. Native evidence checkpoint: `c7ec243c5`; no native equations or binaries changed.

## Completed checks

- `wctl run-pytest tests/wepp/soils/test_rock_fragments.py tests/locales/earth/soils/test_isric_rock_basis.py tests/locales/earth/soils/test_isric_crs_workaround.py tests/nodb/mods/test_rusle_c_integration.py tests/nodb/mods/test_rusle_k_integration.py tests/soils/test_ssurgo_fc_wp_sanitization.py -q --maxfail=1`: 102 passed, two dependency deprecation warnings.
- `wctl check-test-stubs`: passed.
- `wctl run-stubtest wepppy.wepp.soils.rock_fragments`: passed.
- Changed-file broad-exception enforcement including the new module: passed, zero additional broad catches.
- Scoped/staged Markdown lint: passed. Code quality observability retained as nonblocking telemetry.
- Real artifact experiment: 239 hashed files, 16 populated RUSLE C cases and seven serialized SoilGrids horizons. Regression tests separately cover zero, nodata, explicit overrides and absent sources.
- Native fixture: complete 16-year execution, 30 initialization layers, seven fresh outputs, 17,532 daily records across three OFEs. Observed CPM agrees with independently reconstructed mass/density arithmetic.
- Independent diagnostic replay: 505 conversions and inverse checks, 36 overlap bounds and 586 initial capacity-ordering checks.
- Prior immutable evidence: 60 rock-audit, 100 capacity-review and 2,223 storage-ownership files match their archived hashes.

## Broad regression disposition

`wctl run-pytest tests --maxfail=1` exited 0: **12,591 passed, 423 skipped, 5,830 warnings in 3,569.86 seconds**. The separately executed focused suite covers all three final regression files, including the conversion tests added after broad-suite collection. No production code changed during the broad run. Warnings and skip details are retained in the complete log.

## Reproduction and retained failures

Use fresh output directories for `investigate_rock.py`, `produce_artifacts.py`, and `read_native_fixture.py`. Their command-line help and retained receipts specify inputs; native execution also requires the pinned private observer/runtime bundle. Public evidence contains no native source. Current source snapshots and logs are under `out/rock-representation-20261031/` with verified archival recorded in `archive-receipt.json`.

The raw packet retains failing-before implementation tests, the first actual-builder fixture failure (missing bounding-box setup), the first overlap diagnostic's floating-point endpoint failure, corrected attempts, and the bounded NRCS query timeout. The endpoint check uses a declared numerical tolerance; it does not alter physical overlap bounds. No missing survey observations were replaced with estimates.

## Limits

This is local generated-artifact and consumer-boundary validation. It establishes neither complete water/particle closure nor field calibration, production deployment, automatic migration, or acceptance of the Roads magnitude gates. Source-specific surface acquisition, SIFT metadata, SSURGO retention reconciliation and new native rock physics remain governed by the [continuation specification](development-roadmap.md).
