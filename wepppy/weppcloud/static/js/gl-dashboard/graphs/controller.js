import { GRAPH_CONTEXT_KEYS, GRAPH_MODES } from '../config.js';

/**
 * Graph list, activation, and timeseries wiring for gl-dashboard.
 * Pure DOM/graph coordination; data loading is delegated to graphLoadersFactory.
 */

export function createGraphController({
  graphDefs,
  graphScenarios,
  graphContrastScenarios,
  graphLoadersFactory,
  yearSlider,
  getState,
  setValue,
  graphModeController,
  timeseriesGraph,
  graphPanelEl,
  graphModeButtons,
  graphEmptyEl,
  graphListEl,
  cumulativeMeasureOptions,
  monthLabels,
}) {
  const contrastScenarios = Array.isArray(graphContrastScenarios) ? graphContrastScenarios : [];
  let graphLoaders;
  let activeGraphLoad = null;
  const getGraph = typeof timeseriesGraph === 'function' ? timeseriesGraph : () => timeseriesGraph;

  const {
    clearGraphModeOverride,
    setGraphFocus,
    setGraphMode,
    syncGraphLayout,
    ensureGraphExpanded,
  } = graphModeController;
  const { OMNI, CLIMATE_YEARLY, OPENET_YEARLY } = GRAPH_CONTEXT_KEYS;
  const VALID_GRAPH_MODES = Object.values(GRAPH_MODES);
  const normalizeGraphMode = (value) => (VALID_GRAPH_MODES.includes(value) ? value : null);

  function ensureGraphLoaders() {
    if (!graphLoaders) {
      graphLoaders = graphLoadersFactory();
    }
    return graphLoaders;
  }

  function getCumulativeGraphOptions() {
    const measureOpt =
      cumulativeMeasureOptions.find((opt) => opt.key === getState().cumulativeMeasure) ||
      cumulativeMeasureOptions[0];
    const measureKey = measureOpt ? measureOpt.key : 'runoff_volume';
    if (getState().cumulativeMeasure !== measureKey) {
      setValue('cumulativeMeasure', measureKey);
    }
    const selected = Array.isArray(getState().cumulativeScenarioSelections)
      ? getState().cumulativeScenarioSelections
      : [];
    return { measureKey, scenarioPaths: selected };
  }

  function ensureClimateGraphSelected() {
    setValue('activeGraphKey', 'climate-yearly');
    const radio = document.getElementById('graph-climate-yearly');
    if (radio && !radio.checked) {
      radio.checked = true;
    }
  }

  function getClimateGraphOptions() {
    const waterYear = getState().climateWaterYear;
    const startMonth = waterYear ? getState().climateStartMonth || 10 : 1;
    return { waterYear: !!waterYear, startMonth };
  }

  function ensureOpenetYearlySelected() {
    setValue('activeGraphKey', 'openet-yearly');
    const radio = document.getElementById('graph-openet-yearly');
    if (radio && !radio.checked) {
      radio.checked = true;
    }
  }

  function getOpenetYearlyGraphOptions() {
    const waterYear = getState().openetYearlyWaterYear;
    const startMonth = waterYear ? getState().openetYearlyStartMonth || 10 : 1;
    const datasetKey = getState().openetYearlySelectedDatasetKey || getState().openetSelectedDatasetKey;
    return { waterYear: !!waterYear, startMonth, datasetKey };
  }

  async function loadRapTimeseriesData() {
    const data = await ensureGraphLoaders().buildRapTimeseriesData();
    if (!data) {
      getGraph()?.hide();
      syncGraphLayout();
      return;
    }
    getGraph()?.setData(data);
    syncGraphLayout();
  }

  async function loadWeppYearlyTimeseriesData() {
    const data = await ensureGraphLoaders().buildWeppYearlyTimeseriesData();
    if (!data) {
      getGraph()?.hide();
      syncGraphLayout();
      return;
    }
    getGraph()?.setData(data);
    syncGraphLayout();
  }

  async function loadOpenetTimeseriesData() {
    const data = await ensureGraphLoaders().buildOpenetTimeseriesData();
    if (!data) {
      getGraph()?.hide();
      syncGraphLayout();
      return;
    }
    getGraph()?.setData(data);
    syncGraphLayout();
  }

  function syncOpenetYearlySelection(data) {
    if (!data) return data;
    const years = Array.isArray(data.seriesYears) ? data.seriesYears : [];
    if (!years.length) return data;
    const selected =
      getState().openetYearlySelectedYear && years.includes(getState().openetYearlySelectedYear)
        ? getState().openetYearlySelectedYear
        : years[years.length - 1];
    data.selectedYear = selected;
    data.highlightSeriesId = String(selected);
    return data;
  }

  async function loadOpenetYearlyTimeseriesData() {
    const options = getOpenetYearlyGraphOptions();
    const data = await ensureGraphLoaders().loadGraphDataset('openet-yearly', { options });
    if (!data) {
      getGraph()?.hide();
      syncGraphLayout();
      return;
    }
    syncOpenetYearlySelection(data);
    getGraph()?.setData(data);
    syncGraphLayout();
  }

  async function activateGraphItem(key, options = {}) {
    if (getState().rapCumulativeMode && !['climate-yearly', 'openet-yearly'].includes(key)) {
      return;
    }
    if (activeGraphLoad && activeGraphLoad.key === key && !options.force) {
      return activeGraphLoad.promise;
    }
    setValue('activeGraphKey', key);
    ensureGraphExpanded();
    const keepFocus = options.keepFocus || false;
    const graphOptions = options.graphOptions;
    const loadPromise = (async () => {
      const data = await ensureGraphLoaders().loadGraphDataset(key, { force: options.force, options: graphOptions });
      const stateNow = getState();
      const stale = stateNow.activeGraphKey !== key;
      if (data) {
        if (stale) {
          syncGraphLayout();
          return;
        }
        if (!keepFocus) {
          setGraphFocus(
            data.source === OMNI || data.source === CLIMATE_YEARLY || data.source === OPENET_YEARLY
          );
        }
        if (key === 'openet-yearly') {
          syncOpenetYearlySelection(data);
        }
        getGraph()?.setData(data);
        if (data.source === CLIMATE_YEARLY && Array.isArray(data.years) && data.years.length) {
          const minYear = Math.min(...data.years);
          const maxYear = Math.max(...data.years);
          const selYear =
            data.selectedYear != null && Number.isFinite(data.selectedYear) ? data.selectedYear : maxYear;
          setValue('climateYearlySelectedYear', selYear);
          yearSlider.setRange(minYear, maxYear, selYear);
        } else if (data.source === OPENET_YEARLY && Array.isArray(data.seriesYears) && data.seriesYears.length) {
          const minYear = Math.min(...data.seriesYears);
          const maxYear = Math.max(...data.seriesYears);
          const selYear =
            data.selectedYear != null && Number.isFinite(data.selectedYear) ? data.selectedYear : maxYear;
          setValue('openetYearlySelectedYear', selYear);
          yearSlider.setRange(minYear, maxYear, selYear);
        }
      } else {
        getGraph()?.hide();
        if (graphEmptyEl) {
          graphEmptyEl.textContent = 'No data available for this graph.';
          graphEmptyEl.style.display = '';
        }
      }
      syncGraphLayout();
    })();
    activeGraphLoad = { key, promise: loadPromise };
    try {
      await loadPromise;
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to activate graph', err);
      getGraph()?.hide();
      if (graphEmptyEl) {
        graphEmptyEl.textContent = 'Unable to load graph data.';
        graphEmptyEl.style.display = '';
      }
    } finally {
      if (activeGraphLoad && activeGraphLoad.promise === loadPromise) {
        activeGraphLoad = null;
      }
    }
  }

  function handleCumulativeMeasureChange(nextValue) {
    setValue('cumulativeMeasure', nextValue);
    if (getState().activeGraphKey === 'cumulative-contribution') {
      const options = getCumulativeGraphOptions();
      activateGraphItem('cumulative-contribution', {
        force: true,
        keepFocus: true,
        graphOptions: options,
      });
    }
  }

  function handleCumulativeScenarioToggle(path, checked) {
    const current = Array.isArray(getState().cumulativeScenarioSelections)
      ? getState().cumulativeScenarioSelections.slice()
      : [];
    const nextSet = new Set(current);
    if (checked) {
      nextSet.add(path);
    } else {
      nextSet.delete(path);
    }
    const next = Array.from(nextSet);
    setValue('cumulativeScenarioSelections', next);
    if (getState().activeGraphKey === 'cumulative-contribution') {
      const options = getCumulativeGraphOptions();
      activateGraphItem('cumulative-contribution', {
        force: true,
        keepFocus: true,
        graphOptions: options,
      });
    }
  }

  function renderCumulativeControls(details) {
    const toolbar = document.createElement('div');
    toolbar.className = 'gl-graph__toolbar';

    const measureField = document.createElement('div');
    measureField.className = 'gl-graph__field';
    const measureLabel = document.createElement('label');
    measureLabel.setAttribute('for', 'gl-cumulative-measure');
    measureLabel.textContent = 'Measure';
    const measureSelect = document.createElement('select');
    measureSelect.id = 'gl-cumulative-measure';
    cumulativeMeasureOptions.forEach((opt) => {
      const optionEl = document.createElement('option');
      optionEl.value = opt.key;
      optionEl.textContent = opt.label;
      measureSelect.appendChild(optionEl);
    });
    const measureOpt =
      cumulativeMeasureOptions.find((opt) => opt.key === getState().cumulativeMeasure) ||
      cumulativeMeasureOptions[0];
    measureSelect.value = measureOpt.key;
    measureSelect.addEventListener('change', (e) => handleCumulativeMeasureChange(e.target.value));
    measureField.appendChild(measureLabel);
    measureField.appendChild(measureSelect);

    const scenarioField = document.createElement('div');
    scenarioField.className = 'gl-graph__field';
    const scenarioLabel = document.createElement('span');
    scenarioLabel.textContent = 'Select Scenarios';
    const scenarioList = document.createElement('div');
    scenarioList.className = 'gl-graph__scenario-list';
    const selectedSet = new Set(getState().cumulativeScenarioSelections || []);
    const scenarioGroups = [
      { items: (graphScenarios || []).slice(1) },
      { items: contrastScenarios },
    ];
    let renderedAny = false;
    let scenarioIndex = 0;
    scenarioGroups.forEach((group, groupIndex) => {
      if (!group.items || !group.items.length) return;
      if (renderedAny && groupIndex > 0) {
        const divider = document.createElement('hr');
        divider.className = 'gl-graph__divider';
        divider.style.border = '0';
        divider.style.borderTop = '1px solid var(--wc-color-border-muted, #2d3a4a)';
        divider.style.margin = '0.35rem 0';
        scenarioList.appendChild(divider);
      }
      group.items.forEach((scenario) => {
        const scenarioKey = scenario.path || `_pups/omni/scenarios/${scenario.name || `scenario-${scenarioIndex}`}`;
        const id = `gl-cumulative-scenario-${scenarioIndex}`;
        scenarioIndex += 1;
        const wrapper = document.createElement('label');
        wrapper.className = 'gl-layer-item';
        wrapper.style.display = 'flex';
        wrapper.style.alignItems = 'center';
        wrapper.style.gap = '0.5rem';
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.id = id;
        input.value = scenarioKey;
        input.checked = selectedSet.has(scenarioKey);
        input.addEventListener('change', (e) => handleCumulativeScenarioToggle(scenarioKey, e.target.checked));
        const span = document.createElement('span');
        span.textContent = scenario.name || scenario.path || `Scenario ${scenarioIndex}`;
        wrapper.appendChild(input);
        wrapper.appendChild(span);
        scenarioList.appendChild(wrapper);
      });
      renderedAny = true;
    });
    scenarioField.appendChild(scenarioLabel);
    scenarioField.appendChild(scenarioList);

    toolbar.appendChild(measureField);
    toolbar.appendChild(scenarioField);
    details.appendChild(toolbar);
  }

  function renderClimateControls(details) {
    const monthLabelsSafe = Array.isArray(monthLabels) && monthLabels.length === 12
      ? monthLabels
      : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const wrapper = document.createElement('div');
    wrapper.className = 'gl-graph__options gl-wepp-stat__options';

    const modeLabel = document.createElement('div');
    modeLabel.textContent = 'Year Mode';
    modeLabel.style.fontSize = '0.9rem';
    modeLabel.style.color = 'var(--wc-color-text-muted)';
    wrapper.appendChild(modeLabel);

    const modeContainer = document.createElement('div');
    modeContainer.style.display = 'flex';
    modeContainer.style.gap = '0.75rem';
    const calendarLabel = document.createElement('label');
    calendarLabel.style.display = 'flex';
    calendarLabel.style.alignItems = 'center';
    calendarLabel.style.gap = '0.35rem';
    const calendarInput = document.createElement('input');
    calendarInput.type = 'radio';
    calendarInput.name = 'climate-year-mode';
    calendarInput.value = 'calendar';
    calendarInput.checked = !getState().climateWaterYear;
    calendarInput.addEventListener('change', () => handleClimateModeChange('calendar'));
    calendarInput.addEventListener('click', () => handleClimateModeChange('calendar'));
    const calendarSpan = document.createElement('span');
    calendarSpan.textContent = 'Calendar Year';
    calendarLabel.appendChild(calendarInput);
    calendarLabel.appendChild(calendarSpan);

    const waterLabel = document.createElement('label');
    waterLabel.style.display = 'flex';
    waterLabel.style.alignItems = 'center';
    waterLabel.style.gap = '0.35rem';
    const waterInput = document.createElement('input');
    waterInput.type = 'radio';
    waterInput.name = 'climate-year-mode';
    waterInput.value = 'water';
    waterInput.checked = !!getState().climateWaterYear;
    waterInput.addEventListener('change', () => handleClimateModeChange('water'));
    waterInput.addEventListener('click', () => handleClimateModeChange('water'));
    const waterSpan = document.createElement('span');
    waterSpan.textContent = 'Water Year';
    waterLabel.appendChild(waterInput);
    waterLabel.appendChild(waterSpan);

    modeContainer.appendChild(calendarLabel);
    modeContainer.appendChild(waterLabel);
    wrapper.appendChild(modeContainer);

    const startField = document.createElement('div');
    startField.className = 'gl-graph__field';
    const startLabel = document.createElement('label');
    startLabel.textContent = 'Water Year start month';
    startLabel.style.fontSize = '0.9rem';
    startLabel.style.color = 'var(--wc-color-text-muted)';
    const startSelect = document.createElement('select');
    startSelect.id = 'gl-climate-start-month';
    for (let i = 1; i <= 12; i++) {
      const opt = document.createElement('option');
      opt.value = String(i);
      opt.textContent = monthLabelsSafe[i - 1] || `Month ${i}`;
      startSelect.appendChild(opt);
    }
    const startVal = getState().climateStartMonth || 10;
    startSelect.value = String(startVal);
    startSelect.disabled = !getState().climateWaterYear;
    startSelect.addEventListener('change', (e) => handleClimateStartMonthChange(e.target.value));

    startField.appendChild(startLabel);
    startField.appendChild(startSelect);
    wrapper.appendChild(startField);
    details.appendChild(wrapper);
  }

  function renderOpenetYearlyControls(details) {
    const monthLabelsSafe = Array.isArray(monthLabels) && monthLabels.length === 12
      ? monthLabels
      : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const openetMeta = getState().openetMetadata;
    const datasetKeys = openetMeta && Array.isArray(openetMeta.datasetKeys) ? openetMeta.datasetKeys : [];
    if (!datasetKeys.length) return;

    let selectedDataset = getState().openetYearlySelectedDatasetKey;
    if (!selectedDataset || !datasetKeys.includes(selectedDataset)) {
      selectedDataset = datasetKeys.includes('ensemble') ? 'ensemble' : datasetKeys[0];
      setValue('openetYearlySelectedDatasetKey', selectedDataset);
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'gl-graph__options gl-wepp-stat__options';

    const datasetLabel = document.createElement('div');
    datasetLabel.textContent = 'Dataset';
    datasetLabel.style.fontSize = '0.9rem';
    datasetLabel.style.color = 'var(--wc-color-text-muted)';
    wrapper.appendChild(datasetLabel);

    const datasetContainer = document.createElement('div');
    datasetContainer.style.display = 'flex';
    datasetContainer.style.flexDirection = 'column';
    datasetContainer.style.gap = '0.35rem';

    datasetKeys.forEach((key) => {
      const label = document.createElement('label');
      label.style.display = 'flex';
      label.style.alignItems = 'center';
      label.style.gap = '0.35rem';
      const input = document.createElement('input');
      input.type = 'radio';
      input.name = 'openet-yearly-dataset';
      input.value = key;
      input.checked = key === selectedDataset;
      input.addEventListener('change', () => handleOpenetYearlyDatasetChange(key));
      input.addEventListener('click', () => handleOpenetYearlyDatasetChange(key));
      const span = document.createElement('span');
      span.textContent = key;
      label.appendChild(input);
      label.appendChild(span);
      datasetContainer.appendChild(label);
    });

    wrapper.appendChild(datasetContainer);

    const modeLabel = document.createElement('div');
    modeLabel.textContent = 'Year Mode';
    modeLabel.style.fontSize = '0.9rem';
    modeLabel.style.color = 'var(--wc-color-text-muted)';
    wrapper.appendChild(modeLabel);

    const modeContainer = document.createElement('div');
    modeContainer.style.display = 'flex';
    modeContainer.style.gap = '0.75rem';
    const calendarLabel = document.createElement('label');
    calendarLabel.style.display = 'flex';
    calendarLabel.style.alignItems = 'center';
    calendarLabel.style.gap = '0.35rem';
    const calendarInput = document.createElement('input');
    calendarInput.type = 'radio';
    calendarInput.name = 'openet-year-mode';
    calendarInput.value = 'calendar';
    calendarInput.checked = !getState().openetYearlyWaterYear;
    calendarInput.addEventListener('change', () => handleOpenetYearlyModeChange('calendar'));
    calendarInput.addEventListener('click', () => handleOpenetYearlyModeChange('calendar'));
    const calendarSpan = document.createElement('span');
    calendarSpan.textContent = 'Calendar Year';
    calendarLabel.appendChild(calendarInput);
    calendarLabel.appendChild(calendarSpan);

    const waterLabel = document.createElement('label');
    waterLabel.style.display = 'flex';
    waterLabel.style.alignItems = 'center';
    waterLabel.style.gap = '0.35rem';
    const waterInput = document.createElement('input');
    waterInput.type = 'radio';
    waterInput.name = 'openet-year-mode';
    waterInput.value = 'water';
    waterInput.checked = !!getState().openetYearlyWaterYear;
    waterInput.addEventListener('change', () => handleOpenetYearlyModeChange('water'));
    waterInput.addEventListener('click', () => handleOpenetYearlyModeChange('water'));
    const waterSpan = document.createElement('span');
    waterSpan.textContent = 'Water Year';
    waterLabel.appendChild(waterInput);
    waterLabel.appendChild(waterSpan);

    modeContainer.appendChild(calendarLabel);
    modeContainer.appendChild(waterLabel);
    wrapper.appendChild(modeContainer);

    const startField = document.createElement('div');
    startField.className = 'gl-graph__field';
    const startLabel = document.createElement('label');
    startLabel.textContent = 'Water Year start month';
    startLabel.style.fontSize = '0.9rem';
    startLabel.style.color = 'var(--wc-color-text-muted)';
    const startSelect = document.createElement('select');
    startSelect.id = 'gl-openet-year-start-month';
    for (let i = 1; i <= 12; i++) {
      const opt = document.createElement('option');
      opt.value = String(i);
      opt.textContent = monthLabelsSafe[i - 1] || `Month ${i}`;
      startSelect.appendChild(opt);
    }
    const startVal = getState().openetYearlyStartMonth || 10;
    startSelect.value = String(startVal);
    startSelect.disabled = !getState().openetYearlyWaterYear;
    startSelect.addEventListener('change', (e) => handleOpenetYearlyStartMonthChange(e.target.value));

    startField.appendChild(startLabel);
    startField.appendChild(startSelect);
    wrapper.appendChild(startField);
    details.appendChild(wrapper);
  }

  function handleClimateModeChange(mode) {
    const waterYear = mode === 'water';
    const currentState = getState();
    let nextStart = currentState.climateStartMonth || 10;
    if (!waterYear) {
      nextStart = 1;
    } else if (!nextStart || nextStart === 1) {
      nextStart = 10;
    }
    setValue('climateWaterYear', waterYear);
    setValue('climateStartMonth', nextStart);
    ensureClimateGraphSelected();
    const select = document.getElementById('gl-climate-start-month');
    if (select) {
      select.disabled = !waterYear;
      select.value = String(nextStart);
    }
    const options = getClimateGraphOptions();
    activateGraphItem('climate-yearly', { force: true, graphOptions: options, keepFocus: true });
  }

  function handleClimateStartMonthChange(val) {
    const month = Math.min(12, Math.max(1, Number(val) || 10));
    setValue('climateStartMonth', month);
    ensureClimateGraphSelected();
    const options = getClimateGraphOptions();
    activateGraphItem('climate-yearly', { force: true, graphOptions: options, keepFocus: true });
  }

  function handleOpenetYearlyDatasetChange(datasetKey) {
    setValue('openetYearlySelectedDatasetKey', datasetKey);
    ensureOpenetYearlySelected();
    const options = getOpenetYearlyGraphOptions();
    activateGraphItem('openet-yearly', { force: true, graphOptions: options, keepFocus: true });
  }

  function handleOpenetYearlyModeChange(mode) {
    const waterYear = mode === 'water';
    const currentState = getState();
    let nextStart = currentState.openetYearlyStartMonth || 10;
    if (!waterYear) {
      nextStart = 1;
    } else if (!nextStart || nextStart === 1) {
      nextStart = 10;
    }
    setValue('openetYearlyWaterYear', waterYear);
    setValue('openetYearlyStartMonth', nextStart);
    ensureOpenetYearlySelected();
    const select = document.getElementById('gl-openet-year-start-month');
    if (select) {
      select.disabled = !waterYear;
      select.value = String(nextStart);
    }
    const options = getOpenetYearlyGraphOptions();
    activateGraphItem('openet-yearly', { force: true, graphOptions: options, keepFocus: true });
  }

  function handleOpenetYearlyStartMonthChange(val) {
    const month = Math.min(12, Math.max(1, Number(val) || 10));
    setValue('openetYearlyStartMonth', month);
    ensureOpenetYearlySelected();
    const options = getOpenetYearlyGraphOptions();
    activateGraphItem('openet-yearly', { force: true, graphOptions: options, keepFocus: true });
  }

  function renderGraphList() {
    if (!graphListEl) return;
    graphListEl.innerHTML = '';
    let rendered = 0;
    graphDefs.forEach((group, idx) => {
      if (group.key === 'openet-yearly') {
        const openetMeta = getState().openetMetadata;
        const datasetKeys = openetMeta && Array.isArray(openetMeta.datasetKeys) ? openetMeta.datasetKeys : [];
        if (!datasetKeys.length) {
          return;
        }
      }
      const details = document.createElement('details');
      details.className = 'gl-layer-details';
      const hasActive = group.items.some((i) => i.key === getState().activeGraphKey);
      details.open = idx === 0 || hasActive;

      const summary = document.createElement('summary');
      summary.className = 'gl-layer-group';
      summary.textContent = group.title || 'Graphs';
      details.appendChild(summary);

      const itemList = document.createElement('ul');
      itemList.className = 'gl-layer-items';

      group.items.forEach((item) => {
        const li = document.createElement('li');
        li.className = 'gl-layer-item';
        const input = document.createElement('input');
        input.type = 'radio';
        input.name = 'graph-selection';
        input.id = `graph-${item.key}`;
        input.checked = getState().activeGraphKey === item.key;
        input.addEventListener('change', async () => {
          if (!input.checked) return;
          clearGraphModeOverride();
          setValue('activeGraphKey', item.key);
          syncGraphLayout({ resetContext: true });
          let graphOptions;
          if (item.key === 'cumulative-contribution') {
            graphOptions = getCumulativeGraphOptions();
          } else if (item.key === 'climate-yearly') {
            graphOptions = getClimateGraphOptions();
          } else if (item.key === 'openet-yearly') {
            graphOptions = getOpenetYearlyGraphOptions();
          }
          await activateGraphItem(item.key, {
            graphOptions,
            force: item.key === 'climate-yearly' || item.key === 'openet-yearly',
            keepFocus: item.key === 'climate-yearly' || item.key === 'openet-yearly',
          });
        });
        const label = document.createElement('label');
        label.setAttribute('for', input.id);
        label.innerHTML = `<span class=\"gl-layer-name\">${item.label}</span>`;
        li.appendChild(input);
        li.appendChild(label);
        itemList.appendChild(li);
        rendered += 1;
      });

      details.appendChild(itemList);
      if (group.key === 'cumulative') {
        renderCumulativeControls(details);
      }
      if (group.key === 'climate') {
        renderClimateControls(details);
      }
      if (group.key === 'openet-yearly') {
        renderOpenetYearlyControls(details);
      }

      graphListEl.appendChild(details);
    });

    if (graphEmptyEl) {
      graphEmptyEl.hidden = rendered > 0;
    }
  }

  async function handleGraphPanelToggle(visible) {
    if (!visible) {
      setGraphFocus(false);
      return;
    }
    if (activeGraphLoad && activeGraphLoad.key === getState().activeGraphKey) {
      await activeGraphLoad.promise.catch(() => {});
      return;
    }
    if (!getState().activeGraphKey) {
      const openetActive = (getState().openetLayers || []).some((layer) => layer && layer.visible);
      if (openetActive) {
        await loadOpenetTimeseriesData();
      }
      return;
    }
    if (getState().activeGraphKey) {
      const options =
        getState().activeGraphKey === 'cumulative-contribution'
          ? getCumulativeGraphOptions()
          : getState().activeGraphKey === 'climate-yearly'
            ? getClimateGraphOptions()
            : getState().activeGraphKey === 'openet-yearly'
              ? getOpenetYearlyGraphOptions()
            : undefined;
      await activateGraphItem(getState().activeGraphKey, {
        keepFocus: getState().graphFocus,
        graphOptions: options,
        force: ['climate-yearly', 'openet-yearly'].includes(getState().activeGraphKey),
      });
    }
  }

  function bindModeButtons() {
    if (graphModeButtons && graphModeButtons.length) {
      graphModeButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
          const nextMode = normalizeGraphMode(btn.dataset.graphMode) || GRAPH_MODES.SPLIT;
          setGraphMode(nextMode, { source: 'user' });
        });
      });
    }
  }

  return {
    renderGraphList,
    getClimateGraphOptions,
    getCumulativeGraphOptions,
    getOpenetYearlyGraphOptions,
    loadRapTimeseriesData,
    loadWeppYearlyTimeseriesData,
    loadOpenetTimeseriesData,
    loadOpenetYearlyTimeseriesData,
    activateGraphItem,
    handleGraphPanelToggle,
    bindModeButtons,
  };
}
