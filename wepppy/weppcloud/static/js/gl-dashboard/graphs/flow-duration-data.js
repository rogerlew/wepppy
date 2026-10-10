/** Daily populations and independent Weibull curves. No DOM or map dependencies. */
export const FLOW_DURATION_KEY = "flow-duration";
export const FLOW_DURATION_DEFAULTS = {
  source: "hillslope",
  excludedYears: 2,
  scale: "linear",
};
const DAY_MS = 86400000;

function dayNumber(year, month, day) {
  if (![year, month, day].every(Number.isInteger) || year < 1 || year > 9999)
    throw new Error("Invalid daily date");
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  date.setUTCHours(0, 0, 0, 0);
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    throw new Error("Invalid daily date");
  }
  return date.getTime() / DAY_MS;
}

function numeric(value) {
  if (value === null || value === undefined || /^nan$/i.test(String(value)))
    return null;
  if (String(value).trim() === "")
    throw new Error("Invalid daily flow or area");
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0)
    throw new Error("Invalid daily flow or area");
  return number;
}

export function rankDailyFlows(records, source, excludedYears = 2) {
  const seen = new Set();
  const rows = records
    .map((row) => {
      const year = Number(row.year),
        month = Number(row.month),
        day = Number(row.day);
      const ordinal = dayNumber(year, month, day);
      if (Number(row.julian) !== ordinal - dayNumber(year, 1, 1) + 1)
        throw new Error("Invalid Julian date");
      if (seen.has(ordinal)) throw new Error("Duplicate daily records");
      seen.add(ordinal);
      return {
        ...row,
        year,
        ordinal,
        date: `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
      };
    })
    .sort((a, b) => a.ordinal - b.ordinal);
  const years = [...new Set(rows.map((row) => row.year))].sort((a, b) => a - b);
  const excluded = new Set(years.slice(0, excludedYears));
  const eligible = rows.filter((row) => !excluded.has(row.year));
  const points = [];
  let nullDays = 0,
    zeroDays = 0;
  for (const row of eligible) {
    const value = numeric(row.flow);
    const area = source === "hillslope" ? numeric(row.area) : 1;
    if (source === "hillslope" && (area === null || area <= 0))
      throw new Error("Invalid watershed area");
    if (value === null) {
      nullDays += 1;
      continue;
    }
    const flow =
      source === "hillslope" ? (value * area) / 1000 / 86400 : value / 86400;
    if (!Number.isFinite(flow)) throw new Error("Invalid converted discharge");
    if (flow === 0) zeroDays += 1;
    points.push({ flow, date: row.date });
  }
  let expected = 0;
  let periodStart = null,
    periodEnd = null;
  if (rows.length) {
    for (
      let year = rows[0].year;
      year <= rows[rows.length - 1].year;
      year += 1
    ) {
      if (excluded.has(year)) continue;
      const first = Math.max(rows[0].ordinal, dayNumber(year, 1, 1));
      const last = Math.min(
        rows[rows.length - 1].ordinal,
        dayNumber(year, 12, 31),
      );
      expected += Math.max(0, last - first + 1);
      if (last >= first) {
        if (periodStart === null) periodStart = first;
        periodEnd = last;
      }
    }
  }
  points.sort((a, b) => b.flow - a.flow);
  points.forEach((point, index) => {
    point.probability = (100 * (index + 1)) / (points.length + 1);
  });
  return {
    points,
    count: points.length,
    missing: expected - eligible.length + nullDays,
    zeroDays,
    expected,
    warmupDays: rows.length - eligible.length,
    start:
      periodStart === null
        ? null
        : new Date(periodStart * DAY_MS).toISOString().slice(0, 10),
    end:
      periodEnd === null
        ? null
        : new Date(periodEnd * DAY_MS).toISOString().slice(0, 10),
  };
}

export function createFlowDurationLoader({
  scenarios,
  metadata,
  query,
  displayName,
  color,
}) {
  const cache = new Map();
  const curves = new Map();
  async function read(scenario, source) {
    const path = scenario.path || "";
    const readiness = metadata?.scenarios?.[path]?.[source];
    if (!readiness?.available)
      throw new Error(
        readiness?.reason || metadata?.reason || "Daily source is unavailable",
      );
    const key = `${path}:${source}`;
    if (cache.has(key)) return cache.get(key);
    const dataset = source === "hillslope" ? "totalwatsed3" : "chanwb";
    const value = source === "hillslope" ? "Streamflow" : "Outflow (m^3)";
    const payload = {
      datasets: [
        { path: `wepp/output/interchange/${dataset}.parquet`, alias: "d" },
      ],
      columns: [
        "d.year AS year",
        "d.month AS month",
        "d.day_of_month AS day",
        "d.julian AS julian",
        `CAST(d."${value}" AS VARCHAR) AS flow`,
        ...(source === "hillslope"
          ? ['CAST(d."Area" AS VARCHAR) AS area']
          : []),
      ],
      ...(source === "outlet"
        ? {
            filters: [
              { column: "d.Chan_ID", op: "=", value: readiness.channelId },
              { column: "d.Elmt_ID", op: "=", value: readiness.elementId },
            ],
          }
        : {}),
    };
    const pending = query(
      payload,
      path || metadata?.queryScenarioPath || "",
    ).then((result) => {
      if (
        !result ||
        !Array.isArray(result.records) ||
        result.row_count !== result.records.length
      ) {
        throw new Error(
          "Daily query failed or returned an incomplete population",
        );
      }
      return result.records;
    });
    cache.set(key, pending);
    try {
      return await pending;
    } catch (error) {
      cache.delete(key);
      throw error;
    }
  }
  return async (options = {}) => {
    const settings = { ...FLOW_DURATION_DEFAULTS, ...options };
    const series = [];
    // Sequential queries bound concurrent backend work and memory across large catalogs.
    for (let index = 0; index < scenarios.length; index += 1) {
      const scenario = scenarios[index];
      const label = displayName(scenario);
      const item = {
        id: scenario.path || "base",
        label,
        color: color(index, label),
      };
      try {
        const records = await read(scenario, settings.source);
        const curveKey = `${scenario.path || ""}:${settings.source}`;
        let cached = curves.get(curveKey);
        if (!cached || cached.excludedYears !== settings.excludedYears) {
          cached = {
            excludedYears: settings.excludedYears,
            curve: rankDailyFlows(
              records,
              settings.source,
              settings.excludedYears,
            ),
          };
          curves.set(curveKey, cached);
        }
        Object.assign(item, cached.curve);
        if (!item.count)
          item.error = "No eligible daily values after year selection";
      } catch (error) {
        item.error = error.message || "Daily data could not be loaded";
        item.points = [];
      }
      series.push(item);
    }
    return {
      type: FLOW_DURATION_KEY,
      source: FLOW_DURATION_KEY,
      title: "Flow duration curve",
      units: "m³/s",
      settings,
      series,
    };
  };
}
