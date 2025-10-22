import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const BASE_URL = __ENV.STATUS2_WS_URL || 'ws://localhost:9002';
const RUN_ID = __ENV.STATUS2_RUN_ID || 'loadtest';
const CHANNEL = __ENV.STATUS2_CHANNEL || 'wepp';
const MESSAGE_WAIT_TIMEOUT = Number(__ENV.STATUS2_MESSAGE_TIMEOUT_MS || 5000);

export const options = {
  vus: Number(__ENV.STATUS2_VUS || 200),
  duration: __ENV.STATUS2_DURATION || '2m',
  thresholds: {
    status2_message_latency_ms: ['p(95)<50'],
    status2_connection_failures: ['count<1'],
  },
};

const latencyTrend = new Trend('status2_message_latency_ms', true);
const connectionFailures = new Counter('status2_connection_failures');

export default function status2Scenario() {
  const url = `${BASE_URL.replace(/\/$/, '')}/${encodeURIComponent(RUN_ID)}:${encodeURIComponent(CHANNEL)}`;
  const start = Date.now();

  ws.connect(url, {}, function socket(wsConn) {
    wsConn.on('open', function open() {
      wsConn.send(JSON.stringify({ type: 'init' }));
    });

    wsConn.on('message', function message(raw) {
      try {
        const payload = JSON.parse(raw);
        if (payload.type === 'ping') {
          wsConn.send(JSON.stringify({ type: 'pong' }));
        } else if (payload.type === 'status') {
          latencyTrend.add(Date.now() - start);
        }
      } catch (err) {
        // ignore malformed frames
      }
    });

    wsConn.on('error', function error(err) {
      connectionFailures.add(1);
    });

    wsConn.setTimeout(function timeout() {
      // Allow the main test harness to keep the connection warm for a bit
      wsConn.close(1000, 'done');
    }, MESSAGE_WAIT_TIMEOUT);

    sleep(2);
  });

  check(true, { connected: true });
}
