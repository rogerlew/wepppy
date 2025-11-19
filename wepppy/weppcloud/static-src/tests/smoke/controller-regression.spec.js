import { test, expect } from '@playwright/test';
import controllerCases from './controller-cases.js';

/**
 * @typedef {import('@playwright/test').Page} Page
 * @typedef {import('@playwright/test').Locator} Locator
 * @typedef {Object} ControllerCase
 * @property {string} name
 * @property {string} formSelector
 * @property {string} actionSelector
 * @property {string|RegExp} requestUrlPattern
 * @property {string} stacktraceLocator
 * @property {string} [hintLocator]
 * @property {"rq_job"} [workflow]
 * @property {(args: { page: Page, phase?: "success"|"failure" }) => Promise<void>|void} [prepareAction]
 * @property {number} [failureStatus]
 * @property {boolean} [requireHintVisible]
 * @property {boolean} [expectJobHint]
 * @property {string} [skipMessage]
 */

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

async function expectStacktracePanelOpen(page, controller) {
  if (!controller.stacktracePanelLocator) {
    return;
  }
  const panel = page.locator(controller.stacktracePanelLocator);
  await expect(panel).toHaveCount(1);
  await expect(panel).toHaveJSProperty('open', true);
}

async function ensureControlExpanded(page, formSelector) {
  if (!formSelector) {
    return;
  }
  const form = page.locator(formSelector).first();
  if (!(await form.count())) {
    return;
  }
  const parentDetails = form.locator('xpath=ancestor::details[1]');
  if (!(await parentDetails.count())) {
    return;
  }
  const isOpen = await parentDetails.evaluate((node) => node.hasAttribute('open'));
  if (isOpen) {
    return;
  }
  const summary = parentDetails.locator('summary').first();
  if (!(await summary.count())) {
    return;
  }
  await summary.click();
  await expect(parentDetails).toHaveJSProperty('open', true);
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

      await ensureControlExpanded(page, controller.formSelector);

      const hintLocator = controller.hintLocator
        ? page.locator(controller.hintLocator)
        : form.locator('[data-job-hint]');
      
      // Verify hint exists (but may be hidden initially)
      await expect(hintLocator).toHaveCount(1);

      const stacktraceLocator = page.locator(controller.stacktraceLocator);
      if (!(await stacktraceLocator.count())) {
        test.skip(true, `Stacktrace panel not present for ${controller.name}`);
      }

      if (controller.workflow === 'rq_job') {
        await runRqJobWorkflow({
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
      await expectStacktracePanelOpen(page, controller);
      if (controller.expectJobHint !== false) {
        await expect(hintLocator).not.toHaveText(/^\s*$/);
        if (controller.requireHintVisible) {
          await expect(hintLocator).toBeVisible();
        }
      }
      expect(intercepted).toBeTruthy();
      } finally {
        await page.unroute(controller.requestUrlPattern).catch(() => {});
      }
    });
  });
});

/**
 * Generic RQ job workflow for controllers that return job_id on success.
 *
 * Tests two scenarios:
 * 1. Successful request that returns a job_id - verifies hint is populated
 * 2. Failed request that returns stacktrace - verifies stacktrace display and hint preservation
 *
 * @param {Object} params
 * @param {Page} params.page - Playwright page object
 * @param {ControllerCase} params.controller - Controller configuration from controller-cases.js
 * @param {Locator} params.hintLocator - Locator for the job hint element
 * @param {Locator} params.stacktraceLocator - Locator for the stacktrace display element
 * @returns {Promise<void>}
 */
async function runRqJobWorkflow({ page, controller, hintLocator, stacktraceLocator }) {
  const button = page.locator(controller.actionSelector);

  // Test 1: Successful build with job_id (verify hint is populated)
  const jobId = `pw-landuse-${Date.now()}`;
  
      await page.route(controller.requestUrlPattern, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ Success: true, job_id: jobId })
        });
  });

  if (typeof controller.prepareAction === 'function') {
    await controller.prepareAction({ page, phase: 'success' });
  }

  await expect(button).toBeEnabled();
  await button.click();
  
  if (controller.expectJobHint !== false) {
    // Wait for job hint to show the job_id (proves response was processed and hint updated)
    if (controller.name === 'debris_flow') {
      await expect(hintLocator).not.toHaveText(/^\s*$/, { timeout: 15000 });
    } else {
      await expect(hintLocator).toContainText(jobId, { timeout: 15000 });
    }
    if (controller.requireHintVisible) {
      await expect(hintLocator).toBeVisible();
    }
  }
  
  await page.unroute(controller.requestUrlPattern).catch(() => {});

  // Test 2: Failure with stacktrace (verify stacktrace display and hint preservation)
  const failureStatus = controller.failureStatus ?? 500;
  await page.route(controller.requestUrlPattern, async (route) => {
    await route.fulfill({
      status: failureStatus,
      contentType: 'application/json',
      body: JSON.stringify({
        Success: false,
        Error: 'Injected landuse failure',
        StackTrace: ['Injected failure for landuse controller', 'Test stacktrace line 2']
      })
    });
  });

  if (typeof controller.prepareAction === 'function') {
    await controller.prepareAction({ page, phase: 'failure' });
  }

  await button.click();
  
  // Verify stacktrace is displayed with both lines
  await expect(stacktraceLocator).toContainText('Injected landuse failure', { timeout: 15000 });
  await expect(stacktraceLocator).toContainText('Test stacktrace line 2', { timeout: 5000 });
  await expectStacktracePanelOpen(page, controller);
  
  if (controller.expectJobHint !== false) {
    // Verify hint is still visible and contains the job_id from first request
    if (controller.name === 'debris_flow') {
      await expect(hintLocator).not.toHaveText(/^\s*$/);
    } else {
      await expect(hintLocator).toContainText(jobId);
    }
    await expect(hintLocator).not.toHaveText(/^\s*$/);
    if (controller.requireHintVisible) {
      await expect(hintLocator).toBeVisible();
    }
  } else {
    await expect(hintLocator).toBeAttached();
  }
  
  await page.unroute(controller.requestUrlPattern).catch(() => {});
}
