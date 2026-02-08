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

### Run Storage / NFS Lifecycle
| Mechanism | Location | Current behavior | Tuning/Follow-up |
| --- | --- | --- | --- |
| TTL metadata (`wd/TTL`) | `wepppy/weppcloud/utils/run_ttl.py` | Rolling policy + disable/exclude states | Adjust TTL policy/schedule only with retention requirements. |
| GC scheduler | `docker/scheduled-tasks.yml`, scheduler sidecar | Daily logical-to-physical cleanup | Tune limits/jitter as run volume grows. |
| NFS deletion fallback | Follow-up in TTL package | Rename-to-trash deferred | Implement only if `EBUSY`/delete tail risk becomes operationally significant. |

### NFS Mount Profiles (wepp1 Candidate Set)
As of February 8, 2026, the following mount profiles are tracked for `nas.rocket.net:/wepp -> /geodata`:

| Profile | Mount line | Status/Intent |
| --- | --- | --- |
| Legacy NFSv3 soft mount | `#nas.rocket.net:/wepp /geodata nfs rw,bg,soft,nointr,rsize=32768,wsize=32768,tcp,vers=3,timeo=600,_netdev 0 0` | Historical baseline; commented out. |
| NFSv4.2 soft mount (32K IO) | `#nas.rocket.net:/wepp /geodata nfs4 rw,noatime,proto=tcp,vers=4.2,soft,rsize=32768,wsize=32768,timeo=600,_netdev 0 0` | Prior candidate; commented out. |
| NFSv4.2 hard mount with `actimeo=0` | `#nas.rocket.net:/wepp /geodata nfs4 rw,noatime,proto=tcp,vers=4.2,hard,intr,actimeo=0,_netdev 0 0` | Prior low-cache candidate; commented out. |
| NFSv4.2 hard mount with directory-cache bias | `nas.rocket.net:/wepp /geodata nfs4 rw,noatime,proto=tcp,vers=4.2,hard,intr,acregmin=3,acregmax=30,acdirmin=0,acdirmax=0,rsize=65536,wsize=65536,_netdev` | Active uncommented target, pending restart to take effect. |

Operational note:
- After restart, verify effective options with `findmnt -no SOURCE,TARGET,FSTYPE,OPTIONS /geodata` and record results in this knowledgebase.

## Failure-Signature Map
| Observed signature | Likely layer | High-probability cause | First checks |
| --- | --- | --- | --- |
| Caddy `status=502`, `msg=\"EOF\"` on `/rq-engine/create/` with ~37-61s durations | `rq-engine` workers | Upstream worker death during blocking request path | Correlate Caddy timestamps with `docker-rq-engine` `Child process [...] died` lines; verify deployed `project_routes.py` version. |
| Caddy `dial tcp ...:8042: connect: connection refused` | `rq-engine` availability | Service restart window or crash-loop | `docker ps`, recent container restart reason, parent/child start logs. |
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

## Drift Controls
- Before incident analysis, capture:
  - Host git SHA (`git rev-parse --short HEAD` in `/workdir/wepppy`).
  - Live container commands (`docker inspect ... .Config.Cmd`).
  - Active Caddyfile from container (`/etc/caddy/Caddyfile`), not only repo file.
- If runtime drift is found, treat repository expectations as hypotheses until host sync is complete.
