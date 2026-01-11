# Observed Error Schema Usages - RQ API

## 1. Summary of Observed Patterns
- Success flag variants: `Success` (capital) dominates weppcloud rq/api; `success` (lowercase) appears in rq-engine validation errors and batch runner routes.
- Error payloads (weppcloud): `error_factory` returns `{Success: False, Error: <msg>}` with HTTP 200 unless overridden; `exception_factory` returns `{Success: False, Error: <msg>, StackTrace: [..]}` with HTTP 500.
- Error payloads (rq-engine): `error_response` returns `{Success: False, Error: <msg>, StackTrace: [..]}` with HTTP 500; `validation_error_response` returns `{success: False, errors: [{code, message, path?, detail?}]}` with HTTP 400.
- Job polling schemas omit success flags: jobstatus/jobinfo return `{id, status, ...}` and use `status: not_found` for missing jobs (HTTP 200).
- Job submission responses typically use `{Success: True, job_id: <id>}`; some routes return `{Success: True, Content: <string|dict>}` for batch-only input updates (no job enqueued).
- Inconsistent casing for keys: `Success` vs `success`, `Error` vs `error`, `job_id` vs `jobId`; several controllers normalize or check both variants.
- Non-JSON success responses exist (`/rq/api/landuse_and_soils/<uuid>.tar.gz` sends a file); errors still return JSON via `error_factory`.
- Observed mismatch: rq-engine `culvert_routes.py` calls `error_response(..., status_code=...)` but `error_response` does not accept `status_code`, so the helper always emits HTTP 500 with `Success` payload.

## 2. Endpoint Inventory

### rq-engine (FastAPI)
| Endpoint | Method | Status Codes | Response Schema (keys) | Uses success/Success | Semantic Meaning | Callers |
| --- | --- | --- | --- | --- | --- | --- |
| `/rq-engine/api/jobstatus/{job_id}` | GET | 200, 500 | 200: `id, runid, status, started_at, ended_at`; 500: `Success, Error, StackTrace` | none (200), `Success` (500) | Job status aggregate | `wepppy/weppcloud/controllers_js/control_base.js`, `wepppy/profile_recorder/playback.py` |
| `/rq-engine/api/jobinfo/{job_id}` | GET | 200, 500 | 200: `id, runid, status, result, started_at, ended_at, description, elapsed_s, exc_info, children`; 500: `Success, Error, StackTrace` | none (200), `Success` (500) | Job tree detail | `wepppy/weppcloud/controllers_js/status_stream.js`, `wepppy/profile_recorder/playback.py`, `wepppy/weppcloud/controllers_js/control_base.js` |
| `/rq-engine/api/jobinfo` | POST | 200, 500 | 200: `jobs, job_ids`; 500: `Success, Error, StackTrace` | none (200), `Success` (500) | Batch job info lookup | `wepppy/weppcloud/controllers_js/batch_runner.js` |
| `/rq-engine/api/culverts-wepp-batch/` | POST | 200, 400, 500 | 200: `job_id, culvert_batch_uuid, status_url`; 400: `success, errors`; 500: `Success, Error, StackTrace` | `success` (400), `Success` (500) | Culvert batch ingestion + job enqueue | No in-repo client found |
| `/rq-engine/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` | POST | 200, 500 (intended 400/404) | 200: `job_id, culvert_batch_uuid, point_id, status_url`; 500: `Success, Error, StackTrace` | `Success` (500) | Retry single culvert run | No in-repo client found |

### weppcloud rq/api (Flask)
| Endpoint | Method | Status Codes | Response Schema (keys) | Uses success/Success | Semantic Meaning | Callers |
| --- | --- | --- | --- | --- | --- | --- |
| `/rq/api/jobstatus/{job_id}` | GET | 200, 500 | 200: `id, runid, status, started_at, ended_at`; 500: `Success, Error, StackTrace` | none (200), `Success` (500) | Job status fallback | `wepppy/weppcloud/controllers_js/control_base.js`, `wepppy/profile_recorder/playback.py` |
| `/rq/api/jobinfo/{job_id}` | GET | 200, 500 | 200: `id, runid, status, result, started_at, ended_at, description, elapsed_s, exc_info, children`; 500: `Success, Error, StackTrace` | none (200), `Success` (500) | Job info fallback | `wepppy/weppcloud/controllers_js/status_stream.js`, `wepppy/weppcloud/controllers_js/control_base.js`, `wepppy/profile_recorder/playback.py` |
| `/rq/api/jobinfo` | POST | 200, 500 | 200: `jobs, job_ids`; 500: `Success, Error, StackTrace` | none (200), `Success` (500) | Batch job info fallback | `wepppy/weppcloud/controllers_js/batch_runner.js` |
| `/rq/api/canceljob/{job_id}` | GET | 200, 500 | 200: `Success`; 500: `Success, Error, StackTrace` | `Success` | Cancel RQ job | No in-repo client found |
| `/runs/<runid>/<config>/rq/api/hello_world` | GET, POST | 200, 500 | 200: `Success, job_id, exc_info, is_failed`; 500: `Success, Error, StackTrace` | `Success` | Enqueue hello_world job | No in-repo client found |
| `/batch/_/<batch_name>/rq/api/run-batch` | POST | 200, 404, 500 | 200: `success, job_id, message`; 404: `success, error`; 500: `Success, Error, StackTrace` | `success` (lowercase) | Enqueue batch run | `wepppy/weppcloud/controllers_js/batch_runner.js` |
| `/rq/api/landuse_and_soils` | POST | 200, 500 | 200: `Success, job_id` or `Success, Error` (error_factory); 500: `Success, Error, StackTrace` | `Success` | Enqueue landuse+soils prep job | No in-repo client found |
| `/rq/api/landuse_and_soils/<uuid>.tar.gz` | GET | 200 | 200: file download or `Success, Error` (error_factory) | `Success` (error path) | Download landuse/soils bundle | No in-repo client found |
| `/runs/<runid>/<config>/rq/api/fetch_dem_and_build_channels` | POST | 200, 500 | 200: `Success, job_id` or `Success, Content`; 500: `Success, Error, StackTrace` | `Success` | Enqueue channel delineation or set batch inputs | `wepppy/weppcloud/controllers_js/channel_delineation.js`, `wepppy/weppcloud/controllers_js/channel_gl.js` |
| `/runs/<runid>/<config>/rq/api/set_outlet` | POST | 200, 500 | 200: `Success, job_id`; 500: `Success, Error, StackTrace` | `Success` | Enqueue outlet set | `wepppy/weppcloud/controllers_js/outlet_gl.js` |
| `/runs/<runid>/<config>/rq/api/build_subcatchments_and_abstract_watershed` | POST | 200, 500 | 200: `Success, job_id` or `Success, Content`; 500: `Success, Error, StackTrace` | `Success` | Enqueue subcatchment build or set batch inputs | `wepppy/weppcloud/controllers_js/subcatchment_delineation.js`, `wepppy/weppcloud/controllers_js/subcatchments_gl.js` |
| `/runs/<runid>/<config>/rq/api/build_landuse` | POST | 200, 500 | 200: `Success, job_id` or `Success, Content` or `Success, Error` (error_factory); 500: `Success, Error, StackTrace` | `Success` | Enqueue landuse build or set batch inputs | `wepppy/weppcloud/controllers_js/landuse.js` |
| `/runs/<runid>/<config>/rq/api/build_treatments` | POST | 200, 500 | 200: `Success, job_id` or `Success, Error` (error_factory); 500: `Success, Error, StackTrace` | `Success` | Enqueue treatments build | `wepppy/weppcloud/controllers_js/treatments.js` |
| `/runs/<runid>/<config>/rq/api/build_soils` | POST | 200, 500 | 200: `Success, job_id` or `Success, Content`; 500: `Success, Error, StackTrace` | `Success` | Enqueue soils build or set batch inputs | `wepppy/weppcloud/controllers_js/soil.js` |
| `/runs/<runid>/<config>/rq/api/build_climate` | POST | 200, 500 | 200: `Success, job_id` or `Success, Content`; 500: `Success, Error, StackTrace` | `Success` | Enqueue climate build or set batch inputs | `wepppy/weppcloud/controllers_js/climate.js` |
| `/runs/<runid>/<config>/rq/api/post_dss_export_rq` | POST | 200, 500 | 200: `Success, job_id` or `Success, Error` (error_factory); 500: `Success, Error, StackTrace` | `Success` | Enqueue DSS export job | `wepppy/weppcloud/controllers_js/dss_export.js` |
| `/runs/<runid>/<config>/rq/api/run_wepp` | POST | 200, 500 | 200: `Success, job_id`; 500: `Success, Error, StackTrace` | `Success` | Enqueue WEPP hillslope run | `wepppy/weppcloud/controllers_js/wepp.js` |
| `/runs/<runid>/<config>/rq/api/run_wepp_watershed` | POST | 200, 500 | 200: `Success, job_id`; 500: `Success, Error, StackTrace` | `Success` | Enqueue WEPP watershed run | `wepppy/weppcloud/controllers_js/wepp.js` |
| `/runs/<runid>/<config>/rq/api/run_omni` | POST | 200, 500 | 200: `Success, job_id` or `Success, Error` (error_factory); 500: `Success, Error, StackTrace` | `Success` | Enqueue Omni scenarios | `wepppy/weppcloud/controllers_js/omni.js` |
| `/runs/<runid>/<config>/rq/api/run_omni_contrasts` | POST | 200, 500 | 200: `Success, job_id` or `Success, Error` (error_factory); 500: `Success, Error, StackTrace` | `Success` | Enqueue Omni contrasts | `wepppy/weppcloud/controllers_js/omni.js` |
| `/runs/<runid>/<config>/rq/api/run_ash` | POST | 200, 500 | 200: `Success, job_id`; 500: `Success, Error, StackTrace` | `Success` | Enqueue ash transport | `wepppy/weppcloud/controllers_js/ash.js` |
| `/runs/<runid>/<config>/rq/api/run_debris_flow` | POST | 200, 500 | 200: `Success, job_id`; 500: `Success, Error, StackTrace` | `Success` | Enqueue debris flow fit | `wepppy/weppcloud/controllers_js/debris_flow.js` |
| `/runs/<runid>/<config>/rq/api/run_rhem_rq` | POST | 200, 500 | 200: `Success, job_id`; 500: `Success, Error, StackTrace` | `Success` | Enqueue RHEM run | `wepppy/weppcloud/controllers_js/rhem.js` |
| `/runs/<runid>/<config>/rq/api/acquire_rap_ts` | POST | 200, 500 | 200: `Success, job_id, payload?`; 500: `Success, Error, StackTrace` | `Success` | Enqueue RAP TS acquisition | `wepppy/weppcloud/controllers_js/rap_ts.js` |
| `/runs/<runid>/<config>/rq/api/acquire_openet_ts` | POST | 200, 500 | 200: `Success, job_id, payload?`; 500: `Success, Error, StackTrace` | `Success` | Enqueue OpenET TS acquisition | `wepppy/weppcloud/controllers_js/openet_ts.js` |
| `/runs/<runid>/<config>/rq/api/fork` | POST | 200, 403, 404, 500 | 200: `Success, job_id, new_runid, undisturbify`; 403: `Success, Error` (error_factory); 404 via abort; 500: `Success, Error, StackTrace` | `Success` | Enqueue fork | No in-repo client found |
| `/runs/<runid>/<config>/rq/api/archive` | POST | 200, 500 | 200: `Success, job_id`; 500: `Success, Error, StackTrace` | `Success` | Enqueue archive job | `wepppy/weppcloud/static/js/archive_console.js` |
| `/runs/<runid>/<config>/rq/api/restore-archive` | POST | 200, 500 | 200: `Success, job_id`; 500: `Success, Error, StackTrace` | `Success` | Enqueue restore job | `wepppy/weppcloud/static/js/archive_console.js` |
| `/runs/<runid>/<config>/rq/api/delete-archive` | POST | 200, 500 | 200: `Success`; 500: `Success, Error, StackTrace` | `Success` | Delete archive | `wepppy/weppcloud/static/js/archive_console.js` |
| `/rq/api/run-sync` | POST | 200, 500 | 200: `Success, sync_job_id, migration_job_id?`; 500: `Success, Error, StackTrace` | `Success` | Enqueue run sync + optional migrations | `wepppy/weppcloud/controllers_js/run_sync_dashboard.js` |
| `/rq/api/run-sync/status` | GET | 200, 500 | 200: `jobs, migrations`; 500: `Success, Error, StackTrace` | none (200), `Success` (500) | Run sync job/migration status | `wepppy/weppcloud/controllers_js/run_sync_dashboard.js` |

## 3. Client Callsite Inventory

### Frontend callsites
- `wepppy/weppcloud/controllers_js/channel_delineation.js`, `wepppy/weppcloud/controllers_js/channel_gl.js`: submit `/rq/api/fetch_dem_and_build_channels`, require `Success === true` and `job_id` to start polling; otherwise push stacktrace from `Error/StackTrace`.
- `wepppy/weppcloud/controllers_js/subcatchment_delineation.js`, `wepppy/weppcloud/controllers_js/subcatchments_gl.js`: submit `/rq/api/build_subcatchments_and_abstract_watershed`, require `Success === true`; set `poll_completion_event` and `job_id`.
- `wepppy/weppcloud/controllers_js/landuse.js`, `wepppy/weppcloud/controllers_js/treatments.js`, `wepppy/weppcloud/controllers_js/soil.js`, `wepppy/weppcloud/controllers_js/climate.js`: submit respective build endpoints and gate on `Success === true` to set `job_id` and status; push stacktrace on `Success === false` or error payloads.
- `wepppy/weppcloud/controllers_js/wepp.js`: submits `/rq/api/run_wepp` and `/rq/api/run_wepp_watershed`, expects `Success === true` and `job_id`, uses stacktrace payload on failures.
- `wepppy/weppcloud/controllers_js/omni.js`: submits `/rq/api/run_omni` and `/rq/api/run_omni_contrasts`, expects `Success === true` and `job_id`.
- `wepppy/weppcloud/controllers_js/ash.js`, `wepppy/weppcloud/controllers_js/debris_flow.js`, `wepppy/weppcloud/controllers_js/rhem.js`: enqueue `/rq/api/run_ash`, `/rq/api/run_debris_flow`, `/rq/api/run_rhem_rq`; accept `Success === true` (some allow `success === true`) and use `job_id`.
- `wepppy/weppcloud/controllers_js/rap_ts.js`, `wepppy/weppcloud/controllers_js/openet_ts.js`: enqueue `/rq/api/acquire_rap_ts` and `/rq/api/acquire_openet_ts`, normalize `Success`/`success` and treat missing `Success` as failure.
- `wepppy/weppcloud/controllers_js/dss_export.js`: enqueues `/rq/api/post_dss_export_rq`, checks `Success === true` or `success === true`, and uses `Error/StackTrace` when present.
- `wepppy/weppcloud/controllers_js/outlet_gl.js`: submits `/rq/api/set_outlet`, requires `Success === true` and `job_id`.
- `wepppy/weppcloud/controllers_js/batch_runner.js`: posts to `/batch/_/<name>/rq/api/run-batch` and expects lowercase `success`; uses `/rq-engine/api/jobinfo` with fallback to `/rq/api/jobinfo` and reads `jobs`/`job_ids` without success flags.
- `wepppy/weppcloud/controllers_js/control_base.js`: polls `/rq-engine/api/jobstatus` with `/rq/api/jobstatus` fallback and relies on `status` field; fetches jobinfo for stacktrace (uses `exc_info` or `description`).
- `wepppy/weppcloud/controllers_js/status_stream.js`: fetches `/rq-engine/api/jobinfo` with `/rq/api/jobinfo` fallback and extracts `exc_info`/`description` for stacktrace display.
- `wepppy/weppcloud/controllers_js/run_sync_dashboard.js`: posts `/rq/api/run-sync` and uses `sync_job_id`/`job_id` (no `Success` check); polls `/rq/api/run-sync/status` for `jobs`/`migrations` arrays.
- `wepppy/weppcloud/static/js/archive_console.js`: uses `/rq/api/archive`, `/rq/api/restore-archive`, `/rq/api/delete-archive`; treats `Success` as the authoritative flag and uses `Error` on failure.
- Static smoke tests in `wepppy/weppcloud/static-src/tests/smoke/` stub rq/api responses with `{Success: true, job_id}` and treat `Success` or `success` as the success signal.

### Backend callsites
- `wepppy/profile_recorder/playback.py`: extracts `job_id`/`jobId` from POST responses, polls `/rq-engine/api/jobstatus` with `/rq/api/jobstatus` fallback (expects `status`), and fetches `/rq-engine/api/jobinfo` with fallback to read job trees and `exc_info`.

## 4. Redundancy Analysis
- Many rq/api endpoints return HTTP 200 with `Success: False` (error_factory) for validation errors, so `Success` currently carries error semantics that status codes do not.
- `exception_factory` and rq-engine `error_response` always include `Success: False`, even though HTTP 500 already encodes failure; the flag is redundant for clients that use HTTP status handling.
- Job polling endpoints return `status` without a success flag; clients already use `status` to decide completion/error, making `Success` unnecessary there.
- Controllers generally interpret `Success` as "job submission accepted" rather than job outcome; job lifecycle is tracked separately via jobstatus/jobinfo.
- Inconsistent casing (`Success` vs `success`) forces clients to normalize or check both, increasing migration and refactor complexity.
- Some endpoints return `Success: True` without `job_id` (batch-input updates), which conflates "inputs saved" with "job queued" semantics.

## 5. Recommendations (Draft)
- Standardize on status-code-first semantics: use 2xx only for successful submissions, 4xx for validation/input errors, and 5xx for server errors; stop returning error payloads with HTTP 200.
- Adopt a single, lower-case error shape for failures, for example `{error: {message, code?, details?}}`, with optional `errors: []` for validation lists (to replace `StackTrace` in non-debug contexts).
- For job submission endpoints, return `202 Accepted` with `{job_id, status_url?}` and optional `warnings` or `message` fields; avoid `Success` flags for accepted submissions.
- For batch-input updates that do not enqueue jobs, return `200` with `{message}` or `{result: {updated: true}}` to distinguish from job submissions.
- Keep jobstatus/jobinfo schemas unchanged but return HTTP 404 for unknown job ids instead of `status: not_found` on 200; update clients to treat 404 as not found.
- Unify casing across all JSON keys (`job_id`, `error`, `errors`), and update frontend helpers (`WCHttp`, `control_base`) to normalize once at the transport layer.
- Migration notes: update controllers and `archive_console.js` to rely on HTTP status + `job_id`, adjust smoke tests for new error shapes, and audit routes that currently set `Success` or `success` to avoid silent regressions.
