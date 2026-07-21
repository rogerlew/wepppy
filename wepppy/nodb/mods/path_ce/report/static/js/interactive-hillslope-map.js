let deckApiCache = null;

function getDeckGlobal() {
  return window.deck || window.deckgl || window.deckGl || null;
}

function hasDeckApi(globalDeck) {
  return Boolean(
    globalDeck?.Deck &&
    globalDeck?.GeoJsonLayer &&
    globalDeck?.MapView &&
    globalDeck?.WebMercatorViewport
  );
}

function loadScript(url, timeoutMs = 15000) {
  return new Promise((resolve, reject) => {
    const existing = Array.from(document.scripts).find(s => s.src === url);
    if (existing) {
      if (hasDeckApi(getDeckGlobal())) {
        resolve(true);
        return;
      }
      existing.addEventListener('load', () => resolve(true), {once: true});
      existing.addEventListener('error', () => reject(new Error(`Failed to load script: ${url}`)), {once: true});
      return;
    }

    const script = document.createElement('script');
    script.src = url;
    script.async = false;

    const timer = setTimeout(() => {
      script.remove();
      reject(new Error(`Timed out loading script: ${url}`));
    }, timeoutMs);

    script.onload = () => {
      clearTimeout(timer);
      resolve(true);
    };

    script.onerror = () => {
      clearTimeout(timer);
      reject(new Error(`Failed to load script: ${url}`));
    };

    document.head.appendChild(script);
  });
}

async function ensureDeckGlobal() {
  if (hasDeckApi(getDeckGlobal())) {
    return true;
  }

  const candidateUrls = [
    'static/js/vendor/deck.gl-8.9.31.min.js',
    './static/js/vendor/deck.gl-8.9.31.min.js',
    '/static/js/vendor/deck.gl-8.9.31.min.js',
    'https://unpkg.com/deck.gl@8.9.31/dist.min.js',
    'https://cdn.jsdelivr.net/npm/deck.gl@8.9.31/dist.min.js'
  ];

  let lastError = null;
  for (const url of candidateUrls) {
    try {
      await loadScript(url);
      if (hasDeckApi(getDeckGlobal())) {
        return true;
      }
    } catch (err) {
      lastError = err;
    }
  }

  if (lastError) {
    throw lastError;
  }
  throw new Error('deck.gl global API not available after script load attempts.');
}

async function resolveDeckApi() {
  if (deckApiCache) {
    return deckApiCache;
  }

  if (!hasDeckApi(getDeckGlobal())) {
    await ensureDeckGlobal();
  }

  const globalDeck = getDeckGlobal();
  if (hasDeckApi(globalDeck)) {
    deckApiCache = {
      Deck: globalDeck.Deck,
      GeoJsonLayer: globalDeck.GeoJsonLayer,
      MapView: globalDeck.MapView,
      WebMercatorViewport: globalDeck.WebMercatorViewport
    };
    return deckApiCache;
  }

  throw new Error('deck.gl failed to load from global bundle.');
}

const COLORS = {
  untreated: [211, 211, 211, 200],
  tier1: [178, 223, 138, 220],
  tier2: [51, 160, 44, 220],
  tier3: [0, 100, 0, 220],
  outline: [0, 0, 0, 180],
  untreatable: [220, 32, 32, 220],
  sdydIncrease: [255, 200, 0, 255],
  channels: [80, 165, 214, 255]
};

const FEATURE_ID_FIELDS = [
  {key: 'wepp_id', label: 'WeppID'},
  {key: 'WeppID', label: 'WeppID'},
  {key: 'weppId', label: 'WeppID'},
  {key: 'WEPPID', label: 'WeppID'},
  {key: 'contrast_id', label: 'Contrast ID'},
  {key: 'contrastId', label: 'Contrast ID'},
  {key: 'ContrastID', label: 'Contrast ID'},
  {key: 'CONTRAST_ID', label: 'Contrast ID'}
];

const FEATURE_ID_FIELD_GROUPS = {
  wepp_id: FEATURE_ID_FIELDS.filter(field => field.label === 'WeppID'),
  contrast_id: FEATURE_ID_FIELDS.filter(field => field.label === 'Contrast ID')
};

function parseJsonish(value) {
  if (value == null) {
    return null;
  }
  if (Array.isArray(value)) {
    return value;
  }
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
    try {
      return JSON.parse(trimmed);
    } catch (err) {
      return null;
    }
  }
  return null;
}

function parseNumberArray(value) {
  const parsed = parseJsonish(value);
  if (Array.isArray(parsed)) {
    return parsed.map(Number).filter(Number.isFinite);
  }
  if (typeof value === 'string') {
    const matches = value.match(/-?\d+(?:\.\d+)?/g);
    if (!matches) {
      return [];
    }
    return matches.map(Number).filter(Number.isFinite);
  }
  return [];
}

function parseNestedNumberArray(value) {
  const parsed = parseJsonish(value);
  if (Array.isArray(parsed)) {
    return parsed.map(item => (Array.isArray(item) ? item.map(Number).filter(Number.isFinite) : []));
  }
  if (typeof value === 'string') {
    // Fallback for CSV strings that are valid-ish arrays but not strict JSON.
    const normalized = value.trim();
    if (normalized.startsWith('[') && normalized.endsWith(']')) {
      try {
        const parsedFallback = JSON.parse(normalized.replace(/'/g, '"'));
        if (Array.isArray(parsedFallback)) {
          return parsedFallback.map(item => (Array.isArray(item) ? item.map(Number).filter(Number.isFinite) : []));
        }
      } catch (err) {
        return [];
      }
    }
  }
  return [];
}

function parseHillslopesSdyd(value) {
  const parsed = parseJsonish(value);
  if (Array.isArray(parsed)) {
    return parsed
      .filter(pair => Array.isArray(pair) && pair.length >= 2)
      .map(pair => ({ weppId: Number(pair[0]), finalSdyd: Number(pair[1]) }))
      .filter(h => Number.isFinite(h.weppId) && Number.isFinite(h.finalSdyd));
  }
  return [];
}

function getUntreatableFromHillslopes(hillslopesSdyd, sdydThreshold) {
  return hillslopesSdyd
    .filter(h => h.finalSdyd > sdydThreshold)
    .map(h => h.weppId);
}

function getFeatureIdentifier(feature, preferredIdField = null) {
  const props = feature?.properties || {};
  if (preferredIdField) {
    const preferredLabel = preferredIdField === 'contrast_id' ? 'Contrast ID' : 'WeppID';

    // Try exact field first.
    const strictId = Number(props[preferredIdField]);
    if (Number.isFinite(strictId)) {
      return {id: strictId, label: preferredLabel};
    }

    // Fall back to known aliases so `wepp_id` can match `WeppID` and similar.
    const preferredGroup = FEATURE_ID_FIELD_GROUPS[preferredIdField] || [{key: preferredIdField, label: preferredLabel}];
    for (const field of preferredGroup) {
      const aliasId = Number(props[field.key]);
      if (Number.isFinite(aliasId)) {
        return {id: aliasId, label: field.label};
      }
    }

    return {id: null, label: preferredLabel};
  }

  const fields = FEATURE_ID_FIELDS;
  for (const field of fields) {
    const id = Number(props[field.key]);
    if (Number.isFinite(id)) {
      return {id, label: field.label};
    }
  }
  return {id: null, label: 'ID'};
}

function getGeojsonBounds(geojson) {
  let minLng = Infinity;
  let minLat = Infinity;
  let maxLng = -Infinity;
  let maxLat = -Infinity;

  function visitCoords(coords) {
    if (!Array.isArray(coords)) {
      return;
    }
    if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
      const [lng, lat] = coords;
      if (lng < minLng) minLng = lng;
      if (lng > maxLng) maxLng = lng;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
      return;
    }
    for (const item of coords) {
      visitCoords(item);
    }
  }

  if (geojson?.features) {
    for (const feature of geojson.features) {
      visitCoords(feature?.geometry?.coordinates);
    }
  }

  if (!Number.isFinite(minLng)) {
    return null;
  }
  return [
    [minLng, minLat],
    [maxLng, maxLat]
  ];
}

function normalizeRows(rows) {
  const selectionByKey = new Map();
  const sdydValues = new Set();
  const sddcValues = new Set();

  for (const row of rows) {
    const sdyd = Number(row.sdyd_threshold);
    const sddc = Number(row.sddc_threshold);
    if (!Number.isFinite(sdyd) || !Number.isFinite(sddc)) {
      continue;
    }

    const selected = parseNumberArray(row.selected_hillslopes);
    const treatments = parseNestedNumberArray(row.treatment_hillslopes);
    const hillslopesSdyd = parseHillslopesSdyd(row.hillslopes_sdyd);
    const untreatable = getUntreatableFromHillslopes(hillslopesSdyd, sdyd);
    const sdydIncreaseIds = parseNumberArray(row.untreatable_sdyd_increase);

    const key = `${sdyd}_${sddc}`;
    selectionByKey.set(key, {
      sdyd,
      sddc,
      selected,
      treatments,
      untreatable,
      sdydIncreaseIds,
      totalCost: Number(row.total_cost),
      finalSddc: Number(row.final_Sddc)
    });

    sdydValues.add(sdyd);
    sddcValues.add(sddc);
  }

  return {
    selectionByKey,
    sdydValues: Array.from(sdydValues).sort((a, b) => a - b),
    sddcValues: Array.from(sddcValues).sort((a, b) => a - b)
  };
}

function formatNumber(value, digits = 0) {
  if (!Number.isFinite(value)) {
    return 'N/A';
  }
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

function parseCsvFallback(csvText) {
  const rows = [];
  let row = [];
  let cell = '';
  let inQuotes = false;

  for (let i = 0; i < csvText.length; i += 1) {
    const ch = csvText[i];

    if (inQuotes) {
      if (ch === '"') {
        if (csvText[i + 1] === '"') {
          cell += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        cell += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
      continue;
    }

    if (ch === ',') {
      row.push(cell);
      cell = '';
      continue;
    }

    if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && csvText[i + 1] === '\n') {
        i += 1;
      }
      row.push(cell);
      cell = '';
      // Skip blank trailing lines
      if (row.length > 1 || (row.length === 1 && row[0].trim() !== '')) {
        rows.push(row);
      }
      row = [];
      continue;
    }

    cell += ch;
  }

  if (cell.length > 0 || row.length > 0) {
    row.push(cell);
    rows.push(row);
  }

  if (rows.length === 0) {
    return [];
  }

  const headers = rows[0].map(h => (h || '').trim());
  const out = [];
  for (let r = 1; r < rows.length; r += 1) {
    const values = rows[r];
    if (!values || values.length === 0) {
      continue;
    }
    const obj = {};
    for (let c = 0; c < headers.length; c += 1) {
      obj[headers[c]] = values[c] ?? '';
    }
    out.push(obj);
  }
  return out;
}

function parseCsvRows(csvText) {
  if (window.Papa && typeof window.Papa.parse === 'function') {
    const parsed = window.Papa.parse(csvText, {
      header: true,
      dynamicTyping: false,
      skipEmptyLines: true
    });
    if (parsed.errors && parsed.errors.length) {
      console.warn('PapaParse reported CSV parse warnings:', parsed.errors.slice(0, 3));
    }
    return parsed.data || [];
  }
  return parseCsvFallback(csvText);
}

function createSlider(values, initialValue, labelText) {
  const wrapper = document.createElement('div');
  wrapper.className = 'hillmap-control hillmap-slider-control';

  const header = document.createElement('div');
  header.className = 'hillmap-slider-header';

  const label = document.createElement('span');
  label.className = 'hillmap-slider-label';
  label.textContent = labelText;

  const valueDisplay = document.createElement('span');
  valueDisplay.className = 'hillmap-slider-value';

  header.appendChild(label);
  header.appendChild(valueDisplay);

  const slider = document.createElement('input');
  slider.type = 'range';
  slider.className = 'hillmap-slider';
  slider.min = String(values[0]);
  slider.max = String(values[values.length - 1]);
  slider.step = '1';

  const initialIndex = values.indexOf(initialValue);
  let currentValue = initialIndex >= 0 ? initialValue : values[0];
  slider.value = String(currentValue);
  valueDisplay.textContent = String(currentValue);

  function findNearest(target) {
    let nearest = values[0];
    let minDiff = Math.abs(target - nearest);
    for (const v of values) {
      const diff = Math.abs(target - v);
      if (diff < minDiff) {
        minDiff = diff;
        nearest = v;
      }
    }
    return nearest;
  }

  slider.addEventListener('input', () => {
    const rawValue = Number(slider.value);
    const snapped = findNearest(rawValue);
    currentValue = snapped;
    valueDisplay.textContent = String(snapped);
  });

  slider.addEventListener('change', () => {
    slider.value = String(currentValue);
  });

  wrapper.appendChild(header);
  wrapper.appendChild(slider);

  return {
    wrapper,
    get value() {
      return currentValue;
    },
    set value(v) {
      const snapped = findNearest(v);
      currentValue = snapped;
      slider.value = String(snapped);
      valueDisplay.textContent = String(snapped);
    },
    addEventListener: (event, handler) => slider.addEventListener(event, handler)
  };
}

// WEPPPY-SEAM: treatment labels are configuration-driven (upstream hardcoded
// the three default mulch tiers); positions map to tier colors.
const DEFAULT_TIER_LABELS = ['0.5 tons/acre', '1 tons/acre', '2 tons/acre'];
const TIER_COLORS = [COLORS.tier1, COLORS.tier2, COLORS.tier3];

function resolveTierLabels(treatmentLabels) {
  if (Array.isArray(treatmentLabels) && treatmentLabels.length) {
    return treatmentLabels.slice(0, TIER_COLORS.length).map(String);
  }
  return DEFAULT_TIER_LABELS;
}

function renderLegend(container, selection, tierLabels) {
  container.innerHTML = '';
  const section = document.createElement('div');
  section.className = 'gl-legend-section';
  const title = document.createElement('div');
  title.className = 'gl-legend-section__title';
  title.textContent = 'Legend';
  section.appendChild(title);

  const labels = tierLabels || DEFAULT_TIER_LABELS;
  const items = [
    {label: 'Untreated', color: COLORS.untreated},
    ...labels.map((label, i) => ({label, color: TIER_COLORS[i] || COLORS.tier3})),
    {label: 'Sdyd increases after treatment', color: COLORS.sdydIncrease, outlineOnly: true},
    {label: 'Hillslope Sdyd threshold not met', color: COLORS.untreatable, outlineOnly: true}
  ];

  const categorical = document.createElement('div');
  categorical.className = 'gl-legend-categorical';
  for (const item of items) {
    const row = document.createElement('div');
    row.className = 'gl-legend-categorical__item';
    const swatch = document.createElement('span');
    swatch.className = 'gl-legend-categorical__swatch';
    swatch.style.backgroundColor = item.outlineOnly ? 'transparent' : `rgba(${item.color.join(',')})`;
    if (item.outlineOnly) {
      swatch.style.borderColor = `rgba(${item.color.join(',')})`;
    }
    const label = document.createElement('span');
    label.textContent = item.label;
    row.appendChild(swatch);
    row.appendChild(label);
    categorical.appendChild(row);
  }

  section.appendChild(categorical);
  container.appendChild(section);

  const metrics = document.createElement('div');
  metrics.className = 'hillmap-legend-metrics';
  metrics.innerHTML = `
    <div>Total Cost ($): <strong>${formatNumber(selection?.totalCost, 0)}</strong></div>
    <div>Final Outlet Sddc (tons): <strong>${formatNumber(selection?.finalSddc, 2)}</strong></div>
  `;
  container.appendChild(metrics);
}

window.initInteractiveHillslopeMap = async function initInteractiveHillslopeMap(options) {
  const {Deck, GeoJsonLayer, MapView, WebMercatorViewport} = await resolveDeckApi();

  const {
    containerId,
    container,
    csvUrl = 'gatecreek_threshold_analysis_results.csv',
    csvText = null,
    hillslopesUrl = 'subcatchments.WGS.geojson',
    hillslopesData = null,
    channelsUrl = 'channels.WGS.geojson',
    channelsData = null,
    initialSdyd = 20,
    initialSddc = 200,
    selectionIdField = null,
    treatmentLabels = null,
    height = 340
  } = options || {};

  // WEPPPY-SEAM: configuration-driven tier labels
  const tierLabels = resolveTierLabels(treatmentLabels);

  const root =
    container ||
    (containerId ? document.getElementById(containerId) : null) ||
    document.body;

  root.classList.add('hillmap-root');
  root.innerHTML = '';

  const controls = document.createElement('div');
  controls.className = 'hillmap-controls';
  const mapEl = document.createElement('div');
  mapEl.className = 'hillmap-map';
  mapEl.style.height = `${height}px`;
  const legend = document.createElement('div');
  legend.className = 'hillmap-legend';
  const tooltip = document.createElement('div');
  tooltip.className = 'hillmap-tooltip';
  tooltip.style.display = 'none';

  root.appendChild(controls);
  root.appendChild(mapEl);
  mapEl.appendChild(legend);
  root.appendChild(tooltip);

  const [resolvedCsvText, hillslopes, channels] = await Promise.all([
    csvText != null ? Promise.resolve(csvText) : fetch(csvUrl).then(res => res.text()),
    hillslopesData != null ? Promise.resolve(hillslopesData) : fetch(hillslopesUrl).then(res => res.json()),
    channelsData != null
      ? Promise.resolve(channelsData)
      : (channelsUrl ? fetch(channelsUrl).then(res => res.json()) : Promise.resolve(null))
  ]);

  const rows = parseCsvRows(resolvedCsvText);
  const {selectionByKey, sdydValues, sddcValues} = normalizeRows(rows);

  const sdydDefault = sdydValues.includes(initialSdyd) ? initialSdyd : sdydValues[0];
  const sddcDefault = sddcValues.includes(initialSddc) ? initialSddc : sddcValues[0];

  const sdydSlider = createSlider(sdydValues, sdydDefault, 'Hillslope Sediment Yield Threshold (tons/acre)');
  const sddcSlider = createSlider(sddcValues, sddcDefault, 'Outlet Sediment Discharge Threshold  (tons)');
  controls.appendChild(sdydSlider.wrapper);
  controls.appendChild(sddcSlider.wrapper);

  const bounds = getGeojsonBounds(hillslopes);
  const width = mapEl.clientWidth || 800;
  const viewport = new WebMercatorViewport({width, height});
  const {longitude, latitude, zoom} = bounds
    ? viewport.fitBounds(bounds, {padding: 40})
    : {longitude: 0, latitude: 0, zoom: 2};

  const deckInstance = new Deck({
    parent: mapEl,
    views: new MapView({repeat: false}),
    initialViewState: {longitude, latitude, zoom},
    controller: true,
    layers: []
  });

  let currentSelection = null;

  function getCategoryLabel(unitId, selection) {
    if (!selection || unitId == null) {
      return 'Untreated';
    }
    if (selection.untreatableSet?.has(unitId)) {
      return 'Hillslope Sdyd threshold not met';
    }
    // WEPPPY-SEAM: labels follow the configured treatments positionally
    if (selection.tier3Set?.has(unitId)) {
      return tierLabels[2] || 'Treatment 3';
    }
    if (selection.tier2Set?.has(unitId)) {
      return tierLabels[1] || 'Treatment 2';
    }
    if (selection.tier1Set?.has(unitId)) {
      return tierLabels[0] || 'Treatment 1';
    }
    return 'Untreated';
  }

  function updateTooltip(info) {
    if (!info?.object) {
      tooltip.style.display = 'none';
      return;
    }
    const {id: unitId, label: unitLabel} = getFeatureIdentifier(info.object, selectionIdField);
    if (unitId == null) {
      tooltip.style.display = 'none';
      return;
    }
    const category = getCategoryLabel(unitId, currentSelection);
    tooltip.innerHTML = `
      <div class="hillmap-tooltip__title">${unitLabel} ${unitId}</div>
      <div class="hillmap-tooltip__row">${category}</div>
      <div class="hillmap-tooltip__row">Sdyd: ${currentSelection?.sdyd ?? 'N/A'}</div>
      <div class="hillmap-tooltip__row">Sddc: ${currentSelection?.sddc ?? 'N/A'}</div>
    `;
    tooltip.style.display = 'block';
    tooltip.style.left = `${info.x + 12}px`;
    tooltip.style.top = `${info.y + 12}px`;
  }

  function buildLayers(selection) {
    if (selection) {
      selection.tier1Set = new Set(selection.treatments?.[0] || []);
      selection.tier2Set = new Set(selection.treatments?.[1] || []);
      selection.tier3Set = new Set(selection.treatments?.[2] || []);
      selection.untreatableSet = new Set(selection.untreatable || []);
    }

    const treatmentTier1 = new Set(selection?.treatments?.[0] || []);
    const treatmentTier2 = new Set(selection?.treatments?.[1] || []);
    const treatmentTier3 = new Set(selection?.treatments?.[2] || []);
    const untreatable = new Set(selection?.untreatable || []);
    const sdydIncreaseSet = new Set(selection?.sdydIncreaseIds || []);
    
    function getCategoryColor(unitId) {
      if (unitId == null) {
        return COLORS.untreated;
      }
      if (treatmentTier3.has(unitId)) {
        return COLORS.tier3;
      }
      if (treatmentTier2.has(unitId)) {
        return COLORS.tier2;
      }
      if (treatmentTier1.has(unitId)) {
        return COLORS.tier1;
      }
      return COLORS.untreated;
    }

    const selectionKey = selection ? `${selection.sdyd}_${selection.sddc}` : 'none';

    const baseLayer = new GeoJsonLayer({
      id: 'hillslopes-base',
      data: hillslopes,
      filled: true,
      stroked: true,
      lineWidthUnits: 'pixels',
      lineWidthMinPixels: 0.6,
      getLineColor: COLORS.outline,
      getFillColor: feature => getCategoryColor(getFeatureIdentifier(feature, selectionIdField).id),
      updateTriggers: {
        getFillColor: selectionKey
      },
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 120],
      onHover: updateTooltip
    });

    const untreatableLayer = new GeoJsonLayer({
      id: 'hillslopes-untreatable',
      data: hillslopes,
      filled: false,
      stroked: true,
      lineWidthUnits: 'pixels',
      lineWidthMinPixels: 0,
      getLineColor: COLORS.untreatable,
      getLineWidth: feature => (untreatable.has(getFeatureIdentifier(feature, selectionIdField).id) ? 3 : 0),
      updateTriggers: {
        getLineWidth: selectionKey
      },
      pickable: false
    });

    const sdydIncreaseLayer = new GeoJsonLayer({
      id: 'hillslopes-sdyd-increase',
      data: hillslopes,
      filled: false,
      stroked: true,
      lineWidthUnits: 'pixels',
      lineWidthMinPixels: 0,
      getLineColor: COLORS.sdydIncrease,
      getLineWidth: feature => (sdydIncreaseSet.has(getFeatureIdentifier(feature, selectionIdField).id) ? 3 : 0),
      updateTriggers: {
        getLineWidth: selectionKey
      },
      pickable: false
    });

    const layers = [];

    if (channels) {
      layers.push(
        new GeoJsonLayer({
          id: 'channels',
          data: channels,
          filled: false,
          stroked: true,
          lineWidthUnits: 'pixels',
          lineWidthMinPixels: 1.5,
          getLineColor: COLORS.channels,
          pickable: false
        })
      );
    }

    layers.push(baseLayer, sdydIncreaseLayer, untreatableLayer);

    return layers;
  }

  function updateSelection() {
    const sdyd = sdydSlider.value;
    const sddc = sddcSlider.value;
    const key = `${sdyd}_${sddc}`;
    let selection = selectionByKey.get(key);

    // Defensive fallback: if exact key is missing, use nearest available combination.
    if (!selection) {
      const sdydNum = Number(sdyd);
      const sddcNum = Number(sddc);
      let best = null;
      let bestDistance = Infinity;
      for (const candidate of selectionByKey.values()) {
        const distance = Math.abs(candidate.sdyd - sdydNum) + Math.abs(candidate.sddc - sddcNum);
        if (distance < bestDistance) {
          bestDistance = distance;
          best = candidate;
        }
      }
      selection = best;
    }

    currentSelection = selection;
    deckInstance.setProps({layers: buildLayers(selection)});
    renderLegend(legend, selection, tierLabels);
  }

  sdydSlider.addEventListener('input', updateSelection);
  sddcSlider.addEventListener('input', updateSelection);

  updateSelection();

  const resizeObserver = new ResizeObserver(() => {
    deckInstance.setProps({
      width: mapEl.clientWidth || width,
      height: mapEl.clientHeight || height
    });
  });
  resizeObserver.observe(mapEl);

  return {
    deck: deckInstance,
    updateSelection,
    destroy: () => {
      resizeObserver.disconnect();
      deckInstance.finalize();
    }
  };
};
