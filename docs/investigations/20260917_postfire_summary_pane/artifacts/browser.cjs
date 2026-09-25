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

  record({stage:'loaded',panelCount:await page.locator('[data-pfdf-result-panel]').count(),message:await form.locator('[data-pfdf-message]').innerText()});
  await page.locator('[data-pfdf-result-panel]').waitFor({state:'visible',timeout:30000});
  assert.equal(await form.locator('[data-pfdf-download]').count(),0);
  assert.equal(await form.getByText('View likelihood report',{exact:true}).count(),1);
  const result=await page.evaluate(()=>{
    const f=document.querySelector('#postfire_debris_flow_form');
    const p=f.querySelector('[data-pfdf-result-panel]');
    return {summary:p.innerText,panels:[...p.parentElement.children].map(x=>x.id),helpBeforeTable:!!(f.querySelector('header a').compareDocumentPosition(f.querySelector('header table'))&Node.DOCUMENT_POSITION_FOLLOWING)};
  });
  assert(result.helpBeforeTable);assert.deepEqual(result.panels,['postfire_status_panel','postfire_summary_panel','postfire_stacktrace_panel']);record({stage:'actual_accepted',...result});
  await form.screenshot({path:path.join(output,'desktop.png')});
  const link=form.getByText('View likelihood report',{exact:true});
  const [report]=await Promise.all([page.waitForEvent('popup'),link.click()]);await report.waitForLoadState('domcontentloaded');assert(report.url().includes('/report/postfire_debris_flow/'));record({stage:'report_open',url:report.url()});await report.close();
  await page.setViewportSize({width:390,height:1000});await form.screenshot({path:path.join(output,'mobile.png')});
  await page.evaluate(async()=>{
    const r=await WCHttp.requestWithSessionToken('/rq-engine/api/runs/thespian-cleanness/config/postfire-debris-flow/state',{method:'GET'});
    window.summaryTestState=r.body.result;
    PostfireDebrisFlow.getInstance().destroy();
    PostfireDebrisFlow.getInstance().render({...summaryTestState,results:null,run:null,upload:null});
  });
  assert.equal(await link.isVisible(),false);record({stage:'absent',report_visible:false});
  await page.evaluate(()=>PostfireDebrisFlow.getInstance().render({...summaryTestState,results:{...summaryTestState.results,current:false},run:{phase:'failed',error:{message:'Example failed replacement'}}}));
  assert(await link.isVisible());assert((await form.locator('[data-pfdf-result-summary]').innerText()).includes('Previous run'));record({stage:'failed_replacement',previous_report_visible:true});
  await form.screenshot({path:path.join(output,'previous-mobile.png')});
  await page.reload();await page.locator('[data-pfdf-result-panel]').waitFor({state:'visible'});record({stage:'reload',report_visible:true});
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
