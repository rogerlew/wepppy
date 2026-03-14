# POLARIS Source Inventory (Discovery Baseline)

## Source

- Base index: `http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/`
- Readme: `http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/Readme`
- VRT catalog: `http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/vrt/`

## Published Variables (13)

- `alpha`
- `bd`
- `clay`
- `hb`
- `ksat`
- `lambda`
- `n`
- `om`
- `ph`
- `sand`
- `silt`
- `theta_r`
- `theta_s`

## Published Statistics (5)

- `mean`
- `mode`
- `p5`
- `p50`
- `p95`

## Published Depth Intervals (6)

- `0_5`
- `5_15`
- `15_30`
- `30_60`
- `60_100`
- `100_200`

## Layer Count

- Reported VRT files under `/vrt/`: `390`
- Combinatorics check: `13 properties x 5 statistics x 6 depths = 390`

## Raster Metadata Snapshot

From `clay_mean_0_5.vrt`:

- CRS: `EPSG:4326` (WGS84 geographic)
- Pixel size: `0.00027777777777570245` degrees (~1 arcsec)
- NoData: `-9999`
- Backing files: many 1x1 degree tiles referenced as relative `../<property>/<stat>/<depth>/lat..._lon....tif`

Implication: run outputs must be explicitly aligned to project raster grid contracts (projection + transform + shape), not consumed directly as native EPSG:4326 layers.

## POLARIS Units/Notes (from source Readme)

- `hb`, `alpha`, `ksat`, `om` are reported in log10 space.
- Resolution is listed as 1 arcsec (~30 m).
- Data published as tiled GeoTIFFs with VRT glue layers.

## Relevant Repository Integration Points

- Run map/grid: `wepppy/nodb/core/ron.py`
- Alignment utility: `wepppy/all_your_base/geo/geo.py::raster_stacker`
- Reference mod patterns:
  - `wepppy/nodb/mods/openet/openet_ts.py`
  - `wepppy/nodb/mods/shrubland/shrubland.py`

## Commands Used During Discovery

```bash
curl -sS 'http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/Readme'
curl -sS 'http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/vrt/' | rg -o 'href="[^"]+\.vrt"' | wc -l
curl -sS 'http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/vrt/clay_mean_0_5.vrt' | sed -n '1,80p'
```
