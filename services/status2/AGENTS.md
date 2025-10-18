# status2 Service Guide

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Purpose
`status2` backs the `/weppcloud-microservices/status/<runid>:<channel>` WebSocket. It streams run-status updates from Redis Pub/Sub to browsers so the project dashboard stays reactive.

## Key Dependencies
- **Redis:** Pub/Sub feed (defaults to `redis://redis:6379/2`). The entrypoint now retries with exponential backoff until Redis responds, so brief outages will not drop the service.
- **Metrics:** Optional Prometheus metrics exposed at `/metrics` when `STATUS_METRICS_ENABLED=true`.
- **Reverse proxy:** Caddy forwards external traffic to the container on port `9002`.

## Runtime Configuration
Environment variables are prefixed with `STATUS_`. Common options:
- `STATUS_REDIS_URL` – connection string; supports TLS/password via Go-Redis URL syntax.
- `STATUS_LISTEN_ADDR` – bind address (default `:9002`).
- `STATUS_PING_INTERVAL`, `STATUS_PONG_TIMEOUT` – WebSocket heartbeat timings.
- `STATUS_REDIS_RETRY_BASE`, `STATUS_REDIS_RETRY_MAX`, `STATUS_REDIS_MAX_RETRIES` – control startup retry behaviour. Use `0` retries for infinite.
- `STATUS_ALLOWED_ORIGINS` – comma-separated list for strict Origin checks.

## Local Development
1. Build with `docker compose build status`.
2. Run the stack (`docker compose up status redis caddy`); Redis must be reachable for the server to leave the retry loop.
3. Hit `http://localhost:9002/health` for readiness and `/metrics` for Prometheus output.
4. To test manually, publish to `status` run channel:
   ```bash
   docker compose exec redis redis-cli \
     -n 2 publish accustomed-pewter:wepp '{"type":"progress","percent":10}'
   ```

## Operational Notes
- The container exits only on fatal misconfiguration (invalid Redis URL, auth failure). Network glitches trigger the retry loop and are logged as warnings.
- Caddy marks the backend unhealthy on connection errors. Confirm the container is up with `docker compose ps status`.
- Metrics include connection counts and message throughput; scrape them to watch for backlog issues.

## Troubleshooting
- **502 from Caddy:** Check `docker compose logs status` for retry messages; ensure the Redis healthcheck is passing.
- **No updates received:** Verify the run/token pair matches the channel pattern `runid:topic`. Redis keyspace events must be enabled (`--notify-keyspace-events Kh` in docker-compose).
- **High CPU/memory:** Inspect metrics and consider scaling websockets behind something like HAProxy if connections >5k.
