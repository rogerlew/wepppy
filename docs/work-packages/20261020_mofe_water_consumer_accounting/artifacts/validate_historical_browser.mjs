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
 const checks=[];
 for (const view of ['ash','ash_contaminant']) {
   const url = `${base}/weppcloud/runs/mofe-water-history-20261020/${config}/report/${view}`;
   const response=await page.goto(url,{waitUntil:'domcontentloaded'});
   fs.writeFileSync(`${out}/historical-${view}.html`,await page.content());
   if (response.status()!==200) throw new Error(`Historical ${view}: ${response.status()}`);
   const warning=await page.locator('[role="status"]').filter({hasText:'Historical ash results'}).innerText();
   if (!warning.includes('unverified or stale')) throw new Error('Missing historical warning');
   checks.push({view,status:response.status(),warning});
 }
 fs.writeFileSync(`${out}/historical-browser-receipt.json`,JSON.stringify(checks,null,2));
 console.log(JSON.stringify(checks));
} finally { await browser.close(); }
