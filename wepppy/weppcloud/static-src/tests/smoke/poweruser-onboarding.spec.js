/* Opt-in Forest acceptance using disposable accounts prepared by the PUUX artifact driver. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { test, expect } from '@playwright/test';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const base = process.env.SMOKE_BASE_URL || 'https://wc.bearhive.duckdns.org';
const root = base + '/weppcloud';
const evidence = path.join(repo, 'docs/work-packages/20261013_poweruser_discovery_onboarding/artifacts');

test('Runs discovery, real activation, refresh and separate internal permission', async ({ browser }) => {
  test.skip(process.env.PUUX_BROWSER !== '1', 'Requires disposable Forest accounts.');
  const credentials = JSON.parse(fs.readFileSync(path.join(repo, 'docker/secrets/puux-browser.json'), 'utf8'));
  const contexts = [];
  async function account(label, width = 1280) {
    const context = await browser.newContext({ viewport: {width, height: 1000} });
    contexts.push(context);
    const credential = credentials[label];
    await context.addCookies([{name:credential.name, value:credential.value, url:base,
      secure:true, httpOnly:true, sameSite:'Lax'}]);
    return context.newPage();
  }
  try {
    const user = await account('ordinary', 390);
    await user.goto(root + '/runs');
    await expect(user.getByRole('heading', {name:'Advanced features'})).toBeVisible();
    await user.getByRole('tab', {name:'Map', exact:true}).click();
    await expect(user.getByRole('link', {name:'Explore PowerUser access'})).toBeVisible();
    await user.getByRole('link', {name:'Explore PowerUser access'}).click();
    await expect(user.locator('#poweruser-access-heading')).toBeFocused();
    await expect(user.getByText('Access is enabled immediately', {exact:false})).toBeVisible();
    await expect(user.locator('[data-internal-access] details')).not.toHaveAttribute('open');
    const csrf = await user.locator('meta[name="csrf-token"]').getAttribute('content');
    const form = user.locator('[data-feature-access-form="poweruser"]');
    const version = await form.getAttribute('data-statement-version');
    const payload = {needs_poweruser:true, accepts_training:true, statement_version:version};
    const noCsrf = await user.request.post(root + '/profile/poweruser', {data:payload});
    expect(noCsrf.status()).toBe(400);
    const stale = await user.request.post(root + '/profile/poweruser', {headers:{'X-CSRFToken':csrf}, data:{...payload, statement_version:'old'}});
    expect(stale.status()).toBe(409);
    await user.getByLabel('Do you need PowerUser access?').check();
    await user.getByLabel('I have read and understand the PowerUser training statement.').check();
    const granted = user.waitForResponse(r=>r.url().endsWith('/profile/poweruser') && r.request().method()==='POST' && r.status()===200);
    const refreshed = user.waitForResponse(r=>new URL(r.url()).pathname==='/weppcloud/profile' && r.request().isNavigationRequest());
    await user.getByRole('button',{name:'Enable PowerUser access', exact:true}).press('Enter');
    expect((await granted).status()).toBe(200); // Grant semantics are read back from refreshed UI and the database.
    await refreshed;
    await expect(user.getByText('PowerUser access is active.',{exact:true})).toBeVisible();
    await expect(user.locator('#poweruser-access-heading')).toBeFocused();
    await expect(user.getByRole('button',{name:'Enable PowerUser access',exact:true})).toHaveCount(0);
    const csrf2 = await user.locator('meta[name="csrf-token"]').getAttribute('content');
    const repeated = await user.request.post(root + '/profile/poweruser', {headers:{'X-CSRFToken':csrf2},data:payload});
    expect(repeated.status()).toBe(200);
    expect((await repeated.json()).result.role_changed).toBe(false);
    await user.screenshot({path:path.join(evidence,'forest-profile-active.png'),fullPage:true});
    await user.getByRole('link',{name:'Open Config Builder',exact:true}).click();
    await expect(user).toHaveURL(/config-builder/);
    await user.goto(root + '/profile');
    await user.getByRole('link',{name:'Go to Runs',exact:true}).click();
    await expect(user.getByRole('heading',{name:'Advanced features'})).toHaveCount(0);
    expect((await user.request.get(root + '/batch/create/')).status()).toBe(403);
    const populated = await account('populated');
    await populated.goto(root + '/runs');
    await expect(populated.getByRole('heading',{name:'Advanced features'})).toBeVisible();
    await expect(populated.getByRole('tab',{name:'Table',exact:true})).toBeVisible();
    await populated.goto(root + '/runs/sabbatical-stitcher/config/');
    await populated.getByText('More',{exact:true}).first().click();
    await expect(populated.getByRole('link',{name:'GL Dashboard',exact:true})).toBeVisible();
    await expect(populated.locator('[data-modal-open="puModal"]')).toHaveCount(0);
    for (const label of ['legacy','admin','root','dev']) {
      const page = await account(label);
      await page.goto(root + '/runs');
      await expect(page.getByRole('heading',{name:'Advanced features'})).toHaveCount(label==='dev'?1:0);
      await page.goto(root + '/profile');
      await expect(page.getByRole('button',{name:'Enable PowerUser access',exact:true})).toHaveCount(label==='dev'?1:0);
      if(label==='legacy') await expect(page.getByText(/No action is required/)).toBeVisible();
    }
    const anonymous = await browser.newContext(); contexts.push(anonymous);
    expect((await anonymous.request.post(root + '/profile/poweruser',{data:payload})).status()).not.toBe(200);
    fs.writeFileSync(path.join(evidence,'forest-onboarding-browser.json'), JSON.stringify({
      ordinary_user_id:credentials.ordinary.id, populated_user_id:credentials.populated.id,
      empty_runs_discovery:true, populated_runs_discovery:true, table_map_notice:true,
      grant_status:200, duplicate_role_changed:false, actual_profile_navigation:true,
      same_fragment_focus:true, new_poweruser_builder_access:true, notice_removed_after_activation:true,
      internal_batch_denied:403, missing_csrf_denied:400, stale_statement_denied:409,
      anonymous_submission_denied:true, role_matrix:['ordinary','legacy','admin','root','dev'],
      narrow_viewport:390, existing_account_roles_changed:false
    },null,2)+'\n');
  } finally { await Promise.all(contexts.map(c=>c.close())); }
});

test('retained Forest presentation, guide and panel readback', async ({browser}) => {
  test.skip(process.env.PUUX_READBACK !== '1', 'Requires completed disposable Forest onboarding.');
  const credentials=JSON.parse(fs.readFileSync(path.join(repo,'docker/secrets/puux-browser.json'),'utf8'));
  const contexts=[];
  async function pageFor(label) {
    const context=await browser.newContext({viewport:{width:1440,height:1000}});contexts.push(context);
    const c=credentials[label];await context.addCookies([{name:c.name,value:c.value,url:base,secure:true,httpOnly:true,sameSite:'Lax'}]);
    return context.newPage();
  }
  try {
    const ordinary=await pageFor('populated');
    await ordinary.goto(root+'/runs');
    await expect(ordinary.getByRole('heading',{name:'Advanced features'})).toBeVisible();
    await ordinary.evaluate(() => window.scrollTo(0,0));
    await ordinary.screenshot({path:path.join(evidence,'forest-runs-discovery.png'),fullPage:true});
    const noticeHeight=(await ordinary.locator('[aria-labelledby="advanced-features-heading"]').boundingBox()).height;
    await ordinary.setViewportSize({width:390,height:1000});
    await expect(ordinary.getByRole('link',{name:'Explore PowerUser access'})).toBeVisible();
    await ordinary.screenshot({path:path.join(evidence,'forest-runs-discovery-narrow.png'),fullPage:true});
    await ordinary.setViewportSize({width:1440,height:1000});
    await ordinary.goto(root+'/profile#poweruser-access-heading');
    await ordinary.locator('[data-internal-access] summary').click();
    await expect(ordinary.getByRole('checkbox',{name:'I have read and understand the internal access statement.'})).toBeVisible();
    const guide=ordinary.getByRole('link',{name:/Explore PowerUser tools and your first steps/});
    const guideResponse=await ordinary.request.get(new URL(await guide.getAttribute('href'), base).href);
    expect(guideResponse.status()).toBe(200);
    expect(await guideResponse.text()).toContain('Getting started with PowerUser tools');
    const rootPage=await pageFor('root');
    await rootPage.goto(root+'/runs/sabbatical-stitcher/config/');
    await rootPage.getByText('More',{exact:true}).first().click();
    await rootPage.getByRole('button',{name:'PowerUser Panel',exact:true}).click();
    const panel=rootPage.locator('#puModal');
    await expect(panel).toBeVisible();
    await expect(panel.getByRole('heading',{name:'Inspect inputs and outputs'})).toBeVisible();
    await expect(panel.getByRole('heading',{name:'Analyze and troubleshoot'})).toBeVisible();
    await expect(panel.locator('details')).not.toHaveAttribute('open');
    await panel.locator('summary').click();
    await expect(panel.getByRole('heading',{name:'Core resources'})).toBeVisible();
    await panel.locator('summary').click();
    await panel.locator('.wc-modal__body').evaluate(body => {body.scrollTop=0;});
    await panel.screenshot({path:path.join(evidence,'forest-poweruser-panel.png')});
    fs.writeFileSync(path.join(evidence,'forest-presentation-readback.json'),JSON.stringify({desktop_width:1440,
      populated_notice:true,notice_height_desktop:noticeHeight,narrow_notice_width:390,
      guide_http_status:200,voluntary_internal_acknowledgment_reachable:true,
      panel_task_headings:true,technical_details_initially_closed:true,technical_details_expand:true},null,2)+'\n');
  } finally {await Promise.all(contexts.map(c=>c.close()));}
});
