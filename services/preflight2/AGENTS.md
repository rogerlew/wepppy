# preflight2 Service Guide

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Purpose
`preflight2` streams run “preflight” validation results (checklist payloads) to browsers via WebSockets. Clients subscribe to `/weppcloud-microservices/preflight/<runid>` and receive realtime status updates sourced from Redis keyspace notifications.

## Core Dependencies
- **Redis:** Backing store and Pub/Sub (`redis://redis:6379/0` by default). Startup now retries with bounded exponential backoff so brief Redis outages no longer crash the container.
- **Keyspace notifications:** Docker Compose enables `--notify-keyspace-events Kh` on Redis; the service listens to those channels.
- **Reverse proxy:** Caddy routes external clients to container port `9001`.

## Configuration
All environment variables use the `PREFLIGHT_` prefix:
- `PREFLIGHT_REDIS_URL` – credential-free Redis endpoint including TLS options if required (resolves the mounted password separately).
  - Falls back to `REDIS_URL` + `REDIS_PASSWORD` (or `REDIS_HOST`/`REDIS_PORT`) when unset.
- `PREFLIGHT_LISTEN_ADDR` – bind address (default `:9001`).
- `PREFLIGHT_PING_INTERVAL`, `PREFLIGHT_PONG_TIMEOUT` – WebSocket heartbeat intervals.
- `PREFLIGHT_ALLOWED_ORIGINS` – required comma-separated exact external origins; empty fails startup.
- `PREFLIGHT_REDIS_RETRY_BASE`, `PREFLIGHT_REDIS_RETRY_MAX`, `PREFLIGHT_REDIS_MAX_RETRIES` – control retry cadence. Set `PREFLIGHT_REDIS_MAX_RETRIES=0` for infinite retries.
- `PREFLIGHT_METRICS_ENABLED=true` – expose Prometheus metrics at `/metrics`.

## Local Development
1. Build: `docker compose build preflight`.
2. Run with dependencies: `docker compose up preflight redis caddy`.
3. Confirm readiness at `http://localhost:9001/health` and collect metrics from `/metrics`.
4. Simulate an update:
   ```bash
   docker compose exec redis redis-cli \
     -n 0 hset my-run checklist '{"status":"ok"}'
   docker compose exec redis redis-cli \
     -n 0 publish __keyspace@0__:my-run set
   ```
   A connected WebSocket client should receive the updated checklist payload.

## Testing
- **Unit**: `wctl run-preflight-tests` (runs `go test ./...` inside the Go builder).
- **Integration**: `wctl run-preflight-tests -tags=integration ./internal/server` exercises the miniredis-backed pub/sub harness.
- **Plan**: `docs/testing-strategy-and-implementation-plan.md` tracks phases, tooling expectations, and open tasks.

## Operational Tips
- On startup failures, inspect `docker compose logs preflight` for retry warnings. Misconfiguration (bad URL, auth failure) exits immediately; networking errors trigger the retry loop.
- Combined with the Redis healthcheck in `docker-compose`, the container won’t start until Redis is actually ready. After Redis maintenance, the service will reconnect automatically.
- Monitor connection and message counters exported via Prometheus to spot performance regressions.

## Troubleshooting
- **Clients see 502s / reconnect loops:** Ensure the container is running and `docker compose ps preflight` reports “healthy”. Review Caddy logs for upstream errors.
- **No checklist updates:** Check that Redis keyspace notifications remain enabled and that the run ID matches the regex `^[A-Za-z0-9_-]+$`.
- **High latency:** The worker uses a single goroutine per websocket; if latency rises with load, consider vertical scaling or sharding readers across Redis channels.

## Browser stream authorization

Use the [canonical contract](../../docs/schemas/weppcloud-websocket-auth-contract.md).
`WEPP_AUTH_JWT_SECRETS_FILE` must mount the shared signing key ring. The owned
`services/streamauth` module validates every upgrade before run-specific Redis
access. Browser clients mint through the same-origin cookie bridge and use the
fixed plus bearer subprotocol pair. Keep proxy header filtering and static error
logs intact; credentials must never enter retained diagnostics. Expiry is 4001,
without terminal hangup. Health probes remain unauthenticated.

Redis credential resolution and legacy conflicts follow the
[transport contract](../../docs/schemas/redis-credential-transport-contract.md).
Endpoints never contain credentials; client options use a non-printing provider.
