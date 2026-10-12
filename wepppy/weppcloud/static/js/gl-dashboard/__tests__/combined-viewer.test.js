import { joinRun, factor, shareUrl, loadRun } from '../combined-viewer-data.js';
const run = {runid: 'a', cfg: 'actual', phosphorus: true, weppIds: {'22': 1}};
const geo = {features: [{properties: {TopazID: 22}, geometry: {type: 'Polygon', coordinates: []}}]};
const row = {wepp_id: 1, 'Hillslope Area': 2, 'Runoff Volume': 100, 'Subrunoff Volume': 20,
  'Baseflow Volume': 0, 'Soil Loss': 40, 'Total Pollutant': 0};
test('native average depths/densities preserve zero and composite IDs', () => {
  const a = joinRun(run, geo, [row])[0];
  expect(a.properties.values).toEqual({runoff: 5, subrunoff: 1, baseflow: 0, loss: 20, phosphorus: 0});
  expect(joinRun({...run, runid: 'b'}, geo, [row])[0].properties.key).not.toBe(a.properties.key);
});
test('missing required data and mismatched coverage fail explicitly', () => {
  expect(() => joinRun(run, geo, [{...row, 'Hillslope Area': 0}])).toThrow();
  expect(() => joinRun(run, geo, [{...row, 'Soil Loss': null}])).toThrow();
  expect(() => joinRun(run, geo, [row, {...row, wepp_id: 2}])).toThrow();
});
test('optional phosphorus is not required while zero configured phosphorus remains valid', () => {
  expect(joinRun({...run, phosphorus: false}, geo, [{...row, 'Total Pollutant': null}])[0].properties.values.phosphorus).toBeUndefined();
});
test('unit factors and encoded share parameters preserve physical values', () => {
  expect(factor('loss', 'English')).toBe(1.12085);
  expect(factor('runoff', 'English')).toBe(25.4);
  const url = new URL(shareUrl({sitePrefix: '/weppcloud', ws: [run], title: 'A & B # <>'},
    {latitude: 45, longitude: -122, zoom: 10}, 'loss', 'English', {loss: 4000}, 'https://example.test'));
  expect(url.searchParams.get('title')).toBe('A & B # <>');
  expect(JSON.parse(url.searchParams.get('ws'))).toEqual([{runid: 'a', cfg: 'actual'}]);
});
test('loader posts canonical query payload and rejects failed requests', async () => {
  const calls = [];
  const fetcher = async (url, options) => {calls.push({url, options}); return {ok: true, json: async () => url.includes('query-engine') ? {records: [row]} : geo};};
  expect(await loadRun(run, '/weppcloud', fetcher)).toHaveLength(1);
  expect(JSON.parse(calls[1].options.body).datasets).toEqual(['wepp/output/interchange/loss_pw0.hill.parquet']);
  await expect(loadRun(run, '/weppcloud', async () => ({ok:false,status:403}))).rejects.toThrow('not ready');
});
test('legacy polygon fragments share one hillslope value without losing geometry', () => {
  const joined = joinRun(run, {features: [...geo.features, ...geo.features]}, [row]);
  expect(joined).toHaveLength(2);
  expect(joined[0].properties.key).toBe(joined[1].properties.key);
  expect(joined[1].properties.values.loss).toBe(20);
});
test('missing optional phosphorus keeps required results and disables only phosphorus', () => {
  const candidate = {...run, phosphorus: true};
  const result = joinRun(candidate, geo, [{...row, 'Total Pollutant': null}]);
  expect(candidate.phosphorus).toBe(false);
  expect(result[0].properties.values.loss).toBe(20);
  expect(result[0].properties.values.phosphorus).toBeUndefined();
});
test('different Topaz IDs cannot reuse a native hillslope row', () => {
  expect(() => joinRun({...run, weppIds: {'22':1,'23':1}},
    {features:[...geo.features,{...geo.features[0],properties:{TopazID:23}}]}, [row])).toThrow('duplicate');
});
test('metadata hillslopes absent from both geometry and native rows fail readiness', () => {
  expect(() => joinRun({...run, weppIds:{'22':1,'33':2}},geo,[row])).toThrow('coverage');
});
