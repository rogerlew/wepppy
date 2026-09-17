const fs = require('node:fs');
const { createHash } = require('node:crypto');
const { chromium } = require(process.cwd() + '/wepppy/weppcloud/static-src/node_modules/playwright');
const forwardedProtoHeader = {};
function fnv32aHash(text) {
  let value = 2166136261;
  for (const char of text) {
    value ^= char.codePointAt(0);
    value = (value + (value << 1) + (value << 4) + (value << 7) + (value << 8) + (value << 24)) >>> 0;
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
  const token = String(challengePayload && challengePayload.token ? challengePayload.token : '').trim();
  const challenge = challengePayload && challengePayload.challenge;
  if (!token || !challenge || typeof challenge !== 'object') {
    throw new Error(`Unexpected CAP challenge payload: [omitted]`);
  }

  const count = Number(challenge.c || 0);
  const saltLength = Number(challenge.s || 0);
  const targetLength = Number(challenge.d || 0);
  if (!Number.isInteger(count) || !Number.isInteger(saltLength) || !Number.isInteger(targetLength)
      || count <= 0 || saltLength <= 0 || targetLength <= 0) {
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

  const challengeResponse = await page.request.post(challengeUrl, { headers: forwardedProtoHeader });
  if (!challengeResponse.ok()) {
    throw new Error(`CAP challenge failed: ${challengeResponse.status()} ${challengeResponse.statusText()}`);
  }
  const challengePayload = await challengeResponse.json();
  const { token, pairs } = buildCapPairs(challengePayload);
  const solutions = pairs.map(([salt, targetHex]) => solvePowNonce(salt, targetHex));

  const redeemResponse = await page.request.post(redeemUrl, {
    headers: forwardedProtoHeader,
    data: { token, solutions },
  });
  if (!redeemResponse.ok()) {
    throw new Error(`CAP redeem failed: ${redeemResponse.status()} ${redeemResponse.statusText()}`);
  }
  const redeemPayload = await redeemResponse.json();
  const capToken = String(redeemPayload && redeemPayload.token ? redeemPayload.token : '').trim();
  if (!capToken || !redeemPayload.success) {
    throw new Error(`CAP redeem did not return a success token: [omitted]`);
  }
  return capToken;
}

async function completeLoginCapIfPresent(page, loginForm) {
  const capTokenInput = loginForm.locator('input[name="cap_token"]');
  if ((await capTokenInput.count()) === 0) {
    return { verified: true, reason: 'Login form has no CAP token field.' };
  }

  const existingToken = await capTokenInput.first().inputValue().catch(() => '');
  if (existingToken) {
    return { verified: true, reason: 'Login CAP token already present.' };
  }

  const capWidget = loginForm.locator('cap-widget[data-cap-api-endpoint]').first();
  if ((await capWidget.count()) === 0) {
    return { verified: false, reason: 'Login form has CAP token field but no CAP widget endpoint.' };
  }

  try {
    const endpoint = await capWidget.getAttribute('data-cap-api-endpoint');
    if (!endpoint) {
      return { verified: false, reason: 'Login CAP widget endpoint is empty.' };
    }
    const capToken = await solveCapTokenFromEndpoint(page, endpoint);
    await capTokenInput.first().evaluate((input, token) => {
      input.value = token;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }, capToken);
  } catch (err) {
    return {
      verified: false,
      reason: `Login CAP challenge did not produce a token (${err && err.message ? err.message : err}).`,
    };
  }
  return { verified: true, reason: 'Login CAP challenge completed.' };
}


(async () => {
  const credentials = Object.fromEntries(fs.readFileSync('docker/secrets/dev-agent.env','utf8')
    .split(/\r?\n/).filter(line => line.includes('=') && !line.trim().startsWith('#'))
    .map(line => {const pos=line.indexOf('=');return [line.slice(0,pos).trim(),line.slice(pos+1).trim().replace(/^['"]|['"]$/g,'')];}));
  const host='https://wc.bearhive.duckdns.org';
  const browser=await chromium.launch({headless:true});
  try {
    const context=await browser.newContext();
    const page=await context.newPage();
    await page.goto(host+'/weppcloud/login',{waitUntil:'domcontentloaded'});
    const form=page.locator('form[name="login_user_form"]');
    await form.locator('input[name="email"]').fill(credentials.DEV_AGENT_EMAIL);
    await form.locator('input[name="password"]').fill(credentials.DEV_AGENT_PASSWORD);
    const result=await completeLoginCapIfPresent(page,form);
    if(!result.verified) throw Error(result.reason);
    await Promise.all([page.waitForURL(url => !url.pathname.endsWith('/login')),form.locator('[type="submit"]').first().click()]);
    await page.goto(host+'/weppcloud/profile',{waitUntil:'domcontentloaded'});
    const csrf=await page.locator('meta[name="csrf-token"]').getAttribute('content');
    const minted=await context.request.post(host+'/weppcloud/profile/mint-token',{headers:{'X-CSRFToken':csrf}});
    if(!minted.ok()) throw Error('Token mint HTTP '+minted.status());
    const data=await minted.json();
    const token=(data.Content||data.content||data.success||{}).token;
    if(!token) throw Error('Token missing; body omitted');
    const cookies=Object.fromEntries((await context.cookies()).map(item=>[item.name,item.value]));
    const target='/tmp/wepppy-freshness-runtime-auth.json';
    fs.writeFileSync(target,JSON.stringify({host,token,cookies}),{mode:0o600});
    fs.chmodSync(target,0o600);
    const state='/tmp/wepppy-freshness-browser-state.json';
    fs.writeFileSync(state,JSON.stringify(await context.storageState()),{mode:0o600});
    console.log('Browser CAP login and token mint passed; secrets retained privately.');
    for(const name of ['configs','endpoints']) {
      const response=await context.request.get(host+'/rq-engine/api/'+name,{headers:{Authorization:'Bearer '+token}});
      if(!response.ok()) throw Error(name+' HTTP '+response.status());
      fs.writeFileSync(__dirname+'/runtime_discovery_'+name+'.json',JSON.stringify(await response.json(),null,2)+'\n');
      console.log(name,response.status());
    }
  } finally {await browser.close();}
})().catch(err=>{console.error(err.message);process.exitCode=1;});
