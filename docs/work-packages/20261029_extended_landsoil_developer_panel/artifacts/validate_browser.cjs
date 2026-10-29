// Local DM-02 acceptance; uses the existing smoke account without changing roles.
const fs = require('fs');
const path = require('path');
const {createHash} = require('crypto');
const assert = require('node:assert/strict');
const repo = path.resolve(__dirname, '../../../..');
const {chromium} = require(path.join(repo, 'wepppy/weppcloud/static-src/node_modules/playwright'));
const base = 'https://wc.bearhive.duckdns.org';
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


(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
    await login(page);
    const receipt = {identity: 'existing smoke account; no account or role mutations', layouts: {}};
    for (const [project, full] of [['base', false], ['legacy', true], ['developer', true]]) {
      const url = `${base}/weppcloud/runs/d2-landsoil-${project}/disturbed9002/?skip_migration_check=true`;
      const response = await page.goto(url, {waitUntil: 'domcontentloaded'});
      assert.equal(response.status(), 200);
      const modal = page.locator('#disturbedModal');
      await modal.waitFor({state: 'attached'});
      assert.equal(await modal.locator('[data-disturbed-action]').count(), full ? 4 : 1);
      assert.equal(await modal.locator('[data-disturbed-modify-link]').count(), full ? 2 : 1);
      assert.equal(await modal.locator('[data-disturbed-lookup-variant]').count(), full ? 2 : 0);
      await page.locator('summary').filter({hasText: /^\s*More\s*$/}).click();
      await page.locator('[data-modal-open="disturbedModal"]').click();
      await modal.waitFor({state: 'visible'});
      await modal.screenshot({path: path.join(__dirname, `panel-${project}.png`)});
      const link = modal.locator('[data-disturbed-modify-link="base"]');
      const editor = await page.request.get(new URL(await link.getAttribute('href'), page.url()).href);
      assert.equal(editor.status(), 200);
      const helpStatuses = [];
      for (const href of await modal.locator('.disturbed-panel__help-link a').evaluateAll(links => links.map(a => a.href))) {
        const help = await page.request.get(href);
        assert.equal(help.status(), 200);
        helpStatuses.push(help.status());
      }
      receipt.layouts[project] = {full, editorStatus: editor.status(), helpStatuses, screenshot: `panel-${project}.png`};
    }
    await page.goto(`${base}/weppcloud/runs/d2-landsoil-legacy/disturbed9002/?skip_migration_check=true`);
    await page.locator('summary').filter({hasText: /^\s*More\s*$/}).click();
    await page.locator('[data-modal-open="disturbedModal"]').click();
    await page.waitForFunction(() => document.querySelector('#disturbed_lookup_variant_extended').checked);
    const selection = page.waitForResponse(response => response.url().endsWith('/tasks/set_lookup_variant'));
    await page.locator('#disturbed_lookup_variant_base').check();
    assert.equal((await selection).status(), 200);
    assert.equal(await page.locator('#disturbedModal [data-disturbed-action]').count(), 4);
    await page.reload();
    assert.equal(await page.locator('#disturbedModal [data-disturbed-action]').count(), 1);
    receipt.transition = 'legacy project: Base selection retains full current DOM; reload renders simple panel';
    fs.writeFileSync(path.join(__dirname, 'browser.json'), JSON.stringify(receipt, null, 2)+'\n');
    console.log(JSON.stringify(receipt));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
