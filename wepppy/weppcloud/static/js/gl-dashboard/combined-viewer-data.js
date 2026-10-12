/** PCV-01: preserve the legacy average annual measures and native LOSS schema. */
import { buildBatchFeatureKey } from './batch-keys.js';

export const VARIABLES = ['runoff', 'subrunoff', 'baseflow', 'loss', 'phosphorus'];
export const LOSS_PATH = 'wepp/output/interchange/loss_pw0.hill.parquet';
const COLUMNS = {runoff: 'Runoff Volume', subrunoff: 'Subrunoff Volume',
  baseflow: 'Baseflow Volume', loss: 'Soil Loss', phosphorus: 'Total Pollutant'};
export function factor(variable, units) {
  return units === 'SI' ? 1 : (['loss', 'phosphorus'].includes(variable) ? 1.12085 : 25.4);
}
export function unitLabel(variable, units) {
  return ['loss', 'phosphorus'].includes(variable)
    ? (units === 'SI' ? 'kg/ha/yr' : 'lb/acre/yr') : (units === 'SI' ? 'mm/yr' : 'in/yr');
}
export function joinRun(run, geojson, rows) {
  if (!Array.isArray(geojson.features) || !geojson.features.length || !Array.isArray(rows) || !rows.length) {
    throw new Error(`${run.runid}: required geometry or loss rows are empty.`);
  }
  run.phosphorus = Boolean(run.phosphorus) && rows.every((row) => Number.isFinite(row['Total Pollutant']));
  const mapping = Object.values(run.weppIds).map(Number);
  if (new Set(mapping).size !== mapping.length) {
    throw new Error(`${run.runid}: duplicate Topaz to WEPP mapping.`);
  }
  const byId = new Map();
  for (const row of rows) {
    const id = Number(row.wepp_id);
    const area = row['Hillslope Area'];
    if (!Number.isInteger(id) || id <= 0 || byId.has(id) || !Number.isFinite(area) || area <= 0) {
      throw new Error(`${run.runid}: invalid or duplicate hillslope/area in loss output.`);
    }
    const values = {};
    for (const variable of VARIABLES) {
      if (variable === 'phosphorus' && !run.phosphorus) continue;
      const value = row[COLUMNS[variable]];
      if (!Number.isFinite(value)) throw new Error(`${run.runid}: ${variable} is missing for hillslope ${id}.`);
      values[variable] = value / (area * (['loss', 'phosphorus'].includes(variable) ? 1 : 10));
    }
    byId.set(id, values);
  }
  if (mapping.length !== byId.size || mapping.some((id) => !byId.has(id))) {
    throw new Error(`${run.runid}: metadata/loss coverage is incomplete.`);
  }
  const seen = new Set();
  const features = geojson.features.map((feature) => {
    const topazId = feature.properties.TopazID ?? feature.properties.topaz_id;
    const id = Number(run.weppIds[String(topazId)]);
    if (!byId.has(id) || !feature.geometry) {
      throw new Error(`${run.runid}: geometry/loss identifiers do not match.`);
    }
    seen.add(id);
    return {...feature, properties: {...feature.properties, topaz_id: String(topazId),
      runid: run.runid, cfg: run.cfg, key: buildBatchFeatureKey(run.runid, topazId), values: byId.get(id)}};
  });
  if (seen.size !== byId.size) throw new Error(`${run.runid}: geometry/loss coverage is incomplete.`);
  return features;
}
export async function loadRun(run, sitePrefix, fetcher = fetch) {
  const path = `${encodeURIComponent(run.runid)}/${encodeURIComponent(run.cfg)}`;
  const [geo, data] = await Promise.all([
    fetcher(`${sitePrefix}/runs/${path}/resources/subcatchments.json`, {credentials: 'same-origin'}),
    fetcher(`/query-engine/runs/${path}/query`, {method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({datasets: [LOSS_PATH], columns: ['*']})}),
  ]);
  if (!geo.ok || !data.ok) {
    throw new Error(`${run.runid}: results are not ready (geometry ${geo.status}, data ${data.status}). Contact the project maintainer.`);
  }
  return joinRun(run, await geo.json(), (await data.json()).records);
}
export function shareUrl(ctx, view, variable, units, ranges, origin) {
  const url = new URL(`${ctx.sitePrefix}/combined_ws_viewer/`, origin);
  const params = {ws: ctx.ws.map(({runid, cfg}) => ({runid, cfg})),
    center: [view.latitude, view.longitude], zoom: view.zoom, title: ctx.title,
    varname: variable, units, varopts: ranges};
  for (const [key, value] of Object.entries(params)) {
    url.searchParams.set(key, typeof value === 'object' ? JSON.stringify(value) : value);
  }
  return url.href;
}
