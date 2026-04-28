import { expect, test } from '@playwright/test';
import {
  extractThemeIds,
  readContrastTargets,
  measureTarget,
  writeContrastReport
} from './theme-metrics.helpers.js';

const DEFAULT_ENFORCED_AA_THEMES = [
  'default',
  'light-high-contrast',
  'ayu-mirage',
  'ayu-mirage-bordered',
  'cursor-dark-midnight',
];

const JEXCEL_TARGET_ID = 'wc_jexcel_table';
const JEXCEL_REQUIRED_PAIR_NAMES = [
  'thead_selected_text_vs_background',
  'tbody_selected_text_vs_background',
  'tbody_row_index_text_vs_background',
  'tbody_regular_text_vs_background',
];
const GENEVA_MARKER_TARGET_ID = 'geneva_summary_marker_labels';
const GENEVA_MARKER_SERIES_IDS = [
  'series_0',
  'series_1',
  'series_2',
  'series_3',
  'series_4',
  'series_fallback',
];
const GENEVA_MARKER_LABEL_IDS = [
  'label_5m',
  'label_10m',
  'label_15m',
  'label_30m',
  'label_1h',
  'label_2h',
  'label_3h',
  'label_6h',
  'label_12h',
  'label_24h',
];
const GENEVA_MARKER_PAIR_NAMES = GENEVA_MARKER_SERIES_IDS.flatMap((seriesId) =>
  GENEVA_MARKER_LABEL_IDS.map((labelId) => `${seriesId}_${labelId}`)
);

const KNOWN_LIGHT_THEMES = new Set([
  'default',
  'light-high-contrast',
  'ayu-light',
  'ayu-light-bordered',
]);

const KNOWN_DARK_THEMES = new Set([
  'onedark',
  'dark-modern',
  'ayu-dark',
  'ayu-mirage',
  'ayu-dark-bordered',
  'ayu-mirage-bordered',
  'cursor-dark-anysphere',
  'cursor-dark-midnight',
  'cursor-dark-high-contrast',
]);

function classifyThemeTone(themeId) {
  if (KNOWN_LIGHT_THEMES.has(themeId)) {
    return 'light';
  }
  if (KNOWN_DARK_THEMES.has(themeId)) {
    return 'dark';
  }
  const normalized = String(themeId || '').toLowerCase();
  if (normalized.includes('light')) {
    return 'light';
  }
  if (normalized.includes('dark') || normalized.includes('mirage')) {
    return 'dark';
  }
  return null;
}

function relativeLuminance(color) {
  if (!color) {
    return null;
  }
  const toLinear = (channel) => {
    const normalized = Number(channel) / 255;
    return normalized <= 0.03928
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4;
  };
  return (
    0.2126 * toLinear(color.r)
    + 0.7152 * toLinear(color.g)
    + 0.0722 * toLinear(color.b)
  );
}

function parseEnforcedThemes() {
  const raw = String(process.env.THEME_METRICS_ENFORCED_THEMES || '').trim();
  if (!raw) {
    return DEFAULT_ENFORCED_AA_THEMES;
  }
  const parsed = raw
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);
  return parsed.length > 0 ? parsed : DEFAULT_ENFORCED_AA_THEMES;
}

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
    const enforcedThemes = parseEnforcedThemes();
    const enforcedThemeSet = new Set(enforcedThemes);
    const baseUrl = process.env.SMOKE_BASE_URL || 'http://localhost:8080';
    const themeLabUrl = new URL(THEME_LAB_PATH, baseUrl);
    themeLabUrl.hash = 'theme-lab';
    const extraHeaders = { 'X-Forwarded-Proto': 'https' };

    await page.setExtraHTTPHeaders(extraHeaders);
    await page.goto(themeLabUrl.toString(), { waitUntil: 'networkidle' });
    const themeIds = await extractThemeIds(page);
    const targets = await readContrastTargets(page);

    const results = [];
    for (const themeId of themeIds) {
      const context = await browser.newContext({ extraHTTPHeaders: extraHeaders });
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

    const observedThemes = new Set(results.map((entry) => entry.theme));
    const missingEnforcedThemes = enforcedThemes.filter((themeId) => !observedThemes.has(themeId));
    expect(
      missingEnforcedThemes,
      `Missing enforced themes in theme metrics output: ${missingEnforcedThemes.join(', ')}`
    ).toEqual([]);

    const aaFailures = results.filter(
      (entry) => enforcedThemeSet.has(entry.theme) && !entry.aaExempt && entry.passed === false
    );
    const informationalFailures = results.filter(
      (entry) => !enforcedThemeSet.has(entry.theme) && !entry.aaExempt && entry.passed === false
    );

    if (informationalFailures.length > 0) {
      const summaryByTheme = informationalFailures.reduce((acc, entry) => {
        acc[entry.theme] = (acc[entry.theme] || 0) + 1;
        return acc;
      }, {});
      console.log(
        `[theme-metrics] Non-enforced AA failures (${informationalFailures.length}): `
        + `${Object.entries(summaryByTheme).map(([theme, count]) => `${theme}=${count}`).join(', ')}`
      );
    }

    expect(
      aaFailures,
      `WCAG AA contrast failures in enforced themes (${enforcedThemes.join(', ')}):\n${aaFailures
        .slice(0, 20)
        .map(
          (entry) =>
            `- [${entry.theme}] ${entry.targetLabel || entry.targetId} :: ${entry.pairName || '(default)'} `
            + `(ratio=${entry.ratio}, threshold=${entry.threshold}, font=${entry.typography?.fontSize || 'n/a'}/${entry.typography?.fontWeight || 'n/a'})`
        )
        .join('\n')}`
    ).toEqual([]);

    const genevaMarkerResults = results.filter((entry) => entry.targetId === GENEVA_MARKER_TARGET_ID);
    const missingGenevaMarkerPairs = [];
    for (const themeId of themeIds) {
      for (const pairName of GENEVA_MARKER_PAIR_NAMES) {
        const entry = genevaMarkerResults.find(
          (item) => item.theme === themeId && item.pairName === pairName
        );
        if (!entry) {
          missingGenevaMarkerPairs.push(`${themeId}:${pairName}`);
        }
      }
    }
    expect(
      missingGenevaMarkerPairs,
      `Missing Geneva summary marker theme-metrics pairs: ${missingGenevaMarkerPairs.join(', ')}`
    ).toEqual([]);

    const genevaMarkerFailures = genevaMarkerResults.filter((entry) => entry.passed !== true);
    expect(
      genevaMarkerFailures,
      `Geneva summary marker label AA failures across all themes:\n${genevaMarkerFailures
        .slice(0, 40)
        .map(
          (entry) =>
            `- [${entry.theme}] ${entry.pairName || '(default)'} `
            + `(ratio=${entry.ratio}, threshold=${entry.threshold}, fg=${entry.foreground?.hex || 'n/a'}, bg=${entry.background?.hex || 'n/a'})`
        )
        .join('\n')}`
    ).toEqual([]);

    const jexcelResults = results.filter((entry) => entry.targetId === JEXCEL_TARGET_ID);
    const missingJexcelPairs = [];
    const jexcelToneFailures = [];
    const DARK_MAX_LUMINANCE = 0.5;
    const LIGHT_MIN_LUMINANCE = 0.5;

    for (const themeId of themeIds) {
      for (const pairName of JEXCEL_REQUIRED_PAIR_NAMES) {
        const entry = jexcelResults.find(
          (item) => item.theme === themeId && item.pairName === pairName
        );
        if (!entry) {
          missingJexcelPairs.push(`${themeId}:${pairName}`);
          continue;
        }
        if (!entry.background || !entry.background.rgba) {
          jexcelToneFailures.push({
            theme: themeId,
            pair: pairName,
            reason: 'background missing',
          });
          continue;
        }

        const tone = classifyThemeTone(themeId);
        if (!tone) {
          continue;
        }
        const luminance = relativeLuminance(entry.background.rgba);
        if (luminance === null) {
          jexcelToneFailures.push({
            theme: themeId,
            pair: pairName,
            reason: 'luminance unavailable',
          });
          continue;
        }

        if (tone === 'dark' && luminance > DARK_MAX_LUMINANCE) {
          jexcelToneFailures.push({
            theme: themeId,
            pair: pairName,
            reason: `expected dark background (luminance <= ${DARK_MAX_LUMINANCE}), got ${luminance.toFixed(3)}`,
          });
        }
        if (tone === 'light' && luminance < LIGHT_MIN_LUMINANCE) {
          jexcelToneFailures.push({
            theme: themeId,
            pair: pairName,
            reason: `expected light background (luminance >= ${LIGHT_MIN_LUMINANCE}), got ${luminance.toFixed(3)}`,
          });
        }
      }
    }

    expect(
      missingJexcelPairs,
      `Missing JSpreadsheet theme-metrics pairs: ${missingJexcelPairs.join(', ')}`
    ).toEqual([]);

    expect(
      jexcelToneFailures,
      `JSpreadsheet theme polarity failures:\n${jexcelToneFailures
        .map((failure) => `- [${failure.theme}] ${failure.pair}: ${failure.reason}`)
        .join('\n')}`
    ).toEqual([]);
  });
});
