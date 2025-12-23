# Mini Work Package: Upload Blueprint for Caddy Timeouts

**Status:** Draft  
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

### Phase 2 - Route migration + client updates
1. Add `/upload/...` equivalents for all upload endpoints, preferably via `add_url_rule` so the same view functions serve both paths.
2. Ensure run-scoped uploads still get the run context preprocessor (add `upload_bp` to `_RUN_CONTEXT_BLUEPRINTS` if runid/config appear in the URL).
3. Update front-end upload calls to target `/upload`:
   - Prefer extending `url_for_run()` with an optional prefix override for easier regex matching in diagnostics.
   - Update the upload flows in controllers/templates to use the new helper.
4. Keep `/weppcloud` upload endpoints temporarily for compatibility, but add logging to quantify remaining usage.

### Phase 3 - Hardening + deprecation
1. Enforce the 20-minute timeout values in Caddy config for `/upload` and confirm `/weppcloud` keeps the 30s default.
2. Add regression tests or smoke checks for upload endpoints that validate the `/upload` prefix.
3. Optionally return deprecation warnings or redirects from `/weppcloud` to `/upload` once clients are updated.

## Documentation Updates (in scope)
- `docker/README.md`: document the `/upload` reverse proxy handler and timeout configuration.
- `wepppy/weppcloud/README.md`: explain how `/upload` differs from `/weppcloud` and where to route file uploads.
- `wepppy/weppcloud/controllers_js/README.md`: document the new upload helper or prefix override.
- Any UI docs referencing upload endpoints (add a short note in the relevant `docs/ui-docs/*` page if needed).

## Open Questions
- Should `/upload` honor `SITE_PREFIX`, or be hard-rooted?
- Do we need to maintain `/weppcloud` upload endpoints indefinitely for external tooling?
