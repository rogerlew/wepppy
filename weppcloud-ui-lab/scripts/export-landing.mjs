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
