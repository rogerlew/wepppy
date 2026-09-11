const {chromium}=require('/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/playwright');
const fs=require('fs');
const assert=require('assert/strict');
const secrets=Object.fromEntries(fs.readFileSync('/workdir/wepppy/docker/secrets/dev-agent.env','utf8').split('\n').filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{let i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1).replace(/^['"]|['"]$/g,'')]}));
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1280,height:1800}});
  page.on('pageerror',e=>console.log('PAGEERROR',e.message));
  await page.goto('https://wc.bearhive.duckdns.org/weppcloud/login');
  await page.locator('input[name=email]').fill(secrets.DEV_AGENT_EMAIL);await page.locator('input[name=password]').fill(secrets.DEV_AGENT_PASSWORD);
  await page.getByRole('button',{name:'Login',exact:true}).click();await page.waitForTimeout(3000);await page.getByRole('button',{name:'Login',exact:true}).click(); await page.waitForURL(url=>!url.pathname.endsWith('/login'),{timeout:20000});
  await page.goto('https://wc.bearhive.duckdns.org/weppcloud/runs/addicted-reservist/config/',{waitUntil:'domcontentloaded',timeout:90000});
  const form=page.locator('#postfire_debris_flow_form');
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/postfire-debris-flow/retry-dnbr')&&r.request().method()==='POST',{timeout:90000});
  await form.locator('[data-pfdf-action="upload"]').click({timeout:90000});
  const response=await responsePromise;
  const receipt=await response.json();
  console.log('RETRY_RECEIPT',response.status(),JSON.stringify(receipt));
  assert(response.ok());
  let view;
  for(let i=0;i<120;i++) {
    await page.waitForTimeout(1000);
    view=await page.evaluate(()=>{
      const f=document.querySelector('#postfire_debris_flow_form');
      return {summary:f?.querySelector('[data-pfdf-summary]')?.textContent,
        message:f?.querySelector('[data-pfdf-message]')?.textContent,
        link:f?.querySelector('[data-job-hint] a')?.textContent,
        status:f?.querySelector('[id="rq_job"]')?.innerText,
        details:f?.querySelector('[id="stacktrace"]')?.textContent};
    });
    if(view.summary?.includes('Applied scale') || view.status?.includes('Failed')) break;
  }
  console.log('UPLOAD_VIEW',JSON.stringify(view));
  assert(view.summary?.includes('Applied scale'));
  assert.equal(view.link,receipt.job_id);
  assert(!view.details?.includes('invalid_raster'));
  await page.reload({waitUntil:'domcontentloaded'});
  for(let i=0;i<30;i++) {
    await page.waitForTimeout(1000);
    const text=await form.locator('[data-pfdf-summary]').innerText();
    if(text.includes('Applied scale')) break;
  }
  assert((await form.locator('[data-pfdf-summary]').innerText()).includes('Applied scale'));
  assert.equal(await form.locator('[data-job-hint] a').innerText(),receipt.job_id);
  await page.evaluate(()=>document.querySelector('#postfire_debris_flow_form').scrollIntoView());
  await page.screenshot({path:'/tmp/pfdf-upload-success.png'});
  console.log('LIVE_UPLOAD_AND_RELOAD_PASS');
 } finally {await browser.close();}
})().catch(error=>{console.error(error.stack);process.exit(1);});
