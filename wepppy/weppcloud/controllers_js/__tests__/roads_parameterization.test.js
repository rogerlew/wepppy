/** @jest-environment jsdom */
/* eslint-env node */
const fs = require('fs');
const path = require('path');
const roles = ['road', 'fill', 'buffer'];
const fields = ['ksat_mm_h', 'ki_kg_s_m4', 'kr_s_m', 'critical_shear_pa'];
function defaults() {
    return Object.fromEntries(roles.map(role => [role, Object.fromEntries(fields.map(field => [field, {mode: 'default'}]))]));
}
function state(status = 'bound') {
    return {enabled: true, readonly: false, parameterization: {status, baseline_id: 'test-baseline', overrides: defaults(), diagnostics: [], groups: [{id: 'a', label: '<script>source</script>', segment_ids: ['s1'], applicable_roles: roles, roles: Object.fromEntries(roles.map(role => [role, Object.fromEntries(fields.map(field => [field, {source: 8, adjusted: 2, resolved: 2, adjustment: '÷ 4', source_asset: 'soils/a.sol'}]))]))}], last_completed_run: null, comparisons: {available: false, reason: 'Run both configurations first.'}}};
}
function fixture(seed) {
    document.body.innerHTML = `<main id="roads_parameterization" data-query-url="/query" data-save-url="/save"><script type="application/json" data-parameterization-seed></script><p data-rp-status></p><p data-rp-errors role="alert"></p><p data-rp-baseline></p><p data-rp-repository></p><p data-rp-state></p><select data-rp-group></select><p data-rp-members></p><div data-rp-actions>${['edit','save','cancel','reset','repair'].map(a => `<button data-rp-action="${a}">${a}</button>`).join('')}</div>${roles.map(role => `<section data-rp-role="${role}"><p data-rp-applicability></p>${fields.map(field => `<div data-rp-row data-role="${role}" data-field="${field}"><span data-rp-source></span><span data-rp-adjustment></span><span data-rp-resolved></span><select aria-label="mode" data-rp-mode><option value="default">Default</option><option value="multiply">Multiply</option><option value="absolute">Absolute</option></select><input aria-label="value" type="number" data-rp-value></div>`).join('')}</section>`).join('')}<div data-rp-readback></div><div data-rp-comparison></div><details><pre data-rp-details></pre></details><a href="/back" data-rp-navigate>Back</a><dialog data-rp-leave><button data-rp-leave-action="save">Save</button><button data-rp-leave-action="discard">Discard</button><button data-rp-leave-action="stay">Stay</button></dialog></main>`;
    document.querySelector('[data-parameterization-seed]').textContent = JSON.stringify(seed);
}
const flush = () => new Promise(resolve => setTimeout(resolve, 0));
describe('Roads parameterization', () => {
    let seed;
    beforeEach(() => {
        seed = state(); fixture(seed);
        window.WCHttp = {getJson: jest.fn(async () => seed), postJson: jest.fn(async () => ({Content: {parameterization: seed.parameterization}}))};
        jest.resetModules();
        require('../dom.js');
        window.eval(fs.readFileSync(path.join(__dirname, '../roads_parameterization.js'), 'utf8'));
        window.RoadsParameterization.init();
    });
    afterEach(() => { window.RoadsParameterization.destroy(); document.body.innerHTML = ''; });
    function click(name) { document.querySelector(`[data-rp-action="${name}"]`).click(); }
    function change(mode, value) {
        const row = document.querySelector('[data-rp-row]');
        row.querySelector('select').value = mode;
        row.querySelector('input').value = value;
        row.querySelector('input').dispatchEvent(new Event('input', {bubbles: true}));
    }
    test('submits only complete parameterization object and locks pending save', async () => {
        let resolve;
        window.WCHttp.postJson.mockImplementation(() => new Promise(done => {resolve = done;}));
        click('edit'); change('multiply', '2'); click('save'); click('save');
        expect(window.WCHttp.postJson).toHaveBeenCalledTimes(1);
        const payload = window.WCHttp.postJson.mock.calls[0][1];
        expect(Object.keys(payload)).toEqual(['parameterization']);
        expect(payload.parameterization.overrides.road.ksat_mm_h).toEqual({mode: 'multiply', value: 2});
        expect(Object.keys(payload.parameterization.overrides)).toEqual(roles);
        expect(document.querySelector('[data-rp-action="cancel"]').disabled).toBe(true);
        resolve({Content: {parameterization: {...seed.parameterization, overrides: payload.parameterization.overrides}}}); await flush();
        expect(document.querySelector('[data-rp-status]').textContent).toContain('Prepare and run');
    });
    test('shows repository drift without changing saved values or enabling adoption', () => {
        const updated = state();
        updated.parameterization.repository_baseline = {status: 'different', baseline_id: 'new-baseline'};
        window.RoadsParameterization.refresh(updated);
        expect(document.querySelector('[data-rp-repository]').textContent).toContain('Repository defaults differ');
        expect(document.querySelector('[data-rp-baseline]').textContent).toContain('test-baseline');
        expect(document.querySelector('[data-rp-details]').textContent).toContain('new-baseline');
        expect(window.WCHttp.postJson).not.toHaveBeenCalled();
        updated.parameterization.repository_baseline = {status: 'unavailable', baseline_id: null, reason: 'Missing asset'};
        window.RoadsParameterization.refresh(updated);
        expect(document.querySelector('[data-rp-repository]').textContent).toContain('could not be checked');
        expect(document.querySelector('[data-rp-baseline]').textContent).toContain('test-baseline');
    });
    test('reset is draft only and cancel rereads without mutation', async () => {
        click('edit'); change('multiply', '2'); click('reset');
        expect(window.WCHttp.postJson).not.toHaveBeenCalled();
        click('cancel'); await flush();
        expect(window.WCHttp.getJson).toHaveBeenCalledWith('/query');
        expect(window.WCHttp.postJson).not.toHaveBeenCalled();
    });
    test('rejects overflow and keeps failed-save draft', async () => {
        click('edit'); change('multiply', '1e308');
        expect(document.querySelector('[data-rp-action="save"]').disabled).toBe(true);
        change('absolute', '3'); window.WCHttp.postJson.mockRejectedValue(new Error('Busy'));
        click('save'); await flush();
        expect(document.querySelector('[data-rp-value]').value).toBe('3');
        expect(document.querySelector('[data-rp-errors]').textContent).toContain('Busy');
    });
    test('passive state cannot replace dirty draft and source labels are text', () => {
        click('edit'); change('absolute', '3');
        window.RoadsParameterization.refresh(state());
        expect(document.querySelector('[data-rp-value]').value).toBe('3');
        expect(document.querySelector('[data-rp-group]').textContent).toContain('<script>source</script>');
        expect(document.querySelectorAll('script')).toHaveLength(1);
    });
    test('readonly and absent states never allow a save', () => {
        window.RoadsParameterization.refresh({...state(), readonly: true}); click('edit');
        expect(document.querySelector('[data-rp-action="save"]').disabled).toBe(true);
        window.RoadsParameterization.refresh({enabled: false, readonly: true, parameterization: null});
        expect(document.querySelector('[data-rp-action="edit"]').disabled).toBe(true);
    });
    test('unbound saves default binding and invalid repair is explicit', async () => {
        window.RoadsParameterization.refresh(state('unbound')); click('edit'); click('save'); await flush();
        expect(window.WCHttp.postJson).toHaveBeenCalledTimes(1);
        window.RoadsParameterization.refresh(state('invalid')); click('repair'); click('save'); await flush();
        expect(window.WCHttp.postJson.mock.calls[1][1].parameterization).toEqual({overrides: defaults(), repair: true});
    });
    test('empty numeric editing stays empty and busy state blocks mutations', () => {
        click('edit'); change('absolute', '');
        expect(document.querySelector('[data-rp-value]').value).toBe('');
        expect(document.querySelector('[data-rp-action="save"]').disabled).toBe(true);
        click('reset');
        window.RoadsParameterization.refresh({...state(), status: 'running'});
        expect(document.querySelector('[data-rp-action="edit"]').disabled).toBe(true);
    });
    test('busy shell remains inspectable without guessing parameter values', () => {
        window.RoadsParameterization.refresh({...state(), busy: true, status: 'running', parameterization: null});
        expect(document.querySelector('[data-rp-state]').textContent).toContain('Roads is busy');
        expect(document.querySelector('[data-rp-action="edit"]').disabled).toBe(true);
        expect(document.querySelector('[data-rp-source]').textContent).toBe('Unavailable');
    });
    test('renders compatible comparison metrics with explicit scope and units', () => {
        const updated = state();
        const metrics = {annual_runoff_m3: 2, annual_sediment_kg: 3, annual_runoff_mm: 4, annual_sediment_kg_m2: 5, modeled_area_m2: 500};
        const run = {run_id: 'run-1', completed_at: 'today', metrics, calendar_years: [2001], profile_count: 1, configuration_hash: 'cfg', baseline_id: 'baseline', snapshot_relpath: 'wepp/roads/snapshot.json'};
        updated.parameterization.comparisons = {status: 'available', baseline: run, custom: {...run, run_id: 'run-2'}, difference: metrics};
        window.RoadsParameterization.refresh(updated);
        const comparison = document.querySelector('[data-rp-comparison]').textContent;
        expect(comparison).toContain('not watershed outlet');
        expect(comparison).toContain('Annual runoff (m³/year)');
        expect(comparison).toContain('run-1');
        expect(comparison).toContain('run-2');
        expect(comparison).toContain('500 m²');
    });

    test('server key ordering does not change default status or reset dirtiness', () => {
        const updated = state();
        updated.parameterization.overrides = Object.fromEntries([...roles].sort().map(role => [role, Object.fromEntries([...fields].sort().map(field => [field, {mode: 'default'}]))]));
        window.RoadsParameterization.refresh(updated);
        expect(document.querySelector('[data-rp-state]').textContent).toContain('Default inputs');
        click('edit'); click('reset');
        expect(document.querySelector('[data-rp-action="save"]').disabled).toBe(true);
        const passive = {...updated, readonly: true};
        window.RoadsParameterization.refresh(passive);
        expect(document.querySelector('[data-rp-state]').textContent).toContain('Read-only');
    });

    test('failed query envelope preserves draft rather than hydrating guessed defaults', async () => {
        click('edit'); change('absolute', '3');
        window.WCHttp.getJson.mockResolvedValue({error: {message: 'Read failed'}});
        click('cancel'); await flush();
        expect(document.querySelector('[data-rp-value]').value).toBe('3');
        expect(document.querySelector('[data-rp-errors]').textContent).toContain('Read failed');
    });

});
