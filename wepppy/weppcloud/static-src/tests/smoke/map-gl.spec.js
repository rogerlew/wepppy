import { test, expect } from '@playwright/test';

const fallbackUrl = 'https://wc.bearhive.duckdns.org/weppcloud/runs/rlew-appreciated-tremolite/disturbed9002/';

function buildUrl(path, baseUrl) {
  if (!path) {
    return '';
  }
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  if (!baseUrl) {
    return path;
  }
  const base = baseUrl.replace(/\/$/, '');
  if (base.endsWith('/weppcloud') && path.startsWith('/weppcloud/')) {
    return base + path.substring('/weppcloud'.length);
  }
  return new URL(path, base).toString();
}

function resolveTargetUrl() {
  if (process.env.MAP_GL_URL) {
    return process.env.MAP_GL_URL;
  }
  if (process.env.SMOKE_MAP_GL_PATH && process.env.SMOKE_BASE_URL) {
    return buildUrl(process.env.SMOKE_MAP_GL_PATH, process.env.SMOKE_BASE_URL);
  }
  if (process.env.SMOKE_RUN_PATH) {
    return buildUrl(process.env.SMOKE_RUN_PATH, process.env.SMOKE_BASE_URL || '');
  }
  return fallbackUrl;
}

async function openRun(page) {
  const targetUrl = resolveTargetUrl();
  await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
  await expect(page.locator('#mapid')).toBeVisible();
}

function attachConsoleCapture(page) {
  const consoleErrors = [];

  page.on('pageerror', (error) => {
    const message = error.message || String(error);
    if (message === 'Object') return;
    consoleErrors.push({ type: 'pageerror', message, stack: error.stack || '' });
  });

  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    const text = message.text();
    if (text.includes('Debris flow form not found')) return;
    if (text.includes('Failed to load resource') && text.includes('401')) return;
    consoleErrors.push({ type: 'console', message: text });
  });

  return consoleErrors;
}

test.describe('map gl smoke', () => {
  test('run loads without console errors and map canvas is visible', async ({ page }) => {
    const consoleErrors = attachConsoleCapture(page);

    await openRun(page);

    const map = page.locator('#mapid');
    await expect(map).toBeVisible();
    const box = await map.boundingBox();
    expect(box).not.toBeNull();
    expect(box.width).toBeGreaterThan(0);
    expect(box.height).toBeGreaterThan(0);

    expect(consoleErrors).toEqual([]);
  });
});
