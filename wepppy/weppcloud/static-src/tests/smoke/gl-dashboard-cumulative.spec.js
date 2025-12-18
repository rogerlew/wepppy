import { test, expect } from '@playwright/test';

const targetUrl =
  process.env.GL_DASHBOARD_URL ||
  ((process.env.SMOKE_BASE_URL && process.env.GL_DASHBOARD_PATH)
    ? `${process.env.SMOKE_BASE_URL}${process.env.GL_DASHBOARD_PATH}`
    : 'https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/gl-dashboard');

async function openDashboard(page) {
  await page.goto(targetUrl, { waitUntil: 'networkidle' });
  await expect(page.locator('#gl-dashboard-map')).toBeVisible();
}

async function expandSection(page, title) {
  const summary = page.locator('summary.gl-layer-group', { hasText: title });
  await expect(summary).toBeVisible({ timeout: 20000 });
  await summary.evaluate((el) => {
    const details = el.closest('details');
    if (details && !details.open) details.open = true;
  });
  await summary.scrollIntoViewIfNeeded();
}

test.describe('gl-dashboard cumulative contribution', () => {
  test('distinct scenarios render distinct curves', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Cumulative Contribution');

    // Select soil loss measure
    await page.selectOption('#gl-cumulative-measure', 'soil_loss');

    // Enable all available scenarios
    const checkboxes = page.locator('.gl-graph__scenario-list input[type="checkbox"]');
    const count = await checkboxes.count();
    if (count < 1) {
      test.skip('No scenarios available for cumulative contribution');
    }
    for (let i = 0; i < count; i++) {
      const cb = checkboxes.nth(i);
      await cb.evaluate((el) => {
        el.checked = true;
        el.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }

    // Activate the cumulative graph
    await page.locator('#graph-cumulative-contribution').check({ force: true });

    // Wait for graph data to load
    await expect.poll(async () =>
      page.evaluate(() => {
        const g = window.glDashboardTimeseriesGraph;
        return g && g._data && g._data.series ? Object.keys(g._data.series).length : 0;
      })
    ).toBeGreaterThan(1);

    const result = await page.evaluate(() => {
      const data = window.glDashboardTimeseriesGraph?._data;
      if (!data || !data.series) return null;
      const seriesVals = Object.values(data.series).map((s) => JSON.stringify(s.values || []));
      const unique = new Set(seriesVals);
      return {
        seriesCount: seriesVals.length,
        uniqueCount: unique.size,
      };
    });

    expect(result).not.toBeNull();
    expect(result.seriesCount).toBeGreaterThan(1);
    expect(result.uniqueCount).toBeGreaterThan(1);
  });
});
