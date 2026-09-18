// Read-only production page/download checks against remotely captured hashes.
const { chromium } = require(process.cwd() + '/wepppy/weppcloud/static-src/node_modules/playwright');
const fs = require('fs');
const crypto = require('crypto');
const evidence = '/tmp/mofe-production-evidence';
const token = JSON.parse(fs.readFileSync('/tmp/mofe-production-auth.json', 'utf8')).token;
const role = process.argv[2];
const privateRun = process.argv[3] === 'private';
if (privateRun) {
  const visibility = JSON.parse(fs.readFileSync(`${evidence}/${role}-visibility.json`, 'utf8'));
  const ownership = JSON.parse(fs.readFileSync(`${evidence}/${role}-owner-presence.json`, 'utf8'));
  if (visibility.pre_repair_public_marker !== false || visibility.current_public_marker !== false
      || !(ownership.owner_count > 0) || ownership.runid !== visibility.runid) {
    throw new Error('Private-page expectation requires unchanged archived visibility evidence');
  }
}
const readback = JSON.parse(fs.readFileSync(`${evidence}/${role}-final-readback.json`, 'utf8'));
const sources = JSON.parse(fs.readFileSync(`${evidence}/${role}-summary-sources.json`, 'utf8'));
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    let pageStatus;
    page.on('response', response => {
      if (response.request().isNavigationRequest() && response.frame() === page.mainFrame()) {
        pageStatus = response.status();
      }
    });
    const runid = readback.runid;
    const url = `https://wepp.cloud/weppcloud/runs/${runid}/canada-wbt-mofe/`;
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    if (response.status() !== 200 && !(privateRun && response.status() === 404)) {
      throw new Error(`Page HTTP ${response.status()}`);
    }
    await page.locator('#cap-gate').waitFor({ state: 'detached', timeout: 60000 });
    if (privateRun) {
      await page.getByText('404 - Resource Not Found', { exact: true }).waitFor({ timeout: 60000 });
      if (pageStatus !== 404 || !(await page.title()).includes('Run Not Found')) {
        throw new Error('Private page did not return the expected anonymous access denial');
      }
    } else {
      await page.locator('#landuse_form').waitFor({ state: 'attached', timeout: 60000 });
      if (pageStatus !== 200) throw new Error(`Run page HTTP ${pageStatus}`);
    }
    const downloads = [];
    for (const [path, expected] of [
      ['landuse/hill_101.mofe.man', readback.manifests['landuse/hill_*.mofe.man']['landuse/hill_101.mofe.man']],
      ['wepp/output/interchange/loss_pw0.hill.parquet', sources[0].sha256],
    ]) {
      const result = await context.request.get(url + 'download/' + path, {
        headers: { Authorization: 'Bearer ' + token }
      });
      if (result.status() !== 200) throw new Error(`${path}: HTTP ${result.status()}`);
      const sha256 = crypto.createHash('sha256').update(await result.body()).digest('hex');
      if (sha256 !== expected) throw new Error(`${path}: download hash mismatch`);
      downloads.push({ path, status: result.status(), sha256 });
    }
    const record = { runid, title: await page.title(), capGateAbsent: true, pageStatus,
      pageAccess: privateRun ? 'expected anonymous denial; preserved private run' : 'public run page',
      ownerAuthenticatedPage: 'not tested', downloads };
    fs.writeFileSync(`${evidence}/${role}-browser.json`, JSON.stringify(record, null, 2));
    await page.screenshot({ path: `${evidence}/${role}-browser.png` });
    console.log(JSON.stringify(record));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
