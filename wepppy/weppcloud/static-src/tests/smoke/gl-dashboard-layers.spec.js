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

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function expandSection(page, title) {
  const summary = page.locator('summary.gl-layer-group').filter({
    hasText: new RegExp(`^${escapeRegExp(title)}$`),
  });
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

async function waitForChannels(page, timeout = 20000) {
  try {
    await page.waitForFunction(
      () => (window.glDashboardState?.channelsGeoJson?.features || []).length > 0,
      { timeout },
    );
    return true;
  } catch (err) {
    return false;
  }
}

async function waitForWeppChannelLayers(page, timeout = 20000) {
  try {
    await page.waitForFunction(
      () => (window.glDashboardState?.weppChannelLayers || []).length > 0,
      { timeout },
    );
    return true;
  } catch (err) {
    return false;
  }
}

async function waitForWeppYearlyChannelLayers(page, timeout = 20000) {
  try {
    await page.waitForFunction(
      () => (window.glDashboardState?.weppYearlyChannelLayers || []).length > 0,
      { timeout },
    );
    return true;
  } catch (err) {
    return false;
  }
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

  test('Channels overlay toggles and legend updates', async ({ page }) => {
    await openDashboard(page);
    const hasChannels = await waitForChannels(page);
    if (!hasChannels) {
      test.skip('Channels data not available in this run');
    }

    const channelsToggle = page.locator('#gl-channels-toggle');
    await expect(channelsToggle).toBeVisible({ timeout: 15000 });
    await expect(channelsToggle).toBeChecked();

    await expect.poll(async () => getDeckLayerIds(page)).toContain('channels-pass2');
    const channelLegendTitle = page.locator('#gl-legends-content .gl-legend-section__title', { hasText: 'Channel Order' });
    await expect(channelLegendTitle).toBeVisible({ timeout: 15000 });

    await channelsToggle.uncheck({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).not.toContain('channels-pass2');
    await expect.poll(async () => channelLegendTitle.count()).toBe(0);

    await channelsToggle.check({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('channels-pass2');
    await expect.poll(async () => channelLegendTitle.count()).toBeGreaterThan(0);
  });

  test('Channel labels toggle shows/hides label layer', async ({ page }) => {
    await openDashboard(page);
    const hasChannels = await waitForChannels(page);
    if (!hasChannels) {
      test.skip('Channels data not available in this run');
    }

    const channelsToggle = page.locator('#gl-channels-toggle');
    if (await channelsToggle.isVisible()) {
      await channelsToggle.check({ force: true });
    }
    await expect.poll(async () => getDeckLayerIds(page)).toContain('channels-pass2');

    const labelsToggle = page.locator('#gl-channel-labels-toggle');
    await expect(labelsToggle).toBeVisible({ timeout: 15000 });
    await expect(labelsToggle).not.toBeChecked();

    await labelsToggle.check({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('channel-labels');

    await labelsToggle.uncheck({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).not.toContain('channel-labels');
  });

  test('WEPP channel overlays stay independent from hillslope overlays', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'WEPP');

    const runoffToggle = page.getByRole('radio', { name: /^Runoff \(mm\)\b/ });
    if ((await runoffToggle.count()) === 0) {
      test.skip('WEPP hillslope overlays not available in this run');
    }

    const hasWeppChannels = await waitForWeppChannelLayers(page);
    if (!hasWeppChannels) {
      test.skip('WEPP channel overlays not available in this run');
    }

    await expect(runoffToggle).toBeVisible({ timeout: 15000 });
    await runoffToggle.first().click({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('wepp-wepp-runoff');

    const dischargeToggle = page.locator('label[for^="layer-WEPP-Channel-"]', { hasText: 'Discharge Volume (m^3)' });
    await expect(dischargeToggle).toBeVisible({ timeout: 15000 });
    await dischargeToggle.click({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('wepp-channel-wepp-channel-discharge');
    await expect.poll(async () => getDeckLayerIds(page)).toContain('wepp-wepp-runoff');

    const dischargeLegend = page
      .locator('#gl-legends-content .gl-legend-section')
      .filter({ hasText: 'Discharge Volume' })
      .first();
    await expect(dischargeLegend).toBeVisible({ timeout: 10000 });

    const soilLossToggle = page.locator('label[for^="layer-WEPP-Channel-"]', { hasText: 'Soil Loss (kg)' });
    await expect(soilLossToggle).toBeVisible({ timeout: 15000 });
    await soilLossToggle.click({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('wepp-channel-wepp-channel-soil-loss');
    await expect.poll(async () => getDeckLayerIds(page)).not.toContain('wepp-channel-wepp-channel-discharge');
    await expect.poll(async () => getDeckLayerIds(page)).toContain('wepp-wepp-runoff');

    const soilLossLegend = page
      .locator('#gl-legends-content .gl-legend-section')
      .filter({ hasText: 'Soil Loss (kg)' })
      .first();
    await expect(soilLossLegend).toBeVisible({ timeout: 10000 });
  });

  test('WEPP channel radios stay in sync with WEPP Yearly channels', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'WEPP');
    const hasWeppChannels = await waitForWeppChannelLayers(page);
    if (!hasWeppChannels) {
      test.skip('WEPP channel overlays not available in this run');
    }

    await expandSection(page, 'WEPP Yearly');
    const hasWeppYearlyChannels = await waitForWeppYearlyChannelLayers(page);
    if (!hasWeppYearlyChannels) {
      test.skip('WEPP yearly channel overlays not available in this run');
    }

    const weppDischarge = page.locator('label[for^="layer-WEPP-Channel-"]', { hasText: 'Discharge Volume (m^3)' });
    await expect(weppDischarge).toBeVisible({ timeout: 15000 });
    await weppDischarge.click({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('wepp-channel-wepp-channel-discharge');

    const yearlyDischarge = page.locator('label[for^="layer-WEPP-Yearly-Channel-"]', { hasText: 'Discharge Volume (m^3)' });
    await expect(yearlyDischarge).toBeVisible({ timeout: 15000 });
    await yearlyDischarge.click({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('wepp-yearly-channel-wepp-yearly-channel-discharge');
    await expect.poll(async () => getDeckLayerIds(page)).not.toContain('wepp-channel-wepp-channel-discharge');

    const weppDischargeInput = page.locator('#layer-WEPP-Channel-wepp-channel-discharge');
    await expect(weppDischargeInput).not.toBeChecked();

    const weppSoilLoss = page.locator('label[for^="layer-WEPP-Channel-"]', { hasText: 'Soil Loss (kg)' });
    await expect(weppSoilLoss).toBeVisible({ timeout: 15000 });
    await weppSoilLoss.click({ force: true });
    await expect.poll(async () => getDeckLayerIds(page)).toContain('wepp-channel-wepp-channel-soil-loss');
    await expect.poll(async () => getDeckLayerIds(page)).not.toContain('wepp-yearly-channel-wepp-yearly-channel-discharge');

    const yearlyDischargeInput = page.locator('#layer-WEPP-Yearly-Channel-wepp-yearly-channel-discharge');
    await expect(yearlyDischargeInput).not.toBeChecked();
  });

  test('Channel Order radio stays exclusive with WEPP channel overlays', async ({ page }) => {
    await openDashboard(page);
    const hasChannels = await waitForChannels(page);
    if (!hasChannels) {
      test.skip('Channels data not available in this run');
    }

    const hasWeppChannels = await waitForWeppChannelLayers(page);
    if (!hasWeppChannels) {
      test.skip('WEPP channel overlays not available in this run');
    }

    await expandSection(page, 'Channels');
    const channelOrder = page.locator('#layer-Channels-channel-order');
    await expect(channelOrder).toBeVisible({ timeout: 15000 });
    await channelOrder.check({ force: true });
    await expect(channelOrder).toBeChecked();

    await expandSection(page, 'WEPP');
    const weppDischarge = page.locator('label[for^="layer-WEPP-Channel-"]', { hasText: 'Discharge Volume (m^3)' });
    await expect(weppDischarge).toBeVisible({ timeout: 15000 });
    await weppDischarge.click({ force: true });

    await expect(channelOrder).not.toBeChecked();
    await expect.poll(async () => getDeckLayerIds(page)).toContain('wepp-channel-wepp-channel-discharge');
    await expect.poll(async () => getDeckLayerIds(page)).not.toContain('channels-pass2');

    await expandSection(page, 'Channels');
    await channelOrder.check({ force: true });
    await expect(channelOrder).toBeChecked();

    const weppDischargeInput = page.locator('#layer-WEPP-Channel-wepp-channel-discharge');
    await expect(weppDischargeInput).not.toBeChecked();
    await expect.poll(async () => getDeckLayerIds(page)).toContain('channels-pass2');
    await expect.poll(async () => getDeckLayerIds(page)).not.toContain('wepp-channel-wepp-channel-discharge');

    const hasWeppYearlyChannels = await waitForWeppYearlyChannelLayers(page);
    if (!hasWeppYearlyChannels) {
      return;
    }

    await expandSection(page, 'WEPP Yearly');
    const yearlyDischarge = page.locator('label[for^="layer-WEPP-Yearly-Channel-"]', { hasText: 'Discharge Volume (m^3)' });
    await expect(yearlyDischarge).toBeVisible({ timeout: 15000 });
    await yearlyDischarge.click({ force: true });

    await expect(channelOrder).not.toBeChecked();
    await expect.poll(async () => getDeckLayerIds(page)).toContain('wepp-yearly-channel-wepp-yearly-channel-discharge');
    await expect.poll(async () => getDeckLayerIds(page)).not.toContain('channels-pass2');

    await expandSection(page, 'Channels');
    await channelOrder.check({ force: true });
    const yearlyDischargeInput = page.locator('#layer-WEPP-Yearly-Channel-wepp-yearly-channel-discharge');
    await expect(yearlyDischargeInput).not.toBeChecked();
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

  test('Sidebar controls share the same width', async ({ page }) => {
    await openDashboard(page);
    const basemapSelect = page.locator('#gl-basemap-select');
    await expect(basemapSelect).toBeVisible({ timeout: 15000 });

    const weppEventSummary = page.locator('summary.gl-layer-group', { hasText: 'WEPP Event' });
    if ((await weppEventSummary.count()) === 0) {
      test.skip('WEPP Event section not present in this run');
    }
    await expandSection(page, 'WEPP Event');

    const dateInput = page.locator('#gl-wepp-event-date');
    if ((await dateInput.count()) === 0) {
      test.skip('WEPP Event date input not available in this run');
    }
    await expect(dateInput).toBeVisible({ timeout: 15000 });

    const climateSummary = page.locator('summary.gl-layer-group', { hasText: 'Climate Yearly' });
    if ((await climateSummary.count()) === 0) {
      test.skip('Climate Yearly graph section not present in this run');
    }
    await expandSection(page, 'Climate Yearly');

    const climateSelect = page.locator('#gl-climate-start-month');
    if ((await climateSelect.count()) === 0) {
      test.skip('Climate start month select not available in this run');
    }
    await expect(climateSelect).toBeVisible({ timeout: 15000 });

    const widths = await page.evaluate(() => {
      const basemap = document.getElementById('gl-basemap-select');
      const date = document.getElementById('gl-wepp-event-date');
      const climate = document.getElementById('gl-climate-start-month');
      if (!basemap || !date || !climate) return null;
      return {
        basemap: basemap.getBoundingClientRect().width,
        date: date.getBoundingClientRect().width,
        climate: climate.getBoundingClientRect().width,
      };
    });

    if (!widths) {
      test.skip('Width comparison controls missing');
    }

    expect(Math.abs(widths.date - widths.basemap)).toBeLessThanOrEqual(1);
    expect(Math.abs(widths.climate - widths.basemap)).toBeLessThanOrEqual(1);
  });

  test('WEPP Yearly to OpenET switches graph context to monthly slider', async ({ page }) => {
    await openDashboard(page);
    const weppYearlySummary = page.locator('summary.gl-layer-group', { hasText: 'WEPP Yearly' });
    if ((await weppYearlySummary.count()) === 0) {
      test.skip('WEPP Yearly section not present in this run');
    }
    await expandSection(page, 'WEPP Yearly');

    const weppYearlyRadio = page.locator('input[id^="layer-WEPP-Yearly-"]');
    if ((await weppYearlyRadio.count()) === 0) {
      test.skip('WEPP Yearly layers not available in this run');
    }
    await expect(weppYearlyRadio.first()).toBeVisible({ timeout: 15000 });
    await weppYearlyRadio.first().click({ force: true });
    await expect.poll(async () =>
      page.evaluate(() => window.glDashboardTimeseriesGraph?._source || null),
    ).toBe('wepp_yearly');

    const openetSummary = page.locator('summary.gl-layer-group', { hasText: 'OpenET' });
    if ((await openetSummary.count()) === 0) {
      test.skip('OpenET section not present in this run');
    }
    await expandSection(page, 'OpenET');

    const openetLayer = await page.evaluate(() => {
      const layers = window.glDashboardState?.openetLayers || [];
      if (!layers.length) return null;
      const ensemble = layers.find((layer) => layer.datasetKey === 'ensemble');
      const target = ensemble || layers[0];
      return target ? `layer-OpenET-${target.key}` : null;
    });
    if (!openetLayer) {
      test.skip('OpenET layers not available in state');
    }

    const radio = page.locator(`#${openetLayer}`);
    await expect(radio).toBeVisible({ timeout: 15000 });
    await radio.click({ force: true });

    await expect.poll(async () =>
      page.evaluate(() => window.glDashboardTimeseriesGraph?._source || null),
    ).toBe('openet');
    await expect.poll(async () =>
      page.evaluate(() => document.getElementById('gl-month-slider')?.classList.contains('is-visible') || false),
    ).toBeTruthy();
    await expect.poll(async () =>
      page.evaluate(() => document.getElementById('gl-year-slider')?.classList.contains('is-visible') || false),
    ).toBeFalsy();
  });

  test('OpenET selection shows monthly slider and renders layer', async ({ page }) => {
    await openDashboard(page);
    const openetSummary = page.locator('summary.gl-layer-group', { hasText: 'OpenET' });
    if ((await openetSummary.count()) === 0) {
      test.skip('OpenET section not present in this run');
    }
    await expandSection(page, 'OpenET');

    const openetLayer = await page.evaluate(() => {
      const layers = window.glDashboardState?.openetLayers || [];
      if (!layers.length) return null;
      return { id: `layer-OpenET-${layers[0].key}` };
    });
    if (!openetLayer) {
      test.skip('OpenET layers not available in state');
    }

    const radio = page.locator(`#${openetLayer.id}`);
    await expect(radio).toBeVisible({ timeout: 15000 });
    await radio.click({ force: true });

    await expect.poll(async () =>
      page.evaluate(() => document.getElementById('gl-month-slider')?.classList.contains('is-visible') || false),
    ).toBeTruthy();
    await expect.poll(async () =>
      page.evaluate(() => document.getElementById('gl-year-slider')?.classList.contains('is-visible') || false),
    ).toBeFalsy();
    await expect.poll(async () => {
      const ids = await getDeckLayerIds(page);
      return ids.some((id) => typeof id === 'string' && id.includes('openet-'));
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
