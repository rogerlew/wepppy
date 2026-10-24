import { jest } from '@jest/globals';
import { createRoadsController, scopeNavigationUrl, readScopeRestore, restoredView, restoreDisplay, roadColor, profileScopeText } from '../roads.js';

const feature = (rate = 2.75) => ({ type: 'Feature', geometry: { type: 'LineString', coordinates: [[0, 0], [1, 1]] },
  properties: { segment_id: 'a', name: '<img src=x onerror="window.pwned=true">', roads_detachment: {
    state: 'complete', rate_t_ha_year: rate, annual_detachment_kg: 11, modeled_area_m2: 40, profile_count: 1,
    profiles: [{ segment_run_id: 1, profile_scope: 'mixed_profile', soil_loss_kg: 11, modeled_area_m2: 40,
      soil_loss_density_kg_m2: .275, simulation_years: 16, segment_length_m: 20, design: 'outslope_rutted' }] } } });
const payload = () => ({ type: 'FeatureCollection', features: [feature()], roads_detachment: {
  state: 'available', units: 't/ha/year', remainder_profile_count: 0, reason: null } });
function setup(fetchImpl, scope = 'baseline') {
  document.body.innerHTML = `<section id="gl-roads-panel"><select id="gl-output-scope"><option value="baseline">Baseline</option><option value="roads">Roads</option></select>
    <p id="gl-output-scope-status"></p><input id="gl-roads-visible" type="checkbox"><p id="gl-roads-status"></p>
    <div id="gl-roads-legend"></div><details id="gl-roads-details"><div id="gl-roads-selection" tabindex="-1"></div><div id="gl-roads-table"></div></details>
    <select id="gl-scenario-select"><option value="">Base</option></select><input id="gl-comparison-toggle" type="checkbox"></section>`;
  const state = { currentScenarioPath: '', comparisonMode: false };
  const location = { href: 'https://example.test/p/runs/a/cfg/gl-dashboard?roads=on', hash: '', assign: jest.fn() };
  const applyLayers = jest.fn();
  const controller = createRoadsController({ ctx: { runid: 'a', config: 'cfg', sitePrefix: '/p', outputScope: scope },
    deck: { GeoJsonLayer: class { constructor(props) { this.props = props; } } },
    getState: () => state, setValue: (key, value) => { state[key] = value; }, applyLayers,
    jet2Color: (x) => [x * 255, 0, 0, 255], fetchImpl, location });
  return { controller, state, applyLayers, location };
}

test('uses guarded compact view, literal tooltip/table/details and stable geometry', async () => {
  const fetchImpl = jest.fn(async () => ({ ok: true, json: async () => payload() }));
  const { controller } = setup(fetchImpl);
  await controller.load();
  expect(fetchImpl.mock.calls[0][0]).toBe('/p/runs/a/cfg/resources/roads.json?view=detachment');
  const first = controller.layer();
  const second = controller.layer();
  expect(second.props.data).toBe(first.props.data);
  expect(document.querySelector('#gl-roads-table img')).toBeNull();
  document.querySelector('#gl-roads-table button').click();
  expect(document.querySelector('#gl-roads-selection').textContent).toContain('Modeled source road-segment length: 20 m');
  expect(document.querySelector('#gl-roads-selection').textContent).toContain('Includes modeled road/fill/buffer');
  expect(document.querySelector('#gl-roads-selection img')).toBeNull();
  expect(controller.tooltip({ layer: { id: 'roads-detachment' }, object: feature() })).toHaveProperty('text');
});

test.each([[401, 'access was denied'], [403, 'access was denied'], [409, 'Prepare and run'], [404, 'not available'], [500, 'Reload to retry']])('isolates HTTP %s errors', async (status, text) => {
  const { controller, state } = setup(async () => ({ ok: false, status, json: async () => ({ error: 'Prepare and run Roads again.' }) }));
  state.weppSummary = { keep: true };
  await controller.load();
  expect(document.querySelector('#gl-roads-status').textContent).toContain(text);
  expect(state.weppSummary).toEqual({ keep: true });
  expect(controller.layer()).toBeNull();
  expect(document.querySelector('#gl-output-scope option[value=baseline]').disabled).toBe(false);
});

test('late response cannot restore invalidated data', async () => {
  let resolve;
  const { controller } = setup(() => new Promise((r) => { resolve = r; }));
  const pending = controller.load();
  controller.unavailable();
  resolve({ ok: true, json: async () => payload() });
  await pending;
  expect(controller.layer()).toBeNull();
  expect(document.querySelector('#gl-roads-table').children).toHaveLength(0);
});

test('scenario temporarily hides roads and preserves visibility preference', async () => {
  const { controller, state } = setup(async () => ({ ok: true, json: async () => payload() }));
  await controller.load();
  state.currentScenarioPath = '_pups/omni/scenarios/a'; controller.sync();
  expect(controller.layer()).toBeNull();
  expect(state.roadsVisible).toBe(true);
  state.currentScenarioPath = ''; controller.sync();
  expect(controller.layer()).not.toBeNull();
});

test('Roads scope disables only map scenario controls', () => {
  setup(jest.fn(), 'roads');
  expect(document.querySelector('#gl-scenario-select').disabled).toBe(true);
  expect(document.querySelector('#gl-comparison-toggle').disabled).toBe(true);
});

test('scope URL preserves viewport and separate visibility while clearing unsupported graph/scenario', () => {
  const state = { roadsVisible: false, currentViewState: { longitude: 1, latitude: 2, zoom: 8 },
    currentScenarioPath: 'scenario', comparisonMode: true, activeGraphKey: 'flow-duration', weppLayers: [{ key: 'soil_loss', visible: true }] };
  const url = new URL(scopeNavigationUrl('https://x/r/gl-dashboard', 'roads', state));
  expect(url.searchParams.get('output_scope')).toBe('roads');
  expect(url.searchParams.get('roads')).toBe('off');
  const restore = readScopeRestore(url.hash);
  expect(restore.graph).toBeNull();
  expect(restore.notice).toContain('Flow Duration was cleared');
  expect(restoredView(restore).zoom).toBe(8);
  expect(restore.layers.weppLayers).toEqual(['soil_loss']);
  expect(restore).not.toHaveProperty('currentScenarioPath');
  state.activeGraphKey = 'climate-yearly';
  expect(readScopeRestore(new URL(scopeNavigationUrl(url.href, 'baseline', state)).hash).graph).toBe('climate-yearly');
});

test('negative, zero and missing have separate colors; mixed/unclassified labels explicit', () => {
  const jet = jest.fn(() => [1, 2, 3, 255]);
  expect(roadColor(feature(-1), 10, jet)).toEqual([130, 60, 150, 255]);
  expect(jet).not.toHaveBeenCalled();
  roadColor(feature(0), 0, jet); expect(jet).toHaveBeenCalledWith(0);
  const missing = feature(); missing.properties.roads_detachment.state = 'partial';
  expect(roadColor(missing, 10, jet)).toEqual([140, 140, 140, 255]);
  expect(profileScopeText([{ profile_scope: null }])).toBe('Unclassified profile');
});

test('obsolete delayed 409 body cannot poison a newer successful read', async () => {
  let resolveBody;
  const fetchImpl = jest.fn()
    .mockResolvedValueOnce({ ok: false, status: 409, json: () => new Promise((r) => { resolveBody = r; }) })
    .mockResolvedValueOnce({ ok: true, json: async () => payload() });
  const { controller } = setup(fetchImpl);
  const old = controller.load();
  await Promise.resolve();
  await controller.load();
  resolveBody({ error: 'Stale old response' }); await old;
  expect(controller.layer()).not.toBeNull();
  expect(document.querySelector('#gl-output-scope option[value=roads]').disabled).toBe(false);
});

test.each(['no_completed_profiles', 'unavailable_mean_annual', 'partial', 'negative'])('does not label %s as measured zero', async (state) => {
  const data = payload();
  if (state === 'partial') data.features[0].properties.roads_detachment.state = 'partial';
  else if (state === 'negative') data.features[0].properties.roads_detachment.rate_t_ha_year = -1;
  else { data.features = []; data.roads_detachment.state = state; data.roads_detachment.reason = state; }
  const { controller } = setup(async () => ({ ok: true, json: async () => data })); await controller.load();
  expect(document.querySelector('#gl-roads-legend').textContent).not.toContain('results are zero');
  expect(document.querySelector('#gl-roads-legend input')).toBeNull();
});


test('nullable display preferences restore before detection without changing layer data', () => {
  const state = { roadsMaxOverride: null, weppYearlySelectedYear: null, openetSelectedDatasetKey: null, weppLayers: [] };
  const saved = { display: { roadsMaxOverride: 20, weppYearlySelectedYear: 2010, openetSelectedDatasetKey: 'ensemble', weppStatistic: 'median' }, layers: { weppLayers: ['wepp-soil-loss'] } };
  const setValue = (k, v) => { state[k] = v; };
  restoreDisplay(saved, () => state, setValue, { layers: false });
  expect(state.roadsMaxOverride).toBe(20);
  expect(state.weppYearlySelectedYear).toBe(2010);
  expect(state.openetSelectedDatasetKey).toBe('ensemble');
  state.weppLayers = [{ key: 'wepp-soil-loss', visible: false }];
  restoreDisplay(saved, () => state, setValue, { display: false });
  expect(state.weppLayers[0].visible).toBe(true);
});


test('invalid maximum edits keep displayed control and scale consistent', async () => {
  const { controller, state } = setup(async () => ({ ok: true, json: async () => payload() }));
  await controller.load();
  const input = document.querySelector('#gl-roads-legend input');
  input.focus();
  input.value = '0'; input.dispatchEvent(new Event('change'));
  expect(input.value).toBe('2.75');
  expect(state.roadsMaxOverride).toBeUndefined();
  input.value = '8'; input.dispatchEvent(new Event('change'));
  expect(state.roadsMaxOverride).toBe(8);
  expect(document.activeElement).toBe(input);
  input.value = ''; input.dispatchEvent(new Event('change'));
  expect(input.value).toBe('8');
});
