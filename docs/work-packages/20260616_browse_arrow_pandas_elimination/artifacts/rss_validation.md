# Browse Worker RSS Validation

**Date**: 2026-06-16 19:24 UTC  
**Environment**: local `docker-compose.dev.yml` stack, `wepppy-browse` Gunicorn service with 3 Uvicorn workers on port 9009  
**Code state**: local working tree after Arrow-backed browse parquet implementation and logger visibility patch  
**Run artifact**: `/wc1/runs/ho/honeyed-marathoner/_pups/omni/scenarios/mulch_15_sbs_map/wepp/output/interchange/H.wat.parquet`

## Probe

Artifact size:

```text
34,332,309 bytes
```

Baseline worker RSS after local `browse` restart and health check:

```text
PID 8   RSS 450,648 KiB
PID 9   RSS 450,408 KiB
PID 38  RSS 453,840 KiB
```

Requests:

```bash
curl -sS -o /tmp/browse-preview-probe2.html -w 'preview %{http_code} %{time_total} %{size_download}\n' \
  'http://127.0.0.1:9009/weppcloud/runs/honeyed-marathoner/ho/browse/_pups/omni/scenarios/mulch_15_sbs_map/wepp/output/interchange/H.wat.parquet'

curl -sS -o /tmp/browse-csv-probe2.csv -w 'csv %{http_code} %{time_total} %{size_download}\n' \
  'http://127.0.0.1:9009/weppcloud/runs/honeyed-marathoner/ho/download/_pups/omni/scenarios/mulch_15_sbs_map/wepp/output/interchange/H.wat.parquet?as_csv=1'
```

Results:

```text
preview 200 0.281098 334423
csv 200 103.551648 152631570
```

Telemetry emitted by the browse workers:

```text
INFO:wepppy.microservices.browse.browse:browse parquet operation=preview file=H.wat.parquet size_bytes=34332309 rows=500 duration_ms=193.9 rss_before_kb=520924 rss_after_kb=470752 rss_delta_kb=-50172 status=ok
INFO:wepppy.microservices.browse._download:browse parquet operation=csv_export file=H.wat.parquet size_bytes=34332309 rows=None duration_ms=103290.4 rss_before_kb=450616 rss_after_kb=748656 rss_delta_kb=298040 status=ok
```

Immediate worker RSS after the CSV export completed:

```text
PID 8   RSS 450,656 KiB
PID 9   RSS 582,856 KiB
PID 38  RSS 470,292 KiB
```

Worker RSS after a 15 second settling window:

```text
PID 8   RSS 450,656 KiB
PID 9   RSS 582,856 KiB
PID 38  RSS 470,292 KiB
```

## Interpretation

The local Gunicorn worker process model exercised the new route code through HTTP, not helper-only calls. The heaviest worker settled at about 583 MiB after a 34 MB parquet preview and full CSV export that produced a 153 MB response. That is materially below the June 16 production failure signature of workers retaining tens of GiB RSS.

This probe validates the local process-model mitigation. It is not a substitute for post-deployment monitoring on `wepp1`, where NFS behavior, public traffic mix, Caddy buffering, and longer worker lifetimes may still affect RSS and latency.
