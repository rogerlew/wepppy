const {chromium}=require('/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/playwright');
const fs=require('fs');
const assert=require('assert/strict');
const secrets=Object.fromEntries(fs.readFileSync('/workdir/wepppy/docker/secrets/dev-agent.env','utf8').split('\n').filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{let i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1).replace(/^['"]|['"]$/g,'')]}));
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1280,height:1800}});
  page.on('pageerror',e=>console.log('PAGEERROR',e.message));
  await page.goto('https://wc.bearhive.duckdns.org/weppcloud/login');
  await page.locator('input[name=email]').fill(secrets.DEV_AGENT_EMAIL);await page.locator('input[name=password]').fill(secrets.DEV_AGENT_PASSWORD);
  await page.getByRole('button',{name:'Login',exact:true}).click();await page.waitForTimeout(3000);await page.getByRole('button',{name:'Login',exact:true}).click(); await page.waitForURL(url=>!url.pathname.endsWith('/login'),{timeout:20000});
  await page.goto('https://wc.bearhive.duckdns.org/weppcloud/runs/addicted-reservist/config/',{waitUntil:'domcontentloaded',timeout:90000});
  await page.waitForTimeout(5000);
  await page.evaluate(()=>document.querySelector('#postfire_debris_flow_form').scrollIntoView({behavior:'instant',block:'start'}));
  await page.waitForTimeout(1000);
  const cdp=await page.context().newCDPSession(page);
  const shot=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  fs.writeFileSync('/tmp/pfdf-upload-success.png',Buffer.from(shot.data,'base64'));
  console.log('SCREENSHOT_PASS');
 } finally {await browser.close();}
})().catch(error=>{console.error(error.stack);process.exit(1);});
