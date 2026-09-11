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
  const names=['events.parquet','design.parquet','inverse.parquet','manifest.json'];
  const expected=JSON.parse(fs.readFileSync('/tmp/pfdf-public-live.log','utf8').split('HASHES ')[1].split('\n')[0]);
  const labels=await page.locator('a').allTextContents();
  for(const name of names) {
    assert(labels.some(label=>label.trim()===name),'Browser is missing '+name);
    const file=await page.request.get(base+'/download/postfire_debris_flow/'+name);
    assert.equal(file.status(),200);
    const hash=require('crypto').createHash('sha256').update(await file.body()).digest('hex');
    assert.equal(hash,expected[name]);
    console.log('PASS listed and downloaded:',name,hash);
  }
  await page.reload({waitUntil:'domcontentloaded',timeout:60000});
  for(const name of names) assert((await page.locator('a').allTextContents()).some(label=>label.trim()===name));
  console.log('PASS standard browser visibility/download hashes and reload');
 } finally {await browser.close();}
})().catch(error=>{console.error(error.stack);process.exit(1);});
