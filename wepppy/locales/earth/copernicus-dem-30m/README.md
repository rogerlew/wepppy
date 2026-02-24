# Copernicus DEM 30m VRT Builder

> Build a GDAL VRT that points to public Copernicus DEM GLO-30 COG tiles over `/vsicurl/`, using the public STAC bucket as the source index.

> **See also:** [AGENTS.md](../../../../AGENTS.md) for repository-wide agent and validation guidance.

## Overview

This module provides a lightweight, reproducible way to create a local `.vrt` file that references Copernicus DEM 30m tiles directly from AWS Open Data without downloading full rasters.

The builder script:
- Enumerates public STAC item records from `https://copernicus-dem-30m-stac.s3.amazonaws.com`.
- Converts item IDs into DEM COG URLs in `https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com`.
- Writes a source list of `/vsicurl/https://...tif` paths.
- Runs `gdalbuildvrt` to assemble a VRT.

This is useful for Earth-scale DEM workflows that need GDAL-compatible remote access while keeping local storage small.

## Workflow

1. Discover STAC item JSON keys from the `items/` prefix.
2. Optionally filter by a WGS84 bounding box.
3. Generate a source list file (`*.sources.txt`).
4. Build the VRT with `gdalbuildvrt`.
5. Optionally verify with `gdalinfo`.

## Requirements

- `python3`
- `gdalbuildvrt` and `gdalinfo` on `PATH`
- Network access to:
  - `https://copernicus-dem-30m-stac.s3.amazonaws.com`
  - `https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com`

## Quick Start

Build a small AOI VRT (faster smoke test):

```bash
python wepppy/locales/earth/copernicus-dem-30m/scripts/build_vrt_from_stac.py \
  --bbox -117.1 43.9 -115.9 45.1 \
  --output-vrt wepppy/locales/earth/copernicus-dem-30m/data/idaho-smoke.vrt \
  --verify-gdalinfo
```

Build a larger/global VRT:

```bash
python wepppy/locales/earth/copernicus-dem-30m/scripts/build_vrt_from_stac.py \
  --output-vrt wepppy/locales/earth/copernicus-dem-30m/data/copernicus-dem-30m.vrt
```

## Script Reference

`scripts/build_vrt_from_stac.py`

| Argument | Default | Description |
|---|---|---|
| `--output-vrt` | `data/copernicus-dem-30m.vrt` | Output VRT path. |
| `--source-list` | `<output-vrt>.sources.txt` | Optional source list path. |
| `--bbox WEST SOUTH EAST NORTH` | unset | Optional WGS84 filter. |
| `--limit` | unset | Optional cap on number of tiles. |
| `--stac-base-url` | public STAC bucket | STAC listing source. |
| `--data-base-url` | public COG bucket | DEM COG base URL. |
| `--dry-run` | `false` | Write source list only. |
| `--verify-gdalinfo` | `false` | Run `gdalinfo` on output VRT. |

## Developer Notes

- The STAC root object is `dem_cop_30.json` in this dataset; item discovery is done via S3 `list-type=2` pagination for robustness.
- Source paths are emitted as `/vsicurl/https://...` so GDAL reads COGs remotely without local tile staging.
- Tile filtering uses tile ID naming (`Copernicus_DSM_COG_10_<lat>_<lon>`) and 1x1 degree extents.
