# Endpoint Inventory Freeze (2026-02-08)

Source-of-truth inventory captured directly from:
- `wepppy/microservices/rq_engine/*.py`
- `wepppy/weppcloud/routes/bootstrap.py`

Snapshot summary:
- Total endpoints inventoried: **71**
- Classification counts: **agent-facing 51**, **internal 14**, **ui-only 6**
- Canonical owner counts: **rq-engine 68**, **Flask wrapper 3**

## Inventory Table

| Method | Path | Module | Function | Classification | Owner | Auth | Scope | Mutates | Notes |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/api/batch/_/{batch_name}/run-batch` | `wepppy/microservices/rq_engine/batch_routes.py:25` | `run_batch` | internal | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Role gate: `["admin"]`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/batch/_/{batch_name}/upload-geojson` | `wepppy/microservices/rq_engine/upload_batch_runner_routes.py:125` | `upload_geojson` | internal | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Role gate: `["Admin"]`. Synchronous BatchRunner resource mutation; no queue. |
| POST | `/api/batch/_/{batch_name}/upload-sbs-map` | `wepppy/microservices/rq_engine/upload_batch_runner_routes.py:254` | `upload_sbs_map` | internal | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Role gate: `["Admin"]`. Synchronous BatchRunner resource mutation; no queue. |
| POST | `/api/canceljob/{job_id}` | `wepppy/microservices/rq_engine/job_routes.py:81` | `canceljob` | agent-facing | rq-engine | JWT Bearer | `rq:status` | mutating | If fetched job metadata includes a run ID, enforces `require_session_marker`. No enqueue; cancels existing RQ job(s). |
| POST | `/api/culverts-wepp-batch/` | `wepppy/microservices/rq_engine/culvert_routes.py:40` | `culverts_wepp_batch` | agent-facing | rq-engine | JWT Bearer | `culvert:batch:submit` | mutating | Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` | `wepppy/microservices/rq_engine/culvert_routes.py:135` | `culverts_retry_run` | agent-facing | rq-engine | JWT Bearer | `culvert:batch:retry` | mutating | Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/huc-fire/tasks/upload-sbs/` | `wepppy/microservices/rq_engine/upload_huc_fire_routes.py:67` | `upload_huc_fire_sbs` | internal | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Creates a new disturbed run synchronously from upload payload; no queue. |
| POST | `/api/jobinfo` | `wepppy/microservices/rq_engine/job_routes.py:278` | `jobinfo_batch` | agent-facing | rq-engine | Open by default (`RQ_ENGINE_POLL_AUTH_MODE`) | `rq:status` when auth mode validates JWT | read-only | Polling remains open in default mode; optional/required JWT modes plus rate limiting + audit logging are now available. |
| GET | `/api/jobinfo/{job_id}` | `wepppy/microservices/rq_engine/job_routes.py:226` | `jobinfo` | agent-facing | rq-engine | Open by default (`RQ_ENGINE_POLL_AUTH_MODE`) | `rq:status` when auth mode validates JWT | read-only | Polling remains open in default mode; optional/required JWT modes plus rate limiting + audit logging are now available. |
| GET | `/api/jobstatus/{job_id}` | `wepppy/microservices/rq_engine/job_routes.py:177` | `jobstatus` | agent-facing | rq-engine | Open by default (`RQ_ENGINE_POLL_AUTH_MODE`) | `rq:status` when auth mode validates JWT | read-only | Polling remains open in default mode; optional/required JWT modes plus rate limiting + audit logging are now available. |
| POST | `/api/landuse-and-soils` | `wepppy/microservices/rq_engine/landuse_soils_routes.py:46` | `build_landuse_and_soils` | internal | rq-engine | Open | - | mutating | Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| GET | `/api/landuse-and-soils/{job_id}.tar.gz` | `wepppy/microservices/rq_engine/landuse_soils_routes.py:73` | `download_landuse_and_soils` | internal | rq-engine | Open | - | read-only | Open endpoint (no JWT). |
| POST | `/api/run-sync` | `wepppy/microservices/rq_engine/run_sync_routes.py:141` | `run_sync` | internal | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Admin-only orchestration; enqueues `run_sync_rq` and optional dependent `migrations_rq`. |
| GET | `/api/run-sync/status` | `wepppy/microservices/rq_engine/run_sync_routes.py:212` | `run_sync_status` | internal | rq-engine | JWT Bearer | - | read-only | Admin-only status read over RQ registries plus `RunMigration` records; no queue. |
| POST | `/api/runs/{runid}/{config}/acquire-openet-ts` | `wepppy/microservices/rq_engine/openet_ts_routes.py:29` | `acquire_openet_ts` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/acquire-rap-ts` | `wepppy/microservices/rq_engine/rap_ts_routes.py:75` | `acquire_rap_ts` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/archive` | `wepppy/microservices/rq_engine/fork_archive_routes.py:275` | `archive_run` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/bootstrap/checkout` | `wepppy/microservices/rq_engine/bootstrap_routes.py:271` | `bootstrap_checkout` | agent-facing | rq-engine | JWT Bearer | `bootstrap:checkout` | mutating | Run access check: `authorize_run_access`. Synchronous bootstrap git checkout under lock; no queue. |
| GET | `/api/runs/{runid}/{config}/bootstrap/commits` | `wepppy/microservices/rq_engine/bootstrap_routes.py:237` | `bootstrap_commits` | agent-facing | rq-engine | JWT Bearer | `bootstrap:read` | read-only | Run access check: `authorize_run_access`. Read-only bootstrap metadata fetch; no queue. |
| GET | `/api/runs/{runid}/{config}/bootstrap/current-ref` | `wepppy/microservices/rq_engine/bootstrap_routes.py:254` | `bootstrap_current_ref` | agent-facing | rq-engine | JWT Bearer | `bootstrap:read` | read-only | Run access check: `authorize_run_access`. Read-only bootstrap metadata fetch; no queue. |
| POST | `/api/runs/{runid}/{config}/bootstrap/enable` | `wepppy/microservices/rq_engine/bootstrap_routes.py:186` | `bootstrap_enable` | agent-facing | rq-engine | JWT Bearer | `bootstrap:enable` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/bootstrap/mint-token` | `wepppy/microservices/rq_engine/bootstrap_routes.py:207` | `bootstrap_mint_token` | agent-facing | rq-engine | JWT Bearer | `bootstrap:token:mint` | mutating | Run access check: `authorize_run_access`. Synchronous bootstrap clone-token minting; no queue. |
| POST | `/api/runs/{runid}/{config}/build-climate` | `wepppy/microservices/rq_engine/climate_routes.py:34` | `build_climate` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/build-landuse` | `wepppy/microservices/rq_engine/landuse_routes.py:43` | `build_landuse` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/build-soils` | `wepppy/microservices/rq_engine/soils_routes.py:42` | `build_soils` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/build-subcatchments-and-abstract-watershed` | `wepppy/microservices/rq_engine/watershed_routes.py:649` | `build_subcatchments_and_abstract_watershed` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/build-treatments` | `wepppy/microservices/rq_engine/treatments_routes.py:42` | `build_treatments` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/delete-archive` | `wepppy/microservices/rq_engine/fork_archive_routes.py:415` | `delete_archive` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Synchronous archive deletion on disk; no queue. |
| POST | `/api/runs/{runid}/{config}/delete-omni-contrasts` | `wepppy/microservices/rq_engine/omni_routes.py:798` | `delete_omni_contrasts` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| GET | `/api/runs/{runid}/{config}/export/ermit` | `wepppy/microservices/rq_engine/export_routes.py:61` | `export_ermit` | agent-facing | rq-engine | JWT Bearer | `rq:export` | read-only | Run access check: `authorize_run_access`. May generate export artifacts synchronously before file response. |
| GET | `/api/runs/{runid}/{config}/export/geodatabase` | `wepppy/microservices/rq_engine/export_routes.py:116` | `export_geodatabase` | agent-facing | rq-engine | JWT Bearer | `rq:export` | read-only | Run access check: `authorize_run_access`. May generate export artifacts synchronously before file response. |
| GET | `/api/runs/{runid}/{config}/export/geopackage` | `wepppy/microservices/rq_engine/export_routes.py:86` | `export_geopackage` | agent-facing | rq-engine | JWT Bearer | `rq:export` | read-only | Run access check: `authorize_run_access`. May generate export artifacts synchronously before file response. |
| GET | `/api/runs/{runid}/{config}/export/prep_details` | `wepppy/microservices/rq_engine/export_routes.py:146` | `export_prep_details` | agent-facing | rq-engine | JWT Bearer | `rq:export` | read-only | Run access check: `authorize_run_access`. May generate export artifacts synchronously before file response. |
| GET | `/api/runs/{runid}/{config}/export/prep_details/` | `wepppy/microservices/rq_engine/export_routes.py:147` | `export_prep_details` | agent-facing | rq-engine | JWT Bearer | `rq:export` | read-only | Run access check: `authorize_run_access`. May generate export artifacts synchronously before file response. |
| POST | `/api/runs/{runid}/{config}/fetch-dem-and-build-channels` | `wepppy/microservices/rq_engine/watershed_routes.py:486` | `fetch_dem_and_build_channels` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/fork` | `wepppy/microservices/rq_engine/fork_archive_routes.py:159` | `fork_project` | agent-facing | rq-engine | Optional JWT; anonymous CAPTCHA path | `rq:enqueue` (if bearer token is used) | mutating | Optional bearer token path calls `authorize_run_access`; anonymous path requires CAPTCHA and public-run eligibility checks. Async enqueue and pre-creates target run metadata. |
| GET | `/api/runs/{runid}/{config}/hello-world` | `wepppy/microservices/rq_engine/debug_routes.py:40` | `hello_world` | internal | rq-engine | Open | - | mutating | Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/hello-world` | `wepppy/microservices/rq_engine/debug_routes.py:41` | `hello_world` | internal | rq-engine | Open | - | mutating | Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/migrate-run` | `wepppy/microservices/rq_engine/migration_routes.py:79` | `migrate_run` | internal | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Access model: `_ensure_run_access` (Admin override + session-marker support for session tokens). Async enqueue; returns `job_id`, `status_url`, `message`, and `result`. |
| POST | `/api/runs/{runid}/{config}/post-dss-export-rq` | `wepppy/microservices/rq_engine/dss_export_routes.py:52` | `post_dss_export` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/restore-archive` | `wepppy/microservices/rq_engine/fork_archive_routes.py:341` | `restore_archive` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/run-ash` | `wepppy/microservices/rq_engine/ash_routes.py:146` | `run_ash` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/run-debris-flow` | `wepppy/microservices/rq_engine/debris_flow_routes.py:38` | `run_debris_flow` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/run-omni` | `wepppy/microservices/rq_engine/omni_routes.py:756` | `run_omni` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/run-omni-contrasts` | `wepppy/microservices/rq_engine/omni_routes.py:770` | `run_omni_contrasts` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/run-omni-contrasts-dry-run` | `wepppy/microservices/rq_engine/omni_routes.py:784` | `run_omni_contrasts_dry_run` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | read-only | Run access check: `authorize_run_access`. Dry-run endpoint; returns contrast report in `result`; no queue. |
| POST | `/api/runs/{runid}/{config}/run-rhem` | `wepppy/microservices/rq_engine/rhem_routes.py:28` | `run_rhem` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/run-swat` | `wepppy/microservices/rq_engine/swat_routes.py:49` | `run_swat` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/run-swat-noprep` | `wepppy/microservices/rq_engine/bootstrap_routes.py:326` | `run_swat_noprep` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/run-wepp` | `wepppy/microservices/rq_engine/wepp_routes.py:173` | `run_wepp` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/run-wepp-npprep` | `wepppy/microservices/rq_engine/bootstrap_routes.py:271` | `run_wepp_npprep` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/run-wepp-watershed` | `wepppy/microservices/rq_engine/wepp_routes.py:204` | `run_wepp_watershed` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/run-wepp-watershed-no-prep` | `wepppy/microservices/rq_engine/bootstrap_routes.py:301` | `run_wepp_watershed_noprep` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/session-token` | `wepppy/microservices/rq_engine/session_routes.py:144` | `issue_session_token` | agent-facing | rq-engine | Bearer or session cookie (public-run fallback) | `rq:status` (if bearer token is used) | mutating | Run access model: bearer tokens must include the run claim; cookie path checks Flask session key (or allows public runs). No queue; returns session token payload. |
| POST | `/api/runs/{runid}/{config}/set-outlet` | `wepppy/microservices/rq_engine/watershed_routes.py:584` | `set_outlet` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/swat/print-prt` | `wepppy/microservices/rq_engine/swat_routes.py:82` | `update_swat_print_prt` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Synchronous SWAT `print.prt` mutation; no queue. |
| POST | `/api/runs/{runid}/{config}/swat/print-prt/meta` | `wepppy/microservices/rq_engine/swat_routes.py:134` | `update_swat_print_prt_meta` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Synchronous SWAT `print.prt` mutation; no queue. |
| POST | `/api/runs/{runid}/{config}/tasks/upload-cli/` | `wepppy/microservices/rq_engine/upload_climate_routes.py:38` | `upload_cli` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Async enqueue; response includes `job_id` (with `status_url`/`message` where implemented). |
| POST | `/api/runs/{runid}/{config}/tasks/upload-cover-transform` | `wepppy/microservices/rq_engine/upload_disturbed_routes.py:87` | `upload_cover_transform` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Synchronous upload/validation mutation; no queue. |
| POST | `/api/runs/{runid}/{config}/tasks/upload-dem/` | `wepppy/microservices/rq_engine/watershed_routes.py:440` | `upload_dem` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Synchronous upload/validation mutation; no queue. |
| POST | `/api/runs/{runid}/{config}/tasks/upload-sbs/` | `wepppy/microservices/rq_engine/upload_disturbed_routes.py:34` | `upload_sbs` | agent-facing | rq-engine | JWT Bearer | `rq:enqueue` | mutating | Run access check: `authorize_run_access`. Synchronous upload/validation mutation; no queue. |
| POST | `/create/` | `wepppy/microservices/rq_engine/project_routes.py:221` | `create` | agent-facing | rq-engine | JWT/rq_token or CAPTCHA | `rq:enqueue` (token-auth paths) | mutating | Creates run directory + Ron config + TTL, then redirects (`303`) to run URL. No queue. |
| GET | `/health` | `wepppy/microservices/rq_engine/__init__.py:51` | `health` | internal | rq-engine | Open | - | read-only | Service liveness endpoint. |
| GET | `/api/bootstrap/verify-token` | `wepppy/weppcloud/routes/bootstrap.py:145` | `verify_token` | internal | Flask wrapper | HTTP Basic + bootstrap JWT | n/a (audience + runid claims) | read-only | Caddy `forward_auth` endpoint. Validates forwarded git path, bootstrap JWT audience/runid, run eligibility, and bootstrap opt-in. |
| POST | `/api/bootstrap/verify-token` | `wepppy/weppcloud/routes/bootstrap.py:145` | `verify_token` | internal | Flask wrapper | HTTP Basic + bootstrap JWT | n/a (audience + runid claims) | read-only | Caddy `forward_auth` endpoint. Same behavior as GET variant. |
| POST | `/runs/<string:runid>/<config>/bootstrap/checkout` | `wepppy/weppcloud/routes/bootstrap.py:126` | `bootstrap_checkout` | ui-only | rq-engine | Flask session (`login_required`) | n/a | mutating | Thin wrapper around shared bootstrap operation in `wepppy/weppcloud/bootstrap/api_shared.py`; deterministic parity with rq-engine contract. |
| GET | `/runs/<string:runid>/<config>/bootstrap/commits` | `wepppy/weppcloud/routes/bootstrap.py:112` | `bootstrap_commits` | ui-only | rq-engine | Flask session (`login_required`) | n/a | read-only | Thin wrapper around shared bootstrap operation in `wepppy/weppcloud/bootstrap/api_shared.py`; deterministic parity with rq-engine contract. |
| GET | `/runs/<string:runid>/<config>/bootstrap/current-ref` | `wepppy/weppcloud/routes/bootstrap.py:145` | `bootstrap_current_ref` | ui-only | rq-engine | Flask session (`login_required`) | n/a | read-only | Thin wrapper around shared bootstrap operation in `wepppy/weppcloud/bootstrap/api_shared.py`; deterministic parity with rq-engine contract. |
| POST | `/runs/<string:runid>/<config>/bootstrap/disable` | `wepppy/weppcloud/routes/bootstrap.py:302` | `bootstrap_disable` | ui-only | Flask wrapper | Flask role gate (`roles_accepted`) | n/a | mutating | Flask-only admin toggle for `Run.bootstrap_disabled`; synchronous DB mutation; no queue. |
| POST | `/runs/<string:runid>/<config>/bootstrap/enable` | `wepppy/weppcloud/routes/bootstrap.py:74` | `enable_bootstrap` | ui-only | rq-engine | Flask session (`login_required`) | n/a | mutating | Thin wrapper around shared bootstrap operation in `wepppy/weppcloud/bootstrap/api_shared.py`; deterministic parity with rq-engine contract. |
| POST | `/runs/<string:runid>/<config>/bootstrap/mint-token` | `wepppy/weppcloud/routes/bootstrap.py:96` | `mint_bootstrap_token` | ui-only | rq-engine | Flask session (`login_required`) | n/a | mutating | Thin wrapper around shared bootstrap operation in `wepppy/weppcloud/bootstrap/api_shared.py`; deterministic parity with rq-engine contract. |

## Duplication And Convergence

| Bootstrap Operation | rq-engine Endpoint | Flask Wrapper Endpoint | Canonical Owner | Migration State |
|---|---|---|---|---|
| Enable bootstrap | `POST /api/runs/{runid}/{config}/bootstrap/enable` | `POST /runs/<runid>/<config>/bootstrap/enable` | `rq-engine` | Still duplicated (thin wrapper parity) |
| Mint bootstrap token | `POST /api/runs/{runid}/{config}/bootstrap/mint-token` | `POST /runs/<runid>/<config>/bootstrap/mint-token` | `rq-engine` | Still duplicated (thin wrapper parity) |
| List bootstrap commits | `GET /api/runs/{runid}/{config}/bootstrap/commits` | `GET /runs/<runid>/<config>/bootstrap/commits` | `rq-engine` | Still duplicated (thin wrapper parity) |
| Get bootstrap current ref | `GET /api/runs/{runid}/{config}/bootstrap/current-ref` | `GET /runs/<runid>/<config>/bootstrap/current-ref` | `rq-engine` | Still duplicated (thin wrapper parity) |
| Checkout bootstrap commit | `POST /api/runs/{runid}/{config}/bootstrap/checkout` | `POST /runs/<runid>/<config>/bootstrap/checkout` | `rq-engine` | Still duplicated (thin wrapper parity) |
| Disable bootstrap | *(none in rq-engine)* | `POST /runs/<runid>/<config>/bootstrap/disable` | `Flask wrapper` | Flask-only |
| Verify git token (forward auth) | *(none in rq-engine)* | `GET/POST /api/bootstrap/verify-token` | `Flask wrapper` | Flask-only (infra exception) |
| No-prep WEPP/SWAT runs | `POST /api/runs/{runid}/{config}/run-wepp-npprep`, `.../run-wepp-watershed-no-prep`, `.../run-swat-noprep` | *(none in Flask bootstrap routes)* | `rq-engine` | Already converged |

## Frozen Decisions

1. Agent-facing Bootstrap operations are canonically owned by `rq-engine`.
2. Minimum Bootstrap scope set is frozen as: `bootstrap:enable`, `bootstrap:token:mint`, `bootstrap:read`, `bootstrap:checkout`.
3. Job polling endpoints remain open/read-only by default (`GET /api/jobstatus/{job_id}`, `GET /api/jobinfo/{job_id}`, `POST /api/jobinfo`), with optional token modes for operational hardening.
4. Endpoint inventory is now frozen as the contract baseline for follow-on OpenAPI/auth alignment work.

## Known Exceptions

- `GET/POST /api/bootstrap/verify-token` remains in Flask because Caddy `forward_auth` currently targets this path and expects Basic-auth style verification semantics.
- `POST /runs/<runid>/<config>/bootstrap/disable` remains Flask-only (`Admin`/`Root` UI/admin control); no rq-engine equivalent exists yet.
- `POST /create/` is intentionally mounted without the `/api` prefix (`wepppy/microservices/rq_engine/__init__.py` includes `project_router` without `prefix="/api"`).
- Frozen scope minimums for Bootstrap remain the contract baseline; rq-engine enforces the explicit `bootstrap:*` scopes.

## Post-Freeze Enforcement Update (2026-02-08)

- Bootstrap scope enforcement is now active in rq-engine:
  - `bootstrap:enable`
  - `bootstrap:token:mint`
  - `bootstrap:read`
  - `bootstrap:checkout`
- `rq:enqueue` is not accepted as a substitute for Bootstrap operations.
- Flask duplicate endpoints (`enable`, `mint-token`, `commits`, `current-ref`,
  `checkout`) now run as thin wrappers around shared operations in
  `wepppy/weppcloud/bootstrap/api_shared.py`; `/api/bootstrap/verify-token`
  and `bootstrap/disable` remain Flask-owned exceptions.
- Polling hardening landed while preserving default openness:
  - Auth mode switch: `open` (default), `token_optional`, `required` via
    `RQ_ENGINE_POLL_AUTH_MODE`.
  - Rate limit defaults:
    - `RQ_ENGINE_POLL_RATE_LIMIT_COUNT=120`
    - `RQ_ENGINE_POLL_RATE_LIMIT_WINDOW_SECONDS=60`
  - Structured audit logging now records endpoint, outcome, job id, caller,
    and client IP.
- Inventory drift guard added:
  - Script: `tools/check_endpoint_inventory.py`
  - Pytest/CI hook: `tests/tools/test_endpoint_inventory_guard.py`
  - Fails on route drift against this artifact and on missing ownership/
    classification metadata for tracked routes.
