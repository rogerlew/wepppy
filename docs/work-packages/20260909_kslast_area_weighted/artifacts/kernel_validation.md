# Kernel and preparation validation

Confirmed on 2026-09-09 UTC:

- Rust formatting and cargo check pass for raster_characteristics_rust.
- `RUSTFLAGS='-C link-arg=-lpython3.12' PYO3_PYTHON=/usr/bin/python3.12 cargo test -p raster_characteristics_rust --lib`: 8 passed.
- Canonical release Python suite through the WEPPcloud Python 3.12 runtime:
  `wctl docker compose exec -T weppcloud /opt/venv/bin/python -m pytest /workdir/wepppyo3/tests/raster_characteristics -q -o cache_dir=/tmp/kslast-native-pytest`: 43 passed.
- `wctl run-pytest tests/nodb/test_kslast_map.py --maxfail=1 -q`: 28 passed.
- Earlier combined project-grid and soil-util suite: 80 passed; final four actual
  worker propagation cases pass after correcting fixture ntemp to two OFEs.

Fixtures exercise masks, finite/NaN nodata, zero/negative generic values/defaults,
partial/all missing coverage, excluded/channel/empty keys, grid/CRS/band errors,
large finite values and signed cancellation. Stacker fixtures validate uncovered
area with/without source nodata, valid zeros, dtype narrowing and sentinel values
created by GDAL rounding or average resampling. Mapped ordinary/MOFE tests verify
submission values, no-default failure before workers, actual two-OFE soil output,
developed exemptions, source/grid/default changes and directory boundaries.

Review found and closed three correctness issues: signed cancellation required
scaled Neumaier accumulation; nodata validation needed actual GDAL conversion and
post-resampling checks; ordinary-mode real worker propagation needed direct tests.
Security review independently exercised escaping and valid in-run soils aliases
and real Redis maintenance-lock contention. See the dated review artifacts.

Representative three native scans on the actual 1984 x 2044 project grid took
0.6201, 0.6398 and 0.5312 seconds, producing 505 hillslope records. Process peak
RSS was 542856 KiB including WEPPpy imports. This is an observed workload result,
not a comparative benchmark or a claim about arbitrary raster sizes.

Initial plain stubtest was blocked by missing third-party osgeo typing metadata.
The repository-configured invocation passed:
`wctl run-stubtest wepppy.all_your_base.geo.geo --ignore-missing-stub --mypy-config-file /workdir/wepppy/mypy.ini`.
`wctl check-test-stubs` passed. Changed broad-exception enforcement passed with
zero net new handlers. Code-quality observability completed in observe-only mode
using external --json-out/--md-out paths to preserve unrelated dirty reports.
