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
}

function graphPanel(page) {
  return page.locator('#gl-graph');
}

async function ensureGraphMode(page, mode) {
  const btn = page.locator(`[data-graph-mode="${mode}"]`);
  await expect(btn).toBeVisible();
  const isActive = await btn.evaluate((el) => el.classList.contains('is-active'));
  if (!isActive) {
    await btn.click({ force: true });
  }
}

async function expectCollapsed(page) {
  await expect(graphPanel(page)).toHaveClass(/is-collapsed/, { timeout: 10000 });
}

async function requireSection(page, title) {
  const summary = page.locator('summary.gl-layer-group', { hasText: title });
  if ((await summary.count()) === 0) {
    test.skip(`${title} section not present in this run`);
  }
}

async function clickLanduseDominant(page) {
  await expandSection(page, 'Landuse');
  const landuseDominant = page.getByLabel('Dominant landuse').first();
  await expect(landuseDominant).toBeVisible({ timeout: 15000 });
  await landuseDominant.click({ force: true });
}

test.describe('gl-dashboard state transitions', () => {
  test('Basemap selector updates state and deck layer', async ({ page }) => {
    await openDashboard(page);
    const basemapSelect = page.locator('#gl-basemap-select');
    await basemapSelect.selectOption('osm');
    await expect(basemapSelect).toHaveValue('osm');
    const state = await page.evaluate(async () => {
      const mod = await import(`${window.GL_DASHBOARD_CONTEXT.sitePrefix || ''}/static/js/gl-dashboard/state.js`);
      const deck = window.glDashboardDeck;
      const baseLayer = deck && deck.props && Array.isArray(deck.props.layers) ? deck.props.layers[0] : null;
      return {
        basemap: mod.getState().currentBasemapKey,
        baseLayerData: baseLayer && baseLayer.props ? baseLayer.props.data : null,
      };
    });
    expect(state.basemap).toBe('osm');
    expect(state.baseLayerData || '').toContain('openstreetmap');
  });

  test('RAP → Landuse collapses graph', async ({ page }) => {
    await openDashboard(page);
    await requireSection(page, 'RAP');
    await expandSection(page, 'RAP');
    const rapCumulative = page.getByLabel('Cumulative Cover');
    await rapCumulative.scrollIntoViewIfNeeded();
    await rapCumulative.click({ force: true });
    await clickLanduseDominant(page);
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
    await requireSection(page, 'RAP');
    await expandSection(page, 'RAP');
    const rapCumulative = page.getByLabel('Cumulative Cover');
    await rapCumulative.scrollIntoViewIfNeeded();
    await rapCumulative.click({ force: true });
    await clickLanduseDominant(page);
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
    await requireSection(page, 'RAP');
    await expandSection(page, 'RAP');
    const rapCumulative = page.getByLabel('Cumulative Cover');
    await rapCumulative.scrollIntoViewIfNeeded();
    await rapCumulative.click({ force: true });
    await page.getByRole('button', { name: 'Full graph' }).click();
    const graphHeader = page.locator('#gl-graph h4');
    await expect(graphHeader).toContainText('Cumulative');
    await expect(graphPanel(page)).not.toHaveClass(/is-collapsed/);
  });

  test('Cumulative contribution: select Soil Loss and add scenario', async ({ page }) => {
    await openDashboard(page);
    const cumulativeSummary = page.locator('summary.gl-layer-group', { hasText: 'Cumulative Contribution' });
    await cumulativeSummary.evaluate((el) => {
      const details = el.closest('details');
      if (details && !details.open) details.open = true;
    });
    await page.getByLabel('Cumulative contribution curve').click({ force: true });
    const measureSelect = page.locator('#gl-cumulative-measure');
    await measureSelect.selectOption({ value: 'soil_loss' });
    const firstScenario = page.locator('[id^="gl-cumulative-scenario-"]').first();
    if (await firstScenario.count()) {
      await firstScenario.check({ force: true });
    }
    const graphHeader = page.locator('#gl-graph h4');
    await expect(graphHeader).toContainText('Cumulative Contribution');
    const graphData = await page.evaluate(() => {
      const g = window.glDashboardTimeseriesGraph;
      return g && g._data ? { hasData: !!g._data.series, source: g._data.source } : null;
    });
    expect(graphData).not.toBeNull();
    expect(graphData.hasData).toBeTruthy();
  });

  test('Climate yearly graph renders with Soil Loss and scenario', async ({ page }) => {
    await openDashboard(page);
    const climateSummary = page.locator('summary.gl-layer-group', { hasText: 'Climate Yearly' });
    await climateSummary.evaluate((el) => {
      const details = el.closest('details');
      if (details && !details.open) details.open = true;
    });
    // Select the climate yearly graph
    await page.locator('#graph-climate-yearly').click({ force: true });
    await expect.poll(async () => {
      return page.evaluate(async () => {
        const mod = await import(`${window.GL_DASHBOARD_CONTEXT.sitePrefix || ''}/static/js/gl-dashboard/state.js`);
        return mod.getState().activeGraphKey;
      });
    }).toBe('climate-yearly');

    // Ensure Water Year mode and set start month to October
    const waterYearRadio = page.getByLabel('Water Year');
    await waterYearRadio.click({ force: true });
    await page.evaluate(() => {
      const radios = Array.from(document.querySelectorAll('input[type=\"radio\"]'));
      const water = radios.find((r) => r.nextElementSibling && r.nextElementSibling.textContent.includes('Water Year'));
      if (water) {
        water.checked = true;
        water.dispatchEvent(new Event('change', { bubbles: true }));
      }
      const startSelect = Array.from(document.querySelectorAll('select')).find((sel) =>
        Array.from(sel.options || []).some((o) => o.textContent === 'Oct')
      );
      if (startSelect) {
        startSelect.value = Array.from(startSelect.options).find((o) => o.textContent === 'Oct').value;
        startSelect.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });

    // Set measure to Soil Loss (t)
    await page.evaluate(() => {
      const sel = document.getElementById('gl-cumulative-measure');
      if (sel) {
        sel.value = 'soil_loss';
        sel.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });

    // Enable the first scenario checkbox if present
    const firstScenario = page.locator('[id^="gl-cumulative-scenario-"]').first();
    if (await firstScenario.count()) {
      await page.evaluate(() => {
        const cb = document.querySelector('[id^=\"gl-cumulative-scenario-\"]');
        if (cb) {
          cb.checked = true;
          cb.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
    }

    // Expect graph data to be populated for climate yearly
    const graphData = await expect.poll(async () =>
      page.evaluate(() => {
        const g = window.glDashboardTimeseriesGraph;
        return g && g._data ? { type: g._data.type, source: g._data.source, hasPrecip: !!g._data.precipSeries } : null;
      })
    ).toEqual({ type: 'climate-yearly', source: 'climate_yearly', hasPrecip: true });
  });

  test('Climate yearly slider anchors to bottom in full mode', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Climate Yearly');
    await page.locator('#graph-climate-yearly').click({ force: true });
    await expect.poll(async () =>
      page.evaluate(async () => {
        const mod = await import(`${window.GL_DASHBOARD_CONTEXT.sitePrefix || ''}/static/js/gl-dashboard/state.js`);
        return mod.getState().activeGraphKey;
      })
    ).toBe('climate-yearly');
    await ensureGraphMode(page, 'full');

    const slider = page.locator('#gl-year-slider');
    await expect(slider).toHaveClass(/is-visible/, { timeout: 10000 });
    const parentId = await slider.evaluate((el) => (el.parentElement ? el.parentElement.id : null));
    expect(parentId).toBe('gl-graph-container');
    await expect(page.locator('#gl-graph-container')).toHaveClass(/has-bottom-slider/);
    await expect(page.locator('[data-graph-mode="full"]')).toHaveClass(/is-active/);
    await expect(page.locator('.gl-main')).toHaveClass(/graph-focus/);

    const geom = await page.evaluate(() => {
      const s = document.getElementById('gl-year-slider')?.getBoundingClientRect();
      const c = document.getElementById('gl-graph-container')?.getBoundingClientRect();
      return s && c
        ? { sliderBottom: s.bottom, containerBottom: c.bottom }
        : null;
    });
    expect(geom).not.toBeNull();
    expect(Math.abs(geom.containerBottom - geom.sliderBottom)).toBeLessThan(6);
  });

  test('WEPP yearly slider anchors above graph in split mode', async ({ page }) => {
    await openDashboard(page);
    await requireSection(page, 'WEPP Yearly');
    await expandSection(page, 'WEPP Yearly');
    const weppRadio = page.locator('input[id^="layer-WEPP-Yearly-"]').first();
    await expect(weppRadio).toBeVisible({ timeout: 15000 });
    await weppRadio.scrollIntoViewIfNeeded();
    await weppRadio.check({ force: true });
    await ensureGraphMode(page, 'split');

    await expect.poll(async () =>
      page.evaluate(() => (window.glDashboardTimeseriesGraph ? window.glDashboardTimeseriesGraph._source : null))
    ).toBe('wepp_yearly');

    const slider = page.locator('#gl-year-slider');
    await expect(slider).toHaveClass(/is-visible/, { timeout: 10000 });
    const parentId = await slider.evaluate((el) => (el.parentElement ? el.parentElement.id : null));
    expect(parentId).toBe('gl-graph-year-slider');
    await expect(page.locator('#gl-graph-container')).not.toHaveClass(/has-bottom-slider/);
    await expect(page.locator('[data-graph-mode="split"]')).toHaveClass(/is-active/);
    await expect(page.locator('.gl-main')).not.toHaveClass(/graph-focus/);

    const geom = await page.evaluate(() => {
      const s = document.getElementById('gl-year-slider')?.getBoundingClientRect();
      const c = document.getElementById('gl-graph-container')?.getBoundingClientRect();
      return s && c ? { sliderTop: s.top, containerTop: c.top } : null;
    });
    expect(geom).not.toBeNull();
    expect(geom.sliderTop).toBeLessThan(geom.containerTop);
  });

  test('Year slider stays in climate context when switching between WEPP and Climate', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Climate Yearly');
    await page.locator('#graph-climate-yearly').click({ force: true });
    await expect.poll(async () =>
      page.evaluate(async () => {
        const mod = await import(`${window.GL_DASHBOARD_CONTEXT.sitePrefix || ''}/static/js/gl-dashboard/state.js`);
        return mod.getState().activeGraphKey;
      })
    ).toBe('climate-yearly');
    await page.evaluate(() => {
      if (!window.__graphLoads) window.__graphLoads = [];
      if (window.activateGraphItem && !window.activateGraphItem.__wrapped) {
        const orig = window.activateGraphItem;
        const wrapped = async (...args) => {
          window.__graphLoads.push(args[0]);
          return orig.apply(window, args);
        };
        wrapped.__wrapped = true;
        window.activateGraphItem = wrapped;
      }
    });

    await expandSection(page, 'WEPP Yearly');
    const weppRadio = page.locator('input[id^="layer-WEPP-Yearly-"]').first();
    await weppRadio.scrollIntoViewIfNeeded();
    await weppRadio.check({ force: true });
    await expect.poll(async () =>
      page.evaluate(() => (window.glDashboardTimeseriesGraph ? window.glDashboardTimeseriesGraph._source : null))
    ).toBe('wepp_yearly');
    const afterWeppParent = await page.locator('#gl-year-slider').evaluate((el) => (el.parentElement ? el.parentElement.id : null));
    expect(afterWeppParent).toBe('gl-graph-year-slider');

    await page.evaluate(async () => {
      const mod = await import(`${window.GL_DASHBOARD_CONTEXT.sitePrefix || ''}/static/js/gl-dashboard/state.js`);
      if (mod && mod.setValue) {
        mod.setValue('activeGraphKey', null);
      }
      const radio = document.getElementById('graph-climate-yearly');
      if (radio) radio.checked = false;
    });
    await page.locator('#graph-climate-yearly').check({ force: true });
    const afterClimateIndex = await page.evaluate(() => (window.__graphLoads || []).length);
    await expect.poll(async () =>
      page.evaluate(async () => {
        const mod = await import(`${window.GL_DASHBOARD_CONTEXT.sitePrefix || ''}/static/js/gl-dashboard/state.js`);
        return { key: mod.getState().activeGraphKey, source: window.glDashboardTimeseriesGraph?._source || null };
      })
    ).toEqual({ key: 'climate-yearly', source: 'climate_yearly' });

    await page.waitForTimeout(2000);
    const finalParent = await page.locator('#gl-year-slider').evaluate((el) => (el.parentElement ? el.parentElement.id : null));
    expect(finalParent).toBe('gl-graph-container');
    await expect(page.locator('#gl-graph-container')).toHaveClass(/has-bottom-slider/);

    const newCalls = await page.evaluate(
      (idx) => (window.__graphLoads || []).slice(idx),
      afterClimateIndex
    );
    expect(newCalls.some((k) => String(k).includes('wepp'))).toBeFalsy();
  });

  test('RAP slider uses top slot and updates selected year', async ({ page }) => {
    await openDashboard(page);
    await requireSection(page, 'RAP');
    await expandSection(page, 'RAP');
    const rapCumulative = page.getByLabel('Cumulative Cover');
    await rapCumulative.scrollIntoViewIfNeeded();
    await rapCumulative.click({ force: true });
    await ensureGraphMode(page, 'split');

    const slider = page.locator('#gl-year-slider');
    await expect(slider).toHaveClass(/is-visible/, { timeout: 10000 });
    const parentId = await slider.evaluate((el) => (el.parentElement ? el.parentElement.id : null));
    expect(parentId).toBe('gl-graph-year-slider');
    await expect(page.locator('#gl-graph-container')).not.toHaveClass(/has-bottom-slider/);
    await expect(page.locator('[data-graph-mode="split"]')).toHaveClass(/is-active/);
    await expect(page.locator('.gl-main')).not.toHaveClass(/graph-focus/);

    const yearInfo = await page.evaluate(async () => {
      const mod = await import(`${window.GL_DASHBOARD_CONTEXT.sitePrefix || ''}/static/js/gl-dashboard/state.js`);
      const st = mod.getState();
      const years = st.rapMetadata && Array.isArray(st.rapMetadata.years) ? st.rapMetadata.years : [];
      const min = years.length ? years[0] : null;
      const max = years.length ? years[years.length - 1] : null;
      return { current: st.rapSelectedYear, min, max };
    });
    expect(yearInfo.min).not.toBeNull();
    expect(yearInfo.max).not.toBeNull();
    const nextYear = yearInfo.current === yearInfo.max ? yearInfo.min : yearInfo.max;

    await page.evaluate((year) => {
      const input = document.getElementById('gl-year-slider-input');
      if (input) {
        input.value = String(year);
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }, nextYear);

    await expect.poll(async () =>
      page.evaluate(async () => {
        const mod = await import(`${window.GL_DASHBOARD_CONTEXT.sitePrefix || ''}/static/js/gl-dashboard/state.js`);
        return mod.getState().rapSelectedYear;
      })
    ).toBe(nextYear);
  });

  test('Year slider hides when leaving graph-capable contexts', async ({ page }) => {
    await openDashboard(page);
    await expandSection(page, 'Landuse');
    const landuseDominant = page.getByLabel('Dominant landuse');
    await landuseDominant.scrollIntoViewIfNeeded();
    await landuseDominant.click({ force: true });
    await ensureGraphMode(page, 'minimized');
    await expectCollapsed(page);
    await expect(page.locator('#gl-year-slider')).not.toHaveClass(/is-visible/, { timeout: 10000 });
  });

  test('Non-graph overlays hide the year slider (Landuse/Soils/WEPP/WATAR)', async ({ page }) => {
    await openDashboard(page);
    // Show the slider via a graph-capable context.
    await requireSection(page, 'RAP');
    await expandSection(page, 'RAP');
    const rapCumulative = page.getByLabel('Cumulative Cover');
    await rapCumulative.scrollIntoViewIfNeeded();
    await rapCumulative.click({ force: true });
    const slider = page.locator('#gl-year-slider');
    await expect(slider).toHaveClass(/is-visible/, { timeout: 10000 });

    const overlays = [
      { locator: page.locator('summary.gl-layer-group', { hasText: 'Landuse' }), selector: 'input[id^="layer-Landuse-"]' },
      { locator: page.locator('summary.gl-layer-group', { hasText: 'Soils' }), selector: 'input[id^="layer-Soils-"]' },
      { locator: page.locator('summary.gl-layer-group', { hasText: /^WEPP$/ }), selector: 'input[id^="layer-WEPP-"]' },
      { locator: page.locator('summary.gl-layer-group', { hasText: 'WATAR' }), selector: 'input[id^="layer-WATAR-"]' },
    ];

    for (const { locator, selector } of overlays) {
      const summary = locator.first();
      await expect(summary).toBeVisible({ timeout: 15000 });
      await summary.evaluate((el) => {
        const details = el.closest('details');
        if (details && !details.open) details.open = true;
      });
      await summary.scrollIntoViewIfNeeded();

      const input = page.locator(selector).first();
      if (await input.count()) {
        await input.scrollIntoViewIfNeeded();
        await input.click({ force: true });
        await expect(slider).not.toHaveClass(/is-visible/, { timeout: 8000 });
      }
    }
  });
});
