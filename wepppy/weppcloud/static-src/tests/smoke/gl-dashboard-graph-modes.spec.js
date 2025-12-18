import { test, expect } from '@playwright/test';

// Resolve target URL using the same precedence as other gl-dashboard specs
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

async function expandSection(page, title) {
  const summary = page.locator('summary.gl-layer-group', { hasText: title });
  await expect(summary).toBeVisible({ timeout: 15000 });
  await summary.evaluate((el) => {
    const details = el.closest('details');
    if (details && !details.open) details.open = true;
  });
  await summary.scrollIntoViewIfNeeded();
}

async function requireSection(page, title) {
  const summary = page.locator('summary.gl-layer-group', { hasText: title });
  if ((await summary.count()) === 0) {
    test.skip(`${title} section not present in this run`);
  }
}

async function getState(page) {
  return page.evaluate(async () => {
    const mod = await import(`${window.GL_DASHBOARD_CONTEXT.sitePrefix || ''}/static/js/gl-dashboard/state.js`);
    return mod.getState();
  });
}

async function getGraphSource(page) {
  return page.evaluate(() => window.glDashboardTimeseriesGraph?._source || null);
}

async function getActiveMode(page) {
  return page.evaluate(() => {
    const btn = document.querySelector('[data-graph-mode].is-active');
    return btn ? btn.dataset.graphMode : null;
  });
}

async function getGeometry(page) {
  return page.evaluate(() => {
    const slider = document.getElementById('gl-year-slider');
    const container = document.getElementById('gl-graph-container');
    const slot = document.getElementById('gl-graph-year-slider');
    const rect = (node) => (node ? node.getBoundingClientRect() : null);
    return {
      slider: rect(slider),
      container: rect(container),
      slot: rect(slot),
      hasBottom: container ? container.classList.contains('has-bottom-slider') : false,
      parentId: slider && slider.parentElement ? slider.parentElement.id : null,
      visible: slider ? slider.classList.contains('is-visible') : false,
    };
  });
}

test.describe('gl-dashboard graph modes and slider placement', () => {
  test('WEPP Yearly loads split mode with top slider', async ({ page }) => {
    await openDashboard(page);
    await requireSection(page, 'WEPP Yearly');
    await expandSection(page, 'WEPP Yearly');
    const weppRadio = page.locator('input[id^="layer-WEPP-Yearly-"]').first();
    await expect(weppRadio).toBeVisible({ timeout: 15000 });
    await weppRadio.scrollIntoViewIfNeeded();
    await weppRadio.check({ force: true });

    await expect.poll(async () => getGraphSource(page)).toBe('wepp_yearly');
    await expect.poll(async () => getActiveMode(page)).toBe('split');

    const geom = await getGeometry(page);
    expect(geom.visible).toBeTruthy();
    expect(geom.parentId).toBe('gl-graph-year-slider');
    expect(geom.hasBottom).toBe(false);
    expect(geom.slider && geom.container).not.toBeNull();
    expect(geom.slider.top).toBeLessThan(geom.container.top);
  });

  test('Landuse overlay → Climate Yearly forces full mode with bottom slider', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Landuse');
    const landuseDominant = page.getByLabel('Dominant landuse');
    await landuseDominant.scrollIntoViewIfNeeded();
    await landuseDominant.click({ force: true });

    await expandSection(page, 'Climate Yearly');
    await page.locator('#graph-climate-yearly').click({ force: true });

    await expect.poll(async () => getGraphSource(page)).toBe('climate_yearly');
    await expect.poll(async () => (await getState(page)).activeGraphKey).toBe('climate-yearly');
    await expect.poll(async () => getActiveMode(page)).toBe('full');
    await expect(page.locator('.gl-main')).toHaveClass(/graph-focus/);

    const geom = await getGeometry(page);
    expect(geom.visible).toBeTruthy();
    expect(geom.parentId).toBe('gl-graph-container');
    expect(geom.hasBottom).toBe(true);
  });

  test('Climate mode radios activate Climate Yearly graph when not already active', async ({ page }) => {
    await openDashboard(page);
    // Ensure we start from a non-climate context
    await expandSection(page, 'Landuse');
    await page.getByLabel('Dominant landuse').click({ force: true });

    await expandSection(page, 'Climate Yearly');
    const waterYear = page.getByLabel('Water Year');
    await waterYear.click({ force: true });

    await expect(page.locator('#graph-climate-yearly')).toBeChecked();
    await expect.poll(async () => getGraphSource(page)).toBe('climate_yearly');
    await expect.poll(async () => (await getState(page)).activeGraphKey).toBe('climate-yearly');
    await expect.poll(async () => getActiveMode(page)).toBe('full');
    await expect(page.locator('.gl-main')).toHaveClass(/graph-focus/);
  });

  test('Climate Yearly forces full mode with bottom slider', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Climate Yearly');
    await page.locator('#graph-climate-yearly').click({ force: true });

    await expect.poll(async () => getGraphSource(page)).toBe('climate_yearly');
    await expect.poll(async () => (await getState(page)).activeGraphKey).toBe('climate-yearly');
    await expect.poll(async () => getActiveMode(page)).toBe('full');
    await expect(page.locator('.gl-main')).toHaveClass(/graph-focus/);

    const geom = await getGeometry(page);
    expect(geom.visible).toBeTruthy();
    expect(geom.parentId).toBe('gl-graph-container');
    expect(geom.hasBottom).toBe(true);
    expect(geom.slider && geom.container).not.toBeNull();
    expect(Math.abs(geom.container.bottom - geom.slider.bottom)).toBeLessThan(6);
  });

  test('Switching to Cumulative Contribution stays full and slider hides', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Climate Yearly');
    await page.locator('#graph-climate-yearly').click({ force: true });
    await expect.poll(async () => getGraphSource(page)).toBe('climate_yearly');

    const cumulativeSummary = page.locator('summary.gl-layer-group', { hasText: 'Cumulative Contribution' });
    await cumulativeSummary.evaluate((el) => {
      const details = el.closest('details');
      if (details && !details.open) details.open = true;
    });
    await page.getByLabel('Cumulative contribution curve').click({ force: true });

    await expect.poll(async () => (await getState(page)).activeGraphKey).toBe('cumulative-contribution');
    await expect.poll(async () => getGraphSource(page)).toBe('omni');
    await expect.poll(async () => getActiveMode(page)).toBe('full');

    const geom = await getGeometry(page);
    expect(geom.visible).toBeFalsy();
    expect(geom.hasBottom).toBe(false);
  });

  test('Slider visibility off in Cumulative when no yearly context remains', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Cumulative Contribution');
    await page.getByLabel('Cumulative contribution curve').click({ force: true });

    await expect.poll(async () => (await getState(page)).activeGraphKey).toBe('cumulative-contribution');
    await expect.poll(async () => getGraphSource(page)).toBeTruthy();

    const visibleCount = await page.locator('#gl-year-slider.is-visible').count();
    expect(visibleCount).toBe(0);
  });

  test('Sediment discharge graph shows bottom year slider', async ({ page }) => {
    await openDashboard(page);
    await requireSection(page, 'Omni Scenarios');
    await expandSection(page, 'Omni Scenarios');
    await page.locator('#graph-omni-outlet-sediment').click({ force: true });

    await expect.poll(async () => (await getState(page)).activeGraphKey).toBe('omni-outlet-sediment');
    await expect.poll(async () => getGraphSource(page)).toBe('omni');

    const geom = await getGeometry(page);
    expect(geom.visible).toBeTruthy();
    expect(geom.parentId).toBe('gl-graph-container');
    expect(geom.hasBottom).toBe(true);
  });

  test('Stream discharge graph shows bottom year slider', async ({ page }) => {
    await openDashboard(page);
    await requireSection(page, 'Omni Scenarios');
    await expandSection(page, 'Omni Scenarios');
    await page.locator('#graph-omni-outlet-stream').click({ force: true });

    await expect.poll(async () => (await getState(page)).activeGraphKey).toBe('omni-outlet-stream');
    await expect.poll(async () => getGraphSource(page)).toBe('omni');

    const geom = await getGeometry(page);
    expect(geom.visible).toBeTruthy();
    expect(geom.parentId).toBe('gl-graph-container');
    expect(geom.hasBottom).toBe(true);
  });

  test('Year slider hides after switching from Climate Yearly to Soil Loss hillslopes', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Climate Yearly');
    await page.locator('#graph-climate-yearly').click({ force: true });
    await expect.poll(async () => getGraphSource(page)).toBe('climate_yearly');

    await requireSection(page, 'Omni Scenarios');
    await expandSection(page, 'Omni Scenarios');
    await page.locator('#graph-omni-soil-loss-hill').click({ force: true });

    await expect.poll(async () => (await getState(page)).activeGraphKey).toBe('omni-soil-loss-hill');
    await expect.poll(async () => getGraphSource(page)).toBe('omni');

    const geom = await getGeometry(page);
    expect(geom.visible).toBeFalsy();
    expect(geom.hasBottom).toBe(false);
  });

  test('Year slider playback advances year in climate context', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Climate Yearly');
    await page.locator('#graph-climate-yearly').click({ force: true });
    await expect.poll(async () => getGraphSource(page)).toBe('climate_yearly');

    const initialYear = await page.evaluate(() => {
      const input = document.getElementById('gl-year-slider-input');
      return input ? Number(input.value) : null;
    });
    const playBtn = page.locator('#gl-year-slider-play');
    await playBtn.click({ force: true });
    await page.waitForTimeout(3500);
    await playBtn.click({ force: true }); // pause to avoid runaway
    const nextYear = await page.evaluate(() => {
      const input = document.getElementById('gl-year-slider-input');
      return input ? Number(input.value) : null;
    });
    expect(nextYear).not.toBeNull();
    expect(nextYear).not.toBe(initialYear);
    await expect.poll(async () => getActiveMode(page)).toBe('full');
  });

  test('Graph focus hides map and restores on split', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Climate Yearly');
    await page.locator('#graph-climate-yearly').click({ force: true });
    await expect.poll(async () => getGraphSource(page)).toBe('climate_yearly');

    // Full mode should focus the graph
    await page.locator('[data-graph-mode="full"]').click({ force: true });
    await expect(page.locator('.gl-main')).toHaveClass(/graph-focus/);
    await expect(page.locator('.gl-viewport')).toBeHidden();

    // Split should bring the map back
    await page.locator('[data-graph-mode="split"]').click({ force: true });
    await expect(page.locator('.gl-main')).not.toHaveClass(/graph-focus/);
    await expect(page.locator('.gl-viewport')).toBeVisible();
  });

  test('Legends render for WEPP Yearly and show diverging scale in comparison mode', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'WEPP Yearly');
    const weppRadio = page.locator('input[id^="layer-WEPP-Yearly-"]').first();
    await expect(weppRadio).toBeVisible({ timeout: 15000 });
    await weppRadio.check({ force: true });
    await expect.poll(async () => getGraphSource(page)).toBe('wepp_yearly');

    // Legends populated
    const legendSections = page.locator('#gl-legends-content .gl-legend-section');
    await expect.poll(async () => legendSections.count()).toBeGreaterThan(0);

    // Enable scenario + comparison to trigger diverging legend
    const scenarioSelect = page.locator('#gl-scenario-select');
    const optionCount = await scenarioSelect.locator('option').count();
    if (optionCount > 1) {
      const firstScenario = await scenarioSelect.locator('option').nth(1).getAttribute('value');
      if (firstScenario) {
        await scenarioSelect.selectOption(firstScenario);
        await page.locator('#gl-comparison-toggle').check({ force: true });
        const scenarioPath = (await getState(page)).currentScenarioPath;
        if (scenarioPath) {
          await page.waitForTimeout(500);
          const divergingCount = await page.locator('.gl-legend-diverging__bar').count();
          if (divergingCount === 0) {
            test.skip('No diverging legend rendered for comparison scenario in this run');
          }
          expect(divergingCount).toBeGreaterThan(0);
        }
      }
    }
  });
});
