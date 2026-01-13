# Mini Work Package: rq/api migration to rq-engine (staged deprecation)
Status: Complete (Phase 5 validation)
Last Updated: 2026-01-12
Primary Areas: `wepppy/microservices/rq_engine/*`, `wepppy/weppcloud/controllers_js/*`, `wepppy/weppcloud/controllers_js/utils.js`, `wepppy/weppcloud/controllers_js/http.js`, `wepppy/weppcloud/routes/rq/job_dashboard/*`

## Objective
Move all run-scoped RQ endpoints from Flask (`/weppcloud/rq/api/*`) to rq-engine (`/rq-engine/api/*`) and remove the Flask routes after dev validation. Complete the migration in dev before prod.

## Current State Review
- rq-engine JWT auth is in place (Phase 6 JWT mini work package complete).
- Flask `/rq/api/*` and `/upload/*` routes are removed in dev.
- rq-engine owns the run-scoped enqueue routes, culvert batch routes, and cancel job endpoint.
- Controllers now target `/rq-engine/api/*` for queue triggers and polling.

## Scope
- Confirm rq-engine parity for all run-scoped enqueue endpoints.
- Verify controller calls use the rq-engine base path.
- Keep `/rq/api/*` and `/upload/*` removed after dev validation.
- Ensure rq-engine routes stay kebab-case and callers align.
- Verify jobstatus/jobinfo remain read-only and open (as agreed).

## Non-goals
- Changing payload schemas or response contracts beyond endpoint location.
- Reworking auth beyond existing JWT/session behavior.

## Plan
### Phase 1 - Inventory + parity map (completed)
- Enumerate all Flask `/rq/api/*` routes and map to rq-engine equivalents.
- Identify endpoints still missing in rq-engine (likely run-scoped job enqueues).
- Decide which endpoints must remain Flask-only (if any).

**Flask `/rq/api/*` inventory (legacy; removed in dev)**
| Method | Route | Source |
| --- | --- | --- |
| GET/POST | `/runs/<runid>/<config>/rq/api/hello_world` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/session-token` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/batch/_/<batch_name>/rq/api/run-batch` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/rq/api/landuse_and_soils` | `wepppy/weppcloud/routes/rq/api/api.py` |
| GET | `/rq/api/landuse_and_soils/<uuid>.tar.gz` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/fetch_dem_and_build_channels` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/set_outlet` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/build_subcatchments_and_abstract_watershed` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/build_landuse` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/build_treatments` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/build_soils` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/build_climate` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/post_dss_export_rq` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/run_wepp` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/run_wepp_watershed` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/run_omni` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/run_omni_contrasts` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/run_ash` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/run_debris_flow` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/run_rhem_rq` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/acquire_rap_ts` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/acquire_openet_ts` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/fork` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/archive` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/restore-archive` | `wepppy/weppcloud/routes/rq/api/api.py` |
| POST | `/runs/<runid>/<config>/rq/api/delete-archive` | `wepppy/weppcloud/routes/rq/api/api.py` |
| GET | `/rq/api/jobstatus/<job_id>` | `wepppy/weppcloud/routes/rq/api/jobinfo.py` |
| GET | `/rq/api/jobinfo/<job_id>` | `wepppy/weppcloud/routes/rq/api/jobinfo.py` |
| POST | `/rq/api/jobinfo` | `wepppy/weppcloud/routes/rq/api/jobinfo.py` |
| GET | `/rq/api/canceljob/<job_id>` | `wepppy/weppcloud/routes/rq/api/jobinfo.py` |
| POST | `/rq/api/run-sync` | `wepppy/weppcloud/routes/run_sync_dashboard/run_sync_dashboard.py` |
| GET | `/rq/api/run-sync/status` | `wepppy/weppcloud/routes/run_sync_dashboard/run_sync_dashboard.py` |

**Flask `/upload/*` inventory (legacy; removed in dev)**
| Method | Route | Source |
| --- | --- | --- |
| GET | `/upload/health` | `wepppy/weppcloud/routes/upload_bp.py` |
| POST | `/upload/runs/<runid>/<config>/tasks/upload_cli/` | `wepppy/weppcloud/routes/upload_bp.py` |
| POST | `/upload/runs/<runid>/<config>/tasks/upload_sbs/` | `wepppy/weppcloud/routes/upload_bp.py` |
| POST | `/upload/runs/<runid>/<config>/tasks/upload_cover_transform` | `wepppy/weppcloud/routes/upload_bp.py` |
| POST | `/upload/huc-fire/tasks/upload_sbs/` | `wepppy/weppcloud/routes/upload_bp.py` |
| POST | `/upload/batch/_/<batch_name>/upload-geojson` | `wepppy/weppcloud/routes/upload_bp.py` |
| POST | `/upload/batch/_/<batch_name>/upload-sbs-map` | `wepppy/weppcloud/routes/upload_bp.py` |
| POST | `/upload/runs/<runid>/<config>/rq/api/build_landuse` | `wepppy/weppcloud/routes/upload_bp.py` |
| POST | `/upload/runs/<runid>/<config>/rq/api/build_treatments` | `wepppy/weppcloud/routes/upload_bp.py` |
| POST | `/upload/runs/<runid>/<config>/rq/api/run_ash` | `wepppy/weppcloud/routes/upload_bp.py` |
| POST | `/upload/runs/<runid>/<config>/rq/api/run_omni` | `wepppy/weppcloud/routes/upload_bp.py` |
| POST | `/upload/runs/<runid>/<config>/rq/api/run_omni_contrasts` | `wepppy/weppcloud/routes/upload_bp.py` |

**rq-engine routes already present**
| Method | Route | Source |
| --- | --- | --- |
| GET | `/rq-engine/api/jobstatus/{job_id}` | `wepppy/microservices/rq_engine/job_routes.py` |
| GET | `/rq-engine/api/jobinfo/{job_id}` | `wepppy/microservices/rq_engine/job_routes.py` |
| POST | `/rq-engine/api/jobinfo` | `wepppy/microservices/rq_engine/job_routes.py` |
| POST | `/rq-engine/api/canceljob/{job_id}` | `wepppy/microservices/rq_engine/job_routes.py` |
| POST | `/rq-engine/api/culverts-wepp-batch/` | `wepppy/microservices/rq_engine/culvert_routes.py` |
| POST | `/rq-engine/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` | `wepppy/microservices/rq_engine/culvert_routes.py` |
| POST | `/rq-engine/api/landuse-and-soils` | `wepppy/microservices/rq_engine/landuse_soils_routes.py` |
| GET | `/rq-engine/api/landuse-and-soils/{uuid}.tar.gz` | `wepppy/microservices/rq_engine/landuse_soils_routes.py` |
| POST | `/rq-engine/api/batch/_/{batch_name}/run-batch` | `wepppy/microservices/rq_engine/batch_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/build-landuse` | `wepppy/microservices/rq_engine/landuse_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/build-soils` | `wepppy/microservices/rq_engine/soils_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/build-climate` | `wepppy/microservices/rq_engine/climate_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/build-treatments` | `wepppy/microservices/rq_engine/treatments_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/post-dss-export-rq` | `wepppy/microservices/rq_engine/dss_export_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/run-wepp` | `wepppy/microservices/rq_engine/wepp_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/run-wepp-watershed` | `wepppy/microservices/rq_engine/wepp_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/run-omni` | `wepppy/microservices/rq_engine/omni_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/run-omni-contrasts` | `wepppy/microservices/rq_engine/omni_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/run-ash` | `wepppy/microservices/rq_engine/ash_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/run-debris-flow` | `wepppy/microservices/rq_engine/debris_flow_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/run-rhem` | `wepppy/microservices/rq_engine/rhem_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/acquire-rap-ts` | `wepppy/microservices/rq_engine/rap_ts_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/acquire-openet-ts` | `wepppy/microservices/rq_engine/openet_ts_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/fetch-dem-and-build-channels` | `wepppy/microservices/rq_engine/watershed_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/set-outlet` | `wepppy/microservices/rq_engine/watershed_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/build-subcatchments-and-abstract-watershed` | `wepppy/microservices/rq_engine/watershed_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/fork` | `wepppy/microservices/rq_engine/fork_archive_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/archive` | `wepppy/microservices/rq_engine/fork_archive_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/restore-archive` | `wepppy/microservices/rq_engine/fork_archive_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/delete-archive` | `wepppy/microservices/rq_engine/fork_archive_routes.py` |
| POST | `/rq-engine/api/run-sync` | `wepppy/microservices/rq_engine/run_sync_routes.py` |
| GET | `/rq-engine/api/run-sync/status` | `wepppy/microservices/rq_engine/run_sync_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/tasks/upload-cli/` | `wepppy/microservices/rq_engine/upload_climate_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/tasks/upload-sbs/` | `wepppy/microservices/rq_engine/upload_disturbed_routes.py` |
| POST | `/rq-engine/api/runs/<runid>/<config>/tasks/upload-cover-transform` | `wepppy/microservices/rq_engine/upload_disturbed_routes.py` |
| POST | `/rq-engine/api/huc-fire/tasks/upload-sbs/` | `wepppy/microservices/rq_engine/upload_huc_fire_routes.py` |
| POST | `/rq-engine/api/batch/_/<batch_name>/upload-geojson` | `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` |
| POST | `/rq-engine/api/batch/_/<batch_name>/upload-sbs-map` | `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` |

### Phase 2 - rq-engine endpoint parity (completed)
- Implement missing rq-engine endpoints with identical request/response payloads.
- Reuse existing RQ job enqueuing helpers where possible.
- Ensure auth aligns with the JWT model (scopes, run claims, denylist).

**Parity plan (proposed rq-engine route modules)**
| Module | Routes | Notes |
| --- | --- | --- |
| `job_routes.py` | jobstatus/jobinfo/canceljob | Already present. |
| `culvert_routes.py` | culvert batch submit/retry | Already present. |
| `session_routes.py` | `/rq-engine/api/runs/<runid>/<config>/session-token` | Port session token issuance + Redis marker. |
| `batch_routes.py` | `/rq-engine/api/batch/_/<batch_name>/run-batch` | Port batch runner enqueue logic (JWT admin required). |
| `landuse_soils_routes.py` | `/rq-engine/api/landuse-and-soils` + tar download | Port landuse/soils bundle flow. |
| `watershed_routes.py` | fetch-dem-and-build-channels, set-outlet, build-subcatchments-and-abstract-watershed | Run-scoped watershed pipeline. |
| `landuse_routes.py` | build-landuse | Run-scoped RQ enqueue. |
| `soils_routes.py` | build-soils | Run-scoped RQ enqueue. |
| `climate_routes.py` | build-climate | Run-scoped RQ enqueue. |
| `treatments_routes.py` | build-treatments | Implemented (rq-engine run-scoped enqueue). |
| `dss_export_routes.py` | post-dss-export-rq | Implemented (rq-engine run-scoped enqueue). |
| `wepp_routes.py` | run-wepp, run-wepp-watershed | Implemented (rq-engine run-scoped enqueue + response parity). |
| `omni_routes.py` | run-omni, run-omni-contrasts | Implemented (upload-capable endpoints). |
| `ash_routes.py` | run-ash | Implemented (upload-capable endpoint). |
| `debris_flow_routes.py` | run-debris-flow | Implemented (run-scoped RQ enqueue). |
| `rhem_routes.py` | run-rhem | Implemented (run-scoped RQ enqueue). |
| `rap_ts_routes.py` | acquire-rap-ts | Implemented (run-scoped RQ enqueue). |
| `openet_ts_routes.py` | acquire-openet-ts | Implemented (run-scoped RQ enqueue). |
| `fork_archive_routes.py` | fork, archive, restore-archive, delete-archive | Implemented. |
| `run_sync_routes.py` | `/rq-engine/api/run-sync`, `/rq-engine/api/run-sync/status` | Implemented (admin role required). |
| `debug_routes.py` | hello_world | Optional; decide to drop vs keep as a smoke endpoint. |

**Implementation notes**
- Prefer moving shared logic into `wepppy/rq/*` helpers or new shared modules to avoid importing Flask handlers into rq-engine.
- Keep routers in separate files and include them in `wepppy/microservices/rq_engine/__init__.py`.
- Use kebab-case for all new rq-engine route paths and update controller call sites (no new underscores).
- Batch Runner run submissions now require an admin JWT; the manage page injects a `rqEngineToken` bootstrap value for the controller.

### Phase 2.5 - Upload proxy migration (completed)
- Port upload routes to rq-engine under `/rq-engine/api/*` with identical payloads.
- Update controller calls to use `/rq-engine/api/*` upload endpoints (drop `/upload` usage).
- Drop the `/upload/*` proxy entirely (Caddy rule removed).

**Upload parity plan (rq-engine route groups)**
| Group | Routes | Notes |
| --- | --- | --- |
| `upload_climate_routes.py` | `/rq-engine/api/runs/<runid>/<config>/tasks/upload-cli/` | Implemented. |
| `upload_disturbed_routes.py` | `/rq-engine/api/runs/<runid>/<config>/tasks/upload-sbs/`, `/rq-engine/api/runs/<runid>/<config>/tasks/upload-cover-transform` | Implemented. |
| `upload_huc_fire_routes.py` | `/rq-engine/api/huc-fire/tasks/upload-sbs/` | Implemented (JWT user token required). |
| `upload_batch_runner_routes.py` | `/rq-engine/api/batch/_/<batch_name>/upload-geojson`, `/rq-engine/api/batch/_/<batch_name>/upload-sbs-map` | Implemented (admin role required). |

**Upload implementation notes**
- Extract request-agnostic helpers from Flask upload handlers (avoid importing Flask view functions into rq-engine).
- Replace Flask `request.files` usage with FastAPI `UploadFile` handling.
- Keep timeout behavior on `/rq-engine*` (already long in Caddy); `/upload*` routing is removed.

### Phase 3 - Controller migration (completed)
- Add a run-scoped helper that targets rq-engine (e.g., `url_for_rq_engine_run()`).
- Update controllers that call `rq/api/*` to use the new helper.

### Phase 4 - Remove Flask `/rq/api/*` and `/upload/*` (completed)
- Delete `/rq/api/*` and `/upload/*` routes once rq-engine parity + controller migration are validated in dev.
- Remove any route imports/registrations so hot reload startup stays clean.
- Update any docs/tests that still reference `/rq/api/*` or `/upload/*`.

### Phase 5 - Validation + cleanup plan (completed)
- Verify UI workflows: enqueue + polling + cancel + results display.
- Confirm `jobstatus/jobinfo` remain reachable without auth tokens.
- Add tests for rq-engine parity (including upload routes).
- Write a follow-on removal checklist once prod is migrated.
- Manual smoke test completed in dev; schedule a fresh agent review before removing legacy routes in prod.

## Exit Criteria
- All UI controller calls use `/rq-engine/api/*` for rq endpoints.
- rq-engine covers the full `/rq/api/*` surface with matching payloads.
- Flask `/rq/api/*` routes removed and no longer imported.
- Upload routes are handled under `/rq-engine/api/*` and clients no longer rely on `/upload`.
- Dev environment validated; ready for prod deployment.

## Risks / Notes
- Removing Flask endpoints is a hard cut; dev validation must cover all controllers.
- Ensure any new helper preserves `url_for_run()` semantics so run-scoped URLs stay correct.
- Upload endpoints must continue to honor long timeouts (covered by `/rq-engine` reverse proxy).
- Keep rq-engine routes organized in separate modules (avoid a single monolithic router file).
- Set `SESSION_COOKIE_PATH=/` so rq-engine endpoints can read Flask session cookies.

## Open Questions
- Confirm rq-engine base path for browser use: same-origin `/rq-engine` vs direct `:8042`.
- Should rq-engine be exposed outside the default `/rq-engine` reverse proxy path?
