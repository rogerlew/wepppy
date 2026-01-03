const CLIMATE_PATH = 'climate/wepp_cli.parquet';
const SOIL_PATH = 'wepp/output/interchange/H.soil.parquet';
const WATER_PATH = 'wepp/output/interchange/H.wat.parquet';
const OUTLET_PATH = 'wepp/output/interchange/ebe_pw0.parquet';
const HILL_EVENTS_PATH = 'wepp/output/interchange/H.ebe.parquet';
const HILLSLOPE_PATH = 'watershed/hillslopes.parquet';
const TC_PATH = 'wepp/output/interchange/tc_out.parquet';

const INTENSITY_COLUMN_BY_MINUTES = {
  10: 'peak_intensity_10',
  15: 'peak_intensity_15',
  30: 'peak_intensity_30',
  60: 'peak_intensity_60',
};

const warmupYearCache = new Map();
const warmupYearPromiseCache = new Map();

function pad2(value) {
  return String(value).padStart(2, '0');
}

function formatDate(year, month, day) {
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) {
    return '';
  }
  return `${year}-${pad2(month)}-${pad2(day)}`;
}

function toNumberOrNull(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

export function getIntensityColumn(durationMinutes) {
  return INTENSITY_COLUMN_BY_MINUTES[Number(durationMinutes)] || null;
}

function resolveFilterSpec(selectedMetric) {
  const metricKey = selectedMetric && selectedMetric.metricKey ? selectedMetric.metricKey : 'intensity';
  if (metricKey === 'depth') {
    return { metricKey, filterColumn: 'prcp' };
  }
  if (metricKey === 'duration') {
    return { metricKey, filterColumn: 'dur' };
  }
  const intensityColumn = getIntensityColumn(selectedMetric.durationMinutes);
  if (!intensityColumn) {
    throw new Error('Unsupported intensity duration for event filtering.');
  }
  return { metricKey, filterColumn: intensityColumn, intensityColumn };
}

export function computeIntensityRange(value, pct) {
  const numeric = Number(value);
  const percent = Number(pct);
  if (!Number.isFinite(numeric) || !Number.isFinite(percent)) {
    return null;
  }
  const delta = numeric * (percent / 100);
  const minValue = numeric - delta;
  const maxValue = numeric + delta;
  return {
    minValue: Math.min(minValue, maxValue),
    maxValue: Math.max(minValue, maxValue),
  };
}

function buildWarmupFilter(warmupYear, alias = 'ev') {
  if (!Number.isFinite(warmupYear)) {
    return [];
  }
  return [
    {
      column: `${alias}.year`,
      operator: '>',
      value: warmupYear,
    },
  ];
}

export function buildEventFilterPayload({ filterColumn, minValue, maxValue, warmupYear }) {
  return {
    datasets: [{ path: CLIMATE_PATH, alias: 'ev' }],
    columns: [
      'ev.sim_day_index AS sim_day_index',
      'ev.year AS year',
      'ev.month AS month',
      'ev.day_of_month AS day_of_month',
      'ev.prcp AS depth_mm',
      'ev.prcp AS precip_mm',
      'ev.dur AS duration_hours',
      'ev.tp AS tp',
      'ev.ip AS ip',
      'ev.peak_intensity_10 AS peak_intensity_10',
      'ev.peak_intensity_15 AS peak_intensity_15',
      'ev.peak_intensity_30 AS peak_intensity_30',
      'ev.peak_intensity_60 AS peak_intensity_60',
    ],
    filters: [
      {
        column: `ev.${filterColumn}`,
        operator: '>=',
        value: minValue,
      },
      {
        column: `ev.${filterColumn}`,
        operator: '<=',
        value: maxValue,
      },
      ...buildWarmupFilter(warmupYear),
    ],
    order_by: [filterColumn, 'sim_day_index'],
  };
}

export function buildSoilPayload({ filterColumn, minValue, maxValue, warmupYear }) {
  return {
    datasets: [
      { path: CLIMATE_PATH, alias: 'ev' },
      { path: SOIL_PATH, alias: 'soil' },
    ],
    joins: [
      {
        left: 'ev',
        right: 'soil',
        left_on: ['ev.sim_day_index - 1'],
        right_on: ['sim_day_index'],
        type: 'left',
      },
    ],
    columns: [
      'ev.sim_day_index AS sim_day_index',
      'ev.year AS year',
      'ev.month AS month',
      'ev.day_of_month AS day_of_month',
    ],
    aggregations: [
      {
        sql: 'AVG(soil.Saturation) * 100',
        alias: 'soil_saturation_pct',
      },
    ],
    filters: [
      {
        column: `ev.${filterColumn}`,
        operator: '>=',
        value: minValue,
      },
      {
        column: `ev.${filterColumn}`,
        operator: '<=',
        value: maxValue,
      },
      ...buildWarmupFilter(warmupYear),
    ],
    group_by: ['ev.sim_day_index', 'ev.year', 'ev.month', 'ev.day_of_month'],
    order_by: ['ev.sim_day_index'],
  };
}

export function buildSnowPayload({ filterColumn, minValue, maxValue, warmupYear }) {
  const coverageExpr =
    'SUM(CASE WHEN wat."Snow-Water" > 0 THEN wat.Area ELSE 0 END) / NULLIF(SUM(wat.Area), 0) * 100.0';
  return {
    datasets: [
      { path: CLIMATE_PATH, alias: 'ev' },
      { path: WATER_PATH, alias: 'wat' },
    ],
    joins: [
      {
        left: 'ev',
        right: 'wat',
        left_on: ['ev.sim_day_index - 1'],
        right_on: ['sim_day_index'],
        type: 'left',
      },
    ],
    columns: [
      'ev.sim_day_index AS sim_day_index',
      'ev.year AS year',
      'ev.month AS month',
      'ev.day_of_month AS day_of_month',
    ],
    aggregations: [
      {
        sql: coverageExpr,
        alias: 'snow_coverage_t1_pct',
      },
    ],
    filters: [
      {
        column: `ev.${filterColumn}`,
        operator: '>=',
        value: minValue,
      },
      {
        column: `ev.${filterColumn}`,
        operator: '<=',
        value: maxValue,
      },
      ...buildWarmupFilter(warmupYear),
    ],
    group_by: ['ev.sim_day_index', 'ev.year', 'ev.month', 'ev.day_of_month'],
    order_by: ['ev.sim_day_index'],
  };
}

export function buildHydrologyPayload({ filterColumn, minValue, maxValue, warmupYear }) {
  return {
    datasets: [
      { path: CLIMATE_PATH, alias: 'ev' },
      { path: OUTLET_PATH, alias: 'out' },
    ],
    joins: [
      {
        left: 'ev',
        right: 'out',
        left_on: ['ev.sim_day_index'],
        right_on: ['sim_day_index'],
        type: 'left',
      },
    ],
    columns: [
      'ev.sim_day_index AS sim_day_index',
      'ev.year AS year',
      'ev.month AS month',
      'ev.day_of_month AS day_of_month',
    ],
    aggregations: [
      {
        sql: 'MAX(out.runoff_volume)',
        alias: 'runoff_volume_m3',
      },
      {
        sql: 'MAX(out.peak_runoff)',
        alias: 'peak_discharge_m3s',
      },
      {
        sql: 'MAX(out.sediment_yield)',
        alias: 'sediment_yield_kg',
      },
    ],
    filters: [
      {
        column: `ev.${filterColumn}`,
        operator: '>=',
        value: minValue,
      },
      {
        column: `ev.${filterColumn}`,
        operator: '<=',
        value: maxValue,
      },
      ...buildWarmupFilter(warmupYear),
    ],
    group_by: ['ev.sim_day_index', 'ev.year', 'ev.month', 'ev.day_of_month'],
    order_by: ['ev.sim_day_index'],
  };
}

export function buildPrecipVolumePayload({ filterColumn, minValue, maxValue, warmupYear }) {
  return {
    datasets: [
      { path: CLIMATE_PATH, alias: 'ev' },
      { path: HILL_EVENTS_PATH, alias: 'hebe' },
      { path: HILLSLOPE_PATH, alias: 'hill' },
    ],
    joins: [
      {
        left: 'ev',
        right: 'hebe',
        left_on: ['ev.sim_day_index'],
        right_on: ['sim_day_index'],
        type: 'left',
      },
      {
        left: 'hebe',
        right: 'hill',
        left_on: ['wepp_id'],
        right_on: ['wepp_id'],
        type: 'left',
      },
    ],
    columns: [
      'ev.sim_day_index AS sim_day_index',
      'ev.year AS year',
      'ev.month AS month',
      'ev.day_of_month AS day_of_month',
    ],
    aggregations: [
      {
        sql: 'SUM(hebe.Precip * hill.area / 1000.0)',
        alias: 'precip_volume_m3',
      },
      {
        sql: 'SUM(hill.area)',
        alias: 'total_area_m2',
      },
    ],
    filters: [
      {
        column: `ev.${filterColumn}`,
        operator: '>=',
        value: minValue,
      },
      {
        column: `ev.${filterColumn}`,
        operator: '<=',
        value: maxValue,
      },
      ...buildWarmupFilter(warmupYear),
    ],
    group_by: ['ev.sim_day_index', 'ev.year', 'ev.month', 'ev.day_of_month'],
    order_by: ['ev.sim_day_index'],
  };
}

export function buildTcPayloadBySimDay({ warmupYear }) {
  return {
    datasets: [
      { path: CLIMATE_PATH, alias: 'ev' },
      { path: TC_PATH, alias: 'tc' },
    ],
    joins: [
      {
        left: 'ev',
        right: 'tc',
        left_on: ['ev.sim_day_index'],
        right_on: ['sim_day_index'],
        type: 'left',
      },
    ],
    columns: [
      'ev.sim_day_index AS sim_day_index',
      'ev.year AS year',
      'ev.month AS month',
      'ev.day_of_month AS day_of_month',
      'tc."Time of Conc (hr)" AS tc_hours',
    ],
    filters: [...buildWarmupFilter(warmupYear)],
    order_by: ['ev.sim_day_index'],
  };
}

export function buildTcPayloadByJulian({ warmupYear }) {
  return {
    datasets: [
      { path: CLIMATE_PATH, alias: 'ev' },
      { path: TC_PATH, alias: 'tc' },
    ],
    joins: [
      {
        left: 'ev',
        right: 'tc',
        left_on: ['ev.year', 'ev.julian'],
        right_on: ['year', 'day'],
        type: 'left',
      },
    ],
    columns: [
      'ev.sim_day_index AS sim_day_index',
      'ev.year AS year',
      'ev.month AS month',
      'ev.day_of_month AS day_of_month',
      'tc."Time of Conc (hr)" AS tc_hours',
    ],
    filters: [...buildWarmupFilter(warmupYear)],
    order_by: ['ev.sim_day_index'],
  };
}

async function fetchWarmupYear({ postQueryEngine, runid }) {
  if (!runid) {
    return null;
  }
  if (warmupYearCache.has(runid)) {
    return warmupYearCache.get(runid);
  }
  if (warmupYearPromiseCache.has(runid)) {
    return warmupYearPromiseCache.get(runid);
  }

  const payload = {
    datasets: [{ path: CLIMATE_PATH, alias: 'ev' }],
    aggregations: [{ sql: 'MIN(ev.year)', alias: 'min_year' }],
  };

  const promise = postQueryEngine(payload)
    .then((result) => {
      const record = result && Array.isArray(result.records) ? result.records[0] : null;
      const value = record ? Number(record.min_year) : null;
      if (Number.isFinite(value)) {
        warmupYearCache.set(runid, value);
      }
      return Number.isFinite(value) ? value : null;
    })
    .catch((error) => {
      warmupYearPromiseCache.delete(runid);
      throw error;
    });

  warmupYearPromiseCache.set(runid, promise);
  return promise;
}

function mapBySimDay(records, key) {
  const map = new Map();
  (records || []).forEach((row) => {
    const simDay = toNumberOrNull(row.sim_day_index);
    if (!Number.isFinite(simDay)) {
      return;
    }
    map.set(simDay, row[key]);
  });
  return map;
}

function mapRowsBySimDay(records) {
  const map = new Map();
  (records || []).forEach((row) => {
    const simDay = toNumberOrNull(row.sim_day_index);
    if (!Number.isFinite(simDay)) {
      return;
    }
    map.set(simDay, row);
  });
  return map;
}

export function createEventDataManager({ ctx, postQueryEngine }) {
  async function safeQuery(payload, label) {
    try {
      return await postQueryEngine(payload);
    } catch (error) {
      console.warn(`Storm Event Analyzer: ${label} query failed`, error);
      return null;
    }
  }

  async function fetchTcResult({ warmupYear }) {
    if (!ctx.runid) {
      return { available: false, records: [] };
    }
    const primary = buildTcPayloadBySimDay({ warmupYear });
    try {
      const result = await postQueryEngine(primary);
      return { available: true, records: (result && result.records) || [] };
    } catch (error) {
      console.warn('Storm Event Analyzer: tc_out sim_day_index join failed', error);
    }

    const fallback = buildTcPayloadByJulian({ warmupYear });
    try {
      const result = await postQueryEngine(fallback);
      return { available: true, records: (result && result.records) || [] };
    } catch (error) {
      console.warn('Storm Event Analyzer: tc_out julian join failed', error);
      return { available: false, records: [] };
    }
  }

  async function fetchEventRows({ selectedMetric, filterRangePct, includeWarmup }) {
    if (!selectedMetric) {
      return { rows: [], tcAvailable: false };
    }

    const filterSpec = resolveFilterSpec(selectedMetric);

    const range = computeIntensityRange(selectedMetric.value, filterRangePct);
    if (!range) {
      return { rows: [], tcAvailable: false };
    }

    const warmupYear = includeWarmup ? await fetchWarmupYear({ postQueryEngine, runid: ctx.runid }) : null;

    const eventPayload = buildEventFilterPayload({
      filterColumn: filterSpec.filterColumn,
      minValue: range.minValue,
      maxValue: range.maxValue,
      warmupYear,
    });

    const soilPayload = buildSoilPayload({
      filterColumn: filterSpec.filterColumn,
      minValue: range.minValue,
      maxValue: range.maxValue,
      warmupYear,
    });

    const snowPayload = buildSnowPayload({
      filterColumn: filterSpec.filterColumn,
      minValue: range.minValue,
      maxValue: range.maxValue,
      warmupYear,
    });

    const hydroPayload = buildHydrologyPayload({
      filterColumn: filterSpec.filterColumn,
      minValue: range.minValue,
      maxValue: range.maxValue,
      warmupYear,
    });

    const precipPayload = buildPrecipVolumePayload({
      filterColumn: filterSpec.filterColumn,
      minValue: range.minValue,
      maxValue: range.maxValue,
      warmupYear,
    });

    const eventResult = await postQueryEngine(eventPayload);
    const [soilResult, snowResult, hydroResult, precipResult, tcResult] = await Promise.all([
      safeQuery(soilPayload, 'soil saturation'),
      safeQuery(snowPayload, 'snow water'),
      safeQuery(hydroPayload, 'hydrology'),
      safeQuery(precipPayload, 'precip volume'),
      fetchTcResult({ warmupYear }),
    ]);

    const baseRows = (eventResult && eventResult.records) || [];
    const soilMap = mapBySimDay((soilResult && soilResult.records) || [], 'soil_saturation_pct');
    const snowMap = mapBySimDay((snowResult && snowResult.records) || [], 'snow_coverage_t1_pct');
    const hydroMap = mapRowsBySimDay((hydroResult && hydroResult.records) || []);
    const precipMap = mapRowsBySimDay((precipResult && precipResult.records) || []);
    const tcAvailable = !!(tcResult && tcResult.available);
    const tcMap = mapBySimDay((tcResult && tcResult.records) || [], 'tc_hours');

    const rows = baseRows.map((row) => {
      const simDay = toNumberOrNull(row.sim_day_index);
      const year = toNumberOrNull(row.year);
      const month = toNumberOrNull(row.month);
      const day = toNumberOrNull(row.day_of_month);
      const depth = toNumberOrNull(row.depth_mm);
      const precip = toNumberOrNull(row.precip_mm);
      const duration = toNumberOrNull(row.duration_hours);
      const tp = toNumberOrNull(row.tp);
      const ip = toNumberOrNull(row.ip);
      let measureValue = null;
      if (filterSpec.metricKey === 'depth') {
        measureValue = depth;
      } else if (filterSpec.metricKey === 'duration') {
        measureValue = duration;
      } else if (filterSpec.intensityColumn) {
        measureValue = toNumberOrNull(row[filterSpec.intensityColumn]);
      }

      const hydroRow = Number.isFinite(simDay) && hydroMap.has(simDay) ? hydroMap.get(simDay) : null;
      const precipRow = Number.isFinite(simDay) && precipMap.has(simDay) ? precipMap.get(simDay) : null;
      const runoffVolume = hydroRow ? toNumberOrNull(hydroRow.runoff_volume_m3) : null;
      const peakDischarge = hydroRow ? toNumberOrNull(hydroRow.peak_discharge_m3s) : null;
      const sedimentYield = hydroRow ? toNumberOrNull(hydroRow.sediment_yield_kg) : null;
      const precipVolume = precipRow ? toNumberOrNull(precipRow.precip_volume_m3) : null;
      const totalArea = precipRow ? toNumberOrNull(precipRow.total_area_m2) : null;
      const runoffCoefficient =
        Number.isFinite(runoffVolume) && Number.isFinite(precipVolume) && precipVolume > 0
          ? runoffVolume / precipVolume
          : null;
      const runoffMm =
        Number.isFinite(runoffVolume) && Number.isFinite(totalArea) && totalArea > 0
          ? (runoffVolume / totalArea) * 1000
          : null;

      return {
        sim_day_index: simDay,
        year,
        month,
        day_of_month: day,
        date: formatDate(year, month, day),
        measure_value: Number.isFinite(measureValue) ? measureValue : null,
        depth_mm: Number.isFinite(depth) ? depth : null,
        precip_mm: Number.isFinite(precip) ? precip : Number.isFinite(depth) ? depth : null,
        duration_hours: Number.isFinite(duration) ? duration : null,
        tp: Number.isFinite(tp) ? tp : null,
        ip: Number.isFinite(ip) ? ip : null,
        soil_saturation_pct: Number.isFinite(simDay) && soilMap.has(simDay) ? soilMap.get(simDay) : null,
        snow_coverage_t1_pct: Number.isFinite(simDay) && snowMap.has(simDay) ? snowMap.get(simDay) : null,
        runoff_volume_m3: Number.isFinite(runoffVolume) ? runoffVolume : null,
        peak_discharge_m3s: Number.isFinite(peakDischarge) ? peakDischarge : null,
        sediment_yield_kg: Number.isFinite(sedimentYield) ? sedimentYield : null,
        runoff_coefficient: Number.isFinite(runoffCoefficient) ? runoffCoefficient : null,
        runoff_mm: Number.isFinite(runoffMm) ? runoffMm : null,
        tc_hours: Number.isFinite(simDay) && tcAvailable && tcMap.has(simDay) ? tcMap.get(simDay) : null,
        tc_available: tcAvailable,
      };
    });
    return { rows, tcAvailable };
  }

  return { fetchEventRows };
}
