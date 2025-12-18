/**
 * RAP data helpers (summary refresh + active layer selection).
 */

export function createRapDataManager({ getState, setValue, postQueryEngine }) {
  function pickActiveRapLayer() {
    const layers = getState().rapLayers || [];
    for (let i = layers.length - 1; i >= 0; i--) {
      if (layers[i].visible) {
        return layers[i];
      }
    }
    return null;
  }

  async function refreshRapData() {
    const st = getState();
    if (!st.rapSelectedYear) return;

    if (st.rapCumulativeMode) {
      const selectedBands = (st.rapLayers || []).filter((l) => l.selected !== false);
      if (!selectedBands.length) {
        setValue('rapSummary', {});
        return;
      }
      const bandIds = selectedBands.map((l) => l.bandId);
      const payload = {
        datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
        columns: ['rap.topaz_id AS topaz_id', 'rap.value AS value'],
        filters: [
          { column: 'rap.year', op: '=', value: st.rapSelectedYear },
          { column: 'rap.band', op: 'IN', value: bandIds },
        ],
      };
      try {
        const res = await postQueryEngine(payload);
        if (res && res.records) {
          const sumByTopaz = {};
          for (const row of res.records) {
            const tid = String(row.topaz_id);
            sumByTopaz[tid] = (sumByTopaz[tid] || 0) + (row.value || 0);
          }
          setValue('rapSummary', sumByTopaz);
        }
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('gl-dashboard: failed to refresh RAP cumulative data', err);
      }
      return;
    }

    const activeLayer = pickActiveRapLayer();
    if (!activeLayer) return;
    const payload = {
      datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
      columns: ['rap.topaz_id AS topaz_id', 'rap.value AS value'],
      filters: [
        { column: 'rap.year', op: '=', value: st.rapSelectedYear },
        { column: 'rap.band', op: '=', value: activeLayer.bandId },
      ],
    };
    try {
      const res = await postQueryEngine(payload);
      if (res && res.records) {
        const summary = {};
        for (const row of res.records) {
          summary[String(row.topaz_id)] = row.value;
        }
        setValue('rapSummary', summary);
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to refresh RAP data', err);
    }
  }

  return { refreshRapData, pickActiveRapLayer };
}

