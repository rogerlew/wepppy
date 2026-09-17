// Actual UI/RQ acceptance after forest restart. No credentials are retained.
const {chromium}=require('../../../../wepppy/weppcloud/static-src/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {createHash}=require('crypto');
const runid=process.argv[2],config=process.argv[3]||'config';
assert(/^[a-zA-Z0-9_-]+$/.test(runid)&&/^[a-zA-Z0-9_-]+$/.test(config));
const base='https://wc.bearhive.duckdns.org',runBase=`${base}/weppcloud/runs/${runid}/${config}`;
const output=path.join(__dirname,'browser',runid);fs.mkdirSync(output,{recursive:true});
const mode=process.argv[4]||'normal';
const records=[];function record(value){records.push({utc:new Date().toISOString(),...value});fs.writeFileSync(path.join(output,'evidence.json'),JSON.stringify(records,null,2));console.log(JSON.stringify(value));}
function hash(data){return createHash('sha256').update(data).digest('hex');}
function expand(seed, length) {
    let state = 2166136261;
    for (const char of seed) {
        state ^= char.codePointAt(0);
        state = (state + (state << 1) + (state << 4) + (state << 7) + (state << 8) + (state << 24)) >>> 0;
    }
    let result = '';
    while (result.length < length) {
        state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
        result += (state >>> 0).toString(16).padStart(8, '0');
    }
    return result.slice(0, length);
}
async function solveCap(page) {
    if (!await page.locator('input[name=cap_token]').count()) return;
    const endpoint = await page.locator('cap-widget').getAttribute('data-cap-api-endpoint');
    const url = new URL(endpoint, page.url());
    assert.equal(url.origin, base);
    const response = await page.request.post(new URL('challenge', url).href);
    assert(response.ok());
    const { token, challenge: { c, s, d } } = await response.json();
    const solutions = [];
    for (let i = 1; i <= c; i++) {
        const salt = expand(token + i, s), target = expand(token + i + 'd', d);
        let nonce = 0;
        while (!hash(salt + nonce).startsWith(target)) nonce++;
        solutions.push(nonce);
    }
    const redeemed = await page.request.post(new URL('redeem', url).href, { data: { token, solutions } });
    const result = await redeemed.json();
    assert(result.success && result.token);
    await page.locator('input[name=cap_token]').evaluate((el, value) => {
        el.value = value; el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }, result.token);
}

(async()=>{
 const credentials=Object.fromEntries(fs.readFileSync(path.resolve(__dirname,'../../../../docker/secrets/dev-agent.env'),'utf8').split('\n').filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1).replace(/^['"]|['"]$/g,'')]}));
 const browser=await chromium.launch({headless:true});
 let page;
 try {
  page=await browser.newPage({viewport:{width:1440,height:1100},acceptDownloads:true});
  page.on('pageerror',e=>record({page_error:e.message}));
  const pendingMutations=new Set();
  page.on('request',r=>{if(['POST','PUT','PATCH','DELETE'].includes(r.method())&&r.url().includes('/runs/'+runid+'/')){pendingMutations.add(r);record({stage:'request',method:r.method(),url:r.url()});}});
  page.on('requestfinished',r=>pendingMutations.delete(r));page.on('requestfailed',r=>pendingMutations.delete(r));
  await page.goto(base+'/weppcloud/login');
  await page.locator('input[name=email]').fill(credentials.DEV_AGENT_EMAIL);await page.locator('input[name=password]').fill(credentials.DEV_AGENT_PASSWORD);
  await solveCap(page);await page.locator('input[type=submit],button[type=submit]').first().click();await page.waitForURL(u=>!u.pathname.endsWith('/login'));
  await page.goto(runBase+'/');
  const form=page.locator('#postfire_debris_flow_form');await form.waitFor({timeout:45000});
  await page.waitForFunction(()=>typeof WCHttp!=='undefined');
  async function state(){return page.evaluate(async u=>(await WCHttp.requestWithSessionToken(u,{method:'GET'})).body.result,`/rq-engine/api/runs/${runid}/${config}/postfire-debris-flow/state`);}

  const before=await state(); record({stage:'before',state:before});
  if(mode==='verify'){
   assert.equal(before.results.current,true);
   const failed=runid==='thespian-cleanness'?'932b890ecffa4f659d438bcf0dad68e5':'0de91c1f867b463d946c40364d3e8051';
   for(const relative of [failed+'/',failed+'/status.json',failed+'/error.log',before.results.id+'/results/']){
    const response=await page.request.get(runBase+'/browse/postfire_debris_flow/attempts/'+relative);
    assert.equal(response.status(),200);const bytes=await response.body();
    record({stage:'retained_record',relative,status:response.status(),bytes:bytes.length,sha256:hash(bytes)});
   }
   record({stage:'PASS',mode,current:before.results.id,retained_failed:failed});return;
  }

  assert.equal(before.model,'M3'); assert.equal(before.run_ready,true);
  for(let waited=0,quiet=0;quiet<3;waited++){assert(waited<90,'Page mutations did not settle');await page.waitForTimeout(1000);quiet=pendingMutations.size?0:quiet+1;}
  record({stage:'page_mutations_settled'});
  const response=page.waitForResponse(r=>r.url().endsWith('/postfire-debris-flow/run')&&r.request().method()==='POST',{timeout:90000});
  await form.locator('[data-pfdf-action=run]').click({timeout:90000});
  const started=await (await response).json(); record({stage:'submitted',response:started}); assert(started.job_id);
  let after,mutated=false;
  if(mode!=='normal'){
   assert(runid.startsWith('qa-active-cli-'));
   const {execFileSync}=require('child_process');
   const result=execFileSync('wctl',['exec','-T','rq-worker','python',
     'docs/work-packages/20260917_postfire_active_cli_identity/artifacts/runtime_mutation.py',runid,started.result.attempt_id,mode],{encoding:'utf8',timeout:60000});
   record({stage:'mutation',result:JSON.parse(result)}); mutated=true;
  }
  for(let i=0;i<180;i++){
   after=await state();
   if(after.run&&after.run.job_id===started.job_id){
    if(['complete','failed','superseded'].includes(after.run.phase))break;
   }
   await page.waitForTimeout(1000);
  }
  record({stage:'completed',state:after});
  const browse=await page.request.get(runBase+'/browse/postfire_debris_flow/attempts/'+started.result.attempt_id+'/');
  assert.equal(browse.status(),200);record({stage:'attempt_browse',status:browse.status()});
  const job=await page.evaluate(async id=>(await WCHttp.requestWithSessionToken('/rq-engine/api/jobinfo/'+id,{method:'GET'})).body,started.job_id);
  fs.writeFileSync(path.join(output,'job-'+mode+'.json'),JSON.stringify(job,null,2));
  if(mode==='negative'){
   assert(mutated); assert(['failed','superseded'].includes(after.run.phase));
   assert.equal(after.results.id,before.results.id);
   const {execFileSync}=require('child_process');
   record({stage:'restored',result:JSON.parse(execFileSync('wctl',['exec','-T','rq-worker','python',
    'docs/work-packages/20260917_postfire_active_cli_identity/artifacts/runtime_mutation.py',runid,after.run.id,'restore'],{encoding:'utf8',timeout:60000}))});
   record({stage:'PASS',mode,previous_accepted:before.results.id});
  }else{
   assert.equal(after.run.phase,'complete');assert.equal(after.results.current,true);
   if(mode==='overlap')assert(mutated);
   const report=await page.goto(runBase+'/report/postfire_debris_flow/');assert.equal(report.status(),200);
   await page.locator('[data-pfr-response-line]').waitFor({timeout:90000});
   const seed=JSON.parse(await page.locator('#postfire-report-seed').textContent());
   assert.equal(seed.summary.current,true);assert.equal(seed.summary.model,'M3');
   fs.writeFileSync(path.join(output,'seed-'+mode+'.json'),JSON.stringify(seed,null,2));
   await page.screenshot({path:path.join(output,'report-'+mode+'.png'),fullPage:true});
   await page.reload(); await page.locator('[data-pfr-response-line]').waitFor();
   const reloaded=JSON.parse(await page.locator('#postfire-report-seed').textContent());
   assert.equal(reloaded.attempt_id,seed.attempt_id);assert.equal(reloaded.summary.current,true);
   for(const [name,url] of Object.entries(seed.urls.artifacts)){
    const r=await page.request.get(new URL(url,base).href);assert.equal(r.status(),200);
    const bytes=await r.body();record({stage:'artifact',name,bytes:bytes.length,sha256:hash(bytes)});
   }
   record({stage:'PASS',mode,attempt_id:seed.attempt_id,job_id:started.job_id});
  }
 }catch(error){if(page)await page.screenshot({path:path.join(output,'failure-'+mode+'.png'),fullPage:true});throw error;}
 finally{fs.writeFileSync(path.join(output,'evidence-'+mode+'.json'),JSON.stringify(records,null,2));await browser.close();}
})().catch(e=>{record({stage:'FAIL',error:e.message});process.exitCode=1;});
