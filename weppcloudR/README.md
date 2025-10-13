# WEPPcloudR Service

Containerised Plumber API that renders WEPPcloud reports (e.g. the
“DEVAL Details” HTML) using the interchange parquet assets shared by the
main Flask app.

## Build & Run

```
docker build -t weppcloudr-service .
docker run --rm \
  -p 8000:8000 \
  -v /geodata:/geodata:ro \
  -v /wc1:/wc1:ro \
  -v /path/to/weppcloudR:/srv/weppcloudr:ro \
  -v /path/to/WEPPcloudR:/srv/original-weppcloudr:ro \
  weppcloudr-service
```

Environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8000` | Listener port inside the container. |
| `HOST` | `0.0.0.0` | Bind address for Plumber. |
| `PRIMARY_RUN_ROOT` | `/geodata/weppcloud_runs` | Primary location for run directories. |
| `PARTITIONED_RUN_ROOT` | `/wc1/runs` | Partitioned run root for migrated runs. |
| `BATCH_ROOT` | `/wc1/batch` | Root directory for batch scenarios. |
| `TEMPLATE_ROOT` | `/srv/weppcloudr/templates/scripts/users/chinmay` | Directory containing `new_report.Rmd` and helper scripts (bind-mount the repo there). |
| `DEVAL_TEMPLATE` | `<TEMPLATE_ROOT>/new_report.Rmd` | Template used for the DEVAL report. |

## Endpoints

- `GET /healthz` – readiness/liveness probe.
- `GET /runs/<runid>/<config>/report/deval_details` – renders the DEVAL
  R Markdown report and returns HTML. Automatically creates
  `<run>/export/WEPPcloudR/` when absent.

## Next Steps

- Refactor `new_report.Rmd` and helper functions to consume interchange
  parquet data (drop legacy Arc/CSV shims).
- Implement JWT validation when the Flask redirect starts forwarding
  auth headers.
- Add automated smoke tests that mount a fixture run directory and
  verify the HTML payload returned by the render endpoint.
