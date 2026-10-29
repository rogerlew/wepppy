const path=require('path');
const repo=path.resolve(__dirname,'../../../..');
const {chromium}=require(path.join(repo,'wepppy/weppcloud/static-src/node_modules/playwright'));
const fs=require('fs');
const crypto=require('crypto');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const base='https://wc.bearhive.duckdns.org';
 const url=base+'/weppcloud/runs/dm-anisotropy-validation/disturbed9002/?skip_migration_check=true';
 const response=await page.goto(url,{waitUntil:'domcontentloaded'});
 console.log('page',response.status());
 await page.locator('#soil_anisotropy_upper').waitFor({state:'attached'});
 const result=await page.evaluate(()=>({
   upper:{value:document.querySelector('#soil_anisotropy_upper').value,max:document.querySelector('#soil_anisotropy_upper').getAttribute('max')},
   lower:{value:document.querySelector('#soil_anisotropy_lower').value,max:document.querySelector('#soil_anisotropy_lower').getAttribute('max')},
   indicator:!!document.querySelector('[data-project-developer-indicator]:not([hidden])'),
   unauthorizedActivation:!!document.querySelector('[data-project-action="enable-developer-mode"]')
 }));
 if(result.upper.max!==null||result.lower.max!==null||!result.indicator||result.unauthorizedActivation) throw new Error(JSON.stringify(result));
 await page.locator('#soil_anisotropy_upper').evaluate(input=>{for(let e=input.parentElement;e;e=e.parentElement)if(e.tagName==='DETAILS')e.open=true;});
 await page.locator('[data-wepp-anisotropy]').screenshot({path:path.join(__dirname,'soil-options.png')});
 const download=await page.request.get(base+'/weppcloud/runs/dm-anisotropy-validation/disturbed9002/download/wepp/runs/p1.sol');
 result.downloadStatus=download.status();
 result.downloadUrl=download.url();
 result.downloadSha256=crypto.createHash('sha256').update(await download.body()).digest('hex');
 const loss=await page.request.get(base+'/weppcloud/runs/dm-anisotropy-validation/disturbed9002/download/wepp/output/H1.loss.dat');
 result.lossReportStatus=loss.status();
 result.lossReportSha256=crypto.createHash('sha256').update(await loss.body()).digest('hex');
 const browse=await page.request.get(base+'/weppcloud/runs/dm-anisotropy-validation/disturbed9002/browse/wepp/runs/');
 result.browseStatus=browse.status();
 if(download.status()!==200||loss.status()!==200||browse.status()!==200) throw new Error(JSON.stringify(result));
 fs.writeFileSync(path.join(__dirname,'browser.json'),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify(result));
 await browser.close();
})();
