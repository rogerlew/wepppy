import { test, expect } from '@playwright/test';

const baseURL = process.env.SMOKE_BASE_URL || 'http://localhost:8080';
const shouldProvision = process.env.SMOKE_CREATE_RUN !== 'false';
const keepRun = process.env.SMOKE_KEEP_RUN === 'true';
const configSlug = process.env.SMOKE_RUN_CONFIG || 'dev_unit_1';

const selectors = {
  weppTable: '#storm_event_wepp_frequency',
  noaaTable: '#storm_event_noaa_frequency',
  noaaUnavailable: '[data-noaa-unavailable]',
  metricCells: 'td[data-storm-event-analyzer-cell="true"]',
  filterRange: 'input[name="storm_filter_range"]',
  warmupToggle: 'input[name="storm_warmup"]',
  eventRows: '#storm_event_characteristics_table tbody tr:not([data-sort-position="top"])',
  errorBanner: '[data-storm-event-analyzer-error]',
  hyetographCanvas: '[data-storm-event-analyzer-canvas]',
  eventsEmpty: '[data-storm-event-analyzer-events-empty]',
  summaryEmpty: '#storm-event-analyzer__summary [data-empty-state]',
};

let targetRunPath = process.env.SMOKE_RUN_PATH || '';
let createdRunId = null;
let skipSuite = false;
let skipReason =
  'Smoke run target unavailable. Set SMOKE_RUN_PATH or enable SMOKE_CREATE_RUN (requires TEST_SUPPORT_ENABLED=true).';

function buildUrl(path) {
  const base = baseURL.replace(/\/$/, '');

  if (base.endsWith('/weppcloud') && path.startsWith('/weppcloud/')) {
    const relativePath = path.substring('/weppcloud'.length);
    return base + relativePath;
  }

  return new URL(path, base).toString();
}

function resolveRunPath(path) {
  if (!path) {
    return '';
  }
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  return buildUrl(path);
}

function ensureStormEventAnalyzerPath(path) {
  if (!path) {
    return '';
  }
  const trimmed = path.replace(/\/$/, '');
  if (trimmed.endsWith('/storm-event-analyzer')) {
    return trimmed;
  }
  return `${trimmed}/storm-event-analyzer`;
}

function waitForQueryEngineResponse(page) {
  return page.waitForResponse(
    (response) => response.url().includes('/query-engine/') && response.request().method() === 'POST',
  );
}

function skipIfUnavailable() {
  if (skipSuite || !targetRunPath) {
    test.skip(true, skipReason);
  }
}

async function openStormEventAnalyzer(page) {
  await page.goto(targetRunPath, { waitUntil: 'networkidle' });
}

async function selectFirstMetric(page) {
  const metricCells = page.locator(`${selectors.weppTable} ${selectors.metricCells}`);
  await expect(metricCells.first()).toBeVisible();
  await metricCells.first().click();
}

async function waitForEventRows(page) {
  const rows = page.locator(selectors.eventRows);
  await expect.poll(async () => rows.count(), { timeout: 20000 }).toBeGreaterThan(0);
  return rows;
}

test.describe('storm event analyzer smoke', () => {
  test.beforeAll(async ({ request }) => {
    if (targetRunPath) {
      targetRunPath = ensureStormEventAnalyzerPath(resolveRunPath(targetRunPath));
      return;
    }

    if (!shouldProvision) {
      skipSuite = true;
      return;
    }

    const createUrl = buildUrl('/weppcloud/tests/api/create-run');
    const response = await request.post(createUrl, {
      data: { config: configSlug },
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
    const runUrl = buildUrl(payload.run.url);
    targetRunPath = ensureStormEventAnalyzerPath(runUrl);

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

  test('metric selection + events load', async ({ page }) => {
    skipIfUnavailable();

    await openStormEventAnalyzer(page);
    await selectFirstMetric(page);
    await waitForEventRows(page);

    await expect(page.locator(selectors.eventsEmpty)).toBeHidden();
    await expect(page.locator(selectors.hyetographCanvas)).toHaveCount(1);
  });

  test('filter range + warm-up toggle', async ({ page }) => {
    skipIfUnavailable();

    await openStormEventAnalyzer(page);
    await selectFirstMetric(page);
    const eventRows = await waitForEventRows(page);

    const rangeFive = page.locator(`${selectors.filterRange}[value="5"]`);
    const warmupToggle = page.locator(selectors.warmupToggle);

    const rangeResponse = waitForQueryEngineResponse(page);
    await rangeFive.check();
    await rangeResponse;

    const warmupResponse = waitForQueryEngineResponse(page);
    await warmupToggle.setChecked(false);
    await warmupResponse;

    await expect.poll(async () => eventRows.count(), { timeout: 15000 }).toBeGreaterThan(0);
    await expect(page.locator(selectors.errorBanner)).toBeHidden();
  });

  test('event selection + summary update', async ({ page }) => {
    skipIfUnavailable();

    await openStormEventAnalyzer(page);
    await selectFirstMetric(page);
    const eventRows = await waitForEventRows(page);

    const firstRow = eventRows.first();
    await firstRow.click();

    await expect(firstRow).toHaveClass(/is-selected/);
    await expect(firstRow.locator('input[type="radio"]')).toBeChecked();

    await expect(page.locator(selectors.summaryEmpty)).toBeHidden();

    await page.waitForFunction(() => {
      const volumeCell = document.querySelector('[data-storm-event-analyzer-summary="runoff-volume"]');
      const coefficientCell = document.querySelector('[data-storm-event-analyzer-summary="runoff-coefficient"]');
      const values = [volumeCell, coefficientCell].map((cell) => (cell ? (cell.textContent || '').trim() : ''));
      return values.some((text) => text && text !== '--' && text !== '\u2014');
    });
  });

  test('hyetograph highlight tracks selection state', async ({ page }) => {
    skipIfUnavailable();

    await openStormEventAnalyzer(page);
    await selectFirstMetric(page);
    const eventRows = await waitForEventRows(page);

    const firstRow = eventRows.first();
    await firstRow.click();

    const simDayIndex = await firstRow.getAttribute('data-sim-day-index');
    expect(simDayIndex).toBeTruthy();

    await page.waitForFunction(
      (expected) => {
        const state = window.__STORM_EVENT_ANALYZER_STATE__;
        if (!state) {
          return false;
        }
        return String(state.selectedEventSimDayIndex) === expected;
      },
      simDayIndex,
    );

    const selectedIndex = await page.evaluate(
      () => window.__STORM_EVENT_ANALYZER_STATE__?.selectedEventSimDayIndex,
    );
    expect(String(selectedIndex)).toBe(String(simDayIndex));
  });

  test('noaa missing scenario hides table and shows message', async ({ page }) => {
    skipIfUnavailable();

    await page.route('**/climate/atlas14_intensity_pds_mean_metric.csv*', async (route) => {
      await route.fulfill({ status: 404, contentType: 'text/plain', body: 'Not Found' });
    });

    await openStormEventAnalyzer(page);

    const noaaMessage = page.locator(selectors.noaaUnavailable);
    await expect(noaaMessage).toBeVisible();
    await expect(page.locator(selectors.noaaTable)).toHaveAttribute('hidden', 'hidden');
  });

  test('error banner persists while keeping previous results', async ({ page }) => {
    skipIfUnavailable();

    let failNextQuery = false;
    await page.route('**/query-engine/**', async (route) => {
      if (failNextQuery) {
        failNextQuery = false;
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Injected Query Engine failure.' }),
        });
        return;
      }
      await route.continue();
    });

    await openStormEventAnalyzer(page);
    await selectFirstMetric(page);
    const eventRows = await waitForEventRows(page);
    const initialCount = await eventRows.count();
    expect(initialCount).toBeGreaterThan(0);

    failNextQuery = true;
    const responsePromise = waitForQueryEngineResponse(page);
    await page.locator(`${selectors.filterRange}[value="5"]`).check();
    await responsePromise;

    await expect(page.locator(selectors.errorBanner)).toBeVisible();
    await expect.poll(async () => eventRows.count(), { timeout: 15000 }).toBe(initialCount);
  });
});
