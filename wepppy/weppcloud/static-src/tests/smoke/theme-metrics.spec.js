import { test } from '@playwright/test';
import {
  extractThemeIds,
  readContrastTargets,
  measureTarget,
  writeContrastReport
} from './theme-metrics.helpers.js';

const THEME_LAB_PATH = (() => {
  const hasSmokePrefix = Object.prototype.hasOwnProperty.call(process.env, 'SMOKE_SITE_PREFIX');
  const rawPrefix = hasSmokePrefix
    ? (process.env.SMOKE_SITE_PREFIX || '')
    : (process.env.SITE_PREFIX || '/weppcloud');
  const prefix = rawPrefix.trim();
  if (!prefix || prefix === '/') {
    return '/ui/components/';
  }
  const normalized = prefix.endsWith('/') ? prefix.slice(0, -1) : prefix;
  return `${normalized}/ui/components/`;
})();

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
        const syncStorage = (theme) => {
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
        const applyTheme = (theme) => {
          const root = document.documentElement;
          if (!root) return;
          if (theme && theme !== 'default') {
            root.setAttribute('data-theme', theme);
          } else {
            root.removeAttribute('data-theme');
          }
        };
        syncStorage(currentTheme);
        if (document.documentElement) {
          applyTheme(currentTheme);
        } else {
          document.addEventListener('DOMContentLoaded', () => applyTheme(currentTheme), { once: true });
        }
        window.__applyThemeForPlaywright = (theme) => {
          syncStorage(theme);
          applyTheme(theme);
        };
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
