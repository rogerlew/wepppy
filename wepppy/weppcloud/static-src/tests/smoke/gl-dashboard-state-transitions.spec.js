import { test, expect } from '@playwright/test';

// Resolve target URL:
// 1) GL_DASHBOARD_URL (highest priority)
// 2) SMOKE_BASE_URL + GL_DASHBOARD_PATH (if provided)
// 3) hard-coded fallback to the provided run URL
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
  await expect(summary).toBeVisible({ timeout: 15000 });
  // Avoid toggling an already-open <details>; explicitly open it.
  await summary.evaluate((el) => {
    const details = el.closest('details');
    if (details && !details.open) {
      details.open = true;
    }
  });
  // Scroll into view to prevent off-viewport click failures on nested inputs.
  await summary.scrollIntoViewIfNeeded();
}

function graphPanel(page) {
  return page.locator('#gl-graph');
}

async function expectCollapsed(page) {
  await expect(graphPanel(page)).toHaveClass(/is-collapsed/, { timeout: 10000 });
}

test.describe('gl-dashboard state transitions', () => {
  test('RAP → Landuse collapses graph', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'RAP');
    const rapCumulative = page.getByLabel('Cumulative Cover');
    await rapCumulative.scrollIntoViewIfNeeded();
    await rapCumulative.click({ force: true });
    await expandSection(page, 'Landuse');
    const landuseDominant = page.getByLabel('Dominant landuse');
    await landuseDominant.scrollIntoViewIfNeeded();
    await landuseDominant.click({ force: true });
    await page.waitForTimeout(1000);
    await expectCollapsed(page);
  });

  test('Omni full → RAP → Landuse collapses graph', async ({ page }) => {
    await openDashboard(page);
    const sidebar = page.locator('.gl-sidebar');
    await sidebar.evaluate((el) => {
      el.scrollTop = 0;
    });
    await expandSection(page, 'Omni Scenarios');
    const omniChn = page.getByLabel('Soil Loss (channels, tonne)');
    await omniChn.scrollIntoViewIfNeeded();
    await omniChn.click({ force: true });
    await page.getByRole('button', { name: 'Full graph' }).click();
    await expandSection(page, 'RAP');
    const rapCumulative = page.getByLabel('Cumulative Cover');
    await rapCumulative.scrollIntoViewIfNeeded();
    await rapCumulative.click({ force: true });
    await expandSection(page, 'Landuse');
    const landuseDominant = page.getByLabel('Dominant landuse');
    await landuseDominant.scrollIntoViewIfNeeded();
    await landuseDominant.click({ force: true });
    await page.waitForTimeout(1000);
    await expectCollapsed(page);
  });

  test('Year slider hidden on page load', async ({ page }) => {
    await openDashboard(page);
    const yearSlider = page.locator('#gl-year-slider');
    await expect(yearSlider).not.toHaveClass(/is-visible/, { timeout: 1000 });
  });

  test('RAP graph renders after Omni → RAP cumulative → full', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Omni Scenarios');
    const omniChn = page.getByLabel('Soil Loss (channels, tonne)');
    await omniChn.scrollIntoViewIfNeeded();
    await omniChn.click({ force: true });
    await expandSection(page, 'RAP');
    const rapCumulative = page.getByLabel('Cumulative Cover');
    await rapCumulative.scrollIntoViewIfNeeded();
    await rapCumulative.click({ force: true });
    await page.getByRole('button', { name: 'Full graph' }).click();
    const graphHeader = page.locator('#gl-graph h4');
    await expect(graphHeader).toContainText('Cumulative');
    await expect(graphPanel(page)).not.toHaveClass(/is-collapsed/);
  });
});
