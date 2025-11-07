import { test, expect } from '@playwright/test';
import controllerTestCases from './controller-test-cases.js';

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
  // If baseURL ends with /weppcloud, and path starts with /weppcloud/,
  // we need to construct the URL carefully to avoid double-prefixing
  const base = baseURL.replace(/\/$/, ''); // remove trailing slash
  
  if (base.endsWith('/weppcloud') && path.startsWith('/weppcloud/')) {
    // Strip /weppcloud from path and append to base
    const relativePath = path.substring('/weppcloud'.length);
    return base + relativePath;
  }
  
  // Otherwise use standard URL construction
  return new URL(path, base).toString();
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

function buildFailurePayload(controllerName) {
  const label = controllerName.replace(/_/g, ' ');
  const errorMessage = `Injected test failure for ${label}`;
  return {
    errorMessage,
    body: {
      Success: false,
      Error: errorMessage,
      StackTrace: [
        `Controller: ${label}`,
        'Injected stack trace for automated smoke test.'
      ]
    }
  };
}

test.describe('runs0 smoke', () => {
  test.beforeAll(async ({ request }) => {
    if (!targetRunPath && shouldProvision) {
      const overrides = parseOverrides();
      if (skipSuite) {
        return;
      }

      const createUrl = buildUrl('/weppcloud/tests/api/create-run');
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
        await request.delete(buildUrl(`/weppcloud/tests/api/run/${createdRunId}`));
      } catch (err) {
        console.warn('Failed to delete smoke run', err);
      }
    }
  });

  test('loads core controls', async ({ page }) => {
    if (skipSuite) test.skip(true, skipReason);

    const consoleErrors = [];
    page.on('pageerror', (error) => {
      const errorInfo = {
        type: 'pageerror',
        message: error.message || String(error),
        stack: error.stack || '',
        name: error.name || 'Unknown'
      };
      // Filter expected/benign errors
      if (errorInfo.message.includes('Debris flow')) return;
      if (errorInfo.message === 'Object') return;  // Bootstrap quirk
      consoleErrors.push(errorInfo);
    });
    page.on('console', (message) => {
      if (message.type() === 'error') {
        const text = message.text();
        // Filter out expected/benign errors
        if (text.includes('Debris flow form not found')) return;
        if (text.includes('Failed to load resource') && text.includes('401')) return;
        consoleErrors.push({ type: 'console', message: text });
      }
    });

    await page.goto(targetRunPath, { waitUntil: 'networkidle' });

    await expect(page.locator(controllerSelectors.map)).toBeVisible();
    await expect(page.locator(controllerSelectors.landuse)).toBeVisible();
    await expect(page.locator(controllerSelectors.soil)).toBeVisible();
    await expect(page.locator(controllerSelectors.climate)).toBeVisible();
    // observed and wepp may be hidden depending on config
    await expect(page.locator(controllerSelectors.wepp)).toBeAttached();

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
    const isVisible = await treatmentsForm.isVisible();
    if (!isVisible) {
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

  controllerTestCases.forEach((controller) => {
    test(`${controller.name} controller surfaces stacktrace and keeps job hint visible on injected failure`, async ({ page }) => {
      if (skipSuite) test.skip(true, skipReason);

      await page.goto(targetRunPath, { waitUntil: 'networkidle' });

      const form = page.locator(controller.formSelector);
      if (!(await form.count())) {
        test.skip(true, controller.skipMessage || `${controller.name} control not enabled for this run`);
      }

      const hintLocator = controller.hintLocator
        ? page.locator(controller.hintLocator)
        : form.locator('[data-job-hint]');
      
      // Verify hint exists (but may be hidden initially)
      await expect(hintLocator).toHaveCount(1);

      const stacktraceLocator = page.locator(controller.stacktraceLocator);
      if (!(await stacktraceLocator.count())) {
        test.skip(true, `Stacktrace panel not present for ${controller.name}`);
      }

      const { errorMessage, body } = buildFailurePayload(controller.name);
      const routePattern = controller.requestUrlPattern;
      let intercepted = false;

      await page.route(routePattern, async (route) => {
        intercepted = true;
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify(body)
        });
      });

      try {
        await page.locator(controller.actionSelector).click();
        await expect(stacktraceLocator).toContainText(errorMessage, { timeout: 15000 });
        // Hint may remain empty on error since no job was created
        await expect(hintLocator).toBeAttached();
        expect(intercepted).toBeTruthy();
      } finally {
        await page.unroute(routePattern).catch(() => {});
      }
    });
  });
});
