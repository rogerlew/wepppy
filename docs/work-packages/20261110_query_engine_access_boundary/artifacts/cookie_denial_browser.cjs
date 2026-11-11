const {chromium} = require('/home/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/playwright');
const {execFileSync} = require('node:child_process');
const assert = require('node:assert/strict');
const {login,base} = require('./forest_browser.cjs');
(async () => {
 const manifest=JSON.parse(execFileSync('wctl',['exec','-T','weppcloud','cat',
  '/workdir/wepppy/docker/secrets/qe-cookie-denial-followup.json'],{encoding:'utf8'}));
 const browser=await chromium.launch({headless:true});
 try {
 const context=await browser.newContext(); const page=await context.newPage();
 await login(page);
 const entry=await page.goto(`${base}/weppcloud/runs/${manifest.ordinary}/${manifest.config}/`);
 assert.equal(entry.status(),200);
 const names=async()=> (await context.cookies(base+'/query-engine/runs/')).filter(c=>c.name.startsWith('wepp_query_')).map(c=>c.name).sort();
 const before=await names();assert.equal(before.length,1);
 const endpoint=`/query-engine/runs/${manifest.ordinary}/${manifest.config}`;
 const result=await page.evaluate(async url=>{const r=await fetch(url+'/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({datasets:['data/sample.parquet']})});return {status:r.status,body:await r.json()};},endpoint);
 assert.equal(result.status,200);assert.deepEqual(result.body.records,[{value:3},{value:7}]);
 console.log('Ordinary private page/cookie/query records: passed');
 const collection=await page.goto(base+'/weppcloud/bounds_ws_viewer?'+new URLSearchParams({ws:JSON.stringify([{runid:manifest.batch}])}));
 console.log('Admin without Batch membership collection status:',collection.status());
 assert.equal(collection.status(),200);
 assert.deepEqual(await names(),before);
 const denied=await context.request.get(`${base}/query-engine/runs/${manifest.batch}/${manifest.config}/schema`);
 assert.equal(denied.status(),401);
 console.log('Admitted Batch collection remains available without minting a query grant: passed');
 const ordinaryCookie=(await context.cookies(base+'/query-engine/runs/')).find(c=>c.name.startsWith('wepp_query_'));
 const collision=await context.request.get(`${base}/query-engine/runs/${manifest.batch}/${manifest.config}/schema`,{headers:{Authorization:'Bearer '+ordinaryCookie.value}});
 assert.equal(collision.status(),403);
 assert.match(await collision.text(),/Credential not authorized for run/);
 console.log('Ordinary session bearer rejected at grouped resource binding: passed');
 await page.goto(base+'/weppcloud/logout');
 assert.equal((await context.request.get(base+endpoint+'/schema')).status(),401);
 console.log('Ordinary logout revocation: passed');
 await context.close();
 } finally {await browser.close();}
})().catch(error=>{console.error(error.message.split('\n')[0]);process.exitCode=1;});
