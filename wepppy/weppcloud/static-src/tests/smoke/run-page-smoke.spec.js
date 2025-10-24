import { test, expect } from '@playwright/test';

const baseURL = process.env.SMOKE_BASE_URL || 'http://localhost:8080';
const configSlug = process.env.SMOKE_RUN_CONFIG || 'dev_unit_1';
const shouldProvision = process.env.SMOKE_CREATE_RUN !== 'false';
const keepRun = process.env.SMOKE_KEEP_RUN === 'true';

let targetRunPath = process.env.SMOKE_RUN_PATH || '';
let createdRunId = null;
let skipSuite = false;
let skipReason = 'Smoke run target unavailable. Set SMOKE_RUN_PATH or enable SMOKE_CREATE_RUN (requires TEST_SUPPORT_ENABLED=true).';

const controllerSelectors = {
  map: 'form#setloc_form .wc-map',
  landuse: 'form#landuse_form',
  soil: 'form#soil_form',
  climate: 'form#climate_form',
  observed: 'form#observed_form',
  wepp: 'form#wepp_form'
};

function buildUrl(path) {
  return new URL(path, baseURL).toString();
}

function parseOverrides() {
  if (!process.env.SMOKE_RUN_OVERRIDES) {
    return {};
  }
  try {
    const parsed = JSON.parse(process.env.SMOKE_RUN_OVERRIDES);
    if (parsed && typeof parsed === 'object') {
      return parsed;
    }
    throw new Error('SMOKE_RUN_OVERRIDES must be a JSON object');
  } catch (err) {
    skipSuite = true;
    skipReason = `Invalid SMOKE_RUN_OVERRIDES JSON: ${err.message}`;
    return {};
  }
}

test.describe('runs0 smoke', () => {
  test.beforeAll(async ({ request }) => {
    if (!targetRunPath && shouldProvision) {
      const overrides = parseOverrides();
      if (skipSuite) {
        return;
      }

      const createUrl = buildUrl('/tests/api/create-run');
      const response = await request.post(createUrl, {
        data: {
          config: configSlug,
          overrides
        }
      });

      if (!response.ok()) {
        skipSuite = true;
        skipReason = `Failed to provision run via ${createUrl}: ${response.status()} ${response.statusText()}`;
        return;
      }

      const payload = await response.json();
      if (!payload?.run?.url || !payload.run.runid) {
        skipSuite = true;
        skipReason = 'Test support create-run endpoint returned an unexpected payload.';
        return;
      }

      createdRunId = payload.run.runid;
      targetRunPath = buildUrl(payload.run.url);
    }

    if (!targetRunPath) {
      skipSuite = true;
    }
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

  test('loads core controls without console errors', async ({ page }) => {
    if (skipSuite) test.skip(true, skipReason);

    const consoleErrors = [];
    page.on('pageerror', (error) => consoleErrors.push(error));
    page.on('console', (message) => {
      if (message.type() === 'error') {
        consoleErrors.push(new Error(message.text()));
      }
    });

    await page.goto(targetRunPath, { waitUntil: 'networkidle' });

    await expect(page.locator(controllerSelectors.map)).toBeVisible();
    await expect(page.locator(controllerSelectors.landuse)).toBeVisible();
    await expect(page.locator(controllerSelectors.soil)).toBeVisible();
    await expect(page.locator(controllerSelectors.climate)).toBeVisible();
    await expect(page.locator(controllerSelectors.observed)).toBeVisible();
    await expect(page.locator(controllerSelectors.wepp)).toBeVisible();

    await expect(page.locator('form#landuse_form [data-status-panel]')).toBeVisible();

    expect(consoleErrors).toEqual([]);
  });

  test('map tabs render and StatusStream attaches', async ({ page }) => {
    if (skipSuite) test.skip(true, skipReason);

    await page.goto(targetRunPath, { waitUntil: 'networkidle' });

    await page.waitForFunction(() => Boolean(window.WCControllerBootstrap && window.WCControllerBootstrap.getContext), null, { timeout: 15000 });

    const drilldownTab = page.getByRole('tab', { name: /Drilldown/i });
    await drilldownTab.click();
    await expect(page.locator('#drilldown')).toBeVisible();

    const layersTab = page.getByRole('tab', { name: /Layers/i });
    await layersTab.click();
    await expect(page.locator('#sub_layer_selection')).toBeVisible();

    const modifyLanduseTab = page.getByRole('tab', { name: /Modify Landuse/i });
    if (await modifyLanduseTab.count()) {
      await modifyLanduseTab.click();
      await expect(page.locator('#modify')).toBeVisible();
    }

    const statusInfo = await page.evaluate(() => {
      const context = window.WCControllerBootstrap?.getContext?.();
      const landuse = window.Landuse?.getInstance ? window.Landuse.getInstance() : null;
      return {
        contextDefined: Boolean(context && context.run && context.jobIds),
        landuseStatusStream: Boolean(landuse && landuse.statusStream)
      };
    });

    expect(statusInfo.contextDefined).toBeTruthy();
    expect(statusInfo.landuseStatusStream).toBeTruthy();
  });

  test('landuse mode toggles visibility', async ({ page }) => {
    if (skipSuite) test.skip(true, skipReason);

    await page.goto(targetRunPath, { waitUntil: 'networkidle' });

    const singleMode = page.locator('#landuse_mode1');
    const uploadMode = page.locator('#landuse_mode4');

    await singleMode.check();
    await expect(page.locator('#landuse_mode1_controls')).toBeVisible();
    await expect(page.locator('#landuse_mode0_controls')).toBeHidden();

    await uploadMode.check();
    await expect(page.locator('#landuse_mode4_controls')).toBeVisible();
    await expect(page.locator('#landuse_mode1_controls')).toBeHidden();

    const buildButton = page.locator('#btn_build_landuse');
    await expect(buildButton).toBeEnabled();
  });

  test('treatments control (if present) exposes StatusStream', async ({ page }) => {
    if (skipSuite) test.skip(true, skipReason);

    await page.goto(targetRunPath, { waitUntil: 'networkidle' });

    const treatmentsForm = page.locator('form#treatments_form');
    if (!(await treatmentsForm.count())) {
      test.skip(true, 'Treatments control not enabled for this run');
    }

    await expect(treatmentsForm).toBeVisible();
    await expect(treatmentsForm.locator('[data-status-panel]')).toBeVisible();

    const streamAttached = await page.evaluate(() => {
      const treatments = window.Treatments?.getInstance ? window.Treatments.getInstance() : null;
      return Boolean(treatments && treatments.statusStream);
    });

    expect(streamAttached).toBeTruthy();
  });
});
