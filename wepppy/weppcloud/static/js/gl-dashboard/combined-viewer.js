import { createMapController } from './map/controller.js';
import { createBasemapController } from './map/basemap-controller.js';
import { VARIABLES, factor, unitLabel, loadRun, shareUrl } from './combined-viewer-data.js';

const ctx = JSON.parse(document.getElementById('pcv-config').textContent);
const el = (name) => document.getElementById(`pcv-${name}`);
let units = ctx.units;
let variable = ctx.varname;
let ranges = Object.fromEntries(VARIABLES.map((key) => [key, ctx.varopts[key] ?? (units === 'SI' ? 10 : 0.1)]));
let view = {latitude: ctx.center[0], longitude: ctx.center[1], zoom: ctx.zoom};
let features = [];
let collectionData;
let selected = null;
let hillslopeCount = 0;
let map;
let phos = ctx.ws.every((run) => run.phosphorus);
el('variable').value = variable;
el('units').value = units;
el('variable').querySelector('[value="phosphorus"]').disabled = !phos;
if (!phos) el('availability').textContent = 'Phosphorus is unavailable for one or more selected watersheds.';
let basemap;
const controls = el('controls').querySelectorAll('input,select,button');
controls.forEach((control) => {control.disabled = true;});

function showDetails(feature) {
  selected = feature;
  const target = el('details');
  target.replaceChildren();
  if (!feature) return;
  const p = feature.properties;
  const text = document.createElement('p');
  text.textContent = `${p.runid} · Hillslope ${p.topaz_id}: ${(p.values[variable] / factor(variable, units)).toPrecision(6)} ${unitLabel(variable, units)}`;
  target.append(text);
  const link = document.createElement('a');
  link.textContent = 'View watershed run';
  link.href = `${ctx.sitePrefix}/runs/${encodeURIComponent(p.runid)}/${encodeURIComponent(p.cfg)}/`;
  target.append(link);
}
function render() {
  el('range').value = ranges[variable];
  const unavailable = variable === 'phosphorus' && !phos;
  el('feature').disabled = unavailable;
  if (unavailable) {
    showDetails(null);
    const legend = el('legend');
    legend.getContext('2d').clearRect(0, 0, legend.width, legend.height);
    el('legend-label').textContent = '';
    el('status').textContent = 'Selected phosphorus results are unavailable. Choose another result.';
    map.applyLayers([basemap]);
    return;
  }
  const cmap = window.createColormap({colormap: variable === 'loss' ? 'jet2' : variable === 'phosphorus' ? 'viridis' : 'winter', nshades: 64});
  const maxSI = ranges[variable] * factor(variable, units);
  const colorMax = variable === 'phosphorus' && maxSI < 1 ? maxSI ** 2 : maxSI;
  const layer = new window.deck.GeoJsonLayer({id: 'pcv-hillslopes', data: collectionData,
    pickable: true, filled: true, stroked: true, getLineColor: [60, 60, 60, 150], lineWidthMinPixels: 0.5,
    getFillColor: (feature) => {
      const hex = cmap.map(feature.properties.values[variable] / colorMax);
      return [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16)).concat(190);
    }, onClick: ({object}) => showDetails(object),
    updateTriggers: {getFillColor: [variable, units, ranges[variable]]}});
  map.applyLayers([basemap, layer]);
  const canvas = el('legend');
  const drawing = canvas.getContext('2d');
  for (let x = 0; x < canvas.width; x++) {
    drawing.fillStyle = cmap.map(x / (canvas.width - 1));
    drawing.fillRect(x, 0, 1, canvas.height);
  }
  el('legend-label').textContent = `0 — ${ranges[variable]} ${unitLabel(variable, units)}`;
  el('status').textContent = `${ctx.ws.length} watersheds · ${hillslopeCount} hillslopes loaded.`;
  if (selected) showDetails(selected);
}
async function initialize() {
  try {
    if (!window.deck) throw new Error('The map library could not load. Reload the page to retry.');
    basemap = createBasemapController({deck: window.deck,
  basemapDefs: {osm: {template: 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
    getUrl: (x, y, z) => `https://c.tile.openstreetmap.org/${z}/${x}/${y}.png`}},
  getState: () => ({}), setValue: () => {}}).createBaseLayer('osm');
    map = createMapController({deck: window.deck, target: el('map'), controllerOptions: true,
      // Dense legacy geometry can block pointer-down picking on software GPUs.
      // Preserve drag-distance checks while allowing the resulting delayed release.
      eventRecognizerOptions: {click: {time: 5000}},
      initialViewState: view, onViewStateChange: ({viewState}) => {view = viewState;},
      onError: (error) => {el('status').textContent = `Map error: ${error.message}`;},
      getTooltip: ({object}) => object ? `${object.properties.runid}\nHillslope ${object.properties.topaz_id}` : null,
      layers: [basemap]});
    // Bounded sequential loading avoids saturating the query service for large collections.
    for (const run of ctx.ws) features.push(...await loadRun(run, ctx.sitePrefix));
    phos = ctx.ws.every((run) => run.phosphorus);
    el('variable').querySelector('[value="phosphorus"]').disabled = !phos;
    if (!phos) el('availability').textContent = 'Phosphorus is unavailable for one or more selected watersheds.';
    collectionData = {type: 'FeatureCollection', features};
    const listed = new Set();
    for (let i = 0; i < features.length; i++) {
      const key = features[i].properties.key;
      if (listed.has(key)) continue;
      listed.add(key);
      const option = document.createElement('option');
      option.value = String(i);
      option.textContent = `${features[i].properties.runid} / ${features[i].properties.topaz_id}`;
      el('feature').append(option);
    }
    hillslopeCount = listed.size;
    controls.forEach((control) => {control.disabled = false;});
    render();
  } catch (error) {
    features = [];
    if (map) map.applyLayers([basemap]);
    el('status').textContent = `Unable to load the complete collection. ${error.message}`;
    el('controls').querySelectorAll('input,select,button').forEach((control) => {control.disabled = true;});
  }
}
el('controls').addEventListener('submit', (event) => {
  event.preventDefault();
  const value = Number(el('range').value);
  if (!Number.isFinite(value) || value <= 0) {el('status').textContent = 'Enter a positive color range maximum.'; return;}
  ranges[variable] = value;
  render();
});
el('variable').addEventListener('change', () => {variable = el('variable').value; selected = null; el('details').replaceChildren(); render();});
el('units').addEventListener('change', () => {
  const next = el('units').value;
  ranges = Object.fromEntries(VARIABLES.map((key) => [key, ranges[key] * factor(key, units) / factor(key, next)]));
  units = next; render();
});
el('feature').addEventListener('change', () => showDetails(el('feature').value === '' ? null : features[Number(el('feature').value)]));
el('share').addEventListener('click', () => {el('share-url').value = shareUrl(ctx, view, variable, units, ranges, window.location.origin);});
initialize();
