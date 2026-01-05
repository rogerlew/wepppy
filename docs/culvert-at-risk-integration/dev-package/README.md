# Culvert_web_app dev package
> Handoff docs and scripts for building `payload.zip` files for wepp.cloud.

## Purpose
- Provide a readable, minimal payload builder for Culvert_web_app developers.
- Keep the payload contract aligned with `weppcloud-integration.spec.md`.

## Layout
- `README.md` (this file)
- `scripts/` (payload builder entrypoints and helpers)

## Payload preparation for wepp.cloud

### Required layout
```
payload.zip
  topo/hydro-enforced-dem.tif
  topo/streams.tif
  culverts/culvert_points.geojson
  culverts/watersheds.geojson
  metadata.json
  model-parameters.json
```

### Source mapping (Culvert_web_app outputs)
- DEM: `WS_deln/breached_filled_DEM_UTM.tif` -> `topo/hydro-enforced-dem.tif`
- Streams raster: `hydrogeo_vuln/main_stream_raster_UTM.tif` -> `topo/streams.tif`
- Watersheds polygons: `WS_deln/all_ws_polygon_UTM.shp` -> `culverts/watersheds.geojson`
- Culvert points: `WS_deln/Pour_Point_UTM.shp` -> `culverts/culvert_points.geojson`

### GeoJSON conversion
```
ogr2ogr -f GeoJSON culverts/watersheds.geojson WS_deln/all_ws_polygon_UTM.shp
ogr2ogr -f GeoJSON culverts/culvert_points.geojson WS_deln/Pour_Point_UTM.shp
```

### Contract notes
- CRS must match across rasters and GeoJSON; record `crs.proj4` in `metadata.json`.
- `Point_ID` is required in both GeoJSON files.
- Streams are pre-computed; no `mcl`/`csa` parameters in `model-parameters.json`.
- Payload hash/size are computed by wepp.cloud at upload time (optional request params).
- `source.project_id` uses a sanitized project name (non-alphanumeric -> underscore, trimmed).

### Baseline fixture
Use the `Santee_10m_no_hydroenforcement` project as the canonical dev payload:
`/wc1/culvert_app_instance_dir/user_data/1_outputs/Santee_10m_no_hydroenforcement`.

## References
- `docs/culvert-at-risk-integration/weppcloud-integration.spec.md`
- `docs/culvert-at-risk-integration/weppcloud-integration.plan.md`
