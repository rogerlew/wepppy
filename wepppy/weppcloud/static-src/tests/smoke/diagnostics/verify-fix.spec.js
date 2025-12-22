/**
 * Diagnostic: verify slope/aspect colors are not default fills.
 */

import { test, expect } from '@playwright/test';

const diagnosticsEnabled = process.env.SMOKE_DIAGNOSTICS === 'true' || process.env.SMOKE_DIAGNOSTICS === '1';
const fallbackUrl = 'https://wc.bearhive.duckdns.org/weppcloud/runs/air-cooled-broadening/disturbed9002/';
const targetUrl = process.env.MAP_GL_URL || process.env.SMOKE_RUN_PATH || fallbackUrl;

function isDefaultColor(color) {
  if (!Array.isArray(color) || color.length < 3) {
    return false;
  }
  return color[0] === 255 && color[1] === 120 && color[2] === 0;
}

test.describe('diagnostic: slope/aspect colors', () => {
  test.skip(!diagnosticsEnabled, 'Set SMOKE_DIAGNOSTICS=1 to run diagnostic smoke specs.');

  test('slope and aspect should render non-default colors', async ({ page }) => {
    // Hard reload to bypass cache
    await page.goto(targetUrl, {
      waitUntil: 'networkidle'
    });

    await page.waitForSelector('#mapid', { timeout: 30000 });
    await page.waitForTimeout(3000);

  // Test Slope
    console.log('\n=== Testing Slope Choropleth ===');
    await page.locator('#sub_cmap_radio_slope').click();
    await page.waitForTimeout(2000);

  const slopeColors = await page.evaluate(() => {
    const sub = window.SubcatchmentDelineation?.getInstance();
    if (!sub?.glLayer) return { error: 'No GL layer' };

    const samples = sub.state?.data?.features?.slice(0, 5) || [];
    return samples.map(f => {
      const color = sub.glLayer.props?.getFillColor?.(f);
      return {
        topazId: f.properties?.TopazID,
        color,
        isOrange: color?.[0] === 255 && color?.[1] === 120 && color?.[2] === 0
      };
    });
  });

    console.log('Slope colors:', JSON.stringify(slopeColors, null, 2));

    const hasNonDefaultSlope = slopeColors.some(s => s.color && !isDefaultColor(s.color));
    expect(hasNonDefaultSlope).toBe(true);

  // Test Aspect
    console.log('\n=== Testing Aspect Choropleth ===');
    await page.locator('#sub_cmap_radio_aspect').click();
    await page.waitForTimeout(2000);

  const aspectColors = await page.evaluate(() => {
    const sub = window.SubcatchmentDelineation?.getInstance();
    if (!sub?.glLayer) return { error: 'No GL layer' };

    const samples = sub.state?.data?.features?.slice(0, 5) || [];
    return samples.map(f => {
      const color = sub.glLayer.props?.getFillColor?.(f);
      return {
        topazId: f.properties?.TopazID,
        color,
        isOrange: color?.[0] === 255 && color?.[1] === 120 && color?.[2] === 0
      };
    });
  });

    console.log('Aspect colors:', JSON.stringify(aspectColors, null, 2));

    const hasNonDefaultAspect = aspectColors.some(s => s.color && !isDefaultColor(s.color));
    expect(hasNonDefaultAspect).toBe(true);

  // Take screenshots as proof
    await page.locator('#sub_cmap_radio_slope').click();
    await page.waitForTimeout(1000);
    const slopeShot = test.info().outputPath('slope-fixed.png');
    await page.screenshot({ path: slopeShot, fullPage: true });
    console.log(`\n✓ Screenshot: ${slopeShot}`);

    await page.locator('#sub_cmap_radio_aspect').click();
    await page.waitForTimeout(1000);
    const aspectShot = test.info().outputPath('aspect-fixed.png');
    await page.screenshot({ path: aspectShot, fullPage: true });
    console.log(`✓ Screenshot: ${aspectShot}`);

    console.log('\n✅ SUCCESS: Slope and Aspect choropleths are rendering with non-default colors!');
  });
});
