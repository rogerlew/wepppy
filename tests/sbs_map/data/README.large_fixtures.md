# Large SBS Map Fixtures

These fixtures mirror real-world SBS maps to validate the Rust refactor for `sbs_map.py`.
They are intentionally larger than the baseline fixtures and should only be used in
explicit performance/regression runs.

## Files
- `prediction_wgs84_merged.tif`
  - Source: `/wc1/runs/sh/short-order-slickness/disturbed/prediction_wgs84_merged.tif`
  - No color table; 4 classes (0, 1, 2, 255)
- `Rattlesnake.tif`
  - Source: `/wc1/runs/de/decimal-pleasing/disturbed/Rattlesnake.tif`
  - Has SBS color table; 256 classes (0-255)

## Expectations
The baseline summary outputs are stored in:
- `sbs_map_fixtures.json`
- `sbs_map_large_expectations.json` (SoilBurnSeverityMap-derived metadata)

## Running the tests
These fixtures are only exercised when explicitly enabled:

```bash
SBS_MAP_LARGE_FIXTURES=1 wctl run-pytest tests/sbs_map/test_sbs_map_large_fixtures.py -v
```

The test harness will use `wepppyo3.sbs_map.summarize_sbs_raster` when available,
otherwise it falls back to the legacy Python implementation.
