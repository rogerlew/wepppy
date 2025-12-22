/**
 * Diagnostic: deep inspection of deck.gl rendering state.
 */

import { test } from '@playwright/test';

const diagnosticsEnabled = process.env.SMOKE_DIAGNOSTICS === 'true' || process.env.SMOKE_DIAGNOSTICS === '1';
const fallbackUrl = 'https://wc.bearhive.duckdns.org/weppcloud/runs/air-cooled-broadening/disturbed9002/';
const targetUrl = process.env.MAP_GL_URL || process.env.SMOKE_RUN_PATH || fallbackUrl;

test.describe('diagnostic: deck.gl rendering', () => {
  test.skip(!diagnosticsEnabled, 'Set SMOKE_DIAGNOSTICS=1 to run diagnostic smoke specs.');

  test('diagnose deck.gl rendering state', async ({ page }) => {
    await page.goto(targetUrl);
  await page.waitForSelector('#mapid', { timeout: 30000 });
  await page.waitForTimeout(3000);

  // First, check what's currently visible
  const initialState = await page.evaluate(() => {
    const sub = window.SubcatchmentDelineation?.getInstance();
    return {
      mode: sub?.state?.cmapMode,
      hasData: !!sub?.state?.data,
      hasGlLayer: !!sub?.glLayer,
      glLayerId: sub?.glLayer?.id
    };
  });
  console.log('Initial state:', initialState);

  // Click slope radio
  console.log('\n=== Clicking Slope ===');
  await page.locator('#sub_cmap_radio_slope').click();
  await page.waitForTimeout(3000); // Wait longer for rendering

  // Deep inspection of rendering pipeline
  const renderDiagnostic = await page.evaluate(() => {
    const map = window.MapController?.getInstance();
    const sub = window.SubcatchmentDelineation?.getInstance();

    if (!map || !sub) return { error: 'No controllers' };

    // Check if addLayer was called
    const hasLayer = map.hasLayer?.(sub.glLayer);

    // Try to find deck instance multiple ways
    let deckInstance = null;
    const deckPaths = [
      () => map.deckgl,
      () => map._deckgl,
      () => map.deck,
      () => window.deckgl,
      () => window.MapController?._deckgl
    ];

    for (const pathFn of deckPaths) {
      try {
        const candidate = pathFn();
        if (candidate && typeof candidate.setProps === 'function') {
          deckInstance = candidate;
          break;
        }
      } catch (e) {}
    }

    const deckLayers = deckInstance?.props?.layers || [];
    const subLayerInDeck = deckLayers.find(l => l?.id === 'wc-subcatchments');

    // Get actual getFillColor function from the deck layer
    let sampleColors = [];
    if (subLayerInDeck && sub.state?.data?.features) {
      sampleColors = sub.state.data.features.slice(0, 3).map(f => {
        const color = subLayerInDeck.props?.getFillColor?.(f);
        return {
          topazId: f.properties?.TopazID,
          color,
          isOrange: color?.[0] === 255 && color?.[1] === 120
        };
      });
    }

    return {
      mode: sub.state?.cmapMode,
      hasDataSlpAsp: !!sub.state?.dataSlpAsp,
      dataSlpAspKeys: sub.state?.dataSlpAsp ? Object.keys(sub.state.dataSlpAsp).slice(0, 3) : [],
      hasGlLayer: !!sub.glLayer,
      mapHasLayer: hasLayer,
      deckFound: !!deckInstance,
      deckLayerCount: deckLayers.length,
      deckLayerIds: deckLayers.map(l => l?.id),
      hasSubLayerInDeck: !!subLayerInDeck,
      subLayerPropsKeys: subLayerInDeck ? Object.keys(subLayerInDeck.props || {}) : [],
      sampleColors
    };
  });

  console.log('Render diagnostic:', JSON.stringify(renderDiagnostic, null, 2));

  // Check if the problem is that layers aren't being passed to deck
  const layerRegistryCheck = await page.evaluate(() => {
    const map = window.MapController?.getInstance();

    // Try to access internal layer registry
    const registryChecks = [];

    if (map.layers) {
      registryChecks.push({ name: 'map.layers', value: map.layers });
    }

    // Try to trigger applyLayers manually
    let applyLayersResult = null;
    if (typeof map.applyLayers === 'function') {
      try {
        map.applyLayers();
        applyLayersResult = 'called';
      } catch (e) {
        applyLayersResult = 'error: ' + e.message;
      }
    }

    return {
      registryChecks: registryChecks.map(r => ({ name: r.name, type: typeof r.value, length: r.value?.length })),
      applyLayersResult
    };
  });

  console.log('Layer registry check:', JSON.stringify(layerRegistryCheck, null, 2));

    const screenshotPath = test.info().outputPath('diagnostic-slope.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`\nScreenshot saved: ${screenshotPath}`);
  });
});
