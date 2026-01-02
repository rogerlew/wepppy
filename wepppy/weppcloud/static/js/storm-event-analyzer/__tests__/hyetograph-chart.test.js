import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { createHyetographChart } from '../charts/hyetograph.js';

function createMockContext(strokes) {
  const ctx = {
    beginPath: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    stroke: jest.fn(() => {
      strokes.push({ strokeStyle: ctx.strokeStyle, lineWidth: ctx.lineWidth });
    }),
    clearRect: jest.fn(),
    fillText: jest.fn(),
    save: jest.fn(),
    restore: jest.fn(),
    translate: jest.fn(),
    rotate: jest.fn(),
    scale: jest.fn(),
    setTransform: jest.fn(),
  };

  ctx.strokeStyle = '';
  ctx.lineWidth = 1;
  ctx.fillStyle = '';
  ctx.font = '';
  ctx.textAlign = '';
  ctx.textBaseline = '';

  return ctx;
}

describe('storm-event-analyzer hyetograph chart styling', () => {
  let originalGetContext;

  beforeEach(() => {
    originalGetContext = HTMLCanvasElement.prototype.getContext;
  });

  afterEach(() => {
    HTMLCanvasElement.prototype.getContext = originalGetContext;
    document.body.innerHTML = '';
  });

  it('emphasizes the selected series stroke', () => {
    const strokes = [];
    const ctx = createMockContext(strokes);
    HTMLCanvasElement.prototype.getContext = jest.fn(() => ctx);

    const container = document.createElement('div');
    container.getBoundingClientRect = () => ({ width: 640, height: 300 });
    document.body.appendChild(container);

    const chart = createHyetographChart({ container });
    chart.init();
    chart.setSeries([
      {
        sim_day_index: 101,
        points: [
          { elapsed_hours: 0, cumulative_depth_mm: 0 },
          { elapsed_hours: 2, cumulative_depth_mm: 20 },
        ],
      },
      {
        sim_day_index: 202,
        points: [
          { elapsed_hours: 0, cumulative_depth_mm: 0 },
          { elapsed_hours: 2, cumulative_depth_mm: 25 },
        ],
      },
    ]);
    chart.setSelected(202);

    const seriesStrokes = strokes.filter((stroke) => stroke.lineWidth >= 2);
    const highlight = seriesStrokes.find((stroke) => stroke.lineWidth === 3.5);
    const normal = seriesStrokes.find((stroke) => stroke.lineWidth === 2);

    expect(highlight).toBeTruthy();
    expect(normal).toBeTruthy();
    expect(highlight.strokeStyle).toMatch(/rgba\(\d+, \d+, \d+, 1\)/);
    expect(normal.strokeStyle).toMatch(/rgba\(\d+, \d+, \d+, 0\.4\)/);
  });

  it('selects an event when clicking near a line', () => {
    const strokes = [];
    const ctx = createMockContext(strokes);
    HTMLCanvasElement.prototype.getContext = jest.fn(() => ctx);

    const container = document.createElement('div');
    container.getBoundingClientRect = () => ({ width: 640, height: 300 });
    document.body.appendChild(container);

    const onSelect = jest.fn();
    const chart = createHyetographChart({ container, onSelect });
    chart.init();
    chart.setSeries([
      {
        sim_day_index: 101,
        points: [
          { elapsed_hours: 0, cumulative_depth_mm: 0 },
          { elapsed_hours: 2, cumulative_depth_mm: 20 },
        ],
      },
    ]);

    chart.canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 640, height: 300 });
    const targetPoint = chart._renderContext.series[0].points[1];
    chart._onCanvasClick({ clientX: targetPoint.x, clientY: targetPoint.y });

    expect(onSelect).toHaveBeenCalledWith(101);
  });
});
