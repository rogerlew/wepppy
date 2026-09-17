const fs = require('node:fs');
const {chromium} = require(process.cwd()+'/wepppy/weppcloud/static-src/node_modules/playwright');
(async()=>{
  const auth=JSON.parse(fs.readFileSync('/tmp/wepppy-freshness-runtime-auth.json','utf8'));
  const browser=await chromium.launch({headless:true});
  try {
    const context=await browser.newContext({storageState:'/tmp/wepppy-freshness-browser-state.json',viewport:{width:1440,height:1000}});
    const page=await context.newPage();
    let errors=0; page.on('pageerror',()=>{errors++;});
    const url=auth.host+'/weppcloud/runs/qa-freshness-runtime-7e24c8d1/config/report/postfire_debris_flow/';
    const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:120000});
    if(response.status()!==200)throw Error('Report status '+response.status());
    const seed=JSON.parse(await page.locator('#postfire-report-seed').textContent());
    if(seed.status!=='available'||seed.summary.current!==true)throw Error('Report seed is not current');
    await page.waitForFunction(()=>document.querySelector('[data-pfr-current]')?.textContent.includes('Results match the current inputs.'),null,{timeout:60000});
    const message=await page.locator('[data-pfr-current]').textContent();
    await page.screenshot({path:__dirname+'/runtime_postfire_report_browser.png'});
    fs.writeFileSync(__dirname+'/runtime_postfire_report_browser.json',JSON.stringify({url,status:response.status(),
      attempt_id:seed.attempt_id,current:seed.summary.current,message,pageErrors:errors,
      eventRows:seed.events.rows.length,totalEvents:seed.events.total},null,2)+'\n');
    if(errors)throw Error('Report page errors: '+errors);
    console.log('Actual report page and currentness match after restore recovery');
  }finally{await browser.close();}
})().catch(err=>{console.error(err.message);process.exitCode=1;});
