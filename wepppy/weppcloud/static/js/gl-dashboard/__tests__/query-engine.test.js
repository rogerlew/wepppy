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
});
