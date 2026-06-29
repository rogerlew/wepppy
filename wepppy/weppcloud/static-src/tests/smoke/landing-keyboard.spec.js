import { test, expect } from '@playwright/test';

/* global process */

test.use({ ignoreHTTPSErrors: true });

const baseURL = process.env.SMOKE_BASE_URL || 'http://localhost:8080';

const sitePrefix = (() => {
  const hasSmokePrefix = Object.prototype.hasOwnProperty.call(process.env, 'SMOKE_SITE_PREFIX');
  if (hasSmokePrefix) {
    return process.env.SMOKE_SITE_PREFIX || '';
  }
  try {
    const parsed = new URL(baseURL);
    const normalizedPath = (parsed.pathname || '').trim();
    if (normalizedPath && normalizedPath !== '/') {
      return normalizedPath.endsWith('/') ? normalizedPath.slice(0, -1) : normalizedPath;
    }
  } catch (_err) {
    // ignore invalid URL and fall back to repository default prefix
  }
  return '/weppcloud';
})();

function withSitePrefix(pathname) {
  const normalizedPath = pathname.startsWith('/') ? pathname : `/${pathname}`;
  const normalizedPrefix = (sitePrefix || '').trim();
  if (!normalizedPrefix || normalizedPrefix === '/') {
    return normalizedPath;
  }
  const safePrefix = normalizedPrefix.endsWith('/') ? normalizedPrefix.slice(0, -1) : normalizedPrefix;
  if (normalizedPath.startsWith(`${safePrefix}/`) || normalizedPath === safePrefix) {
    return normalizedPath;
  }
  return `${safePrefix}${normalizedPath}`;
}

function buildUrl(pathname) {
  if (/^https?:\/\//i.test(pathname)) {
    return pathname;
  }
  const base = baseURL.replace(/\/$/, '');
  if (base.endsWith('/weppcloud') && pathname.startsWith('/weppcloud/')) {
    return base + pathname.substring('/weppcloud'.length);
  }
  return new URL(pathname, base).toString();
}

async function activeElementName(page) {
  return page.evaluate(() => {
    const element = document.activeElement;
    if (!element || element === document.body) {
      return '';
    }
    const ariaLabel = element.getAttribute('aria-label');
    if (ariaLabel) {
      return ariaLabel.trim();
    }
    const labelledBy = element.getAttribute('aria-labelledby');
    if (labelledBy) {
      const text = labelledBy
        .split(/\s+/)
        .map((id) => document.getElementById(id)?.textContent?.trim() || '')
        .filter(Boolean)
        .join(' ');
      if (text) {
        return text;
      }
    }
    return (element.textContent || '').trim().replace(/\s+/g, ' ');
  });
}

test.describe('light landing keyboard accessibility', () => {
  test('loads installed light route and exposes a usable tab sequence', async ({ page }) => {
    const failedAssets = [];
    page.on('response', (response) => {
      if (response.status() >= 400 && response.url().includes('/landing/light/assets/')) {
        failedAssets.push(`${response.status()} ${response.url()}`);
      }
    });

    await page.goto(buildUrl(withSitePrefix('/landing/light/')), { waitUntil: 'networkidle' });

    await expect(page.getByRole('heading', { name: 'WEPPcloud', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeAttached();
    await expect(page.getByRole('region', { name: 'Explore Active WEPPcloud Projects' })).toBeVisible();
    expect(failedAssets).toEqual([]);

    const focusableCount = await page.evaluate(
      () => document.querySelectorAll('a[href], button, select, textarea, input, [tabindex]:not([tabindex="-1"])').length
    );
    expect(focusableCount).toBeGreaterThan(20);

    await expect(page.getByLabel('Run year filter')).toBeHidden();

    const seen = new Set();
    for (let index = 0; index < 18; index += 1) {
      await page.keyboard.press('Tab');
      const name = await activeElementName(page);
      if (name) {
        seen.add(name);
      }
    }

    expect(seen).toContain('Skip to main content');
    expect(seen).toContain('Interfaces');
    expect(seen).toContain('Docs');
    expect(seen).toContain('WEPP Model');
    expect(seen).toContain('FAQ');
    expect([...seen].some((name) => name.includes('Map of WEPPcloud run locations'))).toBe(true);
    expect(seen).toContain('Zoom map in');
    expect(seen).toContain('Zoom map out');
    expect(seen).toContain('Reset map view');
    expect(seen).toContain('Open run atlas filters');
    expect(seen).not.toContain('Run year filter');

    await page.getByRole('button', { name: 'Open run atlas filters' }).focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('button', { name: 'Close run atlas filters' })).toBeFocused();
    await expect(page.getByLabel('Run year filter')).toBeVisible();

    await page.keyboard.press('Tab');
    await expect(page.getByLabel('Run year filter')).toBeFocused();
  });
});
