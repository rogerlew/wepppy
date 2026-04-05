import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { detectWeppEventOverlays } from '../layers/detector.js';

const originalFetch = global.fetch;

function installSubcatchmentsFetchStub(geoJson = null) {
  const payload = geoJson || {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: { TopazID: 1 },
        geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] },
      },
    ],
  };
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => payload,
  });
  return payload;
}

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
  jest.clearAllMocks();
});

describe('gl-dashboard detector WEPP Event', () => {
  it('normalizes simulation-year metadata and selected date to ISO format', async () => {
    installSubcatchmentsFetchStub();

    const result = await detectWeppEventOverlays({
      buildBaseUrl: (path) => `/runs/base/cfg/${path}`,
      climateCtx: { startYear: 1, endYear: 100 },
      weppEventWatPath: 'wepp/event_wat.parquet',
      weppEventSoilPath: 'wepp/event_soil.parquet',
      weppEventPassPath: 'wepp/event_pass.parquet',
      currentSelectedDate: '1-01-05',
      subcatchmentsGeoJson: null,
    });

    expect(result).toBeTruthy();
    expect(result.weppEventMetadata).toEqual({
      available: true,
      startDate: '0001-01-01',
      endDate: '0100-12-31',
    });
    expect(result.weppEventSelectedDate).toBe('0001-01-05');
    expect(global.fetch).toHaveBeenCalledWith('/runs/base/cfg/resources/subcatchments.json');
  });

  it('clamps selected date to the climate range', async () => {
    installSubcatchmentsFetchStub();

    const result = await detectWeppEventOverlays({
      buildBaseUrl: (path) => `/runs/base/cfg/${path}`,
      climateCtx: { startYear: 1, endYear: 100 },
      weppEventWatPath: 'wepp/event_wat.parquet',
      weppEventSoilPath: 'wepp/event_soil.parquet',
      weppEventPassPath: 'wepp/event_pass.parquet',
      currentSelectedDate: '2024-01-05',
      subcatchmentsGeoJson: null,
    });

    expect(result).toBeTruthy();
    expect(result.weppEventSelectedDate).toBe('0100-12-31');
  });

  it('clamps below-range dates to the simulation start', async () => {
    installSubcatchmentsFetchStub();

    const result = await detectWeppEventOverlays({
      buildBaseUrl: (path) => `/runs/base/cfg/${path}`,
      climateCtx: { startYear: 10, endYear: 20 },
      weppEventWatPath: 'wepp/event_wat.parquet',
      weppEventSoilPath: 'wepp/event_soil.parquet',
      weppEventPassPath: 'wepp/event_pass.parquet',
      currentSelectedDate: '0009-12-31',
      subcatchmentsGeoJson: null,
    });

    expect(result).toBeTruthy();
    expect(result.weppEventSelectedDate).toBe('0010-01-01');
  });

  it('normalizes legacy non-padded selected dates', async () => {
    installSubcatchmentsFetchStub();

    const result = await detectWeppEventOverlays({
      buildBaseUrl: (path) => `/runs/base/cfg/${path}`,
      climateCtx: { startYear: 1, endYear: 100 },
      weppEventWatPath: 'wepp/event_wat.parquet',
      weppEventSoilPath: 'wepp/event_soil.parquet',
      weppEventPassPath: 'wepp/event_pass.parquet',
      currentSelectedDate: '7-1-5',
      subcatchmentsGeoJson: null,
    });

    expect(result).toBeTruthy();
    expect(result.weppEventSelectedDate).toBe('0007-01-05');
  });

  it('falls back to start date when selected date is invalid', async () => {
    installSubcatchmentsFetchStub();

    const result = await detectWeppEventOverlays({
      buildBaseUrl: (path) => `/runs/base/cfg/${path}`,
      climateCtx: { startYear: 2000, endYear: 2020 },
      weppEventWatPath: 'wepp/event_wat.parquet',
      weppEventSoilPath: 'wepp/event_soil.parquet',
      weppEventPassPath: 'wepp/event_pass.parquet',
      currentSelectedDate: '2020-02-31',
      subcatchmentsGeoJson: null,
    });

    expect(result).toBeTruthy();
    expect(result.weppEventSelectedDate).toBe('2000-01-01');
  });

  it('returns null when climate bounds are invalid', async () => {
    installSubcatchmentsFetchStub();

    const result = await detectWeppEventOverlays({
      buildBaseUrl: (path) => `/runs/base/cfg/${path}`,
      climateCtx: { startYear: 0, endYear: 100 },
      weppEventWatPath: 'wepp/event_wat.parquet',
      weppEventSoilPath: 'wepp/event_soil.parquet',
      weppEventPassPath: 'wepp/event_pass.parquet',
      currentSelectedDate: null,
      subcatchmentsGeoJson: null,
    });

    expect(result).toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('returns null when climate bounds are reversed', async () => {
    installSubcatchmentsFetchStub();

    const result = await detectWeppEventOverlays({
      buildBaseUrl: (path) => `/runs/base/cfg/${path}`,
      climateCtx: { startYear: 2025, endYear: 2020 },
      weppEventWatPath: 'wepp/event_wat.parquet',
      weppEventSoilPath: 'wepp/event_soil.parquet',
      weppEventPassPath: 'wepp/event_pass.parquet',
      currentSelectedDate: null,
      subcatchmentsGeoJson: null,
    });

    expect(result).toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
