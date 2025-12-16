/**
 * Graph data loaders for Omni/RAP/WEPP charts.
 * No DOM/deck usage; consumes Query Engine helpers and returns datasets for the graph renderer.
 */
import { WATER_MEASURES, SOIL_MEASURES } from '../config.js';
import { getState } from '../state.js';

const GRAPH_COLORS = [
  [99, 179, 237],
  [139, 92, 246],
  [16, 185, 129],
  [244, 114, 182],
  [251, 146, 60],
  [94, 234, 212],
  [248, 113, 113],
  [125, 211, 252],
];

const WEPP_YEARLY_COLUMN_MAP = {
  runoff_volume: '"Runoff Volume"',
  subrunoff_volume: '"Subrunoff Volume"',
  baseflow_volume: '"Baseflow Volume"',
  soil_loss: '"Soil Loss"',
  sediment_deposition: '"Sediment Deposition"',
  sediment_yield: '"Sediment Yield"',
};

export function createGraphLoaders(deps) {
  const {
    graphScenarios,
    postQueryEngine,
    postQueryEngineForScenario,
    viridisColor,
    winterColor,
    jet2Color,
    RAP_BAND_LABELS,
  } = deps;

  const state = getState();

  function scenarioColor(idx) {
    const c = GRAPH_COLORS[idx % GRAPH_COLORS.length];
    return [c[0], c[1], c[2], 255];
  }

  function quantile(values, q) {
    if (!values.length) return null;
    const sorted = [...values].sort((a, b) => a - b);
    const pos = (sorted.length - 1) * q;
    const lower = Math.floor(pos);
    const upper = Math.ceil(pos);
    if (lower === upper) return sorted[lower];
    const weight = pos - lower;
    return sorted[lower] * (1 - weight) + sorted[upper] * weight;
  }

  function computeBoxStats(values) {
    const clean = (values || []).filter((v) => Number.isFinite(v));
    if (!clean.length) return null;
    const min = Math.min(...clean);
    const max = Math.max(...clean);
    const q1 = quantile(clean, 0.25);
    const median = quantile(clean, 0.5);
    const q3 = quantile(clean, 0.75);
    return { min, q1, median, q3, max };
  }

  async function loadHillLossScenario(scenarioPath) {
    const key = scenarioPath || '';
    if (state.hillLossCache[key]) return state.hillLossCache[key];
    const payload = {
      datasets: [
        { path: 'wepp/output/interchange/loss_pw0.hill.parquet', alias: 'loss' },
        { path: 'watershed/hillslopes.parquet', alias: 'hill' },
      ],
      joins: [{ left: 'loss', right: 'hill', on: 'wepp_id', type: 'inner' }],
      columns: [
        'loss."Hillslope Area" AS area_ha',
        'loss."Soil Loss" AS soil_loss_kg',
        'loss."Runoff Volume" AS runoff_volume_m3',
        'hill.topaz_id AS topaz_id',
      ],
    };
    try {
      const result = await postQueryEngineForScenario(payload, scenarioPath);
      const rows = [];
      if (result && result.records) {
        for (const row of result.records) {
          rows.push({
            area_ha: Number(row.area_ha),
            soil_loss_kg: Number(row.soil_loss_kg),
            runoff_volume_m3: Number(row.runoff_volume_m3),
          });
        }
      }
      state.hillLossCache[key] = rows;
      const totalArea = rows.reduce(
        (acc, r) => acc + (Number.isFinite(r.area_ha) ? r.area_ha : 0),
        0
      );
      state.hillslopeAreaCache[key] = totalArea;
      return rows;
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load hillslope loss data', err);
      state.hillLossCache[key] = [];
      return [];
    }
  }

  async function loadChannelLossScenario(scenarioPath) {
    const key = scenarioPath || '';
    if (state.channelLossCache[key]) return state.channelLossCache[key];
    const payload = {
      datasets: [
        { path: 'wepp/output/interchange/loss_pw0.chn.parquet', alias: 'loss' },
        { path: 'watershed/channels.parquet', alias: 'chn' },
      ],
      joins: [{ left: 'loss', right: 'chn', on: 'wepp_id', type: 'inner' }],
      columns: ['loss."Soil Loss" AS soil_loss_kg', 'chn.topaz_id AS topaz_id'],
    };
    try {
      const result = await postQueryEngineForScenario(payload, scenarioPath);
      const rows = [];
      if (result && result.records) {
        for (const row of result.records) {
          rows.push({
            soil_loss_kg: Number(row.soil_loss_kg),
          });
        }
      }
      state.channelLossCache[key] = rows;
      return rows;
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load channel loss data', err);
      state.channelLossCache[key] = [];
      return [];
    }
  }

  async function loadOutletScenario(scenarioPath) {
    const key = scenarioPath || '';
    if (state.outletAllYearsCache[key]) return state.outletAllYearsCache[key];
    const payload = {
      datasets: [{ path: 'wepp/output/interchange/loss_pw0.all_years.out.parquet', alias: 'out' }],
      columns: ['out.key AS key', 'out.year AS year', 'out.value AS value'],
      order_by: ['year'],
    };
    try {
      const result = await postQueryEngineForScenario(payload, scenarioPath);
      const map = {};
      if (result && result.records) {
        for (const row of result.records) {
          const keyName = row.key;
          const year = Number(row.year);
          const val = Number(row.value);
          if (!map[keyName]) map[keyName] = {};
          if (Number.isFinite(year)) {
            map[keyName][year] = val;
          }
        }
      }
      state.outletAllYearsCache[key] = map;
      return map;
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load outlet data', err);
      state.outletAllYearsCache[key] = {};
      return {};
    }
  }

  async function getTotalAreaHa(scenarioPath) {
    const key = scenarioPath || '';
    if (state.hillslopeAreaCache[key] != null) return state.hillslopeAreaCache[key];
    await loadHillLossScenario(scenarioPath);
    return state.hillslopeAreaCache[key] || 0;
  }

  function selectOutletKey(outletMap, candidates) {
    const keys = Object.keys(outletMap || {});
    if (!keys.length) return null;
    for (const cand of candidates) {
      const exact = keys.find((k) => k.toLowerCase() === cand.toLowerCase());
      if (exact) return exact;
    }
    for (const cand of candidates) {
      const match = keys.find((k) => k.toLowerCase().includes(cand.toLowerCase()));
      if (match) return match;
    }
    return null;
  }

  async function buildHillSoilLossBoxplot() {
    const series = [];
    for (let i = 0; i < graphScenarios.length; i++) {
      const scenario = graphScenarios[i];
      const rows = await loadHillLossScenario(scenario.path);
      const perArea = rows
        .map((r) => {
          const areaHa = Number(r.area_ha);
          const soilKg = Number(r.soil_loss_kg);
          if (!Number.isFinite(areaHa) || areaHa <= 0 || !Number.isFinite(soilKg)) return null;
          return soilKg / (areaHa * 1000);
        })
        .filter((v) => Number.isFinite(v));
      const stats = computeBoxStats(perArea);
      if (stats) {
        series.push({ label: scenario.name, stats, color: scenarioColor(i) });
      }
    }
    return {
      type: 'boxplot',
      title: 'Soil Loss (hillslopes)',
      yLabel: 'tonne/ha',
      source: 'omni',
      series,
    };
  }

  async function buildHillRunoffBoxplot() {
    const series = [];
    for (let i = 0; i < graphScenarios.length; i++) {
      const scenario = graphScenarios[i];
      const rows = await loadHillLossScenario(scenario.path);
      const perArea = rows
        .map((r) => {
          const areaHa = Number(r.area_ha);
          const runoffM3 = Number(r.runoff_volume_m3);
          if (!Number.isFinite(areaHa) || areaHa <= 0 || !Number.isFinite(runoffM3)) return null;
          return (runoffM3 * 1000) / (areaHa * 10000);
        })
        .filter((v) => Number.isFinite(v));
      const stats = computeBoxStats(perArea);
      if (stats) {
        series.push({ label: scenario.name, stats, color: scenarioColor(i) });
      }
    }
    return {
      type: 'boxplot',
      title: 'Runoff (hillslopes)',
      yLabel: 'mm',
      source: 'omni',
      series,
    };
  }

  async function buildChannelSoilLossBoxplot() {
    const series = [];
    for (let i = 0; i < graphScenarios.length; i++) {
      const scenario = graphScenarios[i];
      const rows = await loadChannelLossScenario(scenario.path);
      const tonnes = rows
        .map((r) => {
          const soilKg = Number(r.soil_loss_kg);
          return Number.isFinite(soilKg) ? soilKg / 1000 : null;
        })
        .filter((v) => Number.isFinite(v));
      const stats = computeBoxStats(tonnes);
      if (stats) {
        series.push({ label: scenario.name, stats, color: scenarioColor(i) });
      }
    }
    return {
      type: 'boxplot',
      title: 'Soil Loss (channels)',
      yLabel: 'tonne',
      source: 'omni',
      series,
    };
  }

  async function buildOutletSedimentBars() {
    const yearsSet = new Set();
    const scenarioData = [];
    for (let i = 0; i < graphScenarios.length; i++) {
      const scenario = graphScenarios[i];
      const outletMap = await loadOutletScenario(scenario.path);
      const keyName = selectOutletKey(outletMap, [
        'total sediment discharge from outlet',
        'sediment discharge from outlet',
        'sediment discharge',
      ]);
      const areaHa = await getTotalAreaHa(scenario.path);
      scenarioData.push({ scenario, outletMap, keyName, areaHa, color: scenarioColor(i) });
      if (keyName && outletMap[keyName]) {
        for (const yr of Object.keys(outletMap[keyName])) {
          const yNum = Number(yr);
          if (Number.isFinite(yNum)) yearsSet.add(yNum);
        }
      }
    }
    const years = Array.from(yearsSet).sort((a, b) => a - b);
    const series = [];
    for (const data of scenarioData) {
      if (!data.keyName || !years.length) continue;
      const values = years.map((yr) => {
        const raw = data.outletMap[data.keyName] ? Number(data.outletMap[data.keyName][yr]) : null;
        if (!Number.isFinite(raw) || !data.areaHa) return null;
        return raw / data.areaHa;
      });
      series.push({ label: data.scenario.name, values, color: data.color });
    }
    const lineSeries = {};
    series.forEach((s) => {
      lineSeries[s.label] = { values: s.values, color: s.color };
    });
    return {
      type: 'line',
      title: 'Sediment discharge (outlet)',
      years,
      series: lineSeries,
      xLabel: 'Year',
      yLabel: 'tonne/ha',
      source: 'omni',
    };
  }

  async function buildOutletStreamBars() {
    const yearsSet = new Set();
    const scenarioData = [];
    for (let i = 0; i < graphScenarios.length; i++) {
      const scenario = graphScenarios[i];
      const outletMap = await loadOutletScenario(scenario.path);
      const keyName = selectOutletKey(outletMap, ['water discharge from outlet', 'stream discharge']);
      const areaHa = await getTotalAreaHa(scenario.path);
      scenarioData.push({ scenario, outletMap, keyName, areaHa, color: scenarioColor(i) });
      if (keyName && outletMap[keyName]) {
        for (const yr of Object.keys(outletMap[keyName])) {
          const yNum = Number(yr);
          if (Number.isFinite(yNum)) yearsSet.add(yNum);
        }
      }
    }
    const years = Array.from(yearsSet).sort((a, b) => a - b);
    const series = [];
    for (const data of scenarioData) {
      if (!data.keyName || !years.length) continue;
      const values = years.map((yr) => {
        const raw = data.outletMap[data.keyName] ? Number(data.outletMap[data.keyName][yr]) : null;
        if (!Number.isFinite(raw) || !data.areaHa) return null;
        return (raw * 1000) / (data.areaHa * 10000);
      });
      series.push({ label: data.scenario.name, values, color: data.color });
    }
    const lineSeries = {};
    series.forEach((s) => {
      lineSeries[s.label] = { values: s.values, color: s.color };
    });
    return {
      type: 'line',
      title: 'Stream discharge (outlet)',
      years,
      series: lineSeries,
      xLabel: 'Year',
      yLabel: 'mm',
      source: 'omni',
    };
  }

  const graphLoadersMap = {
    'omni-soil-loss-hill': buildHillSoilLossBoxplot,
    'omni-soil-loss-chn': buildChannelSoilLossBoxplot,
    'omni-runoff-hill': buildHillRunoffBoxplot,
    'omni-outlet-sediment': buildOutletSedimentBars,
    'omni-outlet-stream': buildOutletStreamBars,
  };

  async function loadGraphDataset(key, { force } = {}) {
    if (!force && state.graphDataCache[key]) {
      return state.graphDataCache[key];
    }
    const loader = graphLoadersMap[key];
    if (!loader) return null;
    const data = await loader();
    state.graphDataCache[key] = data;
    return data;
  }

  function rapBandLabel(selectedBands) {
    if (!selectedBands.length) return '';
    if (selectedBands.length === 1) {
      return RAP_BAND_LABELS[selectedBands[0].bandKey] || selectedBands[0].bandKey;
    }
    return 'Cumulative (' + selectedBands.map((l) => RAP_BAND_LABELS[l.bandKey] || l.bandKey).join('+') + ')';
  }

  async function buildRapTimeseriesData() {
    if (!state.rapCumulativeMode && !state.rapLayers.some((l) => l.visible)) {
      return null;
    }

    const selectedBands = state.rapCumulativeMode
      ? state.rapLayers.filter((l) => l.selected !== false)
      : [state.rapLayers.find((l) => l.visible)].filter(Boolean);

    if (!selectedBands.length) {
      return null;
    }

    try {
      const bandIds = selectedBands.map((l) => l.bandId);
      const dataPayload = {
        datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
        columns: ['rap.topaz_id AS topaz_id', 'rap.year AS year', 'rap.band AS band', 'rap.value AS value'],
        filters: [{ column: 'rap.band', op: 'IN', value: bandIds }],
        order_by: ['year'],
      };
      const dataResult = await postQueryEngine(dataPayload);
      if (!dataResult || !dataResult.records || dataResult.records.length === 0) {
        return null;
      }

      const yearSet = new Set();
      const rawData = {};

      for (const row of dataResult.records) {
        const tid = String(row.topaz_id);
        const year = row.year;
        const value = row.value || 0;
        yearSet.add(year);

        if (!rawData[tid]) {
          rawData[tid] = {};
        }
        rawData[tid][year] = (rawData[tid][year] || 0) + value;
      }

      const years = Array.from(yearSet).sort((a, b) => a - b);
      const series = {};

      let minVal = Infinity;
      let maxVal = -Infinity;
      for (const tid of Object.keys(rawData)) {
        for (const yr of years) {
          const v = rawData[tid][yr];
          if (v != null && isFinite(v)) {
            if (v < minVal) minVal = v;
            if (v > maxVal) maxVal = v;
          }
        }
      }
      if (!isFinite(minVal)) minVal = 0;
      if (!isFinite(maxVal)) maxVal = 100;
      const valRange = maxVal - minVal || 1;

      for (const tid of Object.keys(rawData)) {
        const values = years.map((yr) => rawData[tid][yr] ?? null);
        const latestVal = values.filter((v) => v != null).pop() || 0;
        const normalized = Math.min(1, Math.max(0, (latestVal - minVal) / valRange));
        const color = viridisColor(normalized);
        series[tid] = { values, color };
      }

      const bandLabel = rapBandLabel(selectedBands);

      return {
        years,
        series,
        xLabel: 'Year',
        yLabel: bandLabel + ' %',
        currentYear: state.rapSelectedYear,
        source: 'rap',
        title: bandLabel || 'RAP Timeseries',
        tooltipFormatter: (id, value, yr) => {
          const numeric = Number.isFinite(value) ? value.toFixed(1) : value;
          return `Hillslope ${id}: ${numeric}% (${yr}) — ${bandLabel}`;
        },
      };
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load RAP timeseries', err);
      return null;
    }
  }

  function weppYearlyGraphColor(normalized, mode) {
    if (WATER_MEASURES.includes(mode)) {
      return winterColor(normalized);
    }
    if (SOIL_MEASURES.includes(mode)) {
      return jet2Color(normalized);
    }
    return viridisColor(normalized);
  }

  async function buildWeppYearlyTimeseriesData() {
    const overlay = state.weppYearlyLayers.find((l) => l.visible);
    if (
      !overlay ||
      !state.weppYearlyMetadata ||
      !state.weppYearlyMetadata.years ||
      !state.weppYearlyMetadata.years.length
    ) {
      return null;
    }

    try {
      const valueColumn = WEPP_YEARLY_COLUMN_MAP[overlay.mode] || overlay.mode;
      const dataPayload = {
        datasets: [
          { path: 'wepp/output/interchange/loss_pw0.all_years.hill.parquet', alias: 'loss' },
          { path: 'watershed/hillslopes.parquet', alias: 'hill' },
        ],
        joins: [{ left: 'loss', right: 'hill', on: 'wepp_id', type: 'inner' }],
        columns: ['hill.topaz_id AS topaz_id', 'loss.year AS year', `loss.${valueColumn} AS value`],
        order_by: ['year'],
      };
      const dataResult = await postQueryEngine(dataPayload);
      if (!dataResult || !dataResult.records || dataResult.records.length === 0) {
        return null;
      }

      const yearSet = new Set();
      const rawData = {};
      for (const row of dataResult.records) {
        const tid = String(row.topaz_id);
        const year = row.year;
        const value = row.value;
        if (!Number.isFinite(value)) continue;
        yearSet.add(year);
        if (!rawData[tid]) rawData[tid] = {};
        rawData[tid][year] = value;
      }

      const years = Array.from(yearSet).sort((a, b) => a - b);
      if (!years.length) {
        return null;
      }

      let minVal = Infinity;
      let maxVal = -Infinity;
      for (const tid of Object.keys(rawData)) {
        for (const yr of years) {
          const v = rawData[tid][yr];
          if (v != null && isFinite(v)) {
            if (v < minVal) minVal = v;
            if (v > maxVal) maxVal = v;
          }
        }
      }
      if (!isFinite(minVal)) minVal = 0;
      if (!isFinite(maxVal)) maxVal = 1;
      const range = maxVal - minVal || 1;

      const series = {};
      for (const tid of Object.keys(rawData)) {
        const values = years.map((yr) => (rawData[tid][yr] != null ? rawData[tid][yr] : null));
        const latestVal = values.filter((v) => v != null).pop() || 0;
        const normalized = Math.min(1, Math.max(0, (latestVal - minVal) / range));
        const color = weppYearlyGraphColor(normalized, overlay.mode);
        series[tid] = { values, color };
      }

      const tooltipFormatter = (id, value, yr) => {
        const label = overlay.label || overlay.mode;
        const numeric = Number.isFinite(value) ? value.toFixed(2) : value;
        return `Hillslope ${id}: ${numeric} (${yr}) — ${label}`;
      };

      return {
        years,
        series,
        xLabel: 'Year',
        yLabel: overlay.label || overlay.mode,
        currentYear: state.weppYearlySelectedYear,
        source: 'wepp_yearly',
        tooltipFormatter,
      };
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load WEPP yearly timeseries', err);
      return null;
    }
  }

  return {
    loadGraphDataset,
    buildRapTimeseriesData,
    buildWeppYearlyTimeseriesData,
  };
}
