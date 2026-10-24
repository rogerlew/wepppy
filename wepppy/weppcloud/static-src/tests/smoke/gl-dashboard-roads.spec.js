import { test, expect } from '@playwright/test';

const target = process.env.GL_DASHBOARD_ROADS_URL;
test.skip(!target, 'Set GL_DASHBOARD_ROADS_URL to a current Roads project.');

test('real Roads artifacts reach line layer, keyboard details and both scope directions', async ({ page, request }) => {
  test.setTimeout(180000);
  const url = new URL(target); url.searchParams.set('output_scope', 'baseline'); url.searchParams.set('roads', 'on');
  const dataUrl = new URL(url); dataUrl.pathname = dataUrl.pathname.replace(/gl-dashboard\/?$/, 'resources/roads.json'); dataUrl.search = '?view=detachment';
  const response = await request.get(dataUrl.href);
  expect(response.status()).toBe(200);
  expect(response.headers()['cache-control']).toBe('no-store');
  const data = await response.json();
  expect(data.roads_detachment.state).toBe('available');
  const complete = data.features.filter((f) => f.properties.roads_detachment.state === 'complete');
  expect(complete.length).toBeGreaterThan(0);
  for (const feature of complete) {
    const d = feature.properties.roads_detachment;
    const mass = d.profiles.reduce((sum, p) => sum + p.soil_loss_kg, 0);
    const area = d.profiles.reduce((sum, p) => sum + p.modeled_area_m2, 0);
    expect(d.rate_t_ha_year).toBeCloseTo(10 * mass / area, 9);
  }
  await page.goto(url.href, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#gl-roads-visible')).toBeEnabled({ timeout: 60000 });
  await expect.poll(() => page.evaluate(() => window.glDashboardDeck?.props.layers?.some((layer) => layer?.id === 'roads-detachment')), { timeout: 60000 }).toBe(true);
  await page.locator('#gl-roads-details summary').click();
  const button = page.locator('#gl-roads-table button').nth(1);
  await button.focus(); await page.keyboard.press('Enter');
  await expect(page.locator('#gl-roads-selection')).toBeFocused();
  await expect(page.locator('#gl-roads-selection')).toContainText('Modeled source road-segment length');
  await expect(page.locator('#gl-roads-legend')).toContainText('t/ha/year');
  const view = await page.evaluate(() => ({ ...window.glDashboardState.currentViewState }));
  await page.selectOption('#gl-output-scope', 'roads');
  await expect(page).toHaveURL(/output_scope=roads/);
  await expect(page.locator('#gl-roads-visible')).toBeEnabled({ timeout: 60000 });
  expect(await page.evaluate(() => window.GL_DASHBOARD_CONTEXT.weppPaths.lossHill)).toContain('wepp/roads/output');
  expect(await page.evaluate(() => window.glDashboardState.currentViewState.longitude)).toBeCloseTo(view.longitude, 6);
  await expect(page.locator('#gl-roads-visible')).toBeChecked();
  await page.selectOption('#gl-output-scope', 'baseline');
  await expect(page).toHaveURL(/output_scope=baseline/);
  await expect(page.locator('#gl-roads-visible')).toBeEnabled({ timeout: 60000 });
  expect(await page.evaluate(() => window.GL_DASHBOARD_CONTEXT.weppPaths.lossHill)).toBe('wepp/output/interchange/loss_pw0.hill.parquet');
});

test('literal hostile labels and optional failure do not poison baseline', async ({ page }) => {
  test.setTimeout(120000);
  const url = new URL(target); url.searchParams.set('output_scope', 'baseline'); url.searchParams.set('roads', 'on');
  await page.route('**/resources/roads.json?view=detachment', async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    data.features[0].properties.name = '<img src=x onerror="window.roadsXss=true">';
    await route.fulfill({ response, json: data });
  });
  await page.goto(url.href, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#gl-roads-visible')).toBeEnabled({ timeout: 60000 });
  await page.locator('#gl-roads-details summary').click();
  await page.locator('#gl-roads-table button').first().click();
  await expect(page.locator('#gl-roads-selection')).toContainText('<img src=x');
  expect(await page.locator('#gl-roads-panel img').count()).toBe(0);
  expect(await page.evaluate(() => window.roadsXss)).toBeUndefined();
  await page.unroute('**/resources/roads.json?view=detachment');
  await page.route('**/resources/roads.json?view=detachment', (route) => route.fulfill({ status: 503, json: { error: 'injected read outage' } }));
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('#gl-roads-status')).toContainText('Reload to retry', { timeout: 60000 });
  await expect(page.locator('#gl-output-scope')).toHaveValue('baseline');
  await expect.poll(() => page.evaluate(() => !!window.glDashboardState?.weppSummary), { timeout: 60000 }).toBe(true);
  expect(await page.evaluate(() => window.glDashboardDeck.props.layers.some((layer) => layer.id === 'roads-detachment'))).toBe(false);
});

test('yearly data and Roads maximum survive scope roundtrip', async ({ page }) => {
  test.setTimeout(180000);
  const url = new URL(target); url.searchParams.set('output_scope', 'baseline'); url.searchParams.set('roads', 'on');
  await page.goto(url.href, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#gl-roads-visible')).toBeEnabled({ timeout: 60000 });
  const yearly = page.locator('input[id$="wepp-yearly-soil-loss"]');
  await expect(yearly).toBeAttached({ timeout: 60000 });
  await yearly.evaluate((el) => { el.closest('details').open = true; });
  await yearly.check();
  await expect.poll(() => page.evaluate(() => !!window.glDashboardState.weppYearlySummary), { timeout: 60000 }).toBe(true);
  const year = await page.evaluate(() => window.glDashboardState.weppYearlyMetadata.years[0]);
  await page.locator('#gl-year-slider-input').evaluate((el, value) => {
    el.value = String(value); el.dispatchEvent(new Event('input', { bubbles: true }));
  }, year);
  await expect.poll(() => page.evaluate(() => window.glDashboardState.weppYearlySelectedYear)).toBe(year);
  const maxInput = page.locator('#gl-roads-legend input');
  await maxInput.fill('27'); await maxInput.press('Tab');
  await expect(maxInput).toHaveValue('27');
  for (const scope of ['roads', 'baseline']) {
    await page.selectOption('#gl-output-scope', scope);
    await expect(page).toHaveURL(new RegExp(`output_scope=${scope}`));
    await expect(page.locator('#gl-roads-visible')).toBeEnabled({ timeout: 60000 });
    await expect(page.locator('#gl-roads-legend input')).toHaveValue('27');
    await expect.poll(() => page.evaluate(() => !!window.glDashboardState.weppYearlySummary), { timeout: 60000 }).toBe(true);
    expect(await page.evaluate(() => window.glDashboardState.weppYearlySelectedYear)).toBe(year);
    expect(await page.evaluate(() => window.glDashboardState.weppYearlyLayers.find((l) => l.key === 'wepp-yearly-soil-loss').visible)).toBe(true);
    expect(await page.evaluate(() => window.glDashboardState.activeGraphKey)).toBe('wepp-yearly');
  }
});


test('scoped lifecycle failure clears stale visuals without reload and keeps Baseline escape', async ({ page }) => {
  test.setTimeout(120000);
  const url = new URL(target); url.searchParams.set('output_scope', 'roads');
  let navigations = 0;
  page.on('framenavigated', (frame) => { if (frame === page.mainFrame()) navigations += 1; });
  await page.route('**/query-engine/runs/**/query', async (route) => {
    const body = route.request().postData() || '';
    if (body.includes('wepp/roads/output')) {
      await route.fulfill({ status: 409, json: { code: 'roads_results_unavailable', error: 'Roads is busy; wait for the active operation to finish.' } });
    } else await route.continue();
  });
  await page.goto(url.href, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#gl-output-scope-status')).toContainText('Baseline remains available', { timeout: 60000 });
  await expect(page.locator('#gl-output-scope-status')).toContainText('Roads is busy; wait');
  await expect(page.locator('#gl-output-scope-status')).not.toContainText('Prepare and run');
  await expect(page.locator('.gl-main')).toBeHidden();
  expect(navigations).toBe(1);
  await page.selectOption('#gl-output-scope', 'baseline');
  await expect(page).toHaveURL(/output_scope=baseline/);
  await expect(page.locator('.gl-main')).toBeVisible();
  await expect.poll(() => page.evaluate(() => !!window.glDashboardState?.weppSummary), { timeout: 60000 }).toBe(true);
});

test('unavailable scenario graph does not invalidate current Roads map', async ({ page }) => {
  test.setTimeout(120000);
  await page.addInitScript(() => {
    let context;
    Object.defineProperty(window, 'GL_DASHBOARD_CONTEXT', {
      configurable: true, get: () => context,
      set(value) {
        value.omniScenarios = [{ name: 'Unavailable test scenario', path: '_pups/omni/scenarios/missing-test' }];
        context = value;
      },
    });
  });
  await page.route('**/query-engine/runs/**/query', async (route) => {
    const body = route.request().postDataJSON();
    if (body?.scenario === 'missing-test') {
      await route.fulfill({ status: 409, json: { code: 'roads_results_unavailable', error: 'Run Roads for this scenario.' } });
    } else await route.continue();
  });
  const url = new URL(target); url.searchParams.set('output_scope', 'roads'); url.searchParams.set('roads', 'on');
  await page.goto(url.href, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#gl-roads-visible')).toBeEnabled({ timeout: 60000 });
  const graph = page.locator('#graph-omni-soil-loss-hill');
  await graph.evaluate((el) => { el.closest('details').open = true; });
  await graph.check();
  await expect(page.locator('#gl-graph-empty')).toContainText('Selected scenario Roads results', { timeout: 60000 });
  await expect(page.locator('.gl-main')).toBeVisible();
  await expect(page.locator('#gl-output-scope option[value=roads]')).toBeEnabled();
  expect(await page.evaluate(() => window.glDashboardDeck.props.layers.some((layer) => layer.id === 'roads-detachment'))).toBe(true);
});
