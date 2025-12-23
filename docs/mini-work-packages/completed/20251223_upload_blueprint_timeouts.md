# Mini Work Package: Upload Blueprint for Caddy Timeouts

**Status:** Complete  
**Last Updated:** 2025-12-23  
**Primary Areas:** `docker/caddy/Caddyfile`, `wepppy/weppcloud/app.py`, `wepppy/weppcloud/_blueprints_context.py`, `wepppy/weppcloud/routes/*`, `wepppy/weppcloud/controllers_js/*`, `wepppy/weppcloud/README.md`, `docker/README.md`

---

## Objective
Reduce the risk of Caddy's 30s upstream timeout for file uploads by routing upload endpoints under `/upload` with a longer timeout, while keeping non-upload traffic under `/weppcloud`.

## Current Routing Snapshot
- Caddy handles `/weppcloud/*` in `docker/caddy/Caddyfile` with `uri strip_prefix /weppcloud`, then `reverse_proxy weppcloud:8000` and `header_up X-Forwarded-Prefix /weppcloud`.
- Flask configures `ProxyFix(... x_prefix=1)` in `wepppy/weppcloud/app.py`, so `X-Forwarded-Prefix` becomes `request.script_root`.
- Flask blueprints define routes without a `/weppcloud` prefix (paths start with `/runs/...`, `/batch/...`, `/huc-fire/...`), so `/weppcloud` is currently a pure proxy prefix.
- Deployment target: `wc.bearhive.duckdns.org` (forest) behind pfSense HAProxy; wait for HAProxy health checks to pass after Caddy reloads to avoid transient 502s.

## Upload Route Inventory (current)
**Dedicated upload endpoints**
- `POST /runs/<runid>/<config>/tasks/upload_cli/` (CLIGEN CLI) in `wepppy/weppcloud/routes/nodb_api/climate_bp.py`
- `POST /runs/<runid>/<config>/tasks/upload_sbs/` (SBS raster) in `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`
- `POST /runs/<runid>/<config>/tasks/upload_cover_transform` (cover transform) in `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`
- `POST /huc-fire/tasks/upload_sbs/` (creates run) in `wepppy/weppcloud/routes/huc_fire.py`
- `POST /batch/_/<batch_name>/upload-geojson` in `wepppy/weppcloud/routes/batch_runner/batch_runner_bp.py`
- `POST /batch/_/<batch_name>/upload-sbs-map` in `wepppy/weppcloud/routes/batch_runner/batch_runner_bp.py`

**Upload-capable endpoints (file present only for certain modes)**
- `POST /runs/<runid>/<config>/rq/api/build_landuse` (user-defined landuse map via `input_upload_landuse`) in `wepppy/weppcloud/routes/rq/api/api.py`
- `POST /runs/<runid>/<config>/rq/api/build_treatments` (user-defined treatments map via `input_upload_landuse`) in `wepppy/weppcloud/routes/rq/api/api.py`
- `POST /runs/<runid>/<config>/rq/api/run_ash` (ash maps via `input_upload_ash_load`, `input_upload_ash_type_map` when `ash_depth_mode=2`) in `wepppy/weppcloud/routes/rq/api/api.py`
- `POST /runs/<runid>/<config>/rq/api/run_omni` and `POST /runs/<runid>/<config>/rq/api/run_omni_contrasts` (SBS files via `scenarios[i][sbs_file]`) in `wepppy/weppcloud/routes/rq/api/api.py`

## Plan (multi-stage)
### Phase 1 - Blueprint + routing scaffolding
1. Add an `upload_bp` with `url_prefix="/upload"` (new module under `wepppy/weppcloud/routes/`).
2. Register the blueprint in `wepppy/weppcloud/routes/__init__.py` and `wepppy/weppcloud/_blueprints_context.py`.
3. Add a lightweight `/upload/health` or `/upload/ping` route for routing validation.
4. Update `docker/caddy/Caddyfile` with a `/upload*` handler ahead of `/weppcloud*`, using a larger `transport http` timeout (20 minutes). Prefer `uri strip_prefix /upload` so Flask keeps the existing route paths and the blueprint can be an alias-only wrapper.
5. Smoke test routing: confirm `/upload/health` hits Flask and that `/weppcloud/health` still works.

## Phase 1 Handoff Summary
- Added `/upload` reverse-proxy routing in `docker/caddy/Caddyfile` using `handle_path` (strips `/upload`), sets `X-Forwarded-Prefix /upload`, and applies 20-minute upstream timeouts.
- Updated `/health` to emit an upload-specific JSON payload when `request.script_root == "/upload"` so `/upload/health` is distinct from `/weppcloud/health` in `wepppy/weppcloud/_blueprints_context.py`.
- Verified on forest behind pfSense HAProxy:

```bash
curl https://wc.bearhive.duckdns.org/upload/health
```

```json
{
  "message": "upload health endpoint",
  "prefix": "/upload",
  "scope": "upload",
  "status": "ok"
}
```

- Note: No upload-specific blueprint was added; `/upload` currently aliases existing Flask routes via proxy stripping. Phase 2 will add explicit `/upload/...` endpoints if needed.

### Phase 1 Implementation References (commit 51e549b007)
`docker/caddy/Caddyfile`:
```caddy
handle_path /upload* {
    reverse_proxy weppcloud:8000 {
        header_up X-Forwarded-Prefix /upload
        transport http {
            read_timeout 20m
            response_header_timeout 20m
        }
    }
}
```

`wepppy/weppcloud/_blueprints_context.py`:
```python
@app.route("/health")
def health():
    script_root = (request.script_root or "").rstrip("/")
    if script_root == "/upload":
        return jsonify({
            "status": "ok",
            "scope": "upload",
            "message": "upload health endpoint",
            "prefix": request.script_root or "",
        })
    return jsonify("OK")
```

### Phase 2 - Route migration + client updates
1. Add `/upload/...` equivalents for all upload endpoints, preferably via `add_url_rule` so the same view functions serve both paths.
2. Ensure run-scoped uploads still get the run context preprocessor (add `upload_bp` to `_RUN_CONTEXT_BLUEPRINTS` if runid/config appear in the URL).
3. Update front-end upload calls to target `/upload`:
   - Prefer extending `url_for_run()` with an optional prefix override for easier regex matching in diagnostics.
   - Update the upload flows in controllers/templates to use the new helper.
4. Keep `/weppcloud` upload endpoints temporarily for compatibility, but add logging to quantify remaining usage.

## Phase 2 Handoff Summary
- Added `upload_bp` under `/upload` that aliases upload-capable endpoints (`tasks/upload_*`, batch uploads, `rq/api/*` with uploads, and `/huc-fire/tasks/upload_sbs/`) in `wepppy/weppcloud/routes/upload_bp.py`, registered it in `wepppy/weppcloud/routes/__init__.py` and `wepppy/weppcloud/_blueprints_context.py` for run-context preprocessing.
- Implemented legacy prefix logging via `log_upload_prefix_usage()` in `wepppy/weppcloud/utils/uploads.py` (stub updated in `wepppy/weppcloud/utils/uploads.pyi`) and wired it into upload endpoints (`wepppy/weppcloud/routes/nodb_api/climate_bp.py`, `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`, `wepppy/weppcloud/routes/huc_fire.py`, `wepppy/weppcloud/routes/batch_runner/batch_runner_bp.py`, `wepppy/weppcloud/routes/rq/api/api.py`).
- Updated upload clients to call `/upload`:
  - `url_for_run()` accepts a `{ prefix: "/upload" }` override in `wepppy/weppcloud/controllers_js/utils.js`.
  - Upload-capable controllers now use the `/upload` prefix (`wepppy/weppcloud/controllers_js/climate.js`, `wepppy/weppcloud/controllers_js/disturbed.js`, `wepppy/weppcloud/controllers_js/baer.js`, `wepppy/weppcloud/controllers_js/wepp.js`, `wepppy/weppcloud/controllers_js/landuse.js`, `wepppy/weppcloud/controllers_js/treatments.js`, `wepppy/weppcloud/controllers_js/ash.js`, `wepppy/weppcloud/controllers_js/omni.js`).
  - Batch runner uploads now use `/upload/batch/...` via `uploadBaseUrl` in `wepppy/weppcloud/controllers_js/batch_runner.js` (test updated in `wepppy/weppcloud/controllers_js/__tests__/batch_runner.test.js`).
  - HUC fire upload request now posts to `/upload/huc-fire/tasks/upload_sbs/` in `wepppy/weppcloud/templates/huc-fire/index.html`.
- `WCHttp` now bypasses `site_prefix` for `/upload` URLs to prevent `/weppcloud/upload` routing (`wepppy/weppcloud/controllers_js/http.js`).
- Verified on forest: `/upload` routes resolve and upload requests succeed without the `/weppcloud` prefix (after rebuilding controller assets and restarting the stack).

### Phase 2 Implementation References (commit 51e549b007)
`wepppy/weppcloud/routes/upload_bp.py`:
```python
upload_bp = Blueprint("upload", __name__, url_prefix="/upload")
upload_bp.add_url_rule(
    "/runs/<string:runid>/<config>/tasks/upload_cli/",
    view_func=task_upload_cli,
    methods=["POST"],
)
```

`wepppy/weppcloud/controllers_js/utils.js`:
```javascript
if (options && typeof options === "object" && Object.prototype.hasOwnProperty.call(options, "prefix")) {
    outputPrefix = normalizePrefix(options.prefix);
}
```

`wepppy/weppcloud/controllers_js/http.js`:
```javascript
if (url === "/upload" || url.indexOf("/upload/") === 0) {
    return url;
}
```

### Phase 1-2 Sanity Check (current tree)
- Caddy `handle_path /upload*` strips the prefix, so proxied `/upload/health` resolves via `/health` with `request.script_root == "/upload"`; `upload_bp` keeps `/upload/...` working when hitting Flask directly.
- `upload_bp` is included in `_RUN_CONTEXT_BLUEPRINTS` so run-scoped `/upload/...` requests still get context preprocessing (`wepppy/weppcloud/routes/__init__.py`).
- JS upload requests use `url_for_run(..., { prefix: "/upload" })` and `WCHttp` bypasses `site_prefix` to avoid `/weppcloud/upload` routing.

### Phase 3 - Hardening + deprecation
1. Enforce the 20-minute timeout values in Caddy config for `/upload` and confirm `/weppcloud` keeps the 30s default.
2. Add regression tests or smoke checks for upload endpoints that validate the `/upload` prefix.
3. Optionally return deprecation warnings or redirects from `/weppcloud` to `/upload` once clients are updated.

## Phase 3 Handoff Summary
- Removed legacy upload-prefix logging helper/imports (`log_upload_prefix_usage`) from upload routes; `/weppcloud` endpoints now rely on `/upload` usage without extra legacy logging.
- Added tests covering `/upload` behavior:
  - `wepppy/weppcloud/controllers_js/__tests__/http.test.js` verifies `/upload` URLs bypass `site_prefix`.
  - `tests/weppcloud/routes/test_upload_bp.py` checks `/upload/health` payload.
- Manual end-to-end upload verification completed on forest; full endpoint coverage still pending.

## Documentation Updates (completed)
- `docker/README.md`: documented the `/upload` reverse proxy handler and timeout configuration.
- `wepppy/weppcloud/README.md`: explained `/upload` routing, health check, and timeout intent.
- `wepppy/weppcloud/controllers_js/README.md`: documented the `url_for_run` prefix override for uploads.
- `docs/ui-docs/ui-style-guide.md`: updated the file upload pattern to use `/upload` prefix overrides.
- `docs/ui-docs/control-ui-styling/sbs_controls_behavior.md`: noted `/upload` prefix usage in SBS upload flow.
- `docs/ui-docs/control-ui-styling/control-inventory.md`: annotated upload-capable endpoints with `/upload` guidance.
- `docs/ui-docs/control-ui-styling/control-components.md`: added `/upload` guidance for treatments uploads.
- `docs/dev-notes/wc-forest-bearhive-duck-dns-flask-security-installation.md`: captured `/upload` routing and HAProxy health-check wait notes.
- `readme.md`: added operational notes for `/upload` timeout and HAProxy behavior.

## Open Questions
- Should `/upload` honor `SITE_PREFIX`, or be hard-rooted?
- Do we need to maintain `/weppcloud` upload endpoints indefinitely for external tooling?

## Closeout
- All phases complete; `/upload` routing and 20-minute timeouts are live on forest.
- Manual end-to-end upload verification completed on forest; full endpoint coverage testing remains a follow-up.
- Legacy `/weppcloud` upload endpoints remain available; no redirect/deprecation behavior enabled.
