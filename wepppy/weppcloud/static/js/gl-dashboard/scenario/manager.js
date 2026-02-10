/**
 * @typedef {Object} ScenarioContext
 * @property {string} sitePrefix
 * @property {string} runid
 * @property {string} config
 */

/**
 * @callback GetState
 * @returns {Record<string, any>}
 */

/**
 * @callback SetValue
 * @param {string} key
 * @param {any} value
 */

/**
 * @callback SetState
 * @param {Record<string, any>} partialState
 */

/**
 * @typedef {Object} WeppDataManager
 * @property {(year: number) => Promise<void>} [loadBaseWeppYearlyData]
 * @property {(year: number) => void} [computeWeppYearlyDiffRanges]
 */

/**
 * @typedef {(payload: { scenarioPath: string, phase: 'before_base' | 'after_base' }) => Promise<void> | void} ScenarioChangeHandler
 */

/**
 * @typedef {(payload: { enabled: boolean }) => Promise<void> | void} ComparisonChangeHandler
 */

/**
 * @typedef {Object} ScenarioManager
 * @property {(relativePath: string) => string} buildScenarioUrl
 * @property {(relativePath: string) => string} buildBaseUrl
 * @property {(scenarioPath: string) => Promise<void>} setScenario
 * @property {(enabled: boolean) => Promise<void>} setComparisonMode
 * @property {() => Promise<void>} loadBaseScenarioData
 * @property {(baseSummaryOverride?: Record<string, any>) => Record<string, any>} computeComparisonDiffRanges
 */

/**
 * Scenario and comparison controller for GL Dashboard; handles base scenario URLs,
 * base data hydration, and diff range computation.
 * @param {{ ctx: ScenarioContext, getState: GetState, setValue: SetValue, setState: SetState, postQueryEngine?: Function, postBaseQueryEngine?: Function, fetchWeppSummary: Function, weppDataManager?: WeppDataManager, onScenarioChange?: ScenarioChangeHandler, onComparisonChange?: ComparisonChangeHandler }} params
 * @returns {ScenarioManager}
 */
export function createScenarioManager({
  ctx,
  getState,
  setValue,
  setState,
  postQueryEngine,
  postBaseQueryEngine,
  fetchWeppSummary,
  weppDataManager,
  onScenarioChange,
  onComparisonChange,
}) {
  // Reserved for future use; keep references available for injected helpers.
  void postQueryEngine;
  void postBaseQueryEngine;

  function normalizeSitePrefix(prefix) {
    if (!prefix) return '';
    return String(prefix).replace(/\/+$/, '');
  }

  function normalizeRelativePath(value) {
    if (!value) return '';
    return String(value).replace(/^\/+/, '');
  }

  function resolveParentRunId(runid) {
    const raw = String(runid || '');
    const parts = raw.split(';;');
    if (
      parts.length >= 3 &&
      parts[parts.length - 2] &&
      (parts[parts.length - 2] === 'omni' || parts[parts.length - 2] === 'omni-contrast')
    ) {
      return parts.slice(0, -2).join(';;');
    }
    return raw;
  }

  function extractOmniScenarioName(scenarioPath) {
    if (!scenarioPath) return '';
    const normalized = String(scenarioPath).replace(/^_pups\//, '').replace(/^\/+/, '');
    const match = normalized.match(/^omni\/scenarios\/([^/]+)/);
    return match ? match[1] : '';
  }

  function extractOmniContrastId(scenarioPath) {
    if (!scenarioPath) return '';
    const normalized = String(scenarioPath).replace(/^_pups\//, '').replace(/^\/+/, '');
    const match = normalized.match(/^omni\/contrasts\/([^/]+)/);
    return match ? match[1] : '';
  }

  const sitePrefix = normalizeSitePrefix(ctx.sitePrefix);

  function buildRunUrl(runid, relativePath) {
    const runSlug = String(runid || '').trim();
    const configSlug = String(ctx.config || '').trim();
    const path = normalizeRelativePath(relativePath);
    const encodedRunId =
      runSlug.indexOf(';;') !== -1
        ? runSlug
            .split(';;')
            .map((segment) => encodeURIComponent(segment))
            .join(';;')
        : encodeURIComponent(runSlug);
    const runPath = `/runs/${encodedRunId}/${encodeURIComponent(configSlug)}/`;
    return (sitePrefix ? sitePrefix + runPath : runPath) + path;
  }

  function buildScenarioUrl(relativePath) {
    const { currentScenarioPath } = getState();
    if (!currentScenarioPath) {
      return buildRunUrl(ctx.runid, relativePath);
    }

    const contrastId = extractOmniContrastId(currentScenarioPath);
    if (contrastId) {
      const parentRunId = resolveParentRunId(ctx.runid);
      const compositeRunId = `${parentRunId};;omni-contrast;;${contrastId}`;
      return buildRunUrl(compositeRunId, relativePath);
    }

    const scenarioName = extractOmniScenarioName(currentScenarioPath);
    if (!scenarioName) {
      return buildRunUrl(ctx.runid, relativePath);
    }

    const parentRunId = resolveParentRunId(ctx.runid);
    const compositeRunId = `${parentRunId};;omni;;${scenarioName}`;
    return buildRunUrl(compositeRunId, relativePath);
  }

  function buildBaseUrl(relativePath) {
    return buildRunUrl(ctx.runid, relativePath);
  }

  function computeComparisonDiffRanges(baseSummaryOverride) {
    const state = getState();
    const landuseSummary = state.landuseSummary;
    const weppSummary = state.weppSummary;
    const baseSummary = baseSummaryOverride || state.baseSummaryCache || {};
    const ranges = {};

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

    if (landuseSummary && baseSummary.landuse) {
      const coverModes = ['cancov', 'inrcov', 'rilcov'];
      for (const mode of coverModes) {
        const diffs = [];
        for (const topazId of Object.keys(landuseSummary)) {
          const scenarioRow = landuseSummary[topazId];
          const baseRow = baseSummary.landuse[topazId];
          if (!scenarioRow || !baseRow) continue;
          const scenarioValue = Number(scenarioRow[mode]);
          const baseValue = Number(baseRow[mode]);
          if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) continue;
          diffs.push(baseValue - scenarioValue);
        }
        const range = computeRobustRange(diffs);
        if (range) {
          ranges[mode] = range;
        }
      }
    }

    if (weppSummary && baseSummary.wepp) {
      const weppModes = [
        'runoff_volume',
        'subrunoff_volume',
        'baseflow_volume',
        'soil_loss',
        'sediment_deposition',
        'sediment_yield',
      ];
      for (const mode of weppModes) {
        const diffs = [];
        for (const topazId of Object.keys(weppSummary)) {
          const scenarioRow = weppSummary[topazId];
          const baseRow = baseSummary.wepp[topazId];
          if (!scenarioRow || !baseRow) continue;
          const scenarioValue = Number(scenarioRow[mode]);
          const baseValue = Number(baseRow[mode]);
          if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) continue;
          diffs.push(baseValue - scenarioValue);
        }
        const range = computeRobustRange(diffs);
        if (range) {
          ranges[mode] = range;
        }
      }
    }

    setValue('comparisonDiffRanges', ranges);
    return ranges;
  }

  async function loadBaseScenarioData() {
    const baseSummary = {};
    setState({ baseSummaryCache: baseSummary, comparisonDiffRanges: {} });

    try {
      const landuseUrl = buildBaseUrl('query/landuse/subcatchments');
      const landuseResp = await fetch(landuseUrl);
      if (landuseResp && landuseResp.ok) {
        baseSummary.landuse = await landuseResp.json();
      }

      const { weppStatistic } = getState();
      baseSummary.wepp = await fetchWeppSummary(weppStatistic, { base: true });

      const ranges = computeComparisonDiffRanges(baseSummary);
      setState({
        baseSummaryCache: baseSummary,
        comparisonDiffRanges: ranges || {},
      });
    } catch (err) {
      console.warn('gl-dashboard: failed to load base scenario data for comparison', err);
      setState({ baseSummaryCache: baseSummary });
    }
  }

  async function setScenario(scenarioPath) {
    const nextScenario = scenarioPath || '';
    const currentState = getState();
    if (nextScenario === currentState.currentScenarioPath) return;

    setValue('currentScenarioPath', nextScenario);
    // Keep existing subcatchment geometry and overlays visible during scenario transitions.
    // New summaries/metadata will replace these once detection finishes, avoiding map flicker.
    setState({
      weppYearlyRanges: {},
      weppYearlyDiffRanges: {},
      weppYearlyCache: {},
      baseWeppYearlyCache: {},
      weppYearlyChannelSummary: null,
      weppYearlyChannelRanges: {},
      weppYearlyChannelCache: {},
    });

    if (typeof onScenarioChange === 'function') {
      await onScenarioChange({ scenarioPath: nextScenario, phase: 'before_base' });
    }

    const postDetectionState = getState();
    if (postDetectionState.currentScenarioPath !== nextScenario) {
      return;
    }

    if (postDetectionState.comparisonMode && nextScenario) {
      await loadBaseScenarioData();
      const { weppYearlySelectedYear } = getState();
      if (weppYearlySelectedYear != null && weppDataManager && typeof weppDataManager.loadBaseWeppYearlyData === 'function') {
        await weppDataManager.loadBaseWeppYearlyData(weppYearlySelectedYear);
        if (typeof weppDataManager.computeWeppYearlyDiffRanges === 'function') {
          weppDataManager.computeWeppYearlyDiffRanges(weppYearlySelectedYear);
        }
      }
    }

    const postBaseState = getState();
    if (postBaseState.currentScenarioPath !== nextScenario) {
      return;
    }

    if (typeof onScenarioChange === 'function') {
      await onScenarioChange({ scenarioPath: nextScenario, phase: 'after_base' });
    }
  }

  async function setComparisonMode(enabled) {
    const desired = !!enabled;
    setValue('comparisonMode', desired);

    if (!desired) {
      setState({ weppYearlyDiffRanges: {} });
      if (typeof onComparisonChange === 'function') {
        onComparisonChange({ enabled: desired });
      }
      return;
    }

    const state = getState();
    if (state.currentScenarioPath) {
      await loadBaseScenarioData();
      const { weppYearlySelectedYear } = getState();
      if (weppYearlySelectedYear != null && weppDataManager && typeof weppDataManager.loadBaseWeppYearlyData === 'function') {
        await weppDataManager.loadBaseWeppYearlyData(weppYearlySelectedYear);
        if (typeof weppDataManager.computeWeppYearlyDiffRanges === 'function') {
          weppDataManager.computeWeppYearlyDiffRanges(weppYearlySelectedYear);
        }
      }
    }

    if (typeof onComparisonChange === 'function') {
      await onComparisonChange({ enabled: desired });
    }
  }

  return {
    buildScenarioUrl,
    buildBaseUrl,
    setScenario,
    setComparisonMode,
    loadBaseScenarioData,
    computeComparisonDiffRanges,
  };
}
