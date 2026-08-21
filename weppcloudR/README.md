# WEPPcloudR Service

Containerized Plumber API that renders WEPPcloud reports (e.g. the
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

## One-shot renderer

Kubernetes Jobs use `render-request-v1.R`, not the Plumber entrypoint. The
controller mounts one immutable request at `/run/weppcloudr/request.json`,
passes its independently trusted SHA-256 digest, and starts the process with
the canonical run WD as its working directory. The script rejects unknown
fields, mismatched paths/digests, and invalid identifiers, renders to a
generation-unique temporary file, then atomically publishes the final HTML.

The source is included in the standalone WEPPcloudR image, but this repository
change does not build, publish, or deploy that image. The Kubernetes deployment
must provide the reviewed fixed entrypoint, read-only root filesystem,
run-scoped PVC mount, read-only geodata, resource/security context, and disabled
service-account token described by
`docs/schemas/weppcloudr-render-execution-contract.md`.

## Next Steps

- Implement JWT validation when the Flask redirect starts forwarding
  auth headers.
