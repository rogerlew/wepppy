// Shared mutable state for gl-dashboard. Keeps all runtime state in one place
// and provides a simple subscription mechanism for interested consumers.

const state = {
  currentScenarioPath: '',
  comparisonMode: false,
  baseSummaryCache: {},
  comparisonDiffRanges: {},

  subcatchmentsVisible: true,
  subcatchmentLabelsVisible: false,
  currentBasemapKey: 'googleTerrain',
  currentViewState: null,

  graphFocus: false,
  activeGraphKey: null,
  graphDataCache: {},
  hillLossCache: {},
  channelLossCache: {},
  outletAllYearsCache: {},
  hillslopeAreaCache: {},

  detectedLayers: [],
  landuseLayers: [],
  soilsLayers: [],
  hillslopesLayers: [],
  watarLayers: [],
  weppLayers: [],
  weppYearlyLayers: [],
  weppEventLayers: [],
  rapLayers: [],

  landuseSummary: null,
  soilsSummary: null,
  hillslopesSummary: null,
  watarSummary: null,
  weppSummary: null,
  weppStatistic: 'mean',

  weppYearlyMetadata: null,
  weppYearlySelectedYear: null,
  weppYearlySummary: null,
  weppYearlyRanges: {},
  weppYearlyDiffRanges: {},
  weppYearlyCache: {},
  baseWeppYearlyCache: {},

  weppEventSummary: null,
  weppEventMetadata: null,
  weppEventSelectedDate: null,
  weppEventRanges: {},

  rapSummary: null,
  rapMetadata: null,
  rapSelectedYear: null,
  rapCumulativeMode: false,

  subcatchmentsGeoJson: null,
  graphHighlightedTopazId: null,

  watarRanges: {},
  weppRanges: {},

  geoTiffLoader: null,
};

const subscribers = [];

function notify(changedKeys) {
  if (!changedKeys.length) return;
  subscribers.forEach((sub) => {
    if (!sub.keys || changedKeys.some((k) => sub.keys.has(k))) {
      sub.callback(state, changedKeys);
    }
  });
}

export function getState() {
  return state;
}

export function getValue(key) {
  return state[key];
}

export function setState(updates, { silent = false } = {}) {
  const changed = [];
  Object.keys(updates || {}).forEach((key) => {
    const next = updates[key];
    if (state[key] !== next) {
      state[key] = next;
      changed.push(key);
    }
  });
  if (!silent) {
    notify(changed);
  }
}

export function setValue(key, value, options) {
  setState({ [key]: value }, options);
}

export function initState(initial = {}) {
  setState(initial, { silent: true });
}

export function subscribe(keys, callback) {
  const keySet = !keys ? null : new Set(Array.isArray(keys) ? keys : [keys]);
  const sub = { keys: keySet, callback };
  subscribers.push(sub);
  return () => {
    const idx = subscribers.indexOf(sub);
    if (idx !== -1) {
      subscribers.splice(idx, 1);
    }
  };
}
