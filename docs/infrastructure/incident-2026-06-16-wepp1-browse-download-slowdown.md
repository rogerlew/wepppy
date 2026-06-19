# Incident Report: wepp1 Browse Download Slowdown
> Date: June 16, 2026 (America/Los_Angeles)  
> Scope: WEPPcloud archive/file downloads through `browse` on `wepp1`  
> Status: mitigated with targeted `browse` restart; follow-up observation found intermittent `browse` responsiveness degradation, but no current broad download slowdown or high-RSS recurrence

## Summary
A user reported that archived WEPPcloud simulation downloads had become extremely slow, with an approximately 400 MB archive taking several hours where similar files previously downloaded in minutes.

Investigation on `wepp1` found no host-wide CPU, memory, RQ, disk, or public-network saturation at the time of inspection. The concrete server-side fault was isolated to the `browse` service, which serves `/weppcloud/runs/.../download/...` and archive dashboard download links. `browse` had repeated worker timeouts, slow directory listing warnings, and two workers with abnormal resident memory near 45-49 GiB each.

A targeted restart of `browse` cleared the abnormal worker memory and restored a normal service baseline. This likely improved the server-side condition, but the exact user archive URL was not available during initial triage, so the specific slow download path was not reproduced end to end until a follow-up probe.

Follow-up observation on June 19, 2026 found that the Arrow-to-pandas browse mitigation and lazy D-Tale Parquet backend were deployed. Current archive and local Caddy probes were fast, and `browse` worker RSS stayed in the normal hundreds-of-MiB range. However, logs since the June 17 deployment showed intermittent `browse` worker timeouts and slow directory listing warnings. The remaining evidence points to intermittent browse/NFS metadata pressure and noisy client traffic rather than recurrence of the June 16 high-RSS failure mode.

## Impact
- Users could experience very slow downloads for project archive ZIPs or run files served through `browse`.
- Browse directory views could also be slow or time out when NFS metadata operations stalled.
- The main WEPPcloud app and RQ queues were not globally down during inspection.

## Environment
- Host: `wepp1`
- Host time checked: `Tue Jun 16 08:10:04 PDT 2026`
- Compose stack: services up for about 24 hours before mitigation
- Download route:
  - Caddy route `/weppcloud/runs/<runid>/<config>/download/...`
  - reverse proxy target: `browse:9009`
  - browse command: `gunicorn --workers 8 --bind 0.0.0.0:9009 -k uvicorn.workers.UvicornWorker ...`
- Storage:
  - `/geodata` mounted from `nas.rocket.net:/wepp` via NFSv4.2
  - mount options included `hard`, `rsize=65536`, `wsize=65536`, `acregmax=30`, `acdirmin=5`

## Detection
The issue was initiated by a user email report of slow archive downloads. Operational checks then found:

- `docker compose ps`: stack up, including `browse`, `caddy`, `weppcloud`, Redis, Postgres, and RQ services.
- `wctl rq-info`: default and batch queues idle.
- `df -h /geodata`: NFS volume at about 72% used (`33T` size, `24T` used, `9.3T` available).
- `free -h` before mitigation: about `99Gi` used and `152Gi` available.
- `sar -n DEV 1 5`: external NIC utilization near zero during inspection.
- `iostat -xz 1 3`: low host disk utilization and low iowait during inspection.

## Timeline
All times below are June 16, 2026.

| Time | Zone | Event |
| --- | --- | --- |
| 08:10 | PDT | Verified host identity as `wepp1`; load average about `2.86, 2.75, 2.79`. |
| 08:10 | PDT | Confirmed stack was up and RQ queues were idle. |
| 08:10-08:14 | PDT | Checked Caddy route: run downloads are proxied to `browse:9009`. |
| 05:37 | PDT | `browse` logged `WORKER TIMEOUT (pid:13645)`. |
| 05:38 | PDT | `browse` logged `WORKER TIMEOUT (pid:12150)`. |
| 07:09 | PDT | `browse` logged `WORKER TIMEOUT (pid:12735)`. |
| 07:11 | PDT | `browse` logged `WORKER TIMEOUT (pid:12442)`. |
| 08:14 | PDT | Process inspection showed two `browse` workers with abnormal memory: about 48.8 GB and 44.8 GB RSS. |
| 08:16:51 | PDT | Restarted only `browse` with `wctl docker compose restart browse`. |
| 08:17 | PDT | `browse` restarted and all eight workers booted successfully. |
| 08:18 | PDT | Post-restart worker RSS settled around 452-471 MB per worker; current CPU sampled near idle. |

## Technical Findings
### 1) `browse` showed repeated worker timeouts
In the six hours before mitigation, `browse` logs contained 38 matching worker-churn, timeout, or slow-listing entries, including:

```text
[2026-06-16 12:37:41 +0000] [7] [CRITICAL] WORKER TIMEOUT (pid:13645)
[2026-06-16 12:38:08 +0000] [7] [CRITICAL] WORKER TIMEOUT (pid:12150)
[2026-06-16 14:09:34 +0000] [7] [CRITICAL] WORKER TIMEOUT (pid:12735)
[2026-06-16 14:11:21 +0000] [7] [CRITICAL] WORKER TIMEOUT (pid:12442)
```

These are direct service-health symptoms in the process responsible for run file and archive downloads.

### 2) `browse` workers accumulated abnormal memory
Before restart, two `browse` workers were much larger than expected:

```text
PID 183872: VmRSS 48820504 kB, RssAnon 48655888 kB, Threads 294
PID 235613: VmRSS 44845644 kB, RssAnon 44665804 kB, Threads 294
```

After the `browse` restart, all eight workers were in the expected range:

```text
VmRSS about 451944-470528 kB per worker
Threads about 230-251 per worker
```

Host memory also improved:

```text
Before: about 99Gi used, 152Gi available
After:  about 19Gi used, 232Gi available
```

### 3) NFS metadata operations were intermittently pathological
Several diagnostic `find` commands over `/geodata/wc1/runs` blocked in kernel `D` state during shallow metadata scans. The commands were stopped after they failed to complete promptly.

This is consistent with earlier WEPPcloud evidence that browse and archive surfaces are sensitive to NFS metadata latency because they list directories, stat entries, and sometimes count child entries.

### 4) Caddy showed many incomplete browse/download responses
In the last 24 hours before inspection:

```text
download/archive log-line matches: 904
aborting with incomplete response warnings: 1279
```

Many warnings were for `browse:9009` and had crawler-like user agents or remote IPs unrelated to the reporting user. This is not proof that those clients caused the slowdown, but it indicates the browse/download surface was under noisy client pressure.

### 5) WSU-specific evidence was not found in available logs
Searches for `134.121.*`, `wsu`, and `washington` in recent Caddy logs did not find a matching client. Successful downloads are not logged with timing by default, so this does not prove WSU was absent; it only means the available warning/error logs did not show a clear WSU client signature.

### 6) Generic bandwidth probes did not reproduce a broad edge slowdown
After mitigation:

```text
Local Caddy diagnostic, 4 MiB:
http=200 bytes=4194304 speed=138980880Bps time=0.030179s

External probe from operator workspace, 4 MiB:
http=200 bytes=4194304 speed=11815506Bps time=0.354983s
```

The diagnostic endpoint rejected larger 10 MiB and 100 MiB probes with `413`, so it could not be used as a large-file archive substitute.

## Mitigation
Performed a targeted restart of only the `browse` service:

```bash
cd /workdir/wepppy
wctl docker compose restart browse
```

No active established `browse`/Python download sockets were observed immediately before the restart.

## Verification
Post-restart checks:

```bash
wctl docker compose ps browse
wctl docker compose top browse
curl -k --resolve wepp.cloud:443:127.0.0.1 \
  -o /dev/null -sS -w 'browse_http=%{http_code} time=%{time_total}s bytes=%{size_download}\n' \
  https://wepp.cloud/weppcloud/runs/
```

Observed:
- `browse` was `Up`.
- all eight workers booted and logged `Application startup complete`.
- `https://wepp.cloud/weppcloud/runs/` returned `302` in about `0.0106s` through local Caddy.
- current worker CPU sampled near idle with `pidstat`.
- worker memory returned to expected levels.

## Follow-up Exact Archive Probe
After the initial mitigation, the user provided the exact public archive URL:

```text
https://wepp.cloud/weppcloud/runs/arcadian-mourner/disturbed9002_wbt/download/archives/arcadian-mourner.20260616T152300Z.zip
```

Run path mapping:

```text
host:      /geodata/wc1/runs/ar/arcadian-mourner/archives/arcadian-mourner.20260616T152300Z.zip
container: /wc1/runs/ar/arcadian-mourner/archives/arcadian-mourner.20260616T152300Z.zip
```

Observed at `Tue Jun 16 08:26:31 PDT 2026`:

```text
size=731391829 bytes
mtime=2026-06-16 08:25:31.003685000 -0700
```

Public response headers were correct:

```text
HTTP/2 200
accept-ranges: bytes
content-disposition: attachment; filename="arcadian-mourner.20260616T152300Z.zip"
content-type: application/zip
content-length: 731391829
```

Read and download timings:

```text
host_full_read elapsed=5.41 sec
local_caddy_full http=200 version=2 bytes=731391829 speed=135449904Bps time=5.399722s
external_full_auto http=200 version=2 bytes=731391829 speed=117202809Bps time=6.240395s
external_full_http1 http=200 version=1.1 bytes=731391829 speed=116611325Bps time=6.272048s
```

The exact archive did not reproduce a server-side or general public-edge slowdown after the `browse` restart. HTTP/2 and HTTP/1.1 performed similarly from the operator workspace. `curl` on the operator host did not include HTTP/3 support, so QUIC/HTTP/3 client-path behavior was not tested even though Caddy advertises `h3` via `alt-svc`.

## PyArrow-to-Pandas Remediation Work
The June 16 high-RSS finding was routed into two remediation work packages because there were two separate long-lived service boundaries where Parquet data could become pandas DataFrames:

- [Browse Arrow-to-Pandas Elimination](../work-packages/20260616_browse_arrow_pandas_elimination/package.md) targets the `browse` service request paths. Its inventory found production browse Parquet materialization in `_download.py`, `flow.py`, and `parquet_filters.py`: `table.to_pandas()`, `env.pd.read_parquet(...)`, and DuckDB `.df()` conversions. The implementation replaces those paths with bounded DuckDB/PyArrow helpers, Arrow-backed HTML previews, batch-oriented CSV export with `ParquetFile.iter_batches(...)`, and RSS/duration telemetry for Parquet preview/export operations. The local Gunicorn validation artifact showed a 34 MB Parquet preview plus 153 MB CSV export settling with the hottest worker around 583 MiB RSS, materially below the June 16 failure signature of 45-49 GiB workers.
- [D-Tale Lazy Parquet Backend](../work-packages/20260616_dtale_lazy_parquet_backend/package.md) targets the separate `dtale` service. The browse D-Tale bridge only forwards authorized path/filter metadata, but D-Tale itself previously loaded Parquet artifacts through eager pandas paths. This package registers Parquet, GeoParquet, and PQ files as lazy D-Tale datasets, uses bounded DuckDB/PyArrow page reads for grid data, removes Parquet from the eager `_load_dataframe` dispatch, and rejects lazy D-Tale export requests that would otherwise ask for all rows. Small pandas slices remain only at the D-Tale presentation seam where upstream D-Tale expects pandas-shaped page data.

The work-package docs were still in their production-observation window at the time of this incident-report update. The June 19 production check confirms that the deployed code included the D-Tale lazy backend commit and that current `browse`/`dtale` RSS did not show recurrence of the PyArrow-to-pandas high-RSS failure mode. It does not close the observation window because `browse` still logged intermittent worker timeouts and slow directory listings after deployment.

## Post-Mitigation Observation
Observed on `wepp1` on June 19, 2026 between about 08:49 and 08:52 PDT:

- `browse`, `caddy`, and `dtale` were running and had been up since June 17, 2026 at about 06:36 PDT.
- Deployed code was `1eff84354` (`Add lazy parquet D-Tale backend`, committed June 16, 2026 at 13:22:57 PDT).
- Host load was low (`1.20, 1.08, 1.45`), `/geodata` was 72% used, memory had about 222 GiB available, and sampled iowait/public-network use were low.
- Current `browse` worker RSS was about 488-645 MiB per worker; `dtale` was about 814 MiB RSS.
- A local Caddy 4 MiB diagnostic completed in `0.033075s` at about 126.8 MB/s.
- `/weppcloud/runs/` returned `302` through local Caddy in `0.012370s`.
- The exact incident archive still existed with size `731391829` bytes and returned correct headers.
- A 64 MiB public range request for the exact incident archive completed in `1.521683s` at about 44.1 MB/s.
- The same 64 MiB archive range through local Caddy on `wepp1` completed in `0.562602s` at about 119.3 MB/s.

The 72-hour log window still showed intermittent degraded `browse` responsiveness after the June 17 rollout:

```text
browse WORKER TIMEOUT entries: 70
slow listing warnings: 95
caddy incomplete responses: 1561
caddy incomplete responses involving browse:9009: 1489
```

Timeouts appeared in clusters, including June 18 around 10:58-11:01 PDT and smaller clusters later on June 18 and early June 19. Slow listing warnings were spread across the window; the worst observed warning was:

```text
2026-06-18T16:22:44Z browse.get_page_entries() completed after 51.9 seconds
```

Recent Caddy incomplete-response examples were mostly client disconnects within milliseconds to a few seconds, often with crawler-like user agents and public run-file paths. That is noisy pressure on `browse`, but it is not by itself proof of a current server-side throughput collapse.

No production restart or mitigation action was performed during this observation.

## Assessment
Most likely contributors:

- Original June 16 event: `browse` worker memory growth or leaked request state.
- Ongoing intermittent symptoms: slow NFS metadata calls under browse/archive listing workloads.
- Ongoing external pressure: noisy crawler traffic or aborted clients increasing `browse` worker churn.

Less likely based on current evidence:

- whole-host CPU saturation.
- whole-host public network saturation.
- RQ backlog.
- Postgres or Redis outage.
- Caddy/TLS as the primary bottleneck.
- recurrence of the June 16 high-RSS browse worker condition after the June 17 deployment.

Not proven:

- the exact slow archive path that affected the user.
- WSU firewall/content-inspection behavior.
- a single NAS fault versus application-level metadata amplification.
- whether the remaining worker timeout clusters are caused by a small set of pathological directories, client disconnect pressure, NFS latency, or another request path.

## Follow-up Actions
1. Continue `browse` post-deployment observation for the 14-day work-package window:
   - alert or manually check for `WORKER TIMEOUT` clusters
   - sample worker RSS and confirm workers remain below a practical threshold, for example 4 GiB
   - track slow listing warnings and correlate them with request paths when possible
   - append production observations to the browse and D-Tale work-package trackers before closing the observation windows
2. Add or enable access timing for successful `browse` downloads and slow browse listings:
   - runid/config/subpath
   - file size
   - response duration
   - client IP / forwarded IP
   - status and disconnect/abort reason
3. Add path-safe logging for slow directory listings so operators can identify directories that trigger metadata amplification without logging private file contents.
4. Ask the user to retry the exact archive URL and report:
   - wall-clock elapsed time
   - browser
   - whether they are on the WSU network or VPN
   - whether an HTTP/1.1 command-line download is also slow
5. Investigate why `browse` workers previously retained tens of GiB and hundreds of threads, but treat this as a recurrence-prevention task unless high RSS returns.
6. Consider reducing metadata amplification for archive listings:
   - cache archive list metadata briefly
   - avoid opening ZIP comments during every archive list request when not needed
   - avoid recursive or child-count metadata calls in high-latency NFS paths
7. Consider Caddy/user-agent controls during crawler pressure events if incomplete-response warnings continue.
8. If WSU remains slow while external probes are fast, test whether disabling QUIC/HTTP/3 or using HTTP/1.1 changes the client-side result.

## Useful Commands For Recurrence
```bash
# Host identity and stack health
hostname
date
uptime
cd /workdir/wepppy && wctl docker compose ps
cd /workdir/wepppy && wctl rq-info

# Browse service health
cd /workdir/wepppy && wctl docker compose logs --since 6h browse \
  | egrep 'WORKER TIMEOUT|directory count took|get_page_entries\(\) completed'
cd /workdir/wepppy && wctl docker compose top browse

# Worker memory
for p in $(pgrep -f 'gunicorn --workers 8 --bind 0.0.0.0:9009' | tail -n +2); do
  echo "PID=$p"
  egrep 'VmRSS|RssAnon|Threads|State' /proc/$p/status
done

# Download route smoke through local Caddy
curl -k --resolve wepp.cloud:443:127.0.0.1 \
  -o /dev/null -sS \
  -w 'http=%{http_code} bytes=%{size_download} speed=%{speed_download}Bps time=%{time_total}s\n' \
  'https://wepp.cloud/query-engine/diagnostics/bandwidth/download?bytes=4194304'
```
