# Read-only project watershed artifact audit

Audited 2026-09-09 UTC at WEPPpy revision
`db03285e986c7d42afb65434429e02eff66a2b48`. The frozen Topanga 10 m fixture
was located through the closed terrain package's `artifacts/inventory.py`.
Source files and closed packages were not modified. This fixture establishes
artifact reuse, not a live postfire assessment or predictor validation.

## Authority trace

`Watershed.bound` in `wepppy/nodb/core/watershed.py` resolves to
`dem/wbt/bound.tif`. `WhiteBoxToolsTopazEmulator._create_bound` in
`wepppy/topo/wbt/wbt_topaz_emulator.py` calls the owned WBT watershed tool with
the existing `flovec` D8 pointer and `outlet.geojson`. Its subsequent
`gdal_contour -p -fl 1` creates `bound.geojson`, followed by the WGS84 view.
These are derived display polygons, distinct from a user-drawn selection
polygon or `target_watershed.tif` used to guide outlet selection.

`WatershedOperationsMixin.set_outlet` adopts WBT's resolved Outlet;
`Watershed.find_outlet` likewise uses `set_outlet_from_geojson`. Preserve actual
row/column and projected cell-center coordinates, not requested coordinates.
The emulator's routing property selects `flovec.tif` or `flovec.vrt` according
to existing configuration. The raw DEM is `Watershed.dem_fn`; WBT `relief`
is conditioned terrain and must not replace raw elevations for M3 H.

## Measured evidence

[Machine-readable evidence](watershed_artifact_audit.json) records complete
grid identity and SHA-256 hashes for seven source files. The audit script checks
the hashes again after inspection. NumPy performs support comparisons and
compiled GDAL rasterizes the existing polygon; no D8 traversal or new
delineation is implemented.

- EPSG:32611, 391 rows × 380 columns, identical affine transforms for raw DEM,
  D8 pointer, watershed mask and subcatchments.
- `bound.tif`: label 1 within the watershed, NoData -32768 outside; 49,917 cells.
  Each cell is 100 m²; full watershed area is 4,991,700 m².
- Resolved outlet: row 201, column 36, center
  (353931.5645379969, 3776366.5143099623), inside the routed mask. Requested
  row 203, column 37 is different; the audit does not re-snap it.
- Positive valid `subwta.tif` support differs by zero cells. This includes
  channel cells; outlet subcatchment label is 24.
- Center-cell rasterization of the derived projected boundary differs by zero
  cells. Polygon geometry is not substituted for routing authority.
- Zero watershed cells touch the raster's outer edge. This is a limited
  boundary diagnostic, not proof of complete or hydrologically correct routing.

The outlet JSON contains `outlet_in_mask=false` and `watershed_cell_count=0`.
Owned WBT `find_outlet.rs` initializes these values when its optional selection
mask is absent; those fields describe selection-mask diagnostics. They do not
describe the subsequently delineated `bound.tif`. The measured routed mask
includes the outlet; no source repair is appropriate.

## Reproduction and limits

From the WEPPpy repository root:

```bash
wctl run-python docs/work-packages/20260908_staley_watershed_engine/artifacts/audit_watershed.py > /tmp/staley_watershed_audit.json
diff -u docs/work-packages/20260908_staley_watershed_engine/artifacts/watershed_artifact_audit.json /tmp/staley_watershed_audit.json
```

The container rerun used rasterio 1.3.10 and NumPy 1.26.0 and reproduced
the recorded JSON exactly. The script requires the existing
sibling WBT fixture; it fails explicitly if missing. It has no production role.
Slope/SBS interpretation, missing data, K units and readiness, M3 production
terrain fidelity, and predictor support policies remain successor decisions.
