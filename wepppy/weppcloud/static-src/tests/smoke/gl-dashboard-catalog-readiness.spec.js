import { expect, test } from '@playwright/test';

const url = process.env.GL_CATALOG_TEST_URL;
const topazId = process.env.GL_CATALOG_TEST_TOPAZ_ID;
const runoffMm = Number(process.env.GL_CATALOG_TEST_RUNOFF_MM ?? NaN);

test.skip(!url || !topazId || !Number.isFinite(runoffMm),
  'Requires a disposable managed dashboard URL and a known WEPP hillslope runoff value.');

const preparePath = /\/query-engine\/runs\/.+\/catalog\/prepare$/;
const statusPath = /\/query-engine\/runs\/.+\/catalog\/status(?:\?|$)/;
const queryPath = /\/query-engine\/runs\/.+\/query$/;

async function expectWeppOverlay(page) {
  const section = page.locator('#gl-layer-list summary').filter({ hasText: /^WEPP$/ });
  await expect(section).toBeVisible({ timeout: 60000 });
  await expect.poll(async () =>
    page.evaluate((id) => window.glDashboardState?.weppSummary?.[id]?.runoff_volume, topazId),
  ).toBeCloseTo(runoffMm, 5);
  await section.evaluate((element) => { element.closest('details').open = true; });
  await page.locator('#layer-WEPP-wepp-runoff').click();
  await expect.poll(async () => page.evaluate(() =>
    window.glDashboardDeck?.props.layers?.map((layer) => layer.id) || [],
  )).toContain('wepp-wepp-runoff');
}

test('two tabs hold result queries until catalog readiness', async ({ context }) => {
  const pages = await Promise.all([context.newPage(), context.newPage()]);
  const queries = new Map(pages.map((page) => [page, 0]));
  let unblock;
  const release = new Promise((resolve) => { unblock = resolve; });
  try {
    const prepares = pages.map((page) => page.waitForResponse((response) =>
      preparePath.test(response.url()) && response.status() === 202
    ));
    for (const page of pages) {
      page.on('request', (request) => {
        if (queryPath.test(request.url()) && request.method() === 'POST') {
          queries.set(page, queries.get(page) + 1);
        }
      });
      await page.route(statusPath, async (route) => {
        await release;
        await route.continue();
      });
    }
    await Promise.all(pages.map((page) => page.goto(url, { waitUntil: 'domcontentloaded' })));
    await Promise.all(prepares);
    for (const page of pages) {
      await expect(page.locator('#gl-dashboard-map')).toBeVisible();
      await expect(page.locator('#gl-catalog-status')).toHaveText('Preparing watershed results…');
      expect(queries.get(page)).toBe(0);
    }
    unblock();
    await Promise.all(pages.map(expectWeppOverlay));
    for (const page of pages) {
      expect(queries.get(page)).toBeGreaterThan(0);
      await expect(page.locator('#gl-catalog-status')).toBeEmpty();
    }
  } finally {
    unblock();
  }
});

test('retry restores WEPP results on the same page', async ({ page }) => {
  await page.route(preparePath, (route) => route.fulfill({
    status: 503,
    json: { state: 'unavailable', code: 'catalog_refresh_unavailable' },
  }), { times: 1 });
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  const retry = page.locator('#gl-catalog-retry');
  await expect(retry).toBeVisible();
  await expect(page.locator('#gl-dashboard-map')).toBeVisible();
  const readiness = page.waitForResponse((response) =>
    preparePath.test(response.url()) && [200, 202].includes(response.status())
  );
  await retry.click();
  await readiness;
  await expectWeppOverlay(page);
  await expect(retry).toBeHidden();
});
