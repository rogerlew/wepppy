# Profile Recorder Playbook

> Onboarding notes for Codex agents extending the profile recorder / playback stack.

## Overview
- The recorder sits on the WEPPcloud frontend (`WCHttp.request` interceptor) and streams backend-facing events into `_logs/profile.events.jsonl` plus the data repo drafts under `/workdir/wepppy-test-engine-data/profiles/_drafts/<run>/<capture>/`.
- The assembler consumes those events on the fly, snapshots seed assets (configs, uploads, derived files) and writes promoted profiles under `/profiles/<slug>/`.
- Playback provisions a fresh scratch workspace (`PROFILE_PLAYBACK_RUN_ROOT`), hydrates seeds/configs, then replays recorded requests against WEPPcloud via the FastAPI service in `services/profile_playback/app.py`.

## Key Files
- `profile_recorder/profile_recorder.py` — Flask extension that appends audit events and forwards them to the assembler.
- `profile_recorder/assembler.py` — Streaming event handler; responsible for seed snapshots and profile promotion.
- `profile_recorder/playback.py` — Replays recorded events, handles RQ job polling, and rebuilds multipart payloads.
- `wepppy/weppcloud/controllers_js/http.js` + `recorder_interceptor.js` — Frontend plumbing that wraps all controller HTTP traffic and emits recorder events.
- `/workdir/wepppy-test-engine-data` — Shared data repo (bind mounted in Docker) holding drafts, promoted profiles, seeds, and playback workspaces.

## Requirements for Upload Support
When adding support for a new multipart/form-data workflow:
- **Recorder capture:** Update `_capture_file_upload()` in `assembler.py` to copy the canonical source files from the run directory into `seed/uploads/<namespace>/`. Include any sidecar metadata (e.g., `.meta`, `.json`) needed for replay. Keep seeds <50 MB where possible; flag anything larger for LFS review.
- **Playback rebuild:** Extend `_build_form_request()` in `playback.py` with helper(s) that locate the seeded file. Playback starts from a clean workspace, so seeds must contain everything needed to rebuild the upload payload. Ensure the mime type matches what the original controller submitted.
- **Config state:** If the upload toggles NoDb state (checkboxes, selection lists), read those values from the controller instance in playback so the reconstructed form mirrors the original request.
- **Tests / verification:** Capture a profile that exercises the new upload, promote it, and run `wctl run-test-profile <slug>` to confirm the playback pipeline succeeds end-to-end.
- **Documentation:** Record any special handling (e.g., temporary directories, additional derived files) here or in the spec (`PROFILE_TEST_ENGINE_SPEC.md`) so future agents know the expectations.

## Operational Notes
- Playback always initialises a clean workspace; never assume prior run assets are restored. Keep the capture seeds authoritative for every upload/config dependency.
- Replay rewrites `/runs/<original>/<config>/...` → `/runs/{playback_run_id}/<config>/...`; the FastAPI service generates playback run IDs as `profile;;tmp;;<sandbox_uuid>` so production runs remain untouched while tracking the source identifier for reporting.
- Recorded `/rq/api/jobstatus/<id>` polls and `elevationquery` requests are skipped during replay; the runner waits on the fresh job IDs emitted by each POST response instead.
- Authentication defaults to automated login using `ADMIN_EMAIL` / `ADMIN_PASSWORD` (see `docker/.env`). If a profile needs user-scoped permissions, record with the appropriate account and capture the session cookie for playback (`--cookie-file`).
- The recorder runs globally even when not actively capturing profiles; audit logs under each run’s `_logs/` folder always append new events. Promotion copies only the slice under `_drafts/<run>/<capture>/`.

## Troubleshooting
- **Event missing in profile capture:** Confirm the frontend call uses `WCHttp.request` (not raw `fetch`). If missing, rebuild the controller bundle (`python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`) and hard refresh to ensure the interceptor is active.
- **Playback missing upload file:** Check `capture/seed/uploads/` in the promoted profile. If empty, seed capture was not implemented or the recorder ran before the upload completed.
- **Job status stuck on 404:** Expected once the worker drops the job. Playback treats 404 as completion; ensure the follow-up GET populates expected data before the next step.
- **New upload type:** Mirror the existing patterns for landuse (`_populate_landuse_form`) and SBS (`_populate_sbs_form`), then add exhaustive logging in verbose mode to trace payload assembly during development.

## Multipart Upload Inventory
| Endpoint | Form field(s) | Stored under | Owning controller / notes |
| --- | --- | --- | --- |
| `/runs/<runid>/<config>/tasks/upload_sbs/` | `input_upload_sbs` | `<run>/baer/` or `<run>/disturbed/` | BAER or Disturbed SBS raster. **Recorder/playback support implemented.** |
| `/runs/<runid>/<config>/tasks/upload_cover_transform` | `input_upload_cover_transform` | `<run>/revegetation/` | Revegetation user-defined cover transform CSV. **Capture/playback supported.** |
| `/runs/<runid>/<config>/tasks/upload_cli/` | `input_upload_cli` | `Climate.cli_dir` (typically `<run>/climate/`) | CLIGEN `.cli` uploads. **Capture/playback supported.** |
| `/runs/<runid>/<config>/rq/api/build_landuse` | `input_upload_landuse` (UserDefined mode) | `Landuse.lc_dir` (copied to `_filename`, stacked into `landuse.lc_fn`) | Landuse user-defined raster. **Supported** through existing landuse form logic. |
| `/runs/<runid>/<config>/rq/api/build_treatments` | `input_upload_landuse` | `Landuse.lc_dir` | Treatments user-defined map; shares plumbing with landuse. **Handled via landuse replay helpers.** |
| `/runs/<runid>/<config>/rq/api/run_ash` | `input_upload_ash_load` (required), `input_upload_ash_type_map` (optional) | `<run>/ash/` | Ash load/type rasters. **Capture/playback supported (with optional type map).** |
| `/runs/<runid>/<config>/rq/api/run_omni` (SBS scenario) | `scenarios[i][sbs_file]` (indexed per scenario) | `<run>/omni/_limbo/<idx>/` | Omni scenario SBS uploads. **Capture/playback supported (per-index seed + JSON replay).** |
| `/huc-fire/tasks/upload_sbs/` | `input_upload_sbs` | `<new run>/disturbed/` | HUC fire helper (creates run on upload). Optional for profile engine; document before adding support. |
| `/batch/_/<batch_name>/upload-geojson` | `geojson_file` / `file` | `batch/<batch_name>/resources/` | Batch runner GeoJSON ingest (outside run context). Capture optional; treat as future enhancement. |

Happy recording!
