const DEFAULT_PADDING = { top: 32, right: 24, bottom: 60, left: 70 };
const MIN_CANVAS_WIDTH = 400;
const MIN_CANVAS_HEIGHT = 260;
const LINE_WIDTH = 2;
const HIGHLIGHT_WIDTH = 3.5;
const SELECT_DISTANCE_PX = 8;
const DEPTH_CATEGORY = 'xs-distance';

function parseColor(value) {
  if (!value) {
    return [255, 204, 0];
  }
  const raw = String(value).trim();
  if (raw.startsWith('#')) {
    const hex = raw.slice(1);
    if (hex.length === 3) {
      const r = parseInt(hex[0] + hex[0], 16);
      const g = parseInt(hex[1] + hex[1], 16);
      const b = parseInt(hex[2] + hex[2], 16);
      return [r, g, b];
    }
    if (hex.length === 6) {
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      return [r, g, b];
    }
  }
  if (raw.startsWith('rgb')) {
    const parts = raw.replace(/rgba?\(|\)/g, '').split(',');
    const nums = parts.map((part) => Number(part.trim()));
    if (nums.length >= 3 && nums.slice(0, 3).every((num) => Number.isFinite(num))) {
      return [nums[0], nums[1], nums[2]];
    }
  }
  return [255, 204, 0];
}

export function buildStrokeStyle(color, alpha) {
  const [r, g, b] = parseColor(color);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function computeTicks(min, max, count) {
  const range = max - min;
  if (range === 0) {
    return [min];
  }
  const step = range / (count - 1);
  const ticks = [];
  for (let i = 0; i < count; i += 1) {
    ticks.push(min + step * i);
  }
  return [...new Set(ticks)];
}

function formatTick(value) {
  const abs = Math.abs(value);
  if (abs >= 10) {
    return value.toFixed(0);
  }
  if (abs >= 1) {
    return value.toFixed(1);
  }
  return value.toFixed(2);
}

function resolvePreferredUnit(unitPrefs, fallback) {
  if (unitPrefs && unitPrefs[DEPTH_CATEGORY]) {
    return unitPrefs[DEPTH_CATEGORY];
  }
  return fallback;
}

function resolveUnitLabel(unitizer, unitKey) {
  if (!unitizer || typeof unitizer.renderUnits !== 'function') {
    return unitKey;
  }
  const html = unitizer.renderUnits(unitKey);
  if (!html || typeof document === 'undefined') {
    return unitKey;
  }
  const wrapper = document.createElement('div');
  wrapper.innerHTML = html;
  const preferred = wrapper.querySelector('.unitizer:not(.invisible)');
  const text = preferred ? preferred.textContent : wrapper.textContent;
  return text && text.trim() ? text.trim() : unitKey;
}

function createDepthConverter(unitizer, preferredUnit) {
  if (!unitizer || typeof unitizer.convert !== 'function') {
    return (value) => value;
  }
  if (!preferredUnit || preferredUnit === 'mm') {
    return (value) => value;
  }
  return (value) => unitizer.convert(value, 'mm', preferredUnit);
}

export function createHyetographChart(options = {}) {
  const {
    container = document.querySelector('[data-storm-event-analyzer-chart]'),
    emptyEl = null,
    padding = DEFAULT_PADDING,
    unitizer = null,
    unitPrefs = null,
    onSelect = null,
  } = options;

  const chart = {
    container,
    emptyEl,
    canvas: null,
    ctx2d: null,
    _series: [],
    _selectedId: null,
    _padding: { ...padding },
    _unitizer: unitizer,
    _unitPrefs: unitPrefs,
    _onSelect: onSelect,
    _renderContext: null,

    init() {
      if (!this.container) return;
      this.container.style.position = 'relative';
      this.container.innerHTML = '';
      this.canvas = document.createElement('canvas');
      this.canvas.setAttribute('data-storm-event-analyzer-canvas', '');
      this.canvas.style.display = 'block';
      this.canvas.style.width = '100%';
      this.canvas.style.height = '100%';
      this.canvas.style.cursor = 'pointer';
      this.container.appendChild(this.canvas);
      this.ctx2d = this.canvas.getContext('2d');
      this.canvas.addEventListener('click', (event) => this._onCanvasClick(event));
      window.addEventListener('resize', () => {
        if (this._series.length) {
          this._resizeCanvas();
          this.render();
        }
      });
      this._resizeCanvas();
    },

    setSeries(series) {
      this._series = Array.isArray(series) ? series : [];
      this._renderContext = null;
      this._updateEmptyState();
      this._resizeCanvas();
      this.render();
    },

    setSelected(simDayIndex) {
      const next = simDayIndex == null ? null : String(simDayIndex);
      if (this._selectedId !== next) {
        this._selectedId = next;
        this.render();
      }
    },

    setUnitizer(unitizerClient, prefs) {
      this._unitizer = unitizerClient;
      if (prefs !== undefined) {
        this._unitPrefs = prefs;
      }
      this.render();
    },

    setUnitPrefs(prefs) {
      this._unitPrefs = prefs;
      this.render();
    },

    _updateEmptyState() {
      if (!this.emptyEl) return;
      if (this._series.length) {
        this.emptyEl.setAttribute('hidden', 'hidden');
      } else {
        this.emptyEl.removeAttribute('hidden');
      }
    },

    _resizeCanvas() {
      if (!this.canvas || !this.container) return;
      const rect = this.container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const width = Math.max(rect.width || 0, MIN_CANVAS_WIDTH);
      const height = Math.max(rect.height || 0, MIN_CANVAS_HEIGHT);
      this.canvas.width = width * dpr;
      this.canvas.height = height * dpr;
      this.canvas.style.width = `${width}px`;
      this.canvas.style.height = `${height}px`;
      if (this.ctx2d) {
        this.ctx2d.setTransform(1, 0, 0, 1, 0, 0);
        this.ctx2d.scale(dpr, dpr);
      }
    },

    _getTheme() {
      const root = getComputedStyle(document.documentElement);
      const text = root.getPropertyValue('--wc-color-text').trim() || '#e5e7eb';
      const muted = root.getPropertyValue('--wc-color-text-muted').trim() || '#94a3b8';
      const axis = root.getPropertyValue('--wc-color-border').trim() || '#334155';
      const grid =
        root.getPropertyValue('--wc-color-border-muted').trim() || 'rgba(148, 163, 184, 0.35)';
      const highlight = root.getPropertyValue('--wc-color-accent').trim() || '#ffcc00';
      return { text, muted, axis, grid, highlight };
    },

    render() {
      if (!this.ctx2d || !this.canvas) return;
      const ctx = this.ctx2d;
      const dpr = window.devicePixelRatio || 1;
      const width = this.canvas.width / dpr;
      const height = this.canvas.height / dpr;
      ctx.clearRect(0, 0, width, height);

      if (!this._series.length) {
        return;
      }

      const theme = this._getTheme();
      const pad = { ...this._padding, bottom: Math.max(this._padding.bottom, 60) };
      const plotWidth = width - pad.left - pad.right;
      const plotHeight = height - pad.top - pad.bottom;

      const preferredUnit = resolvePreferredUnit(this._unitPrefs, 'mm');
      const convertDepth = createDepthConverter(this._unitizer, preferredUnit);
      const unitLabel = resolveUnitLabel(this._unitizer, 'mm');

      let xMax = 0;
      let yMax = 0;
      const seriesData = this._series.map((series) => {
        const points = series.points.map((point) => ({
          x: point.elapsed_hours,
          y: convertDepth(point.cumulative_depth_mm),
        }));
        points.forEach((point) => {
          if (Number.isFinite(point.x) && point.x > xMax) {
            xMax = point.x;
          }
          if (Number.isFinite(point.y) && point.y > yMax) {
            yMax = point.y;
          }
        });
        return { id: String(series.sim_day_index), points };
      });

      if (!Number.isFinite(xMax) || xMax <= 0) {
        xMax = 1;
      }
      if (!Number.isFinite(yMax) || yMax <= 0) {
        yMax = 1;
      }

      const yPad = yMax * 0.1 || 1;
      yMax += yPad;

      const xScale = (value) => pad.left + (value / xMax) * plotWidth;
      const yScale = (value) => pad.top + plotHeight - (value / yMax) * plotHeight;

      ctx.strokeStyle = theme.axis;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top);
      ctx.lineTo(pad.left, height - pad.bottom);
      ctx.lineTo(width - pad.right, height - pad.bottom);
      ctx.stroke();

      ctx.fillStyle = theme.muted;
      ctx.font = '13px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      const xTicks = computeTicks(0, xMax, 6);
      xTicks.forEach((tick) => {
        const x = xScale(tick);
        ctx.beginPath();
        ctx.moveTo(x, height - pad.bottom);
        ctx.lineTo(x, height - pad.bottom + 4);
        ctx.stroke();
        ctx.fillText(formatTick(tick), x, height - pad.bottom + 6);
      });

      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      const yTicks = computeTicks(0, yMax, 5);
      yTicks.forEach((tick) => {
        const y = yScale(tick);
        ctx.beginPath();
        ctx.moveTo(pad.left - 4, y);
        ctx.lineTo(pad.left, y);
        ctx.stroke();
        ctx.fillText(formatTick(tick), pad.left - 6, y);
        ctx.strokeStyle = theme.grid;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(width - pad.right, y);
        ctx.stroke();
        ctx.strokeStyle = theme.axis;
      });

      ctx.fillStyle = theme.muted;
      ctx.font = '14px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText('Elapsed time (hours)', pad.left + plotWidth / 2, height - 22);

      ctx.save();
      ctx.translate(12, pad.top + plotHeight / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillStyle = theme.muted;
      ctx.font = '14px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(`Cumulative depth (${unitLabel})`, 0, 0);
      ctx.restore();

      const highlightColor = buildStrokeStyle(theme.highlight, 1);
      const mutedColor = buildStrokeStyle(theme.highlight, 0.4);
      const selectedId = this._selectedId;

      this._renderContext = {
        series: seriesData.map((series) => ({
          id: series.id,
          points: series.points.map((point) => ({
            x: xScale(point.x),
            y: yScale(point.y),
          })),
        })),
        bounds: {
          left: pad.left,
          right: width - pad.right,
          top: pad.top,
          bottom: height - pad.bottom,
        },
      };

      seriesData.forEach((series) => {
        if (selectedId && series.id === selectedId) {
          return;
        }
        this._drawLine(ctx, series.points, xScale, yScale, mutedColor, LINE_WIDTH);
      });

      if (selectedId) {
        const selected = seriesData.find((series) => series.id === selectedId);
        if (selected) {
          this._drawLine(ctx, selected.points, xScale, yScale, highlightColor, HIGHLIGHT_WIDTH);
        }
      } else {
        seriesData.forEach((series) => {
          this._drawLine(ctx, series.points, xScale, yScale, highlightColor, LINE_WIDTH);
        });
      }
    },

    _drawLine(ctx, points, xScale, yScale, color, width) {
      ctx.strokeStyle = color;
      ctx.lineWidth = width;
      ctx.beginPath();
      let started = false;
      points.forEach((point) => {
        if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) {
          return;
        }
        const x = xScale(point.x);
        const y = yScale(point.y);
        if (!started) {
          ctx.moveTo(x, y);
          started = true;
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.stroke();
    },

    _onCanvasClick(event) {
      if (!this._renderContext || !this.canvas) {
        return;
      }
      if (typeof this._onSelect !== 'function') {
        return;
      }
      const rect = this.canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const bounds = this._renderContext.bounds;
      if (x < bounds.left || x > bounds.right || y < bounds.top || y > bounds.bottom) {
        return;
      }

      let bestId = null;
      let bestDistance = SELECT_DISTANCE_PX;

      this._renderContext.series.forEach((series) => {
        const points = series.points || [];
        for (let i = 0; i < points.length - 1; i += 1) {
          const a = points[i];
          const b = points[i + 1];
          const distance = this._distanceToSegment(x, y, a.x, a.y, b.x, b.y);
          if (distance < bestDistance) {
            bestDistance = distance;
            bestId = series.id;
          }
        }
      });

      if (bestId !== null) {
        this._onSelect(Number(bestId));
      }
    },

    _distanceToSegment(px, py, ax, ay, bx, by) {
      const dx = bx - ax;
      const dy = by - ay;
      if (dx === 0 && dy === 0) {
        return Math.hypot(px - ax, py - ay);
      }
      const t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy);
      const clamped = Math.max(0, Math.min(1, t));
      const cx = ax + clamped * dx;
      const cy = ay + clamped * dy;
      return Math.hypot(px - cx, py - cy);
    },
  };

  return chart;
}
