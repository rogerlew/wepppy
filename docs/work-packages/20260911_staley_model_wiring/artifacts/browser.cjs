const {chromium}=require('/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/playwright');
const fs=require('fs');
const assert=require('assert/strict');
const secrets=Object.fromEntries(fs.readFileSync('/workdir/wepppy/docker/secrets/dev-agent.env','utf8').split('\n').filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{let i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1).replace(/^['"]|['"]$/g,'')]}));
(async()=>{
 const browser=await chromium.launch({headless:true});
 let page;
 try {
  page=await browser.newPage({viewport:{width:1280,height:1800}});
  page.on('pageerror',e=>console.log('PAGEERROR',e.message));
  page.on('request',r=>{if(r.method()==='POST' && r.url().includes('postfire-debris-flow')) console.log('POST',new URL(r.url()).pathname);});
  console.log('Login');
  await page.goto('https://wc.bearhive.duckdns.org/weppcloud/login');
  await page.locator('input[name=email]').fill(secrets.DEV_AGENT_EMAIL);await page.locator('input[name=password]').fill(secrets.DEV_AGENT_PASSWORD);
  await page.getByRole('button',{name:'Login',exact:true}).click();await page.waitForTimeout(3000);await page.getByRole('button',{name:'Login',exact:true}).click(); await page.waitForURL(url=>!url.pathname.endsWith('/login'),{timeout:20000});
  const base='https://wc.bearhive.duckdns.org/weppcloud/runs/addicted-reservist/config';
  await page.goto(base+'/#postfire-debris-flow',{waitUntil:'domcontentloaded',timeout:90000});
  await page.waitForFunction(()=>window.WCHttp && document.querySelector('#postfire_debris_flow_form'),null,{timeout:60000,polling:100});
  const form=page.locator('#postfire_debris_flow_form');
  await page.evaluate(()=>{document.querySelector('#map details').open=false;document.getElementById('postfire_debris_flow_form').scrollIntoView();});
  await page.waitForFunction(()=>window.preflightConnected === true);
  const read=()=>page.evaluate(async()=>(await WCHttp.requestWithSessionToken('/rq-engine/api/runs/addicted-reservist/config/postfire-debris-flow/state')).body.result);
  let state=await read();
  console.log('RADIOS',await form.locator('input[type=radio]').evaluateAll(xs=>xs.map(x=>({name:x.name,value:x.value,checked:x.checked}))));
  console.log('BEFORE',JSON.stringify({model:state.model,run:state.run,required:state.required,results:state.results && {id:state.results.id,model:state.results.model,current:state.results.current}}));
  if(state.run && ['queued','running','staged','enqueue_unknown'].includes(state.run.phase)) throw new Error('Existing active job; no new submission.');
  await page.waitForFunction(()=>!document.querySelector('[data-pfdf-action=run]').disabled,null,{timeout:60000,polling:100});
  for(const model of (process.env.PFDF_MODELS || 'M1,M3').split(',')) {

    console.log('CLICK-DOM',await page.evaluate(()=>({url:location.href,radios:[...document.querySelectorAll('[name=model]')].map(x=>({id:x.id,checked:x.checked,connected:x.isConnected}))})));
    if(state.model !== model) {
      console.log('SELECT',model);
      const [response]=await Promise.all([
        page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/postfire-debris-flow/selection') && r.request().method()==='POST',{timeout:60000}),
        model === 'M3' ? page.evaluate(()=>document.getElementById('postfire_model_m3').click()) : page.evaluate(()=>document.getElementById('postfire_model_m1').click())
      ]);
      assert.equal(response.status(),200,await response.text());
    }
    await page.waitForFunction(`document.querySelector('[name=model]:checked').value === ${JSON.stringify(model)} && !document.querySelector('[data-pfdf-action=run]').disabled`,null,{timeout:60000,polling:100});
    state=await read();assert.equal(state.model,model);
    assert.equal(await form.locator('[data-pfdf-dnbr-fields]').isVisible(),model==='M1');
    assert.equal(state.required.some(x=>x.key==='k'),model==='M1');
    assert.equal(state.required.some(x=>x.key==='soils'),model==='M3');
    assert.equal(state.required.some(x=>x.key==='dnbr'),model==='M1');
    const [response]=await Promise.all([
      page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/postfire-debris-flow/run') && r.request().method()==='POST',{timeout:60000}),
      page.evaluate(()=>document.querySelector('[data-pfdf-action=run]').click())
    ]);const receipt=await response.json();assert.equal(response.status(),200,JSON.stringify(receipt));
    console.log('SUBMITTED',model,JSON.stringify(receipt));
    for(let n=0;n<100;n++) {
      state=await read();
      if(state.run.id!==receipt.result.attempt_id) throw new Error('Run superseded; stop.');
      if(!['queued','running','staged','enqueue_unknown'].includes(state.run.phase)) break;
      await page.waitForTimeout(1000);
    }
    assert.equal(state.run.model,model);
    if(model==='M1') {assert.equal(state.run.phase,'complete',JSON.stringify(state.run));assert.equal(state.results.model,'M1');}
    else {assert.equal(state.run.phase,'failed');assert.equal(state.run.error.code,'integration_pending');assert.equal(state.results.model,'M1');assert.equal(state.results.current,true);}
    console.log('TERMINAL',JSON.stringify({run:state.run,results:state.results && {id:state.results.id,model:state.results.model,current:state.results.current}}));
    await page.reload({waitUntil:'domcontentloaded',timeout:90000});
    await page.evaluate(()=>{document.querySelector('#map details').open=false;document.getElementById('postfire_debris_flow_form').scrollIntoView();});
    await page.waitForFunction(model=>document.querySelector('[name=model]:checked')?.value===model && !document.querySelector('[data-pfdf-action=run]').disabled,model,{timeout:60000,polling:100});
    if(model==='M3') {
      await page.waitForFunction(()=>document.querySelector('[data-pfdf-message]').textContent.includes('M3 soil and terrain integration'),null,{timeout:60000,polling:100});
      assert.ok((await page.evaluate(()=>document.getElementById('postfire_debris_flow_form').textContent)).includes(receipt.job_id));
      assert.equal(await form.locator('[data-pfdf-dnbr-fields]').isVisible(),false);
    }
  }
  await page.evaluate(()=>document.getElementById('postfire_debris_flow_form').scrollIntoView());
  await page.screenshot({path:'/tmp/pfdf-model-control.png',fullPage:false});
  console.log('PASS M1/M3 actual UI submissions, persisted model, conditional inputs, M3 failure/job ID, and retained current M1 outputs');
 } catch(error) {
   console.log('FAIL-DOM',await page.evaluate(()=>({url:location.href,forms:document.querySelectorAll('#postfire_debris_flow_form').length,radios:[...document.querySelectorAll('[name=model]')].map(x=>({id:x.id,value:x.value})),text:document.querySelector('#postfire_debris_flow_form')?.textContent})));
   fs.writeFileSync('/tmp/pfdf-browser-failed.html',await page.content());
   throw error;
 } finally {await browser.close();}
})().catch(error=>{console.error(error.stack);process.exit(1);});
