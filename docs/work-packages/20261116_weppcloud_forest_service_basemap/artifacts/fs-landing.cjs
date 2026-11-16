const {chromium}=require(require('path').resolve(process.cwd(), 'wepppy/weppcloud/static-src/node_modules/playwright'));
const fs=require('fs'),assert=require('assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const page=await browser.newPage({viewport:{width:1280,height:900}});const receipt=[];
const base='https://forest.tail305ec9.ts.net/weppcloud';
for(const variant of ['light','dark']) {
 await page.goto(base+'/landing/'+variant+'/',{waitUntil:'domcontentloaded'});
 const credit=page.locator('[data-forest-service-credit]');await credit.waitFor();await credit.scrollIntoViewIfNeeded();
 const summary=credit.locator('summary');await summary.focus();await page.keyboard.press('Enter');
 assert.equal(await credit.locator('details').getAttribute('open'),'');
 assert.match(await credit.innerText(),/Motor Vehicle Use Maps/);assert.match(await credit.innerText(),/unsuitable for navigation/);
 await page.waitForFunction(()=>document.querySelector('[data-forest-service-credit]').checkVisibility({opacityProperty:true}));await page.waitForTimeout(1000);
 await page.screenshot({path:'/tmp/fs-landing-'+variant+'.png'});
 receipt.push({variant,url:page.url(),credit:await credit.innerText(),keyboard:true,buildScripts:await page.locator('script[src]').evaluateAll(es=>es.map(e=>e.src))});
}
fs.writeFileSync('/tmp/fs-landing.json',JSON.stringify(receipt,null,2));console.log('PASS landing variants');await browser.close();})().catch(e=>{console.error(e);process.exit(1)});
