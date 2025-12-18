import { test, expect } from '@playwright/test';

// Resolve target URL with the same precedence as other gl-dashboard specs
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

test.describe('gl-dashboard layer detection and wiring', () => {
  test('layer controls render and toggling updates the deck stack', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Landuse');

    const dominant = page.getByLabel('Dominant landuse');
    await expect(dominant).toBeVisible({ timeout: 15000 });

    // Layer list should have populated entries once detection finishes.
    const listItems = await page.locator('#gl-layer-list li').count();
    expect(listItems).toBeGreaterThan(0);

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
  });
});
