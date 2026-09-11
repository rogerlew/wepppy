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
   await page.waitForFunction(async ({kind,job,phase,url})=>{
    const r=await WCHttp.requestWithSessionToken(url,{method:'GET'});const s=r.body.result;
    return s[kind]&&s[kind].job_id===job&&s[kind].phase===phase;
   },{kind,job,phase,url:stateUrl},{timeout:90000,polling:1000});
   await page.waitForTimeout(500);
  }
  async function submit(action,endpoint){
   const pending=page.waitForResponse(r=>r.url().endsWith('/'+endpoint)&&r.request().method()==='POST');
   await page.locator('[data-pfdf-action='+action+']').click({timeout:15000});
   const response=await pending;const body=await response.json();
   assert.equal(response.status(),200,JSON.stringify(body));assert(body.job_id);
   return body.job_id;
  }
  await page.goto('https://wc.bearhive.duckdns.org/weppcloud/login');
  await page.locator('input[name=email]').fill(secrets.DEV_AGENT_EMAIL);await page.locator('input[name=password]').fill(secrets.DEV_AGENT_PASSWORD);
  await page.locator('input[type=submit],button[type=submit]').first().click();await page.waitForTimeout(1000);
  await page.goto(`https://wc.bearhive.duckdns.org/weppcloud/runs/${meta.runid}/${meta.config}/`);
  await page.locator('[data-pfdf-required] table').waitFor({timeout:30000});
  await page.locator('#postfire_dnbr_file').focus();
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.id),'postfire_scale');
  await page.keyboard.press('ArrowDown');assert.equal(await page.locator('#postfire_scale').inputValue(),'scaled_1000');
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.dataset.pfdfAction),'upload');
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.value),'cli');
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.dataset.pfdfAction),'run');
  assert.equal(await page.locator('#postfire_dnbr_file').evaluate(e=>e.labels[0].textContent),'differenced Normalized Burn Ratio (dNBR)');
  assert.equal(await page.locator('#postfire_debris_flow_form [data-pfdf-message]').getAttribute('role'),'status');
  console.log('KEYBOARD_ORDER_AND_LABELS_PASS');
 } finally {await browser.close();}
})().catch(error=>{console.error(error.message);process.exit(1);});
