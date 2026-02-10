import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { detectBatchReadiness } from '../layers/detector.js';

const originalFetch = global.fetch;

function installFetchStub(responses) {
  global.fetch = jest.fn().mockImplementation(async (url) => {
    const key = String(url);
    if (!Object.prototype.hasOwnProperty.call(responses, key)) {
      return { ok: false, status: 404, json: async () => null };
    }
    const value = responses[key];
    if (value && value.__status && value.__status !== 200) {
      return { ok: false, status: value.__status, json: async () => null };
    }
    return { ok: true, status: 200, json: async () => value };
  });
}

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
  jest.clearAllMocks();
});

describe('gl-dashboard detector batch readiness', () => {
  it('excludes runs missing required subcatchments geometry and reports degraded optional checks', async () => {
    const ctx = {
      mode: 'batch',
      sitePrefix: '/weppcloud',
      config: 'cfg1',
      batch: {
        name: 'spring-2025-ready',
        runs: [
          { runid: 'batch;;spring-2025-ready;;run-001', leaf_runid: 'run-001' },
          { runid: 'batch;;spring-2025-ready;;run-002', leaf_runid: 'run-002' },
        ],
      },
    };

    const run1Sub = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { TopazID: 1 },
          geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] },
        },
      ],
    };
    const run1Chn = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { TopazID: 10 },
          geometry: { type: 'LineString', coordinates: [[0, 0], [1, 1]] },
        },
      ],
    };

    const responses = {
      '/weppcloud/runs/batch;;spring-2025-ready;;run-001/cfg1/resources/subcatchments.json': run1Sub,
      '/weppcloud/runs/batch;;spring-2025-ready;;run-002/cfg1/resources/subcatchments.json': { __status: 404 },
      '/weppcloud/runs/batch;;spring-2025-ready;;run-001/cfg1/resources/channels.json': run1Chn,
      '/weppcloud/runs/batch;;spring-2025-ready;;run-002/cfg1/resources/channels.json': { __status: 404 },
      '/weppcloud/runs/batch;;spring-2025-ready;;run-001/cfg1/query/landuse/subcatchments': { 1: { dominant: 1 } },
      '/weppcloud/runs/batch;;spring-2025-ready;;run-001/cfg1/query/soils/subcatchments': { 1: { dominant: 'A' } },
      '/weppcloud/runs/batch;;spring-2025-ready;;run-001/cfg1/query/watershed/subcatchments': { 1: { slope_scalar: 0.1 } },
    };

    installFetchStub(responses);

    const result = await detectBatchReadiness({ ctx });
    expect(result).toBeTruthy();
    expect(result.totalRuns).toBe(2);
    expect(result.readyRuns).toEqual([{ runid: 'batch;;spring-2025-ready;;run-001', leaf_runid: 'run-001' }]);

    const statusByLeaf = {};
    result.statuses.forEach((s) => {
      statusByLeaf[s.leaf_runid] = s;
    });

    expect(statusByLeaf['run-001'].ready).toBe(true);
    expect(statusByLeaf['run-001'].missingRequired).toEqual([]);
    expect(statusByLeaf['run-001'].missingOptional).toEqual([]);
    expect(statusByLeaf['run-001'].counts.subcatchments).toBe(1);
    expect(statusByLeaf['run-001'].counts.channels).toBe(1);
    expect(statusByLeaf['run-001'].summaries.landuse.ok).toBe(true);
    expect(statusByLeaf['run-001'].summaries.soils.ok).toBe(true);
    expect(statusByLeaf['run-001'].summaries.hillslopes.ok).toBe(true);

    expect(statusByLeaf['run-002'].ready).toBe(false);
    expect(statusByLeaf['run-002'].missingRequired).toEqual(['subcatchments']);
  });
});

