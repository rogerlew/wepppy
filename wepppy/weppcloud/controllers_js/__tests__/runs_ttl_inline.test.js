/** @jest-environment jsdom */
/* eslint-env node */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const template = fs.readFileSync(path.resolve(__dirname, '../../templates/user/runs2.html'), 'utf8');
const rawScript = template.match(/<script>([\s\S]*?)<\/script>/)[1];
const response = (body, ok = true) => ({ ok, json: async () => body });
const protectedTtl = { user_disabled: true, policy: 'disabled', delete_state: 'active' };
const success = (ttl = protectedTtl) => response({ Content: { ttl_disabled: true, ttl } });
const run = (runid, date = '2026-11-05T00:00:00Z') => ({ runid, config: 'cfg value', ttl_deletion_at: date, ttl_disabled: false });
async function flush() { for (let n = 0; n < 30; n += 1) await Promise.resolve(); }
async function initialize(rows, post, direction = 'asc') {
    document.head.innerHTML = '<meta name="csrf-token" content="csrf-test">';
    document.body.innerHTML = `<button id="delete_runs_button"></button><button id="disable_ttl_runs_button" disabled></button>
      <div id="runs-ttl-status"></div><div id="runs-delete-status"></div><div id="runs_catalog_status"></div>
      <table id="runs_table"><tbody id="runs_table_body"><tr id="runs_empty_row"><td></td></tr></tbody></table>
      <nav id="runs-pagination"></nav>`;
    const values = { site_prefix: '/weppcloud', show_owner: false, is_admin_runs_viewer: false,
        current_user_alias: '7', selected_alias: '', sort: 'ttl_deletion_at', direction, per_page: 25 };
    const script = rawScript.replace(/{{\s*([\s\S]*?)\s*}}/g, (_, expr) => {
        if (expr.startsWith('url_for')) return JSON.stringify('/' + expr.match(/'([^']+)'/)[1]);
        const key = expr.split('|')[0].trim();
        if (!(key in values)) throw new Error('Unknown template input ' + key);
        return JSON.stringify(values[key]);
    });
    const fetch = jest.fn((url, options) => options?.method === 'POST' ? post(url, options) : Promise.resolve(response({ runs: rows })));
    const context = { document, window, URL, URLSearchParams, Node, fetch, console };
    vm.createContext(context);
    vm.runInContext(script, context);
    await flush();
    return { context, fetch, button: document.getElementById('disable_ttl_runs_button') };
}
function select(...ids) {
    document.querySelectorAll('input[type="checkbox"]').forEach(box => {
        box.checked = ids.includes(box.value);
        box.dispatchEvent(new Event('change'));
    });
}
function status() { return document.getElementById('runs-ttl-status').textContent; }

test('selected requests use existing setter, CSRF and encoded prefixed URL; successful rows move last', async () => {
    const { fetch, button } = await initialize([run('first/run'), run('later')], async () => success());
    expect(button.disabled).toBe(true);
    select('first/run');
    expect(button.disabled).toBe(false);
    button.click();
    expect(button.disabled).toBe(true);
    await flush();
    const posts = fetch.mock.calls.filter(([, options]) => options?.method === 'POST');
    expect(posts).toHaveLength(1);
    expect(posts[0][0]).toBe('/weppcloud/runs/first%2Frun/cfg%20value/tasks/set_ttl_disabled');
    expect(posts[0][1]).toMatchObject({ credentials: 'same-origin', body: '{"ttl_disabled":true}', headers: { 'X-CSRFToken': 'csrf-test', 'Content-Type': 'application/json' } });
    expect(Array.from(document.querySelectorAll('tr[data-run-row]')).map(row => row.id)).toEqual(['later', 'first/run']);
    expect(document.getElementById('first/run').textContent).toContain('Automatic deletion is disabled');
    expect(status()).toContain('1 of 1');
    expect(button.disabled).toBe(true);
});

test('partial failures retain selected failed rows, report text safely, and permit retry', async () => {
    let fail = true;
    const { button } = await initialize([run('ok'), run('<bad>')], async url => url.includes('%3Cbad%3E') && fail ? response({ error: { message: '<img src=x>' } }, false) : success());
    select('ok', '<bad>');
    button.click();
    await flush();
    expect(status()).toContain('1 of 2');
    expect(status()).toContain('<bad>');
    expect(document.querySelector('#runs-ttl-status img')).toBeNull();
    expect(Array.from(document.querySelectorAll('input:checked')).map(box => box.value)).toEqual(['<bad>']);
    expect(button.disabled).toBe(false);
    fail = false;
    button.click();
    await flush();
    expect(document.getElementById('<bad>').textContent).toContain('Automatic deletion is disabled');
});

test.each([null, { ...protectedTtl, delete_state: 'queued' }, { ...protectedTtl, delete_state: 'trash' }, { ...protectedTtl, delete_state: 'purged' }, { ...protectedTtl, user_disabled: false }])('unconfirmed protection is never presented as success: %j', async ttl => {
    const { button } = await initialize([run('uncertain')], async () => success(ttl));
    select('uncertain');
    button.click();
    await flush();
    expect(status()).toContain('0 of 1');
    expect(document.getElementById('uncertain').textContent).toContain('Automatic deletion is enabled');
    expect(button.disabled).toBe(false);
});

test('existing batch exclusion confirms protection', async () => {
    const { button } = await initialize([run('batch')], async () => success({ policy: 'excluded', disabled_reason: 'batch', delete_state: 'active', user_disabled: false }));
    select('batch');
    button.click();
    await flush();
    expect(status()).toContain('1 of 1');
});

test('scope reload during request cannot overwrite new rows', async () => {
    let resolvePost;
    const { context, fetch, button } = await initialize([run('shared')], () => new Promise(resolve => { resolvePost = resolve; }));
    select('shared');
    button.click();
    fetch.mockImplementation(async () => response({ runs: [run('shared')] }));
    context.reloadRunsForScope();
    await flush();
    resolvePost(success());
    await flush();
    expect(document.getElementById('shared').textContent).toContain('Automatic deletion is enabled');
});

test.each(['network', 'json', 'csrf', 'empty'])('transport failure remains retryable: %s', async kind => {
    const { button } = await initialize([run('retry')], async () => {
        if (kind === 'network') throw new Error('Network unavailable');
        if (kind === 'json') return { ok: true, json: async () => { throw new Error('Invalid JSON'); } };
        if (kind === 'csrf') return response({ error: { message: 'CSRF token expired' } }, false);
        return response({});
    });
    select('retry');
    button.click();
    await flush();
    expect(status()).toContain('0 of 1');
    expect(button.disabled).toBe(false);
});

test('empty catalogs and readonly rows cannot issue bulk requests', async () => {
    let result = await initialize([], async () => success());
    result.button.click();
    expect(result.fetch.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(0);
    result = await initialize([{ ...run('readonly'), readonly: true }], async () => success());
    expect(document.querySelector('input[type="checkbox"]').disabled).toBe(true);
    expect(result.button.disabled).toBe(true);
});

test('an obsolete catalog error cannot replace the newer scope or retain its selection', async () => {
    const { context, fetch, button } = await initialize([run('old')], async () => success());
    select('old');
    let rejectOld;
    fetch.mockImplementationOnce(() => new Promise((resolve, reject) => { rejectOld = reject; }));
    context.reloadRunsForScope();
    expect(button.disabled).toBe(true);
    expect(document.getElementById('old')).toBeNull();
    fetch.mockImplementationOnce(async () => response({ runs: [run('new')] }));
    context.reloadRunsForScope();
    await flush();
    rejectOld(new Error('Old scope unavailable'));
    await flush();
    expect(document.getElementById('new')).not.toBeNull();
    expect(document.getElementById('runs_empty_row').hidden).toBe(true);
});

test('search after a failed scope load cannot resurrect prior scope selections', async () => {
    const { context, fetch, button } = await initialize([run('old')], async () => success());
    select('old');
    const errorLog = jest.spyOn(console, 'error').mockImplementation(() => {});
    fetch.mockImplementationOnce(async () => { throw new Error('Scope unavailable'); });
    try {
        context.reloadRunsForScope();
        await flush();
        context.applyRunsFilter();
        expect(document.querySelectorAll('tr[data-run-row]')).toHaveLength(0);
        expect(button.disabled).toBe(true);
    } finally {
        errorLog.mockRestore();
    }
});


test.each(['asc', 'desc'])('bulk protection keeps unknown rows before all disabled rows: %s', async direction => {
    const rows = [run('protect'), { ...run('disabled', null), ttl_disabled: true }, run('unknown', null)];
    const { button } = await initialize(rows, async () => success(), direction);
    select('protect');
    button.click();
    await flush();
    expect(Array.from(document.querySelectorAll('tr[data-run-row]')).map(row => row.id)).toEqual(['unknown', 'protect', 'disabled']);
});
