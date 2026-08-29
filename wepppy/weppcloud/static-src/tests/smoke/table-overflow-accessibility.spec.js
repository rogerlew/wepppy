import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

test.use({ ignoreHTTPSErrors: true });

const sourceDir = path.dirname(fileURLToPath(import.meta.url));
const foundationCss = path.resolve(sourceDir, '../../../static/css/ui-foundation.css');
const themesCss = path.resolve(sourceDir, '../../../static/css/themes/all-themes.css');
const overflowScript = path.resolve(sourceDir, '../../../static/js/table_overflow_accessibility.js');
const aaThemes = [
  'default',
  'light-high-contrast',
  'ayu-mirage',
  'ayu-mirage-bordered',
  'cursor-dark-midnight',
];

test.describe('table overflow accessibility', () => {
  test('makes overflow discoverable and supports horizontal keyboard and wheel input', async ({ page }) => {
    await page.setViewportSize({ width: 640, height: 900 });
    await page.setContent(`
      <!doctype html>
      <html lang="en" class="wc-page">
        <head><title>Table overflow accessibility fixture</title></head>
        <body>
          <main class="wc-page__body">
            <section class="wc-panel wc-stack" aria-labelledby="fixture-heading">
              <h2 id="fixture-heading">Outlet summary table</h2>
              <button id="before-table" type="button">Before table</button>
              <div class="wc-table-wrapper" style="max-width: 500px">
                <table class="wc-table wc-table--dense" id="report_probe_outlet_tbl" style="min-width: 1200px">
                  <caption>Outlet metrics and per-area values</caption>
                  <thead><tr><th>Metric</th><th>Value</th><th>Units</th><th>Per area</th><th>Per area units</th></tr></thead>
                  <tbody><tr><th>Runoff</th><td>42.7</td><td>mm</td><td>427</td><td>m³/ha</td></tr></tbody>
                </table>
              </div>
            </section>
          </main>
        </body>
      </html>
    `);
    await page.addStyleTag({ path: themesCss });
    await page.addStyleTag({ path: foundationCss });
    await page.addScriptTag({ path: overflowScript });

    const wrapper = page.locator('#report_probe_outlet_tbl').locator('..');

    await expect(wrapper).toHaveAttribute('data-wc-horizontal-overflow', 'true');
    await expect(wrapper).toHaveAttribute('tabindex', '0');
    await expect(wrapper).toHaveAttribute('role', 'region');
    await expect(wrapper).toHaveAttribute('aria-label', 'Outlet metrics and per-area values');
    const hint = wrapper.locator('xpath=preceding-sibling::*[1]');
    await expect(hint).toHaveClass(/wc-table-overflow-hint/);
    await expect(hint).toBeVisible();
    await expect(hint).toContainText('Shift + mouse wheel');
    await expect(hint).toContainText('Left and Right Arrow keys');

    await page.locator('#before-table').focus();
    await page.keyboard.press('Tab');
    await expect(wrapper).toBeFocused();
    await page.keyboard.press('ArrowRight');
    await expect.poll(() => wrapper.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);

    await wrapper.evaluate((element) => { element.scrollLeft = 0; });
    await wrapper.hover();
    await page.keyboard.down('Shift');
    await page.mouse.wheel(0, 240);
    await page.keyboard.up('Shift');
    await expect.poll(() => wrapper.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);

    const documentOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    expect(documentOverflow).toBeLessThanOrEqual(1);

    for (const theme of aaThemes) {
      const focusStyle = await wrapper.evaluate((element, themeId) => {
        const root = document.documentElement;
        if (themeId === 'default') {
          root.removeAttribute('data-theme');
        } else {
          root.setAttribute('data-theme', themeId);
        }
        element.focus();
        const style = window.getComputedStyle(element);
        const accentProbe = document.createElement('span');
        accentProbe.style.color = 'var(--wc-color-accent)';
        document.body.appendChild(accentProbe);
        const accent = window.getComputedStyle(accentProbe).color;
        accentProbe.remove();
        return {
          outlineColor: style.outlineColor,
          outlineStyle: style.outlineStyle,
          outlineWidth: Number.parseFloat(style.outlineWidth),
          accent,
        };
      }, theme);
      expect(focusStyle.outlineWidth, `${theme} outline width`).toBeGreaterThanOrEqual(2);
      expect(focusStyle.outlineStyle, `${theme} outline style`).not.toBe('none');
      expect(focusStyle.outlineColor, `${theme} focus token`).toBe(focusStyle.accent);
    }

    await page.evaluate(() => {
      document.documentElement.style.zoom = '2';
      window.WCTableOverflowAccessibility.refresh(document);
    });
    await expect(wrapper).toHaveAttribute('data-wc-horizontal-overflow', 'true');
    const zoomedDocumentOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    expect(zoomedDocumentOverflow).toBeLessThanOrEqual(1);

    const axe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(axe.violations).toEqual([]);
  });
});
