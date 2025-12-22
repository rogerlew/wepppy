/**
 * Diagnostic: live debugging for slope/aspect rendering.
 */

import { test } from '@playwright/test';

const diagnosticsEnabled = process.env.SMOKE_DIAGNOSTICS === 'true' || process.env.SMOKE_DIAGNOSTICS === '1';
const fallbackUrl = 'https://wc.bearhive.duckdns.org/weppcloud/runs/air-cooled-broadening/disturbed9002/';
const targetUrl = process.env.MAP_GL_URL || process.env.SMOKE_RUN_PATH || fallbackUrl;

test.describe('diagnostic: live slope/aspect', () => {
  test.skip(!diagnosticsEnabled, 'Set SMOKE_DIAGNOSTICS=1 to run diagnostic smoke specs.');

  test('check actual rendered colors', async ({ page }) => {
    // Enable verbose console logging
    page.on('console', msg => {
      console.log(`[BROWSER ${msg.type()}]`, msg.text());
    });

    await page.goto(targetUrl);
  await page.waitForSelector('#mapid', { timeout: 30000 });
  await page.waitForTimeout(3000);

  // Click slope radio
  console.log('\n=== Clicking Slope Radio ===');
  await page.locator('#sub_cmap_radio_slope').click({ force: true });
  await page.waitForTimeout(2000);

  // Deep dive into deck.gl rendering state
  const deckState = await page.evaluate(() => {
    const map = window.MapController?.getInstance();
    const sub = window.SubcatchmentDelineation?.getInstance();

    if (!map || !sub) return { error: 'No controllers' };

    // Get deck instance
    const deck = map.deckgl || map._deckgl || map.deck || window.deck;

    // Try to find the actual deck.gl Deck instance
    let deckInstance = null;
    if (deck && deck.deck) {
      deckInstance = deck.deck;
    } else if (typeof deck?.setProps === 'function') {
      deckInstance = deck;
    }

    // Get layers from the deck instance
    const layers = deckInstance?.props?.layers || [];
    const subcatchmentLayer = layers.find(l => l?.id === 'wc-subcatchments');

    // Check if the layer needs update
    const needsUpdate = subcatchmentLayer?.props?.updateTriggers;

    // Sample actual getFillColor from the layer
    const testFeature = sub.state?.data?.features?.[0];
    let actualColor = null;
    if (subcatchmentLayer && testFeature) {
      actualColor = subcatchmentLayer.props?.getFillColor?.(testFeature);
    }

    // Check the map's layer tracking
    const mapLayers = map.layers || [];
    const hasSubLayer = mapLayers.some(l => l?.id === 'wc-subcatchments');

    return {
      mode: sub.state?.cmapMode,
      hasSubGlLayer: !!sub.glLayer,
      subGlLayerId: sub.glLayer?.id,
      deckInstanceFound: !!deckInstance,
      deckLayerCount: layers.length,
      deckLayerIds: layers.map(l => l?.id).filter(Boolean),
      hasSubcatchmentInDeck: !!subcatchmentLayer,
      mapLayerCount: mapLayers.length,
      hasSubcatchmentInMap: hasSubLayer,
      actualColor,
      updateTriggers: needsUpdate,
      // Check if there was a render call
      layerVersion: subcatchmentLayer?.internalState?.layer?.id
    };
  });

  console.log('\nDeck.gl State:', JSON.stringify(deckState, null, 2));

  // Try to manually trigger a refresh
  console.log('\n=== Attempting manual refresh ===');
  await page.evaluate(() => {
    const map = window.MapController?.getInstance();
    if (map && typeof map.refresh === 'function') {
      console.log('Calling map.refresh()');
      map.refresh();
    }
    if (map && typeof map.forceUpdate === 'function') {
      console.log('Calling map.forceUpdate()');
      map.forceUpdate();
    }
    if (map && typeof map.redraw === 'function') {
      console.log('Calling map.redraw()');
      map.redraw();
    }
  });

  await page.waitForTimeout(1000);

  // Take screenshots before and after clicking aspect
    const slopeShot = test.info().outputPath('slope-before-aspect.png');
    await page.screenshot({ path: slopeShot, fullPage: true });
    console.log(`Screenshot saved: ${slopeShot}`);

  // Try aspect
  console.log('\n=== Clicking Aspect Radio ===');
  await page.locator('#sub_cmap_radio_aspect').click({ force: true });
  await page.waitForTimeout(2000);

    const aspectShot = test.info().outputPath('aspect-after-click.png');
    await page.screenshot({ path: aspectShot, fullPage: true });
    console.log(`Screenshot saved: ${aspectShot}`);
  });
});
