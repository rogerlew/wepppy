import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import {
  detectChannelsOverlays,
  detectLanduseOverlays,
  detectSoilsOverlays,
  detectHillslopesOverlays,
} from '../layers/detector.js';

const originalFetch = global.fetch;

function installFetchStub(responses) {
  global.fetch = jest.fn().mockImplementation(async (url) => {
    const key = String(url);
    if (!Object.prototype.hasOwnProperty.call(responses, key)) {
      return { ok: false, status: 404, json: async () => null };
    }
    return { ok: true, status: 200, json: async () => responses[key] };
  });
}

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
  jest.clearAllMocks();
});

describe('gl-dashboard detector batch mode', () => {
  it('merges landuse summary + subcatchments geometry with composite feature keys', async () => {
    const ctx = {
      mode: 'batch',
      sitePrefix: '/weppcloud',
      config: 'cfg1',
      batch: {
        name: 'spring-2025-a',
        runs: [
          { runid: 'batch;;spring-2025-a;;run-001', leaf_runid: 'run-001' },
          { runid: 'batch;;spring-2025-a;;run-002', leaf_runid: 'run-002' },
        ],
      },
    };

    const run1Geo = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { TopazID: 1 },
          geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] },
        },
      ],
    };
    const run2Geo = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { TopazID: 1 },
          geometry: { type: 'Polygon', coordinates: [[[10, 10], [11, 10], [11, 11], [10, 10]]] },
        },
      ],
    };

    const responses = {
      '/weppcloud/runs/batch;;spring-2025-a;;run-001/cfg1/resources/subcatchments.json': run1Geo,
      '/weppcloud/runs/batch;;spring-2025-a;;run-002/cfg1/resources/subcatchments.json': run2Geo,
      '/weppcloud/runs/batch;;spring-2025-a;;run-001/cfg1/query/landuse/subcatchments': {
        1: { cancov: 0.1, inrcov: 0.2, rilcov: 0.3, dominant: 42 },
      },
      '/weppcloud/runs/batch;;spring-2025-a;;run-002/cfg1/query/landuse/subcatchments': {
        1: { cancov: 0.4, inrcov: 0.5, rilcov: 0.6, dominant: 43 },
      },
    };

    installFetchStub(responses);

    const result = await detectLanduseOverlays({
      ctx,
      buildScenarioUrl: () => '/unused',
      buildBaseUrl: () => '/unused',
    });

    expect(result).toBeTruthy();
    expect(Object.keys(result.landuseSummary).sort()).toEqual([
      'batch;;spring-2025-a;;run-001-1',
      'batch;;spring-2025-a;;run-002-1',
    ]);
    expect(result.subcatchmentsGeoJson.features).toHaveLength(2);
    const keys = result.subcatchmentsGeoJson.features.map((f) => f.properties.feature_key).sort();
    expect(keys).toEqual(['batch;;spring-2025-a;;run-001-1', 'batch;;spring-2025-a;;run-002-1']);
    const runids = result.subcatchmentsGeoJson.features.map((f) => f.properties.runid).sort();
    expect(runids).toEqual(['batch;;spring-2025-a;;run-001', 'batch;;spring-2025-a;;run-002']);
    const leaves = result.subcatchmentsGeoJson.features.map((f) => f.properties.leaf_runid).sort();
    expect(leaves).toEqual(['run-001', 'run-002']);
  });

  it('merges soils summary + subcatchments geometry with composite feature keys', async () => {
    const ctx = {
      mode: 'batch',
      sitePrefix: '/weppcloud',
      config: 'cfg1',
      batch: {
        name: 'spring-2025-c',
        runs: [
          { runid: 'batch;;spring-2025-c;;run-001', leaf_runid: 'run-001' },
          { runid: 'batch;;spring-2025-c;;run-002', leaf_runid: 'run-002' },
        ],
      },
    };

    const run1Geo = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { TopazID: 1 },
          geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] },
        },
      ],
    };
    const run2Geo = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { TopazID: 1 },
          geometry: { type: 'Polygon', coordinates: [[[10, 10], [11, 10], [11, 11], [10, 10]]] },
        },
      ],
    };

    const responses = {
      '/weppcloud/runs/batch;;spring-2025-c;;run-001/cfg1/resources/subcatchments.json': run1Geo,
      '/weppcloud/runs/batch;;spring-2025-c;;run-002/cfg1/resources/subcatchments.json': run2Geo,
      '/weppcloud/runs/batch;;spring-2025-c;;run-001/cfg1/query/soils/subcatchments': {
        1: { dominant: 'A', clay: 10, sand: 20, bd: 1.2, rock: 0, soil_depth: 500 },
      },
      '/weppcloud/runs/batch;;spring-2025-c;;run-002/cfg1/query/soils/subcatchments': {
        1: { dominant: 'B', clay: 30, sand: 40, bd: 1.3, rock: 5, soil_depth: 600 },
      },
    };

    installFetchStub(responses);

    const result = await detectSoilsOverlays({
      ctx,
      buildScenarioUrl: () => '/unused',
      buildBaseUrl: () => '/unused',
    });

    expect(result).toBeTruthy();
    expect(Object.keys(result.soilsSummary).sort()).toEqual([
      'batch;;spring-2025-c;;run-001-1',
      'batch;;spring-2025-c;;run-002-1',
    ]);
    expect(result.subcatchmentsGeoJson.features).toHaveLength(2);
    const keys = result.subcatchmentsGeoJson.features.map((f) => f.properties.feature_key).sort();
    expect(keys).toEqual(['batch;;spring-2025-c;;run-001-1', 'batch;;spring-2025-c;;run-002-1']);
  });

  it('merges hillslopes summary + subcatchments geometry with composite feature keys', async () => {
    const ctx = {
      mode: 'batch',
      sitePrefix: '/weppcloud',
      config: 'cfg1',
      batch: {
        name: 'spring-2025-d',
        runs: [
          { runid: 'batch;;spring-2025-d;;run-001', leaf_runid: 'run-001' },
          { runid: 'batch;;spring-2025-d;;run-002', leaf_runid: 'run-002' },
        ],
      },
    };

    const run1Geo = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { TopazID: 1 },
          geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] },
        },
      ],
    };
    const run2Geo = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { TopazID: 1 },
          geometry: { type: 'Polygon', coordinates: [[[10, 10], [11, 10], [11, 11], [10, 10]]] },
        },
      ],
    };

    const responses = {
      '/weppcloud/runs/batch;;spring-2025-d;;run-001/cfg1/resources/subcatchments.json': run1Geo,
      '/weppcloud/runs/batch;;spring-2025-d;;run-002/cfg1/resources/subcatchments.json': run2Geo,
      '/weppcloud/runs/batch;;spring-2025-d;;run-001/cfg1/query/watershed/subcatchments': {
        1: { aspect: 10, slope_scalar: 0.05, length: 100.0 },
      },
      '/weppcloud/runs/batch;;spring-2025-d;;run-002/cfg1/query/watershed/subcatchments': {
        1: { aspect: 20, slope_scalar: 0.1, length: 200.0 },
      },
    };

    installFetchStub(responses);

    const result = await detectHillslopesOverlays({
      ctx,
      buildScenarioUrl: () => '/unused',
      buildBaseUrl: () => '/unused',
    });

    expect(result).toBeTruthy();
    expect(Object.keys(result.hillslopesSummary).sort()).toEqual([
      'batch;;spring-2025-d;;run-001-1',
      'batch;;spring-2025-d;;run-002-1',
    ]);
    expect(result.subcatchmentsGeoJson.features).toHaveLength(2);
    const keys = result.subcatchmentsGeoJson.features.map((f) => f.properties.feature_key).sort();
    expect(keys).toEqual(['batch;;spring-2025-d;;run-001-1', 'batch;;spring-2025-d;;run-002-1']);
  });

  it('merges channels GeoJSON and emits run-aware label data', async () => {
    const ctx = {
      mode: 'batch',
      sitePrefix: '/weppcloud',
      config: 'cfg1',
      batch: {
        name: 'spring-2025-b',
        runs: [
          { runid: 'batch;;spring-2025-b;;run-001', leaf_runid: 'run-001' },
          { runid: 'batch;;spring-2025-b;;run-002', leaf_runid: 'run-002' },
        ],
      },
    };

    const run1Geo = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { TopazID: 10 },
          geometry: { type: 'LineString', coordinates: [[0, 0], [1, 1]] },
        },
      ],
    };
    const run2Geo = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { TopazID: 10 },
          geometry: { type: 'LineString', coordinates: [[10, 10], [11, 11]] },
        },
      ],
    };

    const responses = {
      '/weppcloud/runs/batch;;spring-2025-b;;run-001/cfg1/resources/channels.json': run1Geo,
      '/weppcloud/runs/batch;;spring-2025-b;;run-002/cfg1/resources/channels.json': run2Geo,
    };

    installFetchStub(responses);

    const result = await detectChannelsOverlays({
      ctx,
      buildBaseUrl: () => '/unused',
    });

    expect(result).toBeTruthy();
    expect(result.channelsGeoJson.features).toHaveLength(2);
    const keys = result.channelsGeoJson.features.map((f) => f.properties.feature_key).sort();
    expect(keys).toEqual(['batch;;spring-2025-b;;run-001-10', 'batch;;spring-2025-b;;run-002-10']);
    const texts = result.channelLabelsData.map((l) => l.text).sort();
    expect(texts).toEqual(['run-001:10', 'run-002:10']);
  });
});
