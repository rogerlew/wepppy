# Status2 Microservice Specification

> **See also:** [AGENTS.md](../../AGENTS.md) for Go Microservices section and High Performance Telemetry Pipeline overview.

Date: 2025-10-11  
Owner: Roger  
Developer: codex
Status: Approved

## 1. Context

The legacy `wepppy/microservices/status.py` service is a Tornado-based
WebSocket fan-out for Redis DB 2 Pub/Sub channels. Browsers subscribe to
`wss://…/weppcloud-microservices/status/<runid>:<channel>` and receive JSON
frames whenever long-running tasks publish status strings. The Python service
has accrued operational issues similar to the earlier preflight microservice:
shared event loops stall when Redis or a socket misbehaves, and async race
conditions occasionally drop clients.

`status2` rewrites the service in Go following the same goals as `preflight2`:
predictable per-connection isolation, resilient Redis handling, and strong
observability.

## 2. Goals

- Highly reliable WebSocket streaming of Redis Pub/Sub messages for any
  `<runid>:<channel>` pair.
- Per-connection goroutines with isolated Redis subscriptions (no shared
  bottlenecks).
- Backwards-compatible JSON payloads: `{"type":"status","data":<string>}` plus
  control frames (`ping`, `hangup`).
- Graceful degradation on Redis outages with automatic resubscription and
  bounded retries.
- Operational visibility via structured logs, Prometheus metrics, and health
  endpoints.

## 3. Non-Goals

- Rewriting the browser client.
- Changing channel naming conventions or introducing message schemas beyond
  the existing string payloads.
- Adding message persistence or replay.

## 4. Current Pain Points & Requirements Drivers

Observations from the Tornado service:

1. **Shared Pub/Sub cursor** — all sockets share a single `shared_redis`
   connection; slow clients can block others.
2. **Heartbeat sensitivity** — pings skip when Tornado drops the underlying
   socket reference, leading to phantom disconnects.
3. **Fatal exit strategy** — unexpected exceptions call `os._exit(1)`, causing
   abrupt termination rather than controlled retries.
4. **Limited observability** — minimal logging and no metrics.
5. **Unbounded retry** — reconnect loops spin infinitely on Redis errors without
   jitter or circuit breaking.

These drive the Go design: each connection owns its Pub/Sub stream, heartbeat
timers are reliable, fatal errors are avoided, and instrumentation is built in.

## 5. Functional Requirements

1. **WebSocket endpoint**: `/(<runid>:<channel>)`
   - Accepts `{"type":"init"}` messages and replies with heartbeat `{"type":"ping"}` frames.
   - `{"type":"pong"}` resets idle timers.
   - Sends status payloads as `{"type":"status","data":<string>}`; binary frames ignored.
   - Validates `Origin` header against allowlist to mitigate CSWSH (configurable).
2. **Redis subscription**:
   - Channel names mirror legacy format `<runid>:<channel>`.
   - Each connection maintains its own Redis `PubSub` listener.
   - On receiving messages, forward text payload to browser without mutation.
3. **Heartbeat**:
   - Server emits `ping` every N seconds (default 5s).
   - Connection closes if no `pong` within configured timeout (>60s).
4. **Health & metrics**:
   - `GET /health` returns `OK` when serving requests.
   - Optional `GET /metrics` (Prometheus).
5. **Graceful shutdown**:
   - On server termination, send `{"type":"hangup"}` before closing sockets.
   - Unsubscribe from Redis and close Pub/Sub connections cleanly.

## 6. Non-Functional Requirements

- Target Go ≥ 1.25.
- Support 300 concurrent sockets with <50 ms added latency.
- Handle Redis reconnects with exponential backoff (configurable base/max) and
  capped retry attempts (default 5) before surfacing errors.
- Container image ≤ 50 MB via distroless runtime.
- Structured JSON logs using stdlib `log/slog`.
- Configuration via `STATUS_`-prefixed environment variables (mirroring
  `PREFLIGHT_` knobs where applicable).

## 7. Domain Model & Data Flow

### 7.1 Redis Pub/Sub

- DB: `RedisDB.STATUS` (logical DB 2).
- Channels follow `<runid>:<channel>` names; payloads are plain strings.
- Producers include `StatusMessenger.publish`, RQ job hooks, and command bar
  utilities.

### 7.2 Event Flow

```
Redis (DB 2) ── Pub/Sub message ─▶ Connection goroutine ──▶ WebSocket client
                      │                                      ▲
                      └─ per-connection redis.Client ────────┘
```

Each connection includes:

1. WebSocket read loop (handles `pong`, `init`).
2. Write loop injecting `ping` heartbeats and status payloads.
3. Redis Pub/Sub loop delivering messages.
4. Shared cancellation context to stop all goroutines on error or disconnect.

## 8. High-Level Architecture

### 8.1 Components

- **HTTP Server**: stdlib `net/http` with `http.ServeMux`.
  - Routes: `/health`, `/metrics` (optional), `/{runid}:{channel}` (WebSocket).
  - Use `nhooyr.io/websocket` for WebSocket implementation (context-aware,
    zero-copy features).
- **Config package**: mirrors `preflight2` with `STATUS_` env vars (host,
  ping/pong intervals, redis URL, allowed origins, metrics toggle).
- **Connection manager**: orchestrates per-socket goroutines, tracks active
  counts for metrics, and enforces origin validation.
- **Redis client**: `go-redis v9` using URL config, with connection pool per
  process; each connection gets its own `PubSub`.
- **Message payload**: thin wrapper struct for JSON encoding; no transformation
  of the `data` field beyond string casting.
- **Metrics**: Prometheus counters/gauges:
  - `status_connections_active`
  - `status_messages_forwarded_total`
  - `status_redis_reconnects_total`
  - `status_write_errors_total`

### 8.2 Configuration knobs

| Env Var | Default | Description |
|---------|---------|-------------|
| `STATUS_REDIS_URL` | `redis://localhost:6379/2` | Target Redis DB. |
| `STATUS_LISTEN_ADDR` | `:9002` | Bind address. |
| `STATUS_PING_INTERVAL` | `5s` | Heartbeat cadence. |
| `STATUS_PONG_TIMEOUT` | `75s` | Idle cutoff (set ≥60s in production). |
| `STATUS_LOG_LEVEL` | `info` | Log level for slog handler. |
| `STATUS_METRICS_ENABLED` | `false` | Whether to serve `/metrics`. |
| `STATUS_ALLOWED_ORIGINS` | *(empty)* | Comma-separated wildcard list (e.g., `*.usda.gov`). |
| `STATUS_WRITE_TIMEOUT` | `2s` | Deadline for WebSocket writes. |
| `STATUS_REDIS_REQUEST_TIMEOUT` | `1s` | Timeout for Redis receive operations. |
| `STATUS_REDIS_MAX_RETRIES` | `5` | Retries before surfacing a fatal error (0 disables cap). |
| `STATUS_REDIS_RETRY_BASE` | `1s` | Backoff baseline. |
| `STATUS_REDIS_RETRY_MAX` | `30s` | Backoff ceiling. |
| `STATUS_MAX_MESSAGE_SIZE` | `64KB` | WebSocket read limit. |

## 9. Reliability & Performance Considerations

- **Backpressure**: WebSocket writes use timeouts and per-connection mutex to
  avoid concurrent writes; slow clients are disconnected after timeout.
- **Redis resilience**: Retry loops back off exponentially with per-connection
  jitter (full jitter between base interval and cap) to avoid thundering herd.
  After exceeding retry limit,
  connection closes with appropriate log.
- **Stateless scaling**: No shared state; multiple replicas behind a load
  balancer can handle clients independently.
- **Graceful restart**: Use `http.Server.Shutdown` with context to drain
  connections, sending `hangup` frames first.
- **Observability**: Structured logs with run ID and channel context; metrics
  for connections, message throughput, and errors. Optional tracing hook via
  OpenTelemetry if required later.

## 10. Compatibility Strategy

- Preserve existing URL format (`/{runid}:{channel}`) and payload schema.
- Accept `{"type":"init"}`, respond with `{"type":"ping"}` and expect
  `{"type":"pong"}`; ignore unknown message types for forward compatibility.
- Keep TLS termination handled by external proxy (Caddy/nginx).

## 11. Implementation Plan

1. **Scaffold module**  
   - Create `services/status2/` module mirrored after `preflight2`, with
     `cmd/status2/main.go`, `internal/config`, `internal/server`, etc.
   - Reuse shared patterns where possible (consider extracting common helpers).

2. **Configuration & logging**  
   - Implement env parsing (`STATUS_` prefix) and `String()` summary for boot log.
   - Instantiate `slog` handler with structured JSON output.

3. **Redis abstraction**  
   - Parse Redis URL, instantiate `go-redis` client, validate connection on
     startup.
   - Provide helper to create per-connection `PubSub` with context-aware recv.

4. **Checklist equivalent**  
   - Not required; payload is simple string. Implement `status.Payload` struct
     with `Type` and `Data` fields for consistency.

5. **Connection lifecycle**  
   - Build connection struct with read loop (process `pong`/`init`), ping loop,
     and Redis loop.
   - Use `errgroup.WithContext` to coordinate goroutines.
   - On exit, send hangup, close WebSocket, unsubscribe.

6. **Metrics**  
   - Register Prometheus metrics similar to preflight2; conditional `/metrics`
     handler.

7. **HTTP server & shutdown**  
   - `http.ServeMux` routes, `http.Server` with read/idle timeouts,
     signal-driven graceful shutdown.
   - Update `docker/docker-compose.dev.yml` to point `status` service at new
     Dockerfile/binary (port 9002).

8. **Testing**  
   - Unit tests for config parsing and backoff calculations.
   - Integration tests using ephemeral Redis (testcontainers) verifying
     Pub/Sub → WebSocket flow.
   - Load tests (k6) to ensure concurrency/latency targets.

9. **Packaging**  
   - Multi-stage Dockerfile (Go build → distroless).
   - Ensure `go mod tidy` runs during build to materialize `go.sum`.

10. **Deployment & Migration**  
    - Add compose profile for status2 in dev; run alongside Python service for
      soak tests (alternate port, then switch).
    - Update systemd/Caddy config similarly to preflight2 when ready.
    - Document rollback path (reinstate legacy container).

## 12. Testing Strategy

- **Unit tests**: config parsing, run/channel validation, heartbeat timing.
- **Integration tests**: start local Redis, open WS connections, publish
  messages, assert receipt, simulate Redis dropouts.
- **Fuzz tests**: WebSocket message parsing (ensure unknown frames don’t panic).
- **Load tests**: 300+ concurrent clients publishing at moderate frequency to
  identify bottlenecks.

## 13. Migration Notes

- Redis keyspace configuration unaffected (pure Pub/Sub).
- Coordinate cutover with preflight2 to ensure both Go services run under same
  operational playbooks.
- Update documentation (`docker/README.md`, `wctl`) to point at
  `status2`.
- Retain Python service temporarily for rollback; remove once Go service proves
  stable.

## 14. Developer Notes

- **Local builds**: From `services/status2`, run `go build ./...` to compile. If Go tools are unavailable, rely on `docker compose build status`, which executes the build and generates `go.sum` inside the container.
- **Formatting**: Always run `go fmt ./...` before committing. Consider `golangci-lint` for additional checks; add suppressions via `//nolint` only when justified.
- **Testing**: Place unit tests near their packages. Use `go test ./...` for fast feedback. For end-to-end testing with Redis, start `docker compose up redis` and run `REDIS_URL=redis://localhost:6379/2 go test ./... -tags=integration`.
- **Telemetry helpers**: Reuse patterns from `preflight2` (metrics, logging). If you extend functionality, keep interfaces aligned so operators don’t juggle two different observability stacks.
- **Code organization**: Shared components (config parsing, metrics scaffolding) may eventually move to a `services/common` module; until then, maintain parity manually to avoid drift.

## 15. DevOps Playbook

- **Build pipeline**: `docker compose build status` compiles the Go binary using Go 1.25 and emits a distroless runtime image tagged `status2-dev`.
- **Runtime configuration**: Set `STATUS_*` environment variables in Compose, Kubernetes, or systemd. Ensure `STATUS_REDIS_URL` points at DB 2; credentials should come from secrets or environment management, not the image.
- **Local run**: `docker compose up status` runs the service on `localhost:9002`. Check `/health` for readiness; enable `/metrics` with `STATUS_METRICS_ENABLED=true`.
- **Monitoring**: Key Prometheus metrics include `status2_connections_active`, `status2_messages_forwarded_total`, `status2_redis_reconnects_total`, and `status2_write_errors_total`. Configure alerts for reconnect spikes or zero active connections.
- **Logging**: Structured JSON to stdout. Capture logs via `docker compose logs status -f | jq '.'` or ship to centralized logging. Investigate messages like `redis stream interrupted` promptly.
- **Redis setup**: No keyspace notifications required, but Pub/Sub must be enabled (default). Verify connectivity with `redis-cli -n 2 PUBLISH test:wepp "hello"` while a client listens.
- **Deployment strategy**: Roll out alongside the Python service on a canary port, update Caddy/Nginx routes once validated, and keep the legacy container on standby for rapid rollback until the Go version proves stable across releases.

## 16. WebSocket Contract

### 16.1 Handshake & Message Semantics

- Clients SHOULD optimistically send `{"type":"init"}` immediately after the WebSocket upgrade completes. `status2` does not require the frame to begin streaming, but it keeps parity with historical clients (`wepppy/weppcloud/controllers_js/status_stream.js:294` and `wepppy/weppcloud/controllers_js/ws_client.js:25`).
- `status2` MUST acknowledge readiness by issuing heartbeat frames of the form `{"type":"ping"}` at the cadence defined by `STATUS_PING_INTERVAL` (default 5s).
- Clients MUST reply to every heartbeat with `{"type":"pong"}` over the same connection without additional metadata (`wepppy/weppcloud/controllers_js/status_stream.js:273`, `wepppy/weppcloud/controllers_js/ws_client.js:35`, `wepppy/weppcloud/routes/command_bar/static/command-bar.js:783`).
- Application payloads are text frames encoded as `{"type":"status","data":<string>}`. Unknown message types SHOULD be ignored to preserve forward compatibility.
- When the server intends to terminate a connection, it SHOULD send a final `{"type":"hangup"}` frame and close the socket with normal closure status. Clients MAY treat `hangup` as a cue to reconnect after a randomized backoff.

### 16.2 Heartbeat & Timeout Requirements

- `STATUS_PING_INTERVAL` MUST remain no lower than 5s to avoid overloading browsers with unnecessary traffic; values between 5–15s keep UI panels reactive without spamming telemetry.
- `STATUS_PONG_TIMEOUT` MUST be configured to at least 60s (recommended 75s) in production. Browser clients process pong replies on the main thread; background tabs can experience scheduling delays of 30–45s under Chromium throttling. Values below 60s risk false positives during heavy DOM work or GC pauses.
- Operators MAY retain the legacy 15s timeout during local development for quicker failure detection, but fleet deployments MUST apply `STATUS_PONG_TIMEOUT >= 60s` through environment configuration until the code default is raised.
- Connections that miss two consecutive ping intervals beyond the timeout MUST be closed with `StatusPolicyViolation`. Clients SHOULD treat this as an invitation to reconnect using their built-in exponential backoff.

### 16.3 Known Client Expectations

- **StatusStream panels** (`wepppy/weppcloud/controllers_js/status_stream.js:268-339`) auto-respond to pings and maintain their own reconnect loop. They expect timeliness guarantees on pong windows but tolerate brief transport gaps.
- **Command bar command channel** (`wepppy/weppcloud/routes/command_bar/static/command-bar.js:620-789`) uses the same handshake, responds with `pong`, and reconnects with exponential backoff capped at 30s.
- **Legacy WSClient** controls (`wepppy/weppcloud/controllers_js/ws_client.js:23-109`) respond synchronously to heartbeats and emit spinner UI cues. They do not disable themselves in background tabs, so longer pong windows are essential when the page is throttled.

### 16.4 Compatibility Notes

- Third-party or automation clients MUST honor the same heartbeat contract and SHOULD mirror the browser behavior of sending `init`, replying with `pong`, and ignoring unknown message types.
- Future protocol extensions MUST preserve the `status` frame schema or version it explicitly. Additional control frames MUST be optional and documented alongside this contract.
- Operators SHOULD monitor `status2_write_errors_total` and connection churn metrics when adjusting heartbeat settings; spikes indicate misconfigured timeouts or clients that are not compliant with the contract.
