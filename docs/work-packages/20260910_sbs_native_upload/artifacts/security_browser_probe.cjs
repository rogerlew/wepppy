// Independent renderer probe: local about:blank page, no credentials/run mutation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { createHash } = require('node:crypto');
const { chromium } = require('/workdir/wepppy/wepppy/weppcloud/static-src/node_modules/playwright');
const root = '/workdir/wepppy/wepppy/weppcloud/controllers_js/';
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const requests = [], errors = [];
    page.on('request', request => requests.push(request.url()));
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', route => route.abort());
    await page.setContent('<form><div id="info">Accepted result</div><p data-hint></p><details data-stacktrace-panel hidden><div id="stacktrace"></div></details></form>');
    const sourceHashes = {};
    for (const name of ['control_base.js', 'sbs_error.js']) {
      const source = fs.readFileSync(root + name, 'utf8');
      sourceHashes[name] = createHash('sha256').update(source).digest('hex');
      await page.addScriptTag({ content: source });
    }
    const result = await page.evaluate(async () => {
      window.executed = 0;
      customElements.define('x-probe', class extends HTMLElement { constructor() { super(); window.executed++; } });
      customElements.define('p-probe', class extends HTMLParagraphElement { constructor() { super(); window.executed++; } }, { extends: 'p' });
      const target = document.querySelector('#stacktrace');
      const controller = Object.assign(controlBase(), {
        form: document.querySelector('form'), stacktrace: { element: target, text: value => { target.textContent = value; } },
        infoElement: document.querySelector('#info')
      });
      const html = '<h1 id="clobber" onclick="window.executed++" style="color:red">Gateway</h1><p is="p-probe">Readable</p>' +
        '<script>window.executed++</script><script src="https://security.invalid/script"></script><img src="https://security.invalid/image" onerror="window.executed++">' +
        '<link rel="stylesheet" href="https://security.invalid/style"><style>@import "https://security.invalid/css"</style><base href="https://security.invalid/">' +
        '<meta http-equiv="refresh" content="0;url=https://security.invalid/redirect"><iframe src="https://security.invalid/frame" srcdoc="<script>parent.executed++</script>"></iframe>' +
        '<svg><foreignObject><p>Foreign</p></foreignObject><image href="https://security.invalid/svg"></image></svg><math><mtext>Math</mtext></math>' +
        '<form action="https://security.invalid/post"><input autofocus onfocus="window.executed++"></form><x-probe><p>Custom</p></x-probe>' +
        '<table><tr><td onmouseover="window.executed++">Table</td></tr></table><pre>&lt;img src="https://security.invalid/entity"&gt;</pre>';
      const failure = body => ({ body, response: { headers: new Headers({ 'content-type': 'text/html; charset=utf-8' }) } });
      WCSbsError.show(controller, {}, failure(html));
      const clean = [...target.querySelectorAll('*')].every(node => node.attributes.length === 0);
      const safeText = target.textContent;
      const revealed = document.querySelector('details').open && !document.querySelector('details').hidden;
      const forbidden = target.querySelector('script,img,link,style,base,meta,iframe,svg,math,form,input,x-probe');
      const payload = { error: { message: '<h1 onclick="window.executed++">Literal JSON</h1>' } };
      WCSbsError.show(controller, payload, { body: payload, response: { headers: new Headers({ 'content-type': 'application/json' }) } });
      const jsonLiteral = !target.querySelector('h1') && target.textContent.includes('<h1 onclick=');
      WCSbsError.show(controller, {}, failure('<div>'.repeat(10000) + 'Deep' + '</div>'.repeat(10000)));
      const deep = target.textContent === 'Deep';
      WCSbsError.clear(controller);
      WCSbsError.show(controller, {}, failure(html), 'map');
      WCSbsError.show(controller, {}, failure('<p>Summary failed</p>'), 'summary');
      const retained = WCSbsError.clear(controller, 'summary') === false && target.textContent === safeText;
      const recovered = WCSbsError.clear(controller, 'map') === true && target.textContent === '' && document.querySelector('details').hidden;
      await new Promise(resolve => setTimeout(resolve, 250));
      return { executed: window.executed, clean, safeText, revealed, forbidden: !!forbidden, jsonLiteral, deep, retained, recovered,
        summary: document.querySelector('#info').textContent, hint: document.querySelector('[data-hint]').textContent, url: location.href };
    });
    assert.equal(result.executed, 0); assert.equal(result.clean, true); assert.equal(result.forbidden, false);
    assert.equal(result.revealed, true); assert.equal(result.jsonLiteral, true); assert.equal(result.deep, true);
    assert.equal(result.retained, true); assert.equal(result.recovered, true);
    assert.equal(result.summary, 'Accepted result'); assert.equal(result.hint, ''); assert.equal(result.url, 'about:blank');
    assert.equal(result.safeText, 'GatewayReadableTable<img src="https://security.invalid/entity">');
    assert.deepEqual(requests, []); assert.deepEqual(errors, []);
    console.log(JSON.stringify({ passed: true, sourceHashes, chromium: browser.version(), ...result, requests, errors }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
