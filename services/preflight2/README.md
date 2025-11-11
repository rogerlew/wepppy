# Preflight2 Microservice Specification

> **See also:** [AGENTS.md](../../AGENTS.md) for Go Microservices section and High Performance Telemetry Pipeline overview.

Date: 2025-10-11  
Owner: Roger Lew
Developer: codex
Status: Approved

## 1. Context

The existing `microservices/preflight.py` Tornado application streams readiness
updates for a WEPP run by:

- Listening to Redis keyspace notifications on DB 0 (`RedisPrep` hash changes).
- Recomputing the preflight checklist from the run hash.
- Pushing JSON frames over a WebSocket (`{"type":"preflight", ...}`) to browsers.

While functional, the Python implementation battles chronic stability issues:
heartbeats stop firing, sockets get torn down prematurely, and reconnect storms
occupy browser/client resources. The root causes are a mix of Tornado’s
cooperative scheduling, shared pub/sub cursors, and brittle error handling when
Redis or the network hiccups.

## 2. Goals

Build `preflight2`, a from-scratch Go rewrite of the preflight microservice
with the following outcomes:

- Highly reliable WebSocket streaming under moderate fan-out (dozens of users,
  tens of concurrent runs).
- Deterministic per-connection processing — no shared async state between
  unrelated runs.
- Fast recovery from Redis outages or container restarts.
- Backwards compatible wire protocol so the existing `/static/js/preflight.js`
  can operate unchanged (or with opt-in enhancements).
- Operational transparency: structured logs, metrics, and health checks.

## 3. Non-Goals

- Replacing the browser client or RedisPrep schema.
- Changing the Docker/Caddy routing surface (still listens on port 9001 under
  `/weppcloud-microservices/preflight/`).
- Introducing new checklist semantics beyond what `RedisPrep` already provides.

## 4. Current Pain Points & Requirements Drivers

Pain points observed in `preflight.py`:

1. **Shared async listener** — one Redis pub/sub stream drives all clients;
   stalled writes on a slow socket block everyone.
2. **Heartbeat suppression** — Tornado drops the underlying `stream.socket`,
   causing `_ping()` to skip heartbeats and the client idles out.
3. **Process exits on recoverable errors** — Redis timeouts trigger `os._exit`.
4. **Keyspace fan-out** — we subscribe to the entire DB even though each socket
   only cares about a single run ID.
5. **Limited observability** — no metrics, coarse logging, difficult to inspect
   connection lifecycles.

These directly inform the Go design:

- Use dedicated goroutines per connection, each with its own pub/sub consumer.
- Never let one slow client block another.
- Implement strict heartbeat timers and proactive shutdown of stale sockets.
- Filter Redis notifications server-side to the single run hash.
- Provide metrics (Prometheus) and structured logs for debugging.

 ## 5. Functional Requirements

1. **WebSocket endpoint** at `/(<runid>)`:
   - Accepts the existing client handshake (`{"type":"init"}`).
   - Sends an initial payload containing `{"type":"preflight","checklist":{...},
     "lock_statuses":{...}}`.
   - Validates the `Origin` header against an allowlist (configurable) to reduce CSWSH risk.
   - Responds to `{"type":"pong"}` frames (and any other client activity), resetting per-connection idle timers.
2. **Heartbeat**:
   - Server-sent `{"type":"ping"}` at a configurable interval (default 30 s).
   - Drop connection if no `pong` for 2 intervals (default 60 s).
3. **Redis-driven updates**:
   - Maintain a copy of the target run hash in memory (updated on every
     notification).
   - Recompute checklist fields using the same logic as
     `wepppy.nodb.redis_prep.TaskEnum`.
   - Push updated JSON frames only when diffs occur.
4. **Lock surfaces**:
   - Translate `locked:<filename>` fields into the `lock_statuses` map.
5. **Health endpoints**:
   - `GET /health` returns `200 OK` when ready to serve.
   - Optional `GET /metrics` for Prometheus scraping.
6. **Graceful shutdown**:
   - Drain sockets with a `{"type":"hangup"}` frame before closing.
   - Unsubscribe from Redis and release resources.

## 6. Non-Functional Requirements

- Target Go ≥ 1.25 (current LTS as of Oct 2025).
- Sustain 200 concurrent sockets with <100 ms latency on checklist updates.
- Handle Redis restarts transparently (exponential backoff + replay latest
  hash) with bounded retry loops (default max 5 attempts before surfacing an error).
- Container image smaller than 50 MB (scratch or distroless base).
- Logs structured as JSON with RFC3339 timestamps via `log/slog` (stdlib).
- Configuration via environment variables (prefix `PREFLIGHT_`).

## 7. Domain Model & Data Flow

### 7.1 RedisPrep Schema Recap

- Run hash key: `<runid>` in DB 0.
- Timestamps are stored under fields `timestamps:<TaskEnum value>`.
- Boolean attributes under `attrs:<flag>`.
- Locks under `locked:<filename>`.
- Client requires the derived checklist booleans produced by the current
  `preflight()` function in Python.

### 7.2 Event Flow

```
Redis (DB 0) ──keyspace notification──▶ Connection goroutine ──▶ WebSocket client
              │                                                     ▲
              └─ HGETALL runid (with retries) ◀────── aggregator ───┘
```

Each connection owns:

1. A `redis.PubSub` subscription on `__keyspace@0__:<runid>`.
2. A goroutine reading pub/sub messages and pushing events into a channel.
3. A goroutine that manages the WebSocket (reads `pong`, writes `ping`/payloads).
4. A request-scoped context that cancels both goroutines on disconnect.

No shared state across run IDs beyond a Redis connection pool. All Redis work,
including `HGETALL`, must respect context deadlines (default 500 ms) to avoid
runaway calls during outages.

## 8. High-Level Architecture

### 8.1 Components

- **HTTP Server**: stdlib `net/http` with `http.ServeMux` (or `chi` if middleware
  pressure increases) serving:
  - `GET /health`
  - `GET /metrics` (optional, gated by config)
  - `GET /{runid}` upgraded to WebSocket (using `nhooyr.io/websocket` or
    another zero-allocation library; `nhooyr` preferred).
- **Connection Manager**:
  - Accepts new sockets, validates run IDs (`^[a-zA-Z0-9_-]+$`), and spawns a
    `Connection` struct.
  - Tracks metrics (connections open/closed, failures).
- **Redis Client Factory**:
  - `go-redis v9` with automatic retries, TLS support if URL demands.
  - Pooled connections; each connection creates its own `PubSub` instance.
- **Checklist Evaluator**:
  - Pure Go functions mirroring `preflight()` and `lock_statuses()`.
  - Unit tests using captured hashes from fixtures.
- **Update Diffing**:
  - Cache last sent checklist+locks; only emit when content changes.
- **Heartbeat Supervisor**:
  - `time.Ticker` for pings, `time.Timer` for idle deadline.
- **Error Propagation**:
  - All goroutines share a `context.Context`.
  - First failure (Redis, socket write, JSON marshal) cancels context and
    sends a hangup frame.
  - Goroutines wrap their bodies with panic recovery to log and terminate cleanly.

### 8.2 Configuration knobs

| Env Var | Default | Description |
|---------|---------|-------------|
| `PREFLIGHT_REDIS_URL` | `redis://localhost:6379/0` | Target Redis DB. |
| `PREFLIGHT_LISTEN_ADDR` | `:9001` | Bind address. |
| `PREFLIGHT_PING_INTERVAL` | `5s` | Heartbeat cadence. |
| `PREFLIGHT_PONG_TIMEOUT` | `75s` | Idle cutoff (set ≥60s in production). |
| `PREFLIGHT_LOG_LEVEL` | `info` | Log verbosity. |
| `PREFLIGHT_METRICS_ENABLED` | `false` | Expose `/metrics`. |
| `PREFLIGHT_MAX_MESSAGE_SIZE` | `64KB` | WebSocket read limit. |

## 9. Reliability & Performance Considerations

- **Backpressure**: Socket writes occur with context deadlines (e.g. 2 s); if a
  client cannot keep up, drop the connection to protect the server.
- **Redis resilience**: On pub/sub failure, attempt to resubscribe with
  exponential backoff and replay (`HGETALL`) before sending a fresh payload.
- **Stateless scaling**: The service remains stateless—multiple replicas can run
  behind the same load balancer because each connection is sticky to the worker
  that accepted it.
- **Graceful restart**: Use `http.Server` with `Shutdown(ctx)` so ECS/Kubernetes
  drains connections before exit.
- **Observability**:
  - Export metrics like `preflight_connections_active`,
    `preflight_redis_reconnects_total`, `preflight_messages_sent_total`.
  - Log structured events: connection accepted, closed, Redis error, diff sent.
  - Optional OpenTelemetry traces behind a feature flag for cross-service diagnostics.

## 10. Compatibility Strategy

- Preserve existing JSON schema:

```json
{
  "type": "preflight",
  "checklist": {
    "sbs_map": true,
    "...": false
  },
  "lock_statuses": {
    "wepp.nodb": false,
    ...
  }
}
```

- Continue sending `{"type":"ping"}` / `{"type":"hangup"}` control frames.
- Accept `{"type":"init"}` and `{"type":"pong"}` messages; ignore unknown types.
- Ensure TLS termination still lives in Caddy/Nginx; the Go service speaks plain
  WebSockets on the container's internal network.

## 11. Implementation Plan

1. **Bootstrap module**
   - Initialize the Go module under `services/preflight2` with entry point `cmd/preflight2/main.go`, set up configuration loading
     (stdlib `flag`/`os` or `envconfig` depending on complexity).
   - Wire `http.Server`, logging, and stub handlers.
2. **Redis client + checklist logic**
   - Port `preflight()` and `lock_statuses()` into Go with table-driven tests.
   - Add fixtures by exporting hashes from Redis (JSON files in `testdata/`).
3. **WebSocket handshake & heartbeat**
   - Implement connection struct with ping ticker, pong handler, idle cutoff.
   - Add integration tests using `net/http/httptest` and WebSocket clients.
4. **Pub/Sub integration**
   - Use go-redis `Client.Subscribe` scoped to `__keyspace@0__:<runid>`.
   - On notification, fetch updated hash, recompute checklist, and enqueue diff.
5. **Diffing & delivery**
   - Track last sent payload; skip redundant frames.
   - Marshal JSON with `encoding/json`.
6. **Operational polish**
   - Add `/metrics` (Prometheus registry) and `/health`.
   - Structured logging with `log/slog`.
   - Graceful shutdown with signal handling.
7. **Packaging**
   - Multi-stage Dockerfile (Go build → distroless runtime).
   - Update `docker/docker-compose.dev.yml` to replace the legacy `preflight`
     service entry with the Go-based `preflight2` container (keep environment and port 9001 alignment).
8. **Cutover phase**
   - Deploy side-by-side with old service on alternate port.
   - Run smoke tests, confirm stability, then switch Caddy upstream.
   - Retire Python service after sustained burn-in.

## 12. Testing Strategy

- **Unit tests**:
  - Checklist evaluation for known RedisPrep combinations.
  - Lock extraction.
  - Heartbeat timers via fake clocks where possible.
- **Integration tests**:
  - Spin up ephemeral Redis (testcontainer) and ensure updates propagate.
  - Simulate Redis disconnects to verify reconnection logic.
  - Verify no duplicate frames for unchanged hashes.
- **Load testing**:
  - k6 or vegeta script opening 200 sockets and mutating a run hash.
  - Measure latency and memory footprint.
- **Fuzz testing**:
  - Use Go's native fuzzing to stress checklist evaluation and hash parsing.

## 13. Migration Notes

- Ensure Redis keyspace notifications (`notify-keyspace-events`) still include
  `Kh`. Document the requirement in deployment playbooks.
- Update `wctl` and docs to reference `preflight2`.
- Consider keeping `preflight.py` in maintenance mode during transition; add a
  runtime switch in Caddy to roll back quickly if needed.

## 14. Developer Notes

- **Local builds**: `go build ./...` from `services/preflight2` compiles the binary. If Go tooling isn’t installed, `docker compose build preflight` performs the build inside a container and produces an updated `go.sum`.
- **Formatting & linting**: Run `go fmt ./...` before committing. Optional linters (e.g., `golangci-lint run ./...`) are encouraged but not required yet.
- **Testing**: Use the compose-managed Go builder. `wctl run-preflight-tests` runs `go test ./...`; append flags such as `-tags=integration ./internal/server` to exercise the miniredis/WebSocket harness. See `docs/testing-strategy-and-implementation-plan.md` for the full workflow. A nightly GitHub Action (`preflight-tests-nightly`, 02:35 AM PT) executes the same command on self-hosted runners to catch regressions automatically.
- **Configuration management**: Prefer injecting `PREFLIGHT_*` vars via `.env` or Compose overrides rather than hardcoding defaults. Avoid committing secrets; Redis credentials should come from the environment or Docker secrets.
- **Shared utilities**: If you need common code between `preflight2` and `status2`, consider creating `services/common` for shared logging/config helpers to avoid divergence.

## 15. DevOps Playbook

- **Build**: `docker compose build preflight` compiles the Go binary and assembles the distroless image. This command must run on a machine with outbound network access for Go modules.
- **Run locally**: `docker compose up preflight` exposes the service on `localhost:9001`. Verify `/health` and `/metrics` (when `PREFLIGHT_METRICS_ENABLED=true`).
- **Ports & networking**: The container listens on `0.0.0.0:9001` by default. Ensure reverse proxies (Caddy/Nginx) forward `/weppcloud-microservices/preflight/*` to this service.
- **Monitoring**: Scrape Prometheus metrics; key series include `preflight2_connections_active`, `preflight2_messages_sent_total`, and `preflight2_redis_reconnects_total`. Set alerts on sustained reconnect spikes or zero connections to catch outages.
- **Logging**: Structured JSON to stdout. Pipe through `jq` or ship into Loki/ELK. Look for `connection ended with error` messages to diagnose client issues.
- **Redis prerequisites**: Start Redis with hash keyspace notifications enabled, e.g. `command: ["redis-server", "--notify-keyspace-events", "Kh"]`. Without `Kh`, Redis never publishes the `__keyspace@0__:<runid>` messages caused by `HSET`/`HDEL`, so preflight receives only the initial checklist.
- **Deployment**: Roll out alongside the Python service first (e.g., route 10% of traffic) before swapping the main Caddy upstream. Keep the old container available for at least one release as a fallback.
