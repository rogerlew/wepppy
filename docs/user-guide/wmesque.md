# Download raster data with WMesque

WMesque lets you download a rectangular area from an available raster dataset,
such as an elevation model, at a chosen cell size. You can open the result in
GIS software or use it in your own analysis. This guide covers the WMesque v2
service at `https://wepp.cloud/webservices/wmesque2`.

You can download through a browser without installing WEPPpy. The command-line
examples use `curl`; the metadata example also uses Python 3. If your organization
provides another WMesque server, replace the base URL throughout this guide.
Dataset availability depends on the server.

## Find a dataset

Open the [dataset catalog](https://wepp.cloud/webservices/wmesque2/catalog).
It returns a JSON list of dataset paths. For example:

```json
["/geodata/tenerife/136_MDT25_TF/.vrt"]
```

Remove the `/geodata/` prefix and `/.vrt` suffix to get the dataset ID:
`tenerife/136_MDT25_TF`. Use that ID after `/retrieve/` in a
download URL. The `.vrt` entry describes the source raster; you do not need to
download it.

The catalog combines a maintained legacy inventory with managed datasets. It is
not a live filesystem scan, so a newly installed dataset may be retrievable
before it is listed. If an expected dataset is missing, ask the service operator
to refresh the inventory. The catalog lists identifiers, not a coverage map. Check the source dataset's
coverage, date, units, and usage terms before using it. A listed dataset does not
guarantee that your chosen area contains data. The repository's
[dataset inventory](../infrastructure/wmesque-dataset-sync-manifest.md) provides
additional context, but is not a live availability list.

## Download a small elevation raster

This example requests an area on Tenerife at 25-meter cell size. Open this
[example GeoTIFF download](https://wepp.cloud/webservices/wmesque2/retrieve/tenerife/136_MDT25_TF?bbox=-16.543,28.2907,-16.523,28.3107&cellsize=25&format=GTiff)
in a browser and save the file. Or run:

```bash
curl --fail --show-error --get \
  'https://wepp.cloud/webservices/wmesque2/retrieve/tenerife/136_MDT25_TF' \
  --data-urlencode 'bbox=-16.543,28.2907,-16.523,28.3107' \
  --data-urlencode 'cellsize=25' \
  --data-urlencode 'format=GTiff' \
  --dump-header tenerife-headers.txt \
  --output tenerife-dem.tif
```

The output filename is your choice. Use a new filename to avoid overwriting an
existing download. `--fail` makes HTTP errors fail the command; only use the
output after the command succeeds. The header file retains processing metadata.

Open `tenerife-dem.tif` as a raster layer in your GIS. Check that it lies over
Tenerife, has 25-meter pixels, and contains elevation values rather than only
NoData cells. If you have GDAL installed, inspect it with:

```bash
gdalinfo -stats tenerife-dem.tif
```

This request was checked on November 17, 2026: the downloaded GeoTIFF had 77
columns, 90 rows, 25-meter pixels, a WGS 84 / UTM zone 28N coordinate system
(EPSG:32628), and no NoData cells. Dataset availability and values can change.

## Choose your area and resolution

Without `bbox_crs`, provide `bbox` as four comma-separated WGS84 coordinates:

```text
west longitude,south latitude,east longitude,north latitude
```

Longitude comes first. West longitudes and south latitudes are negative. The
west value must be less than the east value, and south less than north. Choose
a small area within the dataset's coverage. These requests use UTM output;
avoid areas spanning the antimeridian or polar regions in this workflow.

`cellsize` controls the output pixel spacing and defaults to 30 meters. A smaller
number produces more pixels; it does not add detail absent from the source.
The service rejects requests whose estimated width or height exceeds 4096
pixels. Reduce the area or increase the cell size if you reach this limit.

The downloaded raster is projected to UTM automatically, so its coordinates
will usually be eastings and northings, not the longitude/latitude values you
submitted. Inspect the output CRS and extent in your GIS.

### Use coordinates from a projected map

If your bounds are already in a projected coordinate reference system (CRS),
set `bbox_crs` and provide `bbox` in that CRS's easting/northing order:
`left,bottom,right,top`. The output uses that same CRS. For example:

```bash
curl --fail --show-error --get \
  'https://wepp.cloud/webservices/wmesque2/retrieve/tenerife/136_MDT25_TF' \
  --data-urlencode 'bbox=349000,3131000,350000,3132000' \
  --data-urlencode 'bbox_crs=EPSG:32628' \
  --data-urlencode 'cellsize=25' \
  --data-urlencode 'format=GTiff' \
  --output tenerife-projected.tif
```

Use a projected CRS with meter units for the examples in this guide. Although
the API describes `cellsize` in meters, projected requests pass it through in
the target CRS's units without conversion. Do not use `bbox_crs=EPSG:4326`:
for WGS84 longitude/latitude, omit `bbox_crs`.

## Choose resampling and output format

Add optional parameters to the URL or as another `--data-urlencode` argument.
Values are case-sensitive.

| Parameter | Choices and behavior |
| --- | --- |
| `resample` | `near`, `bilinear`, `cubic`, `cubicspline`, `lanczos`, `average`, `rms`, `mode`, `max`, `min`, `med`, `q1`, `q3`, `sum`. If omitted, the service chooses `near` for integer source data and `bilinear` for floating-point data. |
| `format` | `GTiff` (default, `.tif`), `AAIGrid` (`.asc`), `PNG` (`.png`), or `ENVI` (`.raw`). |
| `gdaldem` | Optional terrain processing: `hillshade`, `slope`, `aspect`, `tri`, `tpi`, or `roughness`. Use with elevation data and check its vertical units before interpreting the result. |

For class codes such as land-cover categories, specify `resample=near` to keep
existing class values. For continuous elevation data, `bilinear` interpolates
between neighboring values. The automatic choice is based on storage type,
not the scientific meaning of the dataset.

Use `GTiff` for GIS analysis: the single file carries its georeferencing. Other
formats may require companion files for georeferencing or interpretation;
the service returns only the primary output file, not a bundle of sidecars.
A PNG is not necessarily a styled map. For a terrain visualization, try
`gdaldem=hillshade` with the elevation example and save it under a new filename.

## Keep a record of the download

Save the request URL, retrieval date, downloaded raster, and response headers
alongside your analysis. The `WMesque-Meta` response header contains URL-safe
base64-encoded JSON with dataset, processing, CRS, and timestamp information.
Decode the header saved by the first example with Python 3:

```python
import base64
import json
from pathlib import Path

headers = Path("tenerife-headers.txt").read_text()
encoded = next(
    line.split(":", 1)[1].strip()
    for line in headers.splitlines()
    if line.lower().startswith("wmesque-meta:")
)
metadata = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
Path("tenerife-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(json.dumps(metadata["wmesque"], indent=2))
```

Metadata may also include source information, but is not guaranteed to include
all attribution, licensing, or scientific provenance you need.

For datasets with managed revisions, the
[revision manifest](https://wepp.cloud/webservices/wmesque2/catalog/manifest)
maps dataset IDs to revision hashes in its `datasets` object. To require one
of those revisions, add `expected_revision=HASH`, replacing `HASH` with the full
64-character hash. A different or unavailable revision returns HTTP 409; the
parameter does not retrieve arbitrary historical versions. Successful metadata
records the revision under `wmesque.revision`. Legacy datasets may have no
revision, and their absence from the manifest does not mean they are unavailable.
Keep the raster itself when you need to reproduce an analysis.

## Troubleshoot a download

| Symptom | What to do |
| --- | --- |
| HTTP 400: invalid bounding box or CRS | Use four comma-separated numbers in west/south/east/north order, or easting/northing order with a projected `bbox_crs`. Check that both dimensions have positive extent. |
| HTTP 400: output size exceeds 4096 × 4096 pixels | Request a smaller area or increase `cellsize`. |
| HTTP 400: invalid option | Check capitalization and the supported values above. |
| HTTP 404: dataset unavailable | Check the same server's catalog and use the dataset ID without `/geodata/` or `/.vrt`. If a listed ID fails, report it to the service operator. |
| HTTP 409: requested revision unavailable | Compare your required hash with the manifest. If reproducibility matters, keep the requirement and ask the operator about availability. |
| HTTP 422: validation error | Check for missing `bbox`, a nonnumeric or nonpositive `cellsize`, or a revision hash that is not 64 lowercase hexadecimal characters. |
| HTTP 500, 502, 503, or timeout | Retry a small request later. If it persists, send the operator the request URL, time, and error response. |
| Blank raster or only NoData cells | Check dataset coverage and coordinate order. A successful download does not prove that the requested area contains usable data. |
| Raster appears in the wrong place | Read the file's CRS and extent; check your input coordinates and `bbox_crs`. Use GeoTIFF to preserve georeferencing in the download. |

In a browser, errors normally appear as JSON instead of a download. To inspect
an error from a command-line request, repeat it with `curl --include` and without
`--fail` or `--output`, keeping the same URL and parameters; avoid doing this for
a successful binary download because it writes the raster to your terminal.

## Further reference

- [Operations guide](../infrastructure/wmesque-operations.md): configure servers, publish datasets, and synchronize replicas.
- [Catalog and retrieval contract](../schemas/wmesque-catalog-contract.md): revision and client compatibility guarantees.
- [Service implementation](../../wepppy/webservices/wmesque2.py): full request handling and format details.
