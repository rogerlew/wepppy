import {
  DEFAULT_FILTER_RANGE_PCT,
  DEFAULT_INCLUDE_WARMUP,
  INTENSITY_UNIT_KEY,
} from './config.js';
import { getState, initState, setState, subscribe } from './state.js';
import {
  alignFrequencyToRecurrence,
  filterIntensityRows,
  filterWeppFrequencyRows,
  loadFrequencyData,
} from './data/frequency-data.js?v=storm-event-analyzer';
import { createQueryEngine } from './data/query-engine.js';
import { createEventDataManager } from './data/event-data.js';
import { buildHyetographSeries } from './data/hyetograph-data.js';
import { createHyetographChart } from './charts/hyetograph.js';
import { applyNoaaAvailability, renderFrequencyTable } from './ui/frequency-table.js';
import { renderEventTable, setEventErrorBanner, updateEventSelection } from './ui/event-table.js';
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
  const weppEmptyMessage = document.querySelector('[data-storm-event-analyzer-wepp-empty]');
  const eventTable = document.getElementById('storm_event_characteristics_table');
  const eventsEmptyMessage = document.querySelector('[data-storm-event-analyzer-events-empty]');
  const eventErrorBanner = document.querySelector('[data-storm-event-analyzer-error]');
  const hyetographSection = document.getElementById('storm-event-analyzer__hyetograph');
  const hyetographContainer = document.querySelector('[data-storm-event-analyzer-chart]');
  const hyetographEmptyMessage = hyetographSection
    ? hyetographSection.querySelector('[data-empty-state]')
    : null;

  initState({
    filterRangePct: DEFAULT_FILTER_RANGE_PCT,
    includeWarmup: DEFAULT_INCLUDE_WARMUP,
    selectedMetric: null,
    eventRows: [],
    hyetographSeries: [],
    selectedEventSimDayIndex: null,
    eventError: null,
  });

  bindFilterControls({ setState });

  let unitizerClient = await getUnitizerClient();
  if (unitizerClient && typeof unitizerClient.getPreferencePayload === 'function') {
    setState({ unitPrefs: unitizerClient.getPreferencePayload() });
  }

  const ctx = { runid: window.runid, config: window.config };
  const { postQueryEngine } = createQueryEngine(ctx);
  const eventDataManager = createEventDataManager({ ctx, postQueryEngine });
  const hyetographChart = createHyetographChart({
    container: hyetographContainer,
    emptyEl: hyetographEmptyMessage,
    unitizer: unitizerClient,
    unitPrefs: getState().unitPrefs,
    onSelect: (simDayIndex) => setState({ selectedEventSimDayIndex: simDayIndex }),
  });
  hyetographChart.init();

  let frequencyData;
  try {
    frequencyData = await loadFrequencyData();
  } catch (error) {
    console.error('Storm Event Analyzer: failed to load frequency CSVs', error);
    return;
  }

  const weppIntensityRows = filterWeppFrequencyRows(frequencyData.wepp.rows);
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

  function updateEmptyStates({ rows, error }) {
    const hasRows = Array.isArray(rows) && rows.length > 0;
    if (eventsEmptyMessage) {
      if (!hasRows && !error) {
        eventsEmptyMessage.removeAttribute('hidden');
      } else {
        eventsEmptyMessage.setAttribute('hidden', 'hidden');
      }
    }
    if (weppEmptyMessage) {
      if (!hasRows || error) {
        weppEmptyMessage.removeAttribute('hidden');
      } else {
        weppEmptyMessage.setAttribute('hidden', 'hidden');
      }
    }
    if (hyetographEmptyMessage) {
      if (!hasRows) {
        hyetographEmptyMessage.removeAttribute('hidden');
      } else {
        hyetographEmptyMessage.setAttribute('hidden', 'hidden');
      }
    }
  }

  function renderEventRows(state) {
    if (!eventTable) {
      return;
    }
    const measureUnitKey =
      state.selectedMetric && state.selectedMetric.unitKey ? state.selectedMetric.unitKey : 'mm/hour';
    renderEventTable({
      table: eventTable,
      rows: state.eventRows || [],
      selectedEventSimDayIndex: state.selectedEventSimDayIndex,
      unitizer: unitizerClient,
      measureUnitKey,
      onSelect: (simDayIndex) => setState({ selectedEventSimDayIndex: simDayIndex }),
    });
    setEventErrorBanner({ banner: eventErrorBanner, message: state.eventError });
    updateEmptyStates({ rows: state.eventRows, error: state.eventError });
  }

  let eventRequestId = 0;
  async function refreshEventRows() {
    const state = getState();
    if (!state.selectedMetric) {
      setState({ eventRows: [], hyetographSeries: [], selectedEventSimDayIndex: null, eventError: null });
      return;
    }

    const requestId = (eventRequestId += 1);
    setState({ eventError: null });
    try {
      const rows = await eventDataManager.fetchEventRows({
        selectedMetric: state.selectedMetric,
        filterRangePct: state.filterRangePct,
        includeWarmup: state.includeWarmup,
      });
      if (requestId !== eventRequestId) {
        return;
      }
      const selected = rows.some((row) => row.sim_day_index === state.selectedEventSimDayIndex)
        ? state.selectedEventSimDayIndex
        : null;
      const hyetographSeries = buildHyetographSeries(rows);
      setState({
        eventRows: rows,
        hyetographSeries,
        selectedEventSimDayIndex: selected,
        eventError: null,
      });
    } catch (error) {
      if (requestId !== eventRequestId) {
        return;
      }
      let message = error && error.message ? error.message : 'Query Engine request failed.';
      if (/sim_day_index/i.test(message)) {
        message = 'Event data is missing sim_day_index. Re-run interchange outputs for this run.';
      }
      setState({ eventError: message });
    }
  }

  renderTables(null);
  renderEventRows(getState());

  subscribe(['selectedMetric'], (state) => {
    renderTables(state.selectedMetric);
    refreshEventRows();
  });

  subscribe(['filterRangePct', 'includeWarmup'], () => {
    refreshEventRows();
  });

  subscribe(['eventRows', 'eventError'], (state) => {
    renderEventRows(state);
  });

  subscribe(['hyetographSeries'], (state) => {
    hyetographChart.setSeries(state.hyetographSeries || []);
  });

  subscribe(['selectedEventSimDayIndex'], (state) => {
    updateEventSelection({ table: eventTable, selectedEventSimDayIndex: state.selectedEventSimDayIndex });
    hyetographChart.setSelected(state.selectedEventSimDayIndex);
  });

  document.addEventListener('unitizer:preferences-changed', (event) => {
    const detail = event && event.detail ? event.detail : null;
    setState({ unitPrefs: detail });
    unitizerClient = window.UnitizerClient ? window.UnitizerClient.getClientSync() : unitizerClient;
    renderTables(getState().selectedMetric || null);
    renderEventRows(getState());
    hyetographChart.setUnitizer(unitizerClient, detail);
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initStormEventAnalyzer);
} else {
  initStormEventAnalyzer();
}
