// Browser evidence for real report DOM and real dashboard query/range modules.
// Query responses are the independent DuckDB fixture results; no live API claim.
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require = createRequire('/workdir/wepppy/wepppy/weppcloud/static-src/package.json');
const {chromium} = require('@playwright/test');
const root = '/wc1/runs/mo/mofe-et-dp-validation-20261020/mofe-validation';
const browser = await chromium.launch({headless:true, executablePath:'/home/roger/.cache/ms-playwright/chromium-1194/chrome-linux/chrome'});
const page = await browser.newPage({viewport:{width:1280,height:900}});
await page.route('**/*', route => route.abort());
const html = fs.readFileSync(`${root}/report-view.html`,'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'');
await page.setContent(html,{waitUntil:'domcontentloaded'});
const rows = await page.locator('#hillslopes_watbal tbody tr').count();
if (rows !== 456) throw new Error(`Expected units + 455 hills, got ${rows}`);
const firstRow = await page.locator('#hillslopes_watbal tbody tr').nth(1).locator('td').evaluateAll(cells=>cells.map(cell=>Number(cell.getAttribute('sorttable_customkey'))));
await page.screenshot({path:`${root}/report-browser.png`});
const moduleText = fs.readFileSync('/workdir/wepppy/wepppy/weppcloud/static/js/gl-dashboard/data/wepp-data.js','utf8');
const result = await page.evaluate(async (moduleText) => {
  const {createWeppDataManager} = await import('data:text/javascript;base64,'+btoa(moduleText));
  const state = {weppEventSelectedDate:'2001-01-01',comparisonMode:true,currentScenarioPath:'scenario',baseSummaryCache:{}};
  const payloads = [];
  const scenario = {records:[{topaz_id:101,value:5},{topaz_id:102,value:null}]};
  const baseline = {records:[{topaz_id:101,value:7},{topaz_id:102,value:null}]};
  window.fetch = async (_url,options)=>{payloads.push(JSON.parse(options.body));return {ok:true,json:async()=>baseline};};
  const manager = createWeppDataManager({ctx:{runid:'fixture',config:'cfg'},getState:()=>state,
    setValue:(key,value)=>{state[key]=value;},setState:update=>Object.assign(state,update),
    postQueryEngine:async payload=>{payloads.push(payload);return scenario;},
    pickActiveWeppEventLayer:()=>({mode:'event_ET'}),WEPP_EVENT_WAT_PATH:'H.wat.parquet'});
  await manager.refreshWeppEventData();
  manager.computeWeppEventDiffRanges();
  return {state,payloads};
},moduleText);
if (result.state.weppEventSummary['101'].event_ET !== 5 || result.state.baseSummaryCache.weppEvent['101'].event_ET !== 7 || result.state.comparisonDiffRanges.event_ET.max !== 2) throw new Error('ET scenario/baseline/difference mismatch');
if (result.state.weppEventSummary['102'].event_ET !== null) throw new Error('Unavailable ET became numeric');
fs.writeFileSync(`${root}/browser-receipt.json`,JSON.stringify({reportDataRows:rows-1,firstRow,...result},null,2));
await browser.close();
console.log(JSON.stringify({reportDataRows:rows-1,firstRow,scenarioET:5,baselineET:7,difference:2,unavailableET:null}));
