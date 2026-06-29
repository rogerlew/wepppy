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

async function activeElementSnapshot(page) {
  return page.evaluate(() => {
    const element = document.activeElement;
    if (!element || element === document.body) {
      return {
        name: '',
        tagName: '',
        isMapStage: false,
        hasVisibleFocus: false,
        top: 0,
        bottom: 0,
      };
    }
    const ariaLabel = element.getAttribute('aria-label');
    const labelledBy = element.getAttribute('aria-labelledby');
    let name = ariaLabel ? ariaLabel.trim() : '';
    if (!name && labelledBy) {
      name = labelledBy
        .split(/\s+/)
        .map((id) => document.getElementById(id)?.textContent?.trim() || '')
        .filter(Boolean)
        .join(' ');
    }
    if (!name) {
      name = (element.textContent || '').trim().replace(/\s+/g, ' ');
    }

    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    const outlineWidth = Number.parseFloat(style.outlineWidth || '0');
    const hasVisibleFocus =
      (outlineWidth >= 2 && style.outlineStyle !== 'none') ||
      (style.boxShadow && style.boxShadow !== 'none');

    return {
      name,
      tagName: element.tagName,
      isMapStage: element.classList.contains('light-map-stage'),
      hasVisibleFocus,
      top: rect.top,
      bottom: rect.bottom,
    };
  });
}

test.describe('light landing keyboard accessibility', () => {
  test('loads installed light route and exposes a usable tab sequence', async ({ page }) => {
    const failedVariantRequests = [];
    page.on('response', (response) => {
      const url = response.url();
      const failedVariantAsset = url.includes('/landing/light/assets/');
      const failedVariantData = url.includes('/landing/light/run-locations.json');
      if (response.status() >= 400 && (failedVariantAsset || failedVariantData)) {
        failedVariantRequests.push(`${response.status()} ${url}`);
      }
    });

    await page.goto(buildUrl(withSitePrefix('/landing/light/')), { waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('heading', { name: 'WEPPcloud', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeAttached();
    await expect(page.getByRole('region', { name: 'Explore Active WEPPcloud Projects' })).toBeVisible();
    expect(failedVariantRequests).toEqual([]);
    expect(await page.evaluate(() => document.activeElement === document.body)).toBe(true);

    const focusableCount = await page.evaluate(
      () => document.querySelectorAll('a[href], button, select, textarea, input, [tabindex]:not([tabindex="-1"])').length
    );
    expect(focusableCount).toBeGreaterThan(20);
    await expect(page.getByRole('link', { name: 'Interfaces' })).toHaveAttribute('tabindex', '0');
    await expect(page.getByRole('link', { name: 'Docs', exact: true })).toHaveAttribute('tabindex', '0');

    await expect(page.getByLabel('Run year filter')).toBeHidden();

    const expectedSequence = [
      'Skip to main content',
      'Interfaces',
      'Docs',
      'Research',
      'Login',
      'WEPP Model',
      'FAQ',
      'Zoom map in',
      'Zoom map out',
      'Reset map view',
      'Open run atlas filters',
    ];
    const seen = [];
    const viewportHeight = page.viewportSize()?.height || 720;
    for (let index = 0; index < expectedSequence.length; index += 1) {
      await page.keyboard.press('Tab');
      const snapshot = await activeElementSnapshot(page);
      seen.push(snapshot.name);
      expect(snapshot.isMapStage).toBe(false);
      expect(snapshot.hasVisibleFocus).toBe(true);
      expect(snapshot.top).toBeGreaterThanOrEqual(0);
      expect(snapshot.bottom).toBeLessThanOrEqual(viewportHeight);
    }

    expect(seen).toEqual(expectedSequence);
    expect(seen).not.toContain('Run year filter');

    await page.getByRole('button', { name: 'Open run atlas filters' }).focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('button', { name: 'Close run atlas filters' })).toBeFocused();
    await expect(page.getByLabel('Run year filter')).toBeVisible();

    await page.keyboard.press('Tab');
    await expect(page.getByLabel('Run year filter')).toBeFocused();
    expect((await activeElementSnapshot(page)).hasVisibleFocus).toBe(true);
  });
});
