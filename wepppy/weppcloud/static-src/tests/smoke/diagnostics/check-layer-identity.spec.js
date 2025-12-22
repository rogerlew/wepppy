/**
 * Diagnostic: check if the layer object is actually changing.
 */

import { test } from '@playwright/test';

const diagnosticsEnabled = process.env.SMOKE_DIAGNOSTICS === 'true' || process.env.SMOKE_DIAGNOSTICS === '1';
const fallbackUrl = 'https://wc.bearhive.duckdns.org/weppcloud/runs/air-cooled-broadening/disturbed9002/';
const targetUrl = process.env.MAP_GL_URL || process.env.SMOKE_RUN_PATH || fallbackUrl;

test.describe('diagnostic: layer identity', () => {
  test.skip(!diagnosticsEnabled, 'Set SMOKE_DIAGNOSTICS=1 to run diagnostic smoke specs.');

  test('verify layer is being replaced', async ({ page }) => {
    await page.goto(targetUrl);
  await page.waitForSelector('#mapid', { timeout: 30000 });
  await page.waitForTimeout(3000);

  // Get initial layer reference
  const initialLayer = await page.evaluate(() => {
    const sub = window.SubcatchmentDelineation?.getInstance();
    return {
      layerId: sub?.glLayer?.id,
      layerObject: sub?.glLayer ? 'exists' : 'missing',
      mode: sub?.state?.cmapMode
    };
  });
  console.log('Initial layer:', initialLayer);

  // Click slope
  console.log('\n=== Clicking Slope ===');
  await page.locator('#sub_cmap_radio_slope').click();
  await page.waitForTimeout(2000);

  // Check if layer changed
  const afterSlope = await page.evaluate(() => {
    const sub = window.SubcatchmentDelineation?.getInstance();
    const map = window.MapController?.getInstance();

    // Sample color computation directly
    const testFeature = sub?.state?.data?.features?.[0];
    let computedColor = null;
    if (sub?.glLayer && testFeature) {
      computedColor = sub.glLayer.props?.getFillColor?.(testFeature);
    }

    // Check what map.hasLayer says
    const hasLayer = map?.hasLayer?.(sub?.glLayer);

    return {
      mode: sub?.state?.cmapMode,
      layerId: sub?.glLayer?.id,
      hasDataSlpAsp: !!sub?.state?.dataSlpAsp,
      computedColor,
      mapHasLayer: hasLayer,
      // Try to check internal layer registry
      debug: {
        glLayerType: typeof sub?.glLayer,
        glLayerConstructor: sub?.glLayer?.constructor?.name
      }
    };
  });

  console.log('After slope click:', JSON.stringify(afterSlope, null, 2));

  // Most importantly - check if the issue is in how layers are being added
  // Let me try manually triggering a refresh
  console.log('\n=== Attempting manual layer refresh ===');
  const manualRefreshResult = await page.evaluate(() => {
    const map = window.MapController?.getInstance();
    const sub = window.SubcatchmentDelineation?.getInstance();

    if (!map || !sub?.glLayer) return { error: 'Missing map or layer' };

    // Try removing and re-adding the layer
    const layer = sub.glLayer;
    const hadLayer = map.hasLayer(layer);

    try {
      // Force remove and re-add
      map.removeLayer(layer);
      map.addLayer(layer);

      return {
        hadLayer,
        nowHasLayer: map.hasLayer(layer),
        action: 'removed and re-added'
      };
    } catch (e) {
      return { error: e.message };
    }
  });

  console.log('Manual refresh result:', JSON.stringify(manualRefreshResult, null, 2));

  await page.waitForTimeout(2000);
    const screenshotPath = test.info().outputPath('after-manual-refresh.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`\nScreenshot: ${screenshotPath}`);
  });
});
