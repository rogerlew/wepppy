const { chromium } = require(process.cwd() + '/wepppy/weppcloud/static-src/node_modules/playwright');
const fs = require('fs');
const crypto = require('crypto');
const token = JSON.parse(fs.readFileSync('/tmp/mofe-forest-auth.json', 'utf8')).token;
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const results = [];
    for (const role of ['baseline','low','moderate','high','sbs','prescribed','thin30','thin50']) {
      const runid = 'mofe-0918-' + role;
      const url = 'https://wc-prod.bearhive.duckdns.org/weppcloud/runs/' + runid + '/canada-wbt-mofe/';
      const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      if (response.status() !== 200) throw new Error(runid + ': HTTP ' + response.status());
      await page.locator('#cap-gate').waitFor({ state: 'detached', timeout: 60000 });
      await page.locator('#landuse_form').waitFor({ state: 'attached', timeout: 60000 });
      const download = await context.request.get(url + 'download/landuse/hill_101.mofe.man', {
        headers: { Authorization: 'Bearer ' + token }
      });
      if (download.status() !== 200) throw new Error(runid + ': download HTTP ' + download.status());
      const body = await download.body();
      const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
      const local = fs.readFileSync('/wc1/runs/mo/' + runid + '/landuse/hill_101.mofe.man');
      if (sha(body) !== sha(local)) throw new Error(runid + ': downloaded bytes differ');
      const record = { runid, title: await page.title(), capGateAbsent: true,
                       downloadAuth: 'run-scoped service token',
                       downloadStatus: download.status(), downloadSha256: sha(body) };
      const outputPath = 'wepp/output/interchange/loss_pw0.hill.parquet';
      const output = await context.request.get(url + 'download/' + outputPath, {
        headers: { Authorization: 'Bearer ' + token }
      });
      if (output.status() !== 200) throw new Error(runid + ': output download HTTP ' + output.status());
      const outputBody = await output.body();
      const outputLocal = fs.readFileSync('/wc1/runs/mo/' + runid + '/' + outputPath);
      if (sha(outputBody) !== sha(outputLocal)) throw new Error(runid + ': output downloaded bytes differ');
      record.outputDownloadStatus = output.status();
      record.outputDownloadSha256 = sha(outputBody);
      results.push(record);
      console.log(JSON.stringify(record));
      await page.screenshot({ path: '/tmp/mofe-browser-' + role + '.png' });
    }
    fs.writeFileSync('/tmp/mofe-browser-results.json', JSON.stringify(results, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
