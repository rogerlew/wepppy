// Real public D-Tale UI, with no response interception or service substitution.
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { chromium } = require(process.cwd() + '/wepppy/weppcloud/static-src/node_modules/playwright');

(async () => {
  const label = process.argv[2];
  if (!label || !/^[A-Za-z0-9_-]+$/.test(label)) throw Error('A unique artifact label is required');
  const output = path.join(__dirname, `dtale_public_browser_${label}.json`);
  if (fs.existsSync(output)) throw Error('Retain prior evidence and choose a new label');
  const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, 'dtale_public_runtime_initial.json')));
  if (!fixture.completed || !fixture.named_source_unchanged) throw Error('Public HTTP prerequisite did not pass');
  if (!/^\/wc1\/runs\/qa\/qa-freshness-dtale-[a-f0-9]+$/.test(fixture.root)) throw Error('Disposable root required');
  if (fs.realpathSync(fixture.root) !== fixture.root) throw Error('Fixture root aliases are not accepted');
  const table = path.join(fixture.root, 'table.parquet');
  if (!fs.lstatSync(table).isFile() || fs.lstatSync(table).isSymbolicLink()) throw Error('Ordinary disposable table required');
  const before = fs.readFileSync(path.join(fixture.root, 'acceptance-evidence/before.parquet'));
  const after = fs.readFileSync(path.join(fixture.root, 'acceptance-evidence/after.parquet'));
  const auth = JSON.parse(fs.readFileSync('/tmp/wepppy-freshness-runtime-auth.json'));
  const browse = `${auth.host}/weppcloud/runs/${fixture.runid}/config/dtale/table.parquet`;
  const record = { root: fixture.root, runid: fixture.runid, transport: 'public browser; no routes intercepted',
    phases: [], errors: [], completed: false };
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ storageState: '/tmp/wepppy-freshness-browser-state.json', viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    page.on('pageerror', () => { record.errors.push('pageerror'); });
    async function phase(name, navigate, expectConflict, column, values) {
      const responsePromise = page.waitForResponse(response => /\/dtale\/data\//.test(new URL(response.url()).pathname), { timeout: 60000 });
      const navigation = await navigate();
      if (navigation.status() !== 200) throw Error(`Navigation HTTP ${navigation.status()}`);
      const response = await responsePromise;
      const payload = await response.json();
      const url = new URL(page.url());
      if (!/\/weppcloud\/dtale\/main\/[a-z0-9]+$/.test(url.pathname)) throw Error('Viewer redirect failed');
      const detail = { name, path: url.pathname, status: response.status(), grid: payload };
      record.phases.push(detail);
      fs.writeFileSync(output, JSON.stringify(record, null, 2) + '\n');
      if (expectConflict) {
        if (payload.success !== false || payload.code !== 'changed_source' || payload.results) throw Error('Expected stale generation rejection');
        try {
          await page.locator('.dtale-alert[role="alert"]').filter({ hasText: payload.error }).waitFor({ state: 'visible', timeout: 30000 });
        } catch (error) {
          detail.visibleBody = (await page.locator('body').innerText()).slice(0, 10000);
          detail.alerts = await page.locator('[role="alert"], .dtale-alert, .alert').allTextContents();
          detail.failureScreenshot = `dtale_public_browser_${label}_${name}_failure.png`;
          await page.screenshot({ path: path.join(__dirname, detail.failureScreenshot), fullPage: true });
          throw error;
        }
        detail.visibleGuidance = await page.locator('.dtale-alert[role="alert"]').allTextContents();
      } else {
        if (!payload.columns.some(item => item.name === column)) throw Error('Fresh schema absent');
        if (JSON.stringify([payload.results['0'][column], payload.results['1'][column]]) !== JSON.stringify(values)) throw Error('Fresh row values absent');
        await page.locator('.dtale-alert[role="alert"]').filter({ hasText: /Reopen.*browse/ }).waitFor({ state: 'hidden', timeout: 30000 });
      }
      const screenshot = path.join(__dirname, `dtale_public_browser_${label}_${name}.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      detail.screenshot = path.basename(screenshot);
      fs.writeFileSync(output, JSON.stringify(record, null, 2) + '\n');
    }
    await phase('current', () => page.goto(browse, { waitUntil: 'domcontentloaded', timeout: 120000 }), false, 'z', [8, 9]);
    fs.writeFileSync(table, before);
    await phase('stale', () => page.reload({ waitUntil: 'domcontentloaded', timeout: 120000 }), true);
    await phase('reopened', () => page.goto(browse, { waitUntil: 'domcontentloaded', timeout: 120000 }), false, 'a', [1, 2]);
    fs.writeFileSync(table, after);
    await phase('restored', () => page.goto(browse, { waitUntil: 'domcontentloaded', timeout: 120000 }), false, 'z', [8, 9]);
    record.completed = true;
  } finally {
    // Preserve the final fixture bytes expected by the earlier HTTP evidence.
    fs.writeFileSync(table, after);
    record.finalParquetSha256 = createHash('sha256').update(fs.readFileSync(table)).digest('hex');
    fs.writeFileSync(output, JSON.stringify(record, null, 2) + '\n');
    await browser.close();
  }
  console.log('Public D-Tale browser acceptance passed:', output);
})().catch(error => { console.error(error.message); process.exitCode = 1; });
