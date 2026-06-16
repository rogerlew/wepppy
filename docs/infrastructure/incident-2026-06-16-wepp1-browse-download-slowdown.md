# Incident Report: wepp1 Browse Download Slowdown
> Date: June 16, 2026 (America/Los_Angeles)  
> Scope: WEPPcloud archive/file downloads through `browse` on `wepp1`  
> Status: mitigated with targeted `browse` restart; root cause not fully proven

## Summary
A user reported that archived WEPPcloud simulation downloads had become extremely slow, with an approximately 400 MB archive taking several hours where similar files previously downloaded in minutes.

Investigation on `wepp1` found no host-wide CPU, memory, RQ, disk, or public-network saturation at the time of inspection. The concrete server-side fault was isolated to the `browse` service, which serves `/weppcloud/runs/.../download/...` and archive dashboard download links. `browse` had repeated worker timeouts, slow directory listing warnings, and two workers with abnormal resident memory near 45-49 GiB each.

A targeted restart of `browse` cleared the abnormal worker memory and restored a normal service baseline. This likely improved the server-side condition, but the exact user archive URL was not available, so the specific slow download path was not reproduced end to end.

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

## Assessment
Most likely contributors:

- `browse` worker memory growth or leaked request state.
- slow NFS metadata calls under browse/archive workloads.
- noisy crawler traffic or aborted clients increasing browse worker pressure.

Less likely based on current evidence:

- whole-host CPU saturation.
- whole-host public network saturation.
- RQ backlog.
- Postgres or Redis outage.
- Caddy/TLS as the primary bottleneck.

Not proven:

- the exact slow archive path that affected the user.
- WSU firewall/content-inspection behavior.
- a single NAS fault versus application-level metadata amplification.

## Follow-up Actions
1. Ask the user for one exact slow download URL, approximate timestamp, and whether they were on the WSU network or VPN.
2. Add or enable access timing for successful `browse` downloads, at least for archive ZIPs:
   - runid/config/subpath
   - file size
   - response duration
   - client IP / forwarded IP
   - status and disconnect/abort reason
3. Add lightweight `browse` worker RSS monitoring and alert when a worker exceeds a practical threshold, for example 4 GiB.
4. Investigate why `browse` workers can retain tens of GiB and hundreds of threads.
5. Consider reducing metadata amplification for archive listings:
   - cache archive list metadata briefly
   - avoid opening ZIP comments during every archive list request when not needed
   - avoid recursive or child-count metadata calls in high-latency NFS paths
6. Consider Caddy/user-agent controls during crawler pressure events if incomplete-response warnings continue.
7. Re-run an exact archive-path throughput test when a user provides the affected URL.

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
