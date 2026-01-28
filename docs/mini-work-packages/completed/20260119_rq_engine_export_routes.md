# Mini Work Package: rq-engine export routes (Flask export.py migration)
Status: Completed
Last Updated: 2026-01-19
Primary Areas: `wepppy/microservices/rq_engine/*`, `wepppy/export/*`, `wepppy/weppcloud/routes/__init__.py`, `wepppy/weppcloud/_blueprints_context.py`, `docs/schemas/rq-response-contract.md`

## Objective
Move long-running export endpoints out of Flask and into rq-engine (FastAPI), so exports execute in the rq-engine service and return results directly (no extra RQ job submission).

## Scope
- Add rq-engine export routes for ERMiT, GeoPackage, FileGDB, and prep details.
- Ensure responses follow the RQ response contract on errors.
- Document endpoints and expected inputs/outputs.

## Non-goals
- Changing export formats or file contents.
- Removing on-run-completion exports (handled by RQ workers).
- Refactoring export helpers in `wepppy/export/*` beyond rq-engine wiring.

## Current Call Sites
- No in-repo JS/template callers found (search: `rg "export/(ermit|geopackage|geodatabase|prep_details)"`).
- RQ engine endpoints are the canonical export URLs; Flask `export_bp` has been removed.
- Related background generation (not tied to export routes):
  - `wepppy/rq/wepp_rq.py` runs prep details + gpkg export on run completion.
  - `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` renders the prep details report from Ron summaries.

## rq-engine Routes
- `GET /rq-engine/api/runs/{runid}/{config}/export/ermit`
  - Run `create_ermit_input(wd)` and return file.
- `GET /rq-engine/api/runs/{runid}/{config}/export/geopackage`
  - Ensure `{runid}.gpkg` exists; run `gpkg_export(wd)` if missing; return file.
- `GET /rq-engine/api/runs/{runid}/{config}/export/geodatabase`
  - Ensure `{runid}.gdb.zip` exists; run `gpkg_export(wd)` if missing; return file.
- `GET /rq-engine/api/runs/{runid}/{config}/export/prep_details`
  - Run `export_hillslopes_prep_details(wd)` + `export_channels_prep_details(wd)`.
  - If `no_retrieve` query param set, return success JSON; else zip via `archive_project` and return file.

### Execution Model
- Run export work in rq-engine (FastAPI) using `run_in_threadpool` so the event loop stays responsive.
- No RQ job submission for these routes (per request). If timeouts are a concern, add explicit `asyncio.wait_for` guards and return a structured timeout error.

### Auth/Errors
- Use `require_jwt` + `authorize_run_access` with `rq:export` scope (session tokens include it).
- Use `error_response`/`error_response_with_traceback` from `rq_engine.responses` to honor `docs/schemas/rq-response-contract.md`.
 - Support `?pup=<relpath>` to resolve exports against a pup directory under the run root (reject unknown pups).

## Migration Plan (Completed)
1. **Add rq-engine router**: `wepppy/microservices/rq_engine/export_routes.py` with the four endpoints above; include router in `wepppy/microservices/rq_engine/__init__.py`.
2. **Implement file responses**: use `fastapi.responses.FileResponse` for downloads; guard missing files with structured errors.
3. **Remove Flask routes**: delete `wepppy/weppcloud/routes/export.py` and unregister `export_bp`.
4. **Update clients**: ensure any external clients use `/rq-engine/api/runs/{runid}/{config}/export/*`.
5. **Tests**: add microservice tests for rq-engine routes (success + missing file), and confirm error payloads conform to the RQ response schema.

## Validation Summary (2026-01-19)

Manual testing against `wc.bearhive.duckdns.org` with run `decimal-pleasing/disturbed9002_wbt`:

| Endpoint | Status | Content-Type | Response |
|----------|--------|--------------|----------|
| `/export/ermit` | 200 | application/zip | ERMiT_input_rattlesnake.zip (5 KB) |
| `/export/geopackage` | 200 | application/geopackage+sqlite3 | decimal-pleasing.gpkg (250 KB) |
| `/export/geodatabase` | 200 | application/zip | decimal-pleasing.gdb.zip (48 KB) |
| `/export/prep_details` | 200 | application/zip | decimal-pleasing_prep_details.zip (10 KB) |
| `/export/prep_details?no_retrieve=1` | 200 | application/json | `{"status":"ok"}` |

**Auth/error handling verified:**
- Missing `Authorization` header → 401 `{"error":{"message":"Missing Authorization header","code":"unauthorized"}}`
- Invalid token → 401 `{"error":{"message":"Invalid token: Invalid token format","code":"unauthorized"}}`

All responses conform to `docs/schemas/rq-response-contract.md`.

## Open Questions
- Do we want a global timeout guard (e.g., 30–60s) for synchronous exports, or should these rely on reverse proxy timeouts?
- Any remaining external clients still hitting `/runs/<runid>/<config>/export/*` need a coordinated update.
