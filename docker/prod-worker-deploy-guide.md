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
The main host Redis password is configured via the secret file:
- `docker/secrets/redis_password` (mounted to `/run/secrets/redis_password`)

Ensure Redis is started with auth (wired in `docker/docker-compose.prod.yml`) and that the worker host has the **same** password value in its own `docker/secrets/redis_password` file.

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
- `RQ_REDIS_URL` (use DB 9; **do not** embed passwords in the URL):
  - Local stack (only if Redis is on the same compose network): `redis://redis:6379/9`
  - Remote worker: `redis://<redis_private_ip>:6379/9`

### Required secret files
- `docker/secrets/redis_password`
- `DISCORD_BOT_TOKEN_FILE` should point to a token file (for example `docker/secrets/discord_bot_token`) when Discord notifications are enabled.
  - If `DISCORD_BOT_TOKEN_FILE` is unset, the worker compose defaults to `/dev/null` so worker startup does not fail on missing `.bot_token`.

### Optional
- `WEPPCLOUDR_CONTAINER` (defaults to `weppcloudr`)
- `RQ_WORKER_CPUSET` (defaults to `0-47` in worker compose)
- `WEPPCLOUDR_CPUSET` (defaults to `0-47` in worker compose)
- `WEPPPY_NCPU`, `PERIDOT_CPU` (batch tuning)
  - Provider API keys if the worker runs tasks that call those services:
    - `docker/secrets/opentopography_api_key`
    - `docker/secrets/climate_engine_api_key`

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

Important:
- `rq-info` shows RQ worker `hostname` values, which are typically Docker container IDs (for example `9a0f1116bfe1`), not host FQDNs like `wepp2.tail305ec9.ts.net`.
- To map a reported hostname/container id back to the host:
  - On each host, run `docker ps --format '{{.ID}} {{.Names}}'`.
  - Match the ID prefix from `rq-info` to the container list.

### Validate Redis auth
Inside the worker host:
```
redis-cli -h <redis_ip> -a "$(cat docker/secrets/redis_password)" -n 9 ping
```

## Troubleshooting
### Workers show "Authentication required"
- Confirm `docker/secrets/redis_password` matches the Redis host value.
- Confirm the worker containers have `/run/secrets/redis_password` mounted (Compose `secrets:`).
- Restart workers after changing secret files (Compose secrets are file-backed but workers only read at startup).

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

### Worker host missing from `wepp1 wctl rq-info`
Use this checklist when workers do not appear in `wepp1` `rq-info` output:
1. On the worker host, verify compose env and token path:
   - `grep -nE '^(RQ_REDIS_URL|DISCORD_BOT_TOKEN_FILE)=' docker/.env`
2. Verify required files exist and are readable:
   - `ls -l docker/secrets/redis_password docker/secrets/discord_bot_token`
3. Recreate worker services:
   - `wctl up -d --force-recreate rq-worker rq-worker-batch`
4. Confirm no restart loop:
   - `wctl docker compose ps rq-worker rq-worker-batch`
   - `wctl logs --tail 100 rq-worker rq-worker-batch`
5. Re-check registration:
   - On worker host: `wctl rq-info`
   - On wepp1 host: `wctl rq-info`

## Common Commands
- Tail logs: `wctl logs -f rq-worker`
- Stop stack: `wctl down`
- Inspect compose: `wctl docker compose config`
