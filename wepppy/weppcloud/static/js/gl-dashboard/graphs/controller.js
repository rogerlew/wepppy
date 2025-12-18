/**
 * Graph list, activation, and timeseries wiring for gl-dashboard.
 * Pure DOM/graph coordination; data loading is delegated to graphLoadersFactory.
 */

export function createGraphController({
  graphDefs,
  graphScenarios,
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

  function getClimateGraphOptions() {
    const waterYear = getState().climateWaterYear;
    const startMonth = waterYear ? getState().climateStartMonth || 10 : 1;
    return { waterYear: !!waterYear, startMonth };
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

  async function activateGraphItem(key, options = {}) {
    if (getState().rapCumulativeMode && key !== 'climate-yearly') {
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
          setGraphFocus(data.source === 'omni' || data.source === 'climate_yearly');
        }
        getGraph()?.setData(data);
        if (data.source === 'climate_yearly' && Array.isArray(data.years) && data.years.length) {
          const minYear = Math.min(...data.years);
          const maxYear = Math.max(...data.years);
          const selYear =
            data.selectedYear != null && Number.isFinite(data.selectedYear) ? data.selectedYear : maxYear;
          setValue('climateYearlySelectedYear', selYear);
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
    graphScenarios.slice(1).forEach((scenario, idx) => {
      const id = `gl-cumulative-scenario-${idx}`;
      const wrapper = document.createElement('label');
      wrapper.className = 'gl-layer-item';
      wrapper.style.display = 'flex';
      wrapper.style.alignItems = 'center';
      wrapper.style.gap = '0.5rem';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.id = id;
      input.checked = selectedSet.has(scenario.path);
      input.addEventListener('change', (e) => handleCumulativeScenarioToggle(scenario.path, e.target.checked));
      const span = document.createElement('span');
      span.textContent = scenario.name || scenario.path || `Scenario ${idx + 1}`;
      wrapper.appendChild(input);
      wrapper.appendChild(span);
      scenarioList.appendChild(wrapper);
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
    const options = getClimateGraphOptions();
    activateGraphItem('climate-yearly', { force: true, graphOptions: options, keepFocus: true });
  }

  function renderGraphList() {
    if (!graphListEl) return;
    graphListEl.innerHTML = '';
    let rendered = 0;
    graphDefs.forEach((group, idx) => {
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
          }
          await activateGraphItem(item.key, {
            graphOptions,
            force: item.key === 'climate-yearly',
            keepFocus: item.key === 'climate-yearly',
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
    if (getState().activeGraphKey) {
      const options =
        getState().activeGraphKey === 'cumulative-contribution'
          ? getCumulativeGraphOptions()
          : getState().activeGraphKey === 'climate-yearly'
            ? getClimateGraphOptions()
            : undefined;
      await activateGraphItem(getState().activeGraphKey, {
        keepFocus: getState().graphFocus,
        graphOptions: options,
        force: getState().activeGraphKey === 'climate-yearly',
      });
    }
  }

  function bindModeButtons() {
    if (graphModeButtons && graphModeButtons.length) {
      graphModeButtons.forEach((btn) => {
        btn.addEventListener('click', () => setGraphMode(btn.dataset.graphMode, { source: 'user' }));
      });
    }
  }

  return {
    renderGraphList,
    getClimateGraphOptions,
    getCumulativeGraphOptions,
    loadRapTimeseriesData,
    loadWeppYearlyTimeseriesData,
    activateGraphItem,
    handleGraphPanelToggle,
    bindModeButtons,
  };
}
