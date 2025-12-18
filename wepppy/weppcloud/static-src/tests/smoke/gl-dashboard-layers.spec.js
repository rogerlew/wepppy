import { test, expect } from '@playwright/test';

// Resolve target URL with the same precedence as other gl-dashboard specs
const targetUrl =
  process.env.GL_DASHBOARD_URL ||
  ((process.env.SMOKE_BASE_URL && process.env.GL_DASHBOARD_PATH)
    ? `${process.env.SMOKE_BASE_URL}${process.env.GL_DASHBOARD_PATH}`
    : 'https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/gl-dashboard');

async function openDashboard(page) {
  await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
  await expect(page.locator('#gl-dashboard-map')).toBeVisible();
}

async function waitForDetectedLayers(page, timeout = 20000) {
  try {
    await page.waitForFunction(
      () => (window.glDashboardState?.detectedLayers || []).length > 0,
      { timeout },
    );
    return true;
  } catch (err) {
    return false;
  }
}

async function expandSection(page, title) {
  const summary = page.locator('summary.gl-layer-group', { hasText: title });
  await expect(summary).toBeVisible({ timeout: 15000 });
  await summary.evaluate((el) => {
    const details = el.closest('details');
    if (details && !details.open) details.open = true;
  });
  await summary.scrollIntoViewIfNeeded();
}

async function getDeckLayerIds(page) {
  return page.evaluate(() => {
    const deck = window.glDashboardDeck;
    if (!deck || !deck.props || !Array.isArray(deck.props.layers)) {
      return [];
    }
    return deck.props.layers.filter((l) => l && l.id).map((l) => l.id);
  });
}

async function getDetectedLayer(page, key) {
  return page.evaluate((layerKey) => {
    const layer = (window.glDashboardState?.detectedLayers || []).find((l) => l.key === layerKey);
    if (!layer) return null;
    return {
      key: layer.key,
      visible: !!layer.visible,
      bounds: layer.bounds,
      hasCanvas: !!layer.canvas,
      size: layer.canvas ? { w: layer.canvas.width, h: layer.canvas.height } : null,
    };
  }, key);
}

async function waitForSubcatchments(page) {
  await expect.poll(async () =>
    page.evaluate(() => {
      const st = window.glDashboardState;
      return !!(st && st.subcatchmentsGeoJson && st.subcatchmentsGeoJson.features && st.subcatchmentsGeoJson.features.length);
    }),
  ).toBeTruthy();
}

async function isDetailsOpen(page, title) {
  return page.locator('summary.gl-layer-group', { hasText: title }).evaluate((el) => {
    const details = el.closest('details');
    return details ? details.open : false;
  });
}

test.describe('gl-dashboard layer detection and wiring', () => {
  test('layer controls render and toggling updates the deck stack', async ({ page }) => {
    await openDashboard(page);
    const hasDetected = await waitForDetectedLayers(page);
    if (!hasDetected) {
      test.skip('No raster layers detected in this run');
    }
    await expandSection(page, 'Landuse');

    const dominant = page.getByLabel('Dominant landuse');
    await expect(dominant).toBeVisible({ timeout: 15000 });

    // Layer list should have populated entries once detection finishes.
    await expect.poll(async () => page.locator('#gl-layer-list li').count()).toBeGreaterThan(0);
    await expect(page.locator('#gl-layer-empty')).toBeHidden({ timeout: 5000 });

    // Default dominant overlay should be active.
    await expect.poll(async () => getDeckLayerIds(page)).toContain('landuse-lu-dominant');

    // Switch to canopy cover and ensure the deck updates.
    const canopy = page.getByLabel('Canopy cover (cancov)');
    await canopy.scrollIntoViewIfNeeded();
    await canopy.click({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('landuse-lu-cancov');
    await expect.poll(async () => getDeckLayerIds(page)).not.toContain('landuse-lu-dominant');
  });

  test('raster: landuse nlcd.tif toggles bitmap layer', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Landuse');
    const raster = page.getByLabel('Landuse (nlcd.tif)');
    await expect(raster).toBeVisible({ timeout: 15000 });
    await raster.click({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('raster-landuse');
    await expect.poll(async () => getDetectedLayer(page, 'landuse')).toMatchObject({ visible: true });
    const landuse = await getDetectedLayer(page, 'landuse');
    expect(Array.isArray(landuse.bounds)).toBeTruthy();
    expect(landuse.bounds[0]).toBeGreaterThan(-180);
    expect(landuse.bounds[0]).toBeLessThan(180);
    expect(landuse.bounds[1]).toBeGreaterThan(-90);
    expect(landuse.bounds[1]).toBeLessThan(90);
    expect(landuse.hasCanvas || landuse.size).toBeTruthy();
    const legendSection = page
      .locator('#gl-legends-content .gl-legend-section')
      .filter({ hasText: 'Landuse (nlcd.tif)' })
      .first();
    await expect(legendSection).toBeVisible({ timeout: 10000 });
    await expect(legendSection).toContainText(/NLCD/i);
  });

  test('raster: soils ssurgo.tif toggles bitmap layer', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Soils');
    const raster = page.getByLabel('Soils (ssurgo.tif)');
    await expect(raster).toBeVisible({ timeout: 15000 });
    await raster.click({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('raster-soils');
    await expect.poll(async () => getDetectedLayer(page, 'soils')).toMatchObject({ visible: true });
    const soils = await getDetectedLayer(page, 'soils');
    expect(soils).not.toBeNull();
    expect(Array.isArray(soils.bounds)).toBeTruthy();
    expect(soils.bounds[0]).toBeGreaterThan(-180);
    expect(soils.bounds[0]).toBeLessThan(180);
    expect(soils.bounds[1]).toBeGreaterThan(-90);
    expect(soils.bounds[1]).toBeLessThan(90);
    expect(soils.hasCanvas || soils.size).toBeTruthy();
    const legendSection = page
      .locator('#gl-legends-content .gl-legend-section')
      .filter({ hasText: 'Soils (ssurgo.tif)' })
      .first();
    await expect(legendSection).toBeVisible({ timeout: 10000 });
  });

  test('Subcatchment Labels toggle shows/hides label layer', async ({ page }) => {
    await openDashboard(page);
    await waitForSubcatchments(page);
    const labelsToggle = page.locator('#gl-subcatchment-labels-toggle');
    await expect(labelsToggle).toBeVisible({ timeout: 15000 });

    await labelsToggle.check({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('subcatchment-labels');

    await labelsToggle.uncheck({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).not.toContain('subcatchment-labels');
  });

  test('RAP cumulative stays selected and panel remains open', async ({ page }) => {
    await openDashboard(page);
    const rapSummary = page.locator('summary.gl-layer-group', { hasText: 'RAP' });
    if ((await rapSummary.count()) === 0) {
      test.skip('RAP section not present in this run');
    }
    await expandSection(page, 'RAP');

    const cumulative = page.getByLabel('Cumulative Cover');
    await expect(cumulative).toBeVisible({ timeout: 15000 });
    await cumulative.click({ force: true });

    await expect(cumulative).toBeChecked({ timeout: 10000 });
    await expect.poll(async () => isDetailsOpen(page, 'RAP')).toBeTruthy();
    await expect.poll(async () =>
      page.evaluate(() => window.glDashboardState?.rapCumulativeMode ?? false),
    ).toBeTruthy();
    await expect.poll(async () => {
      const ids = await getDeckLayerIds(page);
      return ids.some((id) => typeof id === 'string' && id.includes('rap-cumulative'));
    }).toBeTruthy();
  });

  test('WEPP Event selection keeps panel open and renders layer', async ({ page }) => {
    await openDashboard(page);
    const weppEventSummary = page.locator('summary.gl-layer-group', { hasText: 'WEPP Event' });
    if ((await weppEventSummary.count()) === 0) {
      test.skip('WEPP Event section not present in this run');
    }
    await expandSection(page, 'WEPP Event');

    const dateInput = page.locator('#gl-wepp-event-date');
    await expect(dateInput).toBeVisible({ timeout: 15000 });
    const meta = await page.evaluate(() => {
      const m = window.glDashboardState?.weppEventMetadata;
      return m ? { start: m.startDate, end: m.endDate } : null;
    });
    if (!meta || (!meta.start && !meta.end)) {
      test.skip('WEPP Event metadata missing start/end date');
    }
    const dateToUse = meta.end || meta.start;
    await dateInput.evaluate((el, val) => {
      el.value = val;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }, dateToUse);

    const details = weppEventSummary.locator('xpath=..');
    const firstRadio = details.locator('input[type="radio"]').first();
    await expect(firstRadio).toBeVisible({ timeout: 15000 });
    await firstRadio.click({ force: true });

    await expect(firstRadio).toBeChecked({ timeout: 10000 });
    await expect.poll(async () => isDetailsOpen(page, 'WEPP Event')).toBeTruthy();
    await expect.poll(async () =>
      page.evaluate(() => (window.glDashboardState?.weppEventLayers || []).some((l) => l.visible)),
    ).toBeTruthy();
    await expect.poll(async () => {
      const ids = await getDeckLayerIds(page);
      return ids.some((id) => typeof id === 'string' && id.includes('wepp-event'));
    }).toBeTruthy();
  });

  test('Landuse selection persists after scenario change', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Landuse');

    const inrcov = page.getByLabel('Interrill cover (inrcov)');
    await expect(inrcov).toBeVisible({ timeout: 15000 });
    await inrcov.click({ force: true });
    await expect(inrcov).toBeChecked();

    await expect.poll(async () => getDeckLayerIds(page)).toContain('landuse-lu-inrcov');

    const scenarioSelect = page.locator('#gl-scenario-select');
    if ((await scenarioSelect.count()) === 0) {
      test.skip('Scenario selector not available in this run');
    }
    const scenarioOptions = scenarioSelect.locator('option[value]:not([value=""])');
    const optionCount = await scenarioOptions.count();
    if (optionCount === 0) {
      test.skip('No alternate scenarios available');
    }
    const scenarioValue = await scenarioOptions.first().getAttribute('value');
    if (!scenarioValue) {
      test.skip('Scenario option missing value');
    }

    await scenarioSelect.selectOption(scenarioValue);
    await expect.poll(async () =>
      page.evaluate((val) => window.glDashboardState?.currentScenarioPath === val, scenarioValue),
    ).toBeTruthy();

    await expect.poll(async () =>
      page.evaluate(() => {
        const layers = window.glDashboardState?.landuseLayers || [];
        return layers.some((l) => l && l.key === 'lu-inrcov' && l.visible);
      }),
    ).toBeTruthy();

    await expect.poll(async () => getDeckLayerIds(page)).toContain('landuse-lu-inrcov');
  });
});
