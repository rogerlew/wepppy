import {
  DEFAULT_FILTER_RANGE_PCT,
  DEFAULT_INCLUDE_WARMUP,
  INTENSITY_UNIT_KEY,
} from './config.js';
import { getState, initState, setState, subscribe } from './state.js';
import {
  alignFrequencyToRecurrence,
  filterIntensityRows,
  loadFrequencyData,
} from './data/frequency-data.js';
import { applyNoaaAvailability, renderFrequencyTable } from './ui/frequency-table.js';
import { bindFilterControls } from './ui/filters.js';

function getUnitizerClient() {
  if (typeof window === 'undefined') {
    return Promise.resolve(null);
  }
  if (!window.UnitizerClient || typeof window.UnitizerClient.ready !== 'function') {
    return Promise.resolve(null);
  }
  return window.UnitizerClient.ready().catch((error) => {
    console.warn('Storm Event Analyzer: UnitizerClient failed to load', error);
    return null;
  });
}

async function initStormEventAnalyzer() {
  const weppTable = document.getElementById('storm_event_wepp_frequency');
  const noaaTable = document.getElementById('storm_event_noaa_frequency');
  if (!weppTable) {
    return;
  }

  const noaaMessage = document.querySelector('[data-noaa-unavailable]');

  initState({
    filterRangePct: DEFAULT_FILTER_RANGE_PCT,
    includeWarmup: DEFAULT_INCLUDE_WARMUP,
    selectedMetric: null,
  });

  bindFilterControls({ setState });

  let unitizerClient = await getUnitizerClient();
  if (unitizerClient && typeof unitizerClient.getPreferencePayload === 'function') {
    setState({ unitPrefs: unitizerClient.getPreferencePayload() });
  }

  let frequencyData;
  try {
    frequencyData = await loadFrequencyData();
  } catch (error) {
    console.error('Storm Event Analyzer: failed to load frequency CSVs', error);
    return;
  }

  const weppIntensityRows = filterIntensityRows(frequencyData.wepp.rows, { requireIntensityLabel: true });
  const weppDisplay = {
    recurrence: frequencyData.wepp.recurrence,
    rows: weppIntensityRows,
  };

  let noaaDisplay = null;
  if (frequencyData.noaa) {
    const alignedNoaa = alignFrequencyToRecurrence(frequencyData.noaa, weppDisplay.recurrence);
    if (alignedNoaa) {
      const noaaRows = filterIntensityRows(alignedNoaa.rows, { requireIntensityLabel: false });
      noaaDisplay = {
        recurrence: alignedNoaa.recurrence,
        rows: noaaRows,
      };
    }
  }

  if (frequencyData.noaaError) {
    console.warn('Storm Event Analyzer: NOAA frequency data error', frequencyData.noaaError);
  }

  function renderTables(selectedMetric) {
    renderFrequencyTable({
      table: weppTable,
      data: weppDisplay,
      tableKey: 'wepp',
      unitizer: unitizerClient,
      selectedMetric,
      onSelect: (metric) => setState({ selectedMetric: metric }),
      unitKey: INTENSITY_UNIT_KEY,
    });

    const noaaAvailable = Boolean(noaaDisplay && noaaDisplay.rows.length);
    applyNoaaAvailability({ table: noaaTable, message: noaaMessage, available: noaaAvailable });

    if (noaaAvailable) {
      renderFrequencyTable({
        table: noaaTable,
        data: noaaDisplay,
        tableKey: 'noaa',
        unitizer: unitizerClient,
        selectedMetric,
        onSelect: (metric) => setState({ selectedMetric: metric }),
        unitKey: INTENSITY_UNIT_KEY,
      });
    }
  }

  renderTables(null);

  subscribe(['selectedMetric'], (state) => {
    renderTables(state.selectedMetric);
  });

  document.addEventListener('unitizer:preferences-changed', (event) => {
    const detail = event && event.detail ? event.detail : null;
    setState({ unitPrefs: detail });
    unitizerClient = window.UnitizerClient ? window.UnitizerClient.getClientSync() : unitizerClient;
    renderTables(getState().selectedMetric || null);
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initStormEventAnalyzer);
} else {
  initStormEventAnalyzer();
}
