const { chromium } = require(process.cwd() + '/wepppy/weppcloud/static-src/node_modules/@playwright/test');
const fs = require('fs');
const { createHash } = require('crypto');
const forwardedProtoHeader = {};
const host = 'https://wc.bearhive.duckdns.org';
const runUrl = host + '/weppcloud/runs/chemotherapeutic-scope/disturbed9002_wbt/';
const out = 'docs/work-packages/20261008_prism_wepp_integration/artifacts/';
function fnv32aHash(text) {
  let value = 2166136261;
  for (const char of text) {
    value ^= char.codePointAt(0);
    value = (value + (value << 1) + (value << 4) + (value << 7) + (value << 8) + (value << 24)) >>> 0;
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
  const token = String(challengePayload && challengePayload.token ? challengePayload.token : '').trim();
  const challenge = challengePayload && challengePayload.challenge;
  if (!token || !challenge || typeof challenge !== 'object') {
    throw new Error(`Unexpected CAP challenge payload: ${JSON.stringify(challengePayload).slice(0, 240)}`);
  }

  const count = Number(challenge.c || 0);
  const saltLength = Number(challenge.s || 0);
  const targetLength = Number(challenge.d || 0);
  if (!Number.isInteger(count) || !Number.isInteger(saltLength) || !Number.isInteger(targetLength)
      || count <= 0 || saltLength <= 0 || targetLength <= 0) {
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

  const challengeResponse = await page.request.post(challengeUrl, { headers: forwardedProtoHeader });
  if (!challengeResponse.ok()) {
    throw new Error(`CAP challenge failed: ${challengeResponse.status()} ${challengeResponse.statusText()}`);
  }
  const challengePayload = await challengeResponse.json();
  const { token, pairs } = buildCapPairs(challengePayload);
  const solutions = pairs.map(([salt, targetHex]) => solvePowNonce(salt, targetHex));

  const redeemResponse = await page.request.post(redeemUrl, {
    headers: forwardedProtoHeader,
    data: { token, solutions },
  });
  if (!redeemResponse.ok()) {
    throw new Error(`CAP redeem failed: ${redeemResponse.status()} ${redeemResponse.statusText()}`);
  }
  const redeemPayload = await redeemResponse.json();
  const capToken = String(redeemPayload && redeemPayload.token ? redeemPayload.token : '').trim();
  if (!capToken || !redeemPayload.success) {
    throw new Error(`CAP redeem did not return a success token: ${JSON.stringify(redeemPayload).slice(0, 240)}`);
  }
  return capToken;
}


(async () => {
 const creds = Object.fromEntries(fs.readFileSync('docker/secrets/dev-agent.env','utf8').split('\n').filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{let i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1).trim().replace(/^['"]|['"]$/g,'')]}));
 const browser = await chromium.launch({headless:true});
 try {
 const page = await browser.newPage({viewport:{width:1440,height:1000}});
 await page.goto(host+'/weppcloud/login', {waitUntil:'domcontentloaded'});
 const form = page.locator('form').filter({has:page.locator('input[name="password"]')});
 await form.locator('input[name="email"]').fill(creds.DEV_AGENT_EMAIL);
 await form.locator('input[name="password"]').fill(creds.DEV_AGENT_PASSWORD);
 if (await form.locator('input[name="cap_token"]').count()) {
  const endpoint = await form.locator('cap-widget').getAttribute('data-cap-api-endpoint');
  const token = await solveCapTokenFromEndpoint(page,endpoint);
  await form.locator('input[name="cap_token"]').evaluate((el,t)=>{el.value=t;},token);
 }
 await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),form.locator('[type="submit"]').first().click()]);
 await page.goto(runUrl,{waitUntil:'domcontentloaded',timeout:60000});
 await page.waitForFunction(()=>window.Climate && Climate.getInstance().datasetMap.observed_prism_800m,{timeout:60000});
 const phase = process.argv[2] || 'inspect';
 const mode = Number(process.argv[3] || 1);
 const result = {phase,mode,url:runUrl,at:new Date().toISOString()};
 if (phase==='climate') {
  const already = await page.locator('#climate_dataset_observed_prism_800m').isChecked();
  const change=already ? Promise.resolve() : page.waitForResponse(r=>r.url().includes('tasks/set_climate_mode/')&&r.request().method()==='POST');
  await page.locator('#climate_dataset_observed_prism_800m').check({force:true});
  // If already selected, no change request is sent; controller selection is already persisted.
  await change.catch(()=>null);
  console.log('PRISM selected');
  await page.locator('#observed_start_year').fill('2019');
  await page.locator('#observed_end_year').fill('2021');
  const advanced = page.locator('details').filter({has:page.locator('#cligen_seed')});
  for (let i=0;i<await advanced.count();i++) {
   const detail=advanced.nth(i);
   if (!(await detail.evaluate(el=>el.open))) await detail.locator(':scope > summary').click();
  }
  await page.locator('#cligen_seed').fill('84568');
  console.log('Years and seed entered');
  await page.locator('#climate_spatialmode'+mode).check({force:true});
  await page.waitForTimeout(1000);
  result.label=await page.locator('#climate_spatialmode2').locator('..').innerText();
  const response=page.waitForResponse(r=>r.url().endsWith('/build-climate')&&r.request().method()==='POST');
  await page.locator('#btn_build_climate').click({force:true});
  const r=await response;result.http=r.status();result.payload=await r.json();
  if(!result.payload.job_id)throw new Error(JSON.stringify(result));
 } else if (phase==='wepp') {
  const response=page.waitForResponse(r=>r.url().endsWith('/run-wepp')&&r.request().method()==='POST');
  await page.evaluate(()=>Wepp.getInstance().run());
  const r=await response;result.http=r.status();result.payload=await r.json();
  if(!result.payload.job_id)throw new Error(JSON.stringify(result));
 } else if (phase==='evidence') {
  result.selection=await page.locator('#climate_catalog_id').inputValue();
  result.spatialMode=await page.locator('input[name="climate_spatialmode"]:checked').inputValue();
  result.label=await page.locator('#climate_spatialmode2').locator('..').innerText();
  if(result.selection!=='observed_prism_800m'||Number(result.spatialMode)!==mode)throw new Error('Persisted menu mismatch');
  const root='/wc1/runs/ch/chemotherapeutic-scope/';
  const proof=JSON.parse(fs.readFileSync(root+'climate/provenance.json','utf8'));
  const source=proof.sources[0].source_directory;
  const listing=await page.request.get(runUrl+'browse/'+source+'/');
  result.browseStatus=listing.status();
  if(!listing.ok()||!(await listing.text()).includes('bulk.csv.gz'))throw new Error('Source browser listing failed');
  const file=source+'/bulk.csv.gz';
  const downloaded=await page.request.get(runUrl+'download/'+file);
  const bytes=await downloaded.body();
  result.downloadStatus=downloaded.status();
  result.source=file;
  result.sha256=createHash('sha256').update(bytes).digest('hex');
  if(!downloaded.ok()||!bytes.equals(fs.readFileSync(root+file)))throw new Error('Downloaded source bytes mismatch');
 } else {
  result.catalog=await page.locator('#climate_catalog_data').textContent().then(JSON.parse);
  result.selection=await page.locator('#climate_catalog_id').inputValue();
 }
 await page.locator('#climate_form').screenshot({path:out+'forest-'+phase+'-'+mode+'.png'});
 fs.writeFileSync(out+'forest-'+phase+'-'+mode+'.json',JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify({phase,mode,http:result.http,job:result.payload?.job_id,selection:result.selection}));
 } finally {await browser.close();}
})().catch(e=>{console.error(e.message);process.exit(1);});
