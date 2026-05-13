# Validation Summary

Evidence class: `Ran`

## wepppyo3

1. `cargo test -p raster_characteristics_rust`
- Result: `PASS`
- Test summary: `2 passed; 0 failed`

2. `cargo build -p raster_characteristics_rust --release`
- Result: `PASS`

3. `pytest tests/raster_characteristics -q`
- Result: `PASS`
- Test summary: `18 passed`

4. `PYTHONPATH=/home/workdir/wepppyo3/release/linux/py312 python3.12 -c "from wepppyo3.raster_characteristics import raster_characteristics_rust as rc; print(rc.__file__)"`
- Result: `PASS`
- Output path confirms release-tree import target.

5. `sha256sum release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so`
- Result: `PASS`
- SHA256: `a2dddb70c3c9670bad8c4103b64d455539896d5ea1be17a99d9c5adc88dccda6`

## WEPPpy targeted consumer checks

1. `wctl run-pytest tests/nodb/test_landuse_coverage_area_source.py tests/soils/test_wepppyo3_nodata_guard.py --maxfail=1`
- Result: `PASS`
- Test summary: `9 passed; 0 failed`

2. Optional expanded check:
   `wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py --maxfail=1`
- Result: `PASS`
- Test summary: `85 passed; 0 failed`

## Docs and diff hygiene

1. `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order`
- Result: `PASS`
- Summary: `9 files validated, 0 errors, 0 warnings`

2. `git diff --check` in `/home/workdir/wepppyo3`
- Result: `PASS`

3. `git diff --check` in `/workdir/wepppy`
- Result: `PASS`

## Pending checklist items

- None.

## Independent review gate

- Artifact: `artifacts/20260513_code_review.md`
- Result: `PASS`
- Summary: `0 high`, `0 medium`, `3 low` (all fixed)
