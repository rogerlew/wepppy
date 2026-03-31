import {
  DEFAULT_FILTER_RANGE_PCT,
  DEFAULT_INCLUDE_WARMUP,
  INTENSITY_UNIT_KEY,
} from './config.js?v=storm-event-analyzer-20260331b';
import { getState, initState, setState, subscribe } from './state.js?v=storm-event-analyzer-20260331b';
import {
  alignFrequencyToRecurrence,
  filterIntensityRows,
  filterWeppFrequencyRows,
  loadFrequencyData,
} from './data/frequency-data.js?v=storm-event-analyzer-20260331b';
import { createQueryEngine } from './data/query-engine.js?v=storm-event-analyzer-20260331b';
import { createEventDataManager } from './data/event-data.js?v=storm-event-analyzer-20260331b';
import { buildHyetographSeries } from './data/hyetograph-data.js?v=storm-event-analyzer-20260331b';
import { createHyetographChart } from './charts/hyetograph.js?v=storm-event-analyzer-20260331b';
import { applyNoaaAvailability, renderFrequencyTable } from './ui/frequency-table.js?v=storm-event-analyzer-20260331b';
import { bindHydrologySummaryCsv, renderHydrologySummary } from './ui/hydrology-summary.js?v=storm-event-analyzer-20260331b';
import { renderEventTable, setEventErrorBanner, updateEventSelection } from './ui/event-table.js?v=storm-event-analyzer-20260331b';
import { bindFilterControls } from './ui/filters.js?v=storm-event-analyzer-20260331b';

const MANUAL_DATE_RE = /^(\d{2}|\d{4})-(\d{2})-(\d{2})$/;

function isLeapYear(year) {
  if (!Number.isFinite(year)) {
    return false;
  }
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

function isValidCalendarDay(year, month, day) {
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) {
    return false;
  }
  if (month < 1 || month > 12 || day < 1) {
    return false;
  }
  const monthLengths = [31, isLeapYear(year) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return day <= monthLengths[month - 1];
}

function parseManualDateInput(value) {
  const text = typeof value === 'string' ? value.trim() : '';
  if (!text) {
    return null;
  }
  const match = MANUAL_DATE_RE.exec(text);
  if (!match) {
    return null;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) {
    return null;
  }
  if (!isValidCalendarDay(year, month, day)) {
    return null;
  }
  return {
    text,
    year,
    month,
    day,
  };
}

function ensureManualDateInput(section) {
  let input = document.querySelector('[data-storm-event-analyzer-manual-date]');
  if (input) {
    return input;
  }
  if (!section) {
    return null;
  }
  const dateCell = section.querySelector('[data-storm-event-analyzer-summary="date"]');
  if (!dateCell) {
    return null;
  }
  dateCell.textContent = '';
  input = document.createElement('input');
  input.type = 'text';
  input.className = 'wc-field__control storm-event-analyzer__summary-date-input';
  input.setAttribute('inputmode', 'numeric');
  input.setAttribute('autocomplete', 'off');
  input.setAttribute('spellcheck', 'false');
  input.setAttribute('pattern', '^\\d{2,4}-\\d{2}-\\d{2}$');
  input.setAttribute('placeholder', 'YY-MM-DD');
  input.setAttribute('data-storm-event-analyzer-manual-date', '');
  if (section.querySelector('#storm-event-analyzer-manual-date-help')) {
    input.setAttribute('aria-describedby', 'storm-event-analyzer-manual-date-help');
  }
  dateCell.appendChild(input);
  return input;
}

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

  const omniContext =
    typeof window !== 'undefined' && window.STORM_EVENT_ANALYZER_CONTEXT
      ? window.STORM_EVENT_ANALYZER_CONTEXT
      : {};
  const omniScenarios = Array.isArray(omniContext.omniScenarios) ? omniContext.omniScenarios : [];
  const baseScenarioLabel = omniContext.baseScenarioLabel || 'Undisturbed';

  const noaaMessage = document.querySelector('[data-noaa-unavailable]');
  const weppEmptyMessage = document.querySelector('[data-storm-event-analyzer-wepp-empty]');
  const eventsSection = document.getElementById('storm-event-analyzer__events');
  const eventTable = document.getElementById('storm_event_characteristics_table');
  const eventsEmptyMessage = document.querySelector('[data-storm-event-analyzer-events-empty]');
  const eventsLoadingMessage = document.querySelector('[data-storm-event-analyzer-events-loading]');
  const eventErrorBanner = document.querySelector('[data-storm-event-analyzer-error]');
  const hyetographSection = document.getElementById('storm-event-analyzer__hyetograph');
  const hyetographContainer = document.querySelector('[data-storm-event-analyzer-chart]');
  const hyetographEmptyMessage = hyetographSection
    ? hyetographSection.querySelector('[data-empty-state]')
    : null;
  const hydrologySummarySection = document.getElementById('storm-event-analyzer__summary');
  const omniSelect = document.querySelector('[data-storm-event-analyzer-omni-select]');
  const manualDateInput = ensureManualDateInput(hydrologySummarySection);

  initState({
    filterRangePct: DEFAULT_FILTER_RANGE_PCT,
    includeWarmup: DEFAULT_INCLUDE_WARMUP,
    selectedMetric: null,
    eventRows: [],
    hyetographSeries: [],
    selectedEventSimDayIndex: null,
    manualDateInput: '',
    eventRowsLoading: false,
    eventError: null,
    tcAvailable: false,
    soilSaturationLabel: 'Top 0.1 m Saturation',
    omniScenarios,
    omniScenario: null,
    omniSummary: null,
    baseScenarioLabel,
  });

  bindFilterControls({ setState });
  bindHydrologySummaryCsv({
    section: hydrologySummarySection,
    tableId: 'storm_event_hydrology_summary',
  });

  let unitizerClient = await getUnitizerClient();
  if (unitizerClient && typeof unitizerClient.getPreferencePayload === 'function') {
    setState({ unitPrefs: unitizerClient.getPreferencePayload() });
  }

  const ctx = { runid: window.runid, config: window.config };
  const { postQueryEngine, postQueryEngineForScenario } = createQueryEngine(ctx);
  let eventDataManager;
  try {
    eventDataManager = createEventDataManager({
      ctx,
      postQueryEngine,
      postQueryEngineForScenario,
      weppPaths: omniContext.weppPaths,
    });
  } catch (error) {
    console.error('Storm Event Analyzer: invalid context', error);
    const message = error instanceof Error ? error.message : 'Invalid storm event analyzer context.';
    setEventErrorBanner({ banner: eventErrorBanner, message });
    return;
  }
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
      onSelect: (metric) =>
        setState({ selectedMetric: metric, manualDateInput: '', eventRowsLoading: true, eventError: null }),
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
        onSelect: (metric) =>
          setState({ selectedMetric: metric, manualDateInput: '', eventRowsLoading: true, eventError: null }),
        unitKey: INTENSITY_UNIT_KEY,
      });
    }
  }

  function updateEmptyStates({ rows, error, loading }) {
    const hasRows = Array.isArray(rows) && rows.length > 0;
    if (eventsSection) {
      eventsSection.classList.toggle('is-loading', !!loading);
    }
    if (eventTable) {
      if (loading) {
        eventTable.setAttribute('aria-busy', 'true');
      } else {
        eventTable.removeAttribute('aria-busy');
      }
    }
    if (eventsLoadingMessage) {
      if (loading) {
        eventsLoadingMessage.removeAttribute('hidden');
      } else {
        eventsLoadingMessage.setAttribute('hidden', 'hidden');
      }
    }
    if (eventsEmptyMessage) {
      if (!hasRows && !error && !loading) {
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
      if (!hasRows && !loading) {
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
      soilSaturationLabel: state.soilSaturationLabel,
      onSelect: (simDayIndex) => setState({ selectedEventSimDayIndex: simDayIndex }),
    });
    setEventErrorBanner({ banner: eventErrorBanner, message: state.eventError });
    updateEmptyStates({ rows: state.eventRows, error: state.eventError, loading: state.eventRowsLoading });
  }

  function renderSummary(state) {
    if (!hydrologySummarySection) {
      return;
    }
    const selectedRow =
      state.selectedEventSimDayIndex == null
        ? null
        : (state.eventRows || []).find(
            (row) => Number(row.sim_day_index) === Number(state.selectedEventSimDayIndex),
          );
    renderHydrologySummary({
      section: hydrologySummarySection,
      row: selectedRow || null,
      unitizer: unitizerClient,
      tcAvailable: !!state.tcAvailable,
      selectedMetric: state.selectedMetric,
      soilSaturationLabel: state.soilSaturationLabel,
      omniScenario: state.omniScenario,
      omniSummary: state.omniSummary,
      baseScenarioLabel: state.baseScenarioLabel,
      manualDateInput: state.manualDateInput,
    });
  }

  function resolveOmniScenario(path) {
    if (!path) {
      return null;
    }
    return (omniScenarios || []).find((scenario) => scenario && scenario.path === path) || null;
  }

  if (omniSelect) {
    omniSelect.addEventListener('change', (event) => {
      const selectedPath = event.target.value || '';
      const scenario = resolveOmniScenario(selectedPath);
      setState({ omniScenario: scenario, omniSummary: null });
    });
  }

  if (manualDateInput) {
    const submitManualDate = () => {
      const nextValue = manualDateInput.value.trim();
      const updates = {
        manualDateInput: nextValue,
        selectedEventSimDayIndex: null,
        eventRowsLoading: !!nextValue,
      };
      if (nextValue) {
        updates.selectedMetric = null;
      }
      setState(updates);
    };
    manualDateInput.addEventListener('change', submitManualDate);
    manualDateInput.addEventListener('blur', submitManualDate);
    manualDateInput.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') {
        return;
      }
      event.preventDefault();
      submitManualDate();
      manualDateInput.blur();
    });
  }

  let eventRequestId = 0;
  async function refreshEventRows() {
    const state = getState();
    const manualDate = parseManualDateInput(state.manualDateInput);
    if (state.manualDateInput) {
      if (!manualDate) {
        setState({
          eventRows: [],
          hyetographSeries: [],
          selectedEventSimDayIndex: null,
          eventError: 'Date must use YY-MM-DD or YYYY-MM-DD.',
          eventRowsLoading: false,
          tcAvailable: false,
          soilSaturationLabel: 'Top 0.1 m Saturation',
        });
        return;
      }

      const requestId = (eventRequestId += 1);
      setState({ eventError: null, eventRowsLoading: true });
      try {
        const result = await eventDataManager.fetchEventRowByDate({
          year: manualDate.year,
          month: manualDate.month,
          day: manualDate.day,
          includeWarmup: state.includeWarmup,
        });
        if (requestId !== eventRequestId) {
          return;
        }
        const row = result && result.row ? result.row : null;
        const rows = row ? [row] : [];
        const tcAvailable = result && typeof result.tcAvailable === 'boolean' ? result.tcAvailable : false;
        const soilSaturationLabel =
          result && result.soilSaturationLabel ? result.soilSaturationLabel : 'Top 0.1 m Saturation';
        const hyetographSeries = buildHyetographSeries(rows);
        setState({
          eventRows: rows,
          hyetographSeries,
          selectedEventSimDayIndex: row ? row.sim_day_index : null,
          eventError: row ? null : `No storm event found for ${manualDate.text}.`,
          eventRowsLoading: false,
          tcAvailable,
          soilSaturationLabel,
        });
      } catch (error) {
        if (requestId !== eventRequestId) {
          return;
        }
        const message = error && error.message ? error.message : 'Query Engine request failed.';
        setState({ eventError: message, eventRowsLoading: false });
      }
      return;
    }

    if (!state.selectedMetric) {
      setState({
        eventRows: [],
        hyetographSeries: [],
        selectedEventSimDayIndex: null,
        eventError: null,
        eventRowsLoading: false,
        tcAvailable: false,
        soilSaturationLabel: 'Top 0.1 m Saturation',
      });
      return;
    }

    const requestId = (eventRequestId += 1);
    setState({ eventError: null, eventRowsLoading: true });
    try {
      const result = await eventDataManager.fetchEventRows({
        selectedMetric: state.selectedMetric,
        filterRangePct: state.filterRangePct,
        includeWarmup: state.includeWarmup,
      });
      if (requestId !== eventRequestId) {
        return;
      }
      const rows = result && Array.isArray(result.rows) ? result.rows : [];
      const tcAvailable = result && typeof result.tcAvailable === 'boolean' ? result.tcAvailable : false;
      const soilSaturationLabel =
        result && result.soilSaturationLabel ? result.soilSaturationLabel : 'Top 0.1 m Saturation';
      const selected = rows.some((row) => row.sim_day_index === state.selectedEventSimDayIndex)
        ? state.selectedEventSimDayIndex
        : null;
      const hyetographSeries = buildHyetographSeries(rows);
      setState({
        eventRows: rows,
        hyetographSeries,
        selectedEventSimDayIndex: selected,
        eventError: null,
        eventRowsLoading: false,
        tcAvailable,
        soilSaturationLabel,
      });
    } catch (error) {
      if (requestId !== eventRequestId) {
        return;
      }
      let message = error && error.message ? error.message : 'Query Engine request failed.';
      if (/sim_day_index/i.test(message)) {
        message = 'Event data is missing sim_day_index. Re-run interchange outputs for this run.';
      }
      setState({ eventError: message, eventRowsLoading: false });
    }
  }

  let omniRequestId = 0;
  async function refreshOmniSummary() {
    const state = getState();
    const scenario = state.omniScenario;
    if (!scenario || state.selectedEventSimDayIndex == null) {
      if (state.omniSummary !== null) {
        setState({ omniSummary: null });
      }
      return;
    }

    const requestId = (omniRequestId += 1);
    setState({ omniSummary: null });
    try {
      const summary = await eventDataManager.fetchScenarioSummary({
        selectedMetric: state.selectedMetric,
        simDayIndex: Number(state.selectedEventSimDayIndex),
        scenarioPath: scenario.path,
      });
      if (requestId !== omniRequestId) {
        return;
      }
      setState({ omniSummary: summary });
    } catch (error) {
      if (requestId !== omniRequestId) {
        return;
      }
      console.warn('Storm Event Analyzer: omni scenario fetch failed', error);
      setState({ omniSummary: null });
    }
  }

  renderTables(null);
  renderEventRows(getState());

  subscribe(['selectedMetric'], (state) => {
    renderTables(state.selectedMetric);
    refreshEventRows();
  });

  subscribe(['manualDateInput'], () => {
    refreshEventRows();
    renderSummary(getState());
  });

  subscribe(['filterRangePct', 'includeWarmup'], () => {
    refreshEventRows();
  });

  subscribe(['eventRows', 'eventError', 'eventRowsLoading'], (state) => {
    renderEventRows(state);
    renderSummary(state);
  });

  subscribe(['hyetographSeries'], (state) => {
    hyetographChart.setSeries(state.hyetographSeries || []);
  });

  subscribe(['selectedEventSimDayIndex'], (state) => {
    updateEventSelection({ table: eventTable, selectedEventSimDayIndex: state.selectedEventSimDayIndex });
    hyetographChart.setSelected(state.selectedEventSimDayIndex);
    renderSummary(state);
  });

  subscribe(['selectedEventSimDayIndex', 'eventRows', 'selectedMetric', 'omniScenario'], () => {
    refreshOmniSummary();
  });

  subscribe(['omniSummary'], (state) => {
    renderSummary(state);
  });

  document.addEventListener('unitizer:preferences-changed', (event) => {
    const detail = event && event.detail ? event.detail : null;
    setState({ unitPrefs: detail });
    unitizerClient = window.UnitizerClient ? window.UnitizerClient.getClientSync() : unitizerClient;
    renderTables(getState().selectedMetric || null);
    renderEventRows(getState());
    renderSummary(getState());
    hyetographChart.setUnitizer(unitizerClient, detail);
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initStormEventAnalyzer);
} else {
  initStormEventAnalyzer();
}
