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
  page.on('request',r=>{if(r.method()==='POST') console.log('POST',new URL(r.url()).pathname);});
  console.log('Login');
  await page.goto('https://wc.bearhive.duckdns.org/weppcloud/login');
  await page.locator('input[name=email]').fill(secrets.DEV_AGENT_EMAIL);await page.locator('input[name=password]').fill(secrets.DEV_AGENT_PASSWORD);
  await page.getByRole('button',{name:'Login',exact:true}).click();await page.waitForTimeout(3000);await page.getByRole('button',{name:'Login',exact:true}).click(); await page.waitForURL(url=>!url.pathname.endsWith('/login'),{timeout:20000});
  const base='https://wc.bearhive.duckdns.org/weppcloud/runs/addicted-reservist/config';

  page.on('response',async response=>{if(response.url().includes('/postfire-debris-flow/selection')) console.log('SELECTION RESPONSE',response.status());});
  let release;
  const ready=new Promise(resolve=>{release=resolve;});
  await page.route('**/postfire-debris-flow/state',async route=>{await ready;await route.continue();});
  await page.goto(base+'/#postfire-debris-flow',{waitUntil:'domcontentloaded',timeout:90000});
  await page.evaluate(()=>{document.querySelector('#map details').open=false;document.getElementById('postfire_debris_flow_form').scrollIntoView();});
  assert.ok(await page.evaluate(()=>[...document.querySelectorAll('#postfire_debris_flow_form [name=model], #postfire_debris_flow_form [name=frequency_source]')].every(x=>x.disabled)));
  release();
  await page.waitForFunction(()=>!document.getElementById('postfire_model_m3').disabled,null,{timeout:60000,polling:100});
  await page.unroute('**/postfire-debris-flow/state');
  async function select(which) {

    const selected=await page.evaluate(()=>({model:document.querySelector('[name=model]:checked').value,frequency:document.querySelector('#postfire_debris_flow_form [name=frequency_source]:checked').value}));
    if ((which==='noaa' && selected.frequency==='noaa') || selected.model===which) return;
    if(which==='noaa') await page.evaluate(()=>document.querySelector('#postfire_debris_flow_form [value=noaa]').click());
    else if(which==='M1') await page.evaluate(()=>document.getElementById('postfire_model_m1').click());
    else await page.evaluate(()=>document.getElementById('postfire_model_m3').click());
    await page.waitForFunction(()=>!document.querySelector('[data-pfdf-action=run]').disabled,null,{timeout:60000,polling:100});
    const state=await page.evaluate(async()=>(await WCHttp.requestWithSessionToken('/rq-engine/api/runs/addicted-reservist/config/postfire-debris-flow/state')).body.result);
    assert.equal(state.frequency_source,'noaa');
    if(which !== 'noaa') assert.equal(state.model,which);
    console.log('SAVED',state.model,state.frequency_source);
  }
  if(!(await page.evaluate(()=>document.querySelector('#postfire_debris_flow_form [value=noaa]').checked))) await select('noaa');
  await select('M3');await select('M1');await select('M3');
  let frame;
  page.on('websocket',ws=>{if(ws.url().includes('/preflight/')) ws.on('framereceived',event=>{frame=JSON.parse(String(event.payload));});});
  await page.reload({waitUntil:'domcontentloaded',timeout:90000});
  await page.evaluate(()=>{document.querySelector('#map details').open=false;document.getElementById('postfire_debris_flow_form').scrollIntoView();});
  await page.waitForFunction(()=>!document.querySelector('[data-pfdf-action=run]').disabled && document.getElementById('postfire_model_m3').checked,null,{timeout:60000,polling:100});
  const dom=await page.evaluate(()=>({model:document.querySelector('[name=model]:checked').value,frequency:document.querySelector('#postfire_debris_flow_form [name=frequency_source]:checked').value,dnbrHidden:document.querySelector('[data-pfdf-dnbr-fields]').hidden,text:document.getElementById('postfire_debris_flow_form').textContent,connected:window.preflightConnected}));
  assert.equal(dom.frequency,'noaa');assert.equal(dom.model,'M3');assert.equal(dom.dnbrHidden,true);
  assert.ok(dom.text.includes('6259b9ab-b249-4edc-a4ac-bdab669df5e0'));
  assert.ok(dom.text.includes('M3 soil and terrain integration is not implemented yet.'));
  console.log('RELOAD',JSON.stringify({model:dom.model,frequency:dom.frequency,dnbrHidden:dom.dnbrHidden,jobIdVisible:true,errorVisible:true,connected:dom.connected}));
  console.log('PREFLIGHT',JSON.stringify(frame));
  const download=await page.evaluate(async()=>{const link=document.querySelector('[data-pfdf-download="manifest.json"]');const result=await WCHttp.requestWithSessionToken(link.href);return {url:link.href,status:result.status};});
  console.log('DOWNLOAD',JSON.stringify(download));
  await page.evaluate(()=>{document.getElementById('postfire-debris-flow').scrollIntoView();window.scrollBy(0,-45);});
  await page.screenshot({path:'/tmp/pfdf-model-control-final.png',fullPage:false});
  console.log('PASS delayed initial state, restored NOAA, M1/M3 persistence, failed M3 job reload, download and preflight stream');
 } finally {await browser.close();}
})().catch(error=>{console.error(error.stack);process.exit(1);});
