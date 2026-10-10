/** @jest-environment jsdom */
/* eslint-env node */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const script = fs.readFileSync(path.resolve(__dirname, '../../templates/reports/wepp/return_periods.htm'), 'utf8')
    .match(/<script>([\s\S]*?)<\/script>/)[1];

function initialize(query = '') {
    document.body.innerHTML = `
      <select id="yearSelection"><option value="./?exclude_yr_indxs=0">First year</option><option value="./?">All years</option></select>
      <details id="advancedOptionsCollapse"></details>
      <form id="excludeMonthsForm"><input id="gringortenCheckbox" type="checkbox">
        <input type="radio" name="method" value="cta" checked><input type="radio" name="method" value="am">
        <input type="checkbox" id="m1" value="1"><input type="checkbox" id="m2" value="2">
      </form>
      <form id="omniScenariosForm"><input type="checkbox" name="omni_scenario" value="undisturbed">
        <input type="checkbox" name="omni_scenario" value="uniform_low">
        <input type="checkbox" name="omni_scenario" value="uniform_high" disabled>
      </form>
      <select id="chnTopazSelect"><option value="94">94</option></select>
      <button id="toggleExtraneous" data-target-state="true"></button>`;
    const url = new URL('http://localhost/runs/project/cfg/report/wepp/return_periods/' + query);
    const location = { href: url.href, pathname: url.pathname, search: url.search };
    const ready = jest.spyOn(document, 'addEventListener').mockImplementation((event, callback) => {
        if (event === 'DOMContentLoaded') callback();
    });
    vm.runInNewContext(script, { window: { location }, document, URL, URLSearchParams });
    ready.mockRestore();
    return location;
}
function submit(id) {
    document.getElementById(id).dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
}
function params(location) {
    return new URL(location.href, 'http://localhost').searchParams;
}
const selectionQuery = '?omni_scenario=undisturbed&omni_scenario=uniform_low&rec_intervals=7,3&method=am&output_scope=roads&exclude_yr_indxs=0';

test('initial controls stay unchecked; apply multiple choices and retain existing filters', () => {
    const location = initialize('?rec_intervals=7,3&method=am&output_scope=roads');
    const boxes = document.querySelectorAll('#omniScenariosForm input');
    expect(Array.from(boxes).every(box => !box.checked)).toBe(true);
    boxes.forEach(box => { box.checked = true; });
    submit('omniScenariosForm');
    expect(params(location).getAll('omni_scenario')).toEqual(['undisturbed', 'uniform_low']);
    expect(params(location).get('rec_intervals')).toBe('7,3');
    expect(params(location).get('output_scope')).toBe('roads');
});

test('clearing all selections removes every repeated value', () => {
    const location = initialize(selectionQuery);
    submit('omniScenariosForm');
    expect(params(location).getAll('omni_scenario')).toEqual([]);
});

test('year selection preserves both scenarios, custom intervals, and scope', () => {
    const location = initialize(selectionQuery);
    document.getElementById('yearSelection').selectedIndex = 1;
    document.getElementById('yearSelection').dispatchEvent(new Event('change'));
    expect(params(location).getAll('omni_scenario')).toEqual(['undisturbed', 'uniform_low']);
    expect(params(location).get('rec_intervals')).toBe('7,3');
    expect(params(location).get('output_scope')).toBe('roads');
    expect(params(location).has('exclude_yr_indxs')).toBe(false);
});

test('advanced selection preserves repeated scenarios without restoring removed year exclusions', () => {
    const location = initialize(selectionQuery);
    document.getElementById('yearSelection').selectedIndex = 1;
    document.getElementById('m2').checked = true;
    document.getElementById('gringortenCheckbox').checked = true;
    submit('excludeMonthsForm');
    expect(params(location).getAll('omni_scenario')).toEqual(['undisturbed', 'uniform_low']);
    expect(params(location).get('rec_intervals')).toBe('7,3');
    expect(params(location).get('exclude_months')).toBe('2');
    expect(params(location).get('method')).toBe('am');
    expect(params(location).has('exclude_yr_indxs')).toBe(false);
});

test.each(['chnTopazSelect', 'toggleExtraneous'])('%s preserves both applied scenarios', id => {
    const location = initialize(selectionQuery);
    document.getElementById(id).dispatchEvent(new Event(id === 'chnTopazSelect' ? 'change' : 'click', { cancelable: true }));
    expect(params(location).getAll('omni_scenario')).toEqual(['undisturbed', 'uniform_low']);
    expect(params(location).get('rec_intervals')).toBe('7,3');
});
