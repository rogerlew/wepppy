// Run from repository root. No traces, screenshots, videos, headers, or tokens are persisted.
import fs from 'node:fs';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { createRequire } from 'node:module';
import { execFileSync, spawnSync } from 'node:child_process';
const repo = process.cwd();
const require = createRequire(path.join(repo, 'wepppy/weppcloud/static-src/package.json'));
const { chromium } = require('playwright');
const base = 'https://forest.tail305ec9.ts.net';
const artifact = path.join(repo, 'docs/work-packages/20261111_status_preflight_websocket_authorization/artifacts');
// CAP/login helpers reuse the established soil-anisotropy smoke workflow.
function fnv32aHash(text) {
  let value = 2166136261;
  for (const char of text) {
    value ^= char.codePointAt(0);
    value =
      (value + (value << 1) + (value << 4) + (value << 7) + (value << 8) + (value << 24)) >>> 0;
  }
  return value >>> 0;
}

function capExpandHex(seed, length) {
  let state = fnv32aHash(seed);

  function nextU32() {
    state ^= (state << 13) >>> 0;
    state ^= state >>> 17;
    state ^= (state << 5) >>> 0;
    state >>>= 0;
    return state;
  }

  let out = '';
  while (out.length < length) {
    out += nextU32().toString(16).padStart(8, '0');
  }
  return out.slice(0, length);
}

function buildCapPairs(challengePayload) {
  const token = String(
    challengePayload && challengePayload.token ? challengePayload.token : ''
  ).trim();
  const challenge = challengePayload && challengePayload.challenge;
  if (!token || !challenge || typeof challenge !== 'object') {
    throw new Error(
      `Unexpected CAP challenge payload: ${JSON.stringify(challengePayload).slice(0, 240)}`
    );
  }

  const count = Number(challenge.c || 0);
  const saltLength = Number(challenge.s || 0);
  const targetLength = Number(challenge.d || 0);
  if (
    !Number.isInteger(count) ||
    !Number.isInteger(saltLength) ||
    !Number.isInteger(targetLength) ||
    count <= 0 ||
    saltLength <= 0 ||
    targetLength <= 0
  ) {
    throw new Error(`Invalid CAP challenge dimensions: ${JSON.stringify(challenge)}`);
  }

  const pairs = [];
  for (let idx = 1; idx <= count; idx += 1) {
    pairs.push([
      capExpandHex(`${token}${idx}`, saltLength),
      capExpandHex(`${token}${idx}d`, targetLength),
    ]);
  }
  return { token, pairs };
}

function solvePowNonce(salt, targetHex) {
  let nonce = 0;
  while (true) {
    const digestHex = createHash('sha256').update(`${salt}${nonce}`, 'utf8').digest('hex');
    if (digestHex.startsWith(targetHex)) {
      return nonce;
    }
    nonce += 1;
  }
}

async function solveCapTokenFromEndpoint(page, endpoint) {
  const endpointUrl = new URL(endpoint, page.url());
  const challengeUrl = new URL('challenge', endpointUrl).toString();
  const redeemUrl = new URL('redeem', endpointUrl).toString();

  const challengeResponse = await page.request.post(challengeUrl, { headers: {} });
  if (!challengeResponse.ok()) {
    throw new Error(
      `CAP challenge failed: ${challengeResponse.status()} ${challengeResponse.statusText()}`
    );
  }
  const challengePayload = await challengeResponse.json();
  const { token, pairs } = buildCapPairs(challengePayload);
  const solutions = pairs.map(([salt, targetHex]) => solvePowNonce(salt, targetHex));

  const redeemResponse = await page.request.post(redeemUrl, {
    headers: {},
    data: { token, solutions },
  });
  if (!redeemResponse.ok()) {
    throw new Error(`CAP redeem failed: ${redeemResponse.status()} ${redeemResponse.statusText()}`);
  }
  const redeemPayload = await redeemResponse.json();
  const capToken = String(redeemPayload && redeemPayload.token ? redeemPayload.token : '').trim();
  if (!capToken || !redeemPayload.success) {
    throw new Error(
      `CAP redeem did not return a success token: ${JSON.stringify(redeemPayload).slice(0, 240)}`
    );
  }
  return capToken;
}


async function login(page) {
  const pairs = Object.fromEntries(fs.readFileSync(path.join(repo, 'docker/secrets/dev-agent.env'), 'utf8')
    .split('\n').filter((s) => s.includes('=') && !s.startsWith('#')).map((line) => {
      const i = line.indexOf('='); return [line.slice(0,i), line.slice(i+1).trim().replace(/^["']|["']$/g,'')];
    }));
  await page.goto(base + '/weppcloud/login');
  await page.locator('input[name="email"]').fill(pairs.DEV_AGENT_EMAIL);
  await page.locator('input[name="password"]').fill(pairs.DEV_AGENT_PASSWORD);
  const cap = page.locator('cap-widget[data-cap-api-endpoint]');
  if (await cap.count()) {
    const token = await solveCapTokenFromEndpoint(page, await cap.getAttribute('data-cap-api-endpoint'));
    await page.locator('input[name="cap_token"]').evaluate((input, value) => {input.value=value;}, token);
  }
  await Promise.all([page.waitForURL((url) => !url.pathname.endsWith('/login')),
    page.locator('input[type="submit"], button[type="submit"]').first().click()]);
}


const checks = {};
const tokens = new Set();
const sockets = new Map();
const messages = [];
const consoleText = [];
const runs = [];
const since = new Date().toISOString();
let stage = 'launch';
function check(name, value) { checks[name] = Boolean(value); if (!value) throw new Error('acceptance assertion: ' + name); }
async function until(predicate, name, timeout = 30000) {
    const end = Date.now() + timeout;
    while (Date.now() < end) { if (await predicate()) return; await new Promise(resolve => setTimeout(resolve, 200)); }
    throw new Error('acceptance timeout: ' + name);
}
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();
page.on('console', msg => consoleText.push(msg.text()));
page.on('pageerror', error => consoleText.push(error.message));
const cdp = await context.newCDPSession(page);
await cdp.send('Network.enable');
cdp.on('Network.webSocketCreated', event => sockets.set(event.requestId, { url: event.url }));
cdp.on('Network.webSocketWillSendHandshakeRequest', event => {
    const socket = sockets.get(event.requestId); if (!socket) return;
    const entry = Object.entries(event.request.headers).find(([key]) => key.toLowerCase() === 'sec-websocket-protocol');
    const protocols = String(entry?.[1] || '').split(',').map(s => s.trim());
    socket.fixed = protocols.includes('wepp-stream.v1');
    const bearer = protocols.find(s => s.startsWith('bearer.'));
    if (bearer) {
        const token = bearer.slice(7); tokens.add(token);
        try {
            const claims = JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString());
            socket.claims = {runid: claims.runid, config: claims.config, aud: claims.aud, scope: claims.scope,
                lifetime: claims.exp - claims.iat, service: claims.stream};
        } catch { socket.invalidClaims = true; }
    }
});
cdp.on('Network.webSocketHandshakeResponseReceived', event => {
    const socket = sockets.get(event.requestId); if (!socket) return;
    socket.status = event.response.status;
    socket.selected = Object.entries(event.response.headers).find(([key]) => key.toLowerCase() === 'sec-websocket-protocol')?.[1] || '';
});
cdp.on('Network.webSocketFrameReceived', event => {
    const socket = sockets.get(event.requestId); if (!socket) return;
    try { messages.push({ url: socket.url, body: JSON.parse(event.response.payloadData) }); } catch { /* control frame */ }
});
async function createPrivateRun() {
    await page.goto(base + '/weppcloud/create');
    const form = page.locator('form.wc-run-form').filter({ has: page.locator('input[name="config"][value="0"]') }).first();
    await Promise.all([page.waitForURL(/\/weppcloud\/runs\/[^/]+\/0\//), form.locator('button').click()]);
    const runid = new URL(page.url()).pathname.split('/')[3];
    runs.push({ runid, config: '0' });
    // Persist only disposable identities so interrupted acceptance can be cleaned up.
    fs.writeFileSync('/tmp/stream-auth-disposable-runs.json', JSON.stringify(runs));
    await page.waitForFunction(() => Boolean(window.WCHttp?.createStreamConnection));
    const status = await page.evaluate(async ({runid, config}) => {
        const result = await window.WCHttp.postJson('/weppcloud/runs/' + runid + '/' + config + '/tasks/set_public', {public:false});
        return result.status;
    }, runs.at(-1));
    check('private-state-' + runs.length, status === 200);
    return runs.at(-1);
}
let failure = false;
try {
    stage = 'login'; await login(page);
    stage = 'create-private-runs';
    const a = await createPrivateRun();
    const b = await createPrivateRun();
    stage = 'authorized-streams';
    await page.goto(base + '/weppcloud/runs/' + a.runid + '/' + a.config + '/');
    await until(() => [...sockets.values()].some(s => s.claims?.runid === a.runid && s.claims?.service === 'preflight' && s.status === 101), 'preflight handshake');
    await until(() => [...sockets.values()].some(s => s.claims?.runid === a.runid && s.url.includes(':wepp?') && s.status === 101), 'status handshake');
    for (const service of ['status','preflight']) {
        const selected = [...sockets.values()].filter(s => s.claims?.runid === a.runid && s.claims?.service === service && s.status === 101);
        check(service + '-valid-handshake', selected.length > 0 && selected.every(s => s.fixed && s.selected === 'wepp-stream.v1'
            && s.claims.config === a.config && s.claims.aud === 'wepp-' + service && s.claims.scope === service + ':read' && s.claims.lifetime === 300));
    }
    check('token-free-urls', [...sockets.values()].every(s => [...tokens].every(token => !s.url.includes(token)) && !/[?&](token|jwt|authorization)=/i.test(s.url)));
    await until(() => messages.some(m => m.url.includes('/preflight/' + a.runid) && m.body.type === 'preflight'), 'preflight payload');
    check('actual-preflight-payload', true);
    const marker = 'STREAM_AUTH_ACCEPTANCE_' + randomUUID();
    const publish = `import json,sys
from redis import Redis
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
r,m=json.loads(sys.stdin.read())
with Redis(**redis_connection_kwargs(RedisDB.STATUS)) as c: print(c.publish(r+':wepp',m))
`;
    execFileSync('wctl', ['exec','-T','weppcloud','python','-c',publish], {input:JSON.stringify([a.runid,marker]),stdio:['pipe','pipe','pipe']});
    await until(() => messages.some(m => m.url.includes('/status/' + a.runid + ':wepp') && m.body.type === 'status' && m.body.data === marker), 'status marker');
    check('actual-status-marker', true);
    stage = 'negative-connections';
    for (const service of ['status','preflight']) {
        for (const crossRun of [false,true]) {
            const result = await page.evaluate(async ({a,b,service,crossRun}) => {
                const credential = crossRun ? await window.WCHttp.getStreamToken(a.runid,a.config,service) : null;
                const url = 'wss://' + location.host + '/weppcloud-microservices/' + service + '/' + b.runid + (service === 'status' ? ':wepp' : '') + '?config=' + b.config;
                return await new Promise(resolve => {
                    const ws = new WebSocket(url, credential ? ['wepp-stream.v1','bearer.'+credential.token] : ['wepp-stream.v1']);
                    let opened=false, received=0;
                    const timer=setTimeout(()=>{ws.close();resolve({opened,received,closed:false});},5000);
                    ws.onopen=()=>{opened=true;}; ws.onmessage=()=>{received++;}; ws.onerror=()=>{};
                    ws.onclose=()=>{clearTimeout(timer);resolve({opened,received,closed:true});};
                });
            }, {a,b,service,crossRun});
            check(service + (crossRun ? '-cross-run-denied' : '-missing-token-denied'), result.closed && !result.opened && result.received===0);
        }
    }
    const anonymous = await browser.newContext();
    for (const run of runs) {
        const response=await anonymous.request.post(base+'/rq-engine/api/runs/'+run.runid+'/'+run.config+'/stream-token', {headers:{Origin:base},data:{service:'status'}});
        check('anonymous-private-denied-' + run.runid, response.status()===403);
    }
    await anonymous.close();
    stage = 'credential-non-retention';
    const storage = await page.evaluate(() => JSON.stringify({local:{...localStorage},session:{...sessionStorage}}));
    const logs = ['weppcloud','wepppy-rq-engine','weppcloud-status','weppcloud-preflight','wepppy-caddy'].map(name => {
        const result = spawnSync('docker',['logs','--since',since,name],{encoding:'utf8',stdio:['ignore','pipe','pipe'],maxBuffer:16*1024*1024});
        check('log-read-' + name, result.status === 0);
        return result.stdout + result.stderr;
    }).join('\n');
    const retained = storage + consoleText.join('\n') + logs + JSON.stringify([...sockets.values()].map(s=>s.selected));
    check('no-raw-credential-in-storage-console-logs-selected-protocol', [...tokens].every(token=>!retained.includes(token)));
    const artifactText=fs.readdirSync(artifact).filter(name=>name.endsWith('.md')||name.endsWith('.json')).map(name=>fs.readFileSync(path.join(artifact,name),'utf8')).join('\n');
    check('no-raw-credential-in-retained-artifacts', [...tokens].every(token=>!artifactText.includes(token)));
} catch {
    failure = true; // Never print an exception that could contain request credentials.
} finally {
    await context.close();
    await browser.close();
    let cleanup = 'no disposable runs';
    if (runs.length) {
        const code=fs.readFileSync(path.join(artifact,'forest_cleanup.py'),'utf8');
        const result=spawnSync('wctl',['exec','-T','weppcloud','python','-c',code],{input:JSON.stringify(runs),encoding:'utf8',stdio:['pipe','pipe','pipe'],maxBuffer:1024*1024});
        try { if(result.status!==0)throw new Error(); cleanup=JSON.parse(result.stdout); } catch { failure=true; cleanup='FAILED; recover exact identities from /tmp/stream-auth-disposable-runs.json'; }
    }
    const receipt={at:new Date().toISOString(),since,revision:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),browser:browser.version(),stage,passed:!failure,checks,runs,cleanup};
    fs.writeFileSync(path.join(artifact,'20261111_forest_browser.json'),JSON.stringify(receipt,null,2)+'\n');
    console.log(JSON.stringify({stage,passed:!failure,checks}));
}
if(failure)process.exitCode=1;
