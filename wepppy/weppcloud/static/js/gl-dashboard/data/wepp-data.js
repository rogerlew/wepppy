/**
 * @typedef {Object} WeppDataManagerDeps
 * @property {{ sitePrefix: string, runid: string, config: string }} ctx Run-scoped identifiers used when hitting base Query Engine paths.
 * @property {() => any} getState Read the reactive dashboard state object.
 * @property {(key: string, value: any, options?: { silent?: boolean }) => void} setValue Write a single state key with notifications.
 * @property {(updates: Record<string, any>, options?: { silent?: boolean }) => void} setState Merge state updates with optional silent flag.
 * @property {(payload: Object) => Promise<{ records?: Object[] } | null>} postQueryEngine Query Engine POST for the active scenario.
 * @property {(payload: Object) => Promise<{ records?: Object[] } | null>} postBaseQueryEngine Query Engine POST for the base scenario (comparison).
 * @property {() => { mode: string } | null} pickActiveWeppEventLayer Resolve the currently selected WEPP event layer descriptor.
 * @property {string} WEPP_YEARLY_PATH Parquet path for yearly WEPP outputs (interchange/H.parquet alias).
 * @property {string} WEPP_LOSS_PATH Parquet path for soil loss outputs (reserved for future queries).
 */

/**
 * @typedef {Object} WeppDataManager
 * @property {(statistic: string, options?: { base?: boolean }) => Promise<Object|null>} fetchWeppSummary Fetch WEPP summary aggregated by topaz_id for a statistic.
 * @property {() => Promise<boolean>} refreshWeppStatisticData Refresh active WEPP summary and ranges for the current statistic.
 * @property {(summaryOverride?: Object|null) => Object|null} computeWeppRanges Compute min/max for WEPP summary modes.
 * @property {(summaryOverride?: Object|null) => Object|null} computeWeppYearlyRanges Compute min/max for yearly WEPP summaries.
 * @property {(year: number) => Object} computeWeppYearlyDiffRanges Compute yearly diff ranges against base cache for a year.
 * @property {(year: number) => Promise<Object|null>} loadBaseWeppYearlyData Load and cache base WEPP yearly summary for a year.
 * @property {() => Promise<boolean>} refreshWeppYearlyData Refresh scenario/base yearly summaries and diff ranges.
 * @property {(summaryOverride?: Object|null) => Object|null} computeWeppEventRanges Compute min/max for WEPP event summaries.
 * @property {() => Object|null} computeWeppEventDiffRanges Compute event diff ranges against base cache.
 * @property {() => Promise<Object|null>} loadBaseWeppEventData Load base WEPP event data for the selected date/layer.
 * @property {() => Promise<boolean>} refreshWeppEventData Refresh scenario event data (and base when in comparison).
 */

/**
 * @param {WeppDataManagerDeps} params
 * @returns {WeppDataManager}
 */
export function createWeppDataManager({
  ctx,
  getState,
  setValue,
  setState,
  postQueryEngine,
  postBaseQueryEngine,
  pickActiveWeppEventLayer,
  WEPP_YEARLY_PATH,
  WEPP_LOSS_PATH,
}) {
  // Placeholder to avoid unused warning until WEPP_LOSS_PATH is used for additional queries.
  void WEPP_LOSS_PATH;

  const WEPP_MODES = ['runoff_volume', 'subrunoff_volume', 'baseflow_volume', 'soil_loss', 'sediment_deposition', 'sediment_yield'];
  const WEPP_EVENT_MODES = ['event_P', 'event_Q', 'event_ET', 'event_peakro', 'event_tdet'];

  function buildWeppAggregations(statistic) {
    const stat = (statistic || 'mean').toLowerCase();
    const measureMap = {
      runoff_volume: { column: '"Runoff Volume"', formula: 'loss.{col} / hill.area * 1000', label: 'mm' },
      subrunoff_volume: { column: '"Subrunoff Volume"', formula: 'loss.{col} / hill.area * 1000', label: 'mm' },
      baseflow_volume: { column: '"Baseflow Volume"', formula: 'loss.{col} / hill.area * 1000', label: 'mm' },
      soil_loss: { column: '"Soil Loss"', formula: 'loss.{col} / hill.area * 10', label: 't/ha' },
      sediment_deposition: { column: '"Sediment Deposition"', formula: 'loss.{col} / hill.area * 10', label: 't/ha' },
      sediment_yield: { column: '"Sediment Yield"', formula: 'loss.{col} / hill.area * 10', label: 't/ha' },
    };

    function statExpression(measure) {
      const expr = measure.formula.replace('{col}', measure.column);
      if (stat === 'p90') return `quantile(${expr}, 0.9)`;
      if (stat === 'sd') return `stddev_samp(${expr})`;
      if (stat === 'cv') {
        return `CASE WHEN avg(${expr}) = 0 THEN NULL ELSE stddev_samp(${expr}) / avg(${expr}) * 100 END`;
      }
      return `avg(${expr})`;
    }

    return Object.entries(measureMap).map(([alias, measure]) => ({
      sql: statExpression(measure),
      alias,
    }));
  }

  async function fetchWeppSummary(statistic, { base = false } = {}) {
    const aggregations = buildWeppAggregations(statistic);
    const columns = ['hill.topaz_id AS topaz_id', 'hill.wepp_id AS wepp_id', 'hill.area AS area'];
    const joins = [{ left: 'loss', right: 'hill', on: 'wepp_id', type: 'inner' }];
    const datasetPaths = [WEPP_YEARLY_PATH];

    async function runWithDataset(path) {
      const payload = {
        datasets: [
          { path, alias: 'loss' },
          { path: 'watershed/hillslopes.parquet', alias: 'hill' },
        ],
        joins,
        columns,
        group_by: ['hill.topaz_id', 'hill.wepp_id', 'hill.area'],
        aggregations,
      };
      const result = base ? await postBaseQueryEngine(payload) : await postQueryEngine(payload);
      if (result && result.records) {
        const summary = {};
        for (const row of result.records) {
          const topazId = row.topaz_id;
          if (topazId != null) {
            summary[String(topazId)] = row;
          }
        }
        return summary;
      }
      return null;
    }

    for (const path of datasetPaths) {
      const summary = await runWithDataset(path);
      if (summary !== null) {
        return summary;
      }
    }
    return null;
  }

  function computeWeppRanges(summaryOverride) {
    const summary = summaryOverride || getState().weppSummary;
    if (!summary) return null;
    const ranges = {};
    for (const mode of WEPP_MODES) {
      let min = Infinity;
      let max = -Infinity;
      for (const key of Object.keys(summary)) {
        const row = summary[key];
        const v = Number(row[mode]);
        if (Number.isFinite(v)) {
          if (v < min) min = v;
          if (v > max) max = v;
        }
      }
      if (!Number.isFinite(min)) min = 0;
      if (!Number.isFinite(max)) max = 1;
      if (max <= min) max = min + 1;
      ranges[mode] = { min, max };
    }
    setValue('weppRanges', ranges);
    return ranges;
  }

  async function refreshWeppStatisticData() {
    const state = getState();
    const hasActiveWepp = (state.weppLayers || []).some((l) => l.visible);
    if (!hasActiveWepp) return false;

    try {
      const weppSummary = await fetchWeppSummary(state.weppStatistic);
      setValue('weppSummary', weppSummary || null);
      if (weppSummary) {
        computeWeppRanges(weppSummary);
      }

      if (state.comparisonMode && state.currentScenarioPath) {
        const baseSummary = await fetchWeppSummary(state.weppStatistic, { base: true });
        const nextBaseSummary = { ...(state.baseSummaryCache || {}) };
        if (baseSummary) {
          nextBaseSummary.wepp = baseSummary;
        }
        setState({ baseSummaryCache: nextBaseSummary });
      }
      return true;
    } catch (err) {
      console.warn('gl-dashboard: failed to refresh WEPP data for statistic', err);
      return false;
    }
  }

  function computeWeppYearlyRanges(summaryOverride) {
    const summary = summaryOverride || getState().weppYearlySummary;
    if (!summary) return null;
    const ranges = {};
    for (const mode of WEPP_MODES) {
      let min = Infinity;
      let max = -Infinity;
      for (const key of Object.keys(summary)) {
        const row = summary[key];
        const v = Number(row[mode]);
        if (Number.isFinite(v)) {
          if (v < min) min = v;
          if (v > max) max = v;
        }
      }
      if (!Number.isFinite(min)) min = 0;
      if (!Number.isFinite(max)) max = 1;
      if (max <= min) max = min + 1;
      ranges[mode] = { min, max };
    }
    setState({ weppYearlyRanges: ranges });
    return ranges;
  }

  function computeWeppYearlyDiffRanges(year) {
    const state = getState();
    const weppYearlySummary = state.weppYearlySummary;
    const baseSummary = (state.baseWeppYearlyCache || {})[year];
    const diffRanges = {};
    if (!weppYearlySummary || !baseSummary) {
      setState({ weppYearlyDiffRanges: {} });
      return {};
    }

    function computeRobustRange(diffs) {
      if (!diffs.length) return null;
      diffs.sort((a, b) => a - b);
      const p5Idx = Math.floor(diffs.length * 0.05);
      const p95Idx = Math.floor(diffs.length * 0.95);
      const p5 = diffs[p5Idx];
      const p95 = diffs[p95Idx];
      const maxAbs = Math.max(Math.abs(p5), Math.abs(p95));
      return { min: -maxAbs, max: maxAbs, p5, p95 };
    }

    for (const mode of WEPP_MODES) {
      const diffs = [];
      for (const topazId of Object.keys(weppYearlySummary)) {
        const scenarioRow = weppYearlySummary[topazId];
        const baseRow = baseSummary[topazId];
        if (!scenarioRow || !baseRow) continue;
        const scenarioValue = Number(scenarioRow[mode]);
        const baseValue = Number(baseRow[mode]);
        if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) continue;
        diffs.push(baseValue - scenarioValue);
      }
      const range = computeRobustRange(diffs);
      if (range) {
        diffRanges[mode] = range;
      }
    }
    setState({ weppYearlyDiffRanges: diffRanges });
    return diffRanges;
  }

  async function loadBaseWeppYearlyData(year) {
    if (!Number.isFinite(year)) return null;
    const state = getState();
    if (state.baseWeppYearlyCache && state.baseWeppYearlyCache[year]) {
      return state.baseWeppYearlyCache[year];
    }
    const columns = [
      'hill.topaz_id AS topaz_id',
      'loss."Runoff Volume" AS runoff_volume',
      'loss."Subrunoff Volume" AS subrunoff_volume',
      'loss."Baseflow Volume" AS baseflow_volume',
      'loss."Soil Loss" AS soil_loss',
      'loss."Sediment Deposition" AS sediment_deposition',
      'loss."Sediment Yield" AS sediment_yield',
    ];
    const payload = {
      datasets: [
        { path: WEPP_YEARLY_PATH, alias: 'loss' },
        { path: 'watershed/hillslopes.parquet', alias: 'hill' },
      ],
      joins: [{ left: 'loss', right: 'hill', on: 'wepp_id', type: 'inner' }],
      columns,
      filters: [{ column: 'loss.year', op: '=', value: year }],
    };
    try {
      const result = await postBaseQueryEngine(payload);
      if (result && result.records) {
        const summary = {};
        for (const row of result.records) {
          const topazId = row.topaz_id;
          if (topazId != null) {
            summary[String(topazId)] = row;
          }
        }
        const nextBase = { ...(state.baseWeppYearlyCache || {}) };
        nextBase[year] = summary;
        setState({ baseWeppYearlyCache: nextBase });
        return summary;
      }
    } catch (err) {
      console.warn('gl-dashboard: failed to load base WEPP yearly data', err);
    }
    return null;
  }

  async function refreshWeppYearlyData() {
    const state = getState();
    const year = state.weppYearlySelectedYear;
    if (!Number.isFinite(year)) return false;

    let summary = (state.weppYearlyCache && state.weppYearlyCache[year]) || null;
    let nextCache = state.weppYearlyCache || {};
    if (!summary) {
      const columns = [
        'hill.topaz_id AS topaz_id',
        'loss."Runoff Volume" AS runoff_volume',
        'loss."Subrunoff Volume" AS subrunoff_volume',
        'loss."Baseflow Volume" AS baseflow_volume',
        'loss."Soil Loss" AS soil_loss',
        'loss."Sediment Deposition" AS sediment_deposition',
        'loss."Sediment Yield" AS sediment_yield',
      ];
      const payload = {
        datasets: [
          { path: WEPP_YEARLY_PATH, alias: 'loss' },
          { path: 'watershed/hillslopes.parquet', alias: 'hill' },
        ],
        joins: [{ left: 'loss', right: 'hill', on: 'wepp_id', type: 'inner' }],
        columns,
        filters: [{ column: 'loss.year', op: '=', value: year }],
      };
      try {
        const result = await postQueryEngine(payload);
        if (result && result.records) {
          summary = {};
          for (const row of result.records) {
            const topazId = row.topaz_id;
            if (topazId != null) {
              summary[String(topazId)] = row;
            }
          }
          nextCache = { ...nextCache, [year]: summary };
        }
      } catch (err) {
        console.warn('gl-dashboard: failed to refresh WEPP yearly data', err);
        summary = null;
      }
    }

    const ranges = summary ? computeWeppYearlyRanges(summary) || {} : {};
    let diffRanges = {};
    if (state.comparisonMode && state.currentScenarioPath) {
      await loadBaseWeppYearlyData(year);
      diffRanges = computeWeppYearlyDiffRanges(year) || {};
    } else {
      setState({ weppYearlyDiffRanges: {} });
    }

    setState({
      weppYearlySummary: summary || null,
      weppYearlyRanges: ranges || {},
      weppYearlyDiffRanges: diffRanges || {},
      weppYearlyCache: { ...nextCache },
      baseWeppYearlyCache: { ...(getState().baseWeppYearlyCache || {}) },
      weppYearlySelectedYear: year,
    });
    return true;
  }

  function computeWeppEventRanges(summaryOverride) {
    const summary = summaryOverride || getState().weppEventSummary;
    if (!summary) return null;
    const ranges = {};
    for (const mode of WEPP_EVENT_MODES) {
      let min = Infinity;
      let max = -Infinity;
      for (const key of Object.keys(summary)) {
        const row = summary[key];
        const v = Number(row[mode]);
        if (Number.isFinite(v)) {
          if (v < min) min = v;
          if (v > max) max = v;
        }
      }
      if (!Number.isFinite(min)) min = 0;
      if (!Number.isFinite(max)) max = 1;
      if (max <= min) max = min + 0.001;
      ranges[mode] = { min, max };
    }
    setState({ weppEventRanges: ranges });
    return ranges;
  }

  function computeWeppEventDiffRanges() {
    const state = getState();
    if (!state.weppEventSummary || !state.baseSummaryCache || !state.baseSummaryCache.weppEvent) return null;

    function computeRobustRange(diffs) {
      if (!diffs.length) return null;
      diffs.sort((a, b) => a - b);
      const p5Idx = Math.floor(diffs.length * 0.05);
      const p95Idx = Math.floor(diffs.length * 0.95);
      const p5 = diffs[p5Idx];
      const p95 = diffs[p95Idx];
      const maxAbs = Math.max(Math.abs(p5), Math.abs(p95));
      return { min: -maxAbs, max: maxAbs, p5, p95 };
    }

    const nextDiffRanges = { ...(state.comparisonDiffRanges || {}) };
    for (const mode of WEPP_EVENT_MODES) {
      const diffs = [];
      for (const topazId of Object.keys(state.weppEventSummary)) {
        const scenarioRow = state.weppEventSummary[topazId];
        const baseRow = state.baseSummaryCache.weppEvent[topazId];
        if (!scenarioRow || !baseRow) continue;
        const scenarioValue = Number(scenarioRow[mode]);
        const baseValue = Number(baseRow[mode]);
        if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) continue;
        diffs.push(baseValue - scenarioValue);
      }
      const range = computeRobustRange(diffs);
      if (range) {
        nextDiffRanges[mode] = range;
      }
    }
    setState({ comparisonDiffRanges: nextDiffRanges });
    return nextDiffRanges;
  }

  async function loadBaseWeppEventData() {
    const state = getState();
    if (!state.weppEventSelectedDate || !state.comparisonMode) return null;

    const [year, month, day] = state.weppEventSelectedDate.split('-').map(Number);
    if (!year || !month || !day) return null;

    const activeLayer = pickActiveWeppEventLayer();
    if (!activeLayer) return null;

    try {
      const mode = activeLayer.mode;
      const columns = ['hill.topaz_id AS topaz_id'];
      let filters;
      let baseQueryResult = {};

      // Query Engine runs as a separate service at /query-engine/ (no sitePrefix)
      const baseQueryPath = ctx.config ? `runs/${ctx.runid}/${ctx.config}` : `runs/${ctx.runid}`;
      const baseQueryUrl = `/query-engine/${baseQueryPath}/query`;

      if (mode === 'event_P' || mode === 'event_Q' || mode === 'event_ET') {
        const parquetPath = 'wepp/output/interchange/H.wat.parquet';
        const watColumn = mode === 'event_P' ? 'P' : mode === 'event_Q' ? 'Q' : null;
        const valueExpression =
          mode === 'event_ET'
            ? '(SUM(wat.Ep) + SUM(wat.Es) + SUM(wat.Er))'
            : `SUM(wat.${watColumn})`;
        filters = [
          { column: 'wat.year', op: '=', value: year },
          { column: 'wat.month', op: '=', value: month },
          { column: 'wat.day_of_month', op: '=', value: day },
        ];
        const dataPayload = {
          datasets: [
            { path: parquetPath, alias: 'wat' },
            { path: 'watershed/hillslopes.parquet', alias: 'hill' },
          ],
          joins: [{ left: 'wat', right: 'hill', on: 'wepp_id', type: 'inner' }],
          columns,
          aggregations: [{ sql: valueExpression, alias: 'value' }],
          filters,
          group_by: ['hill.topaz_id'],
        };
        const resp = await fetch(baseQueryUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify(dataPayload),
        });
        if (resp.ok) {
          const dataResult = await resp.json();
          if (dataResult && dataResult.records) {
            for (const row of dataResult.records) {
              baseQueryResult[String(row.topaz_id)] = { [mode]: row.value };
            }
          }
        }
      } else if (mode === 'event_peakro' || mode === 'event_tdet') {
        const parquetPath = 'wepp/output/interchange/H.pass.parquet';
        const passColumn = mode === 'event_peakro' ? 'peakro' : 'tdet';
        const valueExpression =
          mode === 'event_peakro' ? `MAX(pass.${passColumn})` : `SUM(pass.${passColumn})`;
        filters = [
          { column: 'pass.year', op: '=', value: year },
          { column: 'pass.month', op: '=', value: month },
          { column: 'pass.day_of_month', op: '=', value: day },
        ];
        const dataPayload = {
          datasets: [
            { path: parquetPath, alias: 'pass' },
            { path: 'watershed/hillslopes.parquet', alias: 'hill' },
          ],
          joins: [{ left: 'pass', right: 'hill', on: 'wepp_id', type: 'inner' }],
          columns,
          aggregations: [{ sql: valueExpression, alias: 'value' }],
          filters,
          group_by: ['hill.topaz_id'],
        };
        const resp = await fetch(baseQueryUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify(dataPayload),
        });
        if (resp.ok) {
          const dataResult = await resp.json();
          if (dataResult && dataResult.records) {
            for (const row of dataResult.records) {
              baseQueryResult[String(row.topaz_id)] = { [mode]: row.value };
            }
          }
        }
      }

      const nextBaseSummary = { ...(state.baseSummaryCache || {}) };
      nextBaseSummary.weppEvent = baseQueryResult;
      setState({ baseSummaryCache: nextBaseSummary });

      computeWeppEventDiffRanges();
      return baseQueryResult;
    } catch (err) {
      console.warn('gl-dashboard: failed to load base WEPP Event data for comparison', err);
      return null;
    }
  }

  async function refreshWeppEventData() {
    const state = getState();
    if (!state.weppEventSelectedDate) return false;
    const activeLayer = pickActiveWeppEventLayer();
    if (!activeLayer) return false;

    const [year, month, day] = state.weppEventSelectedDate.split('-').map(Number);
    if (!year || !month || !day) return false;

    try {
      const mode = activeLayer.mode;
      const columns = ['hill.topaz_id AS topaz_id'];
      let dataResult = null;

      if (mode === 'event_P' || mode === 'event_Q' || mode === 'event_ET') {
        const parquetPath = 'wepp/output/interchange/H.wat.parquet';
        const watColumn = mode === 'event_P' ? 'P' : mode === 'event_Q' ? 'Q' : null;
        const valueExpression =
          mode === 'event_ET'
            ? '(SUM(wat.Ep) + SUM(wat.Es) + SUM(wat.Er))'
            : `SUM(wat.${watColumn})`;
        const filters = [
          { column: 'wat.year', op: '=', value: year },
          { column: 'wat.month', op: '=', value: month },
          { column: 'wat.day_of_month', op: '=', value: day },
        ];
        const dataPayload = {
          datasets: [
            { path: parquetPath, alias: 'wat' },
            { path: 'watershed/hillslopes.parquet', alias: 'hill' },
          ],
          joins: [{ left: 'wat', right: 'hill', on: 'wepp_id', type: 'inner' }],
          columns,
          aggregations: [{ sql: valueExpression, alias: 'value' }],
          filters,
          group_by: ['hill.topaz_id'],
        };
        dataResult = await postQueryEngine(dataPayload);
      } else if (mode === 'event_peakro' || mode === 'event_tdet') {
        const parquetPath = 'wepp/output/interchange/H.pass.parquet';
        const passColumn = mode === 'event_peakro' ? 'peakro' : 'tdet';
        const valueExpression =
          mode === 'event_peakro' ? `MAX(pass.${passColumn})` : `SUM(pass.${passColumn})`;
        const filters = [
          { column: 'pass.year', op: '=', value: year },
          { column: 'pass.month', op: '=', value: month },
          { column: 'pass.day_of_month', op: '=', value: day },
        ];
        const dataPayload = {
          datasets: [
            { path: parquetPath, alias: 'pass' },
            { path: 'watershed/hillslopes.parquet', alias: 'hill' },
          ],
          joins: [{ left: 'pass', right: 'hill', on: 'wepp_id', type: 'inner' }],
          columns,
          aggregations: [{ sql: valueExpression, alias: 'value' }],
          filters,
          group_by: ['hill.topaz_id'],
        };
        dataResult = await postQueryEngine(dataPayload);
      }

      const weppEventSummary = {};
      if (dataResult && dataResult.records) {
        for (const row of dataResult.records) {
          weppEventSummary[String(row.topaz_id)] = { [mode]: row.value };
        }
      }

      setValue('weppEventSummary', weppEventSummary);
      const ranges = computeWeppEventRanges(weppEventSummary) || {};
      setState({ weppEventRanges: ranges });

      if (state.comparisonMode && state.currentScenarioPath) {
        await loadBaseWeppEventData();
      }
      return true;
    } catch (err) {
      console.warn('gl-dashboard: failed to refresh WEPP Event data', err);
      setState({ weppEventSummary: {}, weppEventRanges: {} });
      return false;
    }
  }

  return {
    buildWeppAggregations,
    fetchWeppSummary,
    refreshWeppStatisticData,
    computeWeppRanges,
    computeWeppYearlyRanges,
    computeWeppYearlyDiffRanges,
    loadBaseWeppYearlyData,
    refreshWeppYearlyData,
    computeWeppEventRanges,
    computeWeppEventDiffRanges,
    loadBaseWeppEventData,
    refreshWeppEventData,
  };
}
