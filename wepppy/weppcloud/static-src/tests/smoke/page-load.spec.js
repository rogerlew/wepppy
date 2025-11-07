import { test, expect } from '@playwright/test';

const baseURL = process.env.SMOKE_BASE_URL || 'http://localhost:8080';
const shouldProvision = process.env.SMOKE_CREATE_RUN !== 'false';
const keepRun = process.env.SMOKE_KEEP_RUN === 'true';
const configSlug = process.env.SMOKE_RUN_CONFIG || 'dev_unit_1';

let targetRunPath = process.env.SMOKE_RUN_PATH || '';
let createdRunId = null;
let skipSuite = false;
let skipReason = 'Smoke run target unavailable. Provide SMOKE_RUN_PATH or enable SMOKE_CREATE_RUN.';

function buildUrl(path) {
  return new URL(path, baseURL).toString();
}

test.describe('runs0 page load', () => {
  test.beforeAll(async ({ request }) => {
    if (targetRunPath || !shouldProvision) {
      if (!targetRunPath && !shouldProvision) {
        skipSuite = true;
      }
      return;
    }

    const response = await request.post(buildUrl('/tests/api/create-run'), {
      data: { config: configSlug }
    });
    if (!response.ok()) {
      skipSuite = true;
      skipReason = `Failed to provision run: ${response.status()} ${response.statusText()}`;
      return;
    }
    const payload = await response.json();
    if (!payload?.run?.url || !payload.run.runid) {
      skipSuite = true;
      skipReason = 'create-run returned an unexpected payload';
      return;
    }
    createdRunId = payload.run.runid;
    targetRunPath = buildUrl(payload.run.url);
  });

  test.afterAll(async ({ request }) => {
    if (createdRunId && !keepRun && !skipSuite) {
      try {
        await request.delete(buildUrl(`/tests/api/run/${createdRunId}`));
      } catch (err) {
        console.warn('Failed to delete smoke run', err);
      }
    }
  });

  test('loads runs0 core controls without console errors', async ({ page }) => {
    if (skipSuite || !targetRunPath) test.skip(true, skipReason);

    const consoleErrors = [];
    page.on('pageerror', (error) => {
      consoleErrors.push({
        type: 'pageerror',
        message: error.message || String(error),
        stack: error.stack || ''
      });
    });
    page.on('console', (message) => {
      if (message.type() === 'error') {
        const text = message.text();
        if (text.includes('Debris flow form not found')) return;
        if (text.includes('Failed to load resource') && text.includes('401')) return;
        consoleErrors.push({ type: 'console', message: text });
      }
    });

    await page.goto(targetRunPath, { waitUntil: 'networkidle' });

    await expect(page.locator('form#setloc_form .wc-map')).toBeVisible();
    await expect(page.locator('form#landuse_form')).toBeVisible();
    await expect(page.locator('form#soil_form')).toBeVisible();
    await expect(page.locator('form#climate_form')).toBeVisible();
    await expect(page.locator('form#wepp_form')).toBeAttached();

    const landuseStatusPanel = page.locator('form#landuse_form [data-status-panel]');
    await expect(landuseStatusPanel).toBeVisible();

    expect(consoleErrors).toEqual([]);
  });
});
