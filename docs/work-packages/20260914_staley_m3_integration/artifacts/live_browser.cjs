// Generic development acceptance runner. No credentials/session tokens retained.
const { chromium } = require('/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const { createHash } = require('crypto');
const [base, runid, config, model, output, action = 'run'] = process.argv.slice(2);
assert(base && runid && config && ['M1', 'M3'].includes(model) && output);
assert.equal(base, 'https://wc.bearhive.duckdns.org', 'Only the authorized HTTPS development origin is allowed');
assert(/^[a-zA-Z0-9_-]+$/.test(runid) && /^[a-zA-Z0-9_-]+$/.test(config));
let stage = 'setup';
fs.mkdirSync(output, { recursive: true });
const log = [];
function record(value) {
  const row = { utc: new Date().toISOString(), ...value };
  log.push(row);
  fs.writeFileSync(path.join(output, 'browser.json'), JSON.stringify(log, null, 2));
  console.log(JSON.stringify(row));
}
function expand(seed, length) {
  let state = 2166136261;
  for (const char of seed) {
    state ^= char.codePointAt(0);
    state = (state + (state << 1) + (state << 4) + (state << 7) + (state << 8) + (state << 24)) >>> 0;
  }
  let out = '';
  while (out.length < length) {
    state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
    out += (state >>> 0).toString(16).padStart(8, '0');
  }
  return out.slice(0, length);
}
async function cap(page) {
  if (!await page.locator('input[name=cap_token]').count()) return;
  const endpoint = await page.locator('cap-widget').getAttribute('data-cap-api-endpoint');
  const url = new URL(endpoint, page.url());
  const response = await page.request.post(new URL('challenge', url).href);
  assert(response.ok(), 'CAP challenge HTTP failure');
  const { token, challenge: { c, s, d } } = await response.json();
  const solutions = [];
  for (let idx = 1; idx <= c; idx++) {
    const salt = expand(token + idx, s), target = expand(token + idx + 'd', d);
    let nonce = 0;
    while (!createHash('sha256').update(salt + nonce).digest('hex').startsWith(target)) nonce++;
    solutions.push(nonce);
  }
  const redeemed = await page.request.post(new URL('redeem', url).href, { data: { token, solutions } });
  assert(redeemed.ok(), 'CAP redeem HTTP failure');
  const result = await redeemed.json();
  assert(result.success && result.token, 'CAP redemption failed');
  await page.locator('input[name=cap_token]').evaluate((el, value) => {
    el.value = value; el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, result.token);
}
(async () => {
  const secrets = Object.fromEntries(fs.readFileSync('/workdir/wepppy/docker/secrets/dev-agent.env', 'utf8')
    .split('\n').filter(x => x.includes('=') && !x.startsWith('#')).map(x => {
      const i = x.indexOf('='); return [x.slice(0, i), x.slice(i + 1).replace(/^['"]|['"]$/g, '')];
    }));
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 1800 } });
    page.on('pageerror', () => record({ pageerror: true, stage }));
    const prefix = `/rq-engine/api/runs/${runid}/${config}`;
    async function read(url, name) {
      const result = await page.evaluate(async url => {
        const r = await WCHttp.requestWithSessionToken(url, { method: 'GET', cache: 'no-store' });
        return { status: r.response.status, body: r.body };
      }, url);
      record({ method: 'GET', path: url, status: result.status });
      if (name) fs.writeFileSync(path.join(output, name + '.json'), JSON.stringify(result.body, null, 2));
      return result.body;
    }
    stage = 'login';
    await page.goto(base + '/weppcloud/login');
    assert.equal(new URL(page.url()).origin, base);
    assert.equal(new URL(page.url()).pathname, '/weppcloud/login');
    const loginAction = await page.locator('input[name=password]').evaluate(el => el.form.action);
    assert.equal(new URL(loginAction, page.url()).origin, base);
    await page.locator('input[name=email]').fill(secrets.DEV_AGENT_EMAIL);
    await page.locator('input[name=password]').fill(secrets.DEV_AGENT_PASSWORD);
    await cap(page);
    await page.locator('input[type=submit],button[type=submit]').first().click();
    await page.waitForTimeout(1000);
    await page.goto(`${base}/weppcloud/runs/${runid}/${config}/`);
    stage = 'project';
    assert.equal(new URL(page.url()).origin, base);
    record({ page: new URL(page.url()).pathname, title: await page.title() });
    fs.writeFileSync(path.join(output, 'initial_page.txt'), (await page.locator('body').innerText()).slice(0, 20000));
    await page.locator('[data-pfdf-required] table').waitFor({ timeout: 120000 });
    let state;
    stage = 'discovery';
    if (action === 'run') {
    for (const [url, name] of [
      ['/rq-engine/api/configs', 'configs'], ['/rq-engine/api/endpoints?include_operation_docs=true', 'setup_endpoints'],
      [prefix + '/endpoints?include_operation_docs=true', 'endpoints'],
      [prefix + '/pipeline', 'pipeline'], [prefix + '/readiness', 'readiness'],
      [prefix + '/postfire-debris-flow/state', 'before']
    ]) await read(url, name);
    if (!await page.locator(`[name=model][value=${model}]`).isChecked()) {
      const saved = page.waitForResponse(r => r.url().endsWith('/postfire-debris-flow/selection') && r.request().method() === 'POST');
      await page.locator(`[name=model][value=${model}]`).check();
      const selectionResponse = await saved;
      const selectionBody = await selectionResponse.json();
      record({ method: 'POST', path: prefix + '/postfire-debris-flow/selection',
        status: selectionResponse.status(), code: selectionBody.error && selectionBody.error.code });
      assert.equal(selectionResponse.status(), 200);
    }
    const run = page.locator('[data-pfdf-action=run]');
    stage = 'run';
    await page.waitForFunction(() => !document.querySelector('[data-pfdf-action=run]').disabled, {}, { timeout: 30000 });
    const pending = page.waitForResponse(r => r.url().endsWith('/postfire-debris-flow/run') && r.request().method() === 'POST');
    await run.click();
    const response = await pending, body = await response.json();
    assert.equal(response.status(), 200, JSON.stringify(body));
    assert(body.job_id);
    record({ method: 'POST', path: prefix + '/postfire-debris-flow/run', status: response.status(), job_id: body.job_id, model });
    const deadline = Date.now() + 20 * 60 * 1000;
    while (Date.now() < deadline) {
      state = (await read(prefix + '/postfire-debris-flow/state')).result;
      if (state.run && state.run.job_id === body.job_id && ['complete', 'failed'].includes(state.run.phase)) break;
      await page.waitForTimeout(5000);
    }
    record({ job_id: body.job_id, phase: state.run.phase, result_id: state.results && state.results.id });
    } else {
      assert(['inspect', 'browse'].includes(action));
      state = (await read(prefix + '/postfire-debris-flow/state')).result;
    }
    fs.writeFileSync(path.join(output, 'state.json'), JSON.stringify(state, null, 2));
    stage = 'result_validation';
    await read('/rq-engine/api/jobstatus/' + state.run.job_id, 'jobstatus');
    await read('/rq-engine/api/jobinfo/' + state.run.job_id, 'jobinfo');
    if (action !== 'browse') {
    assert.equal(state.run.phase, 'complete', JSON.stringify(state.run));
    assert.equal(state.results.id, state.run.id); assert.equal(state.results.model, model);
    assert(state.results.current); assert(state.results.coverage);
    const downloadEvent = page.waitForEvent('download');
    await page.locator('[data-pfdf-download="valid_mask.tif"]').click();
    const download = await downloadEvent;
    await download.saveAs(path.join(output, 'valid_mask.tif'));
    await page.reload();
    await page.locator('[data-pfdf-files] table').waitFor({ timeout: 30000 });
    const completionMessage = await page.locator('[data-pfdf-message]').innerText();
    if (state.results.partial_reason) assert(completionMessage.includes(state.results.partial_reason));
    fs.writeFileSync(path.join(output, 'completion_message.txt'), completionMessage);
    const summary = await page.locator('[data-pfdf-files]').innerText();
    assert.match(summary, /Valid coverage/);
    fs.writeFileSync(path.join(output, 'summary.txt'), summary);
    await page.evaluate(() => { const c = UnitizerClient.getClientSync(); c.setGlobalPreference(0); c.dispatchPreferenceChange(); });
    await page.waitForTimeout(150);
    const siWarning = await page.locator('[data-pfdf-warning]').innerText();
    await page.evaluate(() => { const c = UnitizerClient.getClientSync(); c.setGlobalPreference(1); c.dispatchPreferenceChange(); });
    await page.waitForTimeout(150);
    const englishWarning = await page.locator('[data-pfdf-warning]').innerText();
    if (state.results.area_warning) assert.notEqual(siWarning, englishWarning);
    assert.equal(await page.locator('[data-pfdf-files]').innerText(), summary);
    record({ unit_preferences: 'SI/English', si_warning: siWarning, english_warning: englishWarning });
    await page.locator('#postfire-debris-flow').screenshot({ path: path.join(output, 'completed.png') });
    await read(prefix + '/outputs', 'outputs');
    }
    if (action === 'browse') {
      stage = 'browse';
      const root = `/wc1/runs/${runid.slice(0, 2)}/${runid}/postfire_debris_flow`;
      const names = fs.readdirSync(root, { recursive: true }).filter(name =>
        /^(source_preparation|attempts)\//.test(name));
      for (const basename of ['native_failure.json', 'native_thick.tif', 'request-00003.body', 'receipt.json', 'cache.sqlite-wal', 'valid_mask.tif']) {
        const name = names.find(name => name.endsWith('/' + basename));
        assert(name, 'Missing retained evidence category');
        const local = path.join(root, name);
        assert(fs.statSync(local).size <= 96 * 1024 * 1024);
        const expected = createHash('sha256').update(fs.readFileSync(local)).digest('hex');
        const project = `${base}/weppcloud/runs/${runid}/${config}`;
        const listing = await page.goto(project + '/browse/postfire_debris_flow/' + path.dirname(name) + '/', { waitUntil: 'domcontentloaded' });
        assert.equal(listing.status(), 200);
        assert((await page.locator('a').allTextContents()).some(label => label.trim() === basename));
        const file = await page.request.get(project + '/download/postfire_debris_flow/' + name);
        assert.equal(file.status(), 200);
        assert.equal(createHash('sha256').update(await file.body()).digest('hex'), expected);
        record({ ordinary_browse_download: name, status: 200, sha256: expected });
      }
    }
    record({ acceptance: 'passed', model, coverage: state.results.coverage });
  } finally { await browser.close(); }
// Playwright errors can include fill() arguments. Never persist raw exceptions.
})().catch(() => { record({ failure: true, stage }); process.exitCode = 1; });
