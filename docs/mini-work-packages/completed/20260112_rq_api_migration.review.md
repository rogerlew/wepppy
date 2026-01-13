# RQ API Migration Review (2026-01-12)

## Blocking issues (must-fix before removing legacy /rq/api in prod)
- None.

## Non-blocking observations
- Run-scoped session-token URLs are constructed manually rather than via `url_for_run` in a few places (`wepppy/weppcloud/controllers_js/http.js:161`, `wepppy/weppcloud/routes/rq/job_dashboard/templates/dashboard_pure.htm:495`). They still target `/rq-engine/api`, but diverge from the helper-only guidance.
- Upload field names align with rq-engine handlers: `input_upload_cli`, `input_upload_sbs`, `input_upload_cover_transform`, `geojson_file`, `sbs_map` in templates/controllers match the FastAPI route expectations (spot-checked against `wepppy/microservices/rq_engine/upload_climate_routes.py:26`, `wepppy/microservices/rq_engine/upload_disturbed_routes.py:35`, `wepppy/microservices/rq_engine/upload_batch_runner_routes.py:107`).
- Jobstatus/jobinfo remain open and canceljob is JWT-protected as expected (`wepppy/microservices/rq_engine/job_routes.py:32`, `wepppy/microservices/rq_engine/job_routes.py:72`).

## Runtime /rq/api or /upload references found
- None in runtime callers (controllers/templates/routes/microservices/scripts). Only docs and profile_recorder references remain.

## Recommendation
Ready. Legacy jobstatus fallback removed, and rq-engine error responses now include `error.details` as required.

## Missing tests / verification gaps
- No automated checks assert `error.details` on 4xx/5xx responses across rq-engine routes; add a contract test or shared helper test.
