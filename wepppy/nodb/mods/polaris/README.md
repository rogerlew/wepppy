# POLARIS NoDb Mod

`wepppy.nodb.mods.polaris` provides run-scoped retrieval and alignment of POLARIS
soil-property rasters.

## Behavior

- Select POLARIS layers via config and/or request payload.
- Fetch source VRTs from `http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/`.
- Align each selected layer to the run DEM grid and persist as GeoTIFF under
  `<wd>/polaris/<layer_id>.tif`.
- Generate:
  - `<wd>/polaris/manifest.json`
  - `<wd>/polaris/README.md`

## Config (`[polaris]`)

- `base_url` (default: POLARIS v1.0 endpoint)
- `properties` (list or `["all"]`)
- `statistics` (list or `["all"]`)
- `depths` (list or `["all"]`)
- `layers` (explicit layer ids or `["all"]`)
- `resample` (`near`, `bilinear`, `cubic`, `cubic_spline`, `lanczos`, `average`, `mode`)
- `keep_source_intermediates` (`true`/`false`)
- `request_timeout_seconds` (int)

Default request (when omitted) targets top-horizon means for:
`sand`, `clay`, `bd`, `om`.
