# Frozen public soil inputs

This panel contains the spatial MUKEY subset and public component and
horizon records for the three genuine 10 m terrain site grids. It contains no
live project database, credentials, WEPP profiles, or publisher PDF.

## Sources and units

- USDA NRCS installed 2025 gNATSGO MUKEY mosaic, nearest-neighbor sampled onto
  each archived terrain grid. This is nominal 30 m source mapping on a 10 m
  project grid, not newly resolved 10 m soil knowledge. `*_lineage.json`
  resolves every key to a Non-MLRA Soil Survey Area. Spatial labels are original,
  not WEPP buildable-profile substitutions. SDA revisions differ from the
  mosaic date; historical snapshot parity is not claimed.
- NRCS SDA `component`/`chorizon` subsets use depths in cm, percentages in
  percent, and stable public IDs. `queries.json` records the exact bounded
  queries, retrieval times, endpoint and returned row counts.
- USGS original STATSGO THICK COG, 2025 reformat of Schwarz and Alexander 1995,
  in inches. `*_statsgo_native.tif` preserves native EPSG:5069 windows and
  sentinels. `statsgo_metadata.json` identifies the publication and asset.
- `manifest.json` supplies file sizes, SHA-256 hashes, source identity and
  attribution. These small GeoTIFF subsets use ordinary Git fixture storage;
  no whole continental raster is redistributed.

The user label `az_ponderosa` is retained; survey areas NM656/NM678 establish
New Mexico provenance, not Arizona. Run IDs remain in the package inventory.
All three live projects lacked soil directories during this study; these are
study-acquired fixtures and do not imply completed project Soils builds.

## Reproduction

From the repository root, explicitly acquire into a **new** directory:

```bash
.venv/bin/python docs/work-packages/20260908_staley_m3_soils/artifacts/acquire_sources.py \
  --terrain /workdir/weppcloud-wbt/test_fixtures/staley_m3_resolution \
  --spatial-source /wc1/geodata/ssurgo/gNATSGSO/2025/.vrt \
  --output /tmp/staley-m3-soils-new-snapshot
```

Acquisition is separate from evaluation. A later SDA response may legitimately
change; never overwrite this panel merely to obtain passing expectations.
The same-session reproduction returned byte-identical six CSV tables and six
raster subsets. Metadata/request timestamps can differ.

`artifacts/run_study.py::database` reconstructs a disposable SQLite database:
CSV column names become TEXT columns, empty cells become SQL NULL, and every
row is inserted unchanged into `component` or `chorizon`. The reader validates
canonical core fields; `compkind` is retained in the fixture but not required
of historical project caches. No live database is opened for writing.

[Canonical interval and support contract](../../../../../wepppy/nodb/mods/postfire_debris_flow/docs/m3_soil_thickness.md)
defines the offline estimates. [Study protocol](../../../../../docs/work-packages/20260908_staley_m3_soils/artifacts/study_protocol.md)
defines source comparison and diagnostic rainfall scenarios. See the package's
validation artifact for final execution commands and generated-output evidence.
