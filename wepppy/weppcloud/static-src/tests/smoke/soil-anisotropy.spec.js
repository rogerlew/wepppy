import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const base = process.env.SMOKE_BASE_URL || 'https://wc.bearhive.duckdns.org';
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

async function setReadonly(page, state) {
  const toggle = page.locator('[data-project-toggle="readonly"]');
  await toggle.evaluate((input) => {
    for (let node = input.parentElement; node; node = node.parentElement) {
      if (node.tagName === 'DETAILS') node.open = true;
    }
  });
  if (await toggle.isChecked() === state) return;
  const responsePromise = page.waitForResponse((response) => response.url().endsWith('/tasks/set_readonly'));
  await toggle.setChecked(state);
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const body = await response.json();
  const jobId = body.Content.job_id;
  // READONLY builds/removes a manifest asynchronously. Wait before reversing it.
  await expect.poll(() => page.evaluate(async (id) => {
    const result = await window.WCHttp.requestWithSessionToken('/rq-engine/api/jobstatus/' + id);
    return result.body.status;
  }, jobId), {timeout:60000}).toBe('finished');
}

test('soil anisotropy forest acceptance', async ({ page }) => {
  test.skip(process.env.SMOKE_SOIL_ANISOTROPY !== 'true', 'Requires the disposable SA-01 forest fixture.');
  test.setTimeout(240000);
  await login(page);
  const runPath = '/weppcloud/runs/sa-anisotropy-validation/disturbed9002/';
  const response = await page.goto(base + runPath + '?skip_migration_check=true');
  expect(response.status()).toBe(200);
  await setReadonly(page, false);
  const upper = page.locator('#soil_anisotropy_upper');
  const lower = page.locator('#soil_anisotropy_lower');
  await expect(upper).toHaveValue('25.0');
  await expect(lower).toHaveValue('3.0');
  await upper.evaluate((input) => {
    for (let node = input.parentElement; node; node = node.parentElement) {
      if (node.tagName === 'DETAILS') node.open = true;
    }
  });
  await expect(upper).toBeVisible();
  await expect(upper).toBeEditable();
  await expect(page.locator('[data-wepp-anisotropy]')).toContainText('Values above 10 can cause numerical instabilities.');
  await upper.fill('30.5');
  await lower.fill('4');
  let payload;
  // Exercise the actual Run button/serializer but never enqueue a model in this smoke.
  await page.route('**/rq-engine/api/runs/**/run-wepp', async (route) => {
    payload = route.request().postDataJSON();
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({message:'Validation transport intercepted; no model queued.'})});
  });
  await page.locator('#btn_run_wepp').click();
  await expect.poll(() => payload).toBeTruthy();
  expect(Number(payload.soil_anisotropy_upper)).toBe(30.5);
  expect(Number(payload.soil_anisotropy_lower)).toBe(4);
  const hourly = page.locator('#checkbox_hourly_seepage');
  await page.locator('#wepp_hourly_seepage').evaluate((node) => {node.open=true;});
  await hourly.uncheck();
  await expect(hourly).toBeEnabled();
  await expect(upper).toBeDisabled();
  await expect(lower).toBeDisabled();
  await page.reload();
  await expect(upper).toBeDisabled();
  await expect(upper).toHaveValue('25.0');
  await hourly.evaluate((input) => {
    for (let node = input.parentElement; node; node = node.parentElement) {
      if (node.tagName === 'DETAILS') node.open = true;
    }
  });
  await hourly.check();
  await expect(upper).toBeEnabled();
  await upper.evaluate((input) => {input.closest('details').open=true;});
  try {
    await setReadonly(page, true);
    await expect(upper).not.toBeEditable();
  } finally {
    await setReadonly(page, false);
  }
  await expect(upper).toBeEditable();
  await page.locator('[data-project-toggle="readonly"]').evaluate((input) => {
    input.closest('details').open = false;
  });
  await page.locator('#wepp_soil_options').screenshot({path:'/tmp/sa-soil-options.png'});
  const artifact = await page.request.get(base + runPath + 'download/wepp/runs/p1.sol');
  expect(artifact.status()).toBe(200);
  const bytes = await artifact.body();
  const receipt = JSON.parse(fs.readFileSync(path.join(repo,'docs/work-packages/20261012_soil_anisotropy/artifacts/forest-validation.json'),'utf8'));
  expect(createHash('sha256').update(bytes).digest('hex')).toBe(receipt.prepared_sha256);
  await page.goto(base+'/weppcloud/runs/grating-implementation/disturbed9002/?skip_migration_check=true');
  await expect(page.locator('#soil_anisotropy_upper')).toBeDisabled();
  console.log('SA-01 browser acceptance:',JSON.stringify({eligibleEditable:true,submitted:[30.5,4],hourlyDisableReload:true,readonly:true,nonMofeDisabled:true,preparedDownloadSha256:receipt.prepared_sha256,modelEnqueued:false}));
});
