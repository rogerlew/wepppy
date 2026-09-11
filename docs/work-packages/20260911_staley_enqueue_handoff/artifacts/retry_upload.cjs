const {chromium}=require('/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/playwright');
const fs=require('fs');
const assert=require('assert/strict');
const secrets=Object.fromEntries(fs.readFileSync('/workdir/wepppy/docker/secrets/dev-agent.env','utf8').split('\n').filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{let i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1).replace(/^['"]|['"]$/g,'')]}));
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1280,height:1800}});
  page.on('pageerror',e=>console.log('PAGEERROR',e.message));
  console.log('Login');
  await page.goto('https://wc.bearhive.duckdns.org/weppcloud/login');
  await page.locator('input[name=email]').fill(secrets.DEV_AGENT_EMAIL);await page.locator('input[name=password]').fill(secrets.DEV_AGENT_PASSWORD);
  await page.getByRole('button',{name:'Login',exact:true}).click();await page.waitForTimeout(3000);await page.getByRole('button',{name:'Login',exact:true}).click(); await page.waitForURL(url=>!url.pathname.endsWith('/login'),{timeout:20000});
  const base='https://wc.bearhive.duckdns.org/weppcloud/runs/addicted-reservist/config';
  await page.goto(base+'/',{waitUntil:'domcontentloaded',timeout:90000});
  await page.waitForFunction(()=>window.WCHttp && document.querySelector('#postfire_debris_flow_form'),{timeout:60000});
  const result=await page.evaluate(async()=>{
   try {
    const prefix='/rq-engine/api/runs/addicted-reservist/config/postfire-debris-flow/';
    const before=(await WCHttp.requestWithSessionToken(prefix+'state')).body.result;
    if(before.upload.id!=='72b501a860cd4520817e32e6ff46f1ef' || before.upload.phase!=='failed') {
      throw new Error('Upload state changed; no retry submitted.');
    }
    return (await WCHttp.postJsonWithSessionToken(prefix+'retry-dnbr',
      {candidate_id:before.upload.id,scale_mode:'auto'},
      {form:document.querySelector('#postfire_debris_flow_form')})).body;
   } catch(error) {throw new Error(JSON.stringify({message:error.message,status:error.status,error:error.body && error.body.error}));}
  });
  console.log('RETRY',JSON.stringify(result));
  let state;
  for(let i=0;i<90;i++) {
    state=await page.evaluate(async()=>(await WCHttp.requestWithSessionToken(
      '/rq-engine/api/runs/addicted-reservist/config/postfire-debris-flow/state')).body.result);
    if(state.upload.id!==result.result.attempt_id) throw new Error('Attempt changed while polling.');
    if(!['staged','queued','running','enqueue_unknown'].includes(state.upload.phase)) break;
    await page.waitForTimeout(2000);
  }
  assert.equal(state.upload.phase,'complete',JSON.stringify(state.upload));
  assert.equal(state.dnbr.id,result.result.attempt_id);
  assert.equal(state.dnbr.current,true);
  console.log('UPLOAD_COMPLETE',JSON.stringify({upload:state.upload,dnbr:state.dnbr,run_ready:state.run_ready,freshness:state.freshness}));
  await page.reload({waitUntil:'domcontentloaded',timeout:90000});
  console.log('PASS real browser submission, real RQ upload and reload');
 } finally {await browser.close();}
})().catch(error=>{console.error(error.stack);process.exit(1);});
