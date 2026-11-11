# status2 Chaos & Load Playbook

This guide outlines the operational drills used to validate `status2` under failure and high-load scenarios.

## Prerequisites

- A selected accessible disposable project and a freshly minted status credential.
- A temporary mode-0600 credential file containing the stream-token JSON response
  (`token`, `expires_at`, `config`, `service`); remove it after the test and never
  upload it as an artifact or enable k6 HTTP debugging.
- Docker Compose development stack running (`wctl up status redis`).
- `k6` installed on the host (`brew install k6` or download from https://k6.io).
- Redis CLI available (`docker compose exec redis redis-cli`).

## 1. Load Testing with k6

1. Build and run `status2` with Redis:
   ```bash
   wctl up -d status redis
   ```
2. Start a bounded background publisher for the same disposable run. Keep it
   running while sockets connect; a one-off publish before connection is lost.
   Use the configured web container's Redis credentials:
   ```bash
   wctl exec -T weppcloud python - "$DISPOSABLE_RUN_ID" <<'PYTHON' &
   import sys, time
   from redis import Redis
   from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
   with Redis(**redis_connection_kwargs(RedisDB.STATUS)) as conn:
       for _ in range(130):
           conn.publish(sys.argv[1] + ':wepp', 'load-test progress')
           time.sleep(1)
   PYTHON
   ```
3. Start the k6 scenario:
   ```bash
   STATUS2_WS_URL=ws://localhost:9002 \
   STATUS2_RUN_ID="$DISPOSABLE_RUN_ID" \
   STATUS2_ORIGIN=https://forest.tail305ec9.ts.net \
   STATUS2_CREDENTIAL_FILE="$PROTECTED_CREDENTIAL_FILE" \
   STATUS2_CHANNEL=wepp \
   STATUS2_VUS=300 \
   STATUS2_DURATION=2m \
   k6 run services/status2/docs/k6-status2-load.js
   ```
The scenario rejects a duration exceeding remaining credential validity and
checks the actual HTTP 101 and fixed negotiated protocol. Failed checks or
zero received status messages fail the run. Mint a fresh credential
for each bounded drill; it does not renew browser sessions. API reference:
[k6 WebSocket parameters](https://grafana.com/docs/k6/latest/javascript-api/k6-ws/params/).

4. Inspect Prometheus metrics (if enabled) or container logs for reconnect spikes.
5. Require successful handshakes and received status messages. The
   `status2_message_connection_age_ms` trend records socket age at receipt; it
   does not measure publish-to-receive latency and has no latency SLO threshold.

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
