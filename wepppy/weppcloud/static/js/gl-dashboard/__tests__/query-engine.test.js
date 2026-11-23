import { afterEach, beforeAll, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { createQueryEngine } from '../data/query-engine.js';
import { getState, initState, setValue } from '../state.js';

const originalFetch = global.fetch;
let originalState;

beforeAll(() => {
  originalState = JSON.parse(JSON.stringify(getState()));
});

beforeEach(() => {
  initState(originalState);
  global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
});

afterEach(() => {
  global.fetch = originalFetch;
  initState(originalState);
  jest.clearAllMocks();
});

describe('gl-dashboard query-engine routing', () => {
  it('routes omni contrast queries to composite runid and omits scenario', async () => {
    setValue('currentScenarioPath', '_pups/omni/contrasts/12');
    const engine = createQueryEngine({ runid: 'decimal-pleasing', config: 'cfg1' });

    await engine.postQueryEngine({ datasets: ['foo'] });

    const [url, init] = global.fetch.mock.calls[0];
    const body = JSON.parse(init.body);

    expect(url).toBe('/query-engine/runs/decimal-pleasing;;omni-contrast;;12/cfg1/query');
    expect(body.scenario).toBeUndefined();
  });

  it('routes omni scenario queries with scenario body param', async () => {
    setValue('currentScenarioPath', '_pups/omni/scenarios/burned');
    const engine = createQueryEngine({ runid: 'decimal-pleasing', config: 'cfg1' });

    await engine.postQueryEngine({ datasets: ['foo'] });

    const [url, init] = global.fetch.mock.calls[0];
    const body = JSON.parse(init.body);

    expect(url).toBe('/query-engine/runs/decimal-pleasing/cfg1/query');
    expect(body.scenario).toBe('burned');
  });

  it('strips composite omni runid to parent when routing scenario queries', async () => {
    setValue('currentScenarioPath', '_pups/omni/scenarios/burned');
    const engine = createQueryEngine({ runid: 'decimal-pleasing;;omni;;undisturbed', config: 'cfg1' });

    await engine.postQueryEngine({ datasets: ['foo'] });

    const [url, init] = global.fetch.mock.calls[0];
    const body = JSON.parse(init.body);

    expect(url).toBe('/query-engine/runs/decimal-pleasing/cfg1/query');
    expect(body.scenario).toBe('burned');
  });

  it('preserves grouped runid segments when building contrast query URLs', async () => {
    setValue('currentScenarioPath', '_pups/omni/contrasts/3');
    const engine = createQueryEngine({ runid: 'batch;;spring-2025;;run-001', config: 'cfg1' });

    await engine.postQueryEngine({ datasets: ['foo'] });

    const [url] = global.fetch.mock.calls[0];

    expect(url).toBe('/query-engine/runs/batch;;spring-2025;;run-001;;omni-contrast;;3/cfg1/query');
  });

  it('strips nested composite runid to parent when routing contrast queries', async () => {
    setValue('currentScenarioPath', '_pups/omni/contrasts/3');
    const engine = createQueryEngine({
      runid: 'batch;;spring-2025;;run-001;;omni;;undisturbed',
      config: 'cfg1',
    });

    await engine.postQueryEngine({ datasets: ['foo'] });

    const [url, init] = global.fetch.mock.calls[0];
    const body = JSON.parse(init.body);

    expect(url).toBe('/query-engine/runs/batch;;spring-2025;;run-001;;omni-contrast;;3/cfg1/query');
    expect(body.scenario).toBeUndefined();
  });

  it('url-encodes unsafe contrast ids when building query-engine URLs', async () => {
    setValue('currentScenarioPath', '_pups/omni/contrasts/treated name#1');
    const engine = createQueryEngine({ runid: 'decimal-pleasing', config: 'cfg1' });

    await engine.postQueryEngine({ datasets: ['foo'] });

    const [url, init] = global.fetch.mock.calls[0];
    const body = JSON.parse(init.body);

    expect(url).toBe('/query-engine/runs/decimal-pleasing;;omni-contrast;;treated%20name%231/cfg1/query');
    expect(body.scenario).toBeUndefined();
  });
});


it.each(['roads_results_unavailable', 'roads_operation_busy'])('preserves busy lifecycle guidance for %s without requesting a rerun', async (code) => {
  const message = 'Roads is busy; wait for the active operation to finish.';
  global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ code, error: message }) });
  const onRoadsUnavailable = jest.fn();
  const engine = createQueryEngine({ runid: 'r', config: 'c', onRoadsUnavailable });
  await expect(engine.postBaseQueryEngine({ datasets: ['wepp/roads/output/interchange/H.wat.parquet'] })).rejects.toThrow(message);
  expect(onRoadsUnavailable).toHaveBeenCalledWith(message);
  await expect(engine.postBaseQueryEngine({ datasets: [] })).rejects.toThrow(message);
  expect(onRoadsUnavailable).toHaveBeenCalledTimes(1);
});


it.each(['_pups/omni/scenarios/missing', '_pups/omni/contrasts/2'])('isolates foreign Roads failure at %s from current-run queries', async (path) => {
  const onRoadsUnavailable = jest.fn();
  const engine = createQueryEngine({ runid: 'r', config: 'c', onRoadsUnavailable });
  global.fetch.mockResolvedValueOnce({ ok: false, status: 409, json: async () => ({ code: 'roads_results_unavailable', error: 'Child Roads results unavailable.' }) });
  await expect(engine.postQueryEngineForScenario({ datasets: [] }, path)).rejects.toMatchObject({ code: 'roads_results_unavailable', foreignScenario: true });
  expect(onRoadsUnavailable).not.toHaveBeenCalled();
  await expect(engine.postBaseQueryEngine({ datasets: [] })).resolves.toEqual({ ok: true });
  global.fetch.mockResolvedValueOnce({ ok: false, status: 409, json: async () => ({ code: 'roads_results_unavailable', error: 'Current Roads unavailable.' }) });
  await expect(engine.postQueryEngineForScenario({ datasets: [] }, '')).rejects.toThrow('Current Roads unavailable.');
  expect(onRoadsUnavailable).toHaveBeenCalledWith('Current Roads unavailable.');
});


function catalogResponse(status, body, retryAfter = null) {
  return {
    status, ok: status < 300,
    headers: new Headers(retryAfter == null ? {} : { 'Retry-After': retryAfter }),
    json: async () => body,
    clone: () => catalogResponse(status, body, retryAfter),
  };
}

it('holds parallel results until one shared catalog preparation is ready', async () => {
  jest.useFakeTimers();
  try {
    const onCatalogState = jest.fn();
    global.fetch
      .mockResolvedValueOnce(catalogResponse(202, { state: 'preparing', code: 'catalog_preparing' }, '2'))
      .mockResolvedValueOnce(catalogResponse(200, { state: 'ready' }))
      .mockResolvedValue(catalogResponse(200, { records: [{ value: 12 }] }));
    const engine = createQueryEngine({ runid: 'r', config: 'c' }, { onCatalogState });
    const work = [engine.postQueryEngine({ datasets: ['a'] }), engine.postBaseQueryEngine({ datasets: ['b'] })];
    await jest.advanceTimersByTimeAsync(1999);
    expect(global.fetch.mock.calls.map(([url]) => url)).toEqual(['/query-engine/runs/r/c/catalog/prepare']);
    expect(onCatalogState).toHaveBeenCalledWith(expect.any(String), 'preparing');
    await jest.advanceTimersByTimeAsync(1);
    expect(await Promise.all(work)).toEqual([{ records: [{ value: 12 }] }, { records: [{ value: 12 }] }]);
    expect(global.fetch.mock.calls.map(([url]) => url)).toEqual([
      '/query-engine/runs/r/c/catalog/prepare', '/query-engine/runs/r/c/catalog/status',
      '/query-engine/runs/r/c/query', '/query-engine/runs/r/c/query',
    ]);
  } finally {
    jest.useRealTimers();
  }
});

it('rejoins readiness after a late query invalidation', async () => {
  jest.useFakeTimers();
  try {
    global.fetch
      .mockResolvedValueOnce(catalogResponse(200, { state: 'ready' }))
      .mockResolvedValueOnce(catalogResponse(202, { state: 'preparing', code: 'catalog_preparing' }, '2'))
      .mockResolvedValueOnce(catalogResponse(200, { state: 'ready' }))
      .mockResolvedValueOnce(catalogResponse(200, { records: [] }));
    const engine = createQueryEngine({ runid: 'r', config: 'c' }, { onCatalogState: jest.fn() });
    const work = engine.postQueryEngine({ datasets: ['a'] });
    await jest.advanceTimersByTimeAsync(1999);
    expect(global.fetch).toHaveBeenCalledTimes(2);
    await jest.advanceTimersByTimeAsync(1);
    expect(await work).toEqual({ records: [] });
    expect(global.fetch.mock.calls.map(([url]) => url.split('/').pop())).toEqual(['prepare', 'query', 'prepare', 'query']);
    expect(JSON.parse(global.fetch.mock.calls[1][1].body).catalog_mode).toBe('wait');
  } finally {
    jest.useRealTimers();
  }
});

it('retries contended prepare without sending SQL or reporting a terminal failure', async () => {
  jest.useFakeTimers();
  try {
    global.fetch
      .mockResolvedValueOnce(catalogResponse(503, { code: 'catalog_refresh_unavailable' }, '2'))
      .mockResolvedValueOnce(catalogResponse(200, { state: 'ready' }))
      .mockResolvedValueOnce(catalogResponse(200, { records: [{ value: 7 }] }));
    const onCatalogState = jest.fn();
    const engine = createQueryEngine({ runid: 'r', config: 'c' }, { onCatalogState });
    const work = engine.postQueryEngine({ datasets: ['a'] });
    await jest.advanceTimersByTimeAsync(1999);
    expect(global.fetch).toHaveBeenCalledTimes(1);
    await jest.advanceTimersByTimeAsync(1);
    expect(await work).toEqual({ records: [{ value: 7 }] });
    expect(onCatalogState).not.toHaveBeenCalledWith(expect.any(String), 'unavailable', expect.any(String));
  } finally {
    jest.useRealTimers();
  }
});

it('drops an old query even after switching away and back to the same scenario', async () => {
  let finish;
  let started;
  const queryStarted = new Promise((resolve) => { started = resolve; });
  global.fetch
    .mockResolvedValueOnce(catalogResponse(200, { state: 'ready' }))
    .mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; started(); }));
  const engine = createQueryEngine({ runid: 'r', config: 'c' }, { onCatalogState: jest.fn() });
  setValue('currentScenarioPath', '_pups/omni/scenarios/a');
  const work = engine.postQueryEngine({ datasets: ['a'] });
  await queryStarted;
  engine.scenarioChanged('_pups/omni/scenarios/b');
  engine.scenarioChanged('_pups/omni/scenarios/a');
  finish(catalogResponse(200, { records: [{ obsolete: true }] }));
  await expect(work).rejects.toMatchObject({ name: 'AbortError' });
});

it('clears a failed readiness check only when the user retries', async () => {
  global.fetch
    .mockResolvedValueOnce(catalogResponse(503, { code: 'catalog_refresh_failed' }))
    .mockResolvedValueOnce(catalogResponse(200, { state: 'ready' }))
    .mockResolvedValueOnce(catalogResponse(200, { records: [{ value: 7 }] }));
  const engine = createQueryEngine({ runid: 'r', config: 'c' }, { onCatalogState: jest.fn() });
  await expect(engine.postQueryEngine({ datasets: ['a'] })).rejects.toMatchObject({ code: 'catalog_preparation' });
  await expect(engine.postBaseQueryEngine({ datasets: ['b'] })).rejects.toMatchObject({ code: 'catalog_preparation' });
  expect(global.fetch).toHaveBeenCalledTimes(1);
  engine.retryCatalogReadiness();
  expect(await engine.postQueryEngine({ datasets: ['a'] })).toEqual({ records: [{ value: 7 }] });
});
