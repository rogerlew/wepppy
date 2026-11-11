const {chromium} = require('/home/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {execFileSync} = require('node:child_process');
const assert = require('node:assert/strict');
const repo = '/home/workdir/wepppy';
const base = 'https://forest.tail305ec9.ts.net';
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


async function login(page, supplied) {
  const pairs = supplied || Object.fromEntries(fs.readFileSync(path.join(repo, 'docker/secrets/dev-agent.env'), 'utf8')
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

(async () => {
 const manifest = JSON.parse(execFileSync('wctl',['exec','-T','weppcloud','cat','/tmp/qe-boundary-fixtures.json'], {encoding:'utf8'}));
 const browser = await chromium.launch({headless:true});
 try {
 const owner = await browser.newContext();
 const page = await owner.newPage();
 page.setDefaultTimeout(45000);
 page.on('requestfailed', r=>{if(r.url().includes('/query-engine/')) console.log('Query transport failure:',r.failure()?.errorText);});
 await login(page);
 console.log('Real password/CAP browser login: passed');
 const run = manifest.runs[0], cfg = manifest.config;
 const direct = await page.goto(`${base}/weppcloud/runs/${run}/${cfg}/`);
 assert.equal(direct.status(),200);
 const cookies = await owner.cookies(base+'/query-engine/runs/');
 const queryCookies = cookies.filter(c => c.name.startsWith('wepp_query_'));
 console.log('Direct page status/cookie count:', direct.status(), queryCookies.length);
 assert.equal(queryCookies.length,1);
 assert(queryCookies.every(c => c.httpOnly && c.secure && c.sameSite==='Lax' && c.path==='/query-engine/runs/'));
 assert(!(await page.evaluate(()=>document.cookie)).includes(queryCookies[0].value));
 const endpoint = `/query-engine/runs/${run}/${cfg}`;
 async function fetchQuery(p, target) {
  return p.evaluate(async url => {const r=await fetch(url+'/query', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({datasets:['data/sample.parquet']})}); return {status:r.status,body:await r.json()};},target);
 }
 const result = await fetchQuery(page,endpoint);
 assert.equal(result.status,200, JSON.stringify(result.body));
 assert.deepEqual(result.body.records,[{value:3},{value:7}]);
 console.log('Owner browser query records: passed');
 const snapshot=()=>JSON.parse(execFileSync('wctl',['exec','-T','weppcloud','python','-c',
  "import json,hashlib; from pathlib import Path; m=json.loads(Path('/tmp/qe-boundary-fixtures.json').read_text()); r=Path('/wc1/runs/qe')/m['runs'][0]; paths=list((r/'_query_engine').rglob('*'))+[r/'exceptions.log']; print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}))"],{encoding:'utf8'}));
 const beforeDenial=snapshot();
 const unrelated=await browser.newContext();
 const unrelatedPage=await unrelated.newPage();
 const supplied=JSON.parse(execFileSync('wctl',['exec','-T','weppcloud','cat','/tmp/qe-boundary-unrelated.json'],{encoding:'utf8'}));
 try {await login(unrelatedPage,supplied);} catch (error) {
 console.log('Unrelated login form result:',(await unrelatedPage.locator('body').innerText()).replaceAll(supplied.DEV_AGENT_EMAIL,'[fixture email]').replaceAll(supplied.DEV_AGENT_PASSWORD,'[redacted]').slice(0,1600)); throw error;
 }
 const unrelatedEntry=await unrelatedPage.goto(`${base}/weppcloud/runs/${run}/${cfg}/`);
 assert.equal(unrelatedEntry.status(),403);
 assert.equal((await unrelated.cookies(base+'/query-engine/runs/')).filter(c=>c.name.startsWith('wepp_query_')).length,0);
 assert.equal((await fetchQuery(unrelatedPage,endpoint)).status,401);
 console.log('Unrelated real browser account denied page/query without minting cookie: passed');
 await unrelated.close();
 const anonymous=await browser.newContext();
 const anonPage=await anonymous.newPage();
 await anonPage.goto(base+'/weppcloud/login');
 const denied=await fetchQuery(anonPage,endpoint);
 assert.equal(denied.status,401);
 const publicResult=await fetchQuery(anonPage,`/query-engine/runs/${manifest.runs[100]}/${cfg}`);
 assert.equal(publicResult.status,200);
 assert.deepEqual(publicResult.body.records,[{value:3},{value:7}]);
 console.log('Anonymous private denial/public query: passed');
 const getActivation=await owner.request.get(base+endpoint+'/activate');
 assert.equal(getActivation.status(),405);
 const wrongOrigin=await owner.request.post(base+endpoint+'/activate',{headers:{Origin:'https://hostile.invalid'}});
 assert.equal(wrongOrigin.status(),403);
 assert.deepEqual(snapshot(),beforeDenial);
 console.log('Denied requests left catalog/log SHA256 manifest unchanged:',Object.keys(beforeDenial).length);
 const activation=await page.evaluate(async url=>{const r=await fetch(url+'/activate',{method:'POST'});return r.status;},endpoint);
 assert.equal(activation,200);
 console.log('POST activation and origin boundaries: passed');
 const chunks=Number(process.env.QE_COLLECTION_CHUNKS || '1');
 for(let i=0;i<chunks;i++) {
 const ws=manifest.runs.slice(i*100/chunks,(i+1)*100/chunks).map(runid=>({runid}));
 const collection=await page.goto(base+'/weppcloud/bounds_ws_viewer?'+new URLSearchParams({ws:JSON.stringify(ws)}));
 if(collection.status()!==200) console.log('Collection failure:',collection.status(),(await collection.text()).slice(0,500));
 assert.equal(collection.status(),200);
 console.log('Collection page admitted:',ws.length);
 }
 const all=(await owner.cookies(base+'/query-engine/runs/')).filter(c=>c.name.startsWith('wepp_query_'));
 console.log('Total collection query cookie count:',all.length);
 assert.equal(all.length,100);
 console.log('100-cookie bytes before query:',all.reduce((n,c)=>n+c.name.length+c.value.length+2,0));
 const last=await fetchQuery(page,`/query-engine/runs/${manifest.runs[99]}/${cfg}`);
 assert.equal(last.status,200,JSON.stringify(last.body));
 assert.deepEqual(last.body.records,[{value:3},{value:7}]);
 console.log('100-cookie request through Caddy accepted; total query cookie bytes:',all.reduce((n,c)=>n+c.name.length+c.value.length+2,0));
 await anonymous.close(); await owner.close();
 } finally {await browser.close();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
