/**
 * Detection helpers for gl-dashboard overlays.
 * Pure data routines: fetch summaries/metadata and return overlay descriptors.
 * No DOM/deck access; suitable for tests/workers.
 */

import {
  DASHBOARD_MODES,
  buildBatchFeatureKey,
  resolveTopazIdFromProperties,
} from '../batch-keys.js';

function logDetection(kind, message, context) {
  const parts = [`gl-dashboard detection: ${message}`];
  if (context !== undefined) {
    parts.push(context);
  }
  console[kind](...parts);
}

const logDetectionInfo = (message, context) => logDetection('info', message, context);
const logDetectionWarn = (message, context) => logDetection('warn', message, context);

const DEFAULT_BATCH_FETCH_CONCURRENCY = 6;

const _batchGeoJsonCache = new Map();

function isBatchContext(ctx) {
  return (
    ctx &&
    ctx.mode === DASHBOARD_MODES.BATCH &&
    ctx.batch &&
    Array.isArray(ctx.batch.runs)
  );
}

function normalizeSitePrefix(prefix) {
  if (!prefix) return '';
  return String(prefix).replace(/\/+$/, '');
}

function normalizeRelativePath(value) {
  if (!value) return '';
  return String(value).replace(/^\/+/, '');
}

function encodeCompositeRunId(runid) {
  const raw = String(runid || '').trim();
  if (!raw) return '';
  if (raw.indexOf(';;') === -1) {
    return encodeURIComponent(raw);
  }
  return raw
    .split(';;')
    .map((segment) => encodeURIComponent(segment))
    .join(';;');
}

function buildRunUrlFromCtx(ctx, runid, relativePath) {
  const sitePrefix = normalizeSitePrefix(ctx && ctx.sitePrefix);
  const runSlug = String(runid || '').trim();
  const configSlug = String(ctx && ctx.config ? ctx.config : '').trim();
  const path = normalizeRelativePath(relativePath);
  const runPath = `/runs/${encodeCompositeRunId(runSlug)}/${encodeCompositeRunId(configSlug)}/`;
  return (sitePrefix ? sitePrefix + runPath : runPath) + path;
}

async function mapWithConcurrency(items, limit, handler) {
  if (!Array.isArray(items) || !items.length) return [];
  const concurrency = Math.max(1, Math.min(Number(limit) || 1, items.length));
  const results = new Array(items.length);
  let nextIndex = 0;

  async function worker() {
    while (nextIndex < items.length) {
      const idx = nextIndex;
      nextIndex += 1;
      try {
        results[idx] = await handler(items[idx], idx);
      } catch (err) {
        results[idx] = null;
      }
    }
  }

  await Promise.all(Array.from({ length: concurrency }, () => worker()));
  return results;
}

function decorateGeoJsonFeaturesForBatch(geoJson, run) {
  if (!geoJson || !Array.isArray(geoJson.features)) return geoJson;
  const runid = run && run.runid != null ? String(run.runid) : '';
  const leaf = run && run.leaf_runid != null ? String(run.leaf_runid) : '';
  geoJson.features.forEach((feature) => {
    if (!feature || typeof feature !== 'object') return;
    const props = feature.properties && typeof feature.properties === 'object' ? feature.properties : {};
    feature.properties = props;
    if (runid) {
      props.runid = runid;
    }
    if (leaf) {
      props.leaf_runid = leaf;
    }
    const topazId = resolveTopazIdFromProperties(props);
    if (topazId == null) return;
    if (props.topaz_id == null) {
      props.topaz_id = topazId;
    }
    if (props.feature_key == null && runid) {
      props.feature_key = buildBatchFeatureKey(runid, topazId);
    }
    if (feature.id == null && props.feature_key != null) {
      feature.id = String(props.feature_key);
    }
  });
  return geoJson;
}

function mergeFeatureCollections(collections, { name } = {}) {
  const mergedFeatures = [];
  let crs = null;
  for (const collection of collections) {
    if (!collection || !Array.isArray(collection.features) || !collection.features.length) {
      continue;
    }
    if (!crs && collection.crs) {
      crs = collection.crs;
    }
    mergedFeatures.push(...collection.features);
  }
  if (!mergedFeatures.length) return null;
  const merged = { type: 'FeatureCollection', features: mergedFeatures };
  if (crs) merged.crs = crs;
  if (name) merged.name = name;
  return merged;
}

async function ensureBatchGeoJson(ctx, kind) {
  if (!isBatchContext(ctx)) return null;
  const baseKey =
    (ctx.batch && (ctx.batch.base_runid || ctx.batch.name)) || String(ctx.runid || 'batch');
  const cacheKey = `${baseKey}::${String(ctx.config || '')}::${kind}`;
  if (_batchGeoJsonCache.has(cacheKey)) {
    return _batchGeoJsonCache.get(cacheKey);
  }

  const promise = (async () => {
    const runs = ctx.batch.runs;
    const relPath = kind === 'channels' ? 'resources/channels.json' : 'resources/subcatchments.json';
    const label = kind === 'channels' ? 'Channels GeoJSON' : 'Subcatchments GeoJSON';
    const perRun = await mapWithConcurrency(runs, DEFAULT_BATCH_FETCH_CONCURRENCY, async (run) => {
      const url = buildRunUrlFromCtx(ctx, run.runid, relPath);
      const resp = await fetch(url);
      if (!resp.ok) {
        logDetectionInfo(`${label} missing`, { url, status: resp.status });
        return null;
      }
      const payload = await resp.json();
      if (!payload || !Array.isArray(payload.features) || !payload.features.length) {
        logDetectionInfo(`${label} empty`, { url });
        return null;
      }
      return decorateGeoJsonFeaturesForBatch(payload, run);
    });

    const merged = mergeFeatureCollections(perRun.filter(Boolean), {
      name: ctx.batch && ctx.batch.name ? `batch:${ctx.batch.name}` : 'batch',
    });
    if (!merged) {
      logDetectionInfo(`Batch ${label} unavailable`, { kind, runs: runs.length });
    }
    return merged;
  })();

  _batchGeoJsonCache.set(cacheKey, promise);
  return promise;
}

async function fetchBatchSummary(ctx, relativePath, { label } = {}) {
  if (!isBatchContext(ctx)) return null;
  const runs = ctx.batch.runs;
  const perRun = await mapWithConcurrency(runs, DEFAULT_BATCH_FETCH_CONCURRENCY, async (run) => {
    const url = buildRunUrlFromCtx(ctx, run.runid, relativePath);
    const resp = await fetch(url);
    if (!resp.ok) {
      logDetectionInfo(`${label || relativePath} missing`, { url, status: resp.status });
      return null;
    }
    const payload = await resp.json();
    if (!payload || Array.isArray(payload) || typeof payload !== 'object') {
      logDetectionInfo(`${label || relativePath} empty`, { url });
      return null;
    }
    return { run, payload };
  });

  const merged = {};
  let mergedCount = 0;
  for (const item of perRun) {
    if (!item) continue;
    const runid = String(item.run.runid || '');
    if (!runid) continue;
    for (const [topazId, row] of Object.entries(item.payload)) {
      if (topazId == null || topazId === '') continue;
      try {
        const featureKey = buildBatchFeatureKey(runid, topazId);
        merged[featureKey] = row;
        mergedCount += 1;
      } catch (err) {
        continue;
      }
    }
  }

  return mergedCount ? merged : null;
}

function countFeaturesByRunId(geoJson) {
  const counts = {};
  if (!geoJson || !Array.isArray(geoJson.features) || !geoJson.features.length) {
    return counts;
  }
  for (const feature of geoJson.features) {
    const props = feature && feature.properties;
    if (!props || typeof props !== 'object') continue;
    const runid = props.runid || props.run_id;
    if (!runid) continue;
    const key = String(runid);
    counts[key] = (counts[key] || 0) + 1;
  }
  return counts;
}

async function checkRunSummaryEndpoint(ctx, run, relativePath, { label } = {}) {
  const url = buildRunUrlFromCtx(ctx, run.runid, relativePath);
  const resp = await fetch(url);
  if (!resp.ok) {
    return { ok: false, status: resp.status, url, label: label || relativePath };
  }
  const payload = await resp.json();
  const ok =
    payload &&
    typeof payload === 'object' &&
    !Array.isArray(payload) &&
    Object.keys(payload).length > 0;
  return { ok, status: resp.status, url, label: label || relativePath };
}

export async function detectBatchReadiness({ ctx } = {}) {
  try {
    if (!isBatchContext(ctx)) return null;

    const allRuns = ctx.batch.runs;

    // Required: subcatchment geometry must be available to participate in the batch map.
    const subcatchmentsGeoJson = await ensureBatchGeoJson(ctx, 'subcatchments');
    const subcatchmentCounts = countFeaturesByRunId(subcatchmentsGeoJson);

    // Optional: channel geometry, used for channel overlay/labels.
    const channelsGeoJson = await ensureBatchGeoJson(ctx, 'channels');
    const channelCounts = countFeaturesByRunId(channelsGeoJson);

    const statuses = allRuns.map((run) => {
      const runid = run && run.runid != null ? String(run.runid) : '';
      const leaf = run && run.leaf_runid != null ? String(run.leaf_runid) : runid;
      const subcatchments = runid ? subcatchmentCounts[runid] || 0 : 0;
      const channels = runid ? channelCounts[runid] || 0 : 0;
      const missingRequired = [];
      const missingOptional = [];
      if (!subcatchments) {
        missingRequired.push('subcatchments');
      }
      if (!channels) {
        missingOptional.push('channels');
      }
      return {
        runid,
        leaf_runid: leaf,
        ready: missingRequired.length === 0,
        counts: { subcatchments, channels },
        missingRequired,
        missingOptional,
        summaries: {},
      };
    });

    const readyRuns = statuses
      .filter((s) => s.ready)
      .map((s) => ({ runid: s.runid, leaf_runid: s.leaf_runid }));

    // Optional summaries (used for supported batch overlays).
    const summaryChecks = [
      { key: 'landuse', label: 'Landuse summary', path: 'query/landuse/subcatchments' },
      { key: 'soils', label: 'Soils summary', path: 'query/soils/subcatchments' },
      { key: 'hillslopes', label: 'Hillslopes summary', path: 'query/watershed/subcatchments' },
    ];

    const byRunId = new Map(statuses.map((s) => [s.runid, s]));
    await mapWithConcurrency(readyRuns, DEFAULT_BATCH_FETCH_CONCURRENCY, async (run) => {
      const status = byRunId.get(String(run.runid || ''));
      if (!status) return null;
      for (const check of summaryChecks) {
        try {
          const result = await checkRunSummaryEndpoint(ctx, run, check.path, { label: check.label });
          status.summaries[check.key] = result;
          if (!result.ok) {
            status.missingOptional.push(check.key);
          }
        } catch (err) {
          status.summaries[check.key] = { ok: false, status: null, url: null, label: check.label };
          status.missingOptional.push(check.key);
        }
      }
      return null;
    });

    // De-dupe missingOptional arrays after summary checks.
    for (const status of statuses) {
      if (status && Array.isArray(status.missingOptional) && status.missingOptional.length > 1) {
        status.missingOptional = Array.from(new Set(status.missingOptional));
      }
    }

    return {
      totalRuns: allRuns.length,
      readyRuns,
      statuses,
      mergedCounts: {
        subcatchments: subcatchmentsGeoJson && Array.isArray(subcatchmentsGeoJson.features) ? subcatchmentsGeoJson.features.length : 0,
        channels: channelsGeoJson && Array.isArray(channelsGeoJson.features) ? channelsGeoJson.features.length : 0,
      },
    };
  } catch (err) {
    logDetectionWarn('failed to detect batch readiness', err);
    return null;
  }
}

const D8_POINTER_DELTAS = Object.freeze({
  1: [1, 1],
  2: [1, 0],
  4: [1, -1],
  8: [0, -1],
  16: [-1, -1],
  32: [-1, 0],
  64: [-1, 1],
  128: [0, 1],
});

const DEFAULT_D8_MAX_ARROWS = Number.POSITIVE_INFINITY;

function computeSampleStride(totalCells, maxArrows) {
  if (!Number.isFinite(totalCells) || totalCells <= 0) return 1;
  if (!Number.isFinite(maxArrows) || maxArrows <= 0) return 1;
  if (totalCells <= maxArrows) return 1;
  return Math.max(1, Math.ceil(Math.sqrt(totalCells / maxArrows)));
}

function buildD8ArrowData({ values, width, height, bounds, nodata, maxArrows }) {
  if (!values || !Number.isFinite(width) || !Number.isFinite(height) || !Array.isArray(bounds) || bounds.length !== 4) {
    return { data: [], stride: 1 };
  }
  const [west, south, east, north] = bounds;
  const cellWidth = (east - west) / width;
  const cellHeight = (north - south) / height;
  if (!Number.isFinite(cellWidth) || !Number.isFinite(cellHeight) || cellWidth === 0 || cellHeight === 0) {
    return { data: [], stride: 1 };
  }

  const totalCells = width * height;
  const stride = computeSampleStride(totalCells, maxArrows);
  const data = [];

  for (let row = 0; row < height; row += stride) {
    const lat = north - (row + 0.5) * cellHeight;
    const rowOffset = row * width;
    for (let col = 0; col < width; col += stride) {
      const code = values[rowOffset + col];
      if (code === 0 || (nodata !== null && nodata !== undefined && code === nodata)) {
        continue;
      }
      const delta = D8_POINTER_DELTAS[code];
      if (!delta) continue;
      const [dxCell, dyCell] = delta;
      const lon = west + (col + 0.5) * cellWidth;
      const angle = (Math.atan2(dyCell, dxCell) * 180) / Math.PI;
      if (!Number.isFinite(angle)) continue;
      data.push({
        position: [lon, lat],
        angle,
      });
    }
  }

  return { data, stride };
}

function resolveD8CellSizeMeters(info) {
  if (!info || typeof info !== 'object') return null;
  const metadata = info.metadata;
  if (!metadata || typeof metadata !== 'object') return null;
  const domain = metadata[''] || metadata.DEFAULT || metadata.default || null;
  let raw = domain && typeof domain === 'object' ? domain.WEPP_CELL_SIZE_M : undefined;
  if (raw === undefined && Object.prototype.hasOwnProperty.call(metadata, 'WEPP_CELL_SIZE_M')) {
    raw = metadata.WEPP_CELL_SIZE_M;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

function collectGeometryCoordinates(geometry) {
  if (!geometry || !geometry.coordinates) return [];
  const coords = geometry.coordinates;
  switch (geometry.type) {
    case 'Point':
      return [coords];
    case 'MultiPoint':
    case 'LineString':
      return Array.isArray(coords) ? coords : [];
    case 'MultiLineString': {
      const merged = [];
      if (Array.isArray(coords)) {
        coords.forEach((line) => {
          if (Array.isArray(line)) {
            merged.push(...line);
          }
        });
      }
      return merged;
    }
    case 'Polygon':
      return Array.isArray(coords) && Array.isArray(coords[0]) ? coords[0] : [];
    case 'MultiPolygon':
      return Array.isArray(coords) && Array.isArray(coords[0]) && Array.isArray(coords[0][0]) ? coords[0][0] : [];
    default:
      return [];
  }
}

function resolveGeometryCenter(geometry) {
  const coords = collectGeometryCoordinates(geometry);
  if (!coords.length) return null;
  let sumX = 0;
  let sumY = 0;
  let count = 0;
  coords.forEach((pt) => {
    if (!Array.isArray(pt) || pt.length < 2) return;
    const x = Number(pt[0]);
    const y = Number(pt[1]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    sumX += x;
    sumY += y;
    count += 1;
  });
  if (!count) return null;
  return [sumX / count, sumY / count];
}

function buildChannelLabelData(geoJson) {
  const labels = [];
  const seen = new Set();
  const features = geoJson && Array.isArray(geoJson.features) ? geoJson.features : [];
  features.forEach((feature) => {
    const props = feature && feature.properties ? feature.properties : {};
    const topazId = props.TopazID || props.topaz_id || props.topaz || props.id || props.WeppID || props.wepp_id;
    if (topazId == null) return;
    const key = props.feature_key != null ? String(props.feature_key) : String(topazId);
    if (seen.has(key)) return;
    const position = resolveGeometryCenter(feature.geometry);
    if (!position) return;
    const leafRunId = props.leaf_runid || null;
    const runLabel = leafRunId ? String(leafRunId) : props.runid ? String(props.runid) : null;
    const text = runLabel ? `${runLabel}:${topazId}` : String(topazId);
    labels.push({ text, position });
    seen.add(key);
  });
  return labels;
}

async function detectSbsLayer({ ctx, loadSbsImage }) {
  const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/query/baer_wgs_map`;
  const resp = await fetch(url);
  if (!resp.ok) {
    logDetectionInfo('SBS map not available', { url, status: resp.status });
    return null;
  }
  const payload = await resp.json();
  if (!payload || !payload.Content) {
    logDetectionInfo('SBS response missing content', { url });
    return null;
  }

  let { bounds } = payload.Content;
  const imgurl = payload.Content.imgurl;
  if (!bounds || !imgurl) {
    logDetectionInfo('SBS payload missing bounds/image', { url, hasBounds: Boolean(bounds), hasImg: Boolean(imgurl) });
    return null;
  }

  // Normalize bounds: API returns [[lat1, lon1], [lat2, lon2]]
  if (Array.isArray(bounds) && bounds.length === 2 && Array.isArray(bounds[0]) && Array.isArray(bounds[1])) {
    const [lat1, lon1] = bounds[0];
    const [lat2, lon2] = bounds[1];
    bounds = [lon1, lat1, lon2, lat2];
  }
  if (!Array.isArray(bounds) || bounds.length !== 4 || bounds.some((v) => !Number.isFinite(v))) {
    logDetectionInfo('SBS bounds invalid', { url, bounds });
    return null;
  }

  const raster = await loadSbsImage(imgurl);
  if (!raster) {
    logDetectionInfo('SBS image failed to load', { imgurl });
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

export function computeBoundsFromGdal(info) {
  const wgs84 = info && info.wgs84Extent && info.wgs84Extent.coordinates;
  if (Array.isArray(wgs84) && wgs84.length) {
    const ring = Array.isArray(wgs84[0]) && Array.isArray(wgs84[0][0]) ? wgs84[0] : wgs84;
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
   logDetectionInfo('Subcatchments GeoJSON missing', { geoUrl, status: geoResp.status });
  return subcatchmentsGeoJson;
}

async function ensureChannels(buildBaseUrl, channelsGeoJson) {
  if (channelsGeoJson) {
    return channelsGeoJson;
  }
  const geoUrl = buildBaseUrl(`resources/channels.json`);
  const geoResp = await fetch(geoUrl);
  if (geoResp.ok) {
    return geoResp.json();
  }
  logDetectionInfo('Channels GeoJSON missing', { geoUrl, status: geoResp.status });
  return channelsGeoJson;
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

function formatMonthLabel(entry, monthLabels) {
  if (!entry) return '';
  const labels = Array.isArray(monthLabels) && monthLabels.length === 12
    ? monthLabels
    : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monthIndex = Number(entry.month) - 1;
  const monthLabel = monthIndex >= 0 && monthIndex < labels.length ? labels[monthIndex] : String(entry.month || '');
  return monthLabel && entry.year ? `${monthLabel} ${entry.year}` : String(entry.year || '');
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
    logDetectionWarn('failed to load SBS map', err);
  }

  for (const def of layerDefs) {
    let found = null;
    for (const path of def.paths) {
      try {
        const info = await fetchGdalInfo(path);
        if (!info) continue;
        const wgs84Bounds = computeBoundsFromGdal(info);
        const colorMap = def.key === 'landuse' ? nlcdColormap : def.key === 'soils' ? soilColorForValue : null;
        const raster = await loadRaster(path, colorMap);
        const bounds = wgs84Bounds || raster.bounds;
        if (!bounds) continue;
        found = {
          key: def.key,
          label: def.label,
          path,
          ...raster,
          bounds,
          visible: false,
        };
        break;
      } catch (err) {
        logDetectionWarn(`failed to load ${def.label} at ${path}`, err);
      }
    }
    if (found) {
      detectedLayers.push(found);
    }
  }

  return { detectedLayers };
}

export async function detectOpenetOverlays({
  buildBaseUrl,
  postBaseQueryEngine,
  monthLabels,
  subcatchmentsGeoJson,
  currentSelectedMonthIndex,
  currentSelectedDatasetKey,
}) {
  try {
    const datasetPayload = {
      datasets: [{ path: 'openet/openet_ts.parquet', alias: 'openet' }],
      columns: ['DISTINCT openet.dataset_key AS dataset_key'],
      order_by: ['dataset_key'],
    };
    const datasetResult = await postBaseQueryEngine(datasetPayload);
    if (!datasetResult || !datasetResult.records || !datasetResult.records.length) {
      logDetectionInfo('OpenET overlays missing dataset keys');
      return null;
    }

    const datasetKeys = datasetResult.records
      .map((row) => row.dataset_key)
      .filter((key) => typeof key === 'string' && key.length);
    if (!datasetKeys.length) {
      logDetectionInfo('OpenET overlays missing dataset keys');
      return null;
    }

    const monthsPayload = {
      datasets: [{ path: 'openet/openet_ts.parquet', alias: 'openet' }],
      columns: ['DISTINCT openet.year AS year', 'openet.month AS month'],
      order_by: ['year', 'month'],
    };
    const monthsResult = await postBaseQueryEngine(monthsPayload);
    if (!monthsResult || !monthsResult.records || !monthsResult.records.length) {
      logDetectionInfo('OpenET overlays missing month list');
      return null;
    }

    const months = monthsResult.records
      .map((row) => ({ year: Number(row.year), month: Number(row.month) }))
      .filter((row) => Number.isFinite(row.year) && Number.isFinite(row.month) && row.month >= 1 && row.month <= 12)
      .sort((a, b) => (a.year !== b.year ? a.year - b.year : a.month - b.month))
      .map((row) => ({ ...row, label: formatMonthLabel(row, monthLabels) }));

    if (!months.length) {
      logDetectionInfo('OpenET overlays missing month list');
      return null;
    }

    let selectedDatasetKey = null;
    if (currentSelectedDatasetKey && datasetKeys.includes(currentSelectedDatasetKey)) {
      selectedDatasetKey = currentSelectedDatasetKey;
    } else if (datasetKeys.includes('ensemble')) {
      selectedDatasetKey = 'ensemble';
    } else {
      selectedDatasetKey = datasetKeys[0];
    }

    let selectedMonthIndex = Number.isFinite(currentSelectedMonthIndex) ? currentSelectedMonthIndex : months.length - 1;
    if (selectedMonthIndex < 0 || selectedMonthIndex >= months.length) {
      selectedMonthIndex = months.length - 1;
    }

    const geoJson = await ensureSubcatchments(buildBaseUrl, subcatchmentsGeoJson);
    if (!geoJson) {
      return {
        openetLayers: [],
        openetMetadata: { months, datasetKeys },
        openetSelectedDatasetKey: selectedDatasetKey,
        openetSelectedMonthIndex: selectedMonthIndex,
        subcatchmentsGeoJson: geoJson,
      };
    }

    const openetLayers = datasetKeys.map((key) => ({
      key,
      label: key,
      datasetKey: key,
      path: 'openet/openet_ts.parquet',
      mode: 'openet_et',
      units: 'mm',
      visible: false,
    }));

    return {
      openetLayers,
      openetMetadata: { months, datasetKeys },
      openetSummary: null,
      openetRanges: {},
      openetSelectedDatasetKey: selectedDatasetKey,
      openetSelectedMonthIndex: selectedMonthIndex,
      subcatchmentsGeoJson: geoJson,
    };
  } catch (err) {
    logDetectionWarn('failed to load OpenET overlays', err);
    return null;
  }
}

export async function detectLanduseOverlays({ ctx, buildScenarioUrl, buildBaseUrl, subcatchmentsGeoJson } = {}) {
  try {
    if (isBatchContext(ctx)) {
      const [landuseSummary, geoJson] = await Promise.all([
        fetchBatchSummary(ctx, 'query/landuse/subcatchments', { label: 'Landuse summary' }),
        subcatchmentsGeoJson ? Promise.resolve(subcatchmentsGeoJson) : ensureBatchGeoJson(ctx, 'subcatchments'),
      ]);
      if (!landuseSummary || !geoJson) {
        logDetectionInfo('Batch landuse overlays missing summary or geometry', {
          hasSummary: Boolean(landuseSummary),
          hasGeoJson: Boolean(geoJson),
        });
        return null;
      }

      const basePath = 'landuse/landuse.parquet';
      const landuseLayers = [
        { key: 'lu-dominant', label: 'Dominant landuse', path: basePath, mode: 'dominant', visible: true },
        { key: 'lu-cancov', label: 'Canopy cover (cancov)', path: basePath, mode: 'cancov', visible: false },
        { key: 'lu-inrcov', label: 'Interrill cover (inrcov)', path: basePath, mode: 'inrcov', visible: false },
        { key: 'lu-rilcov', label: 'Rill cover (rilcov)', path: basePath, mode: 'rilcov', visible: false },
      ];

      return { landuseSummary, subcatchmentsGeoJson: geoJson, landuseLayers };
    }

    const url = buildScenarioUrl(`query/landuse/subcatchments`);
    const geoUrl = subcatchmentsGeoJson ? null : buildBaseUrl(`resources/subcatchments.json`);
    const [subResp, geoResp] = await Promise.all([fetch(url), geoUrl ? fetch(geoUrl) : Promise.resolve(null)]);
    if (!subResp.ok || (geoResp && !geoResp.ok)) {
      logDetectionInfo('Landuse overlays missing', { subStatus: subResp.status, geoStatus: geoResp ? geoResp.status : null });
      return null;
    }

    const landuseSummary = await subResp.json();
    const resolvedGeoJson = subcatchmentsGeoJson || (geoResp ? await geoResp.json() : null);
    if (!landuseSummary || !resolvedGeoJson) {
      logDetectionInfo('Landuse overlays unavailable (empty payload)', {
        hasSummary: Boolean(landuseSummary),
        hasGeoJson: Boolean(resolvedGeoJson),
      });
      return null;
    }

    const basePath = 'landuse/landuse.parquet';
    const landuseLayers = [
      { key: 'lu-dominant', label: 'Dominant landuse', path: basePath, mode: 'dominant', visible: true },
      { key: 'lu-cancov', label: 'Canopy cover (cancov)', path: basePath, mode: 'cancov', visible: false },
      { key: 'lu-inrcov', label: 'Interrill cover (inrcov)', path: basePath, mode: 'inrcov', visible: false },
      { key: 'lu-rilcov', label: 'Rill cover (rilcov)', path: basePath, mode: 'rilcov', visible: false },
    ];

    return { landuseSummary, subcatchmentsGeoJson: resolvedGeoJson, landuseLayers };
  } catch (err) {
    logDetectionWarn('failed to load landuse overlays', err);
    return null;
  }
}

export async function detectSoilsOverlays({ ctx, buildScenarioUrl, buildBaseUrl, subcatchmentsGeoJson }) {
  try {
    if (isBatchContext(ctx)) {
      const [soilsSummary, geoJson] = await Promise.all([
        fetchBatchSummary(ctx, 'query/soils/subcatchments', { label: 'Soils summary' }),
        subcatchmentsGeoJson ? Promise.resolve(subcatchmentsGeoJson) : ensureBatchGeoJson(ctx, 'subcatchments'),
      ]);
      if (!soilsSummary || !geoJson) {
        logDetectionInfo('Batch soils overlays missing summary or geometry', {
          hasSummary: Boolean(soilsSummary),
          hasGeoJson: Boolean(geoJson),
        });
        return null;
      }

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
    }

    const url = buildScenarioUrl(`query/soils/subcatchments`);
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
    if (!subResp.ok || !geoResp.ok) {
      logDetectionInfo('Soils overlays missing', { subStatus: subResp.status, geoStatus: geoResp.status });
      return null;
    }

    const soilsSummary = await subResp.json();
    const geoJson = subcatchmentsGeoJson || (await geoResp.json());
    if (!soilsSummary || !geoJson) {
      logDetectionInfo('Soils overlays unavailable (empty payload)', {
        hasSummary: Boolean(soilsSummary),
        hasGeoJson: Boolean(geoJson),
      });
      return null;
    }

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
    logDetectionWarn('failed to load soils overlays', err);
    return null;
  }
}

export async function detectHillslopesOverlays({ ctx, buildScenarioUrl, buildBaseUrl, subcatchmentsGeoJson }) {
  try {
    if (isBatchContext(ctx)) {
      const [hillslopesSummary, geoJson] = await Promise.all([
        fetchBatchSummary(ctx, 'query/watershed/subcatchments', { label: 'Hillslopes summary' }),
        subcatchmentsGeoJson ? Promise.resolve(subcatchmentsGeoJson) : ensureBatchGeoJson(ctx, 'subcatchments'),
      ]);
      if (!hillslopesSummary || !geoJson) {
        logDetectionInfo('Batch hillslopes overlays missing summary or geometry', {
          hasSummary: Boolean(hillslopesSummary),
          hasGeoJson: Boolean(geoJson),
        });
        return null;
      }

      const basePath = 'watershed/hillslopes.parquet';
      const hillslopesLayers = [
        { key: 'hillslope-slope', label: 'Slope (rise/run)', path: basePath, mode: 'slope_scalar', visible: false },
        { key: 'hillslope-length', label: 'Hillslope length (m)', path: basePath, mode: 'length', visible: false },
        { key: 'hillslope-aspect', label: 'Aspect (degrees)', path: basePath, mode: 'aspect', visible: false },
      ];

      return { hillslopesSummary, subcatchmentsGeoJson: geoJson, hillslopesLayers };
    }

    const url = buildScenarioUrl(`query/watershed/subcatchments`);
    const geoUrl = buildBaseUrl(`resources/subcatchments.json`);
    const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
    if (!subResp.ok || !geoResp.ok) {
      logDetectionInfo('Hillslopes overlays missing', { subStatus: subResp.status, geoStatus: geoResp.status });
      return null;
    }

    const hillslopesSummary = await subResp.json();
    const geoJson = subcatchmentsGeoJson || (await geoResp.json());
    if (!hillslopesSummary || !geoJson) {
      logDetectionInfo('Hillslopes overlays unavailable (empty payload)', {
        hasSummary: Boolean(hillslopesSummary),
        hasGeoJson: Boolean(geoJson),
      });
      return null;
    }

    const basePath = 'watershed/hillslopes.parquet';
    const hillslopesLayers = [
      { key: 'hillslope-slope', label: 'Slope (rise/run)', path: basePath, mode: 'slope_scalar', visible: false },
      { key: 'hillslope-length', label: 'Hillslope length (m)', path: basePath, mode: 'length', visible: false },
      { key: 'hillslope-aspect', label: 'Aspect (degrees)', path: basePath, mode: 'aspect', visible: false },
    ];

    return { hillslopesSummary, subcatchmentsGeoJson: geoJson, hillslopesLayers };
  } catch (err) {
    logDetectionWarn('failed to load hillslopes overlays', err);
    return null;
  }
}

export async function detectD8DirectionLayer({ fetchGdalInfo, loadRasterFromDownload }) {
  if (typeof fetchGdalInfo !== 'function' || typeof loadRasterFromDownload !== 'function') {
    logDetectionInfo('D8 direction loader missing');
    return null;
  }
  const path = 'dem/wbt/flovec.wgs.tif';
  try {
    const info = await fetchGdalInfo(path);
    if (!info) {
      logDetectionInfo('D8 direction raster missing', { path });
      return null;
    }
    const cellSizeMeters = resolveD8CellSizeMeters(info);
    if (!Number.isFinite(cellSizeMeters)) {
      logDetectionInfo('D8 direction raster missing cell size metadata', { path });
      return null;
    }

    const raster = await loadRasterFromDownload(path);
    if (!raster || !raster.values || !raster.width || !raster.height) {
      logDetectionInfo('D8 direction raster empty', { path });
      return null;
    }

    const bounds = computeBoundsFromGdal(info) || raster.bounds;
    if (!bounds) {
      logDetectionInfo('D8 direction raster missing bounds', { path });
      return null;
    }

    const { data, stride } = buildD8ArrowData({
      values: raster.values,
      width: raster.width,
      height: raster.height,
      bounds,
      nodata: raster.nodata,
      maxArrows: DEFAULT_D8_MAX_ARROWS,
    });
    if (!data.length) {
      logDetectionInfo('D8 direction raster has no arrows', { path });
      return null;
    }

    return {
      d8DirectionLayer: {
        key: 'd8-direction',
        label: 'D8 Direction',
        path,
        visible: false,
        data,
        bounds,
        stride,
        cellSizeMeters,
      },
    };
  } catch (err) {
    logDetectionWarn('failed to load D8 direction layer', err);
    return null;
  }
}

export async function detectChannelsOverlays({ ctx, buildBaseUrl } = {}) {
  try {
    const channelsGeoJson = isBatchContext(ctx)
      ? await ensureBatchGeoJson(ctx, 'channels')
      : await (async () => {
          const geoUrl = buildBaseUrl(`resources/channels.json`);
          const geoResp = await fetch(geoUrl);
          if (!geoResp.ok) {
            logDetectionInfo('Channels overlay missing', { geoUrl, status: geoResp.status });
            return null;
          }
          return geoResp.json();
        })();
    if (!channelsGeoJson || !Array.isArray(channelsGeoJson.features) || !channelsGeoJson.features.length) {
      logDetectionInfo('Channels overlay empty');
      return null;
    }
    const channelLabelsData = buildChannelLabelData(channelsGeoJson);
    return { channelsGeoJson, channelLabelsData };
  } catch (err) {
    logDetectionWarn('failed to load channels overlays', err);
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
    if (!result || !result.records || !result.records.length) {
      logDetectionInfo('WATAR overlays missing or empty', { path: watarPath });
      return null;
    }

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
    logDetectionWarn('failed to load WATAR overlays', err);
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
    if (!weppSummary || !resolvedGeo) {
      logDetectionInfo('WEPP overlays missing summary or geometry', {
        hasSummary: Boolean(weppSummary),
        hasGeoJson: Boolean(resolvedGeo),
      });
      return null;
    }

    const weppRanges = computeRanges(weppSummary, [
      'runoff_volume',
      'subrunoff_volume',
      'baseflow_volume',
      'soil_loss',
      'sediment_deposition',
      'sediment_yield',
    ]);

    const weppLayers = [
      { key: 'wepp-runoff', label: 'Runoff (mm)', path: weppLossPath, mode: 'runoff_volume', visible: false },
      { key: 'wepp-subrunoff', label: 'Subrunoff (mm)', path: weppLossPath, mode: 'subrunoff_volume', visible: false },
      { key: 'wepp-baseflow', label: 'Baseflow (mm)', path: weppLossPath, mode: 'baseflow_volume', visible: false },
      { key: 'wepp-soil-loss', label: 'Soil Loss (t/ha)', path: weppLossPath, mode: 'soil_loss', visible: false },
      { key: 'wepp-sed-dep', label: 'Sediment Deposition (t/ha)', path: weppLossPath, mode: 'sediment_deposition', visible: false },
      { key: 'wepp-sed-yield', label: 'Sediment Yield (t/ha)', path: weppLossPath, mode: 'sediment_yield', visible: false },
    ];

    return { weppSummary, weppRanges, weppLayers, subcatchmentsGeoJson: resolvedGeo };
  } catch (err) {
    logDetectionWarn('failed to load WEPP overlays', err);
    return null;
  }
}

export async function detectWeppChannelOverlays({
  buildBaseUrl,
  fetchWeppChannelSummary,
  weppStatistic,
  weppChannelPath,
  channelsGeoJson,
}) {
  try {
    const [channelSummary, geoJson] = await Promise.all([
      fetchWeppChannelSummary(weppStatistic),
      ensureChannels(buildBaseUrl, channelsGeoJson),
    ]);
    const resolvedGeo = channelsGeoJson || geoJson;
    if (!channelSummary || !resolvedGeo) {
      logDetectionInfo('WEPP channel overlays missing summary or geometry', {
        hasSummary: Boolean(channelSummary),
        hasGeoJson: Boolean(resolvedGeo),
      });
      return null;
    }

    const channelRanges = computeRanges(channelSummary, [
      'channel_discharge_volume',
      'channel_soil_loss',
    ]);

    const weppChannelLayers = [
      {
        key: 'wepp-channel-discharge',
        label: 'Discharge Volume (m^3)',
        path: weppChannelPath,
        mode: 'channel_discharge_volume',
        visible: false,
      },
      {
        key: 'wepp-channel-soil-loss',
        label: 'Soil Loss (kg)',
        path: weppChannelPath,
        mode: 'channel_soil_loss',
        visible: false,
      },
    ];

    return {
      weppChannelSummary: channelSummary,
      weppChannelRanges: channelRanges,
      weppChannelLayers,
      channelsGeoJson: resolvedGeo,
    };
  } catch (err) {
    logDetectionWarn('failed to load WEPP channel overlays', err);
    return null;
  }
}

export async function detectWeppYearlyChannelOverlays({
  buildBaseUrl,
  postQueryEngine,
  weppChannelPath,
  channelsGeoJson,
}) {
  try {
    const yearsPayload = {
      datasets: [{ path: weppChannelPath, alias: 'loss' }],
      columns: ['DISTINCT loss.year AS year'],
      order_by: ['year'],
    };
    const yearsResult = await postQueryEngine(yearsPayload);
    if (!yearsResult || !yearsResult.records || !yearsResult.records.length) {
      logDetectionInfo('WEPP yearly channel overlays missing year list', { path: weppChannelPath });
      return { weppYearlyChannelLayers: [], channelsGeoJson };
    }

    const geoJson = await ensureChannels(buildBaseUrl, channelsGeoJson);
    if (!geoJson) {
      logDetectionInfo('WEPP yearly channel overlays missing channels geometry', { path: weppChannelPath });
      return { weppYearlyChannelLayers: [], channelsGeoJson };
    }

    const weppYearlyChannelLayers = [
      {
        key: 'wepp-yearly-channel-discharge',
        label: 'Discharge Volume (m^3)',
        path: weppChannelPath,
        mode: 'channel_discharge_volume',
        visible: false,
      },
      {
        key: 'wepp-yearly-channel-soil-loss',
        label: 'Soil Loss (kg)',
        path: weppChannelPath,
        mode: 'channel_soil_loss',
        visible: false,
      },
    ];

    return { weppYearlyChannelLayers, channelsGeoJson: geoJson };
  } catch (err) {
    logDetectionWarn('failed to load WEPP yearly channel overlays', err);
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
      logDetectionInfo('WEPP yearly overlays missing year list', { path: weppYearlyPath });
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
      logDetectionInfo('WEPP yearly overlays missing subcatchments', { path: weppYearlyPath });
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
    logDetectionWarn('failed to load WEPP yearly overlays', err);
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
      logDetectionInfo('WEPP Event overlays unavailable: missing climate context', {
        hasClimateCtx: Boolean(climateCtx),
      });
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
      { key: 'wepp-event-saturation', label: 'Saturation (%)', path: 'wepp/output/interchange/H.soil.parquet', mode: 'event_Saturation', visible: false },
      { key: 'wepp-event-peakro', label: 'Peak Runoff Rate', path: 'wepp/output/interchange/H.pass.parquet', mode: 'event_peakro', visible: false },
      { key: 'wepp-event-tdet', label: 'Total Detachment', path: 'wepp/output/interchange/H.pass.parquet', mode: 'event_tdet', visible: false },
    ];

    return { weppEventLayers, weppEventMetadata: metadata, weppEventSelectedDate: selectedDate, subcatchmentsGeoJson: geoJson };
  } catch (err) {
    logDetectionWarn('failed to load WEPP Event overlays', err);
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
    if (!yearsResult || !yearsResult.records || !yearsResult.records.length) {
      logDetectionInfo('RAP overlays missing year list');
      return null;
    }

    const bandsPayload = {
      datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
      columns: ['DISTINCT rap.band AS band'],
      order_by: ['band'],
    };
    const bandsResult = await postQueryEngine(bandsPayload);
    if (!bandsResult || !bandsResult.records || !bandsResult.records.length) {
      logDetectionInfo('RAP overlays missing band list');
      return null;
    }

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
      } else {
        logDetectionInfo('RAP overlays missing data for selected year', { year: rapSelectedYear });
      }
    }

    return { rapLayers, rapMetadata, rapSelectedYear, rapSummary, subcatchmentsGeoJson: geoJson };
  } catch (err) {
    logDetectionWarn('failed to load RAP overlays', err);
    return null;
  }
}
