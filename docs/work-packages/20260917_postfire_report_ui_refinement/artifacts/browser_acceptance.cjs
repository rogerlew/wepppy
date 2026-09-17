// Authenticated, read-only acceptance for the post-fire report presentation.
const { chromium } = require('../../../../wepppy/weppcloud/static-src/node_modules/playwright');
const AxeBuilder = require('../../../../wepppy/weppcloud/static-src/node_modules/@axe-core/playwright').default;
const assert = require('assert/strict');
const { createHash } = require('crypto');
const fs = require('fs');
const path = require('path');

const base = 'https://wc.bearhive.duckdns.org';
const reportUrl = base + '/weppcloud/runs/thespian-cleanness/config/report/postfire_debris_flow/';
const output = path.join(__dirname, 'browser');
const records = [];
fs.mkdirSync(output, { recursive: true });

function record(value) {
    const row = { utc: new Date().toISOString(), ...value };
    records.push(row);
    fs.writeFileSync(path.join(output, 'evidence.json'), JSON.stringify(records, null, 2));
    console.log(JSON.stringify(row));
}

function hash(value) {
    return createHash('sha256').update(value).digest('hex');
}

function expand(seed, length) {
    let state = 2166136261;
    for (const character of seed) {
        state ^= character.codePointAt(0);
        state = (state + (state << 1) + (state << 4) + (state << 7) + (state << 8) + (state << 24)) >>> 0;
    }
    let result = '';
    while (result.length < length) {
        state ^= state << 13;
        state ^= state >>> 17;
        state ^= state << 5;
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
    for (let index = 1; index <= c; index += 1) {
        const salt = expand(token + index, s);
        const target = expand(token + index + 'd', d);
        let nonce = 0;
        while (!hash(salt + nonce).startsWith(target)) nonce += 1;
        solutions.push(nonce);
    }
    const redeemed = await page.request.post(new URL('redeem', url).href, { data: { token, solutions } });
    const result = await redeemed.json();
    assert(result.success && result.token);
    await page.locator('input[name=cap_token]').evaluate((element, value) => {
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
    }, result.token);
}

async function inspectPresentation(page) {
    return page.evaluate(() => {
        const summary = document.querySelector('[data-pfr-assessment-summary]');
        const list = summary.querySelector('dl');
        const labels = document.querySelector('[data-pfr-chart-labels]');
        const svg = labels.closest('svg');
        const label = labels.querySelector('.wc-chart-label');
        const labelStyle = getComputedStyle(label);
        const rootStyle = getComputedStyle(document.documentElement);
        const tokenProbe = document.createElement('span');
        tokenProbe.style.color = 'var(--wc-color-text)';
        tokenProbe.style.backgroundColor = 'var(--wc-color-surface)';
        document.body.appendChild(tokenProbe);
        const probeStyle = getComputedStyle(tokenProbe);
        const textTokenComputed = probeStyle.color;
        const surfaceTokenComputed = probeStyle.backgroundColor;
        tokenProbe.remove();
        const form = document.querySelector('[data-pfr-filters]');
        const fields = document.querySelector('[data-pfr-filter-fields]');
        const minimum = document.querySelector('[data-pfr-field=min_probability]');
        const year = document.querySelector('[data-pfr-field=year]');
        const actions = [...form.querySelectorAll('[data-pfr-action]')].map(element => element.dataset.pfrAction);
        return {
            summary_items: list.querySelectorAll('.wc-summary-pane__item').length,
            summary_terms: [...list.querySelectorAll('dt')].map(element => element.textContent.trim()),
            notices: document.querySelector('[data-pfr-warnings]').textContent.trim(),
            final_label_layer: svg.lastElementChild === labels,
            all_text_in_layer: svg.querySelectorAll('text').length === labels.querySelectorAll('text').length,
            label_style: {
                fill: labelStyle.fill,
                stroke: labelStyle.stroke,
                text_token: rootStyle.getPropertyValue('--wc-color-text').trim(),
                surface_token: rootStyle.getPropertyValue('--wc-color-surface').trim(),
                text_token_computed: textTokenComputed,
                surface_token_computed: surfaceTokenComputed,
                stroke_width: labelStyle.strokeWidth,
                stroke_linejoin: labelStyle.strokeLinejoin,
                paint_order: labelStyle.paintOrder,
                pointer_events: labelStyle.pointerEvents,
                layer_pointer_events: getComputedStyle(labels).pointerEvents
            },
            field_gap: getComputedStyle(fields).gap,
            field_count: fields.querySelectorAll('.wc-field').length,
            input_widths: [minimum.getBoundingClientRect().width, year.getBoundingClientRect().width],
            form_width: form.getBoundingClientRect().width,
            form_overflow: form.scrollWidth > form.clientWidth,
            actions,
            numeric_contract: {
                minimum: { min: minimum.min, max: minimum.max, step: minimum.step },
                year: { step: year.step }
            }
        };
    });
}

(async () => {
    const secretFile = path.resolve(__dirname, '../../../../docker/secrets/dev-agent.env');
    const credentials = Object.fromEntries(fs.readFileSync(secretFile, 'utf8').split('\n')
        .filter(line => line.includes('=') && !line.startsWith('#')).map(line => {
            const index = line.indexOf('=');
            return [line.slice(0, index), line.slice(index + 1).replace(/^['"]|['"]$/g, '')];
        }));
    const browser = await chromium.launch({ headless: true });
    const pageErrors = [];
    try {
        const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
        const page = await context.newPage();
        page.on('pageerror', error => pageErrors.push(error.message));
        await page.goto(base + '/weppcloud/login');
        await page.locator('input[name=email]').fill(credentials.DEV_AGENT_EMAIL);
        await page.locator('input[name=password]').fill(credentials.DEV_AGENT_PASSWORD);
        await solveCap(page);
        await page.locator('input[type=submit],button[type=submit]').first().click();
        await page.waitForURL(url => !url.pathname.endsWith('/login'));

        const response = await page.goto(reportUrl);
        assert.equal(response.status(), 200);
        assert.match(response.headers()['cache-control'], /no-store/);
        await page.locator('[data-pfr-event]').first().waitFor({ timeout: 45000 });

        const presentation = await inspectPresentation(page);
        record({ stage: 'desktop-structure-observed', presentation });
        assert.equal(presentation.summary_items, 4);
        assert.deepEqual(presentation.summary_terms, ['Assessment', 'Result status', 'Input coverage', 'Notices']);
        assert(presentation.notices.length > 0);
        assert(presentation.final_label_layer && presentation.all_text_in_layer);
        assert.equal(presentation.label_style.fill, presentation.label_style.text_token_computed);
        assert.equal(presentation.label_style.stroke, presentation.label_style.surface_token_computed);
        assert.equal(presentation.label_style.stroke_width, '3px');
        assert.equal(presentation.label_style.stroke_linejoin, 'round');
        assert.match(presentation.label_style.paint_order, /^stroke/);
        assert.equal(presentation.label_style.pointer_events, 'none');
        assert.equal(presentation.label_style.layer_pointer_events, 'none');
        assert.equal(presentation.field_count, 4);
        assert.deepEqual(presentation.actions, ['apply', 'reset']);
        assert(presentation.input_widths.every(width => width >= 100 && width <= 125));
        assert(presentation.input_widths.every(width => width < presentation.form_width));
        assert.equal(presentation.form_overflow, false);
        assert.deepEqual(presentation.numeric_contract, {
            minimum: { min: '0', max: '100', step: 'any' }, year: { step: '1' }
        });
        record({ stage: 'desktop-structure', acceptance: 'passed' });

        await page.locator('[data-pfr-chart] svg').scrollIntoViewIfNeeded();
        const overlap = await page.evaluate(() => {
            const svg = document.querySelector('[data-pfr-chart] svg');
            const circle = svg.querySelector('circle[data-pfr-scenario]');
            const labels = svg.querySelector('[data-pfr-chart-labels]');
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('class', 'wc-chart-label');
            text.setAttribute('data-pfr-overlap-test', '');
            text.setAttribute('x', circle.getAttribute('cx'));
            text.setAttribute('y', circle.getAttribute('cy'));
            text.textContent = 'Overlap test label';
            labels.appendChild(text);
            const rect = circle.getBoundingClientRect();
            const x = rect.left + rect.width / 2;
            const y = rect.top + rect.height / 2;
            const hit = document.elementFromPoint(x, y);
            return { x, y, width: rect.width, height: rect.height, hit: hit && hit.tagName,
                hit_scenario: hit && hit.getAttribute('data-pfr-scenario') };
        });
        record({ stage: 'pointer-overlap-observed', overlap });
        await page.mouse.click(overlap.x, overlap.y);
        assert.equal(await page.locator('circle[data-pfr-scenario]').first().getAttribute('aria-pressed'), 'true');
        await page.locator('[data-pfr-overlap-test]').evaluate(element => element.remove());
        record({ stage: 'pointer-overlap', selected: true });

        const p50 = page.locator('[data-pfr-p50]');
        await p50.focus();
        await page.keyboard.press('Tab');
        assert.equal(await page.evaluate(() => document.activeElement.matches('circle[data-pfr-scenario]')), true);
        await page.keyboard.press('Enter');
        assert.equal(await page.evaluate(() => document.activeElement.getAttribute('aria-pressed')), 'true');
        await page.keyboard.press('Tab');
        assert.equal(await page.evaluate(() => document.activeElement.matches('circle[data-pfr-scenario]')), true);
        await page.keyboard.press('Space');
        assert.equal(await page.evaluate(() => document.activeElement.getAttribute('aria-pressed')), 'true');
        record({ stage: 'keyboard-markers', tab_enter_space: 'passed' });

        const axe = await new AxeBuilder({ page }).include('[data-postfire-report]').analyze();
        const axeEvidence = {
            url: axe.url,
            timestamp: axe.timestamp,
            test_engine: axe.testEngine,
            violations: axe.violations.map(rule => ({ id: rule.id, impact: rule.impact,
                help: rule.help, node_count: rule.nodes.length,
                targets: rule.nodes.slice(0, 10).map(item => item.target) })),
            incomplete: axe.incomplete.map(rule => ({ id: rule.id, impact: rule.impact,
                help: rule.help, node_count: rule.nodes.length,
                targets: rule.nodes.slice(0, 10).map(item => item.target) })),
            passes: axe.passes.map(rule => ({ id: rule.id, impact: rule.impact,
                node_count: rule.nodes.length }))
        };
        fs.writeFileSync(path.join(output, 'axe.json'), JSON.stringify(axeEvidence, null, 2));
        assert.deepEqual(axe.violations, []);
        record({ stage: 'axe', violations: 0, passes: axe.passes.length });

        for (const theme of ['default', 'light-high-contrast', 'cursor-dark-midnight']) {
            await page.evaluate(value => {
                if (value === 'default') document.documentElement.removeAttribute('data-theme');
                else document.documentElement.setAttribute('data-theme', value);
            }, theme);
            const themed = await inspectPresentation(page);
            assert.equal(themed.label_style.fill, themed.label_style.text_token_computed);
            assert.equal(themed.label_style.stroke, themed.label_style.surface_token_computed);
            assert.equal(themed.label_style.pointer_events, 'none');
            assert.equal(themed.label_style.layer_pointer_events, 'none');
            assert.equal(themed.form_overflow, false);
            const themedAxe = await new AxeBuilder({ page }).include('[data-postfire-report]').analyze();
            assert.deepEqual(themedAxe.violations, []);
            await page.locator('[data-postfire-report]').screenshot({ path: path.join(output, theme + '-desktop.png') });
            await page.setViewportSize({ width: 390, height: 900 });
            const narrow = await inspectPresentation(page);
            assert.equal(narrow.form_overflow, false);
            assert(narrow.input_widths.every(width => width < narrow.form_width));
            await page.screenshot({ path: path.join(output, theme + '-narrow.png'), fullPage: true });
            record({ stage: 'theme', theme, axe_violations: 0, desktop: themed, narrow });
            await page.setViewportSize({ width: 1440, height: 1100 });
        }

        await page.evaluate(() => document.documentElement.removeAttribute('data-theme'));
        await page.evaluate(() => {
            WCHttp.getJson = () => new Promise(() => {});
            document.querySelector('[data-pfr-filters]').requestSubmit();
        });
        await page.waitForFunction(() => document.querySelector('[data-pfr-event]').disabled);
        await page.waitForTimeout(300);
        const loadingStyle = await page.locator('[data-pfr-event]').first().evaluate(element => {
            const probe = document.createElement('span');
            probe.style.color = 'var(--wc-button-disabled-text)';
            element.appendChild(probe);
            const disabledToken = getComputedStyle(probe).color;
            const style = getComputedStyle(element);
            probe.remove();
            return { disabled: element.disabled, color: style.color, disabledToken,
                disabledTokenRaw: style.getPropertyValue('--wc-button-disabled-text').trim(),
                enabledTokenRaw: style.getPropertyValue('--wc-color-link-hover').trim(), opacity: style.opacity };
        });
        record({ stage: 'filter-loading-observed', loadingStyle });
        assert.equal(loadingStyle.disabled, true);
        assert.equal(loadingStyle.color, loadingStyle.disabledToken);
        record({ stage: 'filter-loading', loadingStyle });
        await page.reload();
        await page.locator('[data-pfr-event]').first().waitFor({ timeout: 45000 });

        const query = page.waitForResponse(value => value.url().includes('/query/postfire_debris_flow/?'));
        await page.locator('[data-pfr-field=min_probability]').fill('25');
        await page.locator('[data-pfr-field=sort]').selectOption('probability');
        await page.locator('[data-pfr-field=descending]').check();
        await page.locator('[data-pfr-action=apply]').click();
        const queryResponse = await query;
        assert.equal(queryResponse.status(), 200);
        const queryUrl = new URL(queryResponse.url());
        assert.equal(queryUrl.searchParams.get('min_probability'), '0.25');
        assert.equal(queryUrl.searchParams.get('sort'), 'probability');
        assert.equal(queryUrl.searchParams.get('descending'), 'true');
        const reset = page.waitForResponse(value => value.url().includes('/query/postfire_debris_flow/?'));
        await page.locator('[data-pfr-action=reset]').click();
        const resetResponse = await reset;
        assert.equal(resetResponse.status(), 200);
        const resetUrl = new URL(resetResponse.url());
        assert.equal(resetUrl.searchParams.has('min_probability'), false);
        assert.equal(resetUrl.searchParams.get('sort'), 'row_ordinal');
        assert.equal(resetUrl.searchParams.get('descending'), 'false');
        record({ stage: 'filters', apply_reset: 'passed' });

        assert.deepEqual(pageErrors, []);
        record({ stage: 'complete', page_errors: pageErrors, acceptance: 'passed' });
    } finally {
        await browser.close();
    }
})().catch(error => {
    record({ stage: 'failed', name: error.name, message: error.message });
    process.exitCode = 1;
});
