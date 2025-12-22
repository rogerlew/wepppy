/**
 * Diagnostic: visual verification that slope/aspect are rendering.
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

test.describe('diagnostic: visual slope/aspect', () => {
  test.skip(!diagnosticsEnabled, 'Set SMOKE_DIAGNOSTICS=1 to run diagnostic smoke specs.');

  test('visual verification of slope and aspect', async ({ page }) => {
    await page.goto(targetUrl);
  await page.waitForSelector('#mapid', { timeout: 30000 });
  await page.waitForTimeout(3000);

  // Default view
    const defaultShot = test.info().outputPath('visual-default.png');
    await page.screenshot({ path: defaultShot });
    console.log(`Screenshot: ${defaultShot}`);

  // Click Slope
  console.log('\n=== Clicking Slope ===');
  await page.locator('#sub_cmap_radio_slope').click();
  await page.waitForTimeout(3000); // Wait for rendering

    const slopeShot = test.info().outputPath('visual-slope.png');
    await page.screenshot({ path: slopeShot });
    console.log(`Screenshot: ${slopeShot}`);

  // Verify slope colors are being computed
  const slopeVerification = await page.evaluate(() => {
    const sub = window.SubcatchmentDelineation?.getInstance();
    if (!sub?.glLayer) return { error: 'No layer' };

    const features = sub.state?.data?.features || [];
    const samples = features.slice(0, 10).map(f => {
      const color = sub.glLayer.props?.getFillColor?.(f);
      return {
        topazId: f.properties?.TopazID,
        color,
        isDefault: isDefaultColor(color)
      };
    });

    return {
      mode: sub.state?.cmapMode,
      totalFeatures: features.length,
      samplesWithDefault: samples.filter(s => s.isDefault).length,
      samplesWithColor: samples.filter(s => s.color && !s.isDefault).length,
      updateTriggers: sub.glLayer?.props?.updateTriggers
    };
  });

  console.log('Slope verification:', JSON.stringify(slopeVerification, null, 2));

  // Click Aspect
  console.log('\n=== Clicking Aspect ===');
  await page.locator('#sub_cmap_radio_aspect').click();
  await page.waitForTimeout(3000);

    const aspectShot = test.info().outputPath('visual-aspect.png');
    await page.screenshot({ path: aspectShot });
    console.log(`Screenshot: ${aspectShot}`);

  const aspectVerification = await page.evaluate(() => {
    const sub = window.SubcatchmentDelineation?.getInstance();
    if (!sub?.glLayer) return { error: 'No layer' };

    const features = sub.state?.data?.features || [];
    const samples = features.slice(0, 10).map(f => {
      const color = sub.glLayer.props?.getFillColor?.(f);
      return {
        topazId: f.properties?.TopazID,
        color,
        isDefault: isDefaultColor(color)
      };
    });

    return {
      mode: sub.state?.cmapMode,
      samplesWithDefault: samples.filter(s => s.isDefault).length,
      samplesWithColor: samples.filter(s => s.color && !s.isDefault).length,
      updateTriggers: sub.glLayer?.props?.updateTriggers
    };
  });

  console.log('Aspect verification:', JSON.stringify(aspectVerification, null, 2));

    expect(slopeVerification.samplesWithColor).toBeGreaterThan(0);
    expect(aspectVerification.samplesWithColor).toBeGreaterThan(0);

    console.log('\n✅ Visual verification complete - check screenshots!');
  });
});
