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

async function expectKeyboardFocus(control) {
  await expect(control).toBeFocused();
  const visibleFocus = await control.evaluate((element) => {
    const style = getComputedStyle(element);
    return (parseFloat(style.outlineWidth) > 0 && style.outlineStyle !== 'none')
      || style.boxShadow !== 'none';
  });
  expect(visibleFocus).toBe(true);
}

test('landing keyboard accessibility on the canonical home', async ({ page }) => {
  await page.goto(buildUrl(withSitePrefix('/')), { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { level: 1, name: 'WEPPcloud' })).toBeVisible();
  await page.keyboard.press('Tab');
  await expectKeyboardFocus(page.getByRole('link', { name: 'Skip to main content' }));
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
  await page.keyboard.press('Tab');
  await expectKeyboardFocus(page.getByRole('link', { name: 'WEPP Model', exact: true }));
  await page.keyboard.press('Tab');
  await expectKeyboardFocus(page.getByRole('link', { name: 'FAQ', exact: true }));

  if (await page.locator('[data-run-atlas]').count()) {
    const map = page.getByRole('region', { name: 'Run Atlas map', exact: true });
    await expect(map).toBeVisible();
    await page.keyboard.press('Tab');
    await expectKeyboardFocus(map);
    await page.keyboard.press('ArrowRight');
    for (const action of ['Zoom map in', 'Zoom map out', 'Reset map view']) {
      const button = page.getByRole('button', { name: action });
      const colors = () => button.evaluate((el) => {
        const style = getComputedStyle(el);
        return [style.backgroundColor, style.borderColor];
      });
      const resting = await colors();
      await page.keyboard.press('Tab');
      await expect(button).toBeFocused();
      await expect.poll(colors).not.toEqual(resting);
      await page.keyboard.press('Enter');
    }
  }
});
