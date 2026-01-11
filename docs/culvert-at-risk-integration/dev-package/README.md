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
| Culvert_web_app Output | Payload Path | Notes |
|------------------------|--------------|-------|
| `WS_deln/breached_filled_DEM_UTM.tif` | `topo/hydro-enforced-dem.tif` | Hydro-conditioned DEM |
| `hydrogeo_vuln/main_stream_raster_UTM.tif` | `topo/streams.tif` | Binary stream raster |
| `WS_deln/all_ws_polygon_UTM.shp` | `culverts/watersheds.geojson` | Nested watershed polygons |
| `WS_deln/pour_points_snapped_to_RSCS_UTM.shp` | `culverts/culvert_points.geojson` | Pour points snapped to road-stream crossings |

**Note:** We use RSCS-snapped pour points (snapped to Road-Stream Crossing Sites) rather than
the original `Pour_Point_UTM.shp`. This ensures culvert points are on the stream network,
improving outlet detection fidelity in wepp.cloud.

## Culvert point validation

wepp.cloud validates that each culvert's pour point is inside its associated watershed polygon
(with a 30m buffer to account for simplification and snapping tolerances). Culverts failing
this check are skipped—this is a quality filter to ensure the modeled watershed matches the
intended catchment area.

If a culvert point is far outside its watershed, wepp.cloud's outlet detection could snap to
a different stream location and delineate an entirely different watershed than what
Culvert_web_app computed.

## Contract notes
- CRS must match across rasters and GeoJSON; record `crs.proj4` in `metadata.json`.
- `Point_ID` is required in both GeoJSON files.
- `watersheds.geojson` polygons are simplified (1.0m tolerance) unless you modify the source.
- Streams are pre-computed; no `mcl`/`csa` parameters in `model-parameters.json`.
- `flow_accum_threshold` is extracted from `user_ws_deln_responses.txt` and included in `model-parameters.json` for traceability (not used by wepp.cloud since streams are pre-computed).
- Payload hash/size are computed by wepp.cloud at upload time (optional request params).
- `source.project_id` uses a sanitized project name (non-alphanumeric -> underscore, trimmed).

### Baseline fixture
Use the `Santee_10m_no_hydroenforcement` project as the canonical dev payload:
`/wc1/culvert_app_instance_dir/user_data/1_outputs/Santee_10m_no_hydroenforcement`.

### Pre-built test payloads
Ready-to-use payloads are available in the test fixtures:
```
tests/culverts/test_payloads/santee_mini_4culverts/payload.zip  (~1.3 MB, 4 culverts, 9.33m)
tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip  (~1.5 MB, 63 culverts, 9.33m)
tests/culverts/test_payloads/Tallulah_River/payload.zip  (~595 MB, 49 culverts, 0.82m)
```

Use for quick testing without rebuilding:
```bash
# Minimal payload (4 culverts, fastest for dev iteration)
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/santee_mini_4culverts/payload.zip

# Small payload (63 culverts, 9.33m resolution)
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip

# Large payload (49 culverts, 0.82m high-res LiDAR)
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/Tallulah_River_Demo/payload.zip
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
