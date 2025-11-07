import { test } from '@playwright/test';
import {
  extractThemeIds,
  readContrastTargets,
  measureTarget,
  writeContrastReport
} from './theme-metrics.helpers.js';

const THEME_LAB_PATH = '/weppcloud/ui/components/';

test.describe('theme contrast metrics', () => {
  test('collects rendered contrast ratios for every theme', async ({ page, browser }) => {
    const baseUrl = process.env.SMOKE_BASE_URL || 'http://localhost:8080';
    const themeLabUrl = new URL(THEME_LAB_PATH, baseUrl);
    themeLabUrl.hash = 'theme-lab';

    await page.goto(themeLabUrl.toString(), { waitUntil: 'networkidle' });
    const themeIds = await extractThemeIds(page);
    const targets = await readContrastTargets(page);

    const results = [];
    for (const themeId of themeIds) {
      const context = await browser.newContext();
      const themedPage = await context.newPage();
      await themedPage.addInitScript(({ themeId: currentTheme }) => {
        const applyTheme = (theme) => {
          const root = document.documentElement;
          if (!root) return;
          if (theme && theme !== 'default') {
            root.setAttribute('data-theme', theme);
          } else {
            root.removeAttribute('data-theme');
          }
          try {
            if (!theme || theme === 'default') {
              window.localStorage.removeItem('wc-theme');
            } else {
              window.localStorage.setItem('wc-theme', theme);
            }
          } catch (err) {
            // ignore storage failures (private browsing, etc.)
          }
        };
        applyTheme(currentTheme);
        window.__applyThemeForPlaywright = applyTheme;
      }, { themeId });

      await themedPage.goto(themeLabUrl.toString(), { waitUntil: 'networkidle' });
      await themedPage.locator('#themeContrastTargets').waitFor({ state: 'attached' });

      for (const target of targets) {
        const measurements = await measureTarget(themedPage, target);
        for (const measurement of measurements) {
          results.push({
            theme: themeId,
            ...measurement
          });
        }
      }

      await context.close();
    }

    await writeContrastReport(results, { baseUrl: themeLabUrl.toString() });
  });
});
