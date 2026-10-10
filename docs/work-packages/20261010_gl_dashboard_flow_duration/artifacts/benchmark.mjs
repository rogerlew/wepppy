// Run from repository root: node docs/work-packages/20261010_gl_dashboard_flow_duration/artifacts/benchmark.mjs
import { readFileSync } from 'node:fs';
import { performance } from 'node:perf_hooks';
const source = readFileSync('wepppy/weppcloud/static/js/gl-dashboard/graphs/flow-duration-data.js', 'utf8');
const { createFlowDurationLoader } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const results = [];
for (const [count, years] of [[20, 45], [3, 500]]) {
  const rows = [];
  for (let year = 1980; year < 1980 + years; year++) {
    const start = Date.UTC(year, 0, 1), end = Date.UTC(year + 1, 0, 1);
    for (let t = start; t < end; t += 86400000) {
      const date = new Date(t);
      rows.push({ year, month: date.getUTCMonth() + 1, day: date.getUTCDate(), julian: (t - start) / 86400000 + 1,
        flow: String((rows.length % 1000) * 0.031), area: '9720296.31' });
    }
  }
  const scenarios = Array.from({ length: count }, (_, index) => ({ path: String(index), name: `scenario${index}` }));
  let queries = 0;
  const load = createFlowDurationLoader({ scenarios,
    metadata: { scenarios: Object.fromEntries(scenarios.map(s => [s.path, { hillslope: { available: true } }])) },
    query: async () => { queries++; return { records: rows, row_count: rows.length }; },
    displayName: s => s.name, color: () => [1, 2, 3] });
  const start = performance.now(); const data = await load(); const ranked = performance.now();
  await load({ scale: 'log' }); const cached = performance.now();
  results.push({ scenarios: count, years, sourceRowsPerScenario: rows.length, eligibleRows: data.series[0].count,
    initialRankingMs: ranked - start, cachedScaleMs: cached - ranked, queries, heapMb: process.memoryUsage().heapUsed / 1024 / 1024 });
}
console.log(JSON.stringify(results, null, 2));
