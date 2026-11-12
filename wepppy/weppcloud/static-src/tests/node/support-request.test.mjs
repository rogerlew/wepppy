import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { supportRequest } from '../smoke/support-request.js';

test('support bearer stays on exact support paths, outside redirects and errors', async () => {
  const seen = [];
  const token = 'ephemeral.test.signature';
  const server = http.createServer((req, res) => {
    seen.push({ path: req.url, auth: req.headers.authorization });
    if (req.url.endsWith('/ping')) {
      res.writeHead(302, { Location: '/unrelated' });
      res.end();
    } else if (req.method === 'DELETE') {
      res.writeHead(403);
      res.end(token);
    } else {
      res.writeHead(201, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ run: { runid: 'fixture' }, echo: token }));
    }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const oldBase = process.env.SMOKE_BASE_URL;
  const oldToken = process.env.SMOKE_TEST_SUPPORT_TOKEN;
  process.env.SMOKE_BASE_URL = `http://127.0.0.1:${server.address().port}/weppcloud`;
  process.env.SMOKE_TEST_SUPPORT_TOKEN = token;
  try {
    const response = await supportRequest.post('/tests/api/create-run', { data: { config: 'dev_unit_1' } });
    assert.equal(response.status(), 201);
    assert.equal((await response.json()).run.runid, 'fixture');
    assert.equal((await response.text()).includes(token), false);
    assert.deepEqual(seen, [{ path: '/weppcloud/tests/api/create-run', auth: `Bearer ${token}` }]);
    for (const target of ['/unrelated', 'https://remote.example/tests/api/create-run', '/tests/api/create-run?x=1']) {
      await assert.rejects(supportRequest.post(target), /outside/);
    }
    assert.equal(seen.length, 1);
    await assert.rejects(supportRequest.get('/tests/api/ping'), /Support request failed/);
    assert.equal(seen.length, 2);
    await assert.rejects(supportRequest.delete('/tests/api/run/fixture'), /Support request failed/);
    delete process.env.SMOKE_TEST_SUPPORT_TOKEN;
    await assert.rejects(supportRequest.post('/tests/api/create-run'), /credential unavailable/);
    assert.equal(seen.length, 3);
    process.env.SMOKE_TEST_SUPPORT_TOKEN = token;
    process.env.SMOKE_BASE_URL = `http://127.0.0.1:${server.address().port}/custom`;
    await supportRequest.post('/custom/tests/api/create-run');
    assert.equal(seen.at(-1).path, '/custom/tests/api/create-run');
    process.env.SMOKE_BASE_URL = 'http://remote.example';
    await assert.rejects(supportRequest.post('/tests/api/create-run'), /requires HTTPS/);
  } finally {
    if (oldBase === undefined) delete process.env.SMOKE_BASE_URL; else process.env.SMOKE_BASE_URL = oldBase;
    if (oldToken === undefined) delete process.env.SMOKE_TEST_SUPPORT_TOKEN; else process.env.SMOKE_TEST_SUPPORT_TOKEN = oldToken;
    await new Promise(resolve => server.close(resolve));
  }
});

test('support ignores startup-enabled ambient proxies', async () => {
  const { spawn } = await import('node:child_process');
  let requests = 0;
  const server = http.createServer((req, res) => {
    requests += 1;
    res.end('{}');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const source = `import { supportRequest } from ${JSON.stringify(new URL('../smoke/support-request.js', import.meta.url).href)};
      try { await supportRequest.get('/tests/api/ping'); process.exitCode = 2; }
      catch { process.exitCode = 0; }`;
    const child = spawn(process.execPath, ['--input-type=module', '-e', source], {
      env: { ...process.env, NODE_USE_ENV_PROXY: '1', HTTP_PROXY: `http://127.0.0.1:${server.address().port}`,
        http_proxy: `http://127.0.0.1:${server.address().port}`, NO_PROXY: '', no_proxy: '',
        SMOKE_BASE_URL: 'http://127.0.0.1:1', SMOKE_TEST_SUPPORT_TOKEN: 'canary.proxy.signature' },
      stdio: 'pipe'
    });
    const code = await new Promise(resolve => child.on('exit', resolve));
    assert.equal(code, 0);
    assert.equal(requests, 0);
  } finally {
    await new Promise(resolve => server.close(resolve));
  }
});

test('support verifies TLS despite ambient insecure Node override', async () => {
  const https = await import('node:https');
  const { readFileSync } = await import('node:fs');
  const { spawn } = await import('node:child_process');
  let requests = 0;
  // Public disposable test key: never use these fixtures outside this local test.
  const server = https.createServer({
    key: readFileSync(new URL('./fixtures/localhost-test.key', import.meta.url)),
    cert: readFileSync(new URL('./fixtures/localhost-test.crt', import.meta.url))
  }, (req, res) => { requests += 1; res.end('{}'); });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const source = `import { supportRequest } from ${JSON.stringify(new URL('../smoke/support-request.js', import.meta.url).href)};
      try { await supportRequest.get('/tests/api/ping'); process.exitCode = 2; }
      catch { process.exitCode = 0; }`;
    const child = spawn(process.execPath, ['--input-type=module', '-e', source], {
      env: { ...process.env, NODE_TLS_REJECT_UNAUTHORIZED: '0',
        SMOKE_BASE_URL: `https://127.0.0.1:${server.address().port}`, SMOKE_TEST_SUPPORT_TOKEN: 'canary.tls.signature' },
      stdio: 'pipe'
    });
    const code = await new Promise(resolve => child.on('exit', resolve));
    assert.equal(code, 0);
    assert.equal(requests, 0);
  } finally {
    await new Promise(resolve => server.close(resolve));
  }
});
