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

  function buildScenarioUrl(relativePath) {
    const baseUrl = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/${relativePath}`;
    const { currentScenarioPath } = getState();
    if (currentScenarioPath) {
      const pupPath = currentScenarioPath.replace(/^_pups\//, '');
      return `${baseUrl}?pup=${encodeURIComponent(pupPath)}`;
    }
    return baseUrl;
  }

  function buildBaseUrl(relativePath) {
    return `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/${relativePath}`;
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
    setState({
      landuseSummary: null,
      soilsSummary: null,
      weppSummary: null,
      weppYearlySummary: null,
      weppYearlyMetadata: null,
      weppYearlyRanges: {},
      weppYearlyDiffRanges: {},
      weppYearlyCache: {},
      baseWeppYearlyCache: {},
      weppYearlySelectedYear: null,
      weppEventSummary: null,
      weppYearlyLayers: [],
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
