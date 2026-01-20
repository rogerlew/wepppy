# WEPPcloud Worker Deployment Guide (Prod)
> Deploy and operate a dedicated RQ worker pool for WEPPcloud production.
> **See also:** `AGENTS.md` for repo-wide conventions.

## Scope
This guide covers deploying the worker-only stack (`rq-worker`, `rq-worker-batch`, and optional `weppcloudr`) on a separate host that connects to the main WEPPcloud Redis instance.

## Prerequisites
- Shared storage mounted on the worker node (same paths as the main host):
  - `/geodata` and `/geodata/wc1` (mapped to `/geodata` and `/wc1` in containers).
- Redis reachable on the private NIC of the main WEPPcloud host.
- Docker + Compose installed.
- `wctl` installed via `./wctl/install.sh`.

## Redis and UFW Setup
### 1) Redis auth
Set a password in the main host `docker/.env`:
```
REDIS_PASSWORD=<strong-password>
```

Ensure Redis is started with auth (already wired in `docker/docker-compose.prod.yml`).

### 2) UFW rules (on the Redis host)
Allow only the worker host to reach Redis:
```
ufw allow in on <private_iface> from <worker_ip> to any port 6379 proto tcp
ufw deny 6379/tcp
```

On the worker host (if outbound is locked down):
```
ufw allow out to <redis_ip> port 6379 proto tcp
```

## Environment Variables
### Required
- `RQ_REDIS_URL` (use DB 9):
  - Local stack: `redis://:<password>@redis:6379/9`
  - Remote worker: `redis://:<password>@<redis_private_ip>:6379/9`
- `REDIS_PASSWORD` (keep in `docker/.env` for reuse in other services)

### Optional
- `WEPPCLOUDR_CONTAINER` (defaults to `weppcloudr`)
- `RQ_WORKER_CPUSET` (defaults to `0-47` in worker compose)
- `WEPPCLOUDR_CPUSET` (defaults to `0-47` in worker compose)
- `WEPPPY_NCPU`, `PERIDOT_CPU` (batch tuning)

## Install wctl for worker stack
```
./wctl/install.sh worker
```
This pins `docker/docker-compose.prod.worker.yml` for `wctl` commands.

## Bring up the worker stack
```
wctl up -d
```

To rebuild images:
```
wctl build --no-cache rq-worker rq-worker-batch weppcloudr
```

## WeppcloudR on workers
Some RQ jobs call `docker exec` against a local `weppcloudr` container. If you want those jobs to run on the worker host, keep `weppcloudr` in the worker compose and expose the Docker socket.

If you do not want `weppcloudr` on the worker host, keep `default` workers on the main WEPPcloud host and run only `batch` workers remotely.

## CPU Pinning
Use these environment variables to control CPU ranges without editing compose:
- `RQ_WORKER_CPUSET=0-47`
- `WEPPCLOUDR_CPUSET=0-47`

Example:
```
RQ_WORKER_CPUSET=0-47 WEPPCLOUDR_CPUSET=0-47 wctl up -d
```

## Validation
### Check worker visibility
```
wctl rq-info
```
You should see worker entries for both the main host and the worker node.

### Validate Redis auth
Inside the worker host:
```
redis-cli -h <redis_ip> -a <password> -n 9 ping
```

## Troubleshooting
### Workers show "Authentication required"
- Confirm `RQ_REDIS_URL` includes `:<password>@`.
- Confirm `REDIS_PASSWORD` matches the Redis host value.
- Restart workers after changing env vars.

### Workers appear idle while local host is busy
RQ is pull-based; lower latency or more local processes can bias job pickup. Options:
- Reduce local worker count.
- Route heavy jobs to a dedicated queue and run that queue only on the worker host.

### weppcloudr job failures
- Ensure `weppcloudr` is running on the same host as the worker that picked the job.
- Confirm Docker socket is mounted and `WEPPCLOUDR_CONTAINER` matches the container name.

### Redis unreachable from worker
- Verify UFW rules and private NIC routing.
- Validate Redis is bound to the private interface.
- Use `redis-cli` from the worker host to confirm connectivity.

## Common Commands
- Tail logs: `wctl logs -f rq-worker`
- Stop stack: `wctl down`
- Inspect compose: `wctl docker compose config`
