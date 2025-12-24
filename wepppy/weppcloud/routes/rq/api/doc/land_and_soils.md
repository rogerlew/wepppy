

# Landuse and Soils API Endpoint

Build management and soil files for WEPP based on a specified geographic extent.

---

## Base URL

```
https://wepp.cloud/weppcloud
```

---

## Endpoints

### 1. Submit Job

**POST** `/rq/api/landuse_and_soils`

#### Request Body (JSON)

| Parameter  | Type     | Required | Description                                                                                |
|------------|----------|----------|--------------------------------------------------------------------------------------------|
| `extent`   | list   | Yes      | Bounding box in WGS84 lat/long, ordered as `[xmin,ymax,xmax,ymin]`.                         |
| `cfg`      | string | No       | Optional project-level configuration (load https://wepp.cloud/weppcloud/create/ to see full list of configs)         |
| `nlcd_db`  | string   | No       | Override NLCD database (default: `nlcd/2019`). WEPPcloud supports annual NLCD maps from 1985–2023.  |
| `ssurgo_db`| string   | No       | Override SSURGO database (default: `ssurgo/gNATSGSO/2025`). Recommended to stick to gNATSGSO/2025 to avoid fallback to STATSGO. |

#### Sample Request

```bash
curl -X POST https://wepp.cloud/weppcloud/rq/api/landuse_and_soils \
  -H "Content-Type: application/json" \
  -d '{
    "extent": [-116.41064222362726, 45.24964993419109, -116.34096842541693, 45.298680435792484],
    "nlcd_db": "nlcd/2021",
    "ssurgo_db": "ssurgo/gNATSGSO/2025"
}'
```

#### Response

```json
{
  "Success": true,
  "job_id": "cc4a620e-473f-478e-b33b-71f56fd6b544"
}
```

_Success_ = true indicates the job has been succesfully submitted to the job engine

---

### 2. Check Job Status

**GET** `/rq-engine/api/jobinfo/{job_id}` (preferred)  
Fallback: `/weppcloud/rq/api/jobinfo/{job_id}`

Returns JSON status and progress for the submitted job.

_Note:_ The jobinfo is tied to redis is only available for up to 7 days as currently configured.

#### Sample Request

```bash
curl https://wepp.cloud/rq-engine/api/jobinfo/cc4a620e-473f-478e-b33b-71f56fd6b544
```

---

### 3. Download Project

**GET** `/rq/api/landuse_and_soils/{job_id}.tar.gz`

Once the job is complete, download the resulting WEPPcloud project as a `.tar.gz`.

#### Sample Request

```bash
wget https://wepp.cloud/weppcloud/rq/api/landuse_and_soils/cc4a620e-473f-478e-b33b-71f56fd6b544.tar.gz
mkdir <output_dir>
tar -xvzf cc4a620e-473f-478e-b33b-71f56fd6b544.tar.gz -C <output_dir>
```

---

## Project Structure

After extraction, the archive contains:

```
landuse.nodb        # JSON summary of managements
landuse/
  ├ nlcd.tif            # Raster land cover map
  └ *.man               # Management files (single-year rotations)
   

soils.nodb          # JSON summary of soil classes
soils/
  ├ ssurgo.tif          # Raster soil map
  └ *.sol               # Soil property files
```

---

## Notes & Caveats

- **Extent format** is strict: `xmin,ymax,xmax,ymin` in decimal degrees.
- **Defaults**: if not supplied, uses `nlcd/2019` and `ssurgo/gNATSGO/2025`.
- **NLCD**: annual maps available from 1985 through 2023.
- **Fallback**: if SSURGO data is unavailable, the endpoint will not return a raster when falling back to STATSGO.
- **Performance**: job submission takes only a few seconds for a small watershed and a minute or several minutes for a large watershed.
- **Webhooks (TODO)**: support to callback when job completes for clients with public endpoints.
- **Multi-year rotations (TODO)**: current managements are single-year; future support may include `nyears` parameter to append rotations.

---
