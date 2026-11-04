import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
const require=createRequire(import.meta.url);
const repo='/home/workdir/wepppy';
const {chromium}=require(path.join(repo,'wepppy/weppcloud/static-src/node_modules/playwright'));
const base='https://forest.tail305ec9.ts.net';
const phase=process.argv[2] || 'v1';
if(!/^[a-z0-9-]+$/.test(phase))throw new Error('Invalid evidence phase');
const raw='/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-implementation-ux-'+phase;
const runid='roads-param-ui-20261103-v1';
const config='disturbed9002-wbt-mofe';
const runUrl=base+'/weppcloud/runs/'+runid+'/'+config;
// CAP/login helper copied from existing canonical smoke capability test; tokens
// stay in memory and are deliberately omitted from retained receipts.
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



if(fs.existsSync(path.join(raw,'readback.json')))throw new Error('Evidence phase already completed');
fs.mkdirSync(raw,{recursive:true});
const browser=await chromium.launch({headless:true});
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await login(page);
 const response=await page.goto(runUrl+'/roads/parameterization');
 if(response.status()!==200)throw new Error('view status '+response.status());
 await page.locator('[data-rp-state]').waitFor();
 await page.waitForFunction(()=>window.RoadsParameterization && document.querySelector('[data-rp-state]').textContent.length>0);
 const receipt={origin:base,runid,config,at:new Date().toISOString(),response:response.status()};
 const scriptUrl=await page.locator('script[src*="controllers-gl.js"]').getAttribute('src');const scriptResponse=await page.request.get(new URL(scriptUrl,page.url()).href);receipt.loadedBundleSha256=createHash('sha256').update(await scriptResponse.body()).digest('hex');
 const r=await page.request.get(runUrl+'/query/roads/summary'); receipt.queryStatus=r.status();
 const q=await r.json();fs.writeFileSync(path.join(raw,'query.json'),JSON.stringify(q,null,2));
 receipt.state=await page.locator('[data-rp-state]').innerText();
 receipt.groupOptions=await page.locator('[data-rp-group] option').allTextContents();
 if(q.parameterization?.status==='bound'){const expectedDefault=Object.values(q.parameterization.overrides).every(role=>Object.values(role).every(entry=>entry.mode==='default'));receipt.defaultLabelMatches=receipt.state.includes(expectedDefault?'Default inputs':'Custom overrides');}
 receipt.rowCount=await page.locator('[data-rp-row]').count();
 receipt.readback=await page.locator('[data-rp-readback]').innerText();
 receipt.comparison=await page.locator('[data-rp-comparison]').innerText();
 const complete=q.parameterization?.last_completed_run;
 if(complete?.records?.length){
  const keys=['ksat_mm_h','ki_kg_s_m4','kr_s_m','critical_shear_pa'];
  const expected=complete.records.flatMap(r=>(r.ofes||[]).flatMap(o=>keys.map(k=>Number(o.emitted[k].toPrecision(7)).toString())));
  const rendered=await page.locator('[data-rp-readback] dd').allTextContents();
  receipt.readbackValuesMatch=JSON.stringify(expected)===JSON.stringify(rendered);
  receipt.readbackValueCount=rendered.length;
  await page.locator('[data-rp-readback] details').first().evaluate(e=>{e.open=true});
  receipt.firstProfile=await page.locator('[data-rp-readback] details').first().innerText();
 }
 const comparison=q.parameterization?.comparisons;
 if(comparison?.status==='available'){
  const keys=['annual_runoff_m3','annual_sediment_kg','annual_runoff_mm','annual_sediment_kg_m2'];
  const expected=keys.flatMap(k=>[comparison.baseline.metrics[k],comparison.custom.metrics[k],comparison.difference[k]].map(v=>Number(v.toPrecision(7)).toString()));
  const rendered=await page.locator('[data-rp-comparison] tbody td').allTextContents();
  receipt.comparisonValuesMatch=JSON.stringify(expected)===JSON.stringify(rendered);
  receipt.comparisonMetricCount=rendered.length;
 }

 for(const width of [1440,390]){await page.setViewportSize({width,height:900});await page.screenshot({path:path.join(raw,'view-'+width+'.png'),fullPage:true});receipt[width]=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,overflow:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth).sort((a,b)=>b.getBoundingClientRect().right-a.getBoundingClientRect().right).slice(0,30).map(e=>({tag:e.tagName,id:e.id,cls:e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right,overflow:getComputedStyle(e).overflowX}))}));}
 if(await page.locator('[data-rp-action="edit"]').isEnabled()){
  await page.locator('[data-rp-action="edit"]').click();
  const row=page.locator('[data-rp-row][data-role="road"][data-field="ksat_mm_h"]');
  await row.locator('[data-rp-mode]').selectOption('absolute');
  await row.locator('[data-rp-value]').fill('');
  receipt.empty={value:await row.locator('[data-rp-value]').inputValue(),saveEnabled:await page.locator('[data-rp-action="save"]').isEnabled()};
  await row.locator('[data-rp-value]').pressSequentially('0.125');
  receipt.typing={value:await row.locator('[data-rp-value]').inputValue(),resolved:await row.locator('[data-rp-resolved]').innerText()};
  const before=await page.locator('[data-rp-row][data-role="road"][data-field="ksat_mm_h"] [data-rp-value]').inputValue();
  await page.evaluate(q=>window.RoadsParameterization.refresh(q),q);
  receipt.passiveDraftPreserved=(await row.locator('[data-rp-value]').inputValue())===before;
  await page.locator('[data-rp-navigate]').click();receipt.dirtyDialog=await page.locator('[data-rp-leave]').isVisible();await page.locator('[data-rp-leave-action="stay"]').click();
  await page.locator('[data-rp-action="cancel"]').click();await page.waitForFunction(()=>document.querySelector('[data-rp-status]').textContent.includes('reloaded'));
  receipt.cancelStatus=await page.locator('[data-rp-status]').innerText();
 }
 receipt.errors=errors;fs.writeFileSync(path.join(raw,'readback.json'),JSON.stringify(receipt,null,2));console.log(JSON.stringify({response:receipt.response,rowCount:receipt.rowCount,desktop:receipt[1440],mobile:receipt[390],errors,empty:receipt.empty,typing:receipt.typing,passiveDraftPreserved:receipt.passiveDraftPreserved,dirtyDialog:receipt.dirtyDialog},null,2));
 if(receipt.defaultLabelMatches===false)throw new Error('Default/custom label disagrees with saved entries; receipt retained');
 if(receipt.readbackValuesMatch===false || receipt.comparisonValuesMatch===false)throw new Error('Displayed run values differ from authoritative query; receipt retained');
 if(errors.length || receipt[1440].width!==receipt[1440].scrollWidth || receipt[390].width!==receipt[390].scrollWidth)throw new Error('Rendered page has JS errors or horizontal overflow; receipt retained');
 if(receipt.empty && (receipt.empty.value!=='' || receipt.empty.saveEnabled || receipt.typing.value!=='0.125' || !receipt.passiveDraftPreserved || !receipt.dirtyDialog))throw new Error('Draft ownership/numeric editing failed; receipt retained');
}finally{await browser.close();}
