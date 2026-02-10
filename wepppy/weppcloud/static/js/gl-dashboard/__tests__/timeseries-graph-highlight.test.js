import { describe, expect, it, jest } from '@jest/globals';
import { createTimeseriesGraph } from '../graphs/timeseries-graph.js';

describe('gl-dashboard timeseries graph highlight IDs', () => {
  it('emits composite feature keys as strings (no numeric coercion)', () => {
    const onHighlightSubcatchment = jest.fn();
    const graph = createTimeseriesGraph({
      container: document.createElement('div'),
      emptyEl: document.createElement('div'),
      tooltipEl: document.createElement('div'),
      panelEl: document.createElement('div'),
      onHighlightSubcatchment,
    });

    graph.canvas = {
      getBoundingClientRect: () => ({ left: 0, top: 0 }),
    };
    graph.tooltipEl = document.createElement('div');
    graph.render = jest.fn();
    graph._plotBounds = { left: 0, right: 100, top: 0, bottom: 100 };
    graph._xScale = () => 50;
    graph._yScale = () => 50;
    graph._data = {
      type: 'line',
      years: [2000],
      series: {
        'batch;;spring-2025;;run-001-12': { values: [1], color: [0, 0, 0, 255] },
      },
    };

    graph._onCanvasHover({ clientX: 50, clientY: 50 });

    expect(onHighlightSubcatchment).toHaveBeenCalledTimes(1);
    expect(onHighlightSubcatchment).toHaveBeenLastCalledWith('batch;;spring-2025;;run-001-12');
  });

  it('emits numeric series IDs as strings for consistent comparisons', () => {
    const onHighlightSubcatchment = jest.fn();
    const graph = createTimeseriesGraph({
      container: document.createElement('div'),
      emptyEl: document.createElement('div'),
      tooltipEl: document.createElement('div'),
      panelEl: document.createElement('div'),
      onHighlightSubcatchment,
    });

    graph.canvas = {
      getBoundingClientRect: () => ({ left: 0, top: 0 }),
    };
    graph.tooltipEl = document.createElement('div');
    graph.render = jest.fn();
    graph._plotBounds = { left: 0, right: 100, top: 0, bottom: 100 };
    graph._xScale = () => 40;
    graph._yScale = () => 40;
    graph._data = {
      type: 'line',
      years: [2000],
      series: {
        10: { values: [1], color: [0, 0, 0, 255] },
      },
    };

    graph._onCanvasHover({ clientX: 40, clientY: 40 });

    expect(onHighlightSubcatchment).toHaveBeenCalledTimes(1);
    expect(onHighlightSubcatchment).toHaveBeenLastCalledWith('10');
  });
});

