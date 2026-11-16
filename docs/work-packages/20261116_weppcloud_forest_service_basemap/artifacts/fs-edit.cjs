const {chromium}=require(require('path').resolve(process.cwd(), 'wepppy/weppcloud/static-src/node_modules/playwright'));
const fs=require('fs'),assert=require('assert/strict'),{createHash}=require('node:crypto');
const forwardedProtoHeader={};
function fnv32aHash(text) {
  let value = 2166136261;
  for (const char of text) {
    value ^= char.codePointAt(0);
    value = (value + (value << 1) + (value << 4) + (value << 7) + (value << 8) + (value << 24)) >>> 0;
  }
  return value >>> 0;
}

function capExpandHex(seed, length) {
  let state = fnv32aHash(seed);

  function nextU32() {
    state ^= (state << 13) >>> 0;
    state ^= state >>> 17;
    state ^= (state << 5) >>> 0;
    state >>>= 0;
    return state;
  }

  let out = '';
  while (out.length < length) {
    out += nextU32().toString(16).padStart(8, '0');
  }
  return out.slice(0, length);
}

function buildCapPairs(challengePayload) {
  const token = String(challengePayload && challengePayload.token ? challengePayload.token : '').trim();
  const challenge = challengePayload && challengePayload.challenge;
  if (!token || !challenge || typeof challenge !== 'object') {
    throw new Error(`Unexpected CAP challenge payload: ${JSON.stringify(challengePayload).slice(0, 240)}`);
  }

  const count = Number(challenge.c || 0);
  const saltLength = Number(challenge.s || 0);
  const targetLength = Number(challenge.d || 0);
  if (!Number.isInteger(count) || !Number.isInteger(saltLength) || !Number.isInteger(targetLength)
      || count <= 0 || saltLength <= 0 || targetLength <= 0) {
    throw new Error(`Invalid CAP challenge dimensions: ${JSON.stringify(challenge)}`);
  }

  const pairs = [];
  for (let idx = 1; idx <= count; idx += 1) {
    pairs.push([
      capExpandHex(`${token}${idx}`, saltLength),
      capExpandHex(`${token}${idx}d`, targetLength),
    ]);
  }
  return { token, pairs };
}

function solvePowNonce(salt, targetHex) {
  let nonce = 0;
  while (true) {
    const digestHex = createHash('sha256').update(`${salt}${nonce}`, 'utf8').digest('hex');
    if (digestHex.startsWith(targetHex)) {
      return nonce;
    }
    nonce += 1;
  }
}

async function solveCapTokenFromEndpoint(page, endpoint) {
  const endpointUrl = new URL(endpoint, page.url());
  const challengeUrl = new URL('challenge', endpointUrl).toString();
  const redeemUrl = new URL('redeem', endpointUrl).toString();

  const challengeResponse = await page.request.post(challengeUrl, { headers: forwardedProtoHeader });
  if (!challengeResponse.ok()) {
    throw new Error(`CAP challenge failed: ${challengeResponse.status()} ${challengeResponse.statusText()}`);
  }
  const challengePayload = await challengeResponse.json();
  const { token, pairs } = buildCapPairs(challengePayload);
  const solutions = pairs.map(([salt, targetHex]) => solvePowNonce(salt, targetHex));

  const redeemResponse = await page.request.post(redeemUrl, {
    headers: forwardedProtoHeader,
    data: { token, solutions },
  });
  if (!redeemResponse.ok()) {
    throw new Error(`CAP redeem failed: ${redeemResponse.status()} ${redeemResponse.statusText()}`);
  }
  const redeemPayload = await redeemResponse.json();
  const capToken = String(redeemPayload && redeemPayload.token ? redeemPayload.token : '').trim();
  if (!capToken || !redeemPayload.success) {
    throw new Error(`CAP redeem did not return a success token: ${JSON.stringify(redeemPayload).slice(0, 240)}`);
  }
  return capToken;
}

async function completeLoginCapIfPresent(page, loginForm) {
  const capTokenInput = loginForm.locator('input[name="cap_token"]');
  if ((await capTokenInput.count()) === 0) {
    return { verified: true, reason: 'Login form has no CAP token field.' };
  }

  const existingToken = await capTokenInput.first().inputValue().catch(() => '');
  if (existingToken) {
    return { verified: true, reason: 'Login CAP token already present.' };
  }

  const capWidget = loginForm.locator('cap-widget[data-cap-api-endpoint]').first();
  if ((await capWidget.count()) === 0) {
    return { verified: false, reason: 'Login form has CAP token field but no CAP widget endpoint.' };
  }

  try {
    const endpoint = await capWidget.getAttribute('data-cap-api-endpoint');
    if (!endpoint) {
      return { verified: false, reason: 'Login CAP widget endpoint is empty.' };
    }
    const capToken = await solveCapTokenFromEndpoint(page, endpoint);
    await capTokenInput.first().evaluate((input, token) => {
      input.value = token;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }, capToken);
  } catch (err) {
    return {
      verified: false,
      reason: `Login CAP challenge did not produce a token (${err && err.message ? err.message : err}).`,
    };
  }
  return { verified: true, reason: 'Login CAP challenge completed.' };
}


(async()=>{
const b=await chromium.launch({headless:true,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const page=await b.newPage({viewport:{width:1440,height:1000}});
page.setDefaultTimeout(20000);const base='https://forest.tail305ec9.ts.net/weppcloud';const env={};for(const line of fs.readFileSync(require('path').resolve(process.cwd(), 'docker/secrets/dev-agent.env'),'utf8').split('\n')){const i=line.indexOf('=');if(i>0)env[line.slice(0,i).trim()]=line.slice(i+1).trim().replace(/^['"]|['"]$/g,'');}
console.log('login');await page.goto(base+'/login',{waitUntil:'domcontentloaded'});const form=page.locator('form[name="login_user_form"]');await form.locator('[name=email]').fill(env.DEV_AGENT_EMAIL);await form.locator('[name=password]').fill(env.DEV_AGENT_PASSWORD);assert.equal((await completeLoginCapIfPresent(page,form)).verified,true);await form.locator('[type=submit]').click();await page.waitForURL(u=>!u.pathname.endsWith('/login'));console.log('authenticated');
await page.goto(base+'/runs/mipa-awake-20261102/config/',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.MapController&&MapController.getInstance()._deck);
await page.locator('#mapid').scrollIntoViewIfNeeded();await page.locator('.wc-map-layer-control__toggle').click();await page.locator('input[name="wc-map-basemap"][value="forestService"]').check();await page.waitForFunction(()=>document.querySelector('.wc-basemap-credit')?.textContent.includes('USDA'),null,{timeout:60000});
console.log('forest loaded');await page.getByRole('tab',{name:'Modify',exact:true}).click();const toggle=page.locator('[data-landuse-modify-action="toggle-selection"]');await toggle.check();console.log('selection enabled');await page.waitForFunction(()=>window.LanduseModify?.getInstance().glLayer);await page.waitForTimeout(500);
await page.locator('#mapid').scrollIntoViewIfNeeded();const box=await page.locator('#mapid').boundingBox();console.log('box',box);await page.screenshot({path:'/tmp/fs-edit-before.png'});await page.keyboard.down('Shift');await page.mouse.move(box.x+box.width*0.2,box.y+box.height*0.2);await page.mouse.down();await page.mouse.move(box.x+box.width*0.75,box.y+box.height*0.75,{steps:12});await page.mouse.up();await page.keyboard.up('Shift');
console.log('drag complete');await page.waitForFunction(()=>document.querySelector('[data-landuse-modify-field="topaz-ids"]').value.length>0);const ids=await page.locator('[data-landuse-modify-field="topaz-ids"]').inputValue();await page.screenshot({path:'/tmp/fs-edit.png'});console.log('selected count',ids.length);assert(ids.length>0);
const point=await page.evaluate(()=>{const d=MapController.getInstance()._deck,v=d.getViewports()[0],id=LanduseModify.getInstance().glLayer.id;for(let y=v.height*0.35;y<v.height*0.75;y+=35){for(let x=v.width*0.3;x<v.width*0.75;x+=35){const pick=d.pickObject({x,y,layerIds:[id]});if(pick&&pick.object)return {x,y};}}return null;});assert(point);await page.mouse.click(box.x+point.x,box.y+point.y);await page.waitForFunction(previous=>document.querySelector('[data-landuse-modify-field="topaz-ids"]').value!==previous,ids);console.log('pointer click selection passed');
// Local selection only: never submit a landuse mutation to the project.
await toggle.uncheck();console.log('selection cleared');if(await page.locator('.wc-map-layer-control__toggle').getAttribute('aria-expanded')!=='true')await page.locator('.wc-map-layer-control__toggle').click();console.log('base panel open');await page.locator('input[name="wc-map-basemap"][value="googleTerrain"]').check();
fs.writeFileSync('/tmp/fs-edit.json',JSON.stringify({authenticated:true,selectionBox:true,pointerClick:true,selectedIds:ids,submitted:false,recoveredTerrain:true},null,2));console.log('PASS pointer selection without submission');await b.close();
})().catch(e=>{console.error('Pointer selection validation failed:',e.name,'; no credentials logged');process.exit(1)});
