// Real browser checks; reads local agent credentials without logging them.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(path.join(process.cwd(), 'wepppy/weppcloud/static-src/node_modules/@playwright/test'));

(async () => {
  const restricted = process.argv[2] === 'false';
  const base = 'https://wc.bearhive.duckdns.org';
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    const captchaRequests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {
      if (request.url().includes('/cap/assets/')) captchaRequests.push(request.url().split('/').pop());
    });
    await page.goto(base + '/weppcloud/interfaces/', { waitUntil: 'networkidle' });
    const anonymousForms = await page.locator('.wc-run-form').count();
    if (restricted) {
      if (anonymousForms || await page.locator('cap-widget, #run-context-menu').count()) throw new Error('Restricted anonymous creation DOM present');
      if (captchaRequests.length) throw new Error('Restricted page requested CAPTCHA assets');
      await page.getByRole('link', { name: 'Sign in', exact: true }).click();
    } else {
      if (!anonymousForms) throw new Error('Default anonymous launch forms missing');
      await page.goto(base + '/weppcloud/login', { waitUntil: 'networkidle' });
    }
    const values = {};
    for (const line of fs.readFileSync('docker/secrets/dev-agent.env', 'utf8').split('\n')) {
      const index = line.indexOf('=');
      if (index > 0 && !line.startsWith('#')) values[line.slice(0, index)] = line.slice(index + 1).trim().replace(/^["']|["']$/g, '');
    }
    await page.locator('input[name="email"]').fill(values.DEV_AGENT_EMAIL);
    await page.locator('input[name="password"]').fill(values.DEV_AGENT_PASSWORD);
    if (await page.locator('.wc-cap-trigger').count()) {
      await page.locator('.wc-cap-trigger').click();
      await page.waitForFunction(() => !!document.querySelector('input[name="cap_token"]')?.value, { timeout: 30000 });
    }
    await page.locator('input[type="submit"], button[type="submit"]').first().click();
    await page.waitForURL(url => !url.pathname.endsWith('/login'), { timeout: 30000 });
    await page.goto(base + '/weppcloud/interfaces/', { waitUntil: 'networkidle' });
    const authenticatedForms = await page.locator('.wc-run-form').count();
    if (!authenticatedForms || await page.locator('cap-widget').count()) throw new Error('Authenticated launch state incorrect');
    if (errors.length) throw new Error('Browser errors: ' + errors.join('; '));
    console.log(JSON.stringify({ mode: restricted ? 'false' : 'true', anonymousForms, authenticatedForms, errors, checks: ['real Chromium page load', 'sign-in flow', 'authenticated launch availability', 'no page exceptions'] }, null, 2));
  } finally {
    await browser.close();
  }
// Playwright errors can include locator.fill values; never print their messages.
})().catch(() => { console.error("Creation-policy browser canary failed; inspect locally without logging credentials."); process.exitCode = 1; });
