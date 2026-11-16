const {chromium}=require(require('path').resolve(process.cwd(), 'wepppy/weppcloud/static-src/node_modules/playwright'));const assert=require('assert/strict'),fs=require('fs');
(async()=>{const b=await chromium.launch({headless:true,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const receipt=[];
for(const key of [null,'','constructor','googleSatellite','osm','forestService']) {
const p=await b.newPage();await p.addInitScript(key=>{let context;Object.defineProperty(window,'GL_DASHBOARD_CONTEXT',{get:()=>context,set:v=>{v.basemap=key;context=v;}});},key);
await p.goto('https://forest.tail305ec9.ts.net/weppcloud/runs/mipa-awake-20261102/config/gl-dashboard',{waitUntil:'domcontentloaded'});await p.waitForFunction(()=>!!window.glDashboardDeck);const expected=['googleSatellite','osm','forestService'].includes(key)?key:'googleTerrain';await p.waitForFunction(k=>document.querySelector('#gl-basemap-select').value===k,expected);assert.equal(await p.evaluate(()=>window.currentBasemapKey),expected);
await p.evaluate(()=>window.glDashboardSetBasemap('constructor'));assert.equal(await p.evaluate(()=>window.currentBasemapKey),expected);
receipt.push({initial:key,resolved:expected,unknownInteractiveNoOp:true});await p.close();
}fs.writeFileSync('/tmp/fs-hydration.json',JSON.stringify(receipt,null,2));console.log('PASS initial state cases');await b.close();})().catch(e=>{console.error(e);process.exit(1)});
