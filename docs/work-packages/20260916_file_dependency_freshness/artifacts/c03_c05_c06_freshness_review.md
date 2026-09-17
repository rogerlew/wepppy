# C03, C05, C06 native-consumer baseline review

Date: 2026-09-16. Reviewer: independent QA agent. Disposition: all three
freshness defects reproduced in actual consumer outputs; implementation,
representative performance, and full runtime acceptance remain open.

## Retained evidence and scope

- [Native probe](c03_c05_c06_native_probe.py),
  [results](c03_c05_c06_native_probe.json),
  [execution log](c03_c05_c06_native_probe.log), and
  [disposable inputs](c03_c05_c06_inputs/89e755f77940/).
- Command: `wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/c03_c05_c06_native_probe.py`.
- Actual development service image, UID 1000/GID 993, installed rasterio/GDAL
  and `wepppyo3`; real 2-by-2 GeoTIFF files, EPSG:32611, 30-meter cells.
  No named project files, production code, or tests changed.
- C03 executes actual `Landuse.build_managements`, management-map loading,
  native pair counting, cache admission, and area calculation. Lightweight
  owner bindings replace NoDb lookup; locking, persistence, and notifications
  are isolated. This proves management-summary staleness, not propagation to
  `landuse.nodb`, Parquet, or final WEPP management files.
- C05 executes the actual geometry query, rasterio vectorization/reprojection,
  legend join, and artifact IO. C06 executes the actual auto-burn materializer
  and `raster_stacker`. Neither runs HTTP/RQ orchestration or the Geneva kernel.
  These are native-output proofs, beyond predicate-only collision evidence.

## Confirmed findings

| Consumer | Trigger | Stale output | Control using current inputs |
| --- | --- | --- | --- |
| C03 MOFE counts | Rewrite MOFE pixels from 3:1 to 1:3 cells while preserving size and nanosecond mtime | `build_managements` reuses counts 3:1; areas 0.27/0.09 ha and coverage 75/25% | Native direct count and actual cache invalidation produce 1:3, 0.09/0.27 ha, 25/75% |
| C05 HRU geometry | Rewrite raster class 1 to 2, preserving size/mtime | Actual query retains `hru_value=1`, `hru_id=hru1` | Actual rematerialization returns class 2 / `hru2` |
| C05 legend join | Equal-size legend edit `hru2` to `alt2`, preserving mtime | Query retains `hru2` | Rematerialization returns `alt2` |
| C05 dependency closure | Change external `.msk` from all valid to one valid column; main TIFF SHA remains unchanged | Geometry retains full-width bounds | Rematerialization halves longitude width: maximum longitude changes from -116.999237 to -116.999618 |
| C06 aligned burn | Rewrite source class 1 to 2, preserving size/mtime | Actual aligned raster retains class 1 | Expiring only the disposable target mtime rebuilds class 2 |
| C06 selected source | Select a different, older source containing class 3 | Existing aligned raster retains class 2 | Expiring target rebuilds class 3 |
| C06 canonical grid | Shift bound transform 30 meters east, preserving bound size/mtime | Output retains old transform and full valid extent | Rebuild has new transform and expected nodata edge |

## Consumer and writer trace

**C03:** `wepppy/nodb/core/landuse.py:1962` records path/existence/size/mtime;
`:1988` combines both raster signatures with the MOFE key structure. At
`:2086`, `build_managements` reuses cached pairs and derives management areas
from those counts and `Ron.cellsize`. Mapping values are applied after counting;
they should not force redundant native counting when only labels change.
`watershed.py:854` selects TOPAZ `SUBWTA.ARC`, WBT `subwta.tif`, or TauDEM
`subwta.tif`; `watershed_mixins.py:905` writes `watershed/mofe.tif` using native
assignment followed by GDAL. The cached fields survive NoDb hydration.

The owned native implementation is
`/home/workdir/wepppyo3/raster_characteristics/src/lib.rs:80`, using
`Raster::read` at `/home/workdir/wepppyo3/raster/src/raster.rs:291`: GDAL band
data, dimensions, and nodata affect counts. It opens GDAL datasets rather than
parsing TIFF alone. External validity masks are not read explicitly by this
counting implementation; the C05 mask result must not be generalized to C03.

**C05:** `hru_preparation_service.py:84` asks the owned Geneva kernel to write
`hru_map.tif` and `hru_map_legend.json`. In the same collaborators directory,
`hru_map_geometry_service.py:108` admits the cached GeoJSON by two mtimes;
`:127` actually reads masked raster pixels, transform and CRS, then joins legend
rows. Source bytes, effective mask, georeferencing, and legend metadata all
belong to this consumer's dependency set. The external-mask proof establishes
that a main-file digest alone cannot close C05.

**C06:** `hsg_assignment_service.py:53` resolves required owner paths, then
discovers `Disturbed.sbs_4class_path` before `disturbed_cropped`; explicit burn
overrides pass through unchanged. At `:134`, a fixed output path is admitted
solely by source/bound mtimes (`:204`), losing the selected source identity.
`wepppy/all_your_base/geo/geo.py:203` performs nearest-neighbor reprojection.
It uses the bound profile/grid, source data/nodata/georeferencing, and source
color table. It does not read bound pixels as a clipping mask: a bound-mask edit
alone is not established as an aligned-burn output dependency by this review.

## Smallest compatible correction and acceptance gaps

1. Ratify each consumer's dependency identity before implementation. Preserve
   native GDAL readers and their supported inputs. Do not replace raster work
   with Python pixel processing or assume every consumer uses identical
   sidecars. Recursive referenced datasets, auxiliary metadata and directory
   datasets remain part of the shared closure investigation; they were not
   proven individually for these consumers here.
2. C03 can retain its bounded pair-count cache with verified input identities.
   Existing private persisted signatures should conservatively miss and
   regenerate; do not manufacture a historical content identity. Preserve MOFE
   structure behavior, ordinary non-MOFE runs, TOPAZ ASCII inputs, native nodata
   handling, generated management keys, and current area formulas.
3. C05/C06 need evidence tying the existing output to the source dependencies
   actually consumed. Retaining caching with a versioned dependency record is
   a bounded option; legacy outputs lacking evidence require regeneration.
   Include C06 selected-source identity and canonical grid. Publication must
   keep output and its accepted evidence coherent if inputs change during
   generation. Preserve prior accepted artifacts when generation fails.
4. Preserve Geneva specification §8.1 source selection/explicit-override rules
   and §12.4.6 geometry envelope, WGS84 bounds, join keys, and unavailable states.
   Preserve NoDb locking/persistence contracts. Any new persisted record requires
   the contract checkpoint and compatibility note before implementation.
5. Current C03 tests replace the native counter and simulate signature changes
   (`tests/nodb/test_landuse_coverage_area_source.py:448`). C05 tests use
   placeholder rasters and a fake materializer
   (`tests/nodb/mods/geneva/test_geneva_hru_map_geometry_service.py:59`). C06's
   alignment test replaces `raster_stacker`
   (`tests/nodb/mods/geneva/test_geneva_collaborators.py:833`). Add actual-output
   regressions for the proven triggers, unchanged warm reuse, missing/changed
   dependencies, and accepted-output preservation. Keep orchestration tests;
   mock-only assertions do not establish native freshness.
6. Tiny native fixtures establish correctness failures, not performance
   acceptance. Measure cold identity discovery, warm admission, regeneration,
   and repeated requests on representative large rasters. Keep hashing and
   dependency scans bounded, avoid full raster decoding on each warm call,
   and compare against current native counting/vectorization/reprojection.

Full NoDb persistence, downstream generated management files, live Geneva
query/RQ behavior, and representative unchanged-path latency remain pending.
This review does not close those acceptance gates or the overall work package.
