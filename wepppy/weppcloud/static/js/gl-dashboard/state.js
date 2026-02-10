import { GRAPH_MODES } from './config.js';

/**
 * Shared mutable state for gl-dashboard. Single source of truth plus subscriptions.
 * Pure state container: no DOM/deck usage.
 */

const globalScope = typeof window !== 'undefined' ? window : globalThis;
const STATE_KEY = '__GL_DASHBOARD_STATE__';
const SUBSCRIBERS_KEY = '__GL_DASHBOARD_STATE_SUBSCRIBERS__';

const defaultState = {
  dashboardMode: 'run',
  batchModeEnabled: false,
  currentScenarioPath: '',
  comparisonMode: false,
  baseSummaryCache: {},
  comparisonDiffRanges: {},
  baseScenarioLabel: 'Undisturbed',

  subcatchmentsVisible: true,
  subcatchmentLabelsVisible: false,
  channelsVisible: true,
  channelLabelsVisible: false,
  currentBasemapKey: 'googleTerrain',
  currentViewState: null,

  graphFocus: false,
  graphMode: GRAPH_MODES.MINIMIZED,
  activeGraphKey: null,
  graphDataCache: {},
  cumulativeMeasure: 'runoff_volume',
  cumulativeScenarioSelections: [],
  hillLossCache: {},
  channelLossCache: {},
  outletAllYearsCache: {},
  hillslopeAreaCache: {},

  detectedLayers: [],
  landuseLayers: [],
  soilsLayers: [],
  hillslopesLayers: [],
  d8DirectionLayer: null,
  channelsLayers: [],
  watarLayers: [],
  weppLayers: [],
  weppChannelLayers: [],
  weppYearlyLayers: [],
  weppEventLayers: [],
  rapLayers: [],
  openetLayers: [],

  landuseSummary: null,
  soilsSummary: null,
  hillslopesSummary: null,
  watarSummary: null,
  weppSummary: null,
  weppChannelSummary: null,
  weppStatistic: 'mean',

  weppYearlyMetadata: null,
  weppYearlySelectedYear: null,
  weppYearlySummary: null,
  weppYearlyRanges: {},
  weppYearlyDiffRanges: {},
  weppYearlyCache: {},
  baseWeppYearlyCache: {},
  weppYearlyChannelLayers: [],
  weppYearlyChannelSummary: null,
  weppYearlyChannelRanges: {},
  weppYearlyChannelCache: {},

  weppEventSummary: null,
  weppEventMetadata: null,
  weppEventSelectedDate: null,
  weppEventRanges: {},

  rapSummary: null,
  rapMetadata: null,
  rapSelectedYear: null,
  rapCumulativeMode: false,
  openetSummary: null,
  openetMetadata: null,
  openetRanges: {},
  openetSelectedDatasetKey: null,
  openetSelectedMonthIndex: null,
  openetYearlySelectedDatasetKey: null,
  openetYearlyWaterYear: true,
  openetYearlyStartMonth: 10,
  openetYearlySelectedYear: null,
  openetYearlyCache: {},

  climateYearlySelectedYear: null,
  climateWaterYear: true,
  climateStartMonth: 10,

  // Per-graph log scale preferences for boxplots (keyed by graph key)
  boxplotLogScale: {},

  subcatchmentsGeoJson: null,
  channelsGeoJson: null,
  channelLabelsData: null,
  graphHighlightedTopazId: null,

  watarRanges: {},
  weppRanges: {},
  weppChannelRanges: {},

  geoTiffLoader: null,
};

const existingState = globalScope[STATE_KEY];
const state = existingState || {};

function cloneDefault(value) {
  if (Array.isArray(value)) {
    return [...value];
  }
  if (value && typeof value === 'object') {
    return { ...value };
  }
  return value;
}

function ensureDefaults(target, defaults) {
  Object.keys(defaults).forEach((key) => {
    const fallback = defaults[key];
    const requiresObject = Array.isArray(fallback) || (fallback && typeof fallback === 'object');
    if (target[key] === undefined || (target[key] === null && requiresObject)) {
      target[key] = cloneDefault(fallback);
    }
  });
}

if (!existingState) {
  Object.assign(state, defaultState);
  globalScope[STATE_KEY] = state;
} else {
  ensureDefaults(state, defaultState);
}

const subscribers = globalScope[SUBSCRIBERS_KEY] || [];
if (!globalScope[SUBSCRIBERS_KEY]) {
  globalScope[SUBSCRIBERS_KEY] = subscribers;
}

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
