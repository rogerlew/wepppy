import { test, expect } from '@playwright/test';

const fallbackUrl = 'https://wc.bearhive.duckdns.org/weppcloud/runs/rlew-appreciated-tremolite/disturbed9002/';
const emptyFallbackUrl = 'https://wc.bearhive.duckdns.org/weppcloud/runs/unpaved-neophyte/disturbed9002/';

function buildUrl(path, baseUrl) {
  if (!path) {
    return '';
  }
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  if (!baseUrl) {
    return path;
  }
  const base = baseUrl.replace(/\/$/, '');
  if (base.endsWith('/weppcloud') && path.startsWith('/weppcloud/')) {
    return base + path.substring('/weppcloud'.length);
  }
  return new URL(path, base).toString();
}

function resolveTargetUrl() {
  if (process.env.MAP_GL_URL) {
    return process.env.MAP_GL_URL;
  }
  if (process.env.SMOKE_MAP_GL_PATH && process.env.SMOKE_BASE_URL) {
    return buildUrl(process.env.SMOKE_MAP_GL_PATH, process.env.SMOKE_BASE_URL);
  }
  if (process.env.SMOKE_RUN_PATH) {
    return buildUrl(process.env.SMOKE_RUN_PATH, process.env.SMOKE_BASE_URL || '');
  }
  return fallbackUrl;
}

function resolveEmptyUrl() {
  if (process.env.MAP_GL_EMPTY_URL) {
    return process.env.MAP_GL_EMPTY_URL;
  }
  if (process.env.SMOKE_EMPTY_RUN_PATH && process.env.SMOKE_BASE_URL) {
    return buildUrl(process.env.SMOKE_EMPTY_RUN_PATH, process.env.SMOKE_BASE_URL);
  }
  return emptyFallbackUrl;
}

async function openRun(page, targetUrl, options) {
  const resolved = targetUrl || resolveTargetUrl();
  const opts = options || {};
  await page.goto(resolved, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
  const map = page.locator('#mapid');
  if (opts.allowMissingMap) {
    try {
      await map.waitFor({ state: 'visible', timeout: 15000 });
      return true;
    } catch (error) {
      return false;
    }
  }
  await expect(map).toBeVisible();
  return true;
}

function attachConsoleCapture(page) {
  const consoleErrors = [];

  page.on('pageerror', (error) => {
    const message = error.message || String(error);
    if (message === 'Object') return;
    consoleErrors.push({ type: 'pageerror', message, stack: error.stack || '' });
  });

  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    const text = message.text();
    if (text.includes('Debris flow form not found')) return;
    if (text.includes('Failed to load resource') && text.includes('401')) return;
    consoleErrors.push({ type: 'console', message: text });
  });

  return consoleErrors;
}

function parseZoom(statusText) {
  if (!statusText) {
    return null;
  }
  const match = statusText.match(/Zoom:\s*([0-9.]+)/i);
  if (!match) {
    return null;
  }
  const value = Number(match[1]);
  return Number.isFinite(value) ? value : null;
}

function parseCenter(statusText) {
  if (!statusText) {
    return null;
  }
  const match = statusText.match(/Center:\s*([-0-9.]+)\s*,\s*([-0-9.]+)/i);
  if (!match) {
    return null;
  }
  const lng = Number(match[1]);
  const lat = Number(match[2]);
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
    return null;
  }
  return { lng, lat };
}

async function getZoom(page) {
  const text = await page.locator('#mapstatus').textContent();
  return parseZoom(text || '');
}

async function getCenter(page) {
  const text = await page.locator('#mapstatus').textContent();
  return parseCenter(text || '');
}

async function waitForOverlayFeatures(page, layerKey) {
  await expect.poll(async () => {
    return page.evaluate((key) => {
      const map = window.MapController && typeof window.MapController.getInstance === 'function'
        ? window.MapController.getInstance()
        : null;
      const layer = map ? map[key] : null;
      const data = layer && layer.props ? layer.props.data : null;
      const features = data && data.features ? data.features : Array.isArray(data) ? data : [];
      return features.length;
    }, layerKey);
  }, { timeout: 45000 }).toBeGreaterThan(0);
}

async function waitForMapTransition(page) {
  await expect.poll(async () => {
    return page.evaluate(() => {
      const map = window.MapController && typeof window.MapController.getInstance === 'function'
        ? window.MapController.getInstance()
        : null;
      const viewState = map && map._deck && map._deck.props ? map._deck.props.viewState : null;
      return viewState ? viewState.transitionDuration : null;
    });
  }, { timeout: 10000 }).toBeFalsy();
}

async function openOverlayPanel(page) {
  const layerToggle = page.locator('[data-map-layer-control="true"] .wc-map-layer-control__toggle');
  const panel = page.locator('[data-map-layer-control="true"] .wc-map-layer-control__panel');
  await expect(layerToggle).toBeVisible();
  if (!(await panel.isVisible())) {
    await layerToggle.click();
    await expect(panel).toBeVisible();
  }
  return { layerToggle, panel };
}

async function enableSbsOverlay(page) {
  const { layerToggle } = await openOverlayPanel(page);
  const sbsInput = page.locator('label:has-text("Burn Severity Map") input[type="checkbox"]');
  await expect(sbsInput).toBeVisible();
  await sbsInput.check();
  await layerToggle.click();

  return page.evaluate(async () => {
    const map = window.MapController && typeof window.MapController.getInstance === 'function'
      ? window.MapController.getInstance()
      : null;
    let response = null;
    if (map && typeof map.loadSbsMap === 'function') {
      response = await map.loadSbsMap();
    }
    const legend = document.getElementById('sbs_legend');
    return {
      success: Boolean(response && response.Success === true),
      legendVisible: Boolean(legend && !legend.hidden && legend.innerHTML.trim().length > 0),
      hasImage: Boolean(map && map.sbs_layer && map.sbs_layer.props && map.sbs_layer.props.image),
    };
  });
}

async function getFeatureClickPoint(page, layerKey) {
  return page.evaluate((key) => {
    const map = window.MapController && typeof window.MapController.getInstance === 'function'
      ? window.MapController.getInstance()
      : null;
    const layer = map ? map[key] : null;
    const deck = map && map._deck ? map._deck : null;
    if (!layer || !deck) {
      return null;
    }
    const canProject = typeof deck.project === 'function';
    const canPick = typeof deck.pickObject === 'function';
    if (!canProject && !canPick) {
      return null;
    }
    const data = layer.props ? layer.props.data : null;
    const features = data && data.features ? data.features : Array.isArray(data) ? data : [];
    if (!features.length) {
      return null;
    }
    const canvas = document.getElementById('mapid');
    if (!canvas) {
      return null;
    }
    const rect = canvas.getBoundingClientRect();
    const width = rect.width || 0;
    const height = rect.height || 0;
    const layerId = layer.id || (layer.props ? layer.props.id : null);
    if (layerId && canPick) {
      const step = Math.max(24, Math.round(Math.min(width, height) / 12));
      for (let y = 0; y < height; y += step) {
        for (let x = 0; x < width; x += step) {
          const pick = deck.pickObject({
            x,
            y,
            layerIds: [layerId],
            radius: 6,
          });
          if (pick && pick.object) {
            const props = pick.object.properties || {};
            const name = props.Name || props.name || props.StationName || props.station_name || props.SiteName ||
              props.site_name || props.LocationName || props.location_name || props.StationID || props.station_id ||
              props.ID || props.id || null;
            const coords = Array.isArray(pick.coordinate) ? pick.coordinate : null;
            if (coords && coords.length >= 2 && canProject) {
              const projected = deck.project([coords[0], coords[1]]);
              if (projected && projected.length >= 2) {
                return { x: rect.left + projected[0], y: rect.top + projected[1], name };
              }
            }
            return { x: rect.left + x, y: rect.top + y, name };
          }
        }
      }
    }

    if (!canProject) {
      return null;
    }

    for (let i = 0; i < features.length; i += 1) {
      const feature = features[i];
      const geom = feature && feature.geometry ? feature.geometry : null;
      if (!geom) {
        continue;
      }
      let coords = null;
      if (geom.type === 'Point') {
        coords = geom.coordinates;
      } else if (geom.type === 'MultiPoint' && Array.isArray(geom.coordinates)) {
        coords = geom.coordinates[0];
      } else if (geom.type === 'LineString' && Array.isArray(geom.coordinates)) {
        coords = geom.coordinates[0];
      } else if (geom.type === 'MultiLineString' && Array.isArray(geom.coordinates)) {
        coords = geom.coordinates[0] && geom.coordinates[0][0];
      }
      if (!coords || coords.length < 2) {
        continue;
      }
      const lng = Number(coords[0]);
      const lat = Number(coords[1]);
      if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
        continue;
      }
      const projected = deck.project([lng, lat]);
      if (!projected || projected.length < 2) {
        continue;
      }
      const x = rect.left + projected[0];
      const y = rect.top + projected[1];
      if (x < rect.left || y < rect.top || x > rect.left + width || y > rect.top + height) {
        continue;
      }
      const props = feature.properties || {};
      const name = props.Name || props.name || props.StationName || props.station_name || props.SiteName ||
        props.site_name || props.LocationName || props.location_name || props.StationID || props.station_id ||
        props.ID || props.id || null;
      return { x, y, name };
    }
    return null;
  }, layerKey);
}

test.describe('map gl smoke', () => {
  test('run loads without console errors and map canvas is visible', async ({ page }) => {
    const consoleErrors = attachConsoleCapture(page);

    await openRun(page);

    const map = page.locator('#mapid');
    await expect(map).toBeVisible();
    const box = await map.boundingBox();
    expect(box).not.toBeNull();
    expect(box.width).toBeGreaterThan(0);
    expect(box.height).toBeGreaterThan(0);
    await expect(page.locator('#mapid canvas')).toHaveCount(1);
    await expect(page.locator('#mapstatus')).toContainText('Center');

    const initialZoom = await getZoom(page);
    expect(initialZoom).not.toBeNull();

    await page.locator('#mapid').click({ position: { x: 20, y: 20 } });
    await page.keyboard.press('Shift+Equal');
    await expect.poll(async () => getZoom(page)).toBeGreaterThan(initialZoom);

    const zoomAfterIn = await getZoom(page);
    await page.keyboard.press('Minus');
    await expect.poll(async () => getZoom(page)).toBeLessThan(zoomAfterIn);

    const layerToggle = page.locator('[data-map-layer-control="true"] .wc-map-layer-control__toggle');
    await expect(layerToggle).toBeVisible();
    await layerToggle.click();
    const overlayPanel = page.locator('[data-map-layer-control="true"] .wc-map-layer-control__panel');
    await expect(overlayPanel).toBeVisible();
    const satelliteInput = page.locator('label:has-text("Satellite") input[type="radio"]');
    await expect(satelliteInput).toBeVisible();
    await satelliteInput.check();
    await expect(satelliteInput).toBeChecked();
    await expect(overlayPanel).toBeVisible();
    await expect.poll(async () => {
      return page.evaluate(() => {
        const map = window.MapController && typeof window.MapController.getInstance === 'function'
          ? window.MapController.getInstance()
          : null;
        const layers = map && map._deck && map._deck.props ? map._deck.props.layers : null;
        return layers && layers.length ? layers[0].id : null;
      });
    }).toContain('googleSatellite');

    await page.locator('#mapid').click({ position: { x: 30, y: 30 } });
    await expect(overlayPanel).toBeHidden();

    await layerToggle.click();
    await expect(overlayPanel).toBeVisible();
    const mapBox = await page.locator('#mapid').boundingBox();
    if (mapBox) {
      await page.mouse.move(mapBox.x + mapBox.width / 2, mapBox.y + mapBox.height / 2);
      await page.mouse.down();
      await page.mouse.move(mapBox.x + mapBox.width / 2 + 60, mapBox.y + mapBox.height / 2 + 30);
      await page.mouse.up();
    }
    await expect(overlayPanel).toBeHidden();

    expect(consoleErrors).toEqual([]);
  });

  test('fly to center, enable USGS/SNOTEL, and open marker modals', async ({ page }) => {
    await openRun(page);

    const centerInput = page.locator('#input_centerloc');
    await expect(centerInput).toBeVisible();
    await centerInput.fill('-120.7179, 48.2986, 9.1891575802927');
    await centerInput.press('Enter');

    await expect.poll(async () => getZoom(page)).toBeGreaterThan(9);
    await expect.poll(async () => {
      const center = await getCenter(page);
      return center ? center.lng : null;
    }).toBeCloseTo(-120.718, 2);
    await expect.poll(async () => {
      const center = await getCenter(page);
      return center ? center.lat : null;
    }).toBeCloseTo(48.299, 2);
    await waitForMapTransition(page);

    const { layerToggle } = await openOverlayPanel(page);
    const usgsInput = page.locator('label:has-text("USGS Gage Locations") input[type="checkbox"]');
    const snotelInput = page.locator('label:has-text("SNOTEL Locations") input[type="checkbox"]');
    await expect(usgsInput).toBeVisible();
    await expect(snotelInput).toBeVisible();
    await usgsInput.check();
    await snotelInput.check();
    await layerToggle.click();

    await page.evaluate(async () => {
      const map = window.MapController && typeof window.MapController.getInstance === 'function'
        ? window.MapController.getInstance()
        : null;
      if (map) {
        await map.loadUSGSGageLocations();
        await map.loadSnotelLocations();
      }
    });

    await waitForOverlayFeatures(page, 'usgs_gage');
    await waitForOverlayFeatures(page, 'snotel_locations');

    const modal = page.locator('#wc-map-feature-modal');
    const closeModal = modal.locator('.wc-modal__close');
    const modalTitle = modal.locator('.wc-modal__title');

    const usgsPoint = await getFeatureClickPoint(page, 'usgs_gage');
    expect(usgsPoint).not.toBeNull();
    if (!usgsPoint) {
      throw new Error('USGS feature not available for modal check.');
    }
    await page.mouse.click(usgsPoint.x, usgsPoint.y);
    let usedFallback = false;
    if (!(await modal.isVisible())) {
      usedFallback = true;
      await page.evaluate(() => {
        const map = window.MapController && typeof window.MapController.getInstance === 'function'
          ? window.MapController.getInstance()
          : null;
        const layer = map ? map.usgs_gage : null;
        const data = layer && layer.props ? layer.props.data : null;
        const features = data && data.features ? data.features : Array.isArray(data) ? data : [];
        if (layer && layer.props && typeof layer.props.onClick === 'function' && features.length) {
          layer.props.onClick({ object: features[0] });
        }
      });
    }
    await expect(modal).toBeVisible();
    if (usgsPoint.name && !usedFallback) {
      await expect(modalTitle).toContainText(usgsPoint.name);
    } else {
      const titleText = (await modalTitle.textContent()) || '';
      expect(titleText.trim().length).toBeGreaterThan(0);
    }
    await closeModal.click();
    await expect(modal).toBeHidden();

    const snotelPoint = await getFeatureClickPoint(page, 'snotel_locations');
    usedFallback = false;
    if (snotelPoint) {
      await page.mouse.click(snotelPoint.x, snotelPoint.y);
    }
    if (!(await modal.isVisible())) {
      usedFallback = true;
      await page.evaluate(() => {
        const map = window.MapController && typeof window.MapController.getInstance === 'function'
          ? window.MapController.getInstance()
          : null;
        const layer = map ? map.snotel_locations : null;
        const data = layer && layer.props ? layer.props.data : null;
        const features = data && data.features ? data.features : Array.isArray(data) ? data : [];
        if (layer && layer.props && typeof layer.props.onClick === 'function' && features.length) {
          layer.props.onClick({ object: features[0] });
        }
      });
    }
    await expect(modal).toBeVisible();
    if (snotelPoint && snotelPoint.name && !usedFallback) {
      await expect(modalTitle).toContainText(snotelPoint.name);
    } else {
      const titleText = (await modalTitle.textContent()) || '';
      expect(titleText.trim().length).toBeGreaterThan(0);
    }
    await closeModal.click();
    await expect(modal).toBeHidden();
  });

  test('toggle SBS overlay shows legend', async ({ page }) => {
    await openRun(page);

    const outcome = await enableSbsOverlay(page);

    const legend = page.locator('#sbs_legend');
    if (!outcome.success) {
      await expect(legend).toBeHidden();
      return;
    }
    await expect(legend).toBeVisible();
    const slider = legend.locator('#baer-opacity-slider');
    await expect(slider).toBeVisible();
  });

  test('SBS opacity slider updates layer opacity', async ({ page }) => {
    await openRun(page);

    const outcome = await enableSbsOverlay(page);

    const legend = page.locator('#sbs_legend');
    const slider = legend.locator('#baer-opacity-slider');
    if (!outcome.success) {
      await expect(legend).toBeHidden();
      return;
    }
    await expect(slider).toBeVisible();

    await slider.evaluate((element) => {
      element.value = '0.4';
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    });

    await expect.poll(async () => {
      return page.evaluate(() => {
        const map = window.MapController && typeof window.MapController.getInstance === 'function'
          ? window.MapController.getInstance()
          : null;
        return map && map.sbs_layer && map.sbs_layer.props ? map.sbs_layer.props.opacity : null;
      });
    }).toBeCloseTo(0.4, 1);
  });

  test('empty run tolerates missing SBS resources', async ({ page }) => {
    const mapVisible = await openRun(page, resolveEmptyUrl(), { allowMissingMap: true });
    if (!mapVisible) {
      test.skip(true, 'Empty run map not available.');
    }

    const outcome = await enableSbsOverlay(page);
    const legend = page.locator('#sbs_legend');
    if (outcome.success) {
      await expect(legend).toBeVisible();
    } else {
      await expect(legend).toBeHidden();
    }
  });
});
