import { jest, test, expect } from '@jest/globals';
import { createGraphLoaders } from '../graphs/graph-loaders.js';
import { setValue } from '../state.js';

test.each(['omni-soil-loss-hill', 'omni-soil-loss-chn', 'omni-outlet-sediment'])('%s propagates lifecycle errors without caching an empty graph', async (key) => {
  ['hillLossCache', 'channelLossCache', 'outletAllYearsCache', 'hillslopeAreaCache', 'graphDataCache'].forEach((name) => setValue(name, {}));
  const error = Object.assign(new Error('Selected scenario Roads unavailable.'), { code: 'roads_results_unavailable', foreignScenario: true });
  const query = jest.fn().mockRejectedValue(error);
  const loaders = createGraphLoaders({
    graphScenarios: [{ name: 'Base', path: '' }, { name: 'Child', path: '_pups/omni/scenarios/missing' }],
    postQueryEngineForScenario: query, postBaseQueryEngine: query, postQueryEngine: query,
    weppLossPath: 'wepp/roads/output/interchange/loss_pw0.hill.parquet',
    weppChannelPath: 'wepp/roads/output/interchange/loss_pw0.chn.parquet',
    weppOutletAllYearsPath: 'wepp/roads/output/interchange/loss_pw0.all_years.out.parquet',
  });
  await expect(loaders.loadGraphDataset(key)).rejects.toBe(error);
  const calls = query.mock.calls.length;
  await expect(loaders.loadGraphDataset(key)).rejects.toBe(error);
  expect(query.mock.calls.length).toBeGreaterThan(calls);
});
