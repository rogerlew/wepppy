/**
 * Graph data loaders for Omni/RAP/WEPP charts.
 * No DOM/deck usage; consumes Query Engine helpers and returns datasets for the graph renderer.
 *
 * SCENARIO QUERY ARCHITECTURE (REGRESSION GUARD)
 * ==============================================
 * Scenario data is queried via the `scenario` body parameter, NOT URL path manipulation.
 *
 * ✅ CORRECT: Use postQueryEngineForScenario() which adds { scenario: "name" } to request body
 * ❌ WRONG: Appending _pups/omni/scenarios/... to the URL (server will reject with 400)
 *
 * The query-engine's resolve_run_context() accepts a `scenario` parameter that:
 * 1. Resolves the scenario subdirectory: {run_path}/_pups/omni/scenarios/{scenario}/
 * 2. Overlays scenario-specific parquet files over base run data
 * 3. Returns a context with the scenario's catalog
 *
 * The JavaScript helper chain:
 * 1. scenarioPath(scenario) → builds path string like "_pups/omni/scenarios/mulch_30"
 * 2. postQueryEngineForScenario(path, payload) → extracts scenario name, adds to body
 * 3. Server extracts scenario from body, passes to resolve_run_context()
 *
 * If scenario queries return identical data for all scenarios, check:
 * 1. postQueryEngineForScenario() is extracting scenario name correctly
 * 2. Server is extracting and passing scenario parameter to resolve_run_context()
 * 3. The scenario subdirectory exists and contains the expected parquet files
 *
 * See: wepppy/query_engine/README.md "Querying Omni Scenarios"
 */
import { GRAPH_CONTEXT_KEYS, SOIL_MEASURES, WATER_MEASURES } from '../config.js';
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

// Named scenario colors for base scenario types
const NAMED_SCENARIO_COLORS = {
  burned: [239, 68, 68],      // Red (Tailwind red-500)
  undisturbed: [34, 197, 94], // Green (Tailwind green-500)
};

const WEPP_YEARLY_COLUMN_MAP = {
  runoff_volume: '"Runoff Volume"',
  subrunoff_volume: '"Subrunoff Volume"',
  baseflow_volume: '"Baseflow Volume"',
  soil_loss: '"Soil Loss"',
  sediment_deposition: '"Sediment Deposition"',
  sediment_yield: '"Sediment Yield"',
};

const CUMULATIVE_MEASURE_MAP = {
  runoff_volume: { column: 'runoff_volume_m3', label: 'Runoff (m³)', unit: 'm³', soil: false },
  subrunoff_volume: { column: 'subrunoff_volume_m3', label: 'Lateral Flow (m³)', unit: 'm³', soil: false },
  baseflow_volume: { column: 'baseflow_volume_m3', label: 'Baseflow (m³)', unit: 'm³', soil: false },
  soil_loss: { column: 'soil_loss_kg', label: 'Soil Loss (t)', unit: 't', soil: true },
  sediment_deposition: { column: 'sediment_deposition_kg', label: 'Sed Deposition (t)', unit: 't', soil: true },
  sediment_yield: { column: 'sediment_yield_kg', label: 'Sed Yield (t)', unit: 't', soil: true },
};

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

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
  const {
    OMNI,
    CLIMATE_YEARLY,
    RAP,
    WEPP_YEARLY,
  } = GRAPH_CONTEXT_KEYS;

  function scenarioColor(idx, scenarioName = null) {
    // Check for named scenario colors first (case-insensitive)
    if (scenarioName) {
      const lowerName = scenarioName.toLowerCase();
      if (NAMED_SCENARIO_COLORS[lowerName]) {
        const c = NAMED_SCENARIO_COLORS[lowerName];
        return [c[0], c[1], c[2], 255];
      }
    }
    // Use Math.abs to handle negative indices (e.g., when prepending base scenario)
    const safeIdx = Math.abs(idx) % GRAPH_COLORS.length;
    const c = GRAPH_COLORS[safeIdx];
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

  /**
   * Get the filesystem path for querying scenario data.
   *
   * IMPORTANT: This path is NOT appended to the URL. It is passed to
   * postQueryEngineForScenario() which extracts the scenario name and
   * adds it to the request body as { scenario: "name" }.
   *
   * The server's resolve_run_context() uses this to find:
   *   {run_root}/_pups/omni/scenarios/{name}/
   *
   * @param {Object|null} scenario - Scenario object with name or path property
   * @returns {string} Path string like "_pups/omni/scenarios/mulch_30" or empty for base
   *
   * Examples:
   *   scenarioPath(null) → ''
   *   scenarioPath({ name: 'Base' }) → ''
   *   scenarioPath({ name: 'mulch_30_sbs_map' }) → '_pups/omni/scenarios/mulch_30_sbs_map'
   *   scenarioPath({ path: 'custom/path' }) → 'custom/path'
   */
  function scenarioPath(scenario) {
    if (!scenario) return '';
    // Explicit empty path indicates base scenario
    if (scenario.path === '') return '';
    // Explicit non-empty path takes precedence
    if (scenario.path) return scenario.path;
    // Legacy: name-based base scenario detection
    if (!scenario.name || scenario.name === 'Base' || scenario.name === 'base') return '';
    // Construct path from scenario name
    return `_pups/omni/scenarios/${scenario.name}`;
  }

  /**
   * Get unique cache key for scenario.
   */
  function scenarioKey(scenario) {
    const path = scenarioPath(scenario);
    return path || 'base';
  }

  function scenarioDisplayName(scenario) {
    const path = scenarioPath(scenario);
    if (!path) {
      return getState().baseScenarioLabel || 'Base';
    }
    return scenario?.name || scenario?.path || 'Scenario';
  }

  async function loadHillLossScenario(scenPath) {
    const cacheKey = scenPath || 'base';
    if (state.hillLossCache[cacheKey]) {
      console.debug('gl-dashboard: cache hit for', cacheKey);
      return state.hillLossCache[cacheKey];
    }
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
        'loss."Subrunoff Volume" AS subrunoff_volume_m3',
        'loss."Baseflow Volume" AS baseflow_volume_m3',
        'loss."Sediment Deposition" AS sediment_deposition_kg',
        'loss."Sediment Yield" AS sediment_yield_kg',
        'hill.topaz_id AS topaz_id',
      ],
    };
    try {
      console.debug('gl-dashboard: querying scenario', { scenPath, cacheKey });
      const result = await postQueryEngineForScenario(payload, scenPath);
      const rows = [];
      if (result && result.records) {
        for (const row of result.records) {
          rows.push({
            area_ha: Number(row.area_ha),
            soil_loss_kg: Number(row.soil_loss_kg),
            runoff_volume_m3: Number(row.runoff_volume_m3),
            subrunoff_volume_m3: Number(row.subrunoff_volume_m3),
            baseflow_volume_m3: Number(row.baseflow_volume_m3),
            sediment_deposition_kg: Number(row.sediment_deposition_kg),
            sediment_yield_kg: Number(row.sediment_yield_kg),
          });
        }
      }
      // Debug: log summary of loaded data
      if (rows.length) {
        const totalSoilLoss = rows.reduce((sum, r) => sum + (r.soil_loss_kg || 0), 0);
        console.debug('gl-dashboard: loaded', { scenPath, rows: rows.length, totalSoilLoss });
      }
      if (rows.length || cacheKey !== 'base' || !state.hillLossCache[cacheKey]) {
        state.hillLossCache[cacheKey] = rows;
      }
      if (!rows.length && cacheKey === 'base' && Array.isArray(state.hillLossCache[cacheKey]) && state.hillLossCache[cacheKey].length) {
        return state.hillLossCache[cacheKey];
      }
      const totalArea = rows.reduce(
        (acc, r) => acc + (Number.isFinite(r.area_ha) ? r.area_ha : 0),
        0
      );
      state.hillslopeAreaCache[cacheKey] = totalArea;
      return rows;
    } catch (err) {
      console.warn('gl-dashboard: failed to load hillslope loss data', { scenPath, err });
      state.hillLossCache[cacheKey] = [];
      return [];
    }
  }

  async function loadChannelLossScenario(scenPath) {
    const cacheKey = scenPath || 'base';
    if (state.channelLossCache[cacheKey]) return state.channelLossCache[cacheKey];
    const payload = {
      datasets: [
        { path: 'wepp/output/interchange/loss_pw0.chn.parquet', alias: 'loss' },
        { path: 'watershed/channels.parquet', alias: 'chn' },
      ],
      joins: [{ left: 'loss', right: 'chn', on: 'wepp_id', type: 'inner' }],
      columns: ['loss."Soil Loss" AS soil_loss_kg', 'chn.topaz_id AS topaz_id'],
    };
    try {
      const result = await postQueryEngineForScenario(payload, scenPath);
      const rows = [];
      if (result && result.records) {
        for (const row of result.records) {
          rows.push({
            soil_loss_kg: Number(row.soil_loss_kg),
          });
        }
      }
      if (rows.length || cacheKey !== 'base' || !state.channelLossCache[cacheKey]) {
        state.channelLossCache[cacheKey] = rows;
      }
      if (!rows.length && cacheKey === 'base' && Array.isArray(state.channelLossCache[cacheKey]) && state.channelLossCache[cacheKey].length) {
        return state.channelLossCache[cacheKey];
      }
      return rows;
    } catch (err) {
      console.warn('gl-dashboard: failed to load channel loss data', err);
      state.channelLossCache[cacheKey] = [];
      return [];
    }
  }

  async function loadOutletScenario(scenPath) {
    const cacheKey = scenPath || 'base';
    if (state.outletAllYearsCache[cacheKey]) return state.outletAllYearsCache[cacheKey];
    const payload = {
      datasets: [{ path: 'wepp/output/interchange/loss_pw0.all_years.out.parquet', alias: 'out' }],
      columns: ['out.key AS key', 'out.year AS year', 'out.value AS value'],
      order_by: ['year'],
    };
    try {
      const result = await postQueryEngineForScenario(payload, scenPath);
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
      if (Object.keys(map).length || cacheKey !== 'base' || !state.outletAllYearsCache[cacheKey]) {
        state.outletAllYearsCache[cacheKey] = map;
      }
      if (!Object.keys(map).length && cacheKey === 'base' && state.outletAllYearsCache[cacheKey]) {
        return state.outletAllYearsCache[cacheKey];
      }
      return map;
    } catch (err) {
      console.warn('gl-dashboard: failed to load outlet data', err);
      state.outletAllYearsCache[cacheKey] = {};
      return {};
    }
  }

  async function getTotalAreaHa(scenPath) {
    const cacheKey = scenPath || 'base';
    if (state.hillslopeAreaCache[cacheKey] != null) return state.hillslopeAreaCache[cacheKey];
    await loadHillLossScenario(scenPath);
    return state.hillslopeAreaCache[cacheKey] || 0;
  }

  function normalizeCumulativeValue(raw, measureKey) {
    const def = CUMULATIVE_MEASURE_MAP[measureKey];
    if (!def) return null;
    const val = Number(raw);
    if (!Number.isFinite(val)) return null;
    if (def.soil) {
      return val / 1000; // kg → tonne
    }
    return val;
  }

  function climatePrecipColor(idx) {
    const base = [236, 72, 153];
    const fade = 0.4 + 0.6 * ((idx % 6) / 5);
    return [Math.round(base[0] * fade), Math.round(base[1] * fade), Math.round(base[2] * fade), 255];
  }

  function climateTempColors(idx) {
    const fade = 0.45 + 0.55 * ((idx % 6) / 5);
    const tmin = [59, 130, 246];
    const tmax = [239, 68, 68];
    const scale = (c) => Math.round(c * fade);
    return {
      tmin: [scale(tmin[0]), scale(tmin[1]), scale(tmin[2]), 255],
      tmax: [scale(tmax[0]), scale(tmax[1]), scale(tmax[2]), 255],
    };
  }

  function clampPercent(val) {
    if (!Number.isFinite(val)) return 0;
    const pct = Math.max(0, Math.min(100, val));
    return Math.round(pct * 1e6) / 1e6;
  }

  function buildPercentAxis(step = 0.5) {
    const axis = [];
    const clampedStep = step > 0 ? step : 0.5;
    for (let p = 0; p <= 100 + 1e-9; p += clampedStep) {
      axis.push(clampPercent(Math.min(p, 100)));
    }
    if (axis[axis.length - 1] !== 100) {
      axis.push(100);
    }
    return axis;
  }

  function alignSeriesToAxis(percents, values, axis) {
    if (!percents.length || percents.length !== values.length) return [];
    const aligned = [];
    const n = percents.length;
    for (const pct of axis) {
      if (pct <= percents[0]) {
        aligned.push(values[0]);
        continue;
      }
      if (pct >= percents[n - 1]) {
        aligned.push(values[n - 1]);
        continue;
      }
      let idx = 0;
      while (idx < n - 1 && percents[idx + 1] < pct) {
        idx += 1;
      }
      const p0 = percents[idx];
      const p1 = percents[idx + 1];
      const v0 = values[idx];
      const v1 = values[idx + 1];
      const span = p1 - p0 || 1;
      const t = Math.max(0, Math.min(1, (pct - p0) / span));
      aligned.push(v0 + t * (v1 - v0));
    }
    return aligned;
  }

  function computeCumulativeSeries(rows, measureKey) {
    const def = CUMULATIVE_MEASURE_MAP[measureKey];
    if (!def) return null;
    const valid = [];
    let totalArea = 0;
    for (const row of rows) {
      const areaHa = Number(row.area_ha);
      const rawVal = normalizeCumulativeValue(row[def.column], measureKey);
      if (!Number.isFinite(areaHa) || areaHa <= 0 || !Number.isFinite(rawVal)) continue;
      valid.push({
        areaHa,
        value: rawVal,
        perArea: rawVal / areaHa,
      });
      totalArea += areaHa;
    }
    if (!valid.length || totalArea <= 0) return null;
    valid.sort((a, b) => b.perArea - a.perArea);

    let cumulativeArea = 0;
    let cumulativeValue = 0;
    const percents = [0];
    const values = [0];
    for (const entry of valid) {
      cumulativeArea += entry.areaHa;
      cumulativeValue += entry.value;
      percents.push(clampPercent((cumulativeArea / totalArea) * 100));
      values.push(cumulativeValue);
    }
    if (percents[percents.length - 1] < 100) {
      percents.push(100);
      values.push(cumulativeValue);
    }
    return { percents, values };
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

  async function buildCumulativeContributionGraph(options = {}) {
    const measureKey = CUMULATIVE_MEASURE_MAP[options.measureKey] ? options.measureKey : 'runoff_volume';
    const measureDef = CUMULATIVE_MEASURE_MAP[measureKey];
    const selectedScenarioPaths = Array.isArray(options.scenarioPaths) ? options.scenarioPaths : [];
    
    console.debug('gl-dashboard: buildCumulativeContributionGraph input', {
      measureKey,
      selectedScenarioPaths,
      graphScenariosCount: graphScenarios.length,
      graphScenarios: graphScenarios.map((s) => ({ name: s.name, path: s.path })),
    });
    
    // Build set of selected scenario keys
    const scenarioSet = new Set(['base']); // Always include base
    selectedScenarioPaths.forEach((p) => {
      if (p != null && p !== '' && p !== 'base') scenarioSet.add(p);
    });

    // Ensure base is always included when rendering
    if (!scenarioSet.has('base')) {
      scenarioSet.add('base');
    }
    
    // Filter and process scenarios
    const scenarios = [];
    for (let i = 0; i < graphScenarios.length; i++) {
      const s = graphScenarios[i];
      const key = scenarioKey(s);
      const path = scenarioPath(s);
      console.debug('gl-dashboard: checking scenario', { i, name: s.name, key, path, inSet: scenarioSet.has(key) });
      if (scenarioSet.has(key)) {
        scenarios.push({ scenario: s, originalIndex: i, key, path });
      }
    }
    
    if (!scenarios.length) {
      scenarios.push({ scenario: { name: scenarioDisplayName({}), path: '' }, originalIndex: 0, key: 'base', path: '' });
    } else if (!scenarios.some((s) => s.key === 'base')) {
      // Prepend base so it stays visible even when other scenarios are selected
      // Use originalIndex: 0 to ensure base uses the first color in the palette
      scenarios.unshift({ scenario: { name: scenarioDisplayName({}), path: '' }, originalIndex: 0, key: 'base', path: '' });
    }

    const percentAxis = buildPercentAxis(0.5);
    const seriesEntries = [];

    for (const { scenario, originalIndex, key, path } of scenarios) {
      console.debug('gl-dashboard: loading scenario data', { name: scenario.name, key, path });
      const rows = await loadHillLossScenario(path);
      const cumulative = computeCumulativeSeries(rows, measureKey);
      if (!cumulative) {
        console.debug('gl-dashboard: no cumulative data', { name: scenario.name });
        continue;
      }
      const finalValue = cumulative.values[cumulative.values.length - 1];
      console.debug('gl-dashboard: scenario cumulative', { name: scenario.name, finalValue, points: cumulative.values.length });
      seriesEntries.push({
        id: key,
        label: scenarioDisplayName(scenario),
        percents: cumulative.percents,
        values: cumulative.values,
        color: scenarioColor(originalIndex, scenario.name),
      });
    }

    if (!seriesEntries.length) {
      return null;
    }

    const series = {};
    seriesEntries.forEach((entry) => {
      series[entry.id] = {
        label: entry.label,
        values: alignSeriesToAxis(entry.percents, entry.values, percentAxis),
        color: entry.color,
      };
    });

    const tooltipFormatter = (id, value, pct) => {
      const item = series[id];
      const label = (item && item.label) || id || 'Scenario';
      const numericVal = Number.isFinite(value)
        ? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
        : value;
      const pctVal = Number.isFinite(pct) ? pct.toFixed(1) : pct;
      return `${label}: ${numericVal} ${measureDef.unit} @ ${pctVal}% area`;
    };

    return {
      type: 'line',
      title: `Cumulative Contribution — ${measureDef.label}`,
      years: percentAxis,
      series,
      xLabel: 'Percent of Total Hillslope Area',
      yLabel: measureDef.label,
      source: OMNI,
      tooltipFormatter,
    };
  }

  async function buildClimateYearlyGraph(options = {}) {
    const waterYear = options.waterYear !== undefined ? options.waterYear : state.climateWaterYear;
    const startMonthRaw = options.startMonth || state.climateStartMonth || 10;
    const startMonth = waterYear ? Math.min(12, Math.max(1, startMonthRaw)) : 1;
    const monthLabels = [];
    for (let i = 0; i < 12; i++) {
      const idx = (startMonth - 1 + i) % 12;
      monthLabels.push(MONTH_LABELS[idx]);
    }

    const payload = {
      datasets: [{ path: 'climate/wepp_cli.parquet', alias: 'cli' }],
      columns: [
        'cli.year AS year',
        'COALESCE(cli.month, cli.mo) AS month',
        'cli.prcp AS prcp',
        'cli.tmin AS tmin',
        'cli.tmax AS tmax',
      ],
      order_by: ['year', 'month'],
    };

    try {
      const result = await postQueryEngine(payload);
      if (!result || !Array.isArray(result.records) || !result.records.length) {
        return null;
      }

      const byYear = {};
      for (const row of result.records) {
        const year = Number(row.year);
        const month = Number(row.month);
        if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) continue;
        const targetYear = waterYear
          ? month >= startMonth
            ? year + 1
            : year
          : year;
        const monthIdx = waterYear ? (month - startMonth + 12) % 12 : month - 1;
        const prcp = Number(row.prcp);
        const tmin = Number(row.tmin);
        const tmax = Number(row.tmax);
        if (!byYear[targetYear]) {
          byYear[targetYear] = {
            precip: Array(12).fill(0),
            tminSum: Array(12).fill(0),
            tmaxSum: Array(12).fill(0),
            counts: Array(12).fill(0),
          };
        }
        if (Number.isFinite(prcp)) {
          byYear[targetYear].precip[monthIdx] += prcp;
        }
        if (Number.isFinite(tmin)) {
          byYear[targetYear].tminSum[monthIdx] += tmin;
        }
        if (Number.isFinite(tmax)) {
          byYear[targetYear].tmaxSum[monthIdx] += tmax;
        }
        byYear[targetYear].counts[monthIdx] += 1;
      }

      const years = Object.keys(byYear)
        .map((y) => Number(y))
        .filter(Number.isFinite)
        .sort((a, b) => a - b);
      if (!years.length) return null;

      const precipSeries = {};
      const tempSeries = {};
      years.forEach((yr, idx) => {
        const data = byYear[yr];
        const monthly = [];
        for (let i = 0; i < 12; i++) {
          monthly.push(data.precip[i] || 0);
        }
        const counts = data.counts;
        const tminAvg = data.tminSum.map((sum, i) => {
          const c = counts[i];
          return c > 0 ? sum / c : null;
        });
        const tmaxAvg = data.tmaxSum.map((sum, i) => {
          const c = counts[i];
          return c > 0 ? sum / c : null;
        });
        precipSeries[yr] = { values: monthly, color: climatePrecipColor(idx) };
        const tempColors = climateTempColors(idx);
        tempSeries[yr] = { tmin: tminAvg, tmax: tmaxAvg, colors: tempColors };
      });

      const selectedYear =
        state.climateYearlySelectedYear && years.includes(state.climateYearlySelectedYear)
          ? state.climateYearlySelectedYear
          : years[years.length - 1];
      state.climateYearlySelectedYear = selectedYear;

      return {
        type: 'climate-yearly',
        title: 'Climate Yearly',
        months: monthLabels,
        years,
        precipSeries,
        tempSeries,
        selectedYear,
        xLabel: 'Month',
        yLabel: 'Climate',
        source: CLIMATE_YEARLY,
        currentYear: selectedYear,
        waterYear,
        startMonth,
      };
    } catch (err) {
      console.warn('gl-dashboard: failed to load climate yearly data', err);
      return null;
    }
  }

  async function buildHillSoilLossBoxplot() {
    const series = [];
    // Always include base first for clarity
    const scenarios = [{ ...graphScenarios[0], _base: true }].concat(graphScenarios.slice(1));
    for (let i = 0; i < scenarios.length; i++) {
      const scenario = scenarios[i];
      const path = scenarioPath(scenario);
      const rows = await loadHillLossScenario(path);
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
        series.push({ label: scenarioDisplayName(scenario), stats, color: scenarioColor(i, scenario.name) });
      }
    }
    return {
      type: 'boxplot',
      title: 'Soil Loss (hillslopes)',
      yLabel: 'tonne/ha',
      source: OMNI,
      series,
      defaultLogScale: true,
    };
  }

  async function buildHillRunoffBoxplot() {
    const series = [];
    const scenarios = [{ ...graphScenarios[0], _base: true }].concat(graphScenarios.slice(1));
    for (let i = 0; i < scenarios.length; i++) {
      const scenario = scenarios[i];
      const path = scenarioPath(scenario);
      const rows = await loadHillLossScenario(path);
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
        series.push({ label: scenarioDisplayName(scenario), stats, color: scenarioColor(i, scenario.name) });
      }
    }
    return {
      type: 'boxplot',
      title: 'Runoff (hillslopes)',
      yLabel: 'mm',
      source: OMNI,
      series,
      defaultLogScale: false,
    };
  }

  async function buildChannelSoilLossBoxplot() {
    const series = [];
    const scenarios = [{ ...graphScenarios[0], _base: true }].concat(graphScenarios.slice(1));
    for (let i = 0; i < scenarios.length; i++) {
      const scenario = scenarios[i];
      const path = scenarioPath(scenario);
      const rows = await loadChannelLossScenario(path);
      const tonnes = rows
        .map((r) => {
          const soilKg = Number(r.soil_loss_kg);
          return Number.isFinite(soilKg) ? soilKg / 1000 : null;
        })
        .filter((v) => Number.isFinite(v));
      const stats = computeBoxStats(tonnes);
      if (stats) {
        series.push({ label: scenarioDisplayName(scenario), stats, color: scenarioColor(i, scenario.name) });
      }
    }
    return {
      type: 'boxplot',
      title: 'Soil Loss (channels)',
      yLabel: 'tonne',
      source: OMNI,
      series,
      defaultLogScale: true,
    };
  }

  async function buildOutletSedimentBars() {
    const yearsSet = new Set();
    const scenarioData = [];
    const scenarios = [{ ...graphScenarios[0], _base: true }].concat(graphScenarios.slice(1));
    for (let i = 0; i < scenarios.length; i++) {
      const scenario = scenarios[i];
      const path = scenarioPath(scenario);
      const outletMap = await loadOutletScenario(path);
      const keyName = selectOutletKey(outletMap, [
        'total sediment discharge from outlet',
        'sediment discharge from outlet',
        'sediment discharge',
      ]);
      const areaHa = await getTotalAreaHa(path);
      scenarioData.push({ scenario, outletMap, keyName, areaHa, color: scenarioColor(i, scenario.name) });
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
      series.push({ label: scenarioDisplayName(data.scenario), values, color: data.color });
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
      source: OMNI,
    };
  }

  async function buildOutletStreamBars() {
    const yearsSet = new Set();
    const scenarioData = [];
    const scenarios = [{ ...graphScenarios[0], _base: true }].concat(graphScenarios.slice(1));
    for (let i = 0; i < scenarios.length; i++) {
      const scenario = scenarios[i];
      const path = scenarioPath(scenario);
      const outletMap = await loadOutletScenario(path);
      const keyName = selectOutletKey(outletMap, ['water discharge from outlet', 'stream discharge']);
      const areaHa = await getTotalAreaHa(path);
      scenarioData.push({ scenario, outletMap, keyName, areaHa, color: scenarioColor(i, scenario.name) });
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
      series.push({ label: scenarioDisplayName(data.scenario), values, color: data.color });
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
      source: OMNI,
    };
  }

  const graphLoadersMap = {
    'climate-yearly': buildClimateYearlyGraph,
    'cumulative-contribution': buildCumulativeContributionGraph,
    'omni-soil-loss-hill': buildHillSoilLossBoxplot,
    'omni-soil-loss-chn': buildChannelSoilLossBoxplot,
    'omni-runoff-hill': buildHillRunoffBoxplot,
    'omni-outlet-sediment': buildOutletSedimentBars,
    'omni-outlet-stream': buildOutletStreamBars,
  };

  function graphCacheKey(key, options) {
    if (key === 'cumulative-contribution') {
      const measureKey = options && options.measureKey ? options.measureKey : state.cumulativeMeasure || 'runoff_volume';
      const scenarioKeys = options && Array.isArray(options.scenarioPaths)
        ? options.scenarioPaths.slice().sort().join('|')
        : (state.cumulativeScenarioSelections || []).slice().sort().join('|');
      return `${key}:${measureKey}:${scenarioKeys}`;
    }
    if (key === 'climate-yearly') {
      const water = options && options.waterYear !== undefined ? options.waterYear : state.climateWaterYear;
      const start = options && options.startMonth ? options.startMonth : state.climateStartMonth || 10;
      return `${key}:${water ? 'wy' : 'cy'}:${start}`;
    }
    return key;
  }

  async function loadGraphDataset(key, { force, options } = {}) {
    const cacheKey = graphCacheKey(key, options);
    if (!force && state.graphDataCache[cacheKey]) {
      return state.graphDataCache[cacheKey];
    }
    const loader = graphLoadersMap[key];
    if (!loader) return null;
    const data = await loader(options || {});
    state.graphDataCache[cacheKey] = data;
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
      source: RAP,
      title: bandLabel || 'RAP Timeseries',
        tooltipFormatter: (id, value, yr) => {
          const numeric = Number.isFinite(value) ? value.toFixed(1) : value;
          return `Hillslope ${id}: ${numeric}% (${yr}) — ${bandLabel}`;
        },
      };
    } catch (err) {
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
        columns: ['hill.topaz_id AS topaz_id', 'loss.year AS year', `loss.${valueColumn} AS value`, 'hill.area AS area'],
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
        let value = row.value;
        const area = row.area;
        if (!Number.isFinite(value) || !Number.isFinite(area) || area <= 0) continue;
        
        // Convert units: water measures to mm, soil measures to t/ha
        // Area is in m², raw water values are in m³, raw soil values are in kg
        if (WATER_MEASURES.includes(overlay.mode)) {
          value = (value / area) * 1000; // m³/m² * 1000 = mm
        } else if (SOIL_MEASURES.includes(overlay.mode)) {
          value = (value / area) * 10; // kg/m² * 10 = t/ha
        }
        
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
        source: WEPP_YEARLY,
        tooltipFormatter,
      };
    } catch (err) {
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
