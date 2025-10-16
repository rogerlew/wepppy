# Static Asset Build Pipeline

## Overview
- All third-party browser libraries (Leaflet, Bootstrap, DataTables, jQuery, etc.) are now pulled in via `npm` from `wepppy/weppcloud/static-src`.
- `npm run build:dev` produces readable development assets under `static-src/dist/`; `npm run build` produces minified production assets.
- Docker builds copy the production bundle into `wepppy/weppcloud/static/vendor/` so images ship with everything baked in. The app entrypoint mirrors the bundle to `/srv/weppcloud/static` when `STATIC_ASSET_SYNC_DIR` is set (Compose prod does this for Caddy).

## Local Development
1. Install Node 20 or newer.
2. From `wepppy/weppcloud/static-src` run `npm install --legacy-peer-deps` (only needed after dependency changes).
3. Build and sync assets with the helper script (from anywhere):
   - `wctl build-static-assets` for readable output.
   - `wctl build-static-assets --prod` for the minified bundle (automatically implied when wctl is configured for prod).
   - Script lives at `./wepppy/weppcloud/static-src/build-static-assets.sh` if you need to invoke it directly.
   - Add `--force-install` if you need to refresh `node_modules`.
   - The script automatically rsyncs into `wepppy/weppcloud/static/vendor/`, which is `.gitignore`d so dev builds stay local.

## Docker / Production
- `docker/Dockerfile` contains a `static-builder` stage (`node:20-alpine`) that runs `npm ci --legacy-peer-deps` and `npm run build`.
- The Python runtime stage copies `/app/dist/` into `/workdir/wepppy/wepppy/weppcloud/static/vendor/`.
- `docker/docker-compose.prod.yml` sets:
  - `entrypoint: ./docker/weppcloud-entrypoint.sh`
  - `STATIC_ASSET_SYNC_DIR=/srv/weppcloud/static`
  - `CONTROLLERS_JS_EXTRA_OUTPUTS=/srv/weppcloud/static/js/controllers.js`
- At container start the entrypoint writes `controllers.js` and replaces `/srv/weppcloud/static/vendor/` so the Caddy container (which bind-mounts the same host path) serves current assets.

## Adding a New Library
1. `npm install <package>@<version>` inside `static-src` (prefer pinned versions).
2. Update `scripts/build.mjs` to copy/minify the relevant files into `dist/vendor/<name>/`.
3. Run `npm run build` and sync to `static/vendor/` locally.
4. Replace CDN references in templates with `{{ url_for('static', filename='vendor/<name>/<file>') }}`.
5. Rebuild Docker images (`docker compose build weppcloud`) to bake the new assets.

## Remaining CDN References
- Some secondary pages still reference CDN Bootstrap/jQuery assets. Track TODOs via `rg "cdn.jsdelivr.net/npm/bootstrap"` and replace as we touch those templates.
- Leaflet plugins that are not published on npm (e.g., custom glify layers) remain vendored under `static/js/`.
