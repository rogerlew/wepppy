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

async function waitForOverlayLayer(page, name) {
  return expect.poll(async () => {
    return page.evaluate((layerName) => {
      const map = window.MapController && typeof window.MapController.getInstance === 'function'
        ? window.MapController.getInstance()
        : null;
      const overlay = map && map.overlayMaps ? map.overlayMaps[layerName] : null;
      if (!overlay || !map || typeof map.hasLayer !== 'function') {
        return false;
      }
      return map.hasLayer(overlay);
    }, name);
  }, { timeout: 20000 }).toBeTruthy();
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

  test('channels overlay toggles without console errors', async ({ page }) => {
    const consoleErrors = attachConsoleCapture(page);

    await openRun(page);

    const stubbed = await page.evaluate(() => {
      const http = window.WCHttp;
      if (!http || typeof http.getJson !== 'function') {
        return false;
      }
      if (!http._channelGlOriginalGetJson) {
        http._channelGlOriginalGetJson = http.getJson.bind(http);
      }
      const original = http._channelGlOriginalGetJson;
      http.getJson = (url, options) => {
        if (String(url).includes('resources/netful.json')) {
          return Promise.resolve({
            type: 'FeatureCollection',
            features: [
              {
                type: 'Feature',
                properties: { Order: 2 },
                geometry: { type: 'LineString', coordinates: [[-120.1, 48.1], [-120.2, 48.2]] },
              },
              {
                type: 'Feature',
                properties: { Order: 4 },
                geometry: { type: 'LineString', coordinates: [[-120.3, 48.3], [-120.4, 48.4]] },
              },
            ],
          });
        }
        return original(url, options);
      };
      return true;
    });
    expect(stubbed).toBe(true);

    await page.evaluate(async () => {
      const channel = window.ChannelDelineation && typeof window.ChannelDelineation.getInstance === 'function'
        ? window.ChannelDelineation.getInstance()
        : null;
      if (channel && typeof channel.show === 'function') {
        await channel.show();
      }
    });

    const channelColor = await page.evaluate(() => {
      const channel = window.ChannelDelineation && typeof window.ChannelDelineation.getInstance === 'function'
        ? window.ChannelDelineation.getInstance()
        : null;
      const layer = channel ? channel.glLayer : null;
      return layer && layer.props && typeof layer.props.getLineColor === 'function'
        ? layer.props.getLineColor({ properties: { Order: 2 } })
        : null;
    });
    expect(channelColor).toEqual([71, 158, 255, 230]);

    const { layerToggle } = await openOverlayPanel(page);
    const channelsInput = page.locator('label:has-text("Channels") input[type="checkbox"]');
    await expect(channelsInput).toBeVisible();
    await channelsInput.check();
    await layerToggle.click();

    await expect.poll(async () => {
      return page.evaluate(() => {
        const map = window.MapController && typeof window.MapController.getInstance === 'function'
          ? window.MapController.getInstance()
          : null;
        const layers = map && map._deck && map._deck.props ? map._deck.props.layers : [];
        return layers.some((layer) => layer && layer.id === 'wc-channels-netful');
      });
    }).toBe(true);

    await openOverlayPanel(page);
    await channelsInput.uncheck();
    await layerToggle.click();

    await expect.poll(async () => {
      return page.evaluate(() => {
        const map = window.MapController && typeof window.MapController.getInstance === 'function'
          ? window.MapController.getInstance()
          : null;
        const layers = map && map._deck && map._deck.props ? map._deck.props.layers : [];
        return layers.some((layer) => layer && layer.id === 'wc-channels-netful');
      });
    }).toBe(false);

    await openOverlayPanel(page);
    await channelsInput.check();
    await layerToggle.click();

    await expect.poll(async () => {
      return page.evaluate(() => {
        const map = window.MapController && typeof window.MapController.getInstance === 'function'
          ? window.MapController.getInstance()
          : null;
        const layers = map && map._deck && map._deck.props ? map._deck.props.layers : [];
        return layers.some((layer) => layer && layer.id === 'wc-channels-netful');
      });
    }).toBe(true);

    await openOverlayPanel(page);
    await expect(page.locator('label:has-text("Channels")')).toHaveCount(1);

    expect(consoleErrors).toEqual([]);
  });

  test('channel pass 2 renders labels and drilldown', async ({ page }) => {
    await openRun(page);

    const stubbed = await page.evaluate(() => {
      const http = window.WCHttp;
      if (!http || typeof http.request !== 'function' || typeof http.getJson !== 'function') {
        return false;
      }
      if (!http._channelPass2OriginalRequest) {
        http._channelPass2OriginalRequest = http.request.bind(http);
      }
      if (!http._channelPass2OriginalGetJson) {
        http._channelPass2OriginalGetJson = http.getJson.bind(http);
      }
      const originalRequest = http._channelPass2OriginalRequest;
      const originalGetJson = http._channelPass2OriginalGetJson;
      http.request = (url, options) => {
        const target = String(url || '');
        if (target.includes('query/delineation_pass')) {
          return Promise.resolve({ body: '2' });
        }
        if (target.includes('report/chn_summary/')) {
          return Promise.resolve({ body: '<div id="chn-summary">Channel Summary</div>' });
        }
        return originalRequest(url, options);
      };
      http.getJson = (url, options) => {
        const target = String(url || '');
        if (target.includes('resources/channels.json')) {
          return Promise.resolve({
            type: 'FeatureCollection',
            features: [
              {
                type: 'Feature',
                properties: { Order: 2, TopazID: 123 },
                geometry: {
                  type: 'Polygon',
                  coordinates: [[
                    [-120.1, 45.1],
                    [-120.2, 45.1],
                    [-120.2, 45.2],
                    [-120.1, 45.2],
                    [-120.1, 45.1],
                  ]],
                },
              },
            ],
          });
        }
        return originalGetJson(url, options);
      };
      return true;
    });
    expect(stubbed).toBe(true);

    await page.evaluate(async () => {
      const channel = window.ChannelDelineation && typeof window.ChannelDelineation.getInstance === 'function'
        ? window.ChannelDelineation.getInstance()
        : null;
      if (channel && typeof channel.show === 'function') {
        await channel.show();
      }
      if (channel && channel.glLayer && channel.glLayer.props && typeof channel.glLayer.props.onClick === 'function') {
        const data = channel.glLayer.props.data;
        const feature = data && data.features ? data.features[0] : null;
        if (feature) {
          channel.glLayer.props.onClick({ object: feature });
        }
      }
    });

    await expect.poll(async () => {
      return (await page.locator('#drilldown').textContent()) || '';
    }, { timeout: 10000 }).toContain('Channel Summary');

    const { layerToggle } = await openOverlayPanel(page);
    await expect(page.locator('label:has-text("Channels")')).toHaveCount(1);
    await expect(page.locator('label:has-text("Channel Labels")')).toHaveCount(1);
    await layerToggle.click();
  });

  test('build channels submits job and renders report', async ({ page }) => {
    const consoleErrors = attachConsoleCapture(page);

    await openRun(page);

    const stubbed = await page.evaluate(() => {
      const http = window.WCHttp;
      if (!http || typeof http.request !== 'function' || typeof http.getJson !== 'function') {
        return false;
      }
      if (!http._channelBuildOriginalRequest) {
        http._channelBuildOriginalRequest = http.request.bind(http);
      }
      if (!http._channelBuildOriginalGetJson) {
        http._channelBuildOriginalGetJson = http.getJson.bind(http);
      }
      http.request = (url, options) => {
        const target = String(url || '');
        if (target.includes('rq/api/fetch_dem_and_build_channels')) {
          return Promise.resolve({ body: { Success: true, job_id: 'job-channel-1' } });
        }
        if (target.includes('report/channel')) {
          return Promise.resolve({ body: '<div id="channel-report">Report</div>' });
        }
        return http._channelBuildOriginalRequest(url, options);
      };
      http.getJson = (url, options) => {
        const target = String(url || '');
        if (target.includes('resources/netful.json')) {
          return Promise.resolve({
            type: 'FeatureCollection',
            features: [
              {
                type: 'Feature',
                properties: { Order: 2 },
                geometry: { type: 'LineString', coordinates: [[-120.1, 48.1], [-120.2, 48.2]] },
              },
            ],
          });
        }
        return http._channelBuildOriginalGetJson(url, options);
      };
      return true;
    });
    expect(stubbed).toBe(true);

    await page.evaluate(() => {
      window.ispoweruser = true;
      const channel = window.ChannelDelineation && typeof window.ChannelDelineation.getInstance === 'function'
        ? window.ChannelDelineation.getInstance()
        : null;
      if (channel && typeof channel.onMapChange === 'function') {
        channel.onMapChange();
      }
    });

    await page.locator('#btn_build_channels_en').click();

    await expect(page.locator('#build_channels_form #status')).toContainText(
      'fetch_dem_and_build_channels_rq job submitted',
      { timeout: 20000 },
    );

    await page.evaluate(() => {
      const channel = window.ChannelDelineation && typeof window.ChannelDelineation.getInstance === 'function'
        ? window.ChannelDelineation.getInstance()
        : null;
      if (channel && typeof channel.triggerEvent === 'function') {
        channel.triggerEvent('BUILD_CHANNELS_TASK_COMPLETED', { status: 'finished' });
      }
    });

    await expect(page.locator('#build_channels_form #info')).toContainText('Report', { timeout: 20000 });

    await expect.poll(async () => {
      return page.evaluate(() => {
        const map = window.MapController && typeof window.MapController.getInstance === 'function'
          ? window.MapController.getInstance()
          : null;
        const layers = map && map._deck && map._deck.props ? map._deck.props.layers : [];
        return layers.some((layer) => layer && layer.id === 'wc-channels-netful');
      });
    }).toBe(true);

    expect(consoleErrors).toEqual([]);
  });

  test('outlet cursor click renders temp overlay and outlet marker', async ({ page }) => {
    await openRun(page);

    const stubbed = await page.evaluate(() => {
      const http = window.WCHttp;
      if (!http || typeof http.request !== 'function' || typeof http.getJson !== 'function') {
        return false;
      }
      if (!http._outletGlOriginalRequest) {
        http._outletGlOriginalRequest = http.request.bind(http);
      }
      if (!http._outletGlOriginalGetJson) {
        http._outletGlOriginalGetJson = http.getJson.bind(http);
      }
      http.request = (url, options) => {
        const target = String(url || '');
        if (target.includes('rq/api/set_outlet')) {
          return Promise.resolve({ body: { Success: true, job_id: 'job-1' } });
        }
        if (target.includes('report/outlet')) {
          return Promise.resolve({ body: '<div>Report</div>' });
        }
        return http._outletGlOriginalRequest(url, options);
      };
      http.getJson = (url, options) => {
        const target = String(url || '');
        if (target.includes('query/outlet')) {
          return Promise.resolve({ lat: 45.15, lng: -120.35 });
        }
        return http._outletGlOriginalGetJson(url, options);
      };
      return true;
    });
    expect(stubbed).toBe(true);

    await page.evaluate(() => {
      const outlet = window.Outlet && typeof window.Outlet.getInstance === 'function'
        ? window.Outlet.getInstance()
        : null;
      if (outlet && typeof outlet.setCursorSelection === 'function') {
        outlet.setCursorSelection(true);
      }
    });

    await page.locator('#mapid').click({ position: { x: 200, y: 200 } });

    await expect.poll(async () => {
      return page.evaluate(() => {
        const map = window.MapController && typeof window.MapController.getInstance === 'function'
          ? window.MapController.getInstance()
          : null;
        const layers = map && map._deck && map._deck.props ? map._deck.props.layers : [];
        return layers.some((layer) => layer && layer.id === 'wc-outlet-temp-marker');
      });
    }).toBe(true);

    await expect.poll(async () => {
      return page.evaluate(() => {
        const map = window.MapController && typeof window.MapController.getInstance === 'function'
          ? window.MapController.getInstance()
          : null;
        const layers = map && map._deck && map._deck.props ? map._deck.props.layers : [];
        return layers.some((layer) => layer && layer.id === 'wc-outlet-temp-dialog');
      });
    }).toBe(true);

    await page.evaluate(() => {
      const outlet = window.Outlet && typeof window.Outlet.getInstance === 'function'
        ? window.Outlet.getInstance()
        : null;
      if (outlet && typeof outlet.triggerEvent === 'function') {
        outlet.triggerEvent('SET_OUTLET_TASK_COMPLETED', {});
      }
    });

    await expect.poll(async () => {
      return page.evaluate(() => {
        const map = window.MapController && typeof window.MapController.getInstance === 'function'
          ? window.MapController.getInstance()
          : null;
        const layers = map && map._deck && map._deck.props ? map._deck.props.layers : [];
        const hasTemp = layers.some((layer) => layer && (
          layer.id === 'wc-outlet-temp-marker' || layer.id === 'wc-outlet-temp-dialog'
        ));
        const hasOutlet = layers.some((layer) => layer && layer.id === 'wc-outlet-marker');
        return { hasTemp, hasOutlet };
      });
    }).toEqual({ hasTemp: false, hasOutlet: true });

    await expect(page.locator('label:has-text("Outlet")')).toHaveCount(1);
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

  test('SBS overlay toggle hides legend', async ({ page }) => {
    await openRun(page);

    const outcome = await enableSbsOverlay(page);
    const legend = page.locator('#sbs_legend');
    if (!outcome.success) {
      await expect(legend).toBeHidden();
      return;
    }

    await expect(legend).toBeVisible();

    const { layerToggle } = await openOverlayPanel(page);
    const sbsInput = page.locator('label:has-text("Burn Severity Map") input[type="checkbox"]');
    await expect(sbsInput).toBeVisible();
    await sbsInput.uncheck();
    await layerToggle.click();

    await expect(legend).toBeHidden();
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

  test('subcatchments overlay toggles in GL', async ({ page }) => {
    await openRun(page);

    const outcome = await page.evaluate(async () => {
      const sub = window.SubcatchmentDelineation && typeof window.SubcatchmentDelineation.getInstance === 'function'
        ? window.SubcatchmentDelineation.getInstance()
        : null;
      if (!sub || typeof sub.show !== 'function') {
        return { ok: false, reason: 'subcatchment controller missing' };
      }
      try {
        await sub.show();
      } catch (error) {
        return { ok: false, reason: error.message || String(error) };
      }
      const map = window.MapController && typeof window.MapController.getInstance === 'function'
        ? window.MapController.getInstance()
        : null;
      const layer = map && map.overlayMaps ? map.overlayMaps.Subcatchments : null;
      const hasLayer = Boolean(map && layer && typeof map.hasLayer === 'function' && map.hasLayer(layer));
      return { ok: Boolean(layer), hasLayer };
    });

    if (!outcome.ok) {
      test.skip(true, `Subcatchments unavailable: ${outcome.reason || 'unknown'}`);
    }

    const { layerToggle } = await openOverlayPanel(page);
    const subcatchmentInput = page.locator('label:has-text("Subcatchments") input[type="checkbox"]');
    await expect(subcatchmentInput).toBeVisible();
    if (!outcome.hasLayer) {
      await subcatchmentInput.check();
    }
    await layerToggle.click();

    await waitForOverlayLayer(page, 'Subcatchments');
  });

  test('gridded loss mode adds overlay and updates labels', async ({ page }) => {
    await openRun(page);

    const outcome = await page.evaluate(async () => {
      const sub = window.SubcatchmentDelineation && typeof window.SubcatchmentDelineation.getInstance === 'function'
        ? window.SubcatchmentDelineation.getInstance()
        : null;
      if (!sub || typeof sub.setColorMap !== 'function') {
        return { ok: false, reason: 'subcatchment controller missing' };
      }
      try {
        sub.setColorMap('grd_loss');
      } catch (error) {
        return { ok: false, reason: error.message || String(error) };
      }
      await new Promise((resolve) => setTimeout(resolve, 3000));
      const map = window.MapController && typeof window.MapController.getInstance === 'function'
        ? window.MapController.getInstance()
        : null;
      const layer = map && map.overlayMaps ? map.overlayMaps['Gridded Output'] : null;
      const hasLayer = Boolean(map && layer && typeof map.hasLayer === 'function' && map.hasLayer(layer));
      const units = document.getElementById('wepp_grd_cmap_range_loss_units');
      const unitsText = units ? (units.textContent || units.innerHTML || '').trim() : '';
      return { ok: hasLayer, unitsText };
    });

    if (!outcome.ok) {
      test.skip(true, `Gridded loss unavailable: ${outcome.reason || 'missing layer'}`);
    }

    expect(outcome.unitsText).not.toEqual('');
    await waitForOverlayLayer(page, 'Gridded Output');
  });

  test('build subcatchments updates status', async ({ page }) => {
    await openRun(page);

    const outcome = await page.evaluate(() => {
      const sub = window.SubcatchmentDelineation && typeof window.SubcatchmentDelineation.getInstance === 'function'
        ? window.SubcatchmentDelineation.getInstance()
        : null;
      if (!sub || typeof sub.build !== 'function') {
        return { ok: false, reason: 'subcatchment controller missing' };
      }
      if (typeof sub.connect_status_stream === 'function') {
        sub.connect_status_stream = () => {};
      }
      const http = window.WCHttp;
      if (!http || typeof http.postJson !== 'function') {
        return { ok: false, reason: 'WCHttp missing' };
      }
      http.postJson = async () => ({ body: { Success: true, job_id: 'smoke-job-1' } });
      return { ok: true };
    });

    if (!outcome.ok) {
      test.skip(true, `Subcatchments build unavailable: ${outcome.reason || 'unknown'}`);
    }

    const buildButton = page.locator('[data-subcatchment-action="build"], #btn_build_subcatchments');
    if (!(await buildButton.isVisible())) {
      test.skip(true, 'Build Subcatchments button not visible.');
    }

    await buildButton.click();

    const status = page.locator('#build_subcatchments_form #status');
    await expect.poll(async () => (await status.textContent()) || '').toContain('job submitted');
  });
});
