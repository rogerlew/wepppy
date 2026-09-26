// Rendered-control smoke, not authenticated full-page transport acceptance.
const fs = require('node:fs');
const { chromium } = require('/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/@playwright/test');
(async () => {
  const root = '/workdir/wepppy/wepppy/weppcloud/static/';
  const browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1100, height: 1000}});
  const css = ['vendor/purecss/pure-min.css', 'css/ui-foundation.css', 'css/themes/all-themes.css']
    .map(path => fs.readFileSync(root + path, 'utf8')).join('\n');
  await page.setContent('<!doctype html><html><head><style>' + css + '</style></head><body>' +
    fs.readFileSync('/tmp/single-input-controls.html', 'utf8') + '</body></html>');
  const results = [];
  for (const theme of ['default', 'ayu-mirage', 'light-high-contrast']) {
    await page.evaluate(theme => document.documentElement.setAttribute('data-theme', theme), theme);
    for (const [kind, ext] of [['landuse', 'MAN'], ['soil', 'SOL']]) {
      const input = page.locator('#input_upload_single_' + kind);
      if (!(await input.isVisible())) throw new Error(kind + ' chooser hidden');
      await page.evaluate(() => { document.body.tabIndex = -1; document.body.focus(); });
      let reached = false;
      for (let step = 0; step < 100; step++) {
        await page.keyboard.press("Tab");
        if (await input.evaluate(el => el === document.activeElement)) { reached = true; break; }
      }
      if (!reached) throw new Error(kind + " chooser unreachable by Tab");
      if (!(await input.evaluate(el => el === document.activeElement))) throw new Error('focus unavailable');
      await input.setInputFiles({name: 'Replacement.' + ext, mimeType: 'text/plain', buffer: Buffer.from('test selection')});
      const filename = page.locator('#' + kind + '_source_filename');
      if ((await filename.textContent()) !== 'Acceptance.' + ext) throw new Error('accepted filename changed before submission');
      if (!(await filename.isVisible())) throw new Error('accepted filename hidden');
      const feedback = await filename.evaluate(el => ({
        code: el.tagName, display: el.parentElement.className,
        color: getComputedStyle(el).color, background: getComputedStyle(el.parentElement).backgroundColor
      }));
      if (feedback.display !== 'wc-text-display') throw new Error('SBS feedback hierarchy mismatch');
      results.push({theme, kind, chooser_visible: true, focusable: true, keyboard_tab_reachable: true, accepted_filename_preserved: true, feedback});
    }
  }
  fs.writeFileSync('/workdir/wepppy/docs/work-packages/20260925_single_user_defined_landuse_soils/artifacts/20260926_browser_controls.json', JSON.stringify(results, null, 2) + '\n');
  await browser.close();
  console.log('Rendered Pure controls passed in Chromium across three themes.');
})().catch(error => { console.error(error); process.exit(1); });
