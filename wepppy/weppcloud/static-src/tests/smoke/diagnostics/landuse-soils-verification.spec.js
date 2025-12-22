/**
 * Diagnostic: verify landuse and soils overlays render correctly.
 */

import { test, expect } from '@playwright/test';

const diagnosticsEnabled = process.env.SMOKE_DIAGNOSTICS === 'true' || process.env.SMOKE_DIAGNOSTICS === '1';
const fallbackUrl = 'https://wc.bearhive.duckdns.org/weppcloud/runs/rlew-appreciated-tremolite/disturbed9002/';
const targetUrl = process.env.MAP_GL_URL || process.env.SMOKE_RUN_PATH || fallbackUrl;

test.describe('diagnostic: landuse/soils overlays', () => {
  test.skip(!diagnosticsEnabled, 'Set SMOKE_DIAGNOSTICS=1 to run diagnostic smoke specs.');

  test('landuse and soils overlays should render with correct colors', async ({ page }) => {
    await page.goto(targetUrl);
  await page.waitForSelector('#mapid', { timeout: 30000 });
  await page.waitForTimeout(3000);

  // Test Dominant Landcover
  console.log('\n=== Testing Dominant Landcover ===');

  // Wait for radio to be enabled (preflight check)
  await page.waitForFunction(() => {
    const radio = document.querySelector('#sub_cmap_radio_dom_lc');
    return radio && !radio.disabled;
  }, { timeout: 30000 });

  await page.locator('#sub_cmap_radio_dom_lc').click();
  await page.waitForTimeout(2000);

  const landuseVerification = await page.evaluate(() => {
    const sub = window.SubcatchmentDelineation?.getInstance();
    if (!sub?.glLayer) return { error: 'No GL layer' };

    const features = sub.state?.data?.features || [];
    const samples = features.slice(0, 10).map(f => {
      const color = sub.glLayer.props?.getFillColor?.(f);
      const topazId = f.properties?.TopazID;
      const landuseSummary = sub.state?.dataLanduse?.[topazId];
      return {
        topazId,
        color,
        hasColor: !!color,
        isDefault: color?.[0] === 128 && color?.[1] === 128 && color?.[2] === 128,
        dominantLanduse: landuseSummary?.dominant || landuseSummary?.cover_desc
      };
    });

    return {
      mode: sub.state?.cmapMode,
      hasLanduseSummary: !!sub.state?.dataLanduse,
      totalFeatures: features.length,
      samplesWithColor: samples.filter(s => s.hasColor && !s.isDefault).length,
      updateTriggers: sub.glLayer?.props?.updateTriggers,
      sampleData: samples.slice(0, 3)
    };
  });

  console.log('Landuse verification:', JSON.stringify(landuseVerification, null, 2));

  // Verify landuse has colors
  expect(landuseVerification.mode).toBe('landuse');
  expect(landuseVerification.samplesWithColor).toBeGreaterThan(0);

    const landuseShot = test.info().outputPath('landuse-dominant.png');
    await page.screenshot({ path: landuseShot });
    console.log(`Screenshot: ${landuseShot}`);

  // Test Dominant Soil
  console.log('\n=== Testing Dominant Soil ===');

  // Wait for soil radio to be enabled
  await page.waitForFunction(() => {
    const radio = document.querySelector('#sub_cmap_radio_dom_soil');
    return radio && !radio.disabled;
  }, { timeout: 30000 });

  await page.locator('#sub_cmap_radio_dom_soil').click();
  await page.waitForTimeout(2000);

  const soilsVerification = await page.evaluate(() => {
    const sub = window.SubcatchmentDelineation?.getInstance();
    if (!sub?.glLayer) return { error: 'No GL layer' };

    const features = sub.state?.data?.features || [];
    const samples = features.slice(0, 10).map(f => {
      const color = sub.glLayer.props?.getFillColor?.(f);
      const topazId = f.properties?.TopazID;
      const soilsSummary = sub.state?.dataSoils?.[topazId];
      return {
        topazId,
        color,
        hasColor: !!color,
        isDefault: color?.[0] === 128 && color?.[1] === 128 && color?.[2] === 128,
        soilTexture: soilsSummary?.texture || soilsSummary?.simple_texture,
        mukey: soilsSummary?.mukey
      };
    });

    return {
      mode: sub.state?.cmapMode,
      hasSoilsSummary: !!sub.state?.dataSoils,
      totalFeatures: features.length,
      samplesWithColor: samples.filter(s => s.hasColor && !s.isDefault).length,
      updateTriggers: sub.glLayer?.props?.updateTriggers,
      sampleData: samples.slice(0, 3)
    };
  });

  console.log('Soils verification:', JSON.stringify(soilsVerification, null, 2));

  // Verify soils has colors
  expect(soilsVerification.mode).toBe('soils');
  expect(soilsVerification.samplesWithColor).toBeGreaterThan(0);

    const soilsShot = test.info().outputPath('soils-dominant.png');
    await page.screenshot({ path: soilsShot });
    console.log(`Screenshot: ${soilsShot}`);

  // Check that updateTriggers is working for mode changes
  expect(landuseVerification.updateTriggers).toBeDefined();
  expect(soilsVerification.updateTriggers).toBeDefined();

    console.log('\n✅ Landuse and soils overlays verified!');
  });

  test('landuse cover mode should render if available', async ({ page }) => {
    await page.goto(targetUrl);
    await page.waitForSelector('#mapid', { timeout: 30000 });
    await page.waitForTimeout(3000);

  // Check if vegetation cover radio exists (RAP-enabled runs)
  const coverRadioExists = await page.locator('#sub_cmap_radio_landuse_cover').count() > 0;

  if (coverRadioExists) {
    console.log('\n=== Testing Vegetation Cover ===');
    await page.locator('#sub_cmap_radio_landuse_cover').click();
    await page.waitForTimeout(2000);

    const coverVerification = await page.evaluate(() => {
      const sub = window.SubcatchmentDelineation?.getInstance();
      if (!sub?.glLayer) return { error: 'No GL layer' };

      const features = sub.state?.data?.features || [];
      const samples = features.slice(0, 10).map(f => {
        const color = sub.glLayer.props?.getFillColor?.(f);
        return {
          topazId: f.properties?.TopazID,
          color,
          hasColor: !!color
        };
      });

      return {
        mode: sub.state?.cmapMode,
        samplesWithColor: samples.filter(s => s.hasColor).length
      };
    });

    console.log('Cover verification:', JSON.stringify(coverVerification, null, 2));
    expect(coverVerification.mode).toBe('landuse_cover');
    expect(coverVerification.samplesWithColor).toBeGreaterThan(0);

      const coverShot = test.info().outputPath('landuse-cover.png');
      await page.screenshot({ path: coverShot });
      console.log(`Screenshot: ${coverShot}`);
  } else {
    console.log('Vegetation cover radio not available (RAP not enabled)');
  }
  });
});
