// Actual installed D-Tale UI; only the disposable dataset grid response is intercepted.
const fs = require('fs');
const path = require('path');
const { chromium } = require(path.resolve('wepppy/weppcloud/static-src/node_modules/@playwright/test'));

(async () => {
  const artifactRoot = __dirname;
  const fixture = JSON.parse(fs.readFileSync(path.join(artifactRoot, 'dtale_ui_contract_fixture.json')));
  const browser = await chromium.launch({ headless: true });
  const results = [];
  const message = 'This file changed or cannot be verified. Reopen the dataset from browse.';
  try {
    for (const status of [409, 200]) {
      const page = await browser.newPage();
      const errors = [];
      let intercepted = 0;
      page.on('pageerror', error => errors.push(error.message));
      // Direct published service lacks the normal proxy's /weppcloud stripping.
      // Preserve installed HTML/JS bytes while reproducing that URL mapping.
      await page.route('**/weppcloud/dtale/**', async route => {
        const response = await route.fetch({url: route.request().url().replace('/weppcloud/dtale/', '/dtale/')});
        await route.fulfill({response});
      });
      await page.route(`**/dtale/data/${fixture.data_id}*`, async route => {
        intercepted++;
        await route.fulfill({status, contentType: 'application/json', body: JSON.stringify({
          success: false, error: message, code: 'changed_source',
        })});
      });
      await page.goto(`http://127.0.0.1:9010/dtale/main/${fixture.data_id}`, {waitUntil: 'networkidle'});
      await page.waitForTimeout(1500);
      const alerts = await page.locator('.dtale-alert[role="alert"]').allTextContents();
      await page.screenshot({path: path.join(artifactRoot, `dtale_ui_grid_${status}.png`), fullPage: true});
      results.push({status, intercepted, alerts, guidance_visible: alerts.some(value => value.includes(message)), errors,
        proxy_prefix_mapping: '/weppcloud/dtale/* -> /dtale/* on same local service'});
      await page.close();
    }
  } finally {
    await browser.close();
    fs.writeFileSync(path.join(artifactRoot, 'dtale_ui_contract_probe.json'), JSON.stringify(results, null, 2) + '\n');
  }
  console.log(JSON.stringify(results, null, 2));
})().catch(error => {console.error(error); process.exitCode = 1;});
