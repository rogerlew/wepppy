// Run from repository root after render_ui_preview.py; synthetic local pages only.
const { chromium } = require('../../../../wepppy/weppcloud/static-src/node_modules/playwright');
const fs = require('fs/promises');
const path = require('path');
(async () => {
  const root=process.cwd();
  const browser=await chromium.launch({headless:true, executablePath:process.env.CILOGON_PREVIEW_CHROMIUM});
  const page=await browser.newPage();
  await page.route('**/*',async route=>{
    const url=new URL(route.request().url());
    let file;
    if(url.pathname.startsWith('/static/')) file=path.join(root,'wepppy/weppcloud',url.pathname);
    else if(url.pathname.endsWith('.html')) file=path.join(root,'.cilogon-ui-preview',path.basename(url.pathname));
    if(!file) return route.abort();
    try { await route.fulfill({path:file}); } catch { await route.abort(); }
  });
  const results=[];
  for(const width of [320,375,1280]) {
    await page.setViewportSize({width,height:900});
    for(const name of ['login','profile-shared','profile-cilogon']) {
      await page.goto('http://preview.test/'+name+'.html');
      await page.waitForLoadState('networkidle');
      const sizes=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
      if(sizes.document>width) console.log(await page.evaluate(()=>Array.from(document.querySelectorAll('*')).filter(e=>e.getBoundingClientRect().right>innerWidth).map(e=>[e.tagName,e.className,e.getBoundingClientRect().width]).slice(-20)));
      if(sizes.document>width) throw new Error(`${name} overflows ${width}: ${JSON.stringify(sizes)}`);
      if(name==='login') {
        await page.getByRole('heading',{name:'CILogon — university or organization sign-in'}).waitFor();
        if(!await page.getByText('Use the same email address to access the same WEPPcloud account and projects.').isVisible()) throw new Error('Missing shared copy');
      } else {
        await page.getByRole('heading',{name:'Email Verification'}).waitFor();
        await page.getByRole('button',{name:'Send verification email'}).waitFor();
      }
      if(width===375 || width===1280) await page.screenshot({path:path.join(root,'docs/work-packages/20261117_cilogon_oidc/artifacts',`${name}-${width}.png`),fullPage:true});
      results.push({page:name,width,...sizes});
    }
  }
  await fs.writeFile(path.join(root,'docs/work-packages/20261117_cilogon_oidc/artifacts/ui-layout-results.json'),JSON.stringify(results,null,2)+'\n');
  await browser.close();
  console.log(JSON.stringify(results));
})().catch(error=>{console.error(error);process.exit(1);});
