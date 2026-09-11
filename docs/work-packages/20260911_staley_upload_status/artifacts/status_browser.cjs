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
  for(let pass=0;pass<2;pass++) {
    let report;
    for(let i=0;i<24;i++) {
      await page.waitForTimeout(1000);
      report=await page.evaluate(()=>{
        const form=document.querySelector('#postfire_debris_flow_form');
        return {status:form?.querySelector('[id="rq_job"]')?.innerText,
          link:form?.querySelector('[data-job-hint] a')?.textContent,
          details:form?.querySelector('[id="stacktrace"]')?.textContent,
          rows:form?.querySelectorAll('[id="rq_job"] > div').length};
      });
      if(report.status?.includes('Failed') && report.link && report.details?.includes('invalid_raster')) break;
    }
    console.log('PASS_STATE',pass,JSON.stringify(report));
    assert(report.status?.includes('Failed'));
    assert.equal(report.link,'0d4bc387-010e-44f7-8d3b-ef5f20691021');
    assert(report.details?.includes('invalid_raster'));
    assert.equal(report.rows,2);
    if(pass===0) await page.reload({waitUntil:'domcontentloaded'});
  }
  await page.locator('#postfire_status_panel').screenshot({path:'/tmp/pfdf-failed-status.png'});
  console.log('FAILED_JOB_LINK_LAYOUT_AND_RELOAD_PASS');
 } finally {await browser.close();}
})().catch(error=>{console.error(error.stack);process.exit(1);});
