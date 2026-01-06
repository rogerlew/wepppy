# Culvert_web_app dev package
> Handoff docs and scripts for building `payload.zip` files for wepp.cloud.

## Purpose
- Provide a readable, minimal payload builder for Culvert_web_app developers.
- Keep the payload contract aligned with `weppcloud-integration.spec.md`.
- Submit payloads over SSL and poll until completion.

## Layout
- `README.md` (this file)
- `scripts/` (payload builder and submission tools)
  - `build_payload.py` - Build payload.zip from Culvert_web_app outputs
  - `submit_payload.py` - Submit payload.zip to wepp.cloud over SSL

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

### Pre-built test payload
A ready-to-use payload is available in the test fixtures:
```
tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip  (~1.5 MB)
```

Use this for quick testing without rebuilding:
```bash
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip
```

## SSL Payload Submission

After building a payload, submit it over HTTPS:

```bash
# Submit to production (wepp.cloud)
python scripts/submit_payload.py --payload payload.zip

# Submit to test server (development)
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py --payload payload.zip
```

The `WEPPCLOUD_HOST` environment variable controls the target host:
- Default: `wepp.cloud` (production)
- Testing: `wc.bearhive.duckdns.org`

All connections use HTTPS (no HTTP fallback).

See `scripts/README.md` for full CLI options and observability output.

## References
- `docs/culvert-at-risk-integration/weppcloud-integration.spec.md`
- `docs/culvert-at-risk-integration/weppcloud-integration.plan.md`
