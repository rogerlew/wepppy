import {
  INTENSITY_DURATIONS_MINUTES,
  INTENSITY_UNIT_KEY,
  NOAA_FREQUENCY_PATH,
  NOAA_HEADER_PREFIX,
  WEPP_FREQUENCY_PATH,
  WEPP_HEADER_PREFIX,
} from '../config.js';

const DEFAULT_BREAK_MARKERS = ['date/time', 'pyruntime'];

function extractDurationMinutes(label) {
  if (!label) return null;
  const match = String(label).match(/(\d+)\s*-?\s*(?:min|minute)/i);
  if (!match) return null;
  const value = Number(match[1]);
  return Number.isFinite(value) ? value : null;
}

function normalizeIntensityLabel(durationMinutes) {
  return `${durationMinutes}-min intensity`;
}

function normalizeUnitKey(unit) {
  if (!unit) return null;
  const key = String(unit).trim().toLowerCase();
  if (key === 'mm' || key === 'mm/hr' || key === 'mm/hour') {
    return key === 'mm' ? 'mm' : 'mm/hour';
  }
  if (key === 'h' || key === 'hr' || key === 'hrs' || key === 'hour' || key === 'hours') {
    return 'hours';
  }
  return unit;
}

function parseRecurrence(headerLine) {
  const recurrence = [];
  headerLine
    .split(',')
    .slice(1)
    .forEach((token) => {
      const value = token.trim();
      if (!value) return;
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        recurrence.push(Number.parseInt(parsed, 10));
      }
    });
  return recurrence;
}

function parseValues(valuesPart, recurrenceLength) {
  const parsedValues = [];
  valuesPart.split(',').forEach((rawValue) => {
    const value = rawValue.trim();
    if (!value) {
      return;
    }
    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
      parsedValues.push(numeric);
    } else {
      parsedValues.push(null);
    }
  });

  if (parsedValues.length < recurrenceLength) {
    parsedValues.push(...Array(recurrenceLength - parsedValues.length).fill(null));
  } else if (parsedValues.length > recurrenceLength) {
    parsedValues.length = recurrenceLength;
  }
  return parsedValues;
}

function parseFrequencyCsv(text, { headerPrefix, defaultUnit, parseUnitFromLabel }) {
  const lines = String(text || '').split(/\r?\n/);
  const headerIdx = lines.findIndex((line) => line.toLowerCase().startsWith(headerPrefix));
  if (headerIdx === -1) {
    return null;
  }

  const recurrence = parseRecurrence(lines[headerIdx]);
  if (!recurrence.length) {
    return null;
  }

  const rows = [];
  for (let idx = headerIdx + 1; idx < lines.length; idx += 1) {
    const line = lines[idx];
    if (!line || !line.trim()) {
      break;
    }
    const lowerLine = line.toLowerCase();
    if (DEFAULT_BREAK_MARKERS.some((marker) => lowerLine.startsWith(marker))) {
      break;
    }
    if (!line.includes(':')) {
      continue;
    }
    const [labelPart, valuesPart] = line.split(':', 2);
    let label = labelPart.trim();
    let unit = defaultUnit || '';

    if (parseUnitFromLabel && label.includes('(') && label.endsWith(')')) {
      const lastOpen = label.lastIndexOf('(');
      if (lastOpen !== -1) {
        const labelBase = label.slice(0, lastOpen).trim();
        const unitPart = label.slice(lastOpen + 1, -1).trim();
        if (labelBase) {
          label = labelBase;
        }
        if (unitPart) {
          unit = unitPart;
        }
      }
    }

    const values = parseValues(valuesPart, recurrence.length);
    rows.push({
      label,
      unit,
      unitize: unit === 'mm' || unit === 'mm/hour',
      values,
    });
  }

  if (!rows.length) {
    return null;
  }

  return { recurrence, rows };
}

export function parseWeppFrequencyCsv(text) {
  return parseFrequencyCsv(text, {
    headerPrefix: WEPP_HEADER_PREFIX,
    defaultUnit: '',
    parseUnitFromLabel: true,
  });
}

export function parseNoaaFrequencyCsv(text) {
  return parseFrequencyCsv(text, {
    headerPrefix: NOAA_HEADER_PREFIX,
    defaultUnit: INTENSITY_UNIT_KEY,
    parseUnitFromLabel: false,
  });
}

export function filterIntensityRows(rows, { requireIntensityLabel = false } = {}) {
  const filtered = [];
  (rows || []).forEach((row) => {
    const durationMinutes = extractDurationMinutes(row.label);
    if (!durationMinutes || !INTENSITY_DURATIONS_MINUTES.includes(durationMinutes)) {
      return;
    }
    if (requireIntensityLabel && !String(row.label).toLowerCase().includes('intensity')) {
      return;
    }
    filtered.push({
      ...row,
      durationMinutes,
      displayLabel: normalizeIntensityLabel(durationMinutes),
    });
  });
  return filtered;
}

export function filterWeppFrequencyRows(rows) {
  const depthRow = (rows || []).find((row) => String(row.label || '').toLowerCase().includes('depth'));
  const durationRow = (rows || []).find((row) => String(row.label || '').toLowerCase().includes('duration'));

  const filtered = [];
  if (depthRow) {
    filtered.push({
      ...depthRow,
      metricKey: 'depth',
      displayLabel: 'Depth',
      unitKey: normalizeUnitKey(depthRow.unit) || 'mm',
    });
  }
  if (durationRow) {
    filtered.push({
      ...durationRow,
      metricKey: 'duration',
      displayLabel: 'Duration',
      unitKey: normalizeUnitKey(durationRow.unit) || 'hours',
    });
  }

  const intensityRows = filterIntensityRows(rows, { requireIntensityLabel: true }).map((row) => ({
    ...row,
    metricKey: 'intensity',
    unitKey: INTENSITY_UNIT_KEY,
  }));

  return filtered.concat(intensityRows);
}

export function alignFrequencyToRecurrence(data, recurrence) {
  if (!data || !Array.isArray(data.recurrence)) {
    return null;
  }
  const indexMap = recurrence.map((value) => data.recurrence.indexOf(value));
  if (indexMap.every((idx) => idx === -1)) {
    return null;
  }
  const rows = data.rows.map((row) => {
    const values = indexMap.map((idx) => (idx >= 0 ? row.values[idx] : null));
    return { ...row, values };
  });
  return { recurrence: [...recurrence], rows };
}

function defaultResolveRunUrl(path) {
  const helper = typeof window !== 'undefined' ? window.url_for_run : null;
  if (typeof helper !== 'function') {
    throw new Error('url_for_run is not available');
  }
  return helper(path);
}

async function fetchCsv(path, { fetcher, resolveUrl }) {
  const url = resolveUrl(path);
  const response = await fetcher(url, { credentials: 'same-origin' });
  return response;
}

export async function loadFrequencyData({ fetcher = fetch, resolveUrl = defaultResolveRunUrl } = {}) {
  const weppResponse = await fetchCsv(WEPP_FREQUENCY_PATH, { fetcher, resolveUrl });
  if (!weppResponse.ok) {
    throw new Error(`Failed to load WEPP frequency CSV (${weppResponse.status})`);
  }
  const weppText = await weppResponse.text();
  const weppRaw = parseWeppFrequencyCsv(weppText);
  if (!weppRaw) {
    throw new Error('WEPP frequency CSV did not include a valid ARI header');
  }

  let noaaRaw = null;
  let noaaError = null;

  try {
    const noaaResponse = await fetchCsv(NOAA_FREQUENCY_PATH, { fetcher, resolveUrl });
    if (noaaResponse.ok) {
      const noaaText = await noaaResponse.text();
      noaaRaw = parseNoaaFrequencyCsv(noaaText);
    } else if (noaaResponse.status !== 404) {
      noaaError = new Error(`NOAA frequency CSV returned ${noaaResponse.status}`);
    }
  } catch (error) {
    noaaError = error;
  }

  return {
    wepp: weppRaw,
    noaa: noaaRaw,
    noaaError,
  };
}
