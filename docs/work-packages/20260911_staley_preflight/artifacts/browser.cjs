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
  console.log('Loading project');
  await page.goto('https://wc.bearhive.duckdns.org/weppcloud/runs/addicted-reservist/config/',{waitUntil:'domcontentloaded',timeout:90000});
  console.log('Project DOM loaded');
  let view;
  for(let i=0;i<90;i++) {
    await page.waitForTimeout(1000);
    view=await page.evaluate(()=>{
      const a=document.querySelector('#toc a[href="#postfire-debris-flow"]');
      return {check:window.lastPreflightChecklist?.postfire_debris_flow,
        emoji:a?.getAttribute('data-toc-emoji'),metadata:a?.getAttribute('data-toc-emoji-value'),
        label:a?.textContent,previous:a?.closest('li')?.previousElementSibling?.textContent.trim(),
        job:document.querySelector('#postfire_debris_flow_form [data-job-hint] a')?.textContent};
    });
    if(i%10===0) console.log('View',JSON.stringify(view));
    if(view.check && view.emoji==='🌋' && view.job) break;
  }
  console.log(JSON.stringify(view));
  assert.equal(view.check,true); assert.equal(view.emoji,'🌋');
  assert.equal(view.metadata,'🌋'); assert.equal(view.label,'Post-fire debris flow');
  assert.equal(view.previous,'Gridded RUSLE');
  assert.equal(view.job,'3cb153a8-453d-4817-93a0-72ef6a22e714');
  await page.reload({waitUntil:'domcontentloaded',timeout:90000});
  for(let i=0;i<90;i++) {
    await page.waitForTimeout(1000);
    if(await page.evaluate(()=>document.querySelector('#toc a[href="#postfire-debris-flow"]')?.getAttribute('data-toc-emoji')==='🌋')) break;
  }
  assert.equal(await page.evaluate(()=>document.querySelector('#toc a[href="#postfire-debris-flow"]')?.getAttribute('data-toc-emoji')),'🌋');
  console.log('PASS live preflight websocket checklist, canonical emoji/label/order/job, reload');
 } finally {await browser.close();}
})().catch(error=>{console.error(error.stack);process.exit(1);});
