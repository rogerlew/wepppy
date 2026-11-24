import { DASHBOARD_MODES, getFeatureKeyFromProperties, resolveTopazIdFromProperties } from '../batch-keys.js';

export function resolveFeatureIdentity(props, state) {
  const topazId = resolveTopazIdFromProperties(props);
  const topazLabel = topazId != null ? String(topazId) : null;
  if (state && state.dashboardMode === DASHBOARD_MODES.BATCH) {
    const key = getFeatureKeyFromProperties(props) || null;
    const runLabelRaw = props && (props.leaf_runid || props.runid || props.run_id || null);
    const runLabel = runLabelRaw != null && String(runLabelRaw).trim() ? String(runLabelRaw) : null;
    return { key, topazId: topazLabel, runLabel };
  }
  const key = topazLabel;
  return { key, topazId: topazLabel, runLabel: null };
}

export function pickActive(arr) {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (arr[i].visible) {
      return arr[i];
    }
  }
  return null;
}

export function landuseValue(mode, row) {
  if (!row) return null;
  if (mode === 'dominant') return row.dominant || row.cover_desc || row.key || row._map || null;
  const v = Number(row[mode]);
  return Number.isFinite(v) ? v : null;
}

export function soilsValue(mode, row) {
  if (!row) return null;
  if (mode === 'dominant') return row.texture || row.simple_texture || row.desc || row.dom_texture || row.dom_desc || null;
  const v = Number(row[mode]);
  return Number.isFinite(v) ? v : null;
}

export function modeValue(mode, row) {
  if (!row) return null;
  const v = Number(row[mode]);
  return Number.isFinite(v) ? v : null;
}

export function scalarValue(row) {
  if (row == null) return null;
  const v = Number(row);
  return Number.isFinite(v) ? v : null;
}

export function weppEventValue(mode, row) {
  if (!row || (['event_P', 'event_Q', 'event_ET'].includes(mode) && row[mode] == null)) return null;
  const v = Number(row[mode]);
  return Number.isFinite(v) ? v : null;
}
