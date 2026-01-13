# RQ API Migration Pre-Removal Review (2026-01-12)

## Blocking issues (must-fix before removing `/rq/api/*`)
- None found in runtime callers or proxy config.

## Non-blocking observations
- Routing parity looks complete: every legacy `/rq/api/*` endpoint listed in `docs/mini-work-packages/20260112_rq_api_migration.md` has a kebab-case `/rq-engine/api/*` route under `wepppy/microservices/rq_engine/*` (enqueue, jobinfo/jobstatus, run-sync, and upload routes are present).
- Auth/session routing matches the JWT spec: session token issuance is `POST /rq-engine/api/runs/<runid>/<config>/session-token` (`wepppy/microservices/rq_engine/session_routes.py`), jobstatus/jobinfo remain open (`wepppy/microservices/rq_engine/job_routes.py`), and canceljob is protected with JWT + run marker (`wepppy/microservices/rq_engine/job_routes.py`).
- Caddy has the `/rq-engine` proxy block with long timeouts and no `/upload` handler (`docker/caddy/Caddyfile`).
- HUC fire uploads now target `/rq-engine/api/huc-fire/tasks/upload-sbs/` and the template injects a user JWT; anonymous users are blocked unless authenticated.
- rq-engine upload helpers now emit `result` for uploads and the disturbed controller reads `result`, aligning with `docs/schemas/rq-response-contract.md`.
- Comprehensive stacktrace details are required in `error.details`. Remaining routes to update:
- [x] `wepppy/microservices/rq_engine/job_routes.py` — `GET /jobstatus/{job_id}`, `GET /jobinfo/{job_id}`, `POST /jobinfo`, `POST /canceljob/{job_id}`
- [x] `wepppy/microservices/rq_engine/batch_routes.py` — `POST /batch/_/{batch_name}/run-batch`
- [x] `wepppy/microservices/rq_engine/culvert_routes.py` — `POST /culverts-wepp-batch/`, `POST /culverts-wepp-batch/{batch_uuid}/retry/{point_id}`
- [x] `wepppy/microservices/rq_engine/climate_routes.py` — `POST /runs/{runid}/{config}/build-climate`
- [x] `wepppy/microservices/rq_engine/soils_routes.py` — `POST /runs/{runid}/{config}/build-soils`
- [x] `wepppy/microservices/rq_engine/landuse_routes.py` — `POST /runs/{runid}/{config}/build-landuse`
- [x] `wepppy/microservices/rq_engine/treatments_routes.py` — `POST /runs/{runid}/{config}/build-treatments`
- [x] `wepppy/microservices/rq_engine/landuse_soils_routes.py` — `POST /landuse-and-soils`, `GET /landuse-and-soils/{job_id}.tar.gz`
- [x] `wepppy/microservices/rq_engine/dss_export_routes.py` — `POST /runs/{runid}/{config}/post-dss-export-rq`
- [x] `wepppy/microservices/rq_engine/wepp_routes.py` — `POST /runs/{runid}/{config}/run-wepp`, `POST /runs/{runid}/{config}/run-wepp-watershed`
- [x] `wepppy/microservices/rq_engine/omni_routes.py` — `POST /runs/{runid}/{config}/run-omni`, `POST /runs/{runid}/{config}/run-omni-contrasts`
- [x] `wepppy/microservices/rq_engine/ash_routes.py` — `POST /runs/{runid}/{config}/run-ash`
- [x] `wepppy/microservices/rq_engine/debris_flow_routes.py` — `POST /runs/{runid}/{config}/run-debris-flow`
- [x] `wepppy/microservices/rq_engine/rhem_routes.py` — `POST /runs/{runid}/{config}/run-rhem`
- [x] `wepppy/microservices/rq_engine/rap_ts_routes.py` — `POST /runs/{runid}/{config}/acquire-rap-ts`
- [x] `wepppy/microservices/rq_engine/openet_ts_routes.py` — `POST /runs/{runid}/{config}/acquire-openet-ts`
- [x] `wepppy/microservices/rq_engine/watershed_routes.py` — `POST /runs/{runid}/{config}/fetch-dem-and-build-channels`, `POST /runs/{runid}/{config}/set-outlet`, `POST /runs/{runid}/{config}/build-subcatchments-and-abstract-watershed`
- [x] `wepppy/microservices/rq_engine/run_sync_routes.py` — `POST /run-sync`, `GET /run-sync/status`
- [x] `wepppy/microservices/rq_engine/session_routes.py` — `POST /runs/{runid}/{config}/session-token`
- [x] `wepppy/microservices/rq_engine/upload_climate_routes.py` — `POST /runs/{runid}/{config}/tasks/upload-cli/`
- [x] `wepppy/microservices/rq_engine/upload_disturbed_routes.py` — `POST /runs/{runid}/{config}/tasks/upload-sbs/`, `POST /runs/{runid}/{config}/tasks/upload-cover-transform`
- [x] `wepppy/microservices/rq_engine/upload_huc_fire_routes.py` — `POST /huc-fire/tasks/upload-sbs/`
- [x] `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` — `POST /batch/_/{batch_name}/upload-geojson`, `POST /batch/_/{batch_name}/upload-sbs-map`
- [x] `wepppy/microservices/rq_engine/debug_routes.py` — `GET /runs/{runid}/{config}/hello-world`, `POST /runs/{runid}/{config}/hello-world`
- [x] `wepppy/microservices/rq_engine/fork_archive_routes.py` — `POST /runs/{runid}/{config}/fork`, `POST /runs/{runid}/{config}/archive`, `POST /runs/{runid}/{config}/restore-archive`, `POST /runs/{runid}/{config}/delete-archive` (only some error paths include stacktraces today)

## Runtime `/rq/api` or `/upload` references found
- None in runtime callers (controllers/templates/routes). Legacy references remain only in profile recorder tooling for replay compatibility (`wepppy/profile_recorder/*`), which is not on the runtime request path.

## Recommendation
Ready to remove legacy `/rq/api/*` routes in prod.
