// Detection helpers for gl-dashboard overlays. Pure data routines only; no DOM access.

async function detectSbsLayer({ ctx, loadSbsImage }) {
  const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/query/baer_wgs_map`;
  const resp = await fetch(url);
  if (!resp.ok) {
    return null;
  }
  const payload = await resp.json();
  if (!payload || payload.Success !== true || !payload.Content) {
    return null;
  }

  let { bounds } = payload.Content;
  const imgurl = payload.Content.imgurl;
  if (!bounds || !imgurl) {
    return null;
  }

  // Normalize bounds: API returns [[lat1, lon1], [lat2, lon2]]
  if (Array.isArray(bounds) && bounds.length === 2 && Array.isArray(bounds[0]) && Array.isArray(bounds[1])) {
    const [lat1, lon1] = bounds[0];
    const [lat2, lon2] = bounds[1];
    bounds = [lon1, lat1, lon2, lat2];
  }
  if (!Array.isArray(bounds) || bounds.length !== 4 || bounds.some((v) => !Number.isFinite(v))) {
    return null;
  }

  const raster = await loadSbsImage(imgurl);
  if (!raster) {
    return null;
  }

  return {
    key: 'sbs',
    label: 'SBS Map',
    path: 'query/baer_wgs_map',
    bounds,
    ...raster,
    visible: false,
  };
}

function computeBoundsFromGdal(info) {
  const wgs84 = info && info.wgs84Extent && info.wgs84Extent.coordinates;
  if (Array.isArray(wgs84) && wgs84.length && Array.isArray(wgs84[0])) {
    const ring = wgs84[0];
    let west = Infinity;
    let south = Infinity;
    let east = -Infinity;
    let north = -Infinity;
    for (const pt of ring) {
      if (!Array.isArray(pt) || pt.length < 2) continue;
      const [lon, lat] = pt;
      if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
      if (lon < west) west = lon;
      if (lon > east) east = lon;
      if (lat < south) south = lat;
      if (lat > north) north = lat;
    }
    if ([west, south, east, north].every((v) => Number.isFinite(v))) {
      return [west, south, east, north];
    }
  }
  const cc = info && info.cornerCoordinates;
  if (!cc) return null;
  const ll = cc.lowerLeft || cc.lowerleft || cc.LowerLeft;
  const ur = cc.upperRight || cc.upperright || cc.UpperRight;
  if (!ll || !ur) return null;
  const west = Math.min(ll[0], ur[0]);
  const east = Math.max(ll[0], ur[0]);
  const south = Math.min(ll[1], ur[1]);
  const north = Math.max(ll[1], ur[1]);
  if (![west, south, east, north].every(Number.isFinite)) return null;
  return [west, south, east, north];
}

async function ensureSubcatchments(buildBaseUrl, subcatchmentsGeoJson) {
  if (subcatchmentsGeoJson) {
    return subcatchmentsGeoJson;
  }
  const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
  const geoResp = await fetch(geoUrl);
  if (geoResp.ok) {
    return geoResp.json();
  }
  return subcatchmentsGeoJson;
}

function computeRanges(summary, modes) {
  if (!summary) return {};
  const ranges = {};
  for (const mode of modes) {
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
  return ranges;
}

export async function detectRasterLayers({
  ctx,
  layerDefs,
  loadRaster,
  loadSbsImage,
  fetchGdalInfo,
  nlcdColormap,
  soilColorForValue,
}) {
  const detectedLayers = [];

  try {
    if (loadSbsImage) {
      const sbsLayer = await detectSbsLayer({ ctx, loadSbsImage });
      if (sbsLayer) {
        detectedLayers.push(sbsLayer);
      }
    }
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('gl-dashboard: failed to load SBS map', err);
  }

  for (const def of layerDefs) {
    let found = null;
    for (const path of def.paths) {
      try {
        const info = await fetchGdalInfo(path);
        if (!info) continue;
        const bounds = computeBoundsFromGdal(info);
        if (!bounds) continue;
        const colorMap = def.key === 'landuse' ? nlcdColormap : def.key === 'soils' ? soilColorForValue : null;
        const raster = await loadRaster(path, colorMap);
        found = {
          key: def.key,
          label: def.label,
          path,
          bounds,
          ...raster,
          visible: false,
        };
        break;
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn(`gl-dashboard: failed to load ${def.label} at ${path}`, err);
      }
    }
    if (found) {
      detectedLayers.push(found);
    }
  }

  return { detectedLayers };
}

export async function detectLanduseOverlays({ buildScenarioUrl, buildBaseUrl }) {
  try {
    const url = buildScenarioUrl(`query/landuse/subcatchments`);
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
    if (!subResp.ok || !geoResp.ok) return null;

    const landuseSummary = await subResp.json();
    const subcatchmentsGeoJson = await geoResp.json();
    if (!landuseSummary || !subcatchmentsGeoJson) return null;

    const basePath = 'landuse/landuse.parquet';
    const landuseLayers = [
      { key: 'lu-dominant', label: 'Dominant landuse', path: basePath, mode: 'dominant', visible: true },
      { key: 'lu-cancov', label: 'Canopy cover (cancov)', path: basePath, mode: 'cancov', visible: false },
      { key: 'lu-inrcov', label: 'Interrill cover (inrcov)', path: basePath, mode: 'inrcov', visible: false },
      { key: 'lu-rilcov', label: 'Rill cover (rilcov)', path: basePath, mode: 'rilcov', visible: false },
    ];

    return { landuseSummary, subcatchmentsGeoJson, landuseLayers };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('gl-dashboard: failed to load landuse overlays', err);
    return null;
  }
}

export async function detectSoilsOverlays({ buildScenarioUrl, buildBaseUrl, subcatchmentsGeoJson }) {
  try {
    const url = buildScenarioUrl(`query/soils/subcatchments`);
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
    if (!subResp.ok || !geoResp.ok) return null;

    const soilsSummary = await subResp.json();
    const geoJson = subcatchmentsGeoJson || (await geoResp.json());
    if (!soilsSummary || !geoJson) return null;

    const basePath = 'soils/soils.parquet';
    const soilsLayers = [
      { key: 'soil-dominant', label: 'Dominant soil (color)', path: basePath, mode: 'dominant', visible: false },
      { key: 'soil-clay', label: 'Clay content (%)', path: basePath, mode: 'clay', visible: false },
      { key: 'soil-sand', label: 'Sand content (%)', path: basePath, mode: 'sand', visible: false },
      { key: 'soil-bd', label: 'Bulk density (g/cm³)', path: basePath, mode: 'bd', visible: false },
      { key: 'soil-rock', label: 'Rock content (%)', path: basePath, mode: 'rock', visible: false },
      { key: 'soil-depth', label: 'Soil depth (mm)', path: basePath, mode: 'soil_depth', visible: false },
    ];

    return { soilsSummary, subcatchmentsGeoJson: geoJson, soilsLayers };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('gl-dashboard: failed to load soils overlays', err);
    return null;
  }
}

export async function detectHillslopesOverlays({ buildScenarioUrl, buildBaseUrl, subcatchmentsGeoJson }) {
  try {
    const url = buildScenarioUrl(`query/watershed/subcatchments`);
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
    if (!subResp.ok || !geoResp.ok) return null;

    const hillslopesSummary = await subResp.json();
    const geoJson = subcatchmentsGeoJson || (await geoResp.json());
    if (!hillslopesSummary || !geoJson) return null;

    const basePath = 'watershed/hillslopes.parquet';
    const hillslopesLayers = [
      { key: 'hillslope-slope', label: 'Slope (rise/run)', path: basePath, mode: 'slope_scalar', visible: false },
      { key: 'hillslope-length', label: 'Hillslope length (m)', path: basePath, mode: 'length', visible: false },
      { key: 'hillslope-aspect', label: 'Aspect (degrees)', path: basePath, mode: 'aspect', visible: false },
    ];

    return { hillslopesSummary, subcatchmentsGeoJson: geoJson, hillslopesLayers };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('gl-dashboard: failed to load hillslopes overlays', err);
    return null;
  }
}

export async function detectWatarOverlays({ buildBaseUrl, postQueryEngine, watarPath, subcatchmentsGeoJson }) {
  try {
    const payload = {
      datasets: [{ path: watarPath, alias: 'wtr' }],
      columns: [
        'wtr.topaz_id AS topaz_id',
        'wtr."wind_transport (tonne/ha)" AS wind_transport',
        'wtr."water_transport (tonne/ha)" AS water_transport',
        'wtr."ash_transport (tonne/ha)" AS ash_transport',
      ],
    };
    const result = await postQueryEngine(payload);
    if (!result || !result.records || !result.records.length) return null;

    const watarSummary = {};
    for (const row of result.records) {
      const topazId = row.topaz_id;
      if (topazId != null) {
        watarSummary[String(topazId)] = row;
      }
    }
    const watarRanges = computeRanges(watarSummary, ['wind_transport', 'water_transport', 'ash_transport']);
    const geoJson = await ensureSubcatchments(buildBaseUrl, subcatchmentsGeoJson);
    if (!geoJson) return { watarSummary, watarRanges, subcatchmentsGeoJson };

    const watarLayers = [
      { key: 'watar-wind', label: 'Wind Transport (tonne/ha)', path: watarPath, mode: 'wind_transport', visible: false },
      { key: 'watar-water', label: 'Water Transport (tonne/ha)', path: watarPath, mode: 'water_transport', visible: false },
      { key: 'watar-ash', label: 'Ash Transport (tonne/ha)', path: watarPath, mode: 'ash_transport', visible: false },
    ];

    return { watarSummary, watarRanges, watarLayers, subcatchmentsGeoJson: geoJson };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('gl-dashboard: failed to load WATAR overlays', err);
    return null;
  }
}

export async function detectWeppOverlays({
  buildBaseUrl,
  fetchWeppSummary,
  weppStatistic,
  weppLossPath,
  subcatchmentsGeoJson,
}) {
  try {
    const geoPromise = subcatchmentsGeoJson
      ? Promise.resolve(subcatchmentsGeoJson)
      : fetch(buildBaseUrl(`resources/subcatchments.json`)).then((resp) => (resp.ok ? resp.json() : null));

    const [weppSummary, geoJson] = await Promise.all([fetchWeppSummary(weppStatistic), geoPromise]);
    const resolvedGeo = subcatchmentsGeoJson || geoJson;
    if (!weppSummary || !resolvedGeo) return null;

    const weppRanges = computeRanges(weppSummary, [
      'runoff_volume',
      'subrunoff_volume',
      'baseflow_volume',
      'soil_loss',
      'sediment_deposition',
      'sediment_yield',
    ]);

    const weppLayers = [
      { key: 'wepp-runoff', label: 'Runoff Volume (mm)', path: weppLossPath, mode: 'runoff_volume', visible: false },
      { key: 'wepp-subrunoff', label: 'Subrunoff Volume (mm)', path: weppLossPath, mode: 'subrunoff_volume', visible: false },
      { key: 'wepp-baseflow', label: 'Baseflow Volume (mm)', path: weppLossPath, mode: 'baseflow_volume', visible: false },
      { key: 'wepp-soil-loss', label: 'Soil Loss (tonnes/ha)', path: weppLossPath, mode: 'soil_loss', visible: false },
      { key: 'wepp-sed-dep', label: 'Sediment Deposition (tonnes/ha)', path: weppLossPath, mode: 'sediment_deposition', visible: false },
      { key: 'wepp-sed-yield', label: 'Sediment Yield (tonnes/ha)', path: weppLossPath, mode: 'sediment_yield', visible: false },
    ];

    return { weppSummary, weppRanges, weppLayers, subcatchmentsGeoJson: resolvedGeo };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('gl-dashboard: failed to load WEPP overlays', err);
    return null;
  }
}

export async function detectWeppYearlyOverlays({
  buildBaseUrl,
  postQueryEngine,
  weppYearlyPath,
  currentSelectedYear,
  subcatchmentsGeoJson,
}) {
  try {
    const yearsPayload = {
      datasets: [{ path: weppYearlyPath, alias: 'loss' }],
      columns: ['DISTINCT loss.year AS year'],
      order_by: ['year'],
    };
    const yearsResult = await postQueryEngine(yearsPayload);
    if (!yearsResult || !yearsResult.records || !yearsResult.records.length) {
      return { weppYearlyLayers: [], weppYearlyMetadata: null, weppYearlySelectedYear: null, subcatchmentsGeoJson };
    }

    const years = yearsResult.records
      .map((r) => Number(r.year))
      .filter((y) => Number.isFinite(y))
      .sort((a, b) => a - b);
    if (!years.length) {
      return { weppYearlyLayers: [], weppYearlyMetadata: null, weppYearlySelectedYear: null, subcatchmentsGeoJson };
    }

    const geoJson = await ensureSubcatchments(buildBaseUrl, subcatchmentsGeoJson);
    if (!geoJson) {
      return { weppYearlyLayers: [], weppYearlyMetadata: null, weppYearlySelectedYear: null, subcatchmentsGeoJson };
    }

    const metadata = {
      years,
      minYear: years[0],
      maxYear: years[years.length - 1],
    };
    const selectedYear =
      Number.isFinite(currentSelectedYear) && currentSelectedYear >= metadata.minYear && currentSelectedYear <= metadata.maxYear
        ? currentSelectedYear
        : metadata.maxYear;

    const weppYearlyLayers = [
      { key: 'wepp-yearly-runoff', label: 'Runoff Volume (mm)', path: weppYearlyPath, mode: 'runoff_volume', visible: false },
      { key: 'wepp-yearly-subrunoff', label: 'Subrunoff Volume (mm)', path: weppYearlyPath, mode: 'subrunoff_volume', visible: false },
      { key: 'wepp-yearly-baseflow', label: 'Baseflow Volume (mm)', path: weppYearlyPath, mode: 'baseflow_volume', visible: false },
      { key: 'wepp-yearly-soil-loss', label: 'Soil Loss (tonnes/ha)', path: weppYearlyPath, mode: 'soil_loss', visible: false },
      { key: 'wepp-yearly-sed-dep', label: 'Sediment Deposition (tonnes/ha)', path: weppYearlyPath, mode: 'sediment_deposition', visible: false },
      { key: 'wepp-yearly-sed-yield', label: 'Sediment Yield (tonnes/ha)', path: weppYearlyPath, mode: 'sediment_yield', visible: false },
    ];

    return {
      weppYearlyLayers,
      weppYearlyMetadata: metadata,
      weppYearlySelectedYear: selectedYear,
      subcatchmentsGeoJson: geoJson,
    };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('gl-dashboard: failed to load WEPP yearly overlays', err);
    return null;
  }
}

export async function detectWeppEventOverlays({
  buildBaseUrl,
  climateCtx,
  currentSelectedDate,
  subcatchmentsGeoJson,
}) {
  try {
    if (!climateCtx || !climateCtx.startYear || !climateCtx.endYear) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: no climate context available for WEPP Event');
      return null;
    }

    const minYear = climateCtx.startYear;
    const maxYear = climateCtx.endYear;
    const metadata = {
      available: true,
      startDate: `${minYear}-01-01`,
      endDate: `${maxYear}-12-31`,
    };
    const selectedDate = currentSelectedDate || metadata.startDate;

    const geoJson = await ensureSubcatchments(buildBaseUrl, subcatchmentsGeoJson);
    if (!geoJson) return null;

    const weppEventLayers = [
      { key: 'wepp-event-P', label: 'Precipitation (P)', path: 'wepp/output/interchange/H.wat.parquet', mode: 'event_P', visible: false },
      { key: 'wepp-event-Q', label: 'Runoff (Q)', path: 'wepp/output/interchange/H.wat.parquet', mode: 'event_Q', visible: false },
      { key: 'wepp-event-ET', label: 'Total ET (Ep+Es+Er)', path: 'wepp/output/interchange/H.wat.parquet', mode: 'event_ET', visible: false },
      { key: 'wepp-event-peakro', label: 'Peak Runoff Rate', path: 'wepp/output/interchange/H.pass.parquet', mode: 'event_peakro', visible: false },
      { key: 'wepp-event-tdet', label: 'Total Detachment', path: 'wepp/output/interchange/H.pass.parquet', mode: 'event_tdet', visible: false },
    ];

    return { weppEventLayers, weppEventMetadata: metadata, weppEventSelectedDate: selectedDate, subcatchmentsGeoJson: geoJson };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('gl-dashboard: failed to load WEPP Event overlays', err);
    return null;
  }
}

export async function detectRapOverlays({
  buildBaseUrl,
  postQueryEngine,
  rapBandLabels,
  subcatchmentsGeoJson,
  currentSelectedYear,
}) {
  try {
    const yearsPayload = {
      datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
      columns: ['DISTINCT rap.year AS year'],
      order_by: ['year'],
    };
    const yearsResult = await postQueryEngine(yearsPayload);
    if (!yearsResult || !yearsResult.records || !yearsResult.records.length) return null;

    const bandsPayload = {
      datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
      columns: ['DISTINCT rap.band AS band'],
      order_by: ['band'],
    };
    const bandsResult = await postQueryEngine(bandsPayload);
    if (!bandsResult || !bandsResult.records || !bandsResult.records.length) return null;

    const years = yearsResult.records.map((r) => r.year);
    const bands = bandsResult.records.map((r) => r.band);

    const RAP_BAND_ID_TO_KEY = {
      1: 'annual_forb_grass',
      2: 'bare_ground',
      3: 'litter',
      4: 'perennial_forb_grass',
      5: 'shrub',
      6: 'tree',
    };
    const rapMetadata = {
      available: true,
      years,
      bands: bands.map((id) => ({ id, label: RAP_BAND_ID_TO_KEY[id] || `band_${id}` })),
    };

    let rapSelectedYear = null;
    if (years.length) {
      const latestYear = years[years.length - 1];
      rapSelectedYear =
        years.includes(currentSelectedYear) && Number.isFinite(currentSelectedYear) ? currentSelectedYear : latestYear;
    }

    const geoJson = await ensureSubcatchments(buildBaseUrl, subcatchmentsGeoJson);
    if (!geoJson) {
      return { rapMetadata, rapSelectedYear, subcatchmentsGeoJson };
    }

    const DEFAULT_SELECTED_BANDS = ['tree', 'shrub'];
    const basePath = 'rap/rap_ts.parquet';
    const rapLayers = [];
    for (const band of rapMetadata.bands) {
      const label = rapBandLabels[band.label] || band.label;
      rapLayers.push({
        key: `rap-${band.label}`,
        label: `${label} (%)`,
        path: basePath,
        bandId: band.id,
        bandKey: band.label,
        visible: false,
        selected: DEFAULT_SELECTED_BANDS.includes(band.label),
      });
    }

    let rapSummary = null;
    if (rapLayers.length && rapSelectedYear) {
      const firstBand = rapLayers[0];
      const dataPayload = {
        datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
        columns: ['rap.topaz_id AS topaz_id', 'rap.value AS value'],
        filters: [
          { column: 'rap.year', op: '=', value: rapSelectedYear },
          { column: 'rap.band', op: '=', value: firstBand.bandId },
        ],
      };
      const dataResult = await postQueryEngine(dataPayload);
      if (dataResult && dataResult.records) {
        rapSummary = {};
        for (const row of dataResult.records) {
          rapSummary[String(row.topaz_id)] = row.value;
        }
      }
    }

    return { rapLayers, rapMetadata, rapSelectedYear, rapSummary, subcatchmentsGeoJson: geoJson };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('gl-dashboard: failed to load RAP overlays', err);
    return null;
  }
}
