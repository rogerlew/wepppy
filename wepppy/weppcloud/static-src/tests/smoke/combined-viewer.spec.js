import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const base = process.env.SMOKE_BASE_URL || 'https://wc.bearhive.duckdns.org';
const catalog = JSON.parse(fs.readFileSync(path.join(repo, 'wepppy/weppcloud/utils/portland_collections.json'), 'utf8'));
function fnv32aHash(text) {
  let value = 2166136261;
  for (const char of text) {
    value ^= char.codePointAt(0);
    value =
      (value + (value << 1) + (value << 4) + (value << 7) + (value << 8) + (value << 24)) >>> 0;
  }
  return value >>> 0;
}

function capExpandHex(seed, length) {
  let state = fnv32aHash(seed);

  function nextU32() {
    state ^= (state << 13) >>> 0;
    state ^= state >>> 17;
    state ^= (state << 5) >>> 0;
    state >>>= 0;
    return state;
  }

  let out = '';
  while (out.length < length) {
    out += nextU32().toString(16).padStart(8, '0');
  }
  return out.slice(0, length);
}

function buildCapPairs(challengePayload) {
  const token = String(
    challengePayload && challengePayload.token ? challengePayload.token : ''
  ).trim();
  const challenge = challengePayload && challengePayload.challenge;
  if (!token || !challenge || typeof challenge !== 'object') {
    throw new Error(
      `Unexpected CAP challenge payload: ${JSON.stringify(challengePayload).slice(0, 240)}`
    );
  }

  const count = Number(challenge.c || 0);
  const saltLength = Number(challenge.s || 0);
  const targetLength = Number(challenge.d || 0);
  if (
    !Number.isInteger(count) ||
    !Number.isInteger(saltLength) ||
    !Number.isInteger(targetLength) ||
    count <= 0 ||
    saltLength <= 0 ||
    targetLength <= 0
  ) {
    throw new Error(`Invalid CAP challenge dimensions: ${JSON.stringify(challenge)}`);
  }

  const pairs = [];
  for (let idx = 1; idx <= count; idx += 1) {
    pairs.push([
      capExpandHex(`${token}${idx}`, saltLength),
      capExpandHex(`${token}${idx}d`, targetLength),
    ]);
  }
  return { token, pairs };
}

function solvePowNonce(salt, targetHex) {
  let nonce = 0;
  while (true) {
    const digestHex = createHash('sha256').update(`${salt}${nonce}`, 'utf8').digest('hex');
    if (digestHex.startsWith(targetHex)) {
      return nonce;
    }
    nonce += 1;
  }
}

async function solveCapTokenFromEndpoint(page, endpoint) {
  const endpointUrl = new URL(endpoint, page.url());
  const challengeUrl = new URL('challenge', endpointUrl).toString();
  const redeemUrl = new URL('redeem', endpointUrl).toString();

  const challengeResponse = await page.request.post(challengeUrl, { headers: {} });
  if (!challengeResponse.ok()) {
    throw new Error(
      `CAP challenge failed: ${challengeResponse.status()} ${challengeResponse.statusText()}`
    );
  }
  const challengePayload = await challengeResponse.json();
  const { token, pairs } = buildCapPairs(challengePayload);
  const solutions = pairs.map(([salt, targetHex]) => solvePowNonce(salt, targetHex));

  const redeemResponse = await page.request.post(redeemUrl, {
    headers: {},
    data: { token, solutions },
  });
  if (!redeemResponse.ok()) {
    throw new Error(`CAP redeem failed: ${redeemResponse.status()} ${redeemResponse.statusText()}`);
  }
  const redeemPayload = await redeemResponse.json();
  const capToken = String(redeemPayload && redeemPayload.token ? redeemPayload.token : '').trim();
  if (!capToken || !redeemPayload.success) {
    throw new Error(
      `CAP redeem did not return a success token: ${JSON.stringify(redeemPayload).slice(0, 240)}`
    );
  }
  return capToken;
}


async function login(page) {
  const pairs = Object.fromEntries(fs.readFileSync(path.join(repo, 'docker/secrets/dev-agent.env'), 'utf8')
    .split('\n').filter((s) => s.includes('=') && !s.startsWith('#')).map((line) => {
      const i = line.indexOf('='); return [line.slice(0,i), line.slice(i+1).trim().replace(/^["']|["']$/g,'')];
    }));
  await page.goto(base + '/weppcloud/login');
  await page.locator('input[name="email"]').fill(pairs.DEV_AGENT_EMAIL);
  await page.locator('input[name="password"]').fill(pairs.DEV_AGENT_PASSWORD);
  const cap = page.locator('cap-widget[data-cap-api-endpoint]');
  if (await cap.count()) {
    const token = await solveCapTokenFromEndpoint(page, await cap.getAttribute('data-cap-api-endpoint'));
    await page.locator('input[name="cap_token"]').evaluate((input, value) => {input.value=value;}, token);
  }
  await Promise.all([page.waitForURL((url) => !url.pathname.endsWith('/login')),
    page.locator('input[type="submit"], button[type="submit"]').first().click()]);
}
function url(item) {
  const q = new URLSearchParams(Object.entries(item).map(([k,v]) => [k, typeof v === 'object' ? JSON.stringify(v) : String(v)]));
  return base + '/weppcloud/combined_ws_viewer/?' + q.toString();
}
test('Portland collection browser acceptance', async ({ page, browser }, info) => {
  test.setTimeout(1800000);
  page.setDefaultTimeout(30000);
  if (process.env.PCV_AUTH_MODE === 'drilldown') {
    await login(page);
    const runid = catalog.collections[0].ws[0].runid;
    const destination = `${base}/weppcloud/runs/${runid}/portland-snow/`;
    const response = await page.goto(destination);
    expect(response.status()).toBe(200);
    const migrationGate = (await page.title()).startsWith('Migration Status');
    if (migrationGate) {
      await page.getByRole('link', {name: 'Load Without Migrating', exact: true}).click();
    }
    await expect(page).toHaveTitle(runid);
    await expect(page.locator('#wepp')).toBeVisible();
    console.log('Authenticated run drilldown:', JSON.stringify({
      runid, cfg: 'portland-snow', status: response.status(), title: await page.title(),
      identity: 'restored dev-agent baseline; independent Admin grant',
      migrationGate, usedExistingLoadWithoutMigrating: migrationGate,
      weppSectionVisible: true,
    }));
    return;
  }
  if (process.env.PCV_AUTH_MODE === 'audit') {
    const context = await browser.newContext({storageState: path.join(repo,'docker/secrets/pcv-member-session.json')});
    const auditPage = await context.newPage();
    auditPage.on('pageerror', (error) => console.log('AUDIT PAGE ERROR:',error.message));
    const landing = await auditPage.goto(base+'/weppcloud/locations/portland-municipal/');
    expect(landing.status()).toBe(200);
    const links = await auditPage.locator('a[href*="combined_ws_viewer/?"]').evaluateAll((nodes) => nodes.map((node) => node.href));
    expect(links).toHaveLength(9);
    expect(links.every((link) => new URL(link).origin === base)).toBeTruthy();
    const ownerUrl = new URL(base+'/weppcloud/bounds_ws_viewer/');
    ownerUrl.searchParams.set('ws',JSON.stringify([{runid:process.env.PCV_OWNER_RUN_ID}]));
    expect(process.env.PCV_OWNER_RUN_ID).toBeTruthy();
    const ownerStatus = (await auditPage.request.get(ownerUrl.href)).status();
    expect([200,409]).toContain(ownerStatus);
    const publicContext = await browser.newContext();
    expect((await publicContext.request.get(url(catalog.collections[0]))).status()).toBe(403);
    const publicUrl = new URL(base+'/weppcloud/bounds_ws_viewer/');
    publicUrl.searchParams.set('ws',JSON.stringify([{runid:process.env.PCV_PUBLIC_RUN_ID}]));
    expect(process.env.PCV_PUBLIC_RUN_ID).toBeTruthy();
    const publicStatus = (await publicContext.request.get(publicUrl.href)).status();
    expect([200,409]).toContain(publicStatus);
    await publicContext.close();
    console.log('Independent live grants:',JSON.stringify({owner:{runid:process.env.PCV_OWNER_RUN_ID,status:ownerStatus},public:{runid:process.env.PCV_PUBLIC_RUN_ID,status:publicStatus}}));
    const mixed = new URL(url(catalog.collections[0]));
    mixed.searchParams.set('ws',JSON.stringify([...catalog.collections[0].ws,{runid:'pcv-unrelated-private'}]));
    expect((await auditPage.request.get(mixed.href)).status()).toBe(403);
    for (const endpoint of ['combined_ws_viewer','combined_ws_viewer2','bounds_ws_viewer']) {
      expect((await auditPage.request.get(base+'/weppcloud/'+endpoint+'/?data_uri=data:application/json,{}')).status()).toBe(400);
      const alias = new URL(url(catalog.collections[0]));
      alias.pathname = '/weppcloud/'+endpoint+'/';
      expect((await auditPage.request.get(alias.href)).status()).toBe(200);
    }
    expect((await auditPage.request.post(base+'/weppcloud/combined_ws_viewer/url_generator/', {form:{runids:catalog.collections[0].ws[0].runid}})).status()).toBe(400);
    const hostile = new URL(url(catalog.collections[0]));
    hostile.searchParams.set('ws', JSON.stringify([{runid:'../outside'}]));
    expect((await auditPage.request.get(hostile.href)).status()).toBe(400);
    expect((await auditPage.request.post(base+'/weppcloud/combined_ws_viewer/url_generator/', {form:{runids:catalog.collections[0].ws[0].runid,csrf_token:'invalid'}})).status()).toBe(400);
    await auditPage.goto(url(catalog.collections[0]));
    await expect(auditPage.locator('#pcv-status')).toContainText('7 watersheds', {timeout:120000});
    const canvas = auditPage.locator('#pcv-map canvas');
    await canvas.scrollIntoViewIfNeeded();
    await auditPage.addScriptTag({url:base+'/weppcloud/static/js/tinyqueue.js'});
    await auditPage.addScriptTag({url:base+'/weppcloud/static/js/polylabel.js'});
    const pickPoint = await auditPage.evaluate(async () => {
      const ctx = JSON.parse(document.getElementById('pcv-config').textContent);
      const run = ctx.ws[0];
      const geo = await fetch(`${ctx.sitePrefix}/runs/${run.runid}/${run.cfg}/resources/subcatchments.json`).then((r) => r.json());
      const canvas = document.querySelector('#pcv-map canvas');
      const viewport = new window.deck.WebMercatorViewport({width:canvas.clientWidth,height:canvas.clientHeight,latitude:ctx.center[0],longitude:ctx.center[1],zoom:ctx.zoom});
      const polygons = geo.features.flatMap((f) => f.geometry.type === 'MultiPolygon' ? f.geometry.coordinates : [f.geometry.coordinates]);
      const size = (polygon) => {const ring=polygon[0];return Math.abs(ring.reduce((sum,p,i) => {const q=ring[(i+1)%ring.length];return sum+p[0]*q[1]-q[0]*p[1];},0));};
      polygons.sort((a,b) => size(b)-size(a));
      for (const polygon of polygons.slice(0,30)) {
        const coordinate = window.polylabel(polygon,0.000001);
        const point = viewport.project(coordinate);
        if (point[0]>5 && point[1]>5 && point[0]<canvas.clientWidth-5 && point[1]<canvas.clientHeight-5) return point;
      }
      throw new Error('No visible polygon interior found for picking');
    });
    await auditPage.screenshot({path:'/tmp/pcv-audit-map.png',fullPage:true});
    const box = await canvas.boundingBox();
    console.log('Picking polygon interior:',JSON.stringify({box,pickPoint}));
    await expect.poll(async () => {
      await auditPage.mouse.click(box.x+pickPoint[0],box.y+pickPoint[1]);
      return auditPage.locator('#pcv-details a').count();
    }, {timeout:30000}).toBe(1);
    console.log('Visible polygon mouse picking passed');
    const pickedDetails = await auditPage.locator('#pcv-details').textContent();
    await canvas.scrollIntoViewIfNeeded();
    const mapBox = await canvas.boundingBox();
    await auditPage.mouse.move(mapBox.x+mapBox.width/2,mapBox.y+mapBox.height/2);
    await auditPage.mouse.wheel(0,-500);
    await expect.poll(async () => {
      await auditPage.locator('#pcv-share').click();
      return Number(new URL(await auditPage.locator('#pcv-share-url').inputValue()).searchParams.get('zoom'));
    }).not.toBe(catalog.collections[0].zoom);
    await canvas.scrollIntoViewIfNeeded();
    const dragBox = await canvas.boundingBox();
    await auditPage.mouse.move(dragBox.x+dragBox.width/2,dragBox.y+dragBox.height/2);
    await auditPage.mouse.down();
    await auditPage.mouse.move(dragBox.x+dragBox.width/2+100,dragBox.y+dragBox.height/2+50,{steps:10});
    await auditPage.mouse.up();
    await auditPage.locator('#pcv-share').click();
    expect(await auditPage.locator('#pcv-details').textContent()).toBe(pickedDetails);
    const moved = new URL(await auditPage.locator('#pcv-share-url').inputValue());
    expect(JSON.parse(moved.searchParams.get('center'))).not.toEqual(catalog.collections[0].center);
    const config = await auditPage.locator('#pcv-config').textContent().then(JSON.parse);
    const first = config.ws[0];
    const prefix = `${base}/weppcloud/runs/${first.runid}/${first.cfg}`;
    await auditPage.request.get(`${base}/weppcloud/runs/${first.runid}/?next=${encodeURIComponent(new URL(prefix+'/browse/combined-viewer-preparation/').pathname)}`);
    for (const relative of ['combined-viewer-preparation/manifest.json','wepp/output/interchange/loss_pw0.hill.parquet']) {
      const response = await auditPage.request.get(prefix+'/download/'+relative);
      expect(response.status()).toBe(200);
      const checksum = createHash('sha256').update(await response.body()).digest('hex');
      expect(checksum).toBe(createHash('sha256').update(fs.readFileSync(path.join('/wc1/runs/po',first.runid,relative))).digest('hex'));
      console.log('Final artifact byte parity:',relative,checksum);
    }
    const samples = JSON.parse(fs.readFileSync(path.join(repo,'docs/work-packages/20261012_portland_combined_viewer/artifacts/evidence/browser-collections.json'),'utf8'));
    for (const sample of samples) {
      const run = JSON.parse(new URL(sample.share).searchParams.get('ws')).find((r) => r.runid === sample.sample.runid);
      const response = await auditPage.request.post(`${base}/query-engine/runs/${run.runid}/${run.cfg}/query`,{data:{datasets:['wepp/output/interchange/loss_pw0.hill.parquet'],columns:['*']}});
      expect(response.status()).toBe(200);
      expect((await response.json()).records.find((r) => r.wepp_id === sample.sample.row.wepp_id)).toEqual(sample.sample.row);
    }
    console.log('Final regenerated native samples match all nine browser-rendered samples');
    console.log('Member landing links, same-origin URLs, mixed denial, aliases, payload rejection, CSRF, map picking, pan/zoom and share verified');
    await context.close();
    return;
  }
  if (['revoked','restored'].includes(process.env.PCV_AUTH_MODE)) {
    const context = await browser.newContext({storageState: path.join(repo,'docker/secrets/pcv-member-session.json')});
    const sameSessionPage = await context.newPage();
    const response = await sameSessionPage.goto(url(catalog.collections[0]));
    expect(response.status()).toBe(process.env.PCV_AUTH_MODE === 'revoked' ? 403 : 200);
    console.log('Same-session role check:',JSON.stringify({mode:process.env.PCV_AUTH_MODE,status:response.status()}));
    await context.close();
    return;
  }
  await login(page);
  const sessionFile = path.join(repo,'docker/secrets/pcv-member-session.json');
  await page.context().storageState({path:sessionFile});
  fs.chmodSync(sessionFile,0o600);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const evidence=[];
  let browseRun;
  const anonymous = await browser.newContext();
  expect((await anonymous.request.get(url(catalog.collections[0]))).status()).toBe(403);
  await anonymous.close();
  for (const item of catalog.collections) {
    console.log('Checking collection:', item.title);
    const response = await page.goto(url(item));
    expect(response.status()).toBe(200);
    await expect(page.locator('#pcv-status')).toContainText('7 watersheds', {timeout:120000});
    await expect(page.locator('#pcv-map canvas')).toBeVisible();
    const ctx = await page.locator('#pcv-config').textContent().then(JSON.parse);
    if (!browseRun) browseRun = ctx.ws[0];
    const firstOption = page.locator('#pcv-feature option').nth(1);
    const firstLabel = await firstOption.textContent();
    const firstId = await firstOption.getAttribute('value');
    const [runid, topaz] = firstLabel.split(' / ');
    const run = ctx.ws.find((r) => r.runid === runid);
    const query = await page.request.post(`${base}/query-engine/runs/${run.runid}/${run.cfg}/query`,
      {data:{datasets:['wepp/output/interchange/loss_pw0.hill.parquet'],columns:['*']}});
    expect(query.ok()).toBeTruthy();
    const row = (await query.json()).records.find((r) => r.wepp_id === run.weppIds[topaz]);
    const cols = {loss:'Soil Loss',runoff:'Runoff Volume',subrunoff:'Subrunoff Volume',baseflow:'Baseflow Volume',phosphorus:'Total Pollutant'};
    for (const variable of Object.keys(cols)) {
      if (variable === 'phosphorus' && await page.locator('#pcv-variable option[value=phosphorus]').isDisabled()) {
        await expect(page.locator('#pcv-availability')).toContainText('unavailable');
        continue;
      }
      console.log('Checking result:', item.title, variable);
      await page.locator('#pcv-variable').selectOption(variable);
      for (const units of ['SI','English']) {
        await page.locator('#pcv-units').selectOption(units);
        await page.locator('#pcv-feature').selectOption(firstId);
        const mass = ['loss','phosphorus'].includes(variable);
        const expected = row[cols[variable]] / (row['Hillslope Area'] * (mass ? 1 : 10)) / (units === 'SI' ? 1 : mass ? 1.12085 : 25.4);
        await expect(page.locator('#pcv-details')).toContainText(expected.toPrecision(6));
      }
    }
    await page.locator('#pcv-variable').selectOption('loss');
    await page.locator('#pcv-range').fill('4000');
    await page.locator('#pcv-controls button').click();
    await page.locator('#pcv-share').click();
    const share=await page.locator('#pcv-share-url').inputValue();
    expect(new URL(share).searchParams.get('title')).toBe(item.title);
    console.log('Verified collection:', item.title);
    evidence.push({title:item.title,status:await page.locator('#pcv-status').textContent(),sample:{runid,topaz,row},share});
    if (evidence.length === 1) {
      await page.screenshot({path:info.outputPath('current-conditions.png'),fullPage:true});
      await page.goto(share);
      await expect(page.locator('#pcv-status')).toContainText('7 watersheds', {timeout:120000});
      await expect(page.locator('#pcv-range')).toHaveValue('4000');
    }
  }
  const sampleRun = browseRun;
  const prefix = `${base}/weppcloud/runs/${sampleRun.runid}/${sampleRun.cfg}`;
  // The normal run-session bridge supplies scoped browse credentials.
  await page.goto(`${base}/weppcloud/runs/${sampleRun.runid}/?next=${encodeURIComponent(new URL(prefix+'/browse/combined-viewer-preparation/').pathname)}`);
  const browse = await page.request.get(prefix+'/browse/combined-viewer-preparation/');
  expect(browse.status()).toBe(200);
  expect(await browse.text()).toContain('manifest.json');
  for (const relative of ['combined-viewer-preparation/manifest.json','wepp/output/interchange/loss_pw0.hill.parquet']) {
    const response = await page.request.get(prefix+'/download/'+relative);
    expect(response.status()).toBe(200);
    const bytes = await response.body();
    const expected = fs.readFileSync(path.join('/wc1/runs/po',sampleRun.runid,relative));
    expect(createHash('sha256').update(bytes).digest('hex')).toBe(createHash('sha256').update(expected).digest('hex'));
    console.log('Browse/download byte parity:',relative);
  }
  await page.goto(base+'/weppcloud/combined_ws_viewer/url_generator/');
  await page.locator('#title').fill('Portland & test # <safe>');
  await page.locator('#runids').fill(catalog.collections[0].ws.map((r)=>r.runid).join(', '));
  await page.locator('#url_gen_form button').click();
  const generated=page.locator('a[href*="combined_ws_viewer/?"]');
  await expect(generated).toBeVisible();
  await generated.click();
  await expect(page.locator('#pcv-status')).toContainText('7 watersheds', {timeout:120000});
  await expect(page.locator('h1')).toHaveText('Portland & test # <safe>');
  expect(errors).toEqual([]);
  await info.attach('collections.json',{body:JSON.stringify(evidence,null,2),contentType:'application/json'});
});
