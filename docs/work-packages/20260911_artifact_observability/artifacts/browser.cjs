const {chromium}=require('/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/playwright');
const fs=require('fs');
const assert=require('assert/strict');
const secrets=Object.fromEntries(fs.readFileSync('/workdir/wepppy/docker/secrets/dev-agent.env','utf8').split('\n').filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{let i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1).replace(/^['"]|['"]$/g,'')]}));
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1280,height:1800}});
  page.on('pageerror',e=>console.log('PAGEERROR',e.message));
  console.log('Login');
  await page.goto('https://wc.bearhive.duckdns.org/weppcloud/login');
  await page.locator('input[name=email]').fill(secrets.DEV_AGENT_EMAIL);await page.locator('input[name=password]').fill(secrets.DEV_AGENT_PASSWORD);
  await page.getByRole('button',{name:'Login',exact:true}).click();await page.waitForTimeout(3000);await page.getByRole('button',{name:'Login',exact:true}).click(); await page.waitForURL(url=>!url.pathname.endsWith('/login'),{timeout:20000});
  const base='https://wc.bearhive.duckdns.org/weppcloud/runs/addicted-reservist/config';
  const response=await page.goto(base+'/browse/postfire_debris_flow/',{waitUntil:'domcontentloaded',timeout:60000});
  assert.equal(response.status(),200);
  const rootNames=['events.parquet','design.parquet','inverse.parquet','manifest.json'];
  const upload='attempts/fe868e880df6428697f0f45965783061/';
  const run='attempts/88d613bedab2464b84f752929b86d43c/';
  const expected=JSON.parse(fs.readFileSync('/tmp/artifact-live.log','utf8').split('HASHES ')[1].split('\n')[0]);
  const source=Object.keys(expected).find(name=>name.startsWith('attempts/')&&name.includes('/source/')&&name.endsWith('.img'));
  const summary=Object.keys(expected).find(name=>name.startsWith('attempts/')&&name.endsWith('wbt/summary.json'));
  const prepared=Object.keys(expected).find(name=>name.startsWith('attempts/')&&name.includes('/predictors/')&&name.endsWith('.tif'));
  const historical=Object.keys(expected).find(name=>name.startsWith('attempts/')&&!name.startsWith(upload)&&!name.startsWith(run)&&name.endsWith('/status.json'));
  const names=[...rootNames,source,summary,prepared,historical,upload+'normalized/manifest.json',run+'status.json'];
  assert(names.every(Boolean));
  const labels=await page.locator('a').allTextContents();
  for(const name of names) {
    const parent=name.includes('/')?name.slice(0,name.lastIndexOf('/')+1):'';
    const listing=await page.goto(base+'/browse/postfire_debris_flow/'+parent,{waitUntil:'domcontentloaded',timeout:60000});
    assert.equal(listing.status(),200);
    assert((await page.locator('a').allTextContents()).some(label=>label.trim()===name.split('/').pop()),'Browser is missing '+name);
    const file=await page.request.get(base+'/download/postfire_debris_flow/'+name);
    assert.equal(file.status(),200);
    const hash=require('crypto').createHash('sha256').update(await file.body()).digest('hex');
    assert.equal(hash,expected[name]);
    console.log('PASS listed and downloaded:',name,hash);
  }
  await page.goto(base+'/browse/postfire_debris_flow/',{waitUntil:'domcontentloaded',timeout:60000});
  await page.reload({waitUntil:'domcontentloaded',timeout:60000});
  for(const name of rootNames) assert((await page.locator('a').allTextContents()).some(label=>label.trim()===name));
  console.log('PASS standard browser sources/intermediates/history/results download hashes and reload');
 } finally {await browser.close();}
})().catch(error=>{console.error(error.stack);process.exit(1);});
