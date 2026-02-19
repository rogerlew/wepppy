# Static Asset Build Pipeline

> **See also:** [AGENTS.md](../../../AGENTS.md) for Static Assets section and build command reference.

## Overview
- Third-party browser libraries (Leaflet, Bootstrap, PureCSS, etc.) are managed from `wepppy/weppcloud/static-src` via `npm` plus a small `vendor-sources/` fallback for assets that are not published on npm.
- `npm run build:dev` produces readable development assets under `static-src/dist/`; `npm run build` produces minified production assets.
- `npm run smoke` runs the Playwright smoke suite (backend must be reachable at `SMOKE_BASE_URL`; test-support endpoints are only required when auto-provisioning runs). Useful environment variables:
  - `TEST_SUPPORT_ENABLED=true` on the backend to expose `/weppcloud/tests/api/*` endpoints for run provisioning.
  - `SMOKE_CREATE_RUN` (`true` by default) to auto-provision a run via the test-support create-run endpoint.
  - `SMOKE_RUN_CONFIG` (default `dev_unit_1`) selects the configuration used when provisioning.
  - `SMOKE_RUN_OVERRIDES` optional JSON for config query params (e.g., `{ "general:dem_db": "ned1/2016" }`).
  - `SMOKE_RUN_PATH` to point at an existing run (skips provisioning).
  - `SMOKE_KEEP_RUN=true` keeps the provisioned run after the suite completes.
  - `SMOKE_BASE_URL` and `SMOKE_HEADLESS=false` adjust backend origin and browser mode.
- GL dashboard smoke specs skip RAP or comparison assertions automatically when the target run lacks those datasets; expect occasional `skipped` results rather than failures.
- Some runs legitimately lack RAP or comparison data; skips in those specs are expected and not treated as failures.
- `npm run smoke:theme-metrics` runs the Theme Lab contrast harness. It only needs the UI showcase route (`/ui/components/#theme-lab`) online, so no run provisioning is required. Reports land in `test-results/theme-metrics/` as both JSON and Markdown (consumed by CI and reviewers). You can drive the same run through `wctl run-playwright --suite theme-metrics --env local`.
- Docker builds copy the production bundle into `wepppy/weppcloud/static/vendor/` so images ship with everything baked in. The app entrypoint mirrors the bundle to `/srv/weppcloud/static` when `STATIC_ASSET_SYNC_DIR` is set (Compose prod does this for Caddy).

Common host-side commands (from repo root):
- `wctl run-npm install --legacy-peer-deps`
- `wctl run-npm build:dev` or `wctl run-npm build`
- `wctl run-npm lint`
- `wctl run-npm test`
- `wctl run-npm smoke`

## Local Development
1. Install Node 20 or newer.
2. From `wepppy/weppcloud/static-src` run `npm install --legacy-peer-deps` (only needed after dependency changes).
3. Build and sync assets with the helper script (from anywhere):
   - `wctl build-static-assets` for readable output.
   - `wctl build-static-assets --prod` for the minified bundle (automatically implied when wctl is configured for prod).
   - Script lives at `./wepppy/weppcloud/static-src/build-static-assets.sh` if you need to invoke it directly (supports `--prod`, `--force-install`, and `--skip-controllers`).
   - Controllers bundle (`controllers-gl.js`) is rebuilt by default; pass `--skip-controllers` to bypass it.
   - The script syncs `dist/vendor/` into `wepppy/weppcloud/static/vendor/` (gitignored) and copies `dist/js/archive_console.js` into `wepppy/weppcloud/static/js/archive_console.js`.

## Docker / Production
- `docker/Dockerfile` contains a `static-builder` stage (`node:20-alpine`) that runs `npm ci --legacy-peer-deps` and `npm run build`.
- The Python runtime stage copies `/app/dist/vendor/` into `/workdir/wepppy/wepppy/weppcloud/static/vendor/` and `/app/dist/js/archive_console.js` into `/workdir/wepppy/wepppy/weppcloud/static/js/archive_console.js`.
- `docker/docker-compose.prod.yml` sets:
  - `entrypoint: ./docker/weppcloud-entrypoint.sh`
  - `STATIC_ASSET_SYNC_DIR=/srv/weppcloud/static`
  - `CONTROLLERS_JS_EXTRA_OUTPUTS=/srv/weppcloud/static/js/controllers-gl.js`
- At container start the entrypoint writes `controllers-gl.js` and replaces `/srv/weppcloud/static/vendor/` so the Caddy container (which bind-mounts the same host path) serves current assets.

## Adding a New Library
1. `npm install <package>@<version>` inside `static-src` (prefer pinned versions).
2. Update `scripts/build.mjs` to copy/minify the relevant files into `dist/vendor/<name>/`.
3. Run `npm run build` and sync to `static/vendor/` locally.
4. Replace CDN references in templates with `{{ url_for('static', filename='vendor/<name>/<file>') }}`.
5. Rebuild Docker images (`docker compose build weppcloud`) to bake the new assets.
- If a library is not published on npm, drop its distribution files under `static-src/vendor-sources/<name>/` and reference them in `scripts/build.mjs` (see `purecss` as an example).

## Remaining CDN References
- Some secondary pages still reference CDN Bootstrap assets. Track TODOs via `rg "cdn.jsdelivr.net/npm/bootstrap"` and replace as we touch those templates.
- Leaflet plugins that are not published on npm (e.g., custom glify layers) remain vendored under `static/js/`.

## Playwright Test Artifacts

**IMPORTANT:** When writing custom artifacts in Playwright tests, never use directories managed by Playwright reporters:

- ❌ **`playwright-report/`** - Cleaned by HTML reporter on every run (configured in `playwright.config.mjs`)
- ✅ **`test-results/<custom-subdir>/`** - Safe for custom artifacts (Playwright only manages test-specific subdirectories)

Example from `theme-metrics.spec.js`:
```javascript
// Safe location - not cleaned by Playwright
const DEFAULT_REPORT_DIR = path.join('test-results', 'theme-metrics');
```

If test artifacts mysteriously disappear despite successful `fs.writeFile()` calls, check if they're being written to a directory that Playwright cleans asynchronously after test completion.
