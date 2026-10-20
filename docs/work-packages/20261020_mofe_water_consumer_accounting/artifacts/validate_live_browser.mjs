// Authenticated development-only report and query-engine readback on the isolated copy.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const repo = '/workdir/wepppy';
const require = createRequire(path.join(repo,'wepppy/weppcloud/static-src/package.json'));
const {chromium} = require('@playwright/test');
const base = 'https://wc.bearhive.duckdns.org';
const runid = 'mofe-water-replay-five-year-20261020';
const config = 'disturbed9002-mofe';
const out = `/wc1/runs/mo/${runid}/water-validation`;
// Reuse the repository's canonical stored-agent login/CAP helper without
// retaining credentials or an authenticated browser storage-state artifact.
const smoke = fs.readFileSync(path.join(repo,'wepppy/weppcloud/static-src/tests/smoke/soil-anisotropy.spec.js'),'utf8');
const helpers = smoke.slice(smoke.indexOf('function fnv32aHash'),smoke.indexOf('async function setReadonly'));
const login = new Function('fs','path','repo','base','createHash',helpers+'\nreturn login;')(fs,path,repo,base,createHash);
const browser = await chromium.launch({headless:true,executablePath:'/home/roger/.cache/ms-playwright/chromium-1194/chrome-linux/chrome'});
try {
 const page = await browser.newPage({viewport:{width:1280,height:900}});
 await login(page);
 const url = `${base}/weppcloud/runs/${runid}/${config}/report/wepp/avg_annual_watbal`;
 const response = await page.goto(url,{waitUntil:'domcontentloaded'});
 fs.writeFileSync(`${out}/report-response.html`, await page.content());
 console.log('report response', response.status(), page.url());
 await page.locator('#hillslopes_watbal').waitFor();
 const rows = await page.locator('#hillslopes_watbal tbody tr').evaluateAll(rows=>rows.slice(1).map(row=>Array.from(row.querySelectorAll('td')).map(cell=>Number(cell.getAttribute('sorttable_customkey')))));
 if (rows.length !== 1) throw new Error('Real HTTP report row count mismatch');
 await page.screenshot({path:`${out}/live-report-browser.png`});
 const csv = await page.request.get(url+'?format=csv&table=hillslopes');
 const csvText = await csv.text();
 if (!csv.ok() || !csvText.startsWith('TopazID,')) throw new Error('Real HTTP CSV failed');
 fs.writeFileSync(`${out}/live-report.csv`,csvText);
 const downloads = [];
 const cacheRel = 'wepp/reports/cache/hillslope_watbal_summary.parquet';
 const browse = await page.request.get(`${base}/weppcloud/runs/${runid}/${config}/browse/wepp/reports/cache/`);
 if (!browse.ok() || !(await browse.text()).includes('hillslope_watbal_summary.parquet')) {
   throw new Error('Published report cache is not visible through project browse');
 }
 const exportRoot = '/wc1/runs/mo/mofe-water-replay-five-year-20261020';
 const exportReceipts = JSON.parse(fs.readFileSync(`${exportRoot}/service-receipt.json`,'utf8'));
 const artifacts = [
   {run:runid, rel:cacheRel, local:`/wc1/runs/mo/${runid}/${cacheRel}`},
   ...exportReceipts.map(item=>({run:path.basename(exportRoot),rel:item.result.artifact_relpath,
     local:`${exportRoot}/${item.result.artifact_relpath}`})),
 ];
 for (const artifact of artifacts) {
   const target = `/weppcloud/runs/${artifact.run}/${config}/download/${artifact.rel}`;
   // Use the normal run-entry redirect to mint the scoped browse cookie.
   const response = await page.request.get(`${base}/weppcloud/runs/${artifact.run}/?next=${encodeURIComponent(target)}`);
   const bytes = await response.body();
   const expected = createHash('sha256').update(fs.readFileSync(artifact.local)).digest('hex');
   const actual = createHash('sha256').update(bytes).digest('hex');
   if (!response.ok() || expected !== actual) throw new Error(`Artifact download mismatch: ${artifact.rel}; HTTP ${response.status()}; type ${response.headers()["content-type"]}; bytes ${bytes.length}`);
   downloads.push({run:artifact.run,relpath:artifact.rel,status:response.status(),sha256:actual});
 }
 const events = {};
 for (const mode of ['event_P','event_Q','event_ET']) {
 const result = await page.evaluate(async ({runid,config,mode})=>{
   const {createWeppDataManager} = await import('/weppcloud/static/js/gl-dashboard/data/wepp-data.js');
   const state = {weppEventSelectedDate:'2022-11-04',comparisonMode:true,currentScenarioPath:'validation',baseSummaryCache:{}};
   const manager = createWeppDataManager({ctx:{runid,config},getState:()=>state,
     setValue:(key,value)=>{state[key]=value;},setState:update=>Object.assign(state,update),
     postQueryEngine:async payload=>{
       const response = await fetch(`/query-engine/runs/${runid}/${config}/query`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
       if (!response.ok) throw new Error(`Query engine HTTP ${response.status}: ${await response.text()}`);
       return response.json();
     },pickActiveWeppEventLayer:()=>({mode}),WEPP_EVENT_WAT_PATH:'wepp/output/interchange/H.wat.parquet'});
   const refreshed = await manager.refreshWeppEventData();
   manager.computeWeppEventDiffRanges();
   return {refreshed,state};
 },{runid,config,mode});
 if (!result.refreshed || Object.keys(result.state.weppEventSummary).length !== 1) throw new Error('Live event Q query did not return every hill');
 events[mode] = result;
 }
 fs.writeFileSync(`${out}/live-browser-receipt.json`,JSON.stringify({reportStatus:response.status(),csvStatus:csv.status(),browseStatus:browse.status(),reportRows:rows,downloads,events},null,2));
 console.log(JSON.stringify({reportStatus:response.status(),csvStatus:csv.status(),reportRows:rows.length,eventModes:Object.keys(events)}));
} finally { await browser.close(); }
