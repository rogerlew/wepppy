import { DEFAULT_GRAPH_PADDING } from '../config.js';
import { getState, setValue } from '../state.js';

/**
 * Canvas-based timeseries graph controller (line, box, bars).
 * Handles rendering, hover tooltips, resize scaling, and legend display.
 */
export function createTimeseriesGraph(options = {}) {
  const state = getState();
  const {
    container = document.getElementById('gl-graph-container'),
    emptyEl = document.getElementById('gl-graph-empty'),
    tooltipEl = document.getElementById('gl-graph-tooltip'),
    panelEl = document.getElementById('gl-graph'),
    padding = DEFAULT_GRAPH_PADDING,
    getGraphFocus,
    setGraphFocus,
    onPanelToggle,
    onHighlightSubcatchment,
  } = options;

  const resolveGraphFocus = () =>
    typeof getGraphFocus === 'function' ? getGraphFocus() : state.graphFocus;
  const notifyPanelToggle = (visible) => {
    if (typeof onPanelToggle === 'function') {
      onPanelToggle(visible);
    } else if (typeof window.glDashboardGraphToggled === 'function') {
      window.glDashboardGraphToggled(visible);
    }
  };
  const notifyHighlight = (topazId) => {
    if (typeof onHighlightSubcatchment === 'function') {
      onHighlightSubcatchment(topazId);
    } else if (typeof window.glDashboardHighlightSubcatchment === 'function') {
      window.glDashboardHighlightSubcatchment(topazId);
    }
  };

  const timeseriesGraph = {
    canvas: null,
    ctx2d: null,
    container,
    emptyEl,
    _emptyDefault: '',
    tooltipEl,
    _visible: false,
    _data: null,
    _highlightedId: null,
    _hoveredId: null,
    _currentYear: null,
    _source: null,
    _tooltipFormatter: null,
    _padding: { ...padding },
    _lineWidth: 1.5,
    _highlightWidth: 3,

    init() {
      this.canvas = document.getElementById('gl-graph-canvas');
      if (this.emptyEl) {
        this.emptyEl.textContent = '';
      }
      if (this.canvas) {
        this.ctx2d = this.canvas.getContext('2d');
        this.canvas.addEventListener('mousemove', (e) => this._onCanvasHover(e));
        this.canvas.addEventListener('mouseleave', () => this._onCanvasLeave());
        window.addEventListener('resize', () => {
          if (this._visible && this._data) {
            this._resizeCanvas();
            this.render();
          }
        });
      }
    },

    show() {
      if (this.container) {
        this.container.style.display = 'block';
      }
      if (this.emptyEl) {
        this.emptyEl.style.display = 'none';
        this.emptyEl.textContent = '';
      }
      this._visible = true;
      this._resizeCanvas();
    },

    hide() {
      if (this.container) {
        this.container.style.display = 'none';
      }
      if (this.emptyEl) {
        this.emptyEl.textContent = this._emptyDefault;
        this.emptyEl.style.display = 'block';
      }
      this._visible = false;
      this._data = null;
      this._currentYear = null;
      this._source = null;
      this._tooltipFormatter = null;
    },

    _resizeCanvas() {
      if (!this.canvas || !this.container) return;
      const rect = this.container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const width = Math.max(rect.width, 400);
      const height = resolveGraphFocus() ? Math.max(rect.height * 0.8 || 0, 320) : 200;
      this.canvas.width = width * dpr;
      this.canvas.height = height * dpr;
      this.canvas.style.width = width + 'px';
      this.canvas.style.height = height + 'px';
      if (this.ctx2d) {
        this.ctx2d.setTransform(1, 0, 0, 1, 0, 0);
        this.ctx2d.scale(dpr, dpr);
      }
    },

    setData(data) {
      const state = getState();
      if (state && state.rapCumulativeMode && data && data.source === 'omni') {
        return;
      }
      this._data = data;
      const headerEl = document.querySelector('#gl-graph h4');
      if (headerEl) {
        headerEl.textContent = data && data.title ? data.title : 'Graph';
      }
      this._currentYear = data && data.currentYear != null ? data.currentYear : null;
      this._source = data && data.source ? data.source : null;
      this._tooltipFormatter =
        data && typeof data.tooltipFormatter === 'function' ? data.tooltipFormatter : null;
      if (this._hasData(data)) {
        if (panelEl && panelEl.classList.contains('is-collapsed')) {
          panelEl.classList.remove('is-collapsed');
          notifyPanelToggle(true);
        }
        if (typeof setGraphFocus === 'function') {
          setGraphFocus(data.source === 'omni');
        } else {
          setValue('graphFocus', data.source === 'omni');
        }
        this.show();
        this.render();
      } else {
        this.hide();
      }
    },

    setCurrentYear(year) {
      this._currentYear = year;
      if (this._visible && this._data) {
        this.render();
      }
    },

    highlightSubcatchment(topazId) {
      if (this._highlightedId !== topazId) {
        this._highlightedId = topazId;
        if (this._visible && this._data) {
          this.render();
        }
      }
    },

    clearHighlight() {
      if (this._highlightedId !== null) {
        this._highlightedId = null;
        if (this._visible && this._data) {
          this.render();
        }
      }
    },

    render() {
      if (!this.ctx2d || !this._data) return;
      const type = this._data.type || 'line';
      if (type === 'boxplot') {
        return this._renderBoxplot();
      }
      if (type === 'bars') {
        return this._renderBars();
      }
      return this._renderLine();
    },

    _hasData(data) {
      if (!data) return false;
      const type = data.type || 'line';
      if (type === 'boxplot') {
        return Array.isArray(data.series) && data.series.some((s) => s && s.stats);
      }
      if (type === 'bars') {
        return (
          Array.isArray(data.series) &&
          data.series.length &&
          Array.isArray(data.categories) &&
          data.categories.length
        );
      }
      return data.years && data.series && Object.keys(data.series).length > 0;
    },

    _renderLine() {
      if (!this.ctx2d || !this._data || !this._data.years || !this._data.series) return;
      const theme = this._getTheme();
      const ctx = this.ctx2d;
      const dpr = window.devicePixelRatio || 1;
      const width = this.canvas.width / dpr;
      const height = this.canvas.height / dpr;
      const pad = { ...this._padding, bottom: Math.max(this._padding.bottom, 60) };
      const plotWidth = width - pad.left - pad.right;
      const plotHeight = height - pad.top - pad.bottom;

      ctx.clearRect(0, 0, width, height);

      const years = this._data.years;
      const series = this._data.series;
      const seriesIds = Object.keys(series);
      if (years.length === 0 || seriesIds.length === 0) return;

      const xMin = Math.min(...years);
      const xMax = Math.max(...years);
      const xRange = xMax - xMin || 1;
      const xScale = (yr) => pad.left + ((yr - xMin) / xRange) * plotWidth;

      let yMin = Infinity;
      let yMax = -Infinity;
      for (const id of seriesIds) {
        for (const v of series[id].values) {
          if (v != null && isFinite(v)) {
            if (v < yMin) yMin = v;
            if (v > yMax) yMax = v;
          }
        }
      }
      if (!isFinite(yMin)) yMin = 0;
      if (!isFinite(yMax)) yMax = 100;
      const yPad = (yMax - yMin) * 0.1 || 5;
      yMin = Math.max(0, yMin - yPad);
      yMax = yMax + yPad;
      const yRange = yMax - yMin || 1;
      const yScale = (v) => pad.top + plotHeight - ((v - yMin) / yRange) * plotHeight;

      this._xScale = xScale;
      this._yScale = yScale;
      this._plotBounds = {
        left: pad.left,
        right: width - pad.right,
        top: pad.top,
        bottom: height - pad.bottom,
      };
      this._yMin = yMin;
      this._yMax = yMax;

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
      const xTicks = this._computeTicks(xMin, xMax, 6, true);
      for (const tick of xTicks) {
        const x = xScale(tick);
        ctx.beginPath();
        ctx.moveTo(x, height - pad.bottom);
        ctx.lineTo(x, height - pad.bottom + 4);
        ctx.stroke();
        ctx.fillText(String(tick), x, height - pad.bottom + 6);
      }

      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      const yTicks = this._computeTicks(yMin, yMax, 5, false);
      for (const tick of yTicks) {
        const y = yScale(tick);
        ctx.beginPath();
        ctx.moveTo(pad.left - 4, y);
        ctx.lineTo(pad.left, y);
        ctx.stroke();
        ctx.fillText(tick.toFixed(0), pad.left - 6, y);
        ctx.strokeStyle = theme.grid;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(width - pad.right, y);
        ctx.stroke();
        ctx.strokeStyle = theme.axis;
      }

      if (this._data.xLabel) {
        ctx.fillStyle = theme.muted;
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(this._data.xLabel, pad.left + plotWidth / 2, height - 12);
      }

      if (this._data.yLabel) {
        ctx.save();
        ctx.translate(12, pad.top + plotHeight / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillStyle = theme.muted;
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(this._data.yLabel, 0, 0);
        ctx.restore();
      }

      const highlightId = this._highlightedId || this._hoveredId;
      for (const id of seriesIds) {
        if (id === String(highlightId)) continue;
        this._drawLine(ctx, years, series[id], xScale, yScale, false);
      }

      if (highlightId && series[String(highlightId)]) {
        this._drawLine(ctx, years, series[String(highlightId)], xScale, yScale, true);
      }

      if (this._currentYear && this._currentYear >= xMin && this._currentYear <= xMax) {
        const x = xScale(this._currentYear);
        ctx.strokeStyle = '#ffcc00';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(x, pad.top);
        ctx.lineTo(x, height - pad.bottom);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      if (this._data && this._data.source === 'omni') {
        const legendItems = seriesIds.map((id) => {
          const s = series[id] || {};
          return {
            label: s.label || id,
            color: s.color || [100, 150, 200, 180],
            id,
          };
        });
        if (legendItems.length) {
          const legendX = width - pad.right + 10;
          let legendY = pad.top;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.font = '13px sans-serif';
          legendItems.forEach((item) => {
            const color = item.color;
            ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.9)`;
            ctx.fillRect(legendX, legendY, 14, 14);
            ctx.fillStyle = theme.text;
            ctx.fillText(item.label, legendX + 18, legendY + 7);
            legendY += 18;
          });
        }
      }
    },

    _renderBoxplot() {
      if (!this.ctx2d || !this._data || !Array.isArray(this._data.series)) return;
      const series = this._data.series.filter((s) => s && s.stats);
      if (!series.length) return;
      const theme = this._getTheme();
      const ctx = this.ctx2d;
      const dpr = window.devicePixelRatio || 1;
      const width = this.canvas.width / dpr;
      const height = this.canvas.height / dpr;
      const pad = { ...this._padding, bottom: Math.max(this._padding.bottom, 200) };
      const plotWidth = width - pad.left - pad.right;
      const plotHeight = height - pad.top - pad.bottom;

      ctx.clearRect(0, 0, width, height);

      let yMin = Infinity;
      let yMax = -Infinity;
      for (const s of series) {
        const stats = s.stats;
        yMin = Math.min(yMin, stats.min);
        yMax = Math.max(yMax, stats.max);
      }
      if (!isFinite(yMin)) yMin = 0;
      if (!isFinite(yMax)) yMax = 1;
      const yPad = (yMax - yMin) * 0.1 || 5;
      yMin = yMin - yPad;
      yMax = yMax + yPad;
      const yRange = yMax - yMin || 1;
      const yScale = (v) => pad.top + plotHeight - ((v - yMin) / yRange) * plotHeight;

      ctx.strokeStyle = theme.axis;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top);
      ctx.lineTo(pad.left, height - pad.bottom);
      ctx.lineTo(width - pad.right, height - pad.bottom);
      ctx.stroke();

      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = theme.muted;
      ctx.font = '15px sans-serif';
      const yTicks = this._computeTicks(yMin, yMax, 5, false);
      for (const tick of yTicks) {
        const y = yScale(tick);
        ctx.beginPath();
        ctx.moveTo(pad.left - 4, y);
        ctx.lineTo(pad.left, y);
        ctx.stroke();
        ctx.fillText(tick.toFixed(1), pad.left - 6, y);
        ctx.strokeStyle = theme.grid;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(width - pad.right, y);
        ctx.stroke();
        ctx.strokeStyle = theme.axis;
      }

      if (this._data.yLabel) {
        ctx.save();
        ctx.translate(12, pad.top + plotHeight / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillStyle = theme.muted;
        ctx.font = '16px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(this._data.yLabel, 0, 0);
        ctx.restore();
      }

      const boxWidth = Math.max(20, Math.min(60, plotWidth / Math.max(series.length * 1.5, 1)));
      const gap = (plotWidth - boxWidth * series.length) / (series.length + 1);
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = theme.text;
      ctx.font = '16px sans-serif';

      series.forEach((s, idx) => {
        const xCenter = pad.left + gap * (idx + 1) + boxWidth * idx + boxWidth / 2;
        const { min, q1, median, q3, max } = s.stats;
        const color = s.color || [99, 179, 237];
        const rgba = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.85)`;

        const yMinPos = yScale(min);
        const yMaxPos = yScale(max);
        const yQ1 = yScale(q1);
        const yQ3 = yScale(q3);
        const yMedian = yScale(median);

        ctx.strokeStyle = rgba;
        ctx.fillStyle = rgba;
        ctx.lineWidth = 1.5;

        ctx.beginPath();
        ctx.moveTo(xCenter, yMaxPos);
        ctx.lineTo(xCenter, yQ3);
        ctx.moveTo(xCenter, yQ1);
        ctx.lineTo(xCenter, yMinPos);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(xCenter - boxWidth * 0.3, yMaxPos);
        ctx.lineTo(xCenter + boxWidth * 0.3, yMaxPos);
        ctx.moveTo(xCenter - boxWidth * 0.3, yMinPos);
        ctx.lineTo(xCenter + boxWidth * 0.3, yMinPos);
        ctx.stroke();

        ctx.fillRect(xCenter - boxWidth / 2, yQ3, boxWidth, yQ1 - yQ3);
        ctx.strokeRect(xCenter - boxWidth / 2, yQ3, boxWidth, yQ1 - yQ3);

        ctx.strokeStyle = '#0f172a';
        ctx.beginPath();
        ctx.moveTo(xCenter - boxWidth / 2, yMedian);
        ctx.lineTo(xCenter + boxWidth / 2, yMedian);
        ctx.stroke();

        ctx.save();
        ctx.translate(xCenter, height - pad.bottom + 26);
        ctx.rotate(-Math.PI / 4);
        ctx.fillStyle = theme.text;
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(s.label || `S${idx + 1}`, 0, 0);
        ctx.restore();
      });
    },

    _renderBars() {
      if (
        !this.ctx2d ||
        !this._data ||
        !Array.isArray(this._data.categories) ||
        !Array.isArray(this._data.series)
      )
        return;
      const categories = this._data.categories;
      const series = this._data.series;
      if (!categories.length || !series.length) return;

      const theme = this._getTheme();
      const ctx = this.ctx2d;
      const dpr = window.devicePixelRatio || 1;
      const width = this.canvas.width / dpr;
      const height = this.canvas.height / dpr;
      const pad = this._padding;
      const plotWidth = width - pad.left - pad.right - 80;
      const plotHeight = height - pad.top - pad.bottom;

      ctx.clearRect(0, 0, width, height);

      let yMax = 0;
      for (const s of series) {
        for (const v of s.values) {
          if (v != null && isFinite(v)) {
            if (v > yMax) yMax = v;
          }
        }
      }
      yMax = yMax || 1;
      const yPad = yMax * 0.1;
      const yScale = (v) => pad.top + plotHeight - (v / (yMax + yPad)) * plotHeight;

      ctx.strokeStyle = theme.axis;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top);
      ctx.lineTo(pad.left, height - pad.bottom);
      ctx.lineTo(pad.left + plotWidth, height - pad.bottom);
      ctx.stroke();

      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = theme.muted;
      ctx.font = '13px sans-serif';
      const yTicks = this._computeTicks(0, yMax, 5, false);
      for (const tick of yTicks) {
        const y = yScale(tick);
        ctx.beginPath();
        ctx.moveTo(pad.left - 4, y);
        ctx.lineTo(pad.left, y);
        ctx.stroke();
        ctx.fillText(tick.toFixed(1), pad.left - 6, y);
        ctx.strokeStyle = theme.grid;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(pad.left + plotWidth, y);
        ctx.stroke();
        ctx.strokeStyle = theme.axis;
      }

      const groupWidth = plotWidth / Math.max(categories.length, 1);
      const barWidth = Math.max(6, Math.min(24, groupWidth / Math.max(series.length, 1) - 4));

      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = theme.text;
      ctx.font = '13px sans-serif';

      categories.forEach((cat, idx) => {
        const groupStart = pad.left + groupWidth * idx + groupWidth * 0.1;
        series.forEach((s, sIdx) => {
          const val = s.values[idx];
          if (val == null || !isFinite(val)) return;
          const color = s.color || [99, 179, 237];
          const x = groupStart + sIdx * (barWidth + 4);
          const y = yScale(val);
          const h = height - pad.bottom - y;
          ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.8)`;
          ctx.fillRect(x, y, barWidth, h);
        });
        ctx.fillStyle = theme.text;
        ctx.fillText(
          String(cat),
          groupStart + ((barWidth + 4) * series.length) / 2,
          height - pad.bottom + 6
        );
      });

      const legendX = pad.left + plotWidth + 10;
      let legendY = pad.top;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.font = '13px sans-serif';
      series.forEach((s) => {
        const color = s.color || [99, 179, 237];
        ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.9)`;
        ctx.fillRect(legendX, legendY, 14, 14);
        ctx.fillStyle = theme.text;
        ctx.fillText(s.label || 'Series', legendX + 18, legendY + 7);
        legendY += 18;
      });

      if (this._data.yLabel) {
        ctx.save();
        ctx.translate(12, pad.top + plotHeight / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillStyle = theme.muted;
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(this._data.yLabel, 0, 0);
        ctx.restore();
      }
    },

    _drawLine(ctx, years, seriesData, xScale, yScale, highlighted) {
      const values = seriesData.values;
      const color = seriesData.color || [100, 150, 200, 180];
      ctx.strokeStyle = highlighted
        ? `rgba(${color[0]}, ${color[1]}, ${color[2]}, 1)`
        : `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.5)`;
      ctx.lineWidth = highlighted ? this._highlightWidth : this._lineWidth;
      ctx.beginPath();
      let started = false;
      for (let i = 0; i < years.length; i++) {
        const v = values[i];
        if (v == null || !isFinite(v)) continue;
        const x = xScale(years[i]);
        const y = yScale(v);
        if (!started) {
          ctx.moveTo(x, y);
          started = true;
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
    },

    _computeTicks(min, max, count, integers) {
      const range = max - min;
      if (range === 0) return [min];
      const step = range / (count - 1);
      const ticks = [];
      for (let i = 0; i < count; i++) {
        let tick = min + step * i;
        if (integers) tick = Math.round(tick);
        ticks.push(tick);
      }
      return [...new Set(ticks)];
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

    _onCanvasHover(e) {
      if (!this._data || (this._data.type && this._data.type !== 'line')) return;
      if (!this._xScale || !this._plotBounds) return;
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const bounds = this._plotBounds;

      if (x < bounds.left || x > bounds.right || y < bounds.top || y > bounds.bottom) {
        this._onCanvasLeave();
        return;
      }

      const years = this._data.years;
      const series = this._data.series;
      const seriesIds = Object.keys(series);
      let closestId = null;
      let closestDist = Infinity;
      let closestValue = null;
      let closestYear = null;

      for (const id of seriesIds) {
        const values = series[id].values;
        for (let i = 0; i < years.length; i++) {
          const v = values[i];
          if (v == null || !isFinite(v)) continue;
          const px = this._xScale(years[i]);
          const py = this._yScale(v);
          const dist = Math.sqrt((px - x) ** 2 + (py - y) ** 2);
          if (dist < closestDist && dist < 20) {
            closestDist = dist;
            closestId = id;
            closestValue = v;
            closestYear = years[i];
          }
        }
      }

      if (closestId !== this._hoveredId) {
        this._hoveredId = closestId;
        this.render();
      }

      if (closestId && this.tooltipEl) {
        this.tooltipEl.style.display = 'block';
        this.tooltipEl.style.left = `${x + 10}px`;
        this.tooltipEl.style.top = `${y - 10}px`;
        if (this._tooltipFormatter) {
          this.tooltipEl.textContent = this._tooltipFormatter(closestId, closestValue, closestYear);
        } else {
          this.tooltipEl.textContent = `Hillslope ${closestId}: ${closestValue.toFixed(
            1
          )}% (${closestYear})`;
        }
      }

      notifyHighlight(closestId ? parseInt(closestId, 10) : null);
    },

    _onCanvasLeave() {
      this._hoveredId = null;
      if (this.tooltipEl) {
        this.tooltipEl.style.display = 'none';
      }
      if (this._visible && this._data) {
        this.render();
      }
      notifyHighlight(null);
    },
  };

  return timeseriesGraph;
}
