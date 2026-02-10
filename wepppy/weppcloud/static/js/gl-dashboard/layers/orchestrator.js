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
  fetchWeppChannelSummary,
  weppLossPath,
  weppChannelPath,
  weppYearlyPath,
  watarPath,
  postQueryEngine,
  postBaseQueryEngine,
  yearSlider,
  monthSlider,
  climateCtx,
  applyLayers,
  updateLayerList,
  nlcdColormap,
  soilColorForValue,
  loadRaster,
  loadRasterFromDownload,
  loadSbsImage,
  fetchGdalInfo,
  computeComparisonDiffRanges,
  baseLayerDefs,
  rapBandLabels,
  monthLabels,
  onBaseScenarioDetected,
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
      if (typeof onBaseScenarioDetected === 'function' && result.detectedLayers.some((l) => l && l.key === 'sbs')) {
        onBaseScenarioDetected('Burned');
      }
      updateLayerList();
      applyLayers();
    }
  }

  async function detectLanduseOverlays() {
    const result = await detectorModule.detectLanduseOverlays({
      ctx,
      buildScenarioUrl,
      buildBaseUrl,
      subcatchmentsGeoJson: getState().subcatchmentsGeoJson,
    });
    if (result) {
      const subcatchments = getState().subcatchmentsGeoJson || result.subcatchmentsGeoJson;
      const prevVisible = (getState().landuseLayers || []).find((l) => l && l.visible);
      const nextLanduseLayers = Array.isArray(result.landuseLayers) ? [...result.landuseLayers] : [];
      if (prevVisible && nextLanduseLayers.some((l) => l && l.key === prevVisible.key)) {
        for (const layer of nextLanduseLayers) {
          layer.visible = layer.key === prevVisible.key;
        }
      }
      setState({
        landuseSummary: result.landuseSummary,
        subcatchmentsGeoJson: subcatchments,
        landuseLayers: nextLanduseLayers,
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
      ctx,
      buildScenarioUrl,
      buildBaseUrl,
      subcatchmentsGeoJson: getState().subcatchmentsGeoJson,
    });
    if (result) {
      const subcatchments = getState().subcatchmentsGeoJson || result.subcatchmentsGeoJson;
      setState({
        soilsSummary: result.soilsSummary,
        subcatchmentsGeoJson: subcatchments,
        soilsLayers: result.soilsLayers,
      });
      updateLayerList();
      applyLayers();
    }
  }

  async function detectHillslopesOverlays() {
    const result = await detectorModule.detectHillslopesOverlays({
      ctx,
      buildScenarioUrl,
      buildBaseUrl,
      subcatchmentsGeoJson: getState().subcatchmentsGeoJson,
    });
    if (result) {
      const subcatchments = getState().subcatchmentsGeoJson || result.subcatchmentsGeoJson;
      setState({
        hillslopesSummary: result.hillslopesSummary,
        subcatchmentsGeoJson: subcatchments,
        hillslopesLayers: result.hillslopesLayers,
      });
      updateLayerList();
      applyLayers();
    }
  }

  async function detectD8DirectionLayer() {
    if (typeof detectorModule.detectD8DirectionLayer !== 'function') return;
    const result = await detectorModule.detectD8DirectionLayer({
      fetchGdalInfo,
      loadRasterFromDownload,
    });
    if (result && result.d8DirectionLayer) {
      setValue('d8DirectionLayer', result.d8DirectionLayer);
      updateLayerList();
      applyLayers();
    }
  }

  async function detectChannelsOverlays() {
    const result = await detectorModule.detectChannelsOverlays({ ctx, buildBaseUrl });
    if (result) {
      const existing = getState().channelsLayers || [];
      const hasWeppChannelSelection = (getState().weppChannelLayers || []).some((l) => l && l.visible);
      const hasWeppYearlyChannelSelection = (getState().weppYearlyChannelLayers || []).some((l) => l && l.visible);
      const nextLayers = [
        {
          key: 'channel-order',
          label: 'Channel Order',
          path: 'resources/channels.json',
          mode: 'channel_order',
          visible: false,
        },
      ];
      const prevVisible = existing.find((l) => l && l.visible);
      if (prevVisible && nextLayers.some((l) => l && l.key === prevVisible.key)) {
        for (const layer of nextLayers) {
          layer.visible = layer.key === prevVisible.key;
        }
      } else if (getState().channelsVisible && !(hasWeppChannelSelection || hasWeppYearlyChannelSelection)) {
        nextLayers[0].visible = true;
      }
      setState({
        channelsGeoJson: result.channelsGeoJson,
        channelLabelsData: result.channelLabelsData || [],
        channelsLayers: nextLayers,
      });
      updateLayerList();
      applyLayers();
    }
  }

  async function detectOpenetOverlays() {
    const result = await detectorModule.detectOpenetOverlays({
      buildBaseUrl,
      postBaseQueryEngine,
      monthLabels,
      subcatchmentsGeoJson: getState().subcatchmentsGeoJson,
      currentSelectedMonthIndex: getState().openetSelectedMonthIndex,
      currentSelectedDatasetKey: getState().openetSelectedDatasetKey,
    });
    if (result) {
      const subcatchments = getState().subcatchmentsGeoJson || result.subcatchmentsGeoJson;
      setState({
        openetLayers: result.openetLayers || [],
        openetMetadata: result.openetMetadata || null,
        openetSummary: result.openetSummary || null,
        openetRanges: result.openetRanges || {},
        openetSelectedDatasetKey: result.openetSelectedDatasetKey || null,
        openetSelectedMonthIndex: Number.isFinite(result.openetSelectedMonthIndex)
          ? result.openetSelectedMonthIndex
          : getState().openetSelectedMonthIndex,
        subcatchmentsGeoJson: subcatchments,
      });
      if (monthSlider && result.openetMetadata && Array.isArray(result.openetMetadata.months)) {
        const selectedIndex = Number.isFinite(result.openetSelectedMonthIndex)
          ? result.openetSelectedMonthIndex
          : result.openetMetadata.months.length - 1;
        monthSlider.setRange(result.openetMetadata.months, selectedIndex);
      }
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
      const subcatchments = getState().subcatchmentsGeoJson || result.subcatchmentsGeoJson;
      setState({
        watarSummary: result.watarSummary,
        watarRanges: result.watarRanges || {},
        subcatchmentsGeoJson: subcatchments,
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
      const subcatchments = getState().subcatchmentsGeoJson || result.subcatchmentsGeoJson;
      setState({
        weppSummary: result.weppSummary,
        weppRanges: result.weppRanges || {},
        subcatchmentsGeoJson: subcatchments,
        weppLayers: result.weppLayers,
      });
      if (getState().comparisonMode) {
        computeComparisonDiffRanges();
      }
      updateLayerList();
      applyLayers();
    }
  }

  async function detectWeppChannelOverlays() {
    const result = await detectorModule.detectWeppChannelOverlays({
      buildBaseUrl,
      fetchWeppChannelSummary,
      weppStatistic: getState().weppStatistic,
      weppChannelPath: weppChannelPath || 'wepp/output/interchange/loss_pw0.all_years.chn.parquet',
      channelsGeoJson: getState().channelsGeoJson,
    });
    if (result) {
      const prevVisible = (getState().weppChannelLayers || []).find((l) => l && l.visible);
      const nextLayers = Array.isArray(result.weppChannelLayers) ? [...result.weppChannelLayers] : [];
      if (prevVisible && nextLayers.some((l) => l && l.key === prevVisible.key)) {
        for (const layer of nextLayers) {
          layer.visible = layer.key === prevVisible.key;
        }
      }
      setState({
        weppChannelSummary: result.weppChannelSummary,
        weppChannelRanges: result.weppChannelRanges || {},
        weppChannelLayers: nextLayers,
        channelsGeoJson: result.channelsGeoJson || getState().channelsGeoJson,
      });
      updateLayerList();
      applyLayers();
    }
  }

  async function detectWeppYearlyChannelOverlays() {
    const result = await detectorModule.detectWeppYearlyChannelOverlays({
      buildBaseUrl,
      postQueryEngine,
      weppChannelPath: weppChannelPath || 'wepp/output/interchange/loss_pw0.all_years.chn.parquet',
      channelsGeoJson: getState().channelsGeoJson,
    });
    if (result) {
      const prevVisible = (getState().weppYearlyChannelLayers || []).find((l) => l && l.visible);
      const nextLayers = Array.isArray(result.weppYearlyChannelLayers) ? [...result.weppYearlyChannelLayers] : [];
      if (prevVisible && nextLayers.some((l) => l && l.key === prevVisible.key)) {
        for (const layer of nextLayers) {
          layer.visible = layer.key === prevVisible.key;
        }
      }
      setState({
        weppYearlyChannelLayers: nextLayers,
        channelsGeoJson: result.channelsGeoJson || getState().channelsGeoJson,
      });
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
      const subcatchments = getState().subcatchmentsGeoJson || result.subcatchmentsGeoJson;
      setState({
        weppYearlyLayers: result.weppYearlyLayers,
        weppYearlyMetadata: result.weppYearlyMetadata,
        weppYearlySelectedYear: result.weppYearlySelectedYear,
        subcatchmentsGeoJson: subcatchments,
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
      const subcatchments = getState().subcatchmentsGeoJson || result.subcatchmentsGeoJson;
      setState({
        rapLayers: result.rapLayers || [],
        rapMetadata: result.rapMetadata || null,
        rapSelectedYear: result.rapSelectedYear || null,
        rapSummary: result.rapSummary || null,
        subcatchmentsGeoJson: subcatchments,
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
    const isBatch =
      ctx && ctx.mode === 'batch' && ctx.batch && Array.isArray(ctx.batch.runs);

    const tasks = [detectRasterLayers(), detectHillslopesOverlays(), detectD8DirectionLayer(), detectChannelsOverlays()];

    // Batch mode only supports merged geometry + basic summaries in early phases.
    // Skip run-scoped time-series overlays until a batch fan-out provider exists.
    if (!isBatch) {
      tasks.push(
        detectWeppYearlyChannelOverlays(),
        detectOpenetOverlays(),
        detectWatarOverlays(),
        detectWeppEventOverlays(),
        detectRapOverlays(),
      );
    }
    await Promise.all(tasks);
  }

  return {
    detectRasterLayers,
    detectLanduseOverlays,
    detectSoilsOverlays,
    detectHillslopesOverlays,
    detectD8DirectionLayer,
    detectChannelsOverlays,
    detectOpenetOverlays,
    detectWatarOverlays,
    detectWeppOverlays,
    detectWeppChannelOverlays,
    detectWeppYearlyChannelOverlays,
    detectWeppYearlyOverlays,
    detectWeppEventOverlays,
    detectRapOverlays,
    detectLayers,
  };
}
