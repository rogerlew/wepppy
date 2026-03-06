# Deployment And Tuning Knowledgebase
> Consolidated deployment behavior, tuning levers, and incident signatures for WEPPcloud operators.

## Usage Model
1. Confirm the active runtime on the target host (image, command, mounted Caddyfile, git SHA).
2. Match observed symptoms to the failure-signature table.
3. Apply the smallest viable tuning change in the appropriate layer.
4. Re-run the verification checklist and record results in a package or runbook.

## Runtime Baseline (Repository Current State)
Source-of-truth files: `docker/docker-compose.prod.yml`, `docker/caddy/Caddyfile`.

- `rq-engine` proxy path: `handle_path /rq-engine*` with:
  - `read_timeout 10m`
  - `response_header_timeout 10m`
- `rq-engine` service command in prod compose:
  - `uvicorn wepppy.microservices.rq_engine:app --workers 4 --host 0.0.0.0 --port 8042`
- `weppcloud` service command in prod compose:
  - `gunicorn --workers 4 --threads 2 --timeout 1800 ...`
- Current Caddyfile has no `/upload*` route block; upload routing was consolidated into `/rq-engine/api/*` in the migration series.

Operational note:
- Hosts can drift from repository state. Always verify live container command lines before attributing timeout behavior.

## Package Synthesis (Deployment/Infra/Tuning)
Reviewed mini-work-packages and work-packages with deployment-impacting outcomes:

| Source | Type | Key Carry-Forward |
| --- | --- | --- |
| [`docs/mini-work-packages/completed/20251223_upload_blueprint_timeouts.md`](../mini-work-packages/completed/20251223_upload_blueprint_timeouts.md) | Historical | Introduced `/upload*` long-timeout proxy path (20m) as an intermediate mitigation. |
| [`docs/mini-work-packages/completed/20251223_rq_engine_jobinfo_routes.md`](../mini-work-packages/completed/20251223_rq_engine_jobinfo_routes.md) | Foundational | Added `rq-engine` service and Caddy `/rq-engine*` routing; established polling offload pattern. |
| [`docs/mini-work-packages/completed/20260112_rq_api_migration.md`](../mini-work-packages/completed/20260112_rq_api_migration.md) | Canonical | Migrated run-scoped queue/upload traffic to `/rq-engine/api/*`; removed legacy `/rq/api/*` and `/upload/*` in dev flow. |
| [`docs/mini-work-packages/completed/20260112_rq_api_migration.pre-removal-review.md`](../mini-work-packages/completed/20260112_rq_api_migration.pre-removal-review.md) | Validation | Confirmed parity and proxy posture before legacy removal. |
| [`docs/mini-work-packages/completed/20260112_rq_api_migration.review.md`](../mini-work-packages/completed/20260112_rq_api_migration.review.md) | Validation | Post-migration review confirmed runtime callers removed `/rq/api` and `/upload` dependencies. |
| [`docs/mini-work-packages/completed/20260112_rq-engine-jwt-implementation.md`](../mini-work-packages/completed/20260112_rq-engine-jwt-implementation.md) | Access control foundation | Established rq-engine JWT/session token path needed for safe service-side routing and remote clients. |
| [`docs/mini-work-packages/completed/20260115_rq-engine-migrate-run.md`](../mini-work-packages/completed/20260115_rq-engine-migrate-run.md) | Route migration | Moved migration enqueue/polling into rq-engine canonical paths, reducing Flask route surface and split behavior. |
| [`docs/mini-work-packages/completed/20260119_rq_engine_export_routes.md`](../mini-work-packages/completed/20260119_rq_engine_export_routes.md) | Long-running request handling | Moved export endpoints to rq-engine and documented threadpool execution to keep the event loop responsive. |
| [`docs/mini-work-packages/completed/20260120_weppcloud_idle_tx_fd_leak.md`](../mini-work-packages/completed/20260120_weppcloud_idle_tx_fd_leak.md) | Performance hardening | Detached NoDb loading and query/session closure materially reduced FD growth and idle-in-transaction persistence. |
| [`docs/mini-work-packages/completed/20260203_resource_contraints.md`](../mini-work-packages/completed/20260203_resource_contraints.md) | Capacity protection | Captured crawler-induced 502 patterns and Caddy bot-blocklist/rate-limit recommendations. |
| [`docs/mini-work-packages/completed/20260206_run_ttl_lifecycle.md`](../mini-work-packages/completed/20260206_run_ttl_lifecycle.md) | Storage lifecycle | Added TTL metadata + GC scheduler; logical delete first, deferred physical cleanup on NFS. |
| [`docs/work-packages/20260208_rq_engine_agent_usability/tracker.md`](../work-packages/20260208_rq_engine_agent_usability/tracker.md) | Active work package | Documented polling auth/rate-limit decisions and deploy-readiness checklist items for rq-engine agent paths. |

Interpretation:
- For queue/upload pathing and timeout posture, treat the 2026-01 migration artifacts as current.
- Treat 2025-12 `/upload` timeout guidance as historical context unless a host explicitly still runs that config.
- This synthesis includes packages that changed runtime topology, request routing, timeout/concurrency behavior, capacity posture, or run-storage lifecycle. UI-only and schema-only packages are intentionally excluded.

## Tuning Levers By Layer
### Caddy / Reverse Proxy
| Knob | Location | Default in repo | When to tune |
| --- | --- | --- | --- |
| `read_timeout`, `response_header_timeout` for `/rq-engine*` | `docker/caddy/Caddyfile` | `10m`, `10m` | Only if validated long-running upstream responses exceed current envelope. |
| Bot blocks / crawler controls | `docker/caddy/Caddyfile` | Not globally enabled by default | During crawler pressure events causing browse/download 502 spikes. |
| Route ordering | `docker/caddy/Caddyfile` | Explicit `handle_path` blocks above app fallback | If requests unexpectedly land on wrong upstream service. |

### App Server / Worker Runtime
| Knob | Location | Default in repo | When to tune |
| --- | --- | --- | --- |
| Uvicorn worker count (`rq-engine`) | `docker/docker-compose.prod.yml` | `--workers 4` | CPU saturation or queue API tail-latency pressure. |
| Gunicorn workers/threads (`weppcloud`) | `docker/docker-compose.prod.yml` | `workers=4`, `threads=2`, `timeout=1800` | Request concurrency imbalance, worker stalls, or memory pressure. |
| Polling limiter strategy | rq-engine package decisions | In-process limiter retained | Revisit for cross-worker/global enforcement after deployment telemetry supports it. |

### Database + Session Safety
| Knob | Location | Status | When to tune |
| --- | --- | --- | --- |
| `POSTGRES_IDLE_IN_TX_TIMEOUT` | `wepppy/weppcloud/configuration.py` | Available, historically caution-flagged | If idle-in-transaction reappears; validate OAuth/CAP flows after enabling. |
| `SECRET_KEY` / `SECURITY_PASSWORD_SALT` raw-value parity | `docker/.env` + live container env (`docker inspect`) | Required invariant | Any login/session-cookie failures, especially rq-engine `session-token` 401s. |

Auth secret invariant:
- `weppcloud` and `rq-engine` must run with identical raw `SECRET_KEY` and
  `SECURITY_PASSWORD_SALT` values.
- Do not alter literal single `$` characters inside existing secret values.
- Post-deploy check:

```bash
for c in docker-weppcloud-1 docker-rq-engine-1; do
  s=$(docker inspect "$c" --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^SECRET_KEY=//p')
  printf '%s len=%s sha16=%s\n' "$c" "${#s}" "$(printf %s "$s" | sha256sum | cut -c1-16)"
done
```

Expected: identical length/hash across both containers.

### Run Storage / NFS Lifecycle
| Mechanism | Location | Current behavior | Tuning/Follow-up |
| --- | --- | --- | --- |
| TTL metadata (`wd/TTL`) | `wepppy/weppcloud/utils/run_ttl.py` | Rolling policy + disable/exclude states | Adjust TTL policy/schedule only with retention requirements. |
| GC scheduler | `docker/scheduled-tasks.yml`, scheduler sidecar | Daily logical-to-physical cleanup | Tune limits/jitter as run volume grows. |
| NFS deletion fallback | Follow-up in TTL package | Rename-to-trash deferred | Implement only if `EBUSY`/delete tail risk becomes operationally significant. |

### NFS Mount Profiles (wepp1 Candidate Set)
As of February 9, 2026, the following mount profiles are tracked for `nas.rocket.net:/wepp -> /geodata`:

| Profile | Mount line | Status/Intent |
| --- | --- | --- |
| Legacy NFSv3 soft mount | `#nas.rocket.net:/wepp /geodata nfs rw,bg,soft,nointr,rsize=32768,wsize=32768,tcp,vers=3,timeo=600,_netdev 0 0` | Historical baseline; commented out. |
| NFSv4.2 soft mount (32K IO) | `#nas.rocket.net:/wepp /geodata nfs4 rw,noatime,proto=tcp,vers=4.2,soft,rsize=32768,wsize=32768,timeo=600,_netdev 0 0` | Prior candidate; commented out. |
| NFSv4.2 hard mount with `actimeo=0` | `#nas.rocket.net:/wepp /geodata nfs4 rw,noatime,proto=tcp,vers=4.2,hard,intr,actimeo=0,_netdev 0 0` | Prior low-cache candidate; commented out. |
| NFSv4.2 hard mount with zero directory cache (debug only) | `#nas.rocket.net:/wepp /geodata nfs4 rw,noatime,proto=tcp,vers=4.2,hard,acregmin=3,acregmax=30,acdirmin=0,acdirmax=0,rsize=65536,wsize=65536,_netdev 0 0` | Keep commented out unless explicitly debugging stale-directory visibility. |
| NFSv4.2 hard mount with metadata cache (recommended) | `nas.rocket.net:/wepp /geodata nfs4 rw,noatime,proto=tcp,vers=4.2,hard,timeo=600,retrans=2,rsize=65536,wsize=65536,acregmin=3,acregmax=30,acdirmin=5,acdirmax=60,_netdev,x-systemd.automount,nofail 0 0` | Recommended baseline for `wepp1` run browsing and NoDb-heavy route loads. |

Operational notes:
- `intr` is intentionally omitted in recommended NFSv4 profiles; modern Linux NFS clients ignore it.
- Current degraded profile observed on `wepp1` during incident: `acdirmin=0,acdirmax=0` with `hard` mount semantics.

#### Metadata And Latency Statistics (February 9, 2026)
Benchmark comparison used:
- Degraded host/run: `https://wepp.cloud/weppcloud/runs/olive-colored-bluestone/disturbed9002_wbt`
- Comparator host/run: `https://wc.bearhive.duckdns.org/weppcloud/runs/preliminary-moussaka/wepp-swat-wbt/`

| Benchmark | `wepp1` (`wepp.cloud` + olive run) | `wc.bearhive.duckdns.org` + preliminary run | Relative slowdown |
| --- | --- | --- | --- |
| External HTTPS run-page TTFB, `curl` `time_starttransfer` (`n=30`) | mean `639.0 ms`, p50 `550.9 ms`, p95 `1045.6 ms` | mean `15.4 ms`, p50 `15.2 ms`, p95 `16.5 ms` | `41.5x` (mean) |
| Local Gunicorn run route TTFB (`http://127.0.0.1:8000/runs/.../`, `n=30`) | mean `584.0 ms`, p50 `520.9 ms`, p95 `942.7 ms` | mean `6.0 ms`, p50 `5.7 ms`, p95 `7.5 ms` | `97.3x` (mean) |
| `get_wd(runid, prefer_active=False)` in `weppcloud` container (`n=50`) | mean `8.793 ms`, p50 `8.095 ms`, p95 `15.076 ms` | mean `0.167 ms`, p50 `0.157 ms`, p95 `0.183 ms` | `52.7x` (mean) |
| `os.stat(run_dir)` in `weppcloud` container (`n=50`) | mean `8.552 ms`, p50 `8.562 ms`, p95 `15.615 ms` | mean `0.006 ms`, p50 `0.006 ms`, p95 `0.006 ms` | `1425x` (mean) |
| `len(os.listdir(run_dir))` in `weppcloud` container (`n=50`) | mean `13.318 ms`, p50 `8.951 ms`, p95 `27.799 ms` | mean `0.237 ms`, p50 `0.217 ms`, p95 `0.310 ms` | `56.2x` (mean) |
| NFSv4 per-request `GETATTR` delta on one run-page request (`n=8`) | mean `861.6`, range `691-1090` | `0` for measured comparator route | Not comparable; strong metadata amplification on degraded path |

Interpretation:
- The majority of run-page delay on `wepp1` is server-side, not DNS/connect/TLS overhead.
- Directory metadata churn (`GETATTR`) dominates the degraded path and correlates with high TTFB variance.

#### wepp2 Validation (February 10, 2026)
`wepp2` had `/geodata` mounted with `acdirmin=0,acdirmax=0` and active WEPP binaries holding `/geodata` open, so we did a non-disruptive A/B mount:
- Leave the live mount intact (`/geodata`).
- Mount the same export a second time at `/mnt/geodata_test` with the recommended metadata cache options.

Result (run dir `wc1/runs/ol/olive-colored-bluestone`, metadata-only microbench):

| Benchmark | `wepp2` current `/geodata` (`acdirmin=0,acdirmax=0`) | `wepp2` test mount `/mnt/geodata_test` (`acdirmin=5,acdirmax=60`) | Relative slowdown |
| --- | --- | --- | --- |
| `stat(run_dir)` (`n=20`) | mean `19.138 ms`, p50 `19.397 ms`, p95 `27.210 ms` | mean `0.006 ms`, p50 `0.005 ms`, p95 `0.006 ms` | `~3189x` (mean) |
| `len(os.listdir(run_dir))` (`n=10`) | mean `35.852 ms`, p50 `35.429 ms`, p95 `41.352 ms` | mean `5.619 ms`, p50 `2.463 ms`, p95 `5.000 ms` | `~6.4x` (mean) |

#### Reproducible Benchmark Procedure
Run from a host that can reach both sites and can SSH to `wepp1` over Tailscale.

1. Record effective mount options (host + container view).

```bash
# On wepp1 host
findmnt -T /geodata -o TARGET,SOURCE,FSTYPE,OPTIONS
nfsstat -m

# In weppcloud container (container may see /wc1 rather than /geodata)
c=$(docker ps --format '{{.Names}}' | grep -E 'weppcloud' | head -n1)
docker exec "$c" sh -lc "stat -f -c 'path=%n fstype=%T' /wc1 /wc1/runs; mount | grep -E ' /wc1 | /geodata '"
```

2. Measure external run-page phase timings (`DNS`, `connect`, `TLS`, `TTFB`, `total`).

```bash
python3 - <<'PY'
import subprocess, statistics
urls = [
    "https://wepp.cloud/weppcloud/runs/olive-colored-bluestone/disturbed9002_wbt",
    "https://wc.bearhive.duckdns.org/weppcloud/runs/preliminary-moussaka/wepp-swat-wbt/",
]
fields = ["time_namelookup","time_connect","time_appconnect","time_starttransfer","time_total"]
for url in urls:
    rows = []
    for _ in range(30):
        out = subprocess.check_output(
            ["curl","-k","-sS","-L","-o","/dev/null","-w",";".join([f"%{{{f}}}" for f in fields]),url],
            text=True,
        ).strip()
        rows.append([float(v) * 1000 for v in out.split(";")])
    print(url)
    for idx, f in enumerate(fields):
        col = sorted(r[idx] for r in rows)
        print(f"  {f}: mean_ms={statistics.mean(col):.1f} p50_ms={statistics.median(col):.1f} p95_ms={col[int(0.95*(len(col)-1))]:.1f}")
PY
```

3. Measure local app-only route TTFB on each host (bypasses internet and TLS).

```bash
# Example on wepp1 (run a matching command on comparator host with its run URL)
python3 - <<'PY'
import subprocess, statistics
url = "http://127.0.0.1:8000/runs/olive-colored-bluestone/disturbed9002_wbt/"
vals = []
for _ in range(30):
    t = subprocess.check_output(["curl","-sS","-o","/dev/null","-w","%{time_starttransfer}",url], text=True).strip()
    vals.append(float(t) * 1000)
vals = sorted(vals)
print(url)
print(f"mean_ms={statistics.mean(vals):.1f} p50_ms={statistics.median(vals):.1f} p95_ms={vals[int(0.95*(len(vals)-1))]:.1f} min_ms={vals[0]:.1f} max_ms={vals[-1]:.1f}")
PY
```

4. Measure metadata-sensitive helpers inside `weppcloud` container.

```bash
c=$(docker ps --format '{{.Names}}' | grep -E 'weppcloud' | head -n1)
docker exec -i "$c" python - <<'PY'
import os, time, statistics
from wepppy.weppcloud.utils.helpers import get_wd
runid = "olive-colored-bluestone"  # swap for comparator run
N = 50
path = get_wd(runid, prefer_active=False)
def bench(label, fn):
    vals = []
    for _ in range(N):
        t0 = time.perf_counter()
        fn()
        vals.append((time.perf_counter() - t0) * 1000)
    vals.sort()
    print(f"{label}: mean_ms={statistics.mean(vals):.3f} p50_ms={statistics.median(vals):.3f} p95_ms={vals[int(0.95*(N-1))]:.3f} max_ms={vals[-1]:.3f}")
print("path", path)
bench("get_wd", lambda: get_wd(runid, prefer_active=False))
bench("exists", lambda: os.path.exists(path))
bench("stat", lambda: os.stat(path))
bench("listdir_len", lambda: len(os.listdir(path)))
PY
```

5. Quantify per-request NFS metadata amplification using `/proc/net/rpc/nfs`.

```bash
python3 - <<'PY'
import subprocess
def read_proc4():
    line = subprocess.check_output(["bash","-lc","grep '^proc4 ' /proc/net/rpc/nfs"], text=True).strip().split()
    n = int(line[1])
    return list(map(int, line[2:2+n]))
URL = "http://127.0.0.1:8000/runs/olive-colored-bluestone/disturbed9002_wbt/"
b = read_proc4()
ttfb = float(subprocess.check_output(["curl","-sS","-o","/dev/null","-w","%{time_starttransfer}",URL], text=True).strip()) * 1000
a = read_proc4()
delta = [a[i] - b[i] for i in range(len(a))]
print(f"ttfb_ms={ttfb:.1f} getattr={delta[18]} lookup={delta[19]} read={delta[1]} readdir={delta[29]} open_noat={delta[6]} close={delta[8]}")
PY
```

6. (Optional) Non-disruptive mount A/B to validate metadata caching on a busy host.

This mounts the same export a second time at `/mnt/geodata_test` without touching the live `/geodata` mount.

```bash
run_rel='wc1/runs/ol/olive-colored-bluestone'
opts=$(findmnt -T /geodata -n -o OPTIONS)
addr=$(echo "$opts" | sed -n 's/.*addr=\([^,]*\).*/\1/p')
remote="${addr}:/wepp"

docker run --rm --privileged --pid=host alpine:3.20 sh -lc "\
  apk add --no-cache util-linux >/dev/null && \
  nsenter -t 1 -m -n -- chroot /proc/1/root mkdir -p /mnt/geodata_test && \
  nsenter -t 1 -m -n -- chroot /proc/1/root mount -t nfs4 -o rw,noatime,proto=tcp,vers=4.2,hard,timeo=600,retrans=2,rsize=65536,wsize=65536,acregmin=3,acregmax=30,acdirmin=5,acdirmax=60 \"$remote\" /mnt/geodata_test && \
  nsenter -t 1 -m -n -- chroot /proc/1/root findmnt -T /mnt/geodata_test -o TARGET,SOURCE,FSTYPE,OPTIONS"

python3 - <<PY
import os, time, statistics
run_rel = "${run_rel}"
paths = {"current": "/geodata/" + run_rel, "test": "/mnt/geodata_test/" + run_rel}
def bench(fn, n):
    vals=[]
    for _ in range(n):
        t0=time.perf_counter(); fn(); vals.append((time.perf_counter()-t0)*1000)
    vals.sort()
    return {"mean": statistics.mean(vals), "p50": statistics.median(vals), "p95": vals[int(0.95*(n-1))]}
for name,p in paths.items():
    s=bench(lambda: os.stat(p), 20)
    l=bench(lambda: len(os.listdir(p)), 10)
    print(name, p)
    print(f"  stat mean_ms={s['mean']:.3f} p50_ms={s['p50']:.3f} p95_ms={s['p95']:.3f}")
    print(f"  listdir mean_ms={l['mean']:.3f} p50_ms={l['p50']:.3f} p95_ms={l['p95']:.3f}")
PY

docker run --rm --privileged --pid=host alpine:3.20 sh -lc "\
  apk add --no-cache util-linux >/dev/null && \
  nsenter -t 1 -m -n -- chroot /proc/1/root umount /mnt/geodata_test && \
  nsenter -t 1 -m -n -- chroot /proc/1/root rmdir /mnt/geodata_test || true"
```

7. After mount changes, rerun steps 1-5 and append before/after results to this section.

## Failure-Signature Map
| Observed signature | Likely layer | High-probability cause | First checks |
| --- | --- | --- | --- |
| Caddy `status=502`, `msg=\"EOF\"` on `/rq-engine/create/` with ~37-61s durations | `rq-engine` workers | Upstream worker death during blocking request path | Correlate Caddy timestamps with `docker-rq-engine` `Child process [...] died` lines; verify deployed `project_routes.py` version. |
| Caddy `dial tcp ...:8042: connect: connection refused` | `rq-engine` availability | Service restart window or crash-loop | `docker ps`, recent container restart reason, parent/child start logs. |
| `POST /rq-engine/api/runs/<runid>/<config>/session-token` returns `401 Invalid session cookie` while Redis session key exists | Auth/session boundary | `SECRET_KEY` mismatch between `weppcloud` and `rq-engine` (often from secret-value drift around `$` characters) | Compare `SECRET_KEY` length/hash between containers via `docker inspect`; ensure both services were recreated from the same env values. |
| Rising `502` on browse/download with crawler user agents | Edge/capacity | Aggressive bot traffic | Apply user-agent blocks/rate controls from resource-constraints package; monitor status delta. |
| Many open log FDs per `weppcloud` worker + DB `idle in transaction` | App/DB | Non-detached NoDb loading on list/render paths, delayed session closure | Confirm detached-load code path and query closure behavior from 2026-01 hardening package. |

## Deployment Verification Checklist
Run on target host before and after any tuning/deploy change:

```bash
# 1) Runtime identity
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker inspect --format 'Cmd={{json .Config.Cmd}}' docker-rq-engine-1

# 2) Active proxy config
docker exec docker-caddy-1 sh -lc "nl -ba /etc/caddy/Caddyfile | sed -n '70,105p'"

# 3) Health and path checks
curl -fsS https://<host>/rq-engine/health
curl -fsS "https://<host>/rq-engine/api/jobstatus/<job_id>"

# 4) Error correlation
docker logs --since 2h docker-caddy-1 2>&1 | grep '/rq-engine'
docker logs --since 2h docker-rq-engine-1 2>&1 | grep -E 'Child process|POST /create/'
```

Release hygiene:
- Record deployed git SHA and compose file set used.
- Record whether host runtime matches repository worker/timeouts.
- Record one known-good `/rq-engine/create/` result and one `/api/jobstatus` polling sequence.

## WEPPcloud Hotfix Playbook (Minimal Disruption)
Use this when applying a small `weppcloud` fix (for example template/python hotfix) on a live host and you want to avoid full container restarts.

### 0) Scope + guardrails
- Prefer this flow for bounded fixes in existing files; do not use it for dependency/image changes.
- Keep blast radius small: patch one service, validate, then continue.
- Never assume host file updates are visible in the running container. Confirm in-container content explicitly.

### 1) Capture runtime identity first
```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep weppcloud
docker inspect --format 'Cmd={{json .Config.Cmd}} RestartCount={{.RestartCount}}' docker-weppcloud-1
```

### 2) Verify host vs container file content
```bash
# Host checkout file
sha256sum /workdir/wepppy/wepppy/weppcloud/templates/reports/ash/ash_watershed.htm

# Running container file (authoritative for hotfix effectiveness)
docker exec -i docker-weppcloud-1 sh -lc \
  'sha256sum /workdir/wepppy/wepppy/weppcloud/templates/reports/ash/ash_watershed.htm'
```

If checksums differ, patching only the host checkout is insufficient.

### 3) Stage + copy patch into the running container
```bash
# Stage on host (or copy via scp/cat pipeline from operator workstation)
cp /workdir/wepppy/wepppy/weppcloud/templates/reports/ash/ash_watershed.htm /tmp/ash_watershed.hotfix.htm

# Optional rollback snapshot from container before overwrite
docker cp docker-weppcloud-1:/workdir/wepppy/wepppy/weppcloud/templates/reports/ash/ash_watershed.htm \
  /tmp/ash_watershed.prehotfix.bak.htm

# Apply patch into container filesystem
docker cp /tmp/ash_watershed.hotfix.htm \
  docker-weppcloud-1:/workdir/wepppy/wepppy/weppcloud/templates/reports/ash/ash_watershed.htm

# Verify in-container content after copy
docker exec -i docker-weppcloud-1 sh -lc \
  'sha256sum /workdir/wepppy/wepppy/weppcloud/templates/reports/ash/ash_watershed.htm'
```

### 4) Graceful reload (no full restart)
```bash
# HUP Gunicorn master (PID 1 in container command layout)
docker exec docker-weppcloud-1 sh -lc 'kill -HUP 1'

# Confirm graceful worker rollover
docker logs --since 2m docker-weppcloud-1 2>&1 | grep -E 'Handling signal: hup|Booting worker|Worker exiting'

# Confirm container stayed up
docker ps --filter name=docker-weppcloud-1 --format '{{.Names}} {{.Status}}'
docker inspect --format 'RestartCount={{.RestartCount}}' docker-weppcloud-1
```

Expected:
- `Handling signal: hup`
- new worker `Booting worker` lines
- old worker `Worker exiting` lines
- no container restart count increase

### 5) Functional verification
```bash
# Service health
curl -fsS https://<host>/weppcloud/ >/dev/null
curl -fsS https://<host>/rq-engine/health >/dev/null

# Re-test the failing endpoint directly
curl -k -sS -o /tmp/hotfix_resp.txt -w 'code=%{http_code} ttfb=%{time_starttransfer} total=%{time_total}\n' \
  "https://<host>/weppcloud/runs/<runid>/<config>/report/ash/"
```

### 6) Rollback (if needed)
```bash
docker cp /tmp/ash_watershed.prehotfix.bak.htm \
  docker-weppcloud-1:/workdir/wepppy/wepppy/weppcloud/templates/reports/ash/ash_watershed.htm
docker exec docker-weppcloud-1 sh -lc 'kill -HUP 1'
```

### 7) Record incident notes
- Exact UTC timestamp of copy + reload.
- File path and checksum before/after (host and container).
- Endpoint tested and result (status + TTFB).
- Whether error signatures stopped (for example no new run-level `exception_factory.log` entries).

## Drift Controls
- Before incident analysis, capture:
  - Host git SHA (`git rev-parse --short HEAD` in `/workdir/wepppy`).
  - Live container commands (`docker inspect ... .Config.Cmd`).
  - Active Caddyfile from container (`/etc/caddy/Caddyfile`), not only repo file.
- If runtime drift is found, treat repository expectations as hypotheses until host sync is complete.
