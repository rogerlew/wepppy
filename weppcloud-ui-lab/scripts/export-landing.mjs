import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'

const scriptDir = fileURLToPath(new URL('.', import.meta.url))
const projectRoot = resolve(scriptDir, '..')
const distDir = resolve(projectRoot, 'dist')
const targetDir = resolve(projectRoot, '../wepppy/weppcloud/static/ui-lab')

if (!existsSync(distDir)) {
  console.error('No dist/ directory found. Run `npm run build` first.')
  process.exit(1)
}

rmSync(targetDir, { recursive: true, force: true })
mkdirSync(targetDir, { recursive: true })
cpSync(distDir, targetDir, { recursive: true })

console.log(`Exported landing bundle to ${targetDir}`)

// Reuse the locked landing renderer for optional run/dashboard vector basemaps.
const maplibreDir = resolve(projectRoot, 'node_modules/maplibre-gl')
const rendererTarget = resolve(targetDir, 'maplibre')
mkdirSync(rendererTarget, { recursive: true })
for (const name of ['maplibre-gl.js', 'maplibre-gl.css']) {
  cpSync(resolve(maplibreDir, 'dist', name), resolve(rendererTarget, name))
}
cpSync(resolve(maplibreDir, 'LICENSE.txt'), resolve(rendererTarget, 'LICENSE.txt'))
