/* eslint-env node */
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
  for (;;) {
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


async function login(page, credentialFile = process.env.SMOKE_AGENT_CREDENTIALS_FILE || 'docker/secrets/dev-agent.env') {
  const pairs = Object.fromEntries(fs.readFileSync(path.resolve(repo, credentialFile), 'utf8')
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
  await Promise.all([page.waitForNavigation({timeout:30_000}),
    page.locator('input[type="submit"], button[type="submit"]').first().click()]);
  const messages=await page.locator('.pure-form-message-inline, [role="alert"]').allTextContents();
  await expect(page, messages.join(' ')).not.toHaveURL(/\/login$/, {timeout:5000});
}

test('notification inbox persists explicit read state and page selection', async ({ page }) => {
  test.skip(process.env.SMOKE_NOTIFICATIONS !== 'true', 'Requires the scoped notification acceptance fixture.');
  test.setTimeout(180_000);
  const evidence = path.resolve(repo, process.env.SMOKE_NOTIFICATION_EVIDENCE_DIR || 'docs/work-packages/20261105_user_notifications/artifacts');
  const fixture = JSON.parse(fs.readFileSync(path.join(evidence, 'forest-fixture.json'), 'utf8'));
  await login(page);
  await page.goto(base + '/weppcloud/profile');
  await page.locator('[data-notification-bell]').focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/notifications$/);
  await page.goto(base + '/weppcloud/notifications?sort=newest');
  await expect(page.locator('[data-notification-id]')).toHaveCount(100);
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label', 'Notifications, 101 unread');
  await page.locator('[data-notification-id]').first().check();
  await Promise.all([page.waitForNavigation(), page.getByRole('button', {name:'Mark read', exact:true}).click()]);
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label', 'Notifications, 100 unread');
  await expect(page.locator('[data-notification-id]:checked')).toHaveCount(0);
  await page.goto(base + '/weppcloud/logout');
  await login(page);
  await page.goto(base + '/weppcloud/notifications?sort=newest');
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label', 'Notifications, 100 unread');
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
  await page.route('**/api/notifications/read-state', (route) => route.fulfill({status:503,contentType:'application/json',body:'{}'}));
  await page.locator('[data-notification-id]').first().check();
  await page.getByRole('button', {name:'Mark read', exact:true}).click();
  await expect(page.locator('[data-notification-error]')).toBeVisible();
  await expect(page.locator('[data-notification-id]:checked')).toHaveCount(1);
  await page.unroute('**/api/notifications/read-state');
  await page.route('**/api/notifications/unread-count', (route) => route.fulfill({status:503,contentType:'application/json',body:'{}'}));
  await page.reload();
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label', 'Notifications, unread count unavailable');
  await page.unroute('**/api/notifications/unread-count');
  await page.setViewportSize({width:390,height:844});
  await page.goto(base + '/weppcloud/notifications');
  await expect(page.locator('[data-notification-bell]')).toBeVisible();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
  if (overflow) {
    const details=await page.evaluate(() => Array.from(document.querySelectorAll('*')).filter(el => el.getBoundingClientRect().right > window.innerWidth + 1).map(el => ({tag:el.tagName,classes:el.className,right:el.getBoundingClientRect().right,width:el.getBoundingClientRect().width})).slice(0,15));
    fs.writeFileSync(path.join(evidence,'forest-mobile-overflow.json'),JSON.stringify(details,null,2));
    await page.screenshot({path:path.join(evidence,'forest-mobile-overflow.png')});
  }
  expect(overflow).toBe(false);
  await page.screenshot({path:path.join(evidence,'forest-notifications-mobile.png'),fullPage:false});
  await page.setViewportSize({width:1280,height:900});
  await page.screenshot({path:path.join(evidence,'forest-notifications-desktop.png'),fullPage:false});
  await page.evaluate(() => localStorage.setItem('wc-theme', 'cursor-dark-midnight'));
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'cursor-dark-midnight');
  await expect(page.locator('[data-notification-bell]')).toBeVisible();
  await page.screenshot({path:path.join(evidence,'forest-notifications-dark.png'),fullPage:false});
  await page.evaluate(() => localStorage.removeItem('wc-theme'));
  const pages=[];
  for(const route of ['/weppcloud/runs/','/weppcloud/profile',`/weppcloud/runs/${fixture.runid}/disturbed9002-10m`,
    `/weppcloud/runs/${fixture.runid}/disturbed9002-10m/gl-dashboard`,
    `/weppcloud/runs/${fixture.runid}/disturbed9002-10m/storm-event-analyzer`]) {
    const response=await page.goto(base+route);
    pages.push({route,status:response.status()});
    expect(response.status()).toBe(200);
    await expect(page.locator('[data-notification-bell]')).toBeVisible();
    await page.setViewportSize({width:390,height:844});
    const headerBounds=await page.locator('header [data-notification-bell], header [data-theme-select]').evaluateAll(elements => elements.map(element => ({right:element.getBoundingClientRect().right,left:element.getBoundingClientRect().left})));
    pages[pages.length-1].mobile_header_bounds=headerBounds;
    fs.writeFileSync(path.join(evidence,'forest-header-bounds.json'),JSON.stringify(pages,null,2)+'\n');
    expect(headerBounds.every(bounds => bounds.left>=0 && bounds.right<=390)).toBe(true);
    await page.setViewportSize({width:1280,height:900});
  }
  const anonymous = await page.context().browser().newContext();
  const anonymousPage = await anonymous.newPage();
  let privateFetches = 0;
  anonymousPage.on('request', request => {if(request.url().includes('/api/notifications/')) privateFetches += 1;});
  await anonymousPage.goto(base + '/weppcloud/login');
  await expect(anonymousPage.locator('[data-notification-bell]')).toHaveCount(0);
  expect(privateFetches).toBe(0);
  await anonymous.close();
  const ordinary = await page.context().browser().newContext();
  const ordinaryPage = await ordinary.newPage();
  await login(ordinaryPage, process.env.SMOKE_NOTIFICATION_SECONDARY_CREDENTIALS_FILE || 'docker/secrets/notifications-acceptance.env');
  await ordinaryPage.goto(base + '/weppcloud/notifications');
  await expect(ordinaryPage.getByText('No notifications on this page.')).toBeVisible();
  await expect(ordinaryPage.locator('[data-notification-bell]')).toHaveAttribute('aria-label', 'Notifications, 0 unread');
  await expect(ordinaryPage.locator('[data-notification-count]')).toBeHidden();
  const foreignStatus = await ordinaryPage.evaluate(async (identifier) => {
    const response=await fetch('/weppcloud/api/notifications/read-state', {
      method:'POST', headers:{'Content-Type':'application/json', 'X-CSRFToken':document.querySelector('meta[name="csrf-token"]').content},
      body:JSON.stringify({notification_ids:[identifier],read:true})
    });
    return response.status;
  }, fixture.notice_ids[0]);
  expect(foreignStatus).toBe(404);
  const unchanged = await page.request.get(base + '/weppcloud/api/notifications/unread-count');
  expect((await unchanged.json()).Content.unread_count).toBe(101);
  await ordinary.close();
  fs.writeFileSync(path.join(evidence,'forest-browser.json'),JSON.stringify({read_unread:true,persistence:true,logout_login_persistence:true,keyboard_bell:true,dark_theme:true,failure_preserves_selection:true,count_failure_explicit:true,anonymous_no_private_fetch:true,ordinary_account_empty_and_isolated:true,pagination_100_1:true,selection_cleared:true,mobile_no_overflow:true,pages},null,2)+'\n');
});

test('notification history distinguishes resolved and unavailable states', async ({ page }) => {
  test.skip(process.env.SMOKE_NOTIFICATIONS_HISTORY !== 'true', 'Requires the scoped history acceptance fixture.');
  const evidence = path.resolve(repo, process.env.SMOKE_NOTIFICATION_EVIDENCE_DIR || 'docs/work-packages/20261105_user_notifications/artifacts');
  const fixture = JSON.parse(fs.readFileSync(path.join(evidence, 'forest-fixture.json'), 'utf8'));
  await login(page);
  await page.goto(base + '/weppcloud/notifications?sort=newest&page=2');
  const resolved = page.locator('.wc-notifications-item').filter({has:page.locator(`[data-notification-id="${fixture.notice_ids[0]}"]`)});
  await expect(resolved).toContainText('Resolved');
  await page.goto(base + '/weppcloud/notifications?sort=newest');
  const unavailable = page.locator('.wc-notifications-item').filter({has:page.locator(`[data-notification-id="${fixture.notice_ids[1]}"]`)});
  await expect(unavailable).toContainText('Status unavailable');
  await expect(unavailable).toContainText('This does not mean your project is protected.');
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label', 'Notifications, 99 unread');
  fs.writeFileSync(path.join(evidence,'forest-history-browser.json'),JSON.stringify({resolved_history:true,unavailable_history:true,active_unread_count:99},null,2)+'\n');
});

test('notification fixture pages remain usable without inbox activation', async ({ page }) => {
  test.skip(process.env.SMOKE_NOTIFICATIONS_BASELINE !== 'true', 'Only for application rollback acceptance.');
  test.setTimeout(180_000);
  const evidence = path.resolve(repo, process.env.SMOKE_NOTIFICATION_EVIDENCE_DIR || 'docs/work-packages/20261105_user_notifications/artifacts');
  const fixture = JSON.parse(fs.readFileSync(path.join(evidence, 'forest-fixture.json'), 'utf8'));
  await login(page);
  const pages=[];
  for(const route of ['/weppcloud/profile', `/weppcloud/runs/${fixture.runid}/disturbed9002-10m/`,
    `/weppcloud/runs/${fixture.runid}/disturbed9002-10m/gl-dashboard`,
    `/weppcloud/runs/${fixture.runid}/disturbed9002-10m/storm-event-analyzer`]) {
    const response=await page.goto(base+route);
    pages.push({route,status:response.status()});
    expect(response.status()).toBe(200);
    await expect(page.locator('[data-notification-bell]')).toHaveCount(0);
  }
  const response=await page.request.get(base+'/weppcloud/notifications');
  expect(response.status()).toBe(404);
  fs.writeFileSync(path.join(evidence,'forest-baseline-browser.json'),JSON.stringify({inbox_status:404,bell_absent:true,pages},null,2)+'\n');
});

test('scheduled notification output reaches the authenticated inbox', async ({ page }) => {
  test.skip(process.env.SMOKE_NOTIFICATIONS_SCHEDULED !== 'true', 'Requires a completed actual scheduled sweep.');
  const evidence = path.resolve(repo, process.env.SMOKE_NOTIFICATION_EVIDENCE_DIR || 'docs/work-packages/20261105_user_notifications/artifacts');
  const readback = JSON.parse(fs.readFileSync(path.join(evidence, 'forest-scheduled-readback.json'), 'utf8'));
  await login(page);
  await page.goto(base + '/weppcloud/notifications?sort=read_first');
  const notice = page.locator('.wc-notifications-item').filter({has:page.locator(`[data-notification-id="${readback.fixture_notification_id}"]`)});
  await expect(notice).toContainText('Read · Active');
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label', `Notifications, ${readback.fixture_user_unread_count} unread`);
  fs.writeFileSync(path.join(evidence,'forest-scheduled-browser.json'),JSON.stringify({job_id:readback.job_id,read_state_visible:true,active_warning_visible:true,unread_count_matches_database:true},null,2)+'\n');
});

test('notification fixture cleanup leaves a healthy empty inbox', async ({ page }) => {
  test.skip(process.env.SMOKE_NOTIFICATIONS_CLEANUP !== 'true', 'Only immediately after scoped acceptance cleanup.');
  const evidence = path.resolve(repo, process.env.SMOKE_NOTIFICATION_EVIDENCE_DIR || 'docs/work-packages/20261105_user_notifications/artifacts');
  const cleanup = JSON.parse(fs.readFileSync(path.join(evidence, 'forest-cleanup.json'), 'utf8'));
  expect(cleanup.nonfixture_notifications_retained).toBe(0);
  await login(page);
  await page.goto(base + '/weppcloud/notifications');
  await expect(page.getByText('No notifications on this page.')).toBeVisible();
  await expect(page.locator('[data-notification-bell]')).toHaveAttribute('aria-label','Notifications, 0 unread');
  await expect(page.locator('[data-notification-count]')).toBeHidden();
  const anonymous = await page.context().browser().newContext();
  const count = await anonymous.request.get(base + '/weppcloud/api/notifications/unread-count');
  expect(count.status()).toBe(401);
  const csrf = await anonymous.request.post(base + '/weppcloud/api/notifications/read-state', {data:{notification_ids:[1],read:true}});
  expect(csrf.status()).toBe(400);
  expect((await csrf.json()).error.code).toBe('csrf_failed');
  await anonymous.close();
  fs.writeFileSync(path.join(evidence,'forest-post-cleanup-browser.json'),JSON.stringify({empty_inbox:true,zero_badge_hidden:true,anonymous_count_status:401,missing_csrf_status:400},null,2)+'\n');
});
