/** Roads overlay and scope navigation; data comes from one guarded server view. */
const LAYER_KEYS = ['detectedLayers', 'landuseLayers', 'soilsLayers', 'hillslopesLayers',
  'channelsLayers', 'watarLayers', 'weppLayers', 'weppChannelLayers', 'weppYearlyLayers',
  'weppYearlyChannelLayers', 'weppEventLayers', 'rapLayers', 'openetLayers'];
const DISPLAY_KEYS = ['subcatchmentsVisible', 'subcatchmentLabelsVisible', 'channelsVisible',
  'channelLabelsVisible', 'sbsColorShiftEnabled', 'currentBasemapKey', 'weppStatistic',
  'weppYearlySelectedYear', 'weppEventSelectedDate', 'rapSelectedYear', 'rapCumulativeMode',
  'openetSelectedMonthIndex', 'openetSelectedDatasetKey', 'climateWaterYear', 'climateStartMonth',
  'cumulativeMeasure', 'cumulativeScenarioSelections', 'boxplotLogScale', 'flowDuration',
  'openetYearlySelectedDatasetKey', 'openetYearlySelectedYear', 'openetYearlyWaterYear', 'openetYearlyStartMonth',
  'climateYearlySelectedYear', 'weppYearlyRangeOverrides', 'roadsMaxOverride'];

export function readScopeRestore(hash) {
  try {
    const value = new URLSearchParams(hash.replace(/^#/, '')).get('dashboard');
    const result = value ? JSON.parse(value) : {};
    return result && typeof result === 'object' && !Array.isArray(result) ? result : {};
  } catch { return {}; }
}

export function scopeNavigationUrl(href, scope, state) {
  const url = new URL(href);
  url.searchParams.set('output_scope', scope);
  url.searchParams.set('roads', state.roadsVisible ? 'on' : 'off');
  const restore = { view: state.currentViewState, graph: state.activeGraphKey, layers: {}, display: {} };
  DISPLAY_KEYS.forEach((key) => { restore.display[key] = state[key]; });
  LAYER_KEYS.forEach((key) => {
    restore.layers[key] = (state[key] || []).filter((layer) => layer.visible).map((layer) => layer.key || layer.id);
  });
  if (scope === 'roads') {
    if (state.currentScenarioPath || state.comparisonMode) restore.notice = 'Map scenario and comparison cleared: Roads uses this run’s outputs.';
    if (state.activeGraphKey === 'flow-duration') {
      restore.graph = null;
      restore.notice = `${restore.notice || ''} Flow Duration was cleared because it is available only in Baseline.`.trim();
    }
  }
  url.hash = new URLSearchParams({ dashboard: JSON.stringify(restore) }).toString();
  return url.href;
}

export function restoredView(restore) {
  const v = restore.view;
  if (!v || !['longitude', 'latitude', 'zoom'].every((key) => Number.isFinite(v[key])) ||
      Math.abs(v.longitude) > 180 || Math.abs(v.latitude) > 90 || v.zoom < 2 || v.zoom > 17) return null;
  return { longitude: v.longitude, latitude: v.latitude, zoom: v.zoom,
    pitch: Number.isFinite(v.pitch) ? Math.max(0, Math.min(60, v.pitch)) : 0,
    bearing: Number.isFinite(v.bearing) ? v.bearing : 0, minZoom: 2, maxZoom: 17 };
}

const BOOLEAN_KEYS = new Set(['subcatchmentsVisible', 'subcatchmentLabelsVisible', 'channelsVisible',
  'channelLabelsVisible', 'sbsColorShiftEnabled', 'rapCumulativeMode', 'climateWaterYear', 'openetYearlyWaterYear']);
const NUMBER_KEYS = new Set(['weppYearlySelectedYear', 'rapSelectedYear', 'openetSelectedMonthIndex',
  'climateStartMonth', 'openetYearlySelectedYear', 'openetYearlyStartMonth', 'climateYearlySelectedYear', 'roadsMaxOverride']);
const STRING_KEYS = new Set(['currentBasemapKey', 'weppStatistic', 'weppEventSelectedDate',
  'openetSelectedDatasetKey', 'cumulativeMeasure', 'openetYearlySelectedDatasetKey']);
function validPreference(key, value) {
  if (BOOLEAN_KEYS.has(key)) return typeof value === 'boolean';
  if (NUMBER_KEYS.has(key)) return value === null || (Number.isFinite(value) && (key !== 'roadsMaxOverride' || value > 0));
  if (STRING_KEYS.has(key)) return value === null || typeof value === 'string';
  if (key === 'cumulativeScenarioSelections') return Array.isArray(value) && value.every((v) => typeof v === 'string');
  if (key === 'boxplotLogScale') return value && typeof value === 'object' && !Array.isArray(value) && Object.values(value).every((v) => typeof v === 'boolean');
  if (key === 'weppYearlyRangeOverrides') return value && typeof value === 'object' && !Array.isArray(value) && Object.values(value).every((v) => v && Number.isFinite(v.min) && Number.isFinite(v.max) && v.max >= v.min);
  if (key === 'flowDuration') return value && ['hillslope', 'outlet'].includes(value.source) &&
    Number.isInteger(value.excludedYears) && value.excludedYears >= 0 && ['linear', 'log'].includes(value.scale) && typeof value.includeObserved === 'boolean';
  return false;
}

export function restoreDisplay(restore, getState, setValue, { display: restorePreferences = true, layers: restoreLayers = true } = {}) {
  const display = restore.display || {};
  if (restorePreferences) DISPLAY_KEYS.forEach((key) => {
    if (Object.hasOwn(display, key) && validPreference(key, display[key])) setValue(key, display[key]);
  });
  if (restoreLayers) LAYER_KEYS.forEach((key) => {
    if (!Array.isArray(restore.layers?.[key])) return;
    setValue(key, (getState()[key] || []).map((layer) => ({ ...layer,
      visible: restore.layers[key].includes(layer.key || layer.id) })));
  });
}

const metadata = (feature) => feature.properties.roads_detachment;
const label = (feature) => String(feature.properties.name || feature.properties.NAME ||
  feature.properties.OSUNUM || feature.properties.segment_id);
const numeric = (value, units = '') => Number.isFinite(value) ? `${value.toLocaleString(undefined, { maximumSignificantDigits: 6 })}${units ? ` ${units}` : ''}` : 'Unavailable';
export function profileScopeText(profiles) {
  if (!profiles.length) return 'No completed profile';
  if (profiles.some((p) => p.profile_scope === 'mixed_profile')) return 'Includes modeled road/fill/buffer or land-use OFEs';
  if (profiles.some((p) => !['road', 'mixed_profile'].includes(p.profile_scope))) return 'Unclassified profile';
  return 'Road profile';
}
export function roadStatus(feature) {
  const data = metadata(feature);
  if (data.state === 'partial') return 'Partial — aggregate unavailable';
  if (data.state !== 'complete') return 'No results';
  return `${data.rate_t_ha_year < 0 ? 'Negative result: ' : ''}${numeric(data.rate_t_ha_year, 't/ha/year')}`;
}
export function roadColor(feature, max, jet2Color) {
  const data = metadata(feature);
  if (data.state !== 'complete' || !Number.isFinite(data.rate_t_ha_year)) return [140, 140, 140, 255];
  if (data.rate_t_ha_year < 0) return [130, 60, 150, 255];
  return jet2Color(max > 0 ? Math.min(1, data.rate_t_ha_year / max) : 0);
}

export function createRoadsController({ ctx, deck, getState, setValue, applyLayers, jet2Color,
  fetchImpl = fetch, document: doc = document, location: loc = window.location }) {
  const panel = doc.getElementById('gl-roads-panel');
  const scope = doc.getElementById('gl-output-scope');
  const scopeStatus = doc.getElementById('gl-output-scope-status');
  const toggle = doc.getElementById('gl-roads-visible');
  const status = doc.getElementById('gl-roads-status');
  const legend = doc.getElementById('gl-roads-legend');
  const details = doc.getElementById('gl-roads-details');
  const selection = doc.getElementById('gl-roads-selection');
  const tableHost = doc.getElementById('gl-roads-table');
  let response = null;
  let maxOverride = Number.isFinite(getState().roadsMaxOverride) && getState().roadsMaxOverride > 0 ? getState().roadsMaxOverride : null;
  let requestGeneration = 0;
  let abortController;
  let failure = '';
  const restore = readScopeRestore(loc.hash);
  if (!panel) return { load: async () => {}, layer: () => null, tooltip: () => null, sync: () => {}, unavailable: () => {} };
  setValue('roadsVisible', new URL(loc.href).searchParams.get('roads') === 'on');
  if (restore.notice && scopeStatus) scopeStatus.textContent = String(restore.notice);
  if (ctx.outputScope === 'roads') {
    ['gl-scenario-select', 'gl-comparison-toggle'].forEach((id) => {
      const el = doc.getElementById(id);
      if (el) { el.disabled = true; if (id === 'gl-scenario-select') el.value = ''; else el.checked = false; }
    });
    if (scopeStatus) scopeStatus.textContent += ' Roads uses this run’s outputs. Map scenarios and comparison are unavailable in this scope.';
  }
  scope?.addEventListener('change', () => {
    requestGeneration += 1;
    abortController?.abort();
    loc.assign(scopeNavigationUrl(loc.href, scope.value, getState()));
  });
  toggle?.addEventListener('change', () => {
    setValue('roadsVisible', toggle.checked);
    sync();
    applyLayers();
  });
  function element(tag, text) {
    const el = doc.createElement(tag);
    if (text !== undefined) el.textContent = String(text);
    return el;
  }
  function maxValue() {
    if (maxOverride !== null) return maxOverride;
    return Math.max(0, ...(response?.features || []).map((f) => metadata(f).state === 'complete' ? metadata(f).rate_t_ha_year : 0));
  }
  function showDetails(feature, focus = false) {
    selection.replaceChildren(element('h4', label(feature)), element('p', `Prepared segment: ${feature.properties.segment_id}`),
      element('p', roadStatus(feature)), element('p', profileScopeText(metadata(feature).profiles)));
    const data = metadata(feature);
    selection.append(element('p', `Annual detachment: ${numeric(data.annual_detachment_kg, 'kg/year')}; modeled area: ${numeric(data.modeled_area_m2, 'm²')}; completed profiles: ${data.profile_count}.`));
    if (data.reason) selection.append(element('p', data.reason));
    data.profiles.forEach((p) => {
      selection.append(element('h5', `Profile ${p.segment_run_id}`), element('p',
        `Design: ${p.design || 'Unavailable'}; ${profileScopeText([p])}; simulation years: ${numeric(p.simulation_years)}. ` +
        `Modeled source road-segment length: ${numeric(p.segment_length_m, 'm')}. ` +
        `Annual detachment: ${numeric(p.soil_loss_kg, 'kg/year')}; modeled area: ${numeric(p.modeled_area_m2, 'm²')}; ` +
        `mean annual detachment: ${numeric(p.soil_loss_density_kg_m2 * 10, 't/ha/year')}.`));
    });
    details.open = true;
    if (focus) selection.focus();
  }
  function buildTable() {
    tableHost.replaceChildren();
    const table = element('table');
    table.append(element('caption', 'Road segment detachment — select a segment for profile details'));
    const heading = element('tr');
    ['Segment', 'Mean annual detachment (t/ha/year)', 'Profile scope'].forEach((name) => {
      const th = element('th', name); th.scope = 'col'; heading.append(th);
    });
    const head = element('thead'); head.append(heading); table.append(head);
    const body = element('tbody');
    response.features.forEach((feature) => {
      const row = element('tr');
      const cell = element('td');
      const button = element('button', label(feature)); button.type = 'button';
      button.addEventListener('click', () => showDetails(feature, true)); cell.append(button);
      row.append(cell, element('td', roadStatus(feature)), element('td', profileScopeText(metadata(feature).profiles)));
      body.append(row);
    });
    table.append(body); tableHost.append(table);
  }
  function buildLegend() {
    legend.replaceChildren(element('strong', 'Mean annual detachment (t/ha/year)'),
      element('p', `${response.roads_detachment.remainder_profile_count} replacement remainder profiles excluded from road lines.`),
      element('p', 'Line width is a visibility aid, not modeled width.'));
    const complete = response.features.filter((f) => metadata(f).state === 'complete');
    const nonnegative = complete.filter((f) => metadata(f).rate_t_ha_year >= 0);
    if (!nonnegative.length) {
      legend.append(element('p', complete.length ? 'Only negative results; no nonnegative color range.' : response.roads_detachment.reason || 'No complete numeric results; no color range.'));
      legend.append(element('p', 'Purple: negative result. Gray: no results or partial; not zero.'));
      return;
    }
    const max = maxValue();
    const bar = element('div');
    bar.style.height = '12px';
    const stops = Array.from({ length: 11 }, (_, i) => `rgba(${jet2Color(i / 10).slice(0, 3).join(',')},1)`);
    bar.style.background = `linear-gradient(to right, ${stops.join(',')})`;
    const rangeText = (value) => value > 0 ? `0 – ${numeric(value)} (linear; project-specific range)` : '0 (all nonnegative results are zero)';
    const rangeLabel = element('p', rangeText(max));
    legend.append(bar, rangeLabel);
    const inputLabel = element('label', 'Maximum (t/ha/year) ');
    const input = element('input'); input.type = 'number'; input.min = '0'; input.step = 'any'; input.value = String(Number(max.toPrecision(6)));
    input.addEventListener('change', () => {
      if (input.value !== '' && Number.isFinite(input.valueAsNumber) && input.valueAsNumber > 0) {
        maxOverride = input.valueAsNumber; setValue('roadsMaxOverride', maxOverride); rangeLabel.textContent = rangeText(maxValue()); applyLayers();
      } else {
        input.value = String(Number(maxValue().toPrecision(6)));
      }
    });
    inputLabel.append(input);
    const reset = element('button', 'Use project maximum'); reset.type = 'button';
    reset.addEventListener('click', () => { maxOverride = null; setValue('roadsMaxOverride', null); input.value = String(maxValue()); rangeLabel.textContent = rangeText(maxValue()); applyLayers(); });
    legend.append(inputLabel, reset, element('p', 'Purple: negative result. Gray: no results or partial; not zero.'));
  }
  function sync() {
    const incompatible = !!getState().currentScenarioPath || !!getState().comparisonMode;
    const usable = response && !incompatible && !failure;
    toggle.checked = !!getState().roadsVisible;
    toggle.disabled = !usable;
    status.textContent = failure || (incompatible ? 'Roads detachment is available only for the current run, outside map scenarios and comparison.' : response?.roads_detachment.reason || 'Current Roads results. Full-profile values; road centerlines only.');
    legend.hidden = !usable || !getState().roadsVisible;
    details.hidden = !usable || !getState().roadsVisible;
  }
  function unavailable(message = 'Roads results are no longer current. Prepare and run Roads again.') {
    requestGeneration += 1;
    abortController?.abort();
    response = null; failure = message;
    selection.replaceChildren(); tableHost.replaceChildren(); legend.replaceChildren();
    if (scope) scope.querySelector('option[value="roads"]').disabled = true;
    if (scopeStatus) scopeStatus.textContent = `${message} Baseline remains available.`;
    sync(); applyLayers();
  }
  async function load() {
    const generation = ++requestGeneration;
    abortController?.abort(); abortController = new AbortController();
    response = null; failure = ''; selection.replaceChildren();
    const url = `${ctx.sitePrefix || ''}/runs/${encodeURIComponent(ctx.runid)}/${encodeURIComponent(ctx.config)}/resources/roads.json?view=detachment`;
    try {
      const result = await fetchImpl(url, { signal: abortController.signal, cache: 'no-store', headers: { Accept: 'application/json' } });
      if (generation !== requestGeneration) return;
      if (!result.ok) {
        if (result.status === 401 || result.status === 403) failure = 'Roads access was denied. Sign in or check project access.';
        else if (result.status === 409) {
          const body = await result.json();
          if (generation !== requestGeneration) return;
          failure = typeof body.error === 'string' ? body.error : body.error?.message || 'Roads results are not current. Prepare and run Roads again.';
          if (scope) scope.querySelector('option[value="roads"]').disabled = true;
        } else if (result.status === 404) failure = 'Roads results are not available for this project.';
        else failure = 'Roads results could not be read. Reload to retry or contact support.';
      } else {
        const data = await result.json();
        if (generation !== requestGeneration) return;
        if (data.type !== 'FeatureCollection' || !Array.isArray(data.features) || !data.roads_detachment) throw new Error('Invalid Roads response');
        response = data; buildTable(); buildLegend();
      }
    } catch (error) {
      if (generation !== requestGeneration || error.name === 'AbortError') return;
      failure = 'Roads results could not be read. Reload to retry or contact support.';
    }
    if (generation !== requestGeneration) return;
    sync(); applyLayers();
  }
  function layer() {
    if (!response || failure || !getState().roadsVisible || getState().currentScenarioPath || getState().comparisonMode) return null;
    const max = maxValue();
    return new deck.GeoJsonLayer({ id: 'roads-detachment', data: response, pickable: true,
      stroked: true, filled: false, lineWidthUnits: 'pixels', getLineWidth: 4, lineWidthMinPixels: 4,
      lineWidthMaxPixels: 10, getLineColor: (feature) => roadColor(feature, max, jet2Color),
      updateTriggers: { getLineColor: [max] },
      onClick: ({ object }) => { if (object) showDetails(object); return true; } });
  }
  function tooltip(info) {
    if (!info.layer?.id?.startsWith('roads-detachment') || !info.object) return null;
    return { text: `${label(info.object)}\n${roadStatus(info.object)}\n${profileScopeText(metadata(info.object).profiles)}` };
  }
  return { load, layer, tooltip, sync, unavailable };
}
