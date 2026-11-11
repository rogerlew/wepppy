import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const BASE_URL = __ENV.STATUS2_WS_URL || 'ws://localhost:9002';
const RUN_ID = __ENV.STATUS2_RUN_ID;
const ORIGIN = __ENV.STATUS2_ORIGIN;
if (!RUN_ID || !ORIGIN || !__ENV.STATUS2_CREDENTIAL_FILE) throw new Error('Run, Origin and protected credential file are required');
const credential = JSON.parse(open(__ENV.STATUS2_CREDENTIAL_FILE));
const duration = __ENV.STATUS2_DURATION || '2m';
const boundedDuration = /^(\d+)(s|m)$/.exec(duration);
if (!boundedDuration || typeof credential.token !== 'string' || !credential.token || typeof credential.config !== 'string' || !credential.config || !Number.isInteger(credential.expires_at) || credential.service !== 'status') throw new Error('Invalid smoke credential or duration');
const durationMs = Number(boundedDuration[1]) * (boundedDuration[2] === 'm' ? 60000 : 1000);
if (!Number.isFinite(durationMs) || durationMs <= 0) throw new Error('Duration must be positive');
if (credential.expires_at * 1000 < Date.now() + durationMs + 10000) throw new Error('Mint a fresh credential or shorten the test');
if (/[?@]/.test(BASE_URL)) throw new Error('Base URL must not contain credentials or query parameters');
const CHANNEL = __ENV.STATUS2_CHANNEL || 'wepp';
const MESSAGE_WAIT_TIMEOUT = Number(__ENV.STATUS2_MESSAGE_TIMEOUT_MS || 5000);

export const options = {
  vus: Number(__ENV.STATUS2_VUS || 200),
  duration,
  thresholds: {
    checks: ['rate==1'],
    status2_messages: ['count>0'],
    status2_connection_failures: ['count<1'],
  },
};

const connectionAgeTrend = new Trend('status2_message_connection_age_ms', true);
const receivedMessages = new Counter('status2_messages');
const connectionFailures = new Counter('status2_connection_failures');

export default function status2Scenario() {
  const url = `${BASE_URL.replace(/\/$/, '')}/${encodeURIComponent(RUN_ID)}:${encodeURIComponent(CHANNEL)}?config=${encodeURIComponent(credential.config)}`;
  const start = Date.now();

  const response = ws.connect(url, {headers: {Origin: ORIGIN, 'Sec-WebSocket-Protocol': 'wepp-stream.v1, bearer.' + credential.token}}, function socket(wsConn) {
    wsConn.on('open', function open() {
      wsConn.send(JSON.stringify({ type: 'init' }));
    });

    wsConn.on('message', function message(raw) {
      try {
        const payload = JSON.parse(raw);
        if (payload.type === 'ping') {
          wsConn.send(JSON.stringify({ type: 'pong' }));
        } else if (payload.type === 'status') {
          receivedMessages.add(1);
          connectionAgeTrend.add(Date.now() - start);
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

  const selected = response && response.headers['Sec-Websocket-Protocol'];
  check(response, { connected: r => r && r.status === 101 && (Array.isArray(selected) ? selected[0] : selected) === 'wepp-stream.v1' });
}
