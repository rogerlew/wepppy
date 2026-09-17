// Read-only saved-report audit with normal agent login. No run mutations.
const {chromium}=require('../../../../wepppy/weppcloud/static-src/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {createHash}=require('crypto');
const runid='thespian-cleanness',config='config';
assert(/^[a-zA-Z0-9_-]+$/.test(runid)&&/^[a-zA-Z0-9_-]+$/.test(config));
const base='https://wc.bearhive.duckdns.org',runBase=`${base}/weppcloud/runs/${runid}/${config}`;
const output=path.join(__dirname,'browser',runid);fs.mkdirSync(output,{recursive:true});
const records=[];function record(value){records.push({utc:new Date().toISOString(),...value});fs.writeFileSync(path.join(output,'evidence.json'),JSON.stringify(records,null,2));console.log(JSON.stringify(value));}
function hash(data){return createHash('sha256').update(data).digest('hex');}
function expand(seed, length) {
    let state = 2166136261;
    for (const char of seed) {
        state ^= char.codePointAt(0);
        state = (state + (state << 1) + (state << 4) + (state << 7) + (state << 8) + (state << 24)) >>> 0;
    }
    let result = '';
    while (result.length < length) {
        state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
        result += (state >>> 0).toString(16).padStart(8, '0');
    }
    return result.slice(0, length);
}
async function solveCap(page) {
    if (!await page.locator('input[name=cap_token]').count()) return;
    const endpoint = await page.locator('cap-widget').getAttribute('data-cap-api-endpoint');
    const url = new URL(endpoint, page.url());
    assert.equal(url.origin, base);
    const response = await page.request.post(new URL('challenge', url).href);
    assert(response.ok());
    const { token, challenge: { c, s, d } } = await response.json();
    const solutions = [];
    for (let i = 1; i <= c; i++) {
        const salt = expand(token + i, s), target = expand(token + i + 'd', d);
        let nonce = 0;
        while (!hash(salt + nonce).startsWith(target)) nonce++;
        solutions.push(nonce);
    }
    const redeemed = await page.request.post(new URL('redeem', url).href, { data: { token, solutions } });
    const result = await redeemed.json();
    assert(result.success && result.token);
    await page.locator('input[name=cap_token]').evaluate((el, value) => {
        el.value = value; el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }, result.token);
}

(async()=>{
 const credentials=Object.fromEntries(fs.readFileSync(path.resolve(__dirname,'../../../../docker/secrets/dev-agent.env'),'utf8').split('\n').filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1).replace(/^['"]|['"]$/g,'')]}));
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  page.on('pageerror',e=>record({page_error:e.message}));
  await page.goto(base+'/weppcloud/login');
  await page.locator('input[name=email]').fill(credentials.DEV_AGENT_EMAIL);
  await page.locator('input[name=password]').fill(credentials.DEV_AGENT_PASSWORD);
  await solveCap(page); await page.locator('input[type=submit],button[type=submit]').first().click();
  await page.waitForURL(u=>!u.pathname.endsWith('/login'));
  const response=await page.goto(runBase+'/browse/climate/?page=3');
  assert.equal(response.status(),200);
  const text=await page.locator('body').innerText();
  fs.writeFileSync(path.join(output,'listing_initial.txt'),text);
  record({stage:'listing',url:page.url(),status:response.status()});
  const files=['daymet_1980-2024.parquet','daymet_radiation_toa_normalization_wepp.csv'];
  for(const name of files){
   assert(text.includes(name));
   const r=await page.request.get(runBase+'/download/climate/'+name);
   assert.equal(r.status(),200);
   const actual=hash(fs.readFileSync('/wc1/runs/th/thespian-cleanness/climate/'+name));
   assert.equal(hash(await r.body()),actual);
   record({stage:'visible-download',name,status:r.status(),sha256:actual});
  }
  fs.writeFileSync(path.join(output,'visible_text.txt'),text);
  await page.screenshot({path:path.join(output,'climate.png'),fullPage:true});
 } finally {await browser.close();}
})().catch(e=>{record({error:e.message});process.exitCode=1;});
