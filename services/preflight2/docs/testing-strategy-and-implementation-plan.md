# preflight2 Testing Strategy & Implementation Plan

## 1. Current State Review

- **Service role**: `preflight2` streams RedisPrep checklists and lock statuses over WebSockets so run dashboards reflect real-time readiness.
- **Strengths**:
  - Connection lifecycle mirrors the Go status service: per-socket goroutines, structured logging, optional Prometheus metrics.
  - Checklist evaluation lives in a dedicated package (`internal/checklist`), keeping Redis decoding deterministic and testable.
  - Heartbeat enforcement and hangup semantics match the legacy client expectations, simplifying browser integration.
- **Observed risks & gaps**:
  1. Default heartbeat timeout was tuned for legacy Tornado behaviour (15 s); longer browser throttling windows require higher defaults.
  2. `redisBackoff` uses deterministic exponential growth without jitter, so reconnect storms remain possible after shared outages.
  3. No automated tests were in place prior to this effort; configuration drift or Redis retry regressions could slip through unnoticed.

## 2. Testing Strategy

### 2.1 Unit Tests

| Area | Target | Scenarios |
|------|--------|-----------|
| Configuration | `internal/config` | Defaults, env overrides, log-level parsing, allowed origins list handling. |
| Connection helpers | `internal/server` | Backoff bounds, abort rules, keyspace channel derivation. |
| Checklist logic | `internal/checklist` (future) | Translate Redis hashes into checklist/lock payloads using captured fixtures. |

Unit tests run via `wctl run-preflight-tests` (defaults to `go test ./...`). For deterministic coverage, keep tests self-contained and avoid network dependencies.

### 2.2 Integration Tests

- Guarded behind the `integration` build tag (`//go:build integration`).
- Harness uses `miniredis` + `httptest.Server` to:
  - Seed Redis hashes.
  - Open a WebSocket connection via `nhooyr.io/websocket`.
  - Assert the initial `preflight` payload and subsequent updates after publishing keyspace notifications.
- Execute with:
  ```bash
  wctl run-preflight-tests -tags=integration ./internal/server
  ```

### 2.3 Reliability & Performance Verification

- Reuse the status-service playbooks for chaos and load (Redis restart, network jitter, k6 scenarios) with adjusted endpoints (`ws://localhost:9001`).
- Capture Prometheus counters (`preflight_connections_active`, `_redis_reconnects_total`, `_messages_sent_total`) before/after exercises.

### 2.4 Tooling & Automation

- Compose exposes a `preflight-build` helper (golang:1.25-alpine) so Go toolchain work happens in containers.
- `wctl run-preflight-tests` shells into that service, runs `go mod tidy`, and then executes `go test` with forwarded arguments.
- Plan to wire both unit and integration targets into CI nightly runs once coverage stabilises.

## 3. Implementation Plan

### Phase 1 – Hardening (Complete)

- Raised the default pong timeout to 75 s to match browser throttling windows.
- Ensured Redis request timeouts guard checklist refreshes and kept exponential backoff limits configurable.

### Phase 2 – Test Harness (Complete)

- Added unit suites for configuration parsing and retry helpers (`internal/config/config_test.go`, `internal/server/server_test.go`).
- Built an integration harness using `miniredis` to validate Redis→WebSocket flow (`internal/server/integration_test.go`).
- Documented execution commands in this plan and in `services/preflight2/README.md`.

### Phase 3 – Observability & Load Validation (Planned)

1. Port the `status2` k6 scenario to target `/preflight` and monitor checklist latency under 200+ concurrent sockets.
2. Script Redis restart and `tc` jitter drills tailored to `preflight2`, logging reconnect behaviour and hangup counts.
3. Capture baseline metrics snapshots and integrate load/chaos checks into pre-release validation.

## 4. Deliverables & Acceptance Criteria

- ✅ Reliable Go test harness covering configuration, Redis retry policies, and end-to-end WebSocket updates.
- ☐ Documented load/chaos benchmarks with reproducible scripts.
- ☐ CI job (or scheduled pipeline) invoking `wctl run-preflight-tests` with and without `-tags=integration`.
- ☐ README/AGENTS updates referencing chaos and load documentation once finalized.

## 5. Reference Commands

```bash
# Unit tests
wctl run-preflight-tests

# Integration tests (miniredis + WebSocket)
wctl run-preflight-tests -tags=integration ./internal/server

# Manual Go command (escape hatch)
wctl run --rm preflight-build sh -lc 'PATH=/usr/local/go/bin:$PATH go test ./internal/checklist'
```

Keep this document current; update the status tables and automation notes whenever the test surface evolves.
