import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const base = process.env.SMOKE_BASE_URL || 'https://wc.bearhive.duckdns.org';
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

test('Builder executable capabilities on forest', async ({ page }) => {
  test.skip(process.env.SMOKE_WEPP_CAPABILITIES !== 'true', 'Creates a disposable CBEXEC project.');
  test.setTimeout(180000);
  await login(page);
  const response = await page.goto(base + '/weppcloud/config-builder/');
  expect(response.status()).toBe(200);
  const binary = page.locator('[name=wepp_binary]');
  await expect(binary).toHaveValue('wepp_260803');
  await binary.selectOption('wepp_261010');
  await page.locator('[name=watershed_representation]').selectOption('multiple-ofe');
  const create = page.locator('[data-builder-create]');
  await expect(create).toBeEnabled();
  await page.locator('[name=single_user_defined_uploads]').check();
  await expect(create).toBeEnabled();
  await expect(binary).toHaveValue('wepp_261010');
  await page.locator('[name=single_user_defined_uploads]').uncheck();
  await expect(create).toBeEnabled();
  const createdPromise = page.waitForResponse((result) => result.url().endsWith('/builder/create'));
  await create.click();
  const created = await createdPromise;
  expect(created.status()).toBe(201);
  await page.waitForURL('**/runs/*/config/**');
  const location = new URL(page.url()).pathname;
  const body = {run_id:location.split('/')[3], location};
  await expect(page.locator('#wepp_bin')).toHaveValue('wepp_261010');
  const options = await page.locator('#wepp_bin option').evaluateAll((nodes) => nodes.filter((node) => !node.disabled).map((node) => node.value));
  expect(options).toEqual(['wepp_260803', 'wepp_261010']);
  const schema = await page.evaluate(async (runid) => {
    const result = await window.WCHttp.requestWithSessionToken('/rq-engine/api/runs/' + runid + '/config/controllers/wepp/schema');
    return result.body;
  }, body.run_id);
  expect(schema.fields.wepp_bin.enum).toEqual(options);
  expect(schema.model_authority.allowed_model_tuples).toContain('topaz|single-ofe|wepp_261010');
  expect(schema.model_authority.allowed_model_tuples).toContain('wbt|multiple-ofe|wepp_261010');
  expect(schema.model_authority.executable_revision).toMatch(/^[a-f0-9]{64}$/);
  const rejected = await page.evaluate(async () => {
    try {
      const result = await window.WCHttp.postJsonWithSessionToken(window.url_for_run('prep-wepp-watershed', {prefix:'/rq-engine/api'}), {wepp_bin:'/tmp/not-a-release', kslast:99});
      return {status:result.status, body:result.body};
    } catch (error) { return {status:error.status, body:error.body}; }
  });
  expect(rejected.status).toBe(400);
  expect(rejected.body.error.code).toBe('unsupported_capability');
  await page.reload();
  await expect(page.locator('#wepp_bin')).toHaveValue('wepp_261010');
  const artifact = {runid:body.run_id, location:body.location, builder_created_binary:'wepp_261010',
    upload_validation:true, options, schema, hostile_status:rejected.status,
    scope:'Real authenticated Builder validation/create, run-page options, live schema, hostile API rejection and reload. Native execution is verified separately.'};
  fs.writeFileSync(path.join(repo, 'docs/work-packages/20261012_wepp_executable_capabilities/artifacts/browser-validation.json'), JSON.stringify(artifact, null, 2) + '\n');
});

test('selected WEPP artifacts download through authenticated project routes', async ({ page }) => {
  test.skip(process.env.SMOKE_WEPP_CAPABILITIES_READBACK !== 'true', 'Requires the completed bounded RQ execution receipt.');
  const receiptPath = path.join(repo, 'docs/work-packages/20261012_wepp_executable_capabilities/artifacts/selected-execution-validation.json');
  const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
  await login(page);
  const runPath = '/weppcloud/runs/' + receipt.runid + '/config/';
  const pageResponse = await page.goto(base + runPath);
  expect(pageResponse.status()).toBe(200);
  await expect(page.locator('#wepp_bin')).toHaveValue('wepp_261010');
  const downloads = [];
  for (const [relative, expectedHash] of [
    ['wepp/runs/p1.sol', receipt.prepared_sha256],
    ['wepp/output/H1.loss.dat', receipt.output_sha256]
  ]) {
    const response = await page.request.get(base + runPath + 'download/' + relative);
    expect(response.status()).toBe(200);
    const digest = createHash('sha256').update(await response.body()).digest('hex');
    expect(digest).toBe(expectedHash);
    downloads.push({path:relative, status:response.status(), sha256:digest});
  }
  const stderr = await page.request.get(base + runPath + 'download/wepp/runs/p1.err');
  expect(stderr.status()).toBe(200);
  expect(await stderr.text()).toContain(receipt.hillslope_binary_sha256);
  fs.writeFileSync(path.join(repo, 'docs/work-packages/20261012_wepp_executable_capabilities/artifacts/browser-artifact-readback.json'), JSON.stringify({runid:receipt.runid, downloads, runner_identity_download:true}, null, 2) + '\n');
});

test('selected release and generated artifacts survive canonical archive restore', async ({ page }) => {
  test.skip(process.env.SMOKE_WEPP_CAPABILITIES_ARCHIVE !== 'true', 'Archives/restores only the disposable CBEXEC project.');
  test.setTimeout(180000);
  const evidence = path.join(repo, 'docs/work-packages/20261012_wepp_executable_capabilities/artifacts');
  const receipt = JSON.parse(fs.readFileSync(path.join(evidence, 'selected-execution-validation.json'), 'utf8'));
  expect(receipt.runid).toBe('sabbatical-stitcher');
  await login(page);
  const runPath = '/weppcloud/runs/' + receipt.runid + '/config/';
  await page.goto(base + runPath);
  const submit = async (operation, data) => page.evaluate(async ({operation, data}) => {
    try {
      return (await window.WCHttp.postJsonWithSessionToken(window.url_for_run(operation, {prefix:'/rq-engine/api'}), data)).body;
    } catch (error) { throw new Error(JSON.stringify({status:error.status, body:error.body})); }
  }, {operation, data});
  const waitJob = async (jobId) => expect.poll(() => page.evaluate(async (id) => {
    return (await window.WCHttp.requestWithSessionToken('/rq-engine/api/jobstatus/' + id)).body.status;
  }, jobId), {timeout:60000}).toBe('finished');
  const archive = await submit('archive', {comment:'CBEXEC capability acceptance'});
  await waitJob(archive.job_id);
  const names = fs.readdirSync(path.join(receipt.wd, 'archives')).filter((name) => name.endsWith('.zip')).sort();
  const name = names[names.length - 1];
  expect(name).toBeTruthy();
  const downloaded = await page.request.get(base + runPath + 'download/archives/' + name);
  expect(downloaded.status()).toBe(200);
  const archiveHash = createHash('sha256').update(await downloaded.body()).digest('hex');
  expect(archiveHash).toBe(createHash('sha256').update(fs.readFileSync(path.join(receipt.wd, 'archives', name))).digest('hex'));
  const restore = await submit('restore-archive', {archive_name:name});
  await waitJob(restore.job_id);
  await page.reload();
  await expect(page.locator('#wepp_bin')).toHaveValue('wepp_261010');
  const files = {...receipt.config_hashes_unchanged, 'wepp/runs/p1.sol':receipt.prepared_sha256, 'wepp/output/H1.loss.dat':receipt.output_sha256};
  for (const [relative, digest] of Object.entries(files)) {
    const response = await page.request.get(base + runPath + 'download/' + relative);
    expect(response.status()).toBe(200);
    expect(createHash('sha256').update(await response.body()).digest('hex')).toBe(digest);
  }
  fs.writeFileSync(path.join(evidence, 'archive-restore-validation.json'), JSON.stringify({runid:receipt.runid, archive_job:archive.job_id,
    restore_job:restore.job_id, archive_name:name, archive_sha256:archiveHash, selected_binary:'wepp_261010',
    restored_download_hashes:files}, null, 2) + '\n');
});
