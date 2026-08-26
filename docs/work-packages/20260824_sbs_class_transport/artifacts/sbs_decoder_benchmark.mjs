import fs from 'node:fs';
import vm from 'node:vm';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const artifactDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(artifactDir, '../../../..');
const dashboardModule = await import(pathToFileURL(path.join(
  repoRoot,
  'wepppy/weppcloud/static/js/gl-dashboard/map/layers.js',
)));
global.window = {};
vm.runInThisContext(fs.readFileSync(
  path.join(repoRoot, 'wepppy/weppcloud/controllers_js/map_gl_shared.js'),
  'utf8',
));

const shared = window.WCMapGlShared;
const dashboard = dashboardModule.createLayerUtils({
  deck: {}, getState: () => ({}), colorScales: {}, constants: {},
});
const side = 4096;
const source = new Uint8ClampedArray(side * side * 4);
const colors = [
  [0, 128, 128, 255], [82, 204, 204, 255], [255, 232, 32, 255],
  [168, 0, 0, 255], [46, 203, 24, 255], [1, 2, 3, 80], [0, 0, 0, 0],
];
for (let index = 0; index < source.length; index += 4) {
  source.set(colors[(index / 4) % colors.length], index);
}

const legacyMap = {
  '0_128_128': [0, 158, 115], '82_204_204': [86, 180, 233],
  '255_232_32': [240, 228, 66], '168_0_0': [204, 121, 167],
};
function legacyShifted(data) {
  for (let index = 0; index < data.length; index += 4) {
    if (data[index + 3] === 0) continue;
    const mapped = legacyMap[`${data[index]}_${data[index + 1]}_${data[index + 2]}`];
    if (mapped) data.set(mapped, index);
  }
}
function median(values) {
  return [...values].sort((left, right) => left - right)[2];
}
function benchmark(operation) {
  operation(source.slice());
  const runs = [];
  for (let run = 0; run < 5; run += 1) {
    const destination = source.slice();
    const start = performance.now();
    operation(destination);
    runs.push(performance.now() - start);
  }
  return { runsMs: runs.map((value) => Number(value.toFixed(1))), medianMs: median(runs) };
}

if (typeof global.gc === 'function') global.gc();
const beforeDestination = process.memoryUsage().arrayBuffers;
const memoryDestination = source.slice();
shared.recolorSbsPixels(memoryDestination, 'standard');
const destinationBytes = process.memoryUsage().arrayBuffers - beforeDestination;

const baseline = benchmark(legacyShifted);
const results = {
  baseline,
  runPageStandard: benchmark((data) => shared.recolorSbsPixels(data, 'standard')),
  runPageShifted: benchmark((data) => shared.recolorSbsPixels(data, 'shifted')),
  dashboardStandard: benchmark((data) => dashboard.recolorSbsPixels(data, false)),
  dashboardShifted: benchmark((data) => dashboard.recolorSbsPixels(data, true)),
};
for (const [key, value] of Object.entries(results)) {
  if (key !== 'baseline') value.baselineRatio = value.medianMs / baseline.medianMs;
}
console.log(JSON.stringify({
  side,
  sourceBytes: source.byteLength,
  destinationBytes,
  results,
}, null, 2));
