# Incident Report: wepp1 Browse Download Slowdown
> Date: June 16, 2026 (America/Los_Angeles)  
> Scope: WEPPcloud archive/file downloads through `browse` on `wepp1`  
> Status: mitigated with targeted `browse` restart; follow-up observation found intermittent `browse` responsiveness degradation, but no current broad download slowdown or high-RSS recurrence; dedicated archive download service remediation implemented and locally validated on June 19, 2026 with production cutover evidence still pending

## Summary
A user reported that archived WEPPcloud simulation downloads had become extremely slow, with an approximately 400 MB archive taking several hours where similar files previously downloaded in minutes.

Investigation on `wepp1` found no host-wide CPU, memory, RQ, disk, or public-network saturation at the time of inspection. The concrete server-side fault was isolated to the `browse` service, which serves `/weppcloud/runs/.../download/...` and archive dashboard download links. `browse` had repeated worker timeouts, slow directory listing warnings, and two workers with abnormal resident memory near 45-49 GiB each.

A targeted restart of `browse` cleared the abnormal worker memory and restored a normal service baseline. This likely improved the server-side condition, but the exact user archive URL was not available during initial triage, so the specific slow download path was not reproduced end to end until a follow-up probe.

Follow-up observation on June 19, 2026 found that the Arrow-to-pandas browse mitigation and lazy D-Tale Parquet backend were deployed. Current archive and local Caddy probes were fast, and `browse` worker RSS stayed in the normal hundreds-of-MiB range. However, logs since the June 17 deployment showed intermittent `browse` worker timeouts and slow directory listing warnings. The remaining evidence points to intermittent browse/NFS metadata pressure and noisy client traffic rather than recurrence of the June 16 high-RSS failure mode.

On June 19, 2026, the incident follow-up added a dedicated archive download service. Exact ZIP archive routes keep their public URL shape but can be routed by Caddy to `download:9011` instead of the interactive `browse:9009` worker pool. The service reuses canonical browse authorization and path-security helpers, supports `HEAD`, full `GET`, and single-range/resume `GET`, and emits one structured `download.complete` log line per request. This does not remove NFS as a shared dependency, but it removes browse UI, D-Tale/parquet, directory listing, crawler, and long archive-stream common-cause vectors from the critical archive-download path.

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
  - original reverse proxy target: `browse:9009`
  - dedicated archive remediation target: exact `/download/archives/*.zip` route to `download:9011`; non-archive download and browse route families remain on `browse:9009`
  - browse command: `gunicorn --workers 8 --bind 0.0.0.0:9009 -k uvicorn.workers.UvicornWorker ...`
  - download command: `gunicorn --workers ... --bind 0.0.0.0:9011 -k uvicorn.workers.UvicornWorker wepppy.microservices.download:app`
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

## Dedicated Download Service Remediation
The June 19 follow-up created and pushed the [Dedicated Download Service for Critical Run Artifacts](../work-packages/20260619_dedicated_download_service/package.md) package.

Implemented behavior:

- Adds `wepppy.microservices.download`, a Starlette/Gunicorn/Uvicorn service listening on port `9011`.
- Routes exact archive ZIP URLs matching `/weppcloud/runs/{runid}/{config}/download/archives/*.zip` to `download:9011` through Caddy before the broader `browse` matcher.
- Keeps existing public URLs stable; users do not need new links.
- Leaves directory browsing, schema/files APIs, D-Tale handoff, `gdalinfo`, aria2c manifests, parquet-to-CSV, culvert, batch, and non-migrated compatibility downloads on `browse`.
- Reuses `wepppy.microservices.browse.auth` and `wepppy.microservices.browse.security` so public/private run and path-boundary behavior does not fork.
- Supports `HEAD`, full `GET`, closed ranges, open-ended ranges, suffix ranges, and invalid-range `416` responses.
- Rejects raw `.`, `..`, repeated separator, backslash, hidden path, non-ZIP, and out-of-scope archive paths.
- Runs archive file open, seek, read, and close operations through worker threads so slow storage reads do not block the ASGI event loop.

Enhanced logging:

```text
download.complete route_family=run_archive request_id=<id> runid=<runid> config=<config> path_category=archives basename=<archive.zip> file_size=<bytes> method=<HEAD|GET> status=<status> range_start=<start> range_end=<end> bytes_sent=<bytes> duration_ms=<ms> outcome=<success|client_aborted|not_found|forbidden|range_not_satisfiable|server_error> error_reason=<reason> client_ip=<ip> user_agent=<ua>
```

The log intentionally records the sanitized archive category and basename, not absolute filesystem paths. It must not contain Authorization headers, cookies, JWTs, raw query strings, or full run-root paths.

Local validation evidence captured on June 19, 2026:

```text
wctl focused pytest slice: 140 passed, 5 warnings
local Caddy HEAD: 200, Accept-Ranges: bytes, Content-Length: 2516876934, Server: uvicorn, Via: 1.1 Caddy
local Caddy full GET: 200, 2516876934 bytes in 12.207687 seconds, curl speed 206171483 bytes/s
local Caddy range: 206, Content-Range: bytes 0-1048575/2516876934, 1048576 bytes
local Caddy sparse resume: 206, Content-Range: bytes 2515828358-2516876933/2516876934, 1048576 bytes
download.complete logs: matching HEAD, full GET, and range/resume completion records with bytes, duration, request id, range metadata, and sanitized basename
```

The QA and security review artifacts have no unresolved findings:

- [QA review](../work-packages/20260619_dedicated_download_service/artifacts/20260619_qa_review.md)
- [Security review](../work-packages/20260619_dedicated_download_service/artifacts/20260619_security_review.md)

Production status at the time of this update: code is committed to `master` in commit `0791616db` (`Add dedicated archive download service`), but the incident is not considered fully closed until wepp1 cutover and production smoke/log evidence are captured.

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

Dedicated download remediation assessment:

- The service split should eliminate several non-NFS common-cause vectors for exact archive ZIP downloads: browse worker RSS growth, D-Tale/parquet request pressure, directory listing stalls, crawler-heavy browse paths, and long archive streaming sharing the same worker pool.
- The split does not eliminate NFS. If archive reads stall in NFS kernel I/O, both `browse` and `download` can still be affected by the same storage substrate.
- The new `download.complete` logs make archive health measurable by status, duration, bytes sent, range behavior, client identity, and sanitized artifact identity. Future diagnosis should start from these logs instead of inferring successful download behavior from Caddy warnings alone.

## Follow-up Actions
1. Cut over or confirm cutover of exact archive ZIP downloads to the dedicated `download` service on wepp1:
   - `download` container healthy
   - Caddy archive matcher active before the broad `browse` matcher
   - representative production archive `HEAD`, full `GET`, and range/resume probes return expected headers and statuses
   - matching `download.complete` logs show bytes, duration, status, and range metadata
2. Continue `browse` post-deployment observation for the 14-day work-package window:
   - alert or manually check for `WORKER TIMEOUT` clusters
   - sample worker RSS and confirm workers remain below a practical threshold, for example 4 GiB
   - track slow listing warnings and correlate them with request paths when possible
   - append production observations to the browse and D-Tale work-package trackers before closing the observation windows
3. Use `download.complete` logs as the primary successful-archive evidence source:
   - `status=200` with full `bytes_sent=file_size` for full downloads
   - `status=206` with expected `range_start`, `range_end`, and `bytes_sent` for resume/range probes
   - `duration_ms` and `bytes_sent` for throughput estimates
   - `outcome=client_aborted`, `not_found`, `forbidden`, `range_not_satisfiable`, or `server_error` for failure classification
4. Add or enable equivalent access timing for non-migrated `browse` downloads and slow browse listings:
   - runid/config/subpath
   - file size
   - response duration
   - client IP / forwarded IP
   - status and disconnect/abort reason
5. Add path-safe logging for slow directory listings so operators can identify directories that trigger metadata amplification without logging private file contents.
6. Ask affected users to retry the exact archive URL and report:
   - wall-clock elapsed time
   - browser
   - whether they are on the WSU network or VPN
   - whether an HTTP/1.1 command-line download is also slow
7. Investigate why `browse` workers previously retained tens of GiB and hundreds of threads, but treat this as a recurrence-prevention task unless high RSS returns.
8. Consider reducing metadata amplification for archive listings:
   - cache archive list metadata briefly
   - avoid opening ZIP comments during every archive list request when not needed
   - avoid recursive or child-count metadata calls in high-latency NFS paths
9. Consider Caddy/user-agent controls during crawler pressure events if incomplete-response warnings continue.
10. If WSU remains slow while external probes are fast, test whether disabling QUIC/HTTP/3 or using HTTP/1.1 changes the client-side result.

## Future Health Checks and Troubleshooting

Use these checks when archive downloads are reported slow again. Start by determining whether the exact archive route is being served by `download:9011` or has fallen back to `browse:9009`.

```bash
# Host identity and stack health
hostname
date
uptime
cd /workdir/wepppy && wctl docker compose ps
cd /workdir/wepppy && wctl rq-info

# Dedicated download service health
cd /workdir/wepppy && wctl docker compose ps download caddy browse
cd /workdir/wepppy && wctl docker compose logs --since 30m download \
  | egrep 'download.complete|WORKER TIMEOUT|Traceback|ERROR'

# If the port is published on the host, this should return OK.
curl -fsS http://127.0.0.1:9011/health

# Confirm exact archive routing through local Caddy.
archive_url='https://wepp.cloud/weppcloud/runs/<runid>/<config>/download/archives/<archive>.zip'
curl -k --resolve wepp.cloud:443:127.0.0.1 -I "$archive_url"

# Expected for a public or authorized archive:
# HTTP 200
# Accept-Ranges: bytes
# Content-Length: <archive size>
# Server: uvicorn
# Via: 1.1 Caddy

# Range/resume probe without downloading the whole archive.
curl -k --resolve wepp.cloud:443:127.0.0.1 \
  -H 'Range: bytes=0-1048575' \
  -o /tmp/wepp-archive-range.part -D /tmp/wepp-archive-range.headers \
  -w 'http=%{http_code} bytes=%{size_download} speed=%{speed_download}Bps time=%{time_total}s\n' \
  "$archive_url"
egrep -i 'HTTP/|accept-ranges:|content-range:|content-length:|x-request-id:' /tmp/wepp-archive-range.headers
wc -c /tmp/wepp-archive-range.part

# Full-transfer probe for a representative archive when safe to do so.
curl -k --resolve wepp.cloud:443:127.0.0.1 \
  -o /tmp/wepp-archive-full.zip \
  -w 'http=%{http_code} bytes=%{size_download} speed=%{speed_download}Bps time=%{time_total}s\n' \
  "$archive_url"

# Compute throughput from structured logs. Duration is milliseconds.
cd /workdir/wepppy && wctl docker compose logs --since 30m download \
  | grep 'download.complete' \
  | tail -20

# Browse service health
cd /workdir/wepppy && wctl docker compose logs --since 6h browse \
  | egrep 'WORKER TIMEOUT|directory count took|get_page_entries\(\) completed'
cd /workdir/wepppy && wctl docker compose top browse

# Worker memory
for p in $(pgrep -f 'gunicorn --workers 8 --bind 0.0.0.0:9009' | tail -n +2); do
  echo "PID=$p"
  egrep 'VmRSS|RssAnon|Threads|State' /proc/$p/status
done

# Diagnostic bandwidth route through local Caddy. This is useful for edge sanity,
# but it is not a substitute for exact archive route testing.
curl -k --resolve wepp.cloud:443:127.0.0.1 \
  -o /dev/null -sS \
  -w 'http=%{http_code} bytes=%{size_download} speed=%{speed_download}Bps time=%{time_total}s\n' \
  'https://wepp.cloud/query-engine/diagnostics/bandwidth/download?bytes=4194304'
```

Interpretation guide:

- `Server: uvicorn` plus `download.complete` logs indicates the exact archive route reached the dedicated service.
- `status=200` with `bytes_sent=file_size` and reasonable `duration_ms` indicates a successful full archive transfer from the service perspective.
- `status=206` with expected `range_start`, `range_end`, and `bytes_sent` confirms resume/range behavior.
- Fast local Caddy probes with slow user downloads suggest client path, ISP, VPN, institutional inspection, HTTP/3/QUIC, or browser-specific behavior.
- Slow local Caddy probes plus slow host file reads suggest NFS/storage substrate pressure.
- Slow browse listings with healthy download archive probes suggest metadata amplification or crawler pressure in `browse`, not critical archive streaming.
- High `browse` RSS with healthy `download` RSS suggests recurrence of a browse-specific leak or pandas/materialization path, not the dedicated archive service.

Rollback if the dedicated route is implicated:

```bash
# Disable or revert the exact archive matcher in the active Caddyfile so
# /download/archives/*.zip falls back to browse:9009, then reload Caddy.
cd /workdir/wepppy
wctl docker compose restart caddy

# Optionally stop only the download service after Caddy no longer routes to it.
wctl docker compose stop download
```
