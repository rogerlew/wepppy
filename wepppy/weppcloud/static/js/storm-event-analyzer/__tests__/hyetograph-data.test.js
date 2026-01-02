import { describe, expect, it } from '@jest/globals';
import { computeHyetographPoints } from '../data/hyetograph-data.js';

describe('storm-event-analyzer hyetograph computation', () => {
  it('produces monotonic cumulative depth with matching final depth', () => {
    const depth = 25;
    const duration = 2.5;
    const points = computeHyetographPoints({
      depth_mm: depth,
      duration_hours: duration,
      tp: 0.35,
      ip: 4,
    });

    expect(points).not.toBeNull();
    expect(points.length).toBeGreaterThan(1);

    for (let i = 1; i < points.length; i += 1) {
      expect(points[i].elapsed_hours).toBeGreaterThanOrEqual(points[i - 1].elapsed_hours);
      expect(points[i].cumulative_depth_mm).toBeGreaterThanOrEqual(points[i - 1].cumulative_depth_mm);
    }

    expect(points[points.length - 1].elapsed_hours).toBeCloseTo(duration, 6);
    expect(points[points.length - 1].cumulative_depth_mm).toBeCloseTo(depth, 4);
  });
});
