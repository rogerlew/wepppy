const {chromium}=require(require('path').resolve(process.cwd(), 'wepppy/weppcloud/static-src/node_modules/playwright'));
const fs=require('fs'),assert=require('assert/strict');
const root='https://tiles.arcgis.com/tiles/gGHDlz6USftL5Pau/arcgis/rest/services/FSBasemap_20240617/VectorTileServer/';
const base='https://forest.tail305ec9.ts.net/weppcloud';
(async()=>{
const b=await chromium.launch({headless:true,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--enable-precise-memory-info']});
const page=await b.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(20000);
await page.addInitScript(()=>{let lib;window.__fsMaps=[];Object.defineProperty(window,'maplibregl',{configurable:true,get:()=>lib,set:v=>{lib=v;const Map=v.Map;v.Map=class extends Map {constructor(...args){super(...args);window.__fsMaps.push(this);}};}});});
const receipt={checks:[],requests:[],errors:[]};const captures=[];
page.on('pageerror',e=>receipt.errors.push(e.message));
page.on('request',r=>{if(r.url().startsWith(root)||r.url().includes('forbidden.invalid')){captures.push((async()=>{const h=await r.allHeaders();receipt.requests.push({url:r.url(),credentials:!!(h.cookie||h.authorization),referrer:!!h.referer});})());}});
await page.goto(base+'/runs/mipa-awake-20261102/config/gl-dashboard',{waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>window.glDashboardDeck?.props.layers.length>2);
const sample=()=>page.evaluate(async()=>{const frames=[];const v=glDashboardDeck.getViewports()[0],initial={longitude:v.longitude,latitude:v.latitude,zoom:v.zoom};let previous=performance.now();for(let i=0;i<60;i++){glDashboardDeck.setProps({viewState:{...initial,longitude:initial.longitude+i*0.00002}});await new Promise(requestAnimationFrame);let now=performance.now();frames.push(now-previous);previous=now;}glDashboardDeck.setProps({viewState:initial});return {method:'60 animated longitude updates via Deck viewState',frames,heap:performance.memory.usedJSHeapSize};});
receipt.terrain=await sample();
await page.selectOption('#gl-basemap-select','forestService');
await page.waitForFunction(()=>window.__fsMaps.at(-1)?.loaded(),null,{timeout:60000});
receipt.vector=await sample();
receipt.loaded=await page.evaluate(()=>{const m=__fsMaps.at(-1);return {version:maplibregl.getVersion(),features:m.queryRenderedFeatures().length,symbols:m.queryRenderedFeatures().filter(f=>f.layer.type==='symbol').length,layers:glDashboardDeck.props.layers.filter(Boolean).map(l=>l.id),transfer:performance.getEntriesByType('resource').filter(r=>r.name.includes('maplibre')).map(r=>({name:r.name,bytes:r.transferSize,duration:r.duration}))};});
assert(receipt.loaded.features>0);assert(receipt.loaded.symbols>0);
const alignment=()=>page.evaluate(()=>{const v=glDashboardDeck.getViewports()[0],m=__fsMaps.at(-1);const c=[v.longitude+0.002,v.latitude+0.002],a=v.project(c),d=m.project(c);return {delta:[a[0]-d.x,a[1]-d.y],zoom:v.zoom,mapZoom:m.getZoom(),viewport:[v.width,v.height],canvas:[m.getCanvas().clientWidth,m.getCanvas().clientHeight]};});
receipt.beforePan=await alignment();
const box=await page.locator('#gl-dashboard-map').boundingBox();await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+70,box.y+box.height/2+40,{steps:8});await page.mouse.up();await page.waitForTimeout(500);
receipt.afterPan=await alignment();assert(receipt.afterPan.delta.every(v=>Math.abs(v)<0.01));
receipt.pick=await page.evaluate(()=>{const d=glDashboardDeck,v=d.getViewports()[0];return d.pickObjects({x:0,y:0,width:v.width,height:v.height,maxObjects:2}).map(x=>({layer:x.layer.id,object:!!x.object}));});assert(receipt.pick.length>0);
await page.setViewportSize({width:390,height:844});await page.waitForTimeout(500);receipt.mobile=await alignment();assert(receipt.mobile.delta.every(v=>Math.abs(v)<0.01));await page.locator('.wc-basemap-credit').scrollIntoViewIfNeeded();await page.screenshot({path:'/tmp/fs-mobile.png'});
await page.setViewportSize({width:1440,height:1000});
const originalView=await page.evaluate(()=>{const v=glDashboardDeck.getViewports()[0];return {longitude:v.longitude,latitude:v.latitude,zoom:v.zoom};});
// Coverage and source-edge checks do not alter global controller limits.
for(const view of [{longitude:30,latitude:-20,zoom:3},{longitude:-116.78,latitude:47.49,zoom:19},{longitude:-116.78,latitude:47.49,zoom:20}]){
 await page.evaluate(v=>glDashboardDeck.setProps({viewState:v}),view);await page.waitForTimeout(600);const a=await alignment();assert.equal(a.zoom,a.mapZoom);receipt.checks.push({view,alignment:a});
}
await page.evaluate(v=>glDashboardDeck.setProps({viewState:v}),originalView);
const official=await (await page.request.get(root+'resources/styles/root.json')).json();
await page.selectOption('#gl-basemap-select','googleTerrain');
// Hostile attribution crosses the real adapter/renderer boundary; fixed credit must survive.
const hostile=JSON.parse(JSON.stringify(official));hostile.sources.esri.attribution='<details open onload="1" ontoggle="window.__xss=1">evil</details>';
await page.route(root+'resources/styles/root.json',r=>r.fulfill({json:hostile,headers:{'access-control-allow-origin':'*'}}));
await page.selectOption('#gl-basemap-select','forestService');await page.waitForFunction(()=>__fsMaps.at(-1)?.loaded(),null,{timeout:60000});
assert.equal(await page.evaluate(()=>!!window.__xss||document.querySelector('.wc-basemap-credit details')!==null),false);
assert.match(await page.locator('.wc-basemap-credit').innerText(),/USDA/);receipt.checks.push('hostile attribution stripped; no TileJSON request');
await page.selectOption('#gl-basemap-select','googleTerrain');await page.unroute(root+'resources/styles/root.json');
const foreign=JSON.parse(JSON.stringify(official));foreign.glyphs='https://forbidden.invalid/{fontstack}/{range}.pbf';
await page.route(root+'resources/styles/root.json',r=>r.fulfill({json:foreign,headers:{'access-control-allow-origin':'*'}}));
await page.selectOption('#gl-basemap-select','forestService');await page.getByRole('status').filter({hasText:'Forest Service basemap unavailable'}).waitFor();assert.equal(receipt.requests.some(r=>r.url.includes('forbidden.invalid')),false);receipt.checks.push('hostile URL rejected before request');
await page.selectOption('#gl-basemap-select','googleTerrain');await page.unroute(root+'resources/styles/root.json');
await page.route(root+'resources/styles/root.json',r=>r.fulfill({status:302,headers:{location:'https://forbidden.invalid/redirect','access-control-allow-origin':'*'}}));
await page.selectOption('#gl-basemap-select','forestService');await page.getByRole('status').filter({hasText:'Forest Service basemap unavailable'}).waitFor();assert.equal(receipt.requests.some(r=>r.url.includes('forbidden.invalid')),false);receipt.checks.push('redirect blocked at fetch boundary');
await Promise.all(captures);
assert.equal(receipt.requests.some(r=>r.credentials||r.referrer),false);
fs.writeFileSync('/tmp/fs-deep.json',JSON.stringify(receipt,null,2));console.log('PASS',receipt.checks.length,receipt.loaded,receipt.errors);await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
