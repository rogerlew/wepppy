import { test, expect } from '@playwright/test';
import controllerCases from './controller-cases.js';

const baseURL = process.env.SMOKE_BASE_URL || 'http://localhost:8080';
const shouldProvision = process.env.SMOKE_CREATE_RUN !== 'false';
const keepRun = process.env.SMOKE_KEEP_RUN === 'true';
const configSlug = process.env.SMOKE_RUN_CONFIG || 'dev_unit_1';

let targetRunPath = process.env.SMOKE_RUN_PATH || '';
let createdRunId = null;

function buildUrl(path) {
  const base = baseURL.replace(/\/$/, '');
  
  if (base.endsWith('/weppcloud') && path.startsWith('/weppcloud/')) {
    const relativePath = path.substring('/weppcloud'.length);
    return base + relativePath;
  }
  
  return new URL(path, base).toString();
}

function buildFailurePayload(controllerName) {
  const label = controllerName.replace(/_/g, ' ');
  const message = `Injected test failure for ${label}`;
  return {
    message,
    body: {
      Success: false,
      Error: message,
      StackTrace: [
        `Controller: ${label}`,
        'Injected stack trace for automated smoke test.'
      ]
    }
  };
}

test.describe('controller regression suite', () => {
  test.beforeAll(async ({ request }) => {
    if (targetRunPath || !shouldProvision) {
      return;
    }

    const response = await request.post(buildUrl('/weppcloud/tests/api/create-run'), {
      data: { config: configSlug }
    });
    if (!response.ok()) {
      throw new Error(`Failed to provision run: ${response.status()} ${response.statusText()}`);
    }
    const payload = await response.json();
    if (!payload?.run?.url || !payload.run.runid) {
      throw new Error('create-run returned an unexpected payload');
    }
    createdRunId = payload.run.runid;
    targetRunPath = buildUrl(payload.run.url);
  });

  test.afterAll(async ({ request }) => {
    if (createdRunId && !keepRun) {
      try {
        await request.delete(buildUrl(`/weppcloud/tests/api/run/${createdRunId}`));
      } catch (err) {
        console.warn('Failed to delete smoke run', err);
      }
    }
  });

  controllerCases.forEach((controller) => {
    test(`${controller.name} surfaces stacktrace and preserves job hint`, async ({ page }) => {
      if (!targetRunPath) {
        test.skip(true, 'No target run available. Ensure SMOKE_BASE_URL and TEST_SUPPORT endpoints are accessible.');
      }

      await page.goto(targetRunPath, { waitUntil: 'networkidle' });

      const form = page.locator(controller.formSelector);
      if (!(await form.count())) {
        test.skip(true, controller.skipMessage || `${controller.name} control not enabled for this run`);
      }

      const hintLocator = controller.hintLocator
        ? page.locator(controller.hintLocator)
        : form.locator('[data-job-hint]');
      await expect(hintLocator).toBeVisible();

      const stacktraceLocator = page.locator(controller.stacktraceLocator);
      if (!(await stacktraceLocator.count())) {
        test.skip(true, `Stacktrace panel not present for ${controller.name}`);
      }

      if (controller.workflow === 'landuse') {
        await runLanduseWorkflow({
          page,
          controller,
          hintLocator,
          stacktraceLocator
        });
        return;
      }

      const { message, body } = buildFailurePayload(controller.name);
      let intercepted = false;

      await page.route(controller.requestUrlPattern, async (route) => {
        intercepted = true;
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify(body)
        });
      });

      try {
        await page.locator(controller.actionSelector).click();
        await expect(stacktraceLocator).toContainText(message, { timeout: 15000 });
        await expect(hintLocator).not.toHaveText(/^\s*$/);
        expect(intercepted).toBeTruthy();
      } finally {
        await page.unroute(controller.requestUrlPattern).catch(() => {});
      }
    });
  });
});

async function runLanduseWorkflow({ page, controller, hintLocator, stacktraceLocator }) {
  const jobId = `pw-landuse-${Date.now()}`;
  let intercepted = false;

  await page.route(controller.requestUrlPattern, async (route) => {
    intercepted = true;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ Success: true, job_id: jobId })
    });
  });

  try {
    await page.locator(controller.actionSelector).click();
    await expect(hintLocator).toContainText(jobId, { timeout: 15000 });
    expect(intercepted).toBeTruthy();
  } finally {
    await page.unroute(controller.requestUrlPattern).catch(() => {});
  }

  const failurePayload = buildFailurePayload(controller.name);

  await page.evaluate((payload) => {
    const landuse = window.Landuse && typeof window.Landuse.getInstance === 'function'
      ? window.Landuse.getInstance()
      : null;
    if (!landuse || typeof landuse.pushResponseStacktrace !== 'function') {
      throw new Error('Landuse controller unavailable for stacktrace injection.');
    }
    landuse.pushResponseStacktrace(landuse, payload.body);
  }, failurePayload);

  await expect(stacktraceLocator).toContainText(failurePayload.message, { timeout: 15000 });
  await expect(hintLocator).toContainText(jobId);
}
