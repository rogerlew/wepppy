const {chromium}=require('/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/playwright');
const fs=require('fs');
const assert=require('assert/strict');
const {execFileSync}=require('child_process');
const artifact='/workdir/wepppy/docs/work-packages/20260910_staley_m1_production/artifacts/';
const secrets=Object.fromEntries(fs.readFileSync('/workdir/wepppy/docker/secrets/dev-agent.env','utf8').split('\n').filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{let i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1).replace(/^['"]|['"]$/g,'')]}));
const meta=JSON.parse(fs.readFileSync(artifact+'local_smoke_project.json'));
assert(meta.runid.startsWith('pfdf-smoke-'));
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1280,height:1800}});
  page.on('pageerror',e=>console.log('PAGEERROR',e.message));
  const stateUrl='/rq-engine/api/runs/'+meta.runid+'/'+meta.config+'/postfire-debris-flow/state';
  async function waitAttempt(kind,job,phase){
   const end=Date.now()+90000;
   while(Date.now()<end){
    const s=await page.evaluate(async url=>(await WCHttp.requestWithSessionToken(url,{method:'GET',cache:'no-store'})).body.result,stateUrl);
    if(s[kind]&&s[kind].job_id===job&&s[kind].phase===phase){console.log('ATTEMPT',kind,job,phase);return s;}
    await page.waitForTimeout(1000);
   }
   throw new Error('Timed out waiting for '+kind+' '+job+' '+phase);
  }
  async function submit(action,endpoint){
   const pending=page.waitForResponse(r=>r.url().endsWith('/'+endpoint)&&r.request().method()==='POST');
   await page.locator('[data-pfdf-action='+action+']').click({timeout:15000});
   const response=await pending;const body=await response.json();
   assert.equal(response.status(),200,JSON.stringify(body));assert(body.job_id);
   console.log('SUBMITTED',action,body.job_id,body.result.attempt_id);return body.job_id;
  }
  await page.goto('https://wc.bearhive.duckdns.org/weppcloud/login');
  await page.locator('input[name=email]').fill(secrets.DEV_AGENT_EMAIL);await page.locator('input[name=password]').fill(secrets.DEV_AGENT_PASSWORD);
  await page.locator('input[type=submit],button[type=submit]').first().click();await page.waitForTimeout(1000);
  await page.goto(`https://wc.bearhive.duckdns.org/weppcloud/runs/${meta.runid}/${meta.config}/`);
  await page.locator('[data-pfdf-required] table').waitFor({timeout:30000});
  await page.locator('#postfire_debris_flow_form input[name=file]').setInputFiles(meta.upload);
  const upload=await submit('upload','upload-dnbr');await waitAttempt('upload',upload,'complete');
  console.log('UPLOAD_COMPLETE',upload);
  await page.waitForFunction(()=>document.querySelector('[data-pfdf-summary]').textContent.includes('smoke-dnbr.tif'),{},{timeout:15000});
  assert.match(await page.locator('[data-pfdf-summary]').innerText(),/smoke-dnbr.tif/);
  assert(await page.locator('[name=frequency_source][value=noaa]').isDisabled());
  const run=await submit('run','run-m1');await waitAttempt('run',run,'complete');
  const state=await page.evaluate(async url=>(await WCHttp.requestWithSessionToken(url,{method:'GET'})).body.result,stateUrl);
  console.log('COMPLETION_STATE',JSON.stringify(state));
  assert.equal(state.results.id,state.run.id);assert.equal(state.dnbr.id,state.upload.id);
  assert(state.results.current);assert(state.results.area_warning);
  await page.waitForFunction(()=>document.querySelector('[data-pfdf-warning]').textContent.includes('outside the study basin size range'),{},{timeout:15000});console.log('MODEL_COMPLETE',run,'partial='+state.results.partial);
  const pending=page.waitForEvent('download');await page.locator('[data-pfdf-download="events.parquet"]').click();const download=await pending;
  await download.saveAs('/tmp/pfdf-final-events.parquet');assert(fs.statSync('/tmp/pfdf-final-events.parquet').size>100);
  console.log('DOWNLOAD',download.suggestedFilename(),fs.statSync('/tmp/pfdf-final-events.parquet').size);
  await page.reload();await page.locator('[data-pfdf-summary] table').waitFor({timeout:30000});
  assert.match(await page.locator('[data-pfdf-summary]').innerText(),/smoke-dnbr.tif/);console.log('RELOAD_PRESERVED');
  await page.evaluate(()=>{const c=UnitizerClient.getClientSync();c.setGlobalPreference(0);c.dispatchPreferenceChange();});
  assert.match(await page.locator('[data-pfdf-summary]').innerText(),/10 m/);console.log('SI_10_M');
  await page.evaluate(()=>{const c=UnitizerClient.getClientSync();c.setGlobalPreference(1);c.dispatchPreferenceChange();});
  assert.match(await page.locator('[data-pfdf-summary]').innerText(),/33 ft/);console.log('ENGLISH_33_FT');
  await page.locator('#postfire-debris-flow').screenshot({path:artifact+'control_completed.png'});
  await page.locator('#postfire_debris_flow_form input[name=file]').setInputFiles(meta.wd+'/ambiguous-dnbr.tif');
  const ambiguous=await submit('upload','upload-dnbr');await waitAttempt('upload',ambiguous,'needs_scale');
  assert.match(await page.locator('[data-pfdf-summary]').innerText(),/smoke-dnbr.tif/);
  await page.waitForFunction(()=>document.querySelector('[data-pfdf-candidate]').textContent.includes('ambiguous-dnbr.tif'),{},{timeout:15000});
  assert.match(await page.locator('[data-pfdf-candidate]').innerText(),/ambiguous-dnbr.tif/);console.log('AMBIGUOUS_PRESERVED_ACCEPTED');
  await page.locator('[name=scale_mode]').selectOption('scaled_1000');
  const correction=await submit('upload','retry-dnbr');await waitAttempt('upload',correction,'complete');
  await page.waitForFunction(()=>document.querySelector('[data-pfdf-summary]').textContent.includes('ambiguous-dnbr.tif'),{},{timeout:15000});
  assert.match(await page.locator('[data-pfdf-summary]').innerText(),/ambiguous-dnbr.tif/);console.log('CORRECTION_WITHOUT_REUPLOAD');
  const common='from wepppy.nodb.redis_prep import RedisPrep,TaskEnum\nprep=RedisPrep.getInstance('+JSON.stringify(meta.wd)+')\n';
  const saved=execFileSync('wctl',['exec','-T','weppcloud','python','-'],{input:common+'print(prep[str(TaskEnum.build_climate)])\nprep.remove_timestamp(TaskEnum.build_climate)\n',encoding:'utf8'}).trim();
  try {await page.waitForFunction(()=>document.querySelector('[data-pfdf-required]').textContent.includes('Build climate'),{},{timeout:15000});assert(await page.locator('[data-pfdf-action=run]').isDisabled());console.log('LIVE_INVALIDATION');}
  finally {execFileSync('wctl',['exec','-T','weppcloud','python','-'],{input:common+'prep[str(TaskEnum.build_climate)]='+Number(saved)+'\n',encoding:'utf8'});}
  await page.waitForFunction(()=>!document.querySelector('[data-pfdf-required]').textContent.includes('Build climate'),{},{timeout:15000});
  assert(await page.locator('[data-pfdf-action=run]').isEnabled());console.log('LIVE_RECOVERY');
 } finally {await browser.close();}
})().catch(error=>{console.error(error.message);process.exit(1);});
