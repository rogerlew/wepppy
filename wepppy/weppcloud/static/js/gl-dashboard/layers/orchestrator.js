/**
 * Detection orchestration for gl-dashboard overlays.
 * Wraps detector module functions and updates shared state/UI callbacks.
 */

export function createDetectionController({
  ctx,
  detectorModule,
  getState,
  setState,
  setValue,
  buildScenarioUrl,
  buildBaseUrl,
  fetchWeppSummary,
  weppLossPath,
  weppYearlyPath,
  watarPath,
  postQueryEngine,
  yearSlider,
  climateCtx,
  applyLayers,
  updateLayerList,
  nlcdColormap,
  soilColorForValue,
  loadRaster,
  loadSbsImage,
  fetchGdalInfo,
  computeComparisonDiffRanges,
  baseLayerDefs,
  rapBandLabels,
}) {
  async function detectRasterLayers() {
    const result = await detectorModule.detectRasterLayers({
      ctx,
      layerDefs: baseLayerDefs || [],
      loadRaster,
      loadSbsImage,
      fetchGdalInfo,
      nlcdColormap,
      soilColorForValue,
    });
    if (result && result.detectedLayers) {
      setValue('detectedLayers', result.detectedLayers);
      updateLayerList();
      applyLayers();
    }
  }

  async function detectLanduseOverlays() {
    const result = await detectorModule.detectLanduseOverlays({ buildScenarioUrl, buildBaseUrl });
    if (result) {
      setState({
        landuseSummary: result.landuseSummary,
        subcatchmentsGeoJson: result.subcatchmentsGeoJson || getState().subcatchmentsGeoJson,
        landuseLayers: result.landuseLayers,
      });
      if (getState().comparisonMode) {
        computeComparisonDiffRanges();
      }
      updateLayerList();
      applyLayers();
    }
  }

  async function detectSoilsOverlays() {
    const result = await detectorModule.detectSoilsOverlays({
      buildScenarioUrl,
      buildBaseUrl,
      subcatchmentsGeoJson: getState().subcatchmentsGeoJson,
    });
    if (result) {
      setState({
        soilsSummary: result.soilsSummary,
        subcatchmentsGeoJson: result.subcatchmentsGeoJson || getState().subcatchmentsGeoJson,
        soilsLayers: result.soilsLayers,
      });
      updateLayerList();
      applyLayers();
    }
  }

  async function detectHillslopesOverlays() {
    const result = await detectorModule.detectHillslopesOverlays({
      buildScenarioUrl,
      buildBaseUrl,
      subcatchmentsGeoJson: getState().subcatchmentsGeoJson,
    });
    if (result) {
      setState({
        hillslopesSummary: result.hillslopesSummary,
        subcatchmentsGeoJson: result.subcatchmentsGeoJson || getState().subcatchmentsGeoJson,
        hillslopesLayers: result.hillslopesLayers,
      });
      updateLayerList();
      applyLayers();
    }
  }

  async function detectWatarOverlays() {
    const result = await detectorModule.detectWatarOverlays({
      buildBaseUrl,
      postQueryEngine,
      watarPath,
      subcatchmentsGeoJson: getState().subcatchmentsGeoJson,
    });
    if (result) {
      setState({
        watarSummary: result.watarSummary,
        watarRanges: result.watarRanges || {},
        subcatchmentsGeoJson: result.subcatchmentsGeoJson || getState().subcatchmentsGeoJson,
        watarLayers: result.watarLayers,
      });
      updateLayerList();
      applyLayers();
    }
  }

  async function detectWeppOverlays() {
    const result = await detectorModule.detectWeppOverlays({
      buildBaseUrl,
      fetchWeppSummary,
      weppStatistic: getState().weppStatistic,
      weppLossPath,
      subcatchmentsGeoJson: getState().subcatchmentsGeoJson,
    });
    if (result) {
      setState({
        weppSummary: result.weppSummary,
        weppRanges: result.weppRanges || {},
        subcatchmentsGeoJson: result.subcatchmentsGeoJson || getState().subcatchmentsGeoJson,
        weppLayers: result.weppLayers,
      });
      if (getState().comparisonMode) {
        computeComparisonDiffRanges();
      }
      updateLayerList();
      applyLayers();
    }
  }

  async function detectWeppYearlyOverlays() {
    const result = await detectorModule.detectWeppYearlyOverlays({
      buildBaseUrl,
      postQueryEngine,
      weppYearlyPath: weppYearlyPath || 'wepp/output/interchange/loss_pw0.all_years.hill.parquet',
      currentSelectedYear: getState().weppYearlySelectedYear,
      subcatchmentsGeoJson: getState().subcatchmentsGeoJson,
    });
    if (result) {
      setState({
        weppYearlyLayers: result.weppYearlyLayers,
        weppYearlyMetadata: result.weppYearlyMetadata,
        weppYearlySelectedYear: result.weppYearlySelectedYear,
        subcatchmentsGeoJson: result.subcatchmentsGeoJson || getState().subcatchmentsGeoJson,
      });
      if (result.weppYearlyMetadata && result.weppYearlyMetadata.years && result.weppYearlyMetadata.years.length) {
        yearSlider.setRange(result.weppYearlyMetadata.minYear, result.weppYearlyMetadata.maxYear, result.weppYearlySelectedYear);
      }
      updateLayerList();
      applyLayers();
    }
  }

  async function detectWeppEventOverlays() {
    const result = await detectorModule.detectWeppEventOverlays({
      buildBaseUrl,
      climateCtx,
      currentSelectedDate: getState().weppEventSelectedDate,
      subcatchmentsGeoJson: getState().subcatchmentsGeoJson,
    });
    if (result) {
      setState({
        weppEventLayers: result.weppEventLayers,
        weppEventMetadata: result.weppEventMetadata,
        weppEventSelectedDate: result.weppEventSelectedDate,
        subcatchmentsGeoJson: result.subcatchmentsGeoJson || getState().subcatchmentsGeoJson,
      });
      updateLayerList();
      applyLayers();
    }
  }

  async function detectRapOverlays() {
    const result = await detectorModule.detectRapOverlays({
      buildBaseUrl,
      postQueryEngine,
      rapBandLabels: rapBandLabels || {},
      subcatchmentsGeoJson: getState().subcatchmentsGeoJson,
      currentSelectedYear: getState().rapSelectedYear,
    });
    if (result) {
      setState({
        rapLayers: result.rapLayers || [],
        rapMetadata: result.rapMetadata || null,
        rapSelectedYear: result.rapSelectedYear || null,
        rapSummary: result.rapSummary || null,
        subcatchmentsGeoJson: result.subcatchmentsGeoJson || getState().subcatchmentsGeoJson,
      });
      if (result.rapMetadata && result.rapMetadata.years && result.rapMetadata.years.length) {
        const minYear = result.rapMetadata.years[0];
        const maxYear = result.rapMetadata.years[result.rapMetadata.years.length - 1];
        yearSlider.setRange(minYear, maxYear, result.rapSelectedYear || maxYear);
      }
      updateLayerList();
      applyLayers();
    }
  }

  async function detectLayers() {
    const tasks = [
      detectRasterLayers(),
      detectHillslopesOverlays(),
      detectWatarOverlays(),
      detectWeppEventOverlays(),
      detectRapOverlays(),
    ];
    await Promise.all(tasks);
  }

  return {
    detectRasterLayers,
    detectLanduseOverlays,
    detectSoilsOverlays,
    detectHillslopesOverlays,
    detectWatarOverlays,
    detectWeppOverlays,
    detectWeppYearlyOverlays,
    detectWeppEventOverlays,
    detectRapOverlays,
    detectLayers,
  };
}
