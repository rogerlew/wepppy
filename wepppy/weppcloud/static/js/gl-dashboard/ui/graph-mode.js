import {
  GRAPH_CONTEXT_KEYS,
  GRAPH_MODES,
  GRAPH_SLIDER_PLACEMENTS,
  YEAR_SLIDER_CONTEXTS,
} from '../config.js';

/**
 * @typedef {Object} GraphModeDomRefs
 * @property {HTMLElement | null} [glMainEl]
 * @property {HTMLElement | null} [graphPanelEl]
 * @property {NodeListOf<HTMLElement> | HTMLElement[] | null} [graphModeButtons]
 */

/**
 * @typedef {import('../config.js').GraphMode} GraphMode
 */

/**
 * @typedef {import('../config.js').GraphContextKey} GraphContextKey
 */

/**
 * @typedef {import('../config.js').GraphSliderPlacement} GraphSliderPlacement
 */

/**
 * @typedef {Object} GraphContext
 * @property {GraphContextKey} key
 * @property {boolean} graphCapable
 * @property {GraphSliderPlacement} [slider]
 */

/**
 * @typedef {Object} GraphModeChangePayload
 * @property {GraphMode} mode
 * @property {GraphContextKey} contextKey
 * @property {boolean} graphCapable
 * @property {boolean} focus
 */

/**
 * @typedef {Object} TimeseriesGraph
 * @property {string} [_source]
 * @property {unknown} [_data]
 * @property {() => void} [render]
 * @property {() => void} [_resizeCanvas]
 * @property {() => void} [hide]
 */

/**
 * @typedef {Object} YearSliderController
 * @property {HTMLElement | null} el
 * @property {(ctx?: import('../config.js').YearSliderContext) => void} show
 * @property {() => void} hide
 */

/**
 * @callback GetState
 * @returns {Record<string, any>}
 */

/**
 * @callback SetValue
 * @param {string} key
 * @param {any} value
 */

/**
 * @callback GraphModeChangeHandler
 * @param {GraphModeChangePayload} payload
 */

/**
 * @typedef {Object} GraphModeController
 * @property {() => void} clearGraphModeOverride
 * @property {(enabled: boolean, options?: { skipModeSync?: boolean, force?: boolean }) => void} setGraphFocus
 * @property {(collapsed: boolean, options?: { focusOnExpand?: boolean }) => void} setGraphCollapsed
 * @property {() => void} toggleGraphPanel
 * @property {(mode: GraphMode, options?: { source?: 'auto' | 'user', resetContext?: boolean }) => GraphMode | undefined} setGraphMode
 * @property {(options?: { userOverride?: GraphMode, resetContext?: boolean }) => GraphMode | undefined} syncGraphLayout
 * @property {(stateObj?: Record<string, any>) => GraphContext} resolveGraphContext
 * @property {(mode: GraphMode) => void} updateGraphModeButtons
 * @property {() => void} ensureGraphExpanded
 */

/**
 * Graph mode/layout controller: handles slider placement, panel collapse, and focus.
 * @param {{ getState: GetState, setValue: SetValue, domRefs?: GraphModeDomRefs, yearSlider?: YearSliderController | null, timeseriesGraph?: TimeseriesGraph | (() => TimeseriesGraph | null), onModeChange?: GraphModeChangeHandler }} params
 * @returns {GraphModeController}
 */
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
  const VALID_GRAPH_MODES = Object.values(GRAPH_MODES);
  const normalizeGraphMode = (value) => (VALID_GRAPH_MODES.includes(value) ? value : null);

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
    [GRAPH_CONTEXT_KEYS.CLIMATE_YEARLY]: {
      mode: GRAPH_MODES.FULL,
      slider: GRAPH_SLIDER_PLACEMENTS.BOTTOM,
      focus: true,
    },
    [GRAPH_CONTEXT_KEYS.WEPP_YEARLY]: {
      mode: GRAPH_MODES.SPLIT,
      slider: GRAPH_SLIDER_PLACEMENTS.TOP,
      focus: false,
    },
    [GRAPH_CONTEXT_KEYS.RAP]: {
      mode: GRAPH_MODES.SPLIT,
      slider: GRAPH_SLIDER_PLACEMENTS.TOP,
      focus: false,
    },
    [GRAPH_CONTEXT_KEYS.CUMULATIVE]: {
      mode: GRAPH_MODES.FULL,
      slider: GRAPH_SLIDER_PLACEMENTS.HIDE,
      focus: true,
    },
    [GRAPH_CONTEXT_KEYS.OMNI]: {
      mode: GRAPH_MODES.FULL,
      slider: GRAPH_SLIDER_PLACEMENTS.HIDE,
      focus: true,
    },
    [GRAPH_CONTEXT_KEYS.DEFAULT]: {
      mode: GRAPH_MODES.SPLIT,
      slider: GRAPH_SLIDER_PLACEMENTS.HIDE,
      focus: false,
    },
  };

  const GRAPH_SLIDER_OVERRIDES = {
    'climate-yearly': GRAPH_SLIDER_PLACEMENTS.BOTTOM,
    'cumulative-contribution': GRAPH_SLIDER_PLACEMENTS.HIDE,
    'omni-outlet-sediment': GRAPH_SLIDER_PLACEMENTS.BOTTOM,
    'omni-outlet-stream': GRAPH_SLIDER_PLACEMENTS.BOTTOM,
    'omni-soil-loss-hill': GRAPH_SLIDER_PLACEMENTS.HIDE,
    'omni-soil-loss-chn': GRAPH_SLIDER_PLACEMENTS.HIDE,
    'omni-runoff-hill': GRAPH_SLIDER_PLACEMENTS.HIDE,
  };

  function positionYearSlider(position) {
    const container = document.getElementById('gl-graph-container');
    const slider = yearSlider;
    if (!slider || !slider.el) {
      if (position === GRAPH_SLIDER_PLACEMENTS.HIDE && container) {
        container.classList.remove('has-bottom-slider');
      }
      return;
    }
    if (position === GRAPH_SLIDER_PLACEMENTS.INHERIT) {
      return;
    }
    if (position === GRAPH_SLIDER_PLACEMENTS.TOP) {
      slider.show(YEAR_SLIDER_CONTEXTS.LAYER);
      return;
    }
    if (position === GRAPH_SLIDER_PLACEMENTS.BOTTOM) {
      slider.show(YEAR_SLIDER_CONTEXTS.CLIMATE);
      return;
    }
    slider.hide();
  }

  function currentGraphSource() {
    try {
      const graph = getGraph() || window.glDashboardTimeseriesGraph;
      return graph && graph._source ? graph._source : null;
    } catch {
      return null;
    }
  }

  function updateGraphModeButtons(mode) {
    const buttons = graphModeButtons && typeof graphModeButtons.length === 'number' ? Array.from(graphModeButtons) : [];
    if (!buttons.length) return;
    const omniFocused = currentGraphSource() === GRAPH_CONTEXT_KEYS.OMNI && (getState().graphFocus || false);

    buttons.forEach((btn) => {
      const btnMode = normalizeGraphMode(btn.dataset.graphMode);
      const isActive = btnMode === mode;
      btn.classList.toggle('is-active', isActive);
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      const isMin = btnMode === GRAPH_MODES.MINIMIZED;
      const isSplit = btnMode === GRAPH_MODES.SPLIT;
      const disable = (!btnMode || (!graphControlsEnabled && !isMin)) || (omniFocused && isSplit);
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

  function setGraphFocus(enabled, options = {}) {
    const { skipModeSync = false, force = false } = options;
    const focus = !!enabled;
    if (!focus && graphModeUserOverride === GRAPH_MODES.FULL && !force) {
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
      const mode = collapsed ? GRAPH_MODES.MINIMIZED : focus ? GRAPH_MODES.FULL : GRAPH_MODES.SPLIT;
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
    setGraphMode(collapsing ? GRAPH_MODES.MINIMIZED : GRAPH_MODES.SPLIT, { source: 'user' });
  }

  function applyGraphMode(mode, { graphCapable = true, focusOverride } = {}) {
    const validated = VALID_GRAPH_MODES.includes(mode) ? mode : GRAPH_MODES.SPLIT;
    const effectiveMode = graphCapable ? validated : GRAPH_MODES.MINIMIZED;

    setValue('graphMode', effectiveMode);
    if (effectiveMode === GRAPH_MODES.MINIMIZED) {
      setGraphCollapsed(true);
      setGraphFocus(false, { skipModeSync: true, force: true });
    } else if (effectiveMode === GRAPH_MODES.SPLIT) {
      setGraphCollapsed(false, { focusOnExpand: false });
      setGraphFocus(false, { skipModeSync: true, force: true });
    } else if (effectiveMode === GRAPH_MODES.FULL) {
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
    const sliderOverride = activeKey ? GRAPH_SLIDER_OVERRIDES[activeKey] : null;

    if (activeKey === 'climate-yearly') {
      return {
        key: GRAPH_CONTEXT_KEYS.CLIMATE_YEARLY,
        graphCapable: true,
        slider: sliderOverride || GRAPH_SLIDER_PLACEMENTS.BOTTOM,
      };
    }
    if (activeKey === 'cumulative-contribution') {
      return {
        key: GRAPH_CONTEXT_KEYS.CUMULATIVE,
        graphCapable: true,
        slider: sliderOverride || GRAPH_SLIDER_PLACEMENTS.HIDE,
      };
    }
    if (activeKey && activeKey.startsWith('omni')) {
      return {
        key: GRAPH_CONTEXT_KEYS.OMNI,
        graphCapable: true,
        slider: sliderOverride || GRAPH_SLIDER_PLACEMENTS.HIDE,
      };
    }
    if (!activeKey) {
      if (rapActive) return { key: GRAPH_CONTEXT_KEYS.RAP, graphCapable: true };
      if (yearlyActive) return { key: GRAPH_CONTEXT_KEYS.WEPP_YEARLY, graphCapable: true };
      return { key: GRAPH_CONTEXT_KEYS.DEFAULT, graphCapable: false };
    }

    if (source === GRAPH_CONTEXT_KEYS.CLIMATE_YEARLY) {
      return {
        key: GRAPH_CONTEXT_KEYS.CLIMATE_YEARLY,
        graphCapable: true,
        slider: sliderOverride || GRAPH_SLIDER_PLACEMENTS.BOTTOM,
      };
    }
    if (source === GRAPH_CONTEXT_KEYS.RAP && rapActive) return { key: GRAPH_CONTEXT_KEYS.RAP, graphCapable: true };
    if (source === GRAPH_CONTEXT_KEYS.WEPP_YEARLY && yearlyActive) {
      return { key: GRAPH_CONTEXT_KEYS.WEPP_YEARLY, graphCapable: true };
    }
    if (source === GRAPH_CONTEXT_KEYS.OMNI) {
      return {
        key: GRAPH_CONTEXT_KEYS.OMNI,
        graphCapable: true,
        slider: sliderOverride || GRAPH_SLIDER_PLACEMENTS.HIDE,
      };
    }

    if (rapActive) return { key: GRAPH_CONTEXT_KEYS.RAP, graphCapable: true };
    if (yearlyActive) return { key: GRAPH_CONTEXT_KEYS.WEPP_YEARLY, graphCapable: true };
    return { key: GRAPH_CONTEXT_KEYS.DEFAULT, graphCapable: false };
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
    const def = GRAPH_CONTEXT_DEFS[context.key] || GRAPH_CONTEXT_DEFS[GRAPH_CONTEXT_KEYS.DEFAULT];
    const override = graphModeUserOverride;
    const graphCapable = context.graphCapable;
    const sliderPlacement = graphCapable ? (context.slider || def.slider) : GRAPH_SLIDER_PLACEMENTS.HIDE;
    const mode = graphCapable ? (override || def.mode) : GRAPH_MODES.MINIMIZED;
    const focus = override ? mode === GRAPH_MODES.FULL : def.focus || mode === GRAPH_MODES.FULL;
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
    const validated = VALID_GRAPH_MODES.includes(mode) ? mode : GRAPH_MODES.SPLIT;
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
