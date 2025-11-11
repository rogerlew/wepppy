# status2 Testing Strategy & Implementation Plan

## 1. Current State Review

- **Service role**: `status2` proxies Redis DB 2 Pub/Sub traffic to browser WebSocket clients with per-connection isolation, structured logging, and optional Prometheus metrics.
- **Strengths**:
  - Clean separation among configuration (`internal/config`), transport/payload (`internal/payload`), and runtime orchestration (`internal/server`).
  - Per-connection goroutine model (read, ping, Redis loops) coordinated via `errgroup.WithContext`, avoiding shared bottlenecks.
  - Defensive shutdown path (`sendHangup`) and graceful HTTP server teardown in `cmd/status2/main.go`.
  - Metrics abstraction that becomes a no-op when disabled yet still exposes `/metrics` as a safe 404.
- **Observed risks & gaps**:
  1. `STATUS_REDIS_REQUEST_TIMEOUT` (declared in `internal/config/config.go`) is never applied inside `redisLoop`, so a stalled Redis read can hang a connection indefinitely.
  2. The exponential backoff in `connection.redisBackoff` lacks jitter, potentially causing synchronized reconnect storms during Redis outages.
  3. Default `PongTimeout` is 15s while the service specification and sibling microservices use ≥60s; the shorter timeout risks disconnecting long-lived clients under transient network jitter.
  4. When `STATUS_ALLOWED_ORIGINS` is unset, `websocket.Accept` runs with `InsecureSkipVerify=true`, which is appropriate for internal dev but should be surfaced via logs/metrics so production can enforce explicit origins.
  5. There are no automated tests; high-value behaviors (heartbeat enforcement, Redis retry loop, metrics toggling) are currently only covered by manual verification.

## 2. Testing Strategy

### 2.1 Unit Tests

| Area | Target | Scenarios |
|------|--------|-----------|
| Configuration | `config.Load` | Defaults, duration parsing, log-level normalization, list parsing, invalid inputs falling back safely. |
| Validation | `channelPattern` & `handleWebsocket` routing | Accept/deny path variants (`health`, empty, malformed channel). |
| Connection logic | `connection.redisBackoff`, `shouldAbort`, `forward`, `touch` | Ensure retry ceilings honor `RedisRetryMax`, hangup emits payload even on closed socket (assert error increments metric once). |
| Retry helper | `retryableInitError` | Net timeout, DNS failure, EOF vs non-retryable errors. |
| Metrics wrapper | `metrics.handler` | Enabled/disabled behavior, counters increment/decrement symmetry. |

To keep tests deterministic:
- Place tests beside implementations (e.g., `internal/server/server_test.go`) using the same package to access unexported helpers.
- Use `github.com/alicebob/miniredis/v2` to stub Redis for config and connection tests without networking.
- Inject fake WebSocket connections with `nhooyr.io/websocket/wsjson` + `net/http/httptest`.

### 2.2 Integration Tests

| Focus | Setup | Assertions |
|-------|-------|------------|
| Happy path streaming | Spin up `miniredis`, start HTTP server with `httptest.NewServer`, connect WebSocket client. Publish messages and confirm `{"type":"status","data":…}` ordering and content. |
| Heartbeat enforcement | Use controllable clock (exposed via `timeNow` func or `clock.Clock` interface) to fast-forward without `pong` frames and assert connection closes with timeout error. |
| Redis outage recovery | Simulate `pubsub.ReceiveMessage` failures by pausing `miniredis`, ensure reconnect attempts honor backoff and eventually resume streaming after Redis resumes. |
| Origin filtering | Configure `STATUS_ALLOWED_ORIGINS` and verify requests with disallowed `Origin` headers are rejected with 403. |
| Metrics endpoint | Enable metrics and confirm counters reflect open connections/messages; disable and ensure `/metrics` responds 404. |

All integration tests should run behind a `-tags=integration` build flag so they are optional in quick CI runs but executed in nightly/end-to-end pipelines.

### 2.3 Reliability & Performance Verification

- **Load**: Use `k6` or `vegeta` scripts to hold ~300 concurrent sockets publishing at realistic cadence. Measure latency from Redis publish to WebSocket receive (<50 ms target).
- **Chaos**: Introduce Redis restarts and network jitter (tc/netem in CI or docker compose) to validate exponential backoff and connection churn behavior.
- **Long-run soak**: 24-hour canary with metrics scraping to ensure counters reset correctly and no goroutine leaks occur.

### 2.4 Tooling & Automation

- Extend `wctl` with `run-status2-tests` to execute `go test ./...` (unit) and `go test -tags=integration ./...` inside the container.
- Wire unit tests into the existing CI pipeline; schedule integration/load jobs nightly or before release.
- Add ownership metadata (CODEOWNERS) so Go microservice SMEs approve changes.

## 3. Implementation Plan

### Phase 1 – Hardening (Week 1)

1. **Timeout enforcement**: Thread `cfg.RedisRequestTimeout` through `redisLoop` by wrapping `ReceiveMessage` calls with `context.WithTimeout`, falling back to the main context on expiry. Log timeout events distinctly.
2. **Backoff jitter**: Introduce decorrelated jitter (e.g., full jitter algorithm) to `redisBackoff`, seeded per connection to avoid synchronized reconnects.
3. **Heartbeat alignment**: Update `defaultPongTimeout` to ≥60 s (match preflight2) and document the new default. Add warning log when operating with `InsecureSkipVerify` to nudge production hardening.

### Phase 2 – Test Harness (Week 2)

1. **Unit test scaffolding**: Add `_test.go` files for config, server helpers, and metrics. Leverage table-driven tests and `miniredis` fixtures.
2. **Integration harness**: Create `internal/server/integration_test.go` guarded behind `integration` build tag. Reuse helper to spin up full server, start real WebSocket client using `websocket.Dial`, and manipulate Redis.
3. **CI wiring**: Update project CI to run `go test ./...` on every change; add optional job for `-tags=integration` triggered via label or nightly schedule.

**Status:** ✅ Unit tests cover configuration overrides and retry helpers (`internal/config/config_test.go`, `internal/server/server_test.go`). An integration harness backed by `miniredis` validates Redis→WebSocket forwarding (`internal/server/integration_test.go`, enabled with `-tags=integration`). The new `wctl run-status-tests` helper runs both suites, and accepts extra arguments to toggle integration coverage in CI. Nightly execution is handled by the `status-tests-nightly` GitHub Action (02:40 AM PT) to ensure the Go builder runs on schedule.

### Phase 3 – Observability & Load Validation (Weeks 3–4)

1. **Metrics verification**: Implement e2e test (canary or smoke job) executing k6 scenario, validating Prometheus gauges/counters via scrape snapshot.
2. **Chaos scripts**: Add docker-compose task that restarts Redis during load to validate reconnect logs and ensure no stale sockets remain.
3. **Documentation refresh**: Update `services/status2/README.md` and `AGENTS.md` with new defaults, testing commands, and operational runbooks. Link to this document for future context.

**Status:** ✅ Load-testing harness and chaos drills captured in `docs/k6-status2-load.js` and `docs/chaos-playbook.md`. The README now references the new workflows. Outstanding work: integrate k6 + chaos runs into CI/CD and capture metrics snapshots for regression tracking.

### Deliverables & Acceptance

- Passing unit and integration test suites demonstrating coverage of configuration, handshake, heartbeat, and Redis retry behavior.
- Updated defaults and logging protecting against silent insecure origin usage.
- Load- and chaos-testing evidence showing reconnect jitter prevents synchronized storms and that the service meets latency/SLO targets.
- Documentation referencing the new tooling so future agents can execute tests without rediscovering the workflow.
