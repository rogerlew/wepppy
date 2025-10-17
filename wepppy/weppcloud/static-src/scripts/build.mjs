import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs-extra';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const distDir = path.join(projectRoot, 'dist');
const nodeModules = path.join(projectRoot, 'node_modules');
const vendorSources = path.join(projectRoot, 'vendor-sources');
const isProd = process.env.NODE_ENV === 'production';

await fs.emptyDir(distDir);

const pick = (prodPath, devPath) => (isProd ? prodPath : devPath ?? prodPath);

const resolveSource = async (candidates) => {
  if (!candidates || candidates.length === 0) {
    return null;
  }
  for (const candidate of candidates) {
    if (await fs.pathExists(candidate)) {
      return candidate;
    }
  }
  return null;
};

const logSkip = (label, paths) => {
  const formatted = paths.map((p) => `    - ${path.relative(projectRoot, p)}`).join('\n');
  console.warn(
    `!! Skipping ${label} because none of the expected sources were found.\n${formatted}\n` +
      '   Run npm install in static-src or vendor the asset manually before retrying.'
  );
};

const targets = [
  // Leaflet core
  {
    kind: 'copyFile',
    source: path.join(nodeModules, 'leaflet', 'dist', pick('leaflet.js', 'leaflet-src.js')),
    outfile: path.join(distDir, 'vendor', 'leaflet', 'leaflet.js'),
    includeSourceMap: true,
  },
  {
    kind: 'copyFile',
    source: path.join(nodeModules, 'leaflet', 'dist', 'leaflet.css'),
    outfile: path.join(distDir, 'vendor', 'leaflet', 'leaflet.css'),
    includeSourceMap: true,
  },
  {
    kind: 'copyDir',
    source: path.join(nodeModules, 'leaflet', 'dist', 'images'),
    outdir: path.join(distDir, 'vendor', 'leaflet', 'images'),
  },
  // jQuery
  {
    kind: 'copyFile',
    source: path.join(nodeModules, 'jquery', 'dist', pick('jquery.min.js', 'jquery.js')),
    outfile: path.join(distDir, 'vendor', 'jquery', 'jquery.js'),
    includeSourceMap: true,
  },
  // Pure.css core + responsive grid
  {
    kind: 'copyFile',
    sourceCandidates: [
      path.join(nodeModules, 'purecss', 'build', pick('pure-min.css', 'pure.css')),
      path.join(vendorSources, 'purecss', pick('pure-min.css', 'pure.css')),
    ],
    outfile: path.join(distDir, 'vendor', 'purecss', 'pure-min.css'),
    optional: true,
  },
  {
    kind: 'copyFile',
    sourceCandidates: [
      path.join(nodeModules, 'purecss', 'build', pick('grids-responsive-min.css', 'grids-responsive.css')),
      path.join(vendorSources, 'purecss', pick('grids-responsive-min.css', 'grids-responsive.css')),
    ],
    outfile: path.join(distDir, 'vendor', 'purecss', 'grids-responsive-min.css'),
    optional: true,
  },
  // Bootstrap JS/CSS
  {
    kind: 'copyFile',
    source: path.join(nodeModules, 'bootstrap', 'dist', 'js', pick('bootstrap.bundle.min.js', 'bootstrap.bundle.js')),
    outfile: path.join(distDir, 'vendor', 'bootstrap', 'bootstrap.bundle.js'),
    includeSourceMap: true,
  },
  {
    kind: 'copyFile',
    source: path.join(nodeModules, 'bootstrap', 'dist', 'css', pick('bootstrap.min.css', 'bootstrap.css')),
    outfile: path.join(distDir, 'vendor', 'bootstrap', 'bootstrap.css'),
    includeSourceMap: true,
  },
  // Bootstrap TOC
  {
    kind: 'copyFile',
    source: path.join(vendorSources, 'bootstrap-toc', pick('bootstrap-toc.min.js', 'bootstrap-toc.js')),
    outfile: path.join(distDir, 'vendor', 'bootstrap-toc', 'bootstrap-toc.js'),
  },
  {
    kind: 'copyFile',
    source: path.join(vendorSources, 'bootstrap-toc', pick('bootstrap-toc.min.css', 'bootstrap-toc.css')),
    outfile: path.join(distDir, 'vendor', 'bootstrap-toc', 'bootstrap-toc.css'),
  },
  // DataTables core + Bootstrap integration
  {
    kind: 'copyFile',
    source: path.join(nodeModules, 'datatables.net', 'js', 'jquery.dataTables.js'),
    outfile: path.join(distDir, 'vendor', 'datatables', 'jquery.dataTables.js'),
  },
  {
    kind: 'copyFile',
    source: path.join(nodeModules, 'datatables.net-bs4', 'js', 'dataTables.bootstrap4.js'),
    outfile: path.join(distDir, 'vendor', 'datatables', 'dataTables.bootstrap4.js'),
  },
  {
    kind: 'copyFile',
    source: path.join(nodeModules, 'datatables.net-bs4', 'css', 'dataTables.bootstrap4.css'),
    outfile: path.join(distDir, 'vendor', 'datatables', 'dataTables.bootstrap4.css'),
  },
  // Leaflet AJAX plugin
  {
    kind: 'copyFile',
    source: path.join(nodeModules, 'leaflet-ajax', 'dist', 'leaflet.ajax.js'),
    outfile: path.join(distDir, 'vendor', 'leaflet', 'leaflet.ajax.js'),
  },
  // Spin.js
  {
    kind: 'copyFile',
    source: path.join(nodeModules, 'spin.js', 'spin.js'),
    outfile: path.join(distDir, 'vendor', 'spin', 'spin.js'),
  },
];

const ensureDir = async (filePath) => {
  const dir = path.dirname(filePath);
  await fs.mkdirp(dir);
};

for (const target of targets) {
  const candidateList = target.sourceCandidates ?? (target.source ? [target.source] : []);
  const sourcePath = await resolveSource(candidateList);

  if (!sourcePath) {
    if (target.optional) {
      logSkip(target.outfile, candidateList);
      continue;
    }
    throw new Error(`Unable to locate source for ${target.outfile}`);
  }

  if (target.kind === 'copyFile') {
    await ensureDir(target.outfile);
    await fs.copyFile(sourcePath, target.outfile);
    if (target.includeSourceMap) {
      const mapSource = `${sourcePath}.map`;
      const mapDest = `${target.outfile}.map`;
      if (await fs.pathExists(mapSource)) {
        await ensureDir(mapDest);
        await fs.copyFile(mapSource, mapDest);
        const sourceBase = path.basename(mapSource);
        const destBase = path.basename(mapDest);
        if (sourceBase !== destBase) {
          const originalDest = path.join(path.dirname(mapDest), sourceBase);
          await fs.copyFile(mapSource, originalDest);
        }
      }
    }
  } else if (target.kind === 'copyDir') {
    await fs.copy(sourcePath, target.outdir, { recursive: true });
  } else {
    throw new Error(`Unknown target kind: ${target.kind}`);
  }
}

console.log(
  `Static assets built to ${path.relative(projectRoot, distDir)} (${isProd ? 'production' : 'development'} mode)`
);
