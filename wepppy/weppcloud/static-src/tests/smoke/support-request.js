import http from 'node:http';
import https from 'node:https';
import net from 'node:net';

function supportUrl(input, method) {
  const base = new URL(process.env.SMOKE_BASE_URL || 'http://localhost:8080');
  const host = base.hostname.replace(/^\[|\]$/g, '');
  const loopback = host === 'localhost' || host === '::1'
    || (net.isIP(host) === 4 && host.startsWith('127.'));
  if (base.username || base.password || base.search || base.hash
      || !(base.protocol === 'https:' || (base.protocol === 'http:' && loopback))) {
    throw new Error('Support URL requires HTTPS (HTTP only on loopback), without userinfo/query/fragment.');
  }
  const url = new URL(input, base);
  const prefix = `${base.pathname.replace(/\/$/, '')}/tests/api/`;
  const prefixes = [prefix, '/tests/api/', '/weppcloud/tests/api/'];
  const matchedPrefix = prefixes.find(value => url.pathname.startsWith(value));
  const match = matchedPrefix && url.pathname.slice(matchedPrefix.length).match(/^(ping|create-run|run\/[^/]+)$/);
  const allowed = match && ((method === 'GET' && match[1] === 'ping')
    || (method === 'POST' && match[1] === 'create-run')
    || (method === 'DELETE' && match[1].startsWith('run/')));
  if (!allowed || url.origin !== base.origin || url.username || url.password || url.search || url.hash) {
    throw new Error('Support request target is outside the configured support boundary.');
  }
  url.pathname = `${base.pathname.replace(/\/$/, '')}/tests/api/${match[1]}`;
  return url;
}

async function send(method, input, options = {}) {
  const url = supportUrl(input, method);
  const token = process.env.SMOKE_TEST_SUPPORT_TOKEN;
  if (!token || /\s/.test(token)) {
    throw new Error('Support credential unavailable; use wctl run-playwright.');
  }
  const data = options.data === undefined ? undefined : JSON.stringify(options.data);
  // Native HTTP stays outside Playwright tracing. Never expose request/error objects.
  return new Promise((resolve, reject) => {
    const fail = () => reject(new Error('Support request failed; check backend/profile/credential.'));
    const req = (url.protocol === 'https:' ? https : http).request(url, {
      method,
      rejectUnauthorized: true, // Preserve TLS verification even with ambient Node overrides.
      agent: false, // Do not inherit ambient proxy configuration from global agents.
      headers: {
        Authorization: `Bearer ${token}`,
        ...(data === undefined ? {} : { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) })
      },
      timeout: 60000
    }, (res) => {
      const chunks = [];
      res.on('data', chunk => chunks.push(chunk));
      res.on('error', fail);
      res.on('end', () => {
        const status = res.statusCode;
        // No redirect following; deletion errors must not be mistaken for cleanup.
        if ((status >= 300 && status < 400) || (method === 'DELETE' && status !== 200)) {
          fail();
          return;
        }
        const body = Buffer.concat(chunks).toString().split(token).join('[redacted]');
        resolve({
          ok: () => status >= 200 && status < 300,
          status: () => status,
          statusText: () => String(status),
          text: async () => body,
          json: async () => {
            try { return JSON.parse(body); } catch { throw new Error('Invalid support response JSON.'); }
          }
        });
      });
    });
    req.on('error', fail);
    req.on('timeout', () => { req.destroy(); fail(); });
    req.end(data);
  });
}

export const supportRequest = {
  get: (url) => send('GET', url),
  post: (url, options) => send('POST', url, options),
  delete: (url) => send('DELETE', url)
};
