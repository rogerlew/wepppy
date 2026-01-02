const CLIMATE_PATH = 'climate/wepp_cli.parquet';
const SOIL_PATH = 'wepp/output/interchange/H.soil.parquet';
const WATER_PATH = 'wepp/output/interchange/H.wat.parquet';
const OUTLET_PATH = 'wepp/output/interchange/ebe_pw0.parquet';

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
        sql: 'AVG(wat."Snow-Water")',
        alias: 'snow_water_t1_mm',
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
        sql: 'MAX(out.peak_runoff)',
        alias: 'peak_discharge_m3s',
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

export function createEventDataManager({ ctx, postQueryEngine }) {
  async function safeQuery(payload, label) {
    try {
      return await postQueryEngine(payload);
    } catch (error) {
      console.warn(`Storm Event Analyzer: ${label} query failed`, error);
      return null;
    }
  }

  async function fetchEventRows({ selectedMetric, filterRangePct, includeWarmup }) {
    if (!selectedMetric) {
      return [];
    }

    const filterSpec = resolveFilterSpec(selectedMetric);

    const range = computeIntensityRange(selectedMetric.value, filterRangePct);
    if (!range) {
      return [];
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

    const eventResult = await postQueryEngine(eventPayload);
    const [soilResult, snowResult, hydroResult] = await Promise.all([
      safeQuery(soilPayload, 'soil saturation'),
      safeQuery(snowPayload, 'snow water'),
      safeQuery(hydroPayload, 'hydrology'),
    ]);

    const baseRows = (eventResult && eventResult.records) || [];
    const soilMap = mapBySimDay((soilResult && soilResult.records) || [], 'soil_saturation_pct');
    const snowMap = mapBySimDay((snowResult && snowResult.records) || [], 'snow_water_t1_mm');
    const hydroMap = mapBySimDay((hydroResult && hydroResult.records) || [], 'peak_discharge_m3s');

    return baseRows.map((row) => {
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
        snow_water_t1_mm: Number.isFinite(simDay) && snowMap.has(simDay) ? snowMap.get(simDay) : null,
        peak_discharge_m3s: Number.isFinite(simDay) && hydroMap.has(simDay) ? hydroMap.get(simDay) : null,
      };
    });
  }

  return { fetchEventRows };
}
