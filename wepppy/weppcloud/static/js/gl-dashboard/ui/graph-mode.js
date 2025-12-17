export function createGraphModeController({
  getState,
  setValue,
  domRefs,
  yearSlider,
  timeseriesGraph,
  onModeChange,
}) {
  const glMainEl = domRefs?.glMainEl || null;
  const graphPanelEl = domRefs?.graphPanelEl || null;
  const graphModeButtons = domRefs?.graphModeButtons || null;
  const getGraph = typeof timeseriesGraph === 'function' ? timeseriesGraph : () => timeseriesGraph;

  let graphModeUserOverride = null;
  let graphControlsEnabled = true;
  let lastGraphContextKey = null;

  function clearGraphModeOverride() {
    graphModeUserOverride = null;
  }

  function isRapActive(stateObj) {
    if (!stateObj) return false;
    if (stateObj.rapCumulativeMode) return true;
    return (stateObj.rapLayers || []).some((l) => l && l.visible);
  }

  function isWeppYearlyActive(stateObj) {
    if (!stateObj || !stateObj.weppYearlySummary) return false;
    return (stateObj.weppYearlyLayers || []).some((l) => l && l.visible);
  }

  const GRAPH_CONTEXT_DEFS = {
    climate_yearly: { mode: 'full', slider: 'bottom', focus: true },
    wepp_yearly: { mode: 'split', slider: 'top', focus: false },
    rap: { mode: 'split', slider: 'top', focus: false },
    cumulative: { mode: 'full', slider: 'inherit', focus: true },
    omni: { mode: 'full', slider: 'inherit', focus: true },
    default: { mode: 'split', slider: 'hide', focus: false },
  };

  function positionYearSlider(position) {
    const container = document.getElementById('gl-graph-container');
    const slider = yearSlider;
    if (!slider || !slider.el) {
      if (position === 'hide' && container) {
        container.classList.remove('has-bottom-slider');
      }
      return;
    }
    if (position === 'inherit') {
      return;
    }
    if (position === 'top') {
      slider.show('layer');
      return;
    }
    if (position === 'bottom') {
      slider.show('climate');
      return;
    }
    slider.hide();
  }

  function currentGraphSource() {
    try {
      const graph = getGraph() || window.glDashboardTimeseriesGraph;
      return graph && graph._source ? graph._source : null;
    } catch (err) {
      return null;
    }
  }

  function updateGraphModeButtons(mode) {
    const buttons = graphModeButtons && typeof graphModeButtons.length === 'number' ? Array.from(graphModeButtons) : [];
    if (!buttons.length) return;
    const omniFocused = currentGraphSource() === 'omni' && (getState().graphFocus || false);

    buttons.forEach((btn) => {
      const isActive = btn.dataset.graphMode === mode;
      btn.classList.toggle('is-active', isActive);
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      const isMin = btn.dataset.graphMode === 'minimized';
      const isSplit = btn.dataset.graphMode === 'split';
      const disable = (!graphControlsEnabled && !isMin) || (omniFocused && isSplit);
      if (disable) {
        btn.classList.add('is-disabled');
        btn.setAttribute('aria-disabled', 'true');
        btn.disabled = true;
      } else {
        btn.classList.remove('is-disabled');
        btn.removeAttribute('aria-disabled');
        btn.disabled = false;
      }
    });
  }

  function setGraphControlsEnabled(enabled) {
    graphControlsEnabled = !!enabled;
    updateGraphModeButtons(getState().graphMode || 'split');
  }

  function setGraphFocus(enabled, options = {}) {
    const { skipModeSync = false, force = false } = options;
    const focus = !!enabled;
    if (!focus && graphModeUserOverride === 'full' && !force) {
      return;
    }
    setValue('graphFocus', focus);
    if (glMainEl) {
      if (focus) {
        glMainEl.classList.add('graph-focus');
      } else {
        glMainEl.classList.remove('graph-focus');
      }
    }
    if (!skipModeSync) {
      const collapsed = graphPanelEl ? graphPanelEl.classList.contains('is-collapsed') : false;
      const mode = collapsed ? 'minimized' : focus ? 'full' : 'split';
      setValue('graphMode', mode);
      updateGraphModeButtons(mode);
    }
  }

  function ensureGraphExpanded() {
    if (graphPanelEl) {
      graphPanelEl.classList.remove('is-collapsed');
    }
  }

  function setGraphCollapsed(collapsed, options = {}) {
    const { focusOnExpand = true } = options;
    if (!graphPanelEl) return;
    const wasCollapsed = graphPanelEl.classList.contains('is-collapsed');
    graphPanelEl.classList.toggle('is-collapsed', collapsed);
    const changed = wasCollapsed !== collapsed;
    if (changed && typeof window.glDashboardGraphToggled === 'function') {
      window.glDashboardGraphToggled(!graphPanelEl.classList.contains('is-collapsed'));
    }
    if (collapsed) {
      setValue('graphFocus', false);
      if (glMainEl) {
        glMainEl.classList.remove('graph-focus');
      }
      setGraphFocus(false, { force: true });
    } else {
      setGraphFocus(focusOnExpand);
      const graph = getGraph();
      if (graph && typeof graph._resizeCanvas === 'function') {
        graph._resizeCanvas();
        if (graph._data) {
          graph.render();
        }
      }
    }
  }

  function toggleGraphPanel() {
    if (!graphPanelEl) return;
    const collapsing = !graphPanelEl.classList.contains('is-collapsed');
    setGraphMode(collapsing ? 'minimized' : 'split', { source: 'user' });
  }

  function applyGraphMode(mode, { graphCapable = true, focusOverride } = {}) {
    const validated = ['minimized', 'split', 'full'].includes(mode) ? mode : 'split';
    const effectiveMode = graphCapable ? validated : 'minimized';

    setValue('graphMode', effectiveMode);
    if (effectiveMode === 'minimized') {
      setGraphCollapsed(true);
      setGraphFocus(false, { skipModeSync: true, force: true });
    } else if (effectiveMode === 'split') {
      setGraphCollapsed(false, { focusOnExpand: false });
      setGraphFocus(false, { skipModeSync: true, force: true });
    } else if (effectiveMode === 'full') {
      setGraphCollapsed(false, { focusOnExpand: true });
      setGraphFocus(true, { skipModeSync: true, force: true });
    }
    if (focusOverride !== undefined) {
      setGraphFocus(!!focusOverride, { skipModeSync: true, force: true });
    }
    updateGraphModeButtons(effectiveMode);
    return effectiveMode;
  }

  function resolveGraphContext(stateObj = getState()) {
    const st = stateObj || getState();
    const activeKey = st.activeGraphKey;
    const source = currentGraphSource();
    const rapActive = isRapActive(st);
    const yearlyActive = isWeppYearlyActive(st);

    if (activeKey === 'climate-yearly') return { key: 'climate_yearly', graphCapable: true };
    if (activeKey === 'cumulative-contribution') return { key: 'cumulative', graphCapable: true };
    if (activeKey && activeKey.startsWith('omni')) return { key: 'omni', graphCapable: true };
    if (!activeKey) {
      if (rapActive) return { key: 'rap', graphCapable: true };
      if (yearlyActive) return { key: 'wepp_yearly', graphCapable: true };
      return { key: 'default', graphCapable: false };
    }

    if (source === 'climate_yearly') return { key: 'climate_yearly', graphCapable: true };
    if (source === 'rap' && rapActive) return { key: 'rap', graphCapable: true };
    if (source === 'wepp_yearly' && yearlyActive) return { key: 'wepp_yearly', graphCapable: true };
    if (source === 'omni') return { key: 'omni', graphCapable: true };

    if (rapActive) return { key: 'rap', graphCapable: true };
    if (yearlyActive) return { key: 'wepp_yearly', graphCapable: true };
    return { key: 'default', graphCapable: false };
  }

  function syncGraphLayout(options = {}) {
    const { userOverride, resetContext = false } = options;
    if (userOverride !== undefined) {
      graphModeUserOverride = userOverride;
    }
    if (resetContext) {
      lastGraphContextKey = null;
    }
    const st = getState();
    const context = resolveGraphContext(st);
    const def = GRAPH_CONTEXT_DEFS[context.key] || GRAPH_CONTEXT_DEFS.default;
    const override = graphModeUserOverride;
    const graphCapable = context.graphCapable;
    const sliderPlacement = graphCapable ? def.slider : 'hide';
    const mode = graphCapable ? (override || def.mode) : 'minimized';
    const focus = override ? mode === 'full' : def.focus || mode === 'full';
    const sliderReady = !!(yearSlider && yearSlider.el);
    const layoutKey = `${context.key}|${mode}|${focus ? '1' : '0'}|${sliderPlacement}|${override || ''}|${graphCapable ? 1 : 0}|${sliderReady ? 'ready' : 'pending'}`;
    if (layoutKey === lastGraphContextKey) {
      return;
    }
    lastGraphContextKey = layoutKey;

    if (!graphCapable) {
      const graph = getGraph();
      if (graph && typeof graph.hide === 'function') {
        graph.hide();
      }
      if (st.activeGraphKey) {
        setValue('activeGraphKey', null);
      }
      setValue('graphFocus', false);
      if (glMainEl) {
        glMainEl.classList.remove('graph-focus');
      }
      setGraphFocus(false, { skipModeSync: true, force: true });
    }

    const appliedMode = applyGraphMode(mode, {
      graphCapable,
      focusOverride: focus,
    });

    positionYearSlider(sliderPlacement);

    if (typeof onModeChange === 'function') {
      onModeChange({
        mode: appliedMode,
        contextKey: context.key,
        graphCapable,
        focus,
      });
    }

    return appliedMode;
  }

  function setGraphMode(mode, options = {}) {
    const { source = 'auto', resetContext = false } = options;
    const validated = ['minimized', 'split', 'full'].includes(mode) ? mode : 'split';
    if (source === 'user') {
      graphModeUserOverride = validated;
    } else if (source === 'auto') {
      clearGraphModeOverride();
    }
    return syncGraphLayout({
      userOverride: source === 'user' ? validated : undefined,
      resetContext,
    });
  }

  return {
    clearGraphModeOverride,
    setGraphFocus,
    setGraphCollapsed,
    toggleGraphPanel,
    setGraphMode,
    syncGraphLayout,
    resolveGraphContext,
    updateGraphModeButtons,
    ensureGraphExpanded,
  };
}
