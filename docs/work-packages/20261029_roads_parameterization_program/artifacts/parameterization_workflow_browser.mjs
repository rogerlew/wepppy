import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
const require=createRequire(import.meta.url);
const repo='/home/workdir/wepppy';
const {chromium}=require(path.join(repo,'wepppy/weppcloud/static-src/node_modules/playwright'));
const base='https://forest.tail305ec9.ts.net';
const raw='/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-workflow-v1';
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



const action=process.argv[2] || 'auth-preflight';
const phase=process.argv[3] || '';
const label=phase ? action+'-'+phase : action;
const receiptFile=path.join(raw,label+'.json');
if(fs.existsSync(receiptFile) && action!=='auth-preflight')throw new Error('Receipt already exists: '+action);
const browser=await chromium.launch({headless:true});
const started=new Date().toISOString();
let receipt={action,phase,label,started,origin:base,runid,config};
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await login(page);
 async function openView(){const r=await page.goto(runUrl+'/roads/parameterization');if(r.status()!==200)throw new Error('View status '+r.status());await page.locator('#roads_parameterization').waitFor();}
 async function csrf(){return page.locator('meta[name="csrf-token"]').getAttribute('content');}
 async function postTask(task,data){const r=await page.request.post(runUrl+'/tasks/'+task,{data,headers:{'X-CSRFToken':await csrf(),'Referer':page.url(),'Origin':base}});const payload=await r.json();return {status:r.status(),payload};}
 async function query(){const r=await page.request.get(runUrl+'/query/roads/summary');if(r.status()!==200)throw new Error('Query failed '+r.status());return r.json();}
 async function bearer(){await page.goto(base+'/weppcloud/profile');const r=await page.request.post(base+'/weppcloud/profile/mint-token',{headers:{'X-CSRFToken':await csrf(),'Referer':page.url(),'Origin':base}});if(!r.ok())throw new Error('Token mint failed '+r.status()+' '+await r.text());const p=await r.json();const token=(p.Content||p.content||p.success||{}).token;if(!token)throw new Error('Token missing');return token;}
 async function poll(jobid,token){const states=[];for(let i=0;i<1440;i++){const r=await page.request.get(base+'/rq-engine/api/jobstatus/'+jobid,{headers:{Authorization:'Bearer '+token}});const p=await r.json();if(!r.ok())throw new Error('Job polling '+r.status());if(states.length===0||states.at(-1).status!==p.status){states.push({at:new Date().toISOString(),status:p.status});console.log('job',jobid,p.status);}if(['finished','failed','stopped','canceled','not_found'].includes(p.status)){if(p.status!=='finished')throw new Error('Job terminal '+JSON.stringify(p));return {jobid,states,final:p};}await new Promise(resolve=>setTimeout(resolve,5000));}throw new Error('Job polling timeout');}
 async function nativeTask(task){const token=await bearer();await openView();const submission=await postTask('roads/'+task,{});receipt.submission=submission;const jobid=submission.payload.job_id||submission.payload.Content?.job_id;if(submission.status!==200||!jobid)throw new Error('Enqueue failed '+JSON.stringify(submission));receipt.job=await poll(jobid,token);receipt.query=await query();}
 if(action==='auth-preflight'){
  const response=await page.goto(runUrl+'/query/roads');receipt.status=response.status();receipt.authenticated=true;receipt.payloadKeys=Object.keys(await response.json());if(receipt.status!==200)throw new Error('Protected query failed');
 }else if(action==='prepare'||action==='run'){
  await nativeTask(action==='prepare'?'prepare_segments':'run');
 }else if(action==='ui-default'||action==='ui-custom'||action==='ui-reset'){
  await openView();receipt.before=await query();
  await page.click('[data-rp-action="edit"]');
  if(action==='ui-custom'){
   for(const role of ['road','fill','buffer']){
    for(const field of ['ksat_mm_h','ki_kg_s_m4','kr_s_m','critical_shear_pa']){
     const row=page.locator('[data-rp-row][data-role="'+role+'"][data-field="'+field+'"]');
     await row.locator('[data-rp-mode]').selectOption('multiply');await row.locator('[data-rp-value]').fill('2');
    }
   }
  }else if(action==='ui-reset'){await page.click('[data-rp-action="reset"]');}
  const result=page.waitForResponse(r=>r.url().includes('/tasks/roads/set_params')&&r.request().method()==='POST');
  await page.click('[data-rp-action="save"]');const r=await result;receipt.save={status:r.status(),payload:await r.json()};if(!r.ok()||receipt.save.payload.error)throw new Error('Save failed');
  await page.waitForFunction(()=>document.querySelector('[data-rp-status]').textContent.includes('saved'));
  await page.reload();await page.locator('#roads_parameterization').waitFor();receipt.after=await query();
  receipt.readback=await page.locator('[data-rp-readback]').innerText();receipt.comparison=await page.locator('[data-rp-comparison]').innerText();
  await page.screenshot({path:path.join(raw,label+'-desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(raw,label+'-mobile.png'),fullPage:true});
  receipt.mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
 }else if(action==='invalid'){
  await openView();receipt.before=await query();const overrides=structuredClone(receipt.before.parameterization.overrides);overrides.road.ksat_mm_h={mode:'absolute',value:0};receipt.rejected=await postTask('roads/set_params',{parameterization:{overrides}});receipt.after=await query();if(receipt.before.parameterization.configuration_hash!==receipt.after.parameterization.configuration_hash)throw new Error('Invalid request changed configuration');if(receipt.rejected.status<400&&!receipt.rejected.payload.error&&!receipt.rejected.payload.Error)throw new Error('Invalid request did not return explicit error');
 }else if(action==='cancel'){
  await openView();receipt.before=await query();await page.click('[data-rp-action="edit"]');const row=page.locator('[data-rp-row][data-role="road"][data-field="ki_kg_s_m4"]');await row.locator('[data-rp-mode]').selectOption('multiply');await row.locator('[data-rp-value]').fill('3');await page.click('[data-rp-action="cancel"]');await page.waitForFunction(()=>document.querySelector('[data-rp-status]').textContent.includes('reloaded'));receipt.after=await query();if(receipt.before.parameterization.configuration_hash!==receipt.after.parameterization.configuration_hash)throw new Error('Cancel changed state');
 }else if(action==='inspect'){
  await openView();receipt.query=await query();receipt.readback=await page.locator('[data-rp-readback]').innerText();receipt.comparison=await page.locator('[data-rp-comparison]').innerText();await page.screenshot({path:path.join(raw,label+'-view.png'),fullPage:true});
 }else if(action==='artifacts'){
  await openView();receipt.files=[];
  for(const rel of ['wepp/roads/output/roads.parameterization.comparison.json','wepp/roads/segments/roads.segment.pass.manifest.json','wepp/roads/runs/p900001.sol']){
   const r=await page.request.get(runUrl+'/download/'+rel);const body=await r.body();
   const expected=fs.readFileSync('/wc1/runs/ro/'+runid+'/'+rel);
   if(r.status()!==200||!body.equals(expected))throw new Error('Artifact download mismatch '+rel+' '+r.status());
   receipt.files.push({relpath:rel,status:r.status(),sha256:createHash('sha256').update(body).digest('hex'),bytes:body.length});
  }
  const view=await page.request.get(runUrl+'/browse/wepp/roads/output/');
  receipt.browseStatus=view.status();if(view.status()!==200)throw new Error('Browse failed '+view.status());
 }else if(action==='reports'){
  await openView();receipt.query=await query();receipt.reports=[];
  for(const report of ['summary','results']){
   const r=await page.request.get(runUrl+'/report/roads/'+report);
   const body=(await r.text()).replace(/(<meta[^>]+name="csrf-token"[^>]+content=")[^"]*(")/gi,'$1[redacted]$2');if(r.status()!==200)throw new Error('Report '+report+' status '+r.status());
   fs.writeFileSync(path.join(raw,label+'-'+report+'.html'),body);
   receipt.reports.push({report,status:r.status(),sha256:createHash('sha256').update(body).digest('hex'),bytes:Buffer.byteLength(body)});
  }
 }else if(action==='readonly-on'||action==='readonly-off'){
  const token=await bearer();await openView();const submission=await postTask('set_readonly',{readonly:action==='readonly-on'});receipt.submission=submission;const jobid=submission.payload.Content?.job_id||submission.payload.job_id;if(!jobid)throw new Error('Readonly submission failed');receipt.job=await poll(jobid,token);await openView();receipt.query=await query();receipt.editEnabled=await page.locator('[data-rp-action="edit"]').isEnabled();if(action==='readonly-on'){receipt.denied=await postTask('roads/set_params',{parameterization:{overrides:receipt.query.parameterization.overrides}});if(receipt.denied.status<400)throw new Error('Readonly mutation allowed');}
 }else if(action==='fork-private-auth'){
  const forkUrl=base+'/weppcloud/runs/'+runid+'-fork/'+config;
  await page.goto(forkUrl+'/roads/parameterization');
  const r=await page.request.post(forkUrl+'/tasks/set_public',{data:{public:false},headers:{'X-CSRFToken':await csrf(),Referer:page.url(),Origin:base}});
  receipt.makePrivate={status:r.status(),payload:await r.json()};if(!r.ok()||receipt.makePrivate.payload.error)throw new Error('Private fork setup failed');
  const ownerQuery=await page.request.get(forkUrl+'/query/roads/summary');
  receipt.ownerQueryStatus=ownerQuery.status();receipt.ownerQuery=await ownerQuery.json();
  if(ownerQuery.status()!==200||receipt.ownerQuery.parameterization?.status!=='bound')throw new Error('Authorized private fork query failed');
  const anonymous=await browser.newContext();
  const g=await anonymous.request.get(forkUrl+'/roads/parameterization',{maxRedirects:0});receipt.anonymousGet={status:g.status(),body:(await g.text()).slice(0,500)};
  const anonPage=await anonymous.newPage();await anonPage.goto(base+'/weppcloud/login');
  const anonCsrf=await anonPage.locator('meta[name="csrf-token"]').getAttribute('content');
  const post=await anonymous.request.post(forkUrl+'/tasks/roads/set_params',{data:{parameterization:{overrides:receipt.ownerQuery.parameterization.overrides}},headers:{'X-CSRFToken':anonCsrf,Referer:forkUrl,Origin:base},maxRedirects:0});receipt.anonymousSave={status:post.status(),body:(await post.text()).slice(0,500)};
  if(![401,403,404,302].includes(g.status())||![401,403,404,302].includes(post.status()))throw new Error('Unauthorized fork boundary not denied');
  await anonymous.close();
 }else if(['archive','fork','restore'].includes(action)){
  const token=await bearer();let task=action;let data={};
  if(action==='archive')data={comment:'Roads parameterization workflow'};
  if(action==='fork')data={target_runid:runid+'-fork',undisturbify:false,skip_wepp_runs_output:false};
  if(action==='restore'){task='restore-archive';const prior=JSON.parse(fs.readFileSync(path.join(raw,'archive.json'),'utf8'));data={archive_name:prior.archive_name};}
  const r=await page.request.post(base+'/rq-engine/api/runs/'+runid+'/'+config+'/'+task,{data,headers:{Authorization:'Bearer '+token}});const p=await r.json();receipt.submission={status:r.status(),payload:p};const jobid=p.job_id||p.Content?.job_id;if(!r.ok()||!jobid)throw new Error('Lifecycle submission failed '+JSON.stringify(receipt.submission));receipt.job=await poll(jobid,token);
  if(action==='archive'){await openView();const a=await page.request.get(runUrl+'/rq-archive-dashboard/archives');receipt.archives=await a.json();const list=receipt.archives.Content||receipt.archives.archives||receipt.archives;receipt.archive_name=Array.isArray(list)?list[0]?.name:list.archives?.[0]?.name;if(!receipt.archive_name)throw new Error('Archive listing shape '+JSON.stringify(receipt.archives));}
  receipt.query=await query();
 }else{throw new Error('Unknown action '+action);}
 receipt.errors=errors;receipt.finished=new Date().toISOString();receipt.passed=true;fs.writeFileSync(receiptFile,JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({action,passed:true,errors:errors.length}));
} catch(error){receipt.finished=new Date().toISOString();receipt.passed=false;receipt.error=String(error);fs.writeFileSync(path.join(raw,label+'-failed-'+Date.now()+'.json'),JSON.stringify(receipt,null,2)+'\n');throw error;
} finally {await browser.close();}
