import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const base = process.env.SMOKE_BASE_URL || 'https://forest.tail305ec9.ts.net';
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

test('notification inbox persists explicit read state and page selection', async ({ page }) => {
  test.skip(process.env.SMOKE_NOTIFICATIONS !== 'true', 'Requires the scoped notification acceptance fixture.');
  const evidence = path.join(repo, 'docs/work-packages/20261105_user_notifications/artifacts');
  const fixture = JSON.parse(fs.readFileSync(path.join(evidence, 'forest-fixture.json'), 'utf8'));
  await login(page);
  await page.goto(base + '/weppcloud/notifications?sort=newest');
  await expect(page.locator('[data-notification-id]')).toHaveCount(100);
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label', 'Notifications, 101 unread');
  await page.locator('[data-notification-id]').first().check();
  await Promise.all([page.waitForNavigation(), page.getByRole('button', {name:'Mark read', exact:true}).click()]);
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label', 'Notifications, 100 unread');
  await expect(page.locator('[data-notification-id]:checked')).toHaveCount(0);
  await page.locator('[data-select-all]').check();
  await Promise.all([page.waitForNavigation(), page.getByRole('button', {name:'Mark read', exact:true}).click()]);
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label', 'Notifications, 1 unread');
  await page.reload();
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label', 'Notifications, 1 unread');
  await page.locator('#notification-sort').selectOption('read_first');
  await Promise.all([page.waitForNavigation(), page.getByRole('button', {name:'Apply sort'}).click()]);
  await expect(page.locator('.wc-notifications-item .wc-text-muted').first()).toContainText('Read ·');
  await page.locator('[data-select-all]').check();
  await Promise.all([page.waitForNavigation(), page.getByRole('button', {name:'Mark unread', exact:true}).click()]);
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label', 'Notifications, 101 unread');
  await page.locator('[data-notification-id]').first().check();
  await page.getByRole('link', {name:'Next', exact:true}).click();
  await expect(page.locator('[data-notification-id]')).toHaveCount(1);
  await expect(page.locator('[data-notification-id]:checked')).toHaveCount(0);
  await page.goBack();
  await expect(page.locator('[data-notification-id]:checked')).toHaveCount(0);
  await page.setViewportSize({width:390,height:844});
  await page.goto(base + '/weppcloud/notifications');
  await expect(page.locator('[data-notification-bell]')).toBeVisible();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
  expect(overflow).toBe(false);
  await page.screenshot({path:path.join(evidence,'forest-notifications-mobile.png'),fullPage:false});
  await page.setViewportSize({width:1280,height:900});
  await page.screenshot({path:path.join(evidence,'forest-notifications-desktop.png'),fullPage:false});
  const pages=[];
  for(const route of ['/weppcloud/runs/','/weppcloud/profile',`/weppcloud/runs/${fixture.runid}/disturbed9002-10m`]) {
    const response=await page.goto(base+route);
    pages.push({route,status:response.status()});
    expect(response.status()).toBe(200);
    await expect(page.locator('[data-notification-bell]')).toBeVisible();
  }
  fs.writeFileSync(path.join(evidence,'forest-browser.json'),JSON.stringify({read_unread:true,persistence:true,pagination_100_1:true,selection_cleared:true,mobile_no_overflow:true,pages},null,2)+'\n');
});
