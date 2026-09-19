// Short-lived run-scoped bearer on stdin; never print credentials.
const { chromium } = require(process.cwd() + '/wepppy/weppcloud/static-src/node_modules/playwright');
const fs = require('fs');
const crypto = require('crypto');
const token = fs.readFileSync(0, 'utf8').trim();
const run = 'cover-defaults-validation-20260919';
const url = 'https://wc.bearhive.duckdns.org/weppcloud/runs/' + run + '/canada-wbt-mofe/';
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    if (response.status() !== 200) throw new Error('page HTTP ' + response.status());
    await page.locator('#cap-gate').waitFor({ state: 'detached', timeout: 60000 });
    await page.locator('#landuse_form').waitFor({ state: 'attached', timeout: 60000 });
    for (const relative of ['landuse/hill_101.mofe.man', 'wepp/runs/p1.man',
      'wepp/runs/p1.sol', 'wepp/output/interchange/loss_pw0.hill.parquet']) {
      const download = await context.request.get(url + 'download/' + relative, {
        headers: { Authorization: 'Bearer ' + token }
      });
      if (download.status() !== 200) throw new Error('download HTTP ' + download.status());
      const content = await download.body();
      const local = fs.readFileSync('/wc1/runs/co/' + run + '/' + relative);
      if (sha(content) !== sha(local)) throw new Error('download mismatch: ' + relative);
      console.log(JSON.stringify({ run, relative, pageStatus: response.status(),
        downloadStatus: download.status(), sha256: sha(content) }));
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
