import { YEAR_SLIDER_CONTEXTS } from '../config.js';

/**
 * @typedef {Object} MonthSliderElements
 * @property {HTMLElement | null} el
 * @property {HTMLInputElement | null} input
 * @property {HTMLElement | null} valueEl
 * @property {HTMLElement | null} minEl
 * @property {HTMLElement | null} maxEl
 * @property {HTMLElement | null} playBtn
 */

/**
 * @typedef {Object} MonthSliderController
 * @property {HTMLElement | null} el
 * @property {HTMLInputElement | null} input
 * @property {HTMLElement | null} valueEl
 * @property {HTMLElement | null} minEl
 * @property {HTMLElement | null} maxEl
 * @property {HTMLElement | null} playBtn
 * @property {(items: any[], currentIndex?: number) => void} setRange
 * @property {() => number} getValue
 * @property {(index: number) => void} setValue
 * @property {(event: 'change', callback: (index: number) => void) => void} on
 * @property {(event: 'change', callback: (index: number) => void) => void} off
 * @property {() => void} play
 * @property {() => void} pause
 * @property {() => void} toggle
 * @property {(ctx?: import('../config.js').YearSliderContext) => void} show
 * @property {() => void} hide
 */

/**
 * Month slider controller. Mirrors year slider behavior but uses item indexes + labels.
 * @param {MonthSliderElements & { formatLabel?: (item: any, index: number) => string }} params
 * @returns {MonthSliderController}
 */
export function createMonthSlider({
  el,
  input,
  valueEl,
  minEl,
  maxEl,
  playBtn,
  formatLabel,
}) {
  let listeners = [];
  let visible = false;
  let items = [];
  let minIndex = 0;
  let maxIndex = 0;
  let currentIndex = 0;
  let initialized = false;
  let playing = false;
  let intervalId = null;
  let playButton = playBtn || null;
  const VALID_CONTEXTS = Object.values(YEAR_SLIDER_CONTEXTS);

  const normalizeContext = (ctx) => (VALID_CONTEXTS.includes(ctx) ? ctx : YEAR_SLIDER_CONTEXTS.LAYER);

  function formatItem(item, index) {
    if (typeof formatLabel === 'function') {
      return formatLabel(item, index);
    }
    if (item && typeof item === 'object' && 'label' in item) {
      return String(item.label);
    }
    if (item != null) {
      return String(item);
    }
    return '';
  }

  const updateDisplay = () => {
    if (valueEl) {
      valueEl.textContent = formatItem(items[currentIndex], currentIndex);
    }
  };

  const updateRangeLabels = () => {
    if (minEl) {
      minEl.textContent = items.length ? formatItem(items[minIndex], minIndex) : '';
    }
    if (maxEl) {
      maxEl.textContent = items.length ? formatItem(items[maxIndex], maxIndex) : '';
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

  const init = () => {
    if (!el || !input || initialized) return;
    initialized = true;
    playButton = playButton || playBtn || null;

    input.addEventListener('input', () => {
      let next = parseInt(input.value, 10);
      if (!Number.isFinite(next)) {
        next = minIndex;
      }
      next = Math.max(minIndex, Math.min(maxIndex, next));
      currentIndex = next;
      updateDisplay();
      emit('change', currentIndex);
    });

    if (playButton) {
      playButton.addEventListener('click', () => toggle());
    }
  };

  const setRange = (nextItems, current) => {
    if (!initialized) {
      init();
    }
    items = Array.isArray(nextItems) ? nextItems.slice() : [];
    minIndex = 0;
    maxIndex = Math.max(0, items.length - 1);
    currentIndex = Number.isFinite(current) ? current : maxIndex;
    if (currentIndex < minIndex || currentIndex > maxIndex) {
      currentIndex = maxIndex;
    }
    if (input) {
      input.min = String(minIndex);
      input.max = String(maxIndex);
      input.value = String(currentIndex);
    }
    updateRangeLabels();
    updateDisplay();
  };

  const getValue = () => currentIndex;

  const setValue = (index) => {
    if (!Number.isFinite(index)) return;
    currentIndex = Math.max(minIndex, Math.min(maxIndex, index));
    if (input) input.value = String(currentIndex);
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
      let next = currentIndex + 1;
      if (next > maxIndex) {
        next = minIndex;
      }
      currentIndex = next;
      if (input) input.value = String(next);
      updateDisplay();
      emit('change', currentIndex);
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

  const show = (ctx = YEAR_SLIDER_CONTEXTS.LAYER) => {
    if (!el) return;
    const resolvedContext = normalizeContext(ctx);
    const container = document.getElementById('gl-graph-container');
    const slot = document.getElementById('gl-graph-year-slider');
    const target =
      resolvedContext === YEAR_SLIDER_CONTEXTS.CLIMATE ? (container || slot) : (slot || container);
    if (target && el.parentElement !== target) {
      target.appendChild(el);
    }
    el.classList.add('is-visible');
    visible = true;
  };

  const hide = () => {
    if (el && visible) {
      el.classList.remove('is-visible');
      visible = false;
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
    setRange,
    getValue,
    setValue,
    on,
    off,
    play,
    pause,
    toggle,
    show,
    hide,
  };
}
