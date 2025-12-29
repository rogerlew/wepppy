/**
 * OpenET data helpers (summary refresh + selection resolution).
 */

const OPENET_PATH = 'openet/openet_ts.parquet';

function normalizeMonthIndex(index, months) {
  if (!Array.isArray(months) || !months.length) return null;
  if (Number.isFinite(index) && index >= 0 && index < months.length) {
    return index;
  }
  return months.length - 1;
}

function resolveDatasetKey(state) {
  if (!state) return null;
  const layers = state.openetLayers || [];
  if (state.openetSelectedDatasetKey) {
    const exists = layers.some((layer) => layer.datasetKey === state.openetSelectedDatasetKey);
    if (exists) return state.openetSelectedDatasetKey;
  }
  const visible = layers.find((layer) => layer.visible);
  if (visible && visible.datasetKey) return visible.datasetKey;
  return layers.length ? layers[0].datasetKey : null;
}

export function createOpenetDataManager({ getState, setState, postBaseQueryEngine }) {
  async function refreshOpenetData() {
    const state = getState();
    const metadata = state.openetMetadata;
    if (!metadata || !Array.isArray(metadata.months) || !metadata.months.length) {
      return false;
    }

    const datasetKey = resolveDatasetKey(state);
    if (!datasetKey) return false;

    const selectedIndex = normalizeMonthIndex(state.openetSelectedMonthIndex, metadata.months);
    if (selectedIndex == null) return false;
    const entry = metadata.months[selectedIndex];
    if (!entry || !Number.isFinite(entry.year) || !Number.isFinite(entry.month)) {
      return false;
    }

    const payload = {
      datasets: [{ path: OPENET_PATH, alias: 'openet' }],
      columns: ['openet.topaz_id AS topaz_id', 'openet.value AS value'],
      filters: [
        { column: 'openet.dataset_key', op: '=', value: datasetKey },
        { column: 'openet.year', op: '=', value: entry.year },
        { column: 'openet.month', op: '=', value: entry.month },
      ],
    };

    try {
      const result = await postBaseQueryEngine(payload);
      const summary = {};
      if (result && Array.isArray(result.records)) {
        for (const row of result.records) {
          const topazId = row.topaz_id;
          if (topazId != null) {
            summary[String(topazId)] = row.value;
          }
        }
      }

      let min = Infinity;
      let max = -Infinity;
      for (const key of Object.keys(summary)) {
        const val = Number(summary[key]);
        if (Number.isFinite(val)) {
          if (val < min) min = val;
          if (val > max) max = val;
        }
      }
      if (!Number.isFinite(min)) min = 0;
      if (!Number.isFinite(max)) max = 1;
      if (max <= min) max = min + 1;

      setState({
        openetSummary: summary,
        openetRanges: { min, max },
        openetSelectedDatasetKey: datasetKey,
        openetSelectedMonthIndex: selectedIndex,
      });
      return true;
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to refresh OpenET data', err);
      return false;
    }
  }

  return { refreshOpenetData };
}
