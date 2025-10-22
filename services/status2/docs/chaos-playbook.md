# status2 Chaos & Load Playbook

This guide outlines the operational drills used to validate `status2` under failure and high-load scenarios.

## Prerequisites

- Docker Compose development stack running (`wctl up status redis`).
- `k6` installed on the host (`brew install k6` or download from https://k6.io).
- Redis CLI available (`docker compose exec redis redis-cli`).

## 1. Load Testing with k6

1. Build and run `status2` with Redis:
   ```bash
   wctl up -d status redis
   ```
2. Kick off a background publisher to feed messages:
   ```bash
   docker compose exec redis redis-cli \
     -n 2 --raw --pipe <<'EOF'
   PUBLISH loadtest:wepp "ready"
   PLAY
   EOF
   ```
   or run a Python loop to publish every second.
3. Start the k6 scenario:
   ```bash
   STATUS2_WS_URL=ws://localhost:9002 \
   STATUS2_RUN_ID=loadtest \
   STATUS2_CHANNEL=wepp \
   STATUS2_VUS=300 \
   STATUS2_DURATION=5m \
   k6 run services/status2/docs/k6-status2-load.js
   ```
4. Inspect Prometheus metrics (if enabled) or container logs for reconnect spikes.
5. Compare `status2_message_latency_ms` trend against SLO (95th percentile < 50 ms).

## 2. Redis Restart Drill

1. Ensure k6 load is active (from the previous section).
2. Restart Redis to simulate outage:
   ```bash
   wctl compose restart redis
   ```
3. Observe `status2` logs for retries and eventual recovery.
4. Verify k6 counters (`status2_connection_failures`) remain below threshold.

## 3. Network Jitter Simulation

1. Install `tc` (traffic control) inside the `status` container:
   ```bash
   wctl exec status sh -lc "apk add --no-cache iproute2"
   ```
2. Introduce jitter:
   ```bash
   wctl exec status sh -lc "tc qdisc add dev eth0 root netem delay 200ms 50ms loss 2%"
   ```
3. Run k6 script for 2 minutes.
4. Remove rules:
   ```bash
   wctl exec status sh -lc "tc qdisc del dev eth0 root"
   ```
5. Confirm WebSocket clients stay connected and metrics reflect the induced latency.

## 4. Observability Checks

- Scrape metrics:
  ```bash
  curl -s http://localhost:9002/metrics | grep status2_
  ```
- Review structured logs (`wctl logs -f status`).
- Confirm Redis Pub/Sub message rate matches published volume.

## 5. Post-Drill Cleanup

- Stop load test (`Ctrl+C` for k6).
- Tear down containers if desired:
  ```bash
  wctl down status redis
  ```
- Archive k6 results (`k6 run ... --out json=results.json`) for regression comparison.
