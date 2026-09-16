// Read-only report acceptance. No model/selection/source endpoints are invoked.
const { chromium } = require('../../../../wepppy/weppcloud/static-src/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const { createHash } = require('crypto');
const [runid, output, config = 'config'] = process.argv.slice(2);
assert(/^[a-zA-Z0-9_-]+$/.test(runid || '') && output);
const base = 'https://wc.bearhive.duckdns.org';
assert(/^[a-zA-Z0-9_-]+$/.test(config));
const runBase = `${base}/weppcloud/runs/${runid}/${config}`;
const root = `/wc1/runs/${runid.slice(0, 2)}/${runid}`;
const log = [];
let stage = 'setup';
fs.mkdirSync(output, { recursive: true });
function record(data) {
    const row = { utc: new Date().toISOString(), stage, ...data };
    log.push(row);
    fs.writeFileSync(path.join(output, 'browser.json'), JSON.stringify(log, null, 2));
    console.log(JSON.stringify(row));
}
function hash(data) { return createHash('sha256').update(data).digest('hex'); }
function snapshots() {
    const files = fs.readdirSync(root).filter(name => name.endsWith('.nodb') || name === 'redisprep.dump');
    for (const name of fs.readdirSync(path.join(root, 'postfire_debris_flow'))) {
        if (fs.statSync(path.join(root, 'postfire_debris_flow', name)).isFile()) {
            files.push('postfire_debris_flow/' + name);
        }
    }
    return Object.fromEntries(files.sort().map(name => [name, hash(fs.readFileSync(path.join(root, name)))]));
}
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
(async () => {
    const secretFile = path.resolve(__dirname, '../../../../docker/secrets/dev-agent.env');
    const credentials = Object.fromEntries(fs.readFileSync(secretFile, 'utf8').split('\n')
        .filter(line => line.includes('=') && !line.startsWith('#')).map(line => {
            const index = line.indexOf('=');
            return [line.slice(0, index), line.slice(index + 1).replace(/^['"]|['"]$/g, '')];
        }));
    const before = snapshots();
    const browser = await chromium.launch({ headless: true });
    try {
        const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, acceptDownloads: true });
        const errors = [], mutations = [], recorderRequests = [];
        page.on('pageerror', () => errors.push(stage));
        page.on('response', async response => {
            if (response.url().includes('/query/postfire_debris_flow/')) {
                record({ path: new URL(response.url()).pathname, status: response.status() });
                const content = await response.json().catch(() => null);
                record({ response_keys: content ? Object.keys(content) : [],
                    response_row_count: content && Array.isArray(content.rows) ? content.rows.length : null });
            }
        });
        page.on('request', request => {
            if (request.url().includes(`/runs/${runid}/`) && !['GET', 'HEAD', 'OPTIONS'].includes(request.method())) {
                const requestPath = new URL(request.url()).pathname;
                if (requestPath === `/weppcloud/runs/${runid}/${config}/recorder/events`) {
                    recorderRequests.push(requestPath);
                } else {
                    mutations.push(requestPath);
                }
            }
        });
        stage = 'login';
        await page.goto(base + '/weppcloud/login');
        assert.equal(new URL(page.url()).origin, base);
        assert.equal(new URL(await page.locator('input[name=password]').evaluate(el => el.form.action)).origin, base);
        await page.locator('input[name=email]').fill(credentials.DEV_AGENT_EMAIL);
        await page.locator('input[name=password]').fill(credentials.DEV_AGENT_PASSWORD);
        await solveCap(page);
        await page.locator('input[type=submit],button[type=submit]').first().click();
        await page.waitForURL(url => !url.pathname.endsWith('/login'));
        stage = 'report';
        const started = Date.now();
        const response = await page.goto(runBase + '/report/postfire_debris_flow/');
        assert.equal(response.status(), 200);
        assert.match(response.headers()['cache-control'], /no-store/);
        await page.locator('[data-pfr-event]').first().waitFor();
        const seed = JSON.parse(await page.locator('#postfire-report-seed').textContent());
        assert.equal(seed.status, 'available');
        assert(seed.events.rows.length <= 100 && seed.design.length === 12 && seed.inverse.length === 3);
        assert.equal(seed.summary.model, runid === 'overpriced-sprawl' ? 'M1' : 'M3');
        record({ model: seed.summary.model, attempt_id: seed.attempt_id,
            assessment_id: seed.summary.assessment_id, frequency_source: seed.summary.frequency_source,
            current: seed.summary.current, total_events: seed.events.total, load_ms: Date.now() - started });
        const eventButtons = page.locator('[data-pfr-event]');
        stage = 'event_detail';
        const firstId = await eventButtons.first().getAttribute('data-pfr-event');
        const helperCheck = await page.evaluate(async ({url, attempt, event}) => {
            const target = new URL(url, location.href);
            target.searchParams.set('attempt_id', attempt); target.searchParams.set('event_id', event);
            try {
                const value = await WCHttp.getJson(target.pathname + target.search);
                return {keys: Object.keys(value), rows: Array.isArray(value.rows) ? value.rows.length : null};
            } catch (error) { return {helper_error: error.name, message: String(error.message).replace(/https?:\/\/\S+/g, '[URL]')}; }
        }, {url: seed.urls.event, attempt: seed.attempt_id, event: firstId});
        record({helper_check: helperCheck});
        await eventButtons.first().focus();
        await page.keyboard.press('Enter');
        await page.locator('[data-pfr-detail]').waitFor();
        await page.waitForTimeout(2000);
        record({ detail_status: await page.locator('[data-pfr-status]').innerText() });
        await page.locator('[data-pfr-detail] tbody tr').nth(2).waitFor();
        assert.equal(await page.locator(`[data-pfr-event="${firstId}"]`).getAttribute('aria-expanded'), 'true');
        assert.equal(await page.evaluate(() => document.activeElement.getAttribute('data-pfr-event')), firstId);
        const detail = await page.locator('[data-pfr-detail]').innerText();
        assert.match(detail, /15/); assert.match(detail, /30/); assert.match(detail, /60/);
        stage = 'scenario_selection';
        await page.locator('[data-pfr-scenario]').first().focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('[data-pfr-scenario]').first().getAttribute('aria-pressed'), 'true');
        stage = 'duration';
        const changed = page.waitForResponse(r => r.url().includes('/query/postfire_debris_flow/?'));
        await page.locator('[data-pfr-field=duration]').selectOption('30');
        assert.equal((await changed).status(), 200);
        await page.waitForFunction(() => document.querySelector('[data-pfr-count]').textContent.includes('Showing'));
        stage = 'paging';
        if (seed.events.total > 100) {
        const queryStarted = Date.now();
        const next = page.waitForResponse(r => r.url().includes('/query/postfire_debris_flow/?'));
        await page.locator('[data-pfr-action=next]').click();
        const nextResponse = await next;
        assert.equal(nextResponse.status(), 200);
        const nextPayload = await nextResponse.json();
        assert.equal(nextPayload.query.offset, 100);
        assert.equal(nextPayload.query.duration_minutes, 30);
        record({ page_query_ms: await nextResponse.finished().then(() => Date.now()) - queryStarted,
            page_offset: nextPayload.query.offset, count: nextPayload.events.total });
        } else {
            assert(await page.locator('[data-pfr-action=next]').isDisabled());
            record({ page_offset: 0, count: seed.events.total, next_disabled: true });
        }
        stage = 'units';
        await page.evaluate(() => {
            const client = UnitizerClient.getClientSync();
            client.setGlobalPreference(0); client.dispatchPreferenceChange();
        });
        await page.waitForTimeout(100);
        const si = await page.locator('[data-pfr-body=design]').innerText();
        await page.evaluate(() => {
            const client = UnitizerClient.getClientSync();
            client.setGlobalPreference(1); client.dispatchPreferenceChange();
        });
        await page.waitForTimeout(200);
        assert.notEqual(await page.locator('[data-pfr-body=design]').innerText(), si);
        stage = 'csv';
        const downloaded = page.waitForEvent('download');
        await page.locator('[data-pfr-export=events]').click();
        const download = await downloaded;
        await download.saveAs(path.join(output, 'events-page.csv'));
        assert(fs.readFileSync(path.join(output, 'events-page.csv'), 'utf8').includes(seed.attempt_id));
        stage = 'artifact';
        const artifact = await page.request.get(new URL(seed.urls.artifacts['design.parquet'], page.url()).href);
        assert.equal(artifact.status(), 200);
        assert.match(artifact.headers()['cache-control'], /no-store/);
        assert.equal(hash(await artifact.body()), before['postfire_debris_flow/design.parquet']);
        stage = 'screenshots';
        await page.locator('[data-postfire-report]').screenshot({ path: path.join(output, 'desktop.png') });
        for (const theme of ['light-high-contrast', 'ayu-mirage', 'cursor-dark-midnight']) {
            await page.evaluate(value => document.documentElement.setAttribute('data-theme', value), theme);
            await page.locator('[data-postfire-report]').screenshot({ path: path.join(output, theme + '.png') });
        }
        await page.evaluate(() => document.documentElement.removeAttribute('data-theme'));
        await page.setViewportSize({ width: 390, height: 844 });
        await page.screenshot({ path: path.join(output, 'narrow.png'), fullPage: true });
        stage = 'controlled_detail_failures';
        const expanded = page.locator('[data-pfr-event][aria-expanded=true]');
        if (await expanded.count()) await expanded.click();
        const eventPattern = '**/query/postfire_debris_flow/event?**';
        for (const position of ['first', 'last']) {
            await page.route(eventPattern, route => route.fulfill({status: 503, contentType: 'application/json',
                body: JSON.stringify({error: {code: 'results_unavailable', message: 'Controlled test failure'}})}));
            const button = position === 'first' ? page.locator('[data-pfr-event]').first() : page.locator('[data-pfr-event]').last();
            const id = await button.getAttribute('data-pfr-event');
            await button.focus(); await page.keyboard.press('Enter');
            await page.locator('[data-pfr-detail-retry]').waitFor();
            assert.equal(await page.evaluate(() => document.activeElement.getAttribute('data-pfr-event')), id);
            assert.match(await page.locator('[data-pfr-detail]').innerText(), /Could not load/);
            await page.locator('[data-pfr-detail]').screenshot({path: path.join(output, position + '-detail-error.png')});
            await page.unroute(eventPattern);
            await page.locator('[data-pfr-detail-retry]').click();
            await page.locator('[data-pfr-detail] tbody tr').nth(2).waitFor();
            await button.click();
            record({controlled_failure: position + '_detail', recovery: 'passed'});
        }
        if (seed.events.total > 200) {
            stage = 'controlled_paging_failure';
            const queryPattern = '**/query/postfire_debris_flow/?**';
            await page.route(queryPattern, route => route.fulfill({status: 503, contentType: 'application/json',
                body: JSON.stringify({error: {code: 'results_unavailable', message: 'Controlled test failure'}})}));
            await page.locator('[data-pfr-action=next]').click();
            const localRetry = page.locator('[data-pfr-pagination] [data-pfr-action=retry]');
            await localRetry.waitFor();
            await page.screenshot({path: path.join(output, 'paging-error.png')});
            await page.unroute(queryPattern);
            await localRetry.click();
            await page.waitForFunction(() => document.querySelector('[data-pfr-count]').textContent.includes('Showing 201'));
            record({controlled_failure: 'paging', recovery: 'passed'});
        }
        if (seed.events.total > 200) {
            stage = 'off_page_selection';
            const selected = page.locator('[data-pfr-event]').first();
            const selectedId = await selected.getAttribute('data-pfr-event');
            await selected.click();
            await page.locator('[data-pfr-detail] tbody tr').nth(2).waitFor();
            const durationResponse = page.waitForResponse(r => r.url().includes('/query/postfire_debris_flow/?'));
            await page.locator('[data-pfr-field=duration]').selectOption('15');
            assert.equal((await durationResponse).status(), 200);
            await page.waitForFunction(() => document.querySelector('[data-pfr-count]').textContent.includes('Showing 1'));
            for (let index = 0; index < 2; index++) {
                const paged = page.waitForResponse(r => r.url().includes('/query/postfire_debris_flow/?'));
                await page.locator('[data-pfr-action=next]').click();
                assert.equal((await paged).status(), 200);
            }
            await page.locator('[data-pfr-detail] tbody tr').nth(2).waitFor();
            assert.equal(await page.locator(`[data-pfr-event="${selectedId}"]`).getAttribute('aria-expanded'), 'true');
            record({off_page_selection: 'preserved_after_duration_and_paging'});
        }
        stage = 'ordinary_browse';
        const listing = await page.request.get(runBase + '/browse/postfire_debris_flow/');
        assert.equal(listing.status(), 200);
        assert((await listing.text()).includes('design.parquet'));
        const ordinaryFile = await page.request.get(runBase + '/download/postfire_debris_flow/design.parquet');
        assert.equal(ordinaryFile.status(), 200);
        assert.equal(hash(await ordinaryFile.body()), before['postfire_debris_flow/design.parquet']);
        record({ ordinary_browse_download: 'passed' });
        record({ screenshots: ['desktop.png', 'narrow.png'], page_errors: errors, mutations,
            inherited_recorder_requests: recorderRequests.length });
        assert.deepEqual(errors, []); assert.deepEqual(mutations, []);
        assert.deepEqual(snapshots(), before);
        record({ acceptance: 'passed', protected_files: Object.keys(before).length, unchanged: true });
    } finally { await browser.close(); }
})().catch(() => { record({ failure: true }); process.exitCode = 1; });
