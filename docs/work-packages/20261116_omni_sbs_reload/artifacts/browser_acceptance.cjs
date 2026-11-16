const {chromium}=require('/home/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/playwright');
const fs=require('fs'), path=require('path');
const {createHash}=require('crypto');
const repo='/home/workdir/wepppy', base='https://forest.tail305ec9.ts.net';
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


(async()=>{const browser=await chromium.launch();try {
  const page=await browser.newPage({viewport:{width:1280,height:1000}});
  await login(page);
  const run='/weppcloud/runs/qa-omni-reload-20261116/config/';
  await page.goto(base+run,{waitUntil:'domcontentloaded'});
  await page.locator('#omni_form').waitFor({state:'attached'});
  await page.evaluate(()=>Omni.getInstance().load_scenarios_from_backend());
  const before=await page.evaluate(()=>({
    scenarios:Omni.getInstance().serializeScenarios().scenarios,
    filename:document.querySelector('#omni_form .wc-text-display code').textContent,
    selectedFiles:document.querySelector('#omni_form input[type=file]').files.length
  }));
  if(before.filename!=='qa_omni_reload.tif'||before.selectedFiles!==0||!before.scenarios[0].sbs_file_path) throw Error('saved UI state incorrect');
  await page.locator('#omni_form').evaluate(form=>{for(let n=form;n;n=n.parentElement){if(n.tagName==='DETAILS')n.open=true;}});
  const responsePromise=page.waitForResponse(r=>r.url().includes('/run-omni')&&r.request().method()==='POST',{timeout:60000});
  await page.locator('#btn_run_omni').click();
  const response=await responsePromise;
  const body=await response.json();
  if(response.status()!==202) throw Error('Submission failed: '+response.status()+' '+JSON.stringify(body));
  await page.reload({waitUntil:'domcontentloaded'});
  await page.locator('#omni_form .wc-text-display code').waitFor({state:'attached'});
  const after=await page.evaluate(()=>({scenarios:Omni.getInstance().serializeScenarios().scenarios,filename:document.querySelector('#omni_form .wc-text-display code').textContent}));
  if(after.filename!==before.filename)throw Error('reload lost current filename');
  const output=repo+'/docs/work-packages/20261116_omni_sbs_reload/artifacts/';
  fs.writeFileSync(output+'browser_acceptance.json',JSON.stringify({url:base+run,before,after,status:response.status(),job_id:body.job_id},null,2)+'\n');
  await page.locator('#omni_form').evaluate(form=>{for(let n=form;n;n=n.parentElement){if(n.tagName==='DETAILS')n.open=true;}});
  await page.locator('#omni_form').screenshot({path:output+'browser_saved_map.png'});
  console.log('BROWSER_PASS',response.status(),body.job_id);
} finally {await browser.close();}})().catch(e=>{console.error(e.message);process.exit(1)});
