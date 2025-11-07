import { test, expect } from '@playwright/test';

const baseURL = process.env.SMOKE_BASE_URL || 'http://localhost:8080';
const shouldProvision = process.env.SMOKE_CREATE_RUN !== 'false';
const keepRun = process.env.SMOKE_KEEP_RUN === 'true';
const configSlug = process.env.SMOKE_RUN_CONFIG || 'dev_unit_1';

let targetRunPath = process.env.SMOKE_RUN_PATH || '';
let createdRunId = null;

function buildUrl(path) {
  return new URL(path, baseURL).toString();
}

test.describe('runs0 page load', () => {
  test.beforeAll(async ({ request }) => {
    if (targetRunPath || !shouldProvision) {
      return;
    }

    const response = await request.post(buildUrl('/tests/api/create-run'), {
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
        await request.delete(buildUrl(`/tests/api/run/${createdRunId}`));
      } catch (err) {
        console.warn('Failed to delete smoke run', err);
      }
    }
  });

});
