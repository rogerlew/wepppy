import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const target =
  process.env.GL_DASHBOARD_URL ||
  'https://wc.bearhive.duckdns.org/weppcloud/runs/eighty-five-synthetic/disturbed9002_wbt/gl-dashboard';

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

async function open(page) {
  const file = path.join(repo, 'docker/secrets/dev-agent.env');
  if (fs.existsSync(file)) {
    const entries = fs
      .readFileSync(file, 'utf8')
      .split('\n')
      .filter((line) => line.includes('=') && !line.startsWith('#'));
    const values = Object.fromEntries(
      entries.map((line) => {
        const index = line.indexOf('=');
        return [
          line.slice(0, index),
          line
            .slice(index + 1)
            .trim()
            .replace(/^["']|["']$/g, ''),
        ];
      })
    );
    await page.goto(new URL('/weppcloud/login', target).href);
    const email = page.locator('input[name="email"]');
    if (await email.isVisible()) {
      await email.fill(values.DEV_AGENT_EMAIL);
      await page.locator('input[name="password"]').fill(values.DEV_AGENT_PASSWORD);
      const cap = page.locator('cap-widget[data-cap-api-endpoint]');
      if (await cap.count()) {
        const token = await solveCapTokenFromEndpoint(
          page,
          await cap.getAttribute('data-cap-api-endpoint')
        );
        await page.locator('input[name="cap_token"]').evaluate((input, value) => {
          input.value = value;
        }, token);
      }
      await Promise.all([
        page.waitForURL((url) => !url.pathname.endsWith('/login')),
        page.locator('input[type="submit"], button[type="submit"]').first().click(),
      ]);
    }
  }
  await page.goto(target, { waitUntil: 'networkidle' });
  await expect(page.locator('#graph-flow-duration')).toBeAttached();
  await page.locator('#graph-flow-duration').check({ force: true });
  await expect
    .poll(() => page.evaluate(() => window.glDashboardTimeseriesGraph?._data?.type))
    .toBe('flow-duration');
}

async function snapshot(page) {
  return page.evaluate(() => {
    const graph = window.glDashboardTimeseriesGraph;
    if (!graph?._data) return { settings: {}, series: [] };
    return {
      settings: graph._data.settings,
      series: graph._data.series.map((s) => ({
        label: s.label,
        color: s.color,
        count: s.count,
        missing: s.missing,
        start: s.start,
        end: s.end,
        error: s.error,
        max: s.points[0]?.flow,
        min: s.points.at(-1)?.flow,
        firstP: s.points[0]?.probability,
        lastP: s.points.at(-1)?.probability,
      })),
    };
  });
}

test('flow duration uses daily Omni sources, controls, hover and cached populations', async ({
  page,
}, testInfo) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const requests = [];
  page.on('request', (request) => {
    if (request.method() === 'POST' && /totalwatsed3|chanwb/.test(request.postData() || ''))
      requests.push(request.postData());
  });
  await open(page);
  const hillslope = await snapshot(page);
  expect(hillslope.settings.excludedYears).toBe(2);
  expect(hillslope.series.length).toBeGreaterThan(0);
  expect(hillslope.series.every((s) => !s.error && s.count > 0)).toBe(true);
  const beforeScale = requests.length;
  await page.locator('input[name="fdc-scale"][value="log"]').check();
  await expect.poll(async () => (await snapshot(page)).settings.scale).toBe('log');
  expect((await snapshot(page)).series).toEqual(hillslope.series);
  expect(requests.length).toBe(beforeScale);
  const canvas = page.locator('#gl-graph-canvas');
  const bounds = await canvas.boundingBox();
  await page.mouse.move(bounds.x + bounds.width * 0.6, bounds.y + bounds.height * 0.5);
  await expect(page.locator('#gl-graph-tooltip')).toContainText('m³/s');
  await expect(page.locator('#gl-graph-tooltip')).toContainText('exceedance');
  await page.getByRole('slider', { name: 'Inspect exceedance probability' }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('.gl-flow-duration-info [aria-live]')).toContainText('m³/s');
  await page.locator('input[name="fdc-source"][value="outlet"]').check();
  await expect.poll(async () => (await snapshot(page)).settings.source).toBe('outlet');
  const outlet = await snapshot(page);
  expect(outlet.series.every((s) => !s.error && s.count > 0)).toBe(true);
  await page.selectOption('#fdc-year-selection', '0');
  await expect.poll(async () => (await snapshot(page)).settings.excludedYears).toBe(0);
  const allYears = await snapshot(page);
  expect(allYears.series[0].count).toBeGreaterThan(outlet.series[0].count);
  await page.setViewportSize({ width: 1000, height: 720 });
  expect((await snapshot(page)).settings.excludedYears).toBe(0);
  await expect(page.getByLabel('Exclude rain-on-snow events')).toHaveCount(0);
  if (process.env.FDC_ORACLE_PATH) {
    const oracle = JSON.parse(fs.readFileSync(process.env.FDC_ORACLE_PATH, 'utf8'));
    for (const [source, actual] of [
      ['hillslope', hillslope],
      ['outlet', outlet],
    ]) {
      actual.series.forEach((series, index) => {
        const expected = oracle[source][index];
        expect(series.count).toBe(expected.count);
        expect(series.missing).toBe(0);
        expect(series.max).toBeCloseTo(expected.max, 8);
        expect(series.min).toBeCloseTo(expected.min, 8);
        expect(series.firstP).toBeCloseTo(100 / (series.count + 1), 10);
      });
    }
  }
  fs.writeFileSync(
    '/tmp/fdc-browser-evidence.json',
    JSON.stringify({ hillslope, outlet, allYears, dailyRequests: requests.length, errors }, null, 2)
  );
  await testInfo.attach('flow-duration-result', {
    body: JSON.stringify(
      { hillslope, outlet, allYears, dailyRequests: requests.length, errors },
      null,
      2
    ),
    contentType: 'application/json',
  });
  await page.screenshot({ path: '/tmp/fdc-dashboard.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('standalone Omni child preserves its own source and label', async ({ page }) => {
  test.skip(!target.includes('/eighty-five-synthetic/'), 'Uses the retained undisturbed fixture');
  await open(page);
  const urls = [
    `${target}?pup=omni/scenarios/undisturbed`,
    target.replace('/eighty-five-synthetic/', '/eighty-five-synthetic;;omni;;undisturbed/'),
  ];
  for (const url of urls) {
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.locator('#graph-flow-duration').check({ force: true });
    await expect
      .poll(() => page.evaluate(() => window.glDashboardTimeseriesGraph?._data?.type))
      .toBe('flow-duration');
    await page.locator('input[name="fdc-source"][value="outlet"]').check();
    await expect.poll(async () => (await snapshot(page)).settings.source).toBe('outlet');
    const child = await snapshot(page);
    expect(child.series).toHaveLength(1);
    expect(child.series[0].label).toBe('undisturbed');
    expect(child.series[0].error).toBeUndefined();
    expect(child.series[0].count).toBe(15706);
    expect(child.series[0].max).toBeCloseTo(15.734874074074076, 8);
  }
});
