const fs = require('node:fs');
const {chromium} = require(process.cwd()+'/wepppy/weppcloud/static-src/node_modules/playwright');
(async()=>{
  const runid=process.argv[2], label=process.argv[3], expected=process.argv[4];
  if(!runid?.startsWith('qa-freshness-') || !['current','stale'].includes(expected)) throw Error('Disposable run and expected freshness required');
  const auth=JSON.parse(fs.readFileSync('/tmp/wepppy-freshness-runtime-auth.json','utf8'));
  const browser=await chromium.launch({headless:true});
  try {
    const context=await browser.newContext({storageState:'/tmp/wepppy-freshness-browser-state.json',viewport:{width:1440,height:1000}});
    const page=await context.newPage();
    const network=[]; let pageErrors=0;
    page.on('pageerror',()=>{pageErrors++;});
    page.on('response',r=>{const u=new URL(r.url()); if(u.pathname.includes('postfire')||u.pathname.includes('preflight'))network.push({path:u.pathname,status:r.status()});});
    const url=auth.host+'/weppcloud/runs/'+runid+'/config/';
    const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:120000});
    if(response.status()!==200)throw Error('Run page HTTP '+response.status());
    await page.locator('#postfire_debris_flow_form').waitFor({state:'attached',timeout:60000});
    const message=page.locator('[data-pfdf-message]');
    await page.waitForFunction(expect=>{
      const value=document.querySelector('[data-pfdf-message]')?.textContent||'';
      return expect==='stale'?value.includes('Inputs changed'):value.includes('Run complete');
    },expected,{timeout:60000});
    const buildId=await page.locator('body').getAttribute('data-controllers-gl-expected-build-id');
    const script=await page.locator('script[src*="controllers-gl.js"]').first().getAttribute('src');
    const served=await context.request.get(new URL(script,page.url()).toString());
    if(served.status()!==200)throw Error('Bundle HTTP '+served.status());
    const header=(await served.text()).split('\n').slice(0,80).find(line=>line.includes('Build date:'));
    const servedId=header?.split('Build date:')[1].trim();
    if(!buildId || buildId!==servedId)throw Error('Rendered and served bundle IDs differ');
    const firstMessage=await message.textContent();
    await page.reload({waitUntil:'domcontentloaded',timeout:120000});
    await page.waitForFunction(expect=>{
      const value=document.querySelector('[data-pfdf-message]')?.textContent||'';
      return expect==='stale'?value.includes('Inputs changed'):value.includes('Run complete');
    },expected,{timeout:60000});
    await page.locator('#postfire_debris_flow_form').scrollIntoViewIfNeeded();
    await page.screenshot({path:__dirname+'/runtime_browser_'+label+'.png'});
    fs.writeFileSync(__dirname+'/runtime_browser_'+label+'.json',JSON.stringify({url,status:200,expected,
      firstMessage,reloadedMessage:await message.textContent(),renderedBuildId:buildId,servedBuildId:servedId,
      bundlePath:new URL(script,page.url()).pathname,pageErrors,network},null,2)+'\n');
    console.log('Browser',label,expected,'and bundle alignment passed');
  }finally{await browser.close();}
})().catch(err=>{console.error(err.message);process.exitCode=1;});
