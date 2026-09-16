// Actual UI/RQ acceptance after forest restart. No credentials are retained.
const {chromium}=require('../../../../wepppy/weppcloud/static-src/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {createHash}=require('crypto');
const runid=process.argv[2],config=process.argv[3]||'config';
assert(/^[a-zA-Z0-9_-]+$/.test(runid)&&/^[a-zA-Z0-9_-]+$/.test(config));
const base='https://wc.bearhive.duckdns.org',runBase=`${base}/weppcloud/runs/${runid}/${config}`;
const output=path.join(__dirname,'browser',runid);fs.mkdirSync(output,{recursive:true});
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
  await page.goto(base+'/weppcloud/login');
  await page.locator('input[name=email]').fill(credentials.DEV_AGENT_EMAIL);await page.locator('input[name=password]').fill(credentials.DEV_AGENT_PASSWORD);
  await solveCap(page);await page.locator('input[type=submit],button[type=submit]').first().click();await page.waitForURL(u=>!u.pathname.endsWith('/login'));
  await page.goto(runBase+'/');
  const form=page.locator('#postfire_debris_flow_form');await form.waitFor({timeout:45000});
  await page.waitForFunction(()=>typeof WCHttp!=='undefined');
  async function state(){return page.evaluate(async u=>(await WCHttp.requestWithSessionToken(u,{method:'GET'})).body.result,`/rq-engine/api/runs/${runid}/${config}/postfire-debris-flow/state`);}
  const before=await state();record({stage:'before',state:before});
  if(runid.startsWith('pfdf-kf-')&&!before.dnbr){
   const meta=JSON.parse(fs.readFileSync(path.join(__dirname,'fixture.json')));assert.equal(meta.runid,runid);
   assert(!fs.existsSync(path.join(meta.wd,'rusle')));assert(!fs.existsSync(path.join(meta.wd,'polaris')));
   await form.locator('input[name=file]').setInputFiles(meta.upload);
   await form.locator('[data-pfdf-action=upload]').click({timeout:45000});
   await page.waitForFunction(()=>document.querySelector('[data-pfdf-summary]').textContent.includes('smoke-dnbr.tif'),null,{timeout:150000});
   record({stage:'uploaded',state:await state(),rusle_absent:!fs.existsSync(path.join(meta.wd,'rusle'))});
  }
  let started;
  if(process.argv[4]==='resume'){
   started={job_id:before.run.job_id};record({stage:'resume_existing_ui_submission',response:started});
  }else{
   const runResponse=page.waitForResponse(r=>r.url().endsWith('/postfire-debris-flow/run')&&r.request().method()==='POST',{timeout:90000});
   await form.locator('[data-pfdf-action=run]').click({timeout:90000});
   started=await (await runResponse).json();record({stage:'submitted',response:started});assert(started.job_id);
  }
  let after;
  for(let i=0;i<180;i++){
   after=await state();if(after.run&&after.run.job_id===started.job_id&&['complete','failed','superseded'].includes(after.run.phase))break;
   await page.waitForTimeout(2000);
  }
  record({stage:'completed',state:after});assert.equal(after.run.phase,'complete');assert.equal(after.results.current,true);
  const job=await page.evaluate(async id=>(await WCHttp.requestWithSessionToken('/rq-engine/api/jobinfo/'+id,{method:'GET'})).body,started.job_id);
  fs.writeFileSync(path.join(output,'job.json'),JSON.stringify(job,null,2));
  await form.screenshot({path:path.join(output,'control.png')});
  const response=await page.goto(runBase+'/report/postfire_debris_flow/');assert.equal(response.status(),200);
  await page.locator('[data-pfr-response-line]').waitFor({timeout:90000});
  let seed=JSON.parse(await page.locator('#postfire-report-seed').textContent());
  fs.writeFileSync(path.join(output,'seed.json'),JSON.stringify(seed,null,2));
  assert.equal(seed.summary.current,true);assert.match(seed.summary.soil_source,/Kf/);assert(seed.response_curve.points.length>=101);
  const accepted=seed.attempt_id;
  assert.match(await page.locator('[data-pfr-climate]').innerText(),/modeled\/disaggregated/);
  await page.evaluate(()=>{const c=UnitizerClient.getClientSync();c.setGlobalPreference(0);c.dispatchPreferenceChange();});
  for(const duration of ['15','30','60']){
   if(duration!=='15'){
    const query=page.waitForResponse(r=>r.url().includes('/query/postfire_debris_flow/')&&r.request().method()==='GET');
    await page.locator('[data-pfr-field=duration]').selectOption(duration);
    const q=await (await query).json();assert.equal(q.attempt_id,accepted);assert.equal(q.query.duration_minutes,Number(duration));
    fs.writeFileSync(path.join(output,'duration-'+duration+'.json'),JSON.stringify(q,null,2));
   }
   await page.waitForFunction(d=>document.querySelector('[data-pfr-chart]').textContent.includes(d+'-minute'),duration);
   await page.locator('[data-pfr-curve-details]').evaluate(e=>e.open=true);
   assert(await page.locator('[data-pfr-body=curve] tr').count()>=102);
   const csv=await page.evaluate(()=>PostfireReport.getInstance().csv('curve'));
   assert(csv.includes('subdaily_origin')&&csv.includes('NRCS-derived STATSGO'));
   fs.writeFileSync(path.join(output,'curve-'+duration+'.csv'),csv);
  }
  await page.locator('[data-pfr-curve-details]').evaluate(e=>e.open=false);
  await page.screenshot({path:path.join(output,'report-si.png'),fullPage:true});
  await page.evaluate(()=>{const c=UnitizerClient.getClientSync();c.setGlobalPreference(1);c.dispatchPreferenceChange();});
  fs.writeFileSync(path.join(output,'curve-english.csv'),await page.evaluate(()=>PostfireReport.getInstance().csv('curve')));
  await page.screenshot({path:path.join(output,'report-english.png'),fullPage:true});
  await page.locator('[data-pfr-p50]').focus();assert.equal(await page.locator('[data-pfr-p50]').evaluate(e=>e===document.activeElement),true);
  await page.locator('circle[data-pfr-scenario]').first().focus();await page.keyboard.press('Enter');assert.equal(await page.locator('circle[data-pfr-scenario]').first().getAttribute('aria-pressed'),'true');
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'report-mobile.png'),fullPage:true});
  await page.locator('[data-pfr-curve-details]').evaluate(e=>e.open=true);
  const dl=page.waitForEvent('download');await page.locator('[data-pfr-export=curve]').click();const download=await dl;await download.saveAs(path.join(output,'downloaded-curve.csv'));
  for(const [name,url] of Object.entries(seed.urls.artifacts)){
   const r=await page.request.get(new URL(url,base).href);assert.equal(r.status(),200);const bytes=await r.body();
   record({stage:'artifact',name,sha256:hash(bytes),bytes:bytes.length});
  }
  const sourceList=await page.request.get(runBase+'/browse/postfire_debris_flow/attempts/'+accepted+'/kf/');
  assert.equal(sourceList.status(),200);assert.match(await sourceList.text(),/native_kf.tif/);
  record({stage:'source_browse',status:sourceList.status()});
  await page.reload();await page.locator('[data-pfr-response-line]').waitFor();seed=JSON.parse(await page.locator('#postfire-report-seed').textContent());assert.equal(seed.attempt_id,accepted);
  record({stage:'report_verified',attempt_id:accepted,soil_source:seed.summary.soil_source,curve_points:seed.response_curve.points.length});
  if(runid.startsWith('pfdf-kf-')){
   await page.goto(runBase+'/');await form.waitFor();
   await page.evaluate(async()=>{await Project.getInstance().set_mod('rusle',true,{notify:false});await Project.getInstance().set_mod('rusle',false,{notify:false});});
   for(let n=0;n<3;n++){
    if(n)await page.reload();await form.waitFor({state:'visible',timeout:45000});
    assert(await page.locator('[data-project-mod=postfire_debris_flow]').isChecked());
    const current=await state();assert.equal(current.results.current,true);
    record({stage:'rusle_removal',reload:n,postfire_visible:true,current:true});
   }
  }
  record({stage:'PASS',attempt_id:accepted});
 }catch(error){if(page){await page.screenshot({path:path.join(output,'failure.png'),fullPage:true});record({stage:'failure_page',url:page.url(),text:(await page.locator('body').innerText()).slice(-12000)});}throw error;}finally{await browser.close();}
})().catch(e=>{record({stage:'FAIL',error:e.message});process.exitCode=1;});
