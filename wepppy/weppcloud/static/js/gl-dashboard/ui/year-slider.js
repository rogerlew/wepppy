import { YEAR_SLIDER_CONTEXTS } from '../config.js';

/**
 * @typedef {import('../config.js').YearSliderContext} YearSliderContext
 */
/**
 * @typedef {Object} YearSliderElements
 * @property {HTMLElement | null} el
 * @property {HTMLInputElement | null} input
 * @property {HTMLElement | null} valueEl
 * @property {HTMLElement | null} minEl
 * @property {HTMLElement | null} maxEl
 * @property {HTMLElement | null} playBtn
 */

/**
 * @typedef {Object} YearSliderInitConfig
 * @property {number} [startYear]
 * @property {number} [endYear]
 * @property {boolean} [hasObserved]
 */

/**
 * @typedef {Object} YearSliderController
 * @property {HTMLElement | null} el
 * @property {HTMLInputElement | null} input
 * @property {HTMLElement | null} valueEl
 * @property {HTMLElement | null} minEl
 * @property {HTMLElement | null} maxEl
 * @property {HTMLElement | null} playBtn
 * @property {(config?: YearSliderInitConfig) => void} init
 * @property {(ctx?: YearSliderContext) => void} show
 * @property {() => void} hide
 * @property {(min: number, max: number, current?: number) => void} setRange
 * @property {() => number} getValue
 * @property {(year: number) => void} setValue
 * @property {(event: 'change', callback: (year: number) => void) => void} on
 * @property {(event: 'change', callback: (year: number) => void) => void} off
 * @property {() => void} play
 * @property {() => void} pause
 * @property {() => void} toggle
 */

/**
 * Year slider controller used by graph-mode to place and control the year picker.
 * @param {YearSliderElements} params
 * @returns {YearSliderController}
 */
export function createYearSlider({
  el,
  input,
  valueEl,
  minEl,
  maxEl,
  playBtn,
}) {
  let listeners = [];
  let visible = false;
  let minYear = 1;
  let maxYear = 100;
  let currentYear = 1;
  let hasObserved = false;
  let initialized = false;
  let playing = false;
  let intervalId = null;
  let context = YEAR_SLIDER_CONTEXTS.LAYER;
  let playButton = playBtn || null;
  const VALID_CONTEXTS = Object.values(YEAR_SLIDER_CONTEXTS);

  const normalizeContext = (ctx) => (VALID_CONTEXTS.includes(ctx) ? ctx : YEAR_SLIDER_CONTEXTS.LAYER);

  const updateDisplay = () => {
    if (valueEl) {
      valueEl.textContent = String(currentYear);
    }
  };

  const emit = (event, data) => {
    for (const listener of listeners) {
      if (listener.event === event) {
        listener.callback(data);
      }
    }
  };

  const updatePlayButton = () => {
    if (playButton) {
      playButton.textContent = playing ? '⏸' : '▶';
      playButton.title = playing ? 'Pause' : 'Play';
    }
  };

  const init = (config = {}) => {
    if (!el || !input) return;
    if (initialized) return;
    initialized = true;

    minYear = config.startYear || 1;
    maxYear = config.endYear || 100;
    hasObserved = config.hasObserved || false;
    currentYear = minYear;
    playing = false;
    intervalId = null;
    playButton = playButton || playBtn || null;

    input.min = String(minYear);
    input.max = String(maxYear);
    input.value = String(currentYear);

    if (minEl) minEl.textContent = String(minYear);
    if (maxEl) maxEl.textContent = String(maxYear);
    updateDisplay();

    input.addEventListener('input', () => {
      currentYear = parseInt(input.value, 10);
      updateDisplay();
      emit('change', currentYear);
    });

    if (playButton) {
      playButton.addEventListener('click', () => toggle());
    }
  };

  const show = (ctx = YEAR_SLIDER_CONTEXTS.LAYER) => {
    if (!el) return;
    const resolvedContext = normalizeContext(ctx);
    context = resolvedContext;

    const container = document.getElementById('gl-graph-container');
    const slot = document.getElementById('gl-graph-year-slider');
    const target =
      resolvedContext === YEAR_SLIDER_CONTEXTS.CLIMATE ? (container || slot) : (slot || container);

    if (target && el.parentElement !== target) {
      target.appendChild(el);
    }

    if (container) {
      container.classList.toggle('has-bottom-slider', resolvedContext === YEAR_SLIDER_CONTEXTS.CLIMATE);
    }

    el.classList.add('is-visible');
    visible = true;
  };

  const hide = () => {
    if (el && visible) {
      el.classList.remove('is-visible');
      visible = false;
    }
    const container = document.getElementById('gl-graph-container');
    if (container) {
      container.classList.remove('has-bottom-slider');
    }
  };

  const setRange = (min, max, current) => {
    if (!initialized && el && input) {
      init({ startYear: min, endYear: max });
    }
    minYear = min;
    maxYear = max;
    if (input) {
      input.min = String(min);
      input.max = String(max);
    }
    if (minEl) minEl.textContent = String(min);
    if (maxEl) maxEl.textContent = String(max);
    if (current != null) {
      currentYear = current;
      if (input) input.value = String(current);
    }
    updateDisplay();
  };

  const getValue = () => currentYear;

  const setValue = (year) => {
    currentYear = year;
    if (input) input.value = String(year);
    updateDisplay();
  };

  const on = (event, callback) => {
    listeners.push({ event, callback });
  };

  const off = (event, callback) => {
    listeners = listeners.filter((l) => !(l.event === event && l.callback === callback));
  };

  const play = () => {
    if (playing) return;
    playing = true;
    updatePlayButton();

    intervalId = setInterval(() => {
      let nextYear = currentYear + 1;
      if (nextYear > maxYear) {
        nextYear = minYear;
      }
      currentYear = nextYear;
      if (input) input.value = String(nextYear);
      updateDisplay();
      emit('change', currentYear);
    }, 3000);
  };

  const pause = () => {
    if (!playing) return;
    playing = false;
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
    updatePlayButton();
  };

  const toggle = () => {
    if (playing) {
      pause();
    } else {
      play();
    }
  };

  return {
    get el() {
      return el;
    },
    get input() {
      return input;
    },
    get valueEl() {
      return valueEl;
    },
    get minEl() {
      return minEl;
    },
    get maxEl() {
      return maxEl;
    },
    get playBtn() {
      return playButton;
    },
    init,
    show,
    hide,
    setRange,
    getValue,
    setValue,
    on,
    off,
    play,
    pause,
    toggle,
  };
}
