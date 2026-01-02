const globalScope = typeof window !== 'undefined' ? window : globalThis;
const STATE_KEY = '__STORM_EVENT_ANALYZER_STATE__';
const SUBSCRIBERS_KEY = '__STORM_EVENT_ANALYZER_SUBSCRIBERS__';

const defaultState = {
  selectedMetric: null,
  filterRangePct: 10,
  includeWarmup: true,
  eventRows: [],
  selectedEventSimDayIndex: null,
  eventError: null,
  unitPrefs: null,
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
    if (!sub.keys || changedKeys.some((key) => sub.keys.has(key))) {
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
