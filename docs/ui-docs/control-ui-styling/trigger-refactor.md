# Status-Based Completion Trigger Inventory
Scope: status-based completion triggers tied to the fork console, archive dashboard, and run controls surfaced by `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`.

## Shared Trigger Mechanics
- StatusStream parsing (`wepppy/weppcloud/controllers_js/status_stream.js`)
  - Detects `TRIGGER` in status log lines.
  - Token format: last token = event name, second-to-last token = controller/channel name.
  - Ignores triggers when the controller token does not match the stream channel.
  - Emits `status:trigger` on the panel element and calls the `onTrigger` callback.
- controlBase StatusStream hook (`wepppy/weppcloud/controllers_js/control_base.js`)
  - `attach_status_stream()` always calls `self.triggerEvent(detail.event, detail)` before invoking `config.onTrigger`.
  - Resets spinner for event names containing `COMPLETE`, `FINISH`, `SUCCESS`, or `END_BROADCAST`.
  - Passing a custom `onTrigger` that re-calls `triggerEvent` can double-fire completion.
- controlBase job-status polling (`wepppy/weppcloud/controllers_js/control_base.js`)
  - `set_rq_job_id()` polls `/weppcloud/rq/api/jobstatus/<jobid>` and tracks terminal statuses.
  - On `finished`, `maybeDispatchCompletion()` fires `poll_completion_event` + `job:completed` once (`_job_completion_dispatched`).
  - Only controllers with `poll_completion_event` set can complete via polling.

## Correct Completion Pattern (StatusStream + Poll)
### Single-job RQ controllers
- Attach StatusStream once (no custom `onTrigger` that re-calls `triggerEvent`).
- On job submission success:
  - Set `self.poll_completion_event` to the completion event for that job.
  - Reset `self._completion_seen = false`.
  - Call `self.set_rq_job_id(self, jobId)` to enable polling fallback.
  - Call `self.connect_status_stream(self)` for live status logs.
- In `triggerEvent` override:
  - Guard with `_completion_seen` so completion work is idempotent.
  - Perform completion side effects once (report load, map updates, etc.).
  - Disconnect StatusStream (and optionally stop polling) when done.

Example (single-job):
```javascript
controller.poll_completion_event = "WEPP_RUN_TASK_COMPLETED";
controller._completion_seen = false;
controller.set_rq_job_id(controller, jobId);
controller.connect_status_stream(controller);

const baseTriggerEvent = controller.triggerEvent.bind(controller);
controller.triggerEvent = function (eventName, payload) {
  if (String(eventName).toUpperCase() === "WEPP_RUN_TASK_COMPLETED") {
    if (controller._completion_seen) {
      return baseTriggerEvent(eventName, payload);
    }
    controller._completion_seen = true;
    controller.disconnect_status_stream(controller);
    controller.report();
  }
  return baseTriggerEvent(eventName, payload);
};
```

### Multi-stage RQ controllers
- Keep StatusStream triggers for intermediate steps (e.g., build vs abstraction).
- Use a per-event guard (`completionSeen[eventName]`) instead of a single boolean.
- Set `poll_completion_event` to the final event only, so polling maps to the terminal stage.

### Non-RQ / synchronous controllers
- Do not add polling; continue using direct HTTP completion handlers.
- Still avoid duplicate StatusStream triggers if a channel is attached for logging.

### Avoid double-triggering
- Do not call `triggerEvent` inside `attach_status_stream({ onTrigger })` unless you skip the controlBase default.
- Use a `reportLoaded` or `completionSeen` guard around report loading and heavy UI updates.

## Fork Console
- `wepppy/weppcloud/static/js/fork_console.js`
  - Channel: `fork`
  - Trigger events:
    - `FORK_COMPLETE` -> `handleForkComplete()` (toggle buttons, success message/link, append status).
    - `FORK_FAILED` -> `handleForkFailed()` (toggle buttons, error message, append status).

## Archive Dashboard
- `wepppy/weppcloud/static/js/archive_console.js`
  - Channel: `archive`
  - Trigger events:
    - `ARCHIVE_COMPLETE` -> `archiveFinished()` (enable buttons, clear comment, refresh list).
    - `RESTORE_COMPLETE` -> `restoreFinished()` (enable buttons, refresh list, show load link).

## Run Controls (runs0_pure.htm)
### Channel Delineation
- `wepppy/weppcloud/controllers_js/channel_delineation.js`
  - Channel: `channel_delineation`
  - Completion trigger: `BUILD_CHANNELS_TASK_COMPLETED` (StatusStream trigger or poll completion).
  - Failure triggers: `BUILD_CHANNELS_TASK_FAILED`, `BUILD_CHANNELS_TASK_ERROR`.
  - Actions: disconnect stream, show map layers, load report, emit `channel:build:completed`, fire `job:completed`.
  - Dedupe: `_completion_seen` guard.
  - Polling: `poll_completion_event = "BUILD_CHANNELS_TASK_COMPLETED"`.

### Outlet
- `wepppy/weppcloud/controllers_js/outlet.js`
  - Channel: `outlet`
  - Completion trigger: `SET_OUTLET_TASK_COMPLETED` (StatusStream trigger or poll completion).
  - Actions: disconnect stream, remove popup, show outlet, emit `outlet:set:success`, fire `job:completed`.
  - Dedupe: `_completion_seen` guard.
  - Polling: `poll_completion_event = "SET_OUTLET_TASK_COMPLETED"`.

### Subcatchment Delineation
- `wepppy/weppcloud/controllers_js/subcatchment_delineation.js`
  - Channel: `subcatchment_delineation`
  - Completion triggers:
    - `BUILD_SUBCATCHMENTS_TASK_COMPLETED` -> show subcatchments, show channel delineation, emit `subcatchment:build:completed`.
    - `WATERSHED_ABSTRACTION_TASK_COMPLETED` -> report, disconnect stream, enable `slp_asp` color map, update WEPP phosphorus.
  - Build invalidates `hasSubcatchments` by removing the existing `subwta` before rebuild (`wepppy/nodb/core/watershed.py`).

### Rangeland Cover
- `wepppy/weppcloud/controllers_js/rangeland_cover.js`
  - Channel: `rangeland_cover`
  - Completion trigger: `RANGELAND_COVER_BUILD_TASK_COMPLETED`.
  - Actions: disconnect stream, enable `rangeland_cover` color map, load report, emit `rangeland:run:completed`.
  - Build invalidates `hasCovers` by clearing stored covers at build start (`wepppy/nodb/mods/rangeland_cover/rangeland_cover.py`).

### Landuse
- `wepppy/weppcloud/controllers_js/landuse.js`
  - Channel: `landuse`
  - Completion trigger: `LANDUSE_BUILD_TASK_COMPLETED`.
  - Actions: disconnect stream, load report, enable `dom_lc` color map, emit `landuse:build:completed`.

### Soils
- `wepppy/weppcloud/controllers_js/soil.js`
  - Channel: `soils`
  - Completion trigger: `SOILS_BUILD_TASK_COMPLETED`.
  - Actions: disconnect stream, load report, enable `dom_soil` color map.

### Climate
- `wepppy/weppcloud/controllers_js/climate.js`
  - Channel: `climate`
  - Completion triggers:
    - `CLIMATE_SETSTATIONMODE_TASK_COMPLETED` -> refresh station list and monthlies (unless `skipRefresh`/`skipMonthlies` in payload).
    - `CLIMATE_SETSTATION_TASK_COMPLETED` -> refresh monthlies.
    - `CLIMATE_BUILD_TASK_COMPLETED` or `CLIMATE_BUILD_COMPLETE` -> load climate report.

### RAP Time Series
- `wepppy/weppcloud/controllers_js/rap_ts.js`
  - Channel: `rap_ts`
  - Completion trigger: `RAP_TS_TASK_COMPLETED`.
  - Actions: set completion status message, disconnect stream, emit `rap:timeseries:run:completed`, fire `job:completed`.

### Treatments
- `wepppy/weppcloud/controllers_js/treatments.js`
  - Channel: `treatments`
  - Completion trigger: any event name containing `COMPLETED`, `FINISHED`, or `SUCCESS`.
  - Actions: emit `treatments:job:completed`, disconnect stream.
  - Other trigger parsing: `STARTED`/`QUEUED` -> `treatments:job:started`, `FAILED`/`ERROR` -> `treatments:job:failed`.

### WEPP
- `wepppy/weppcloud/controllers_js/wepp.js`
  - Channel: `wepp`
  - Completion trigger: `WEPP_RUN_TASK_COMPLETED`.
  - Actions: disconnect stream, load WEPP report, notify Observed controller, emit `wepp:run:completed`.

### Ash
- `wepppy/weppcloud/controllers_js/ash.js`
  - Channel: `ash`
  - Completion trigger: `ASH_RUN_TASK_COMPLETED`.
  - Actions: disconnect stream, load report, emit `ash:run:completed`.

### RHEM
- `wepppy/weppcloud/controllers_js/rhem.js`
  - Channel: `rhem`
  - Completion trigger: `RHEM_RUN_TASK_COMPLETED`.
  - Actions: disconnect stream, load report, emit `rhem:run:completed`, fire `job:completed`.

### Omni Scenarios
- `wepppy/weppcloud/controllers_js/omni.js`
  - Channel: `omni`
  - Completion triggers:
    - `OMNI_SCENARIO_RUN_TASK_COMPLETED` -> refresh scenario list, disconnect stream, emit `omni:run:completed`.
    - `END_BROADCAST` -> disconnect stream.

### Debris Flow
- `wepppy/weppcloud/controllers_js/debris_flow.js`
  - Channel: `debris_flow`
  - Completion trigger: `DEBRIS_FLOW_RUN_TASK_COMPLETED` CustomEvent on form (expected from StatusStream trigger).
  - Actions: disconnect stream, load report link.

### DSS Export
- `wepppy/weppcloud/controllers_js/dss_export.js`
  - Channel: `dss_export`
  - Completion trigger: `DSS_EXPORT_TASK_COMPLETED` CustomEvent on form (expected from StatusStream trigger).
  - Actions: disconnect stream, load download link, emit `job:completed`.

### Observed Data
- `wepppy/weppcloud/controllers_js/observed.js`
  - Channel: `observed`
  - StatusStream is attached for logs, but completion is driven by the HTTP response from `tasks/run_model_fit/` (not a StatusStream trigger).

### Disturbed / SBS (BAER)
- `wepppy/weppcloud/controllers_js/disturbed.js`
- `wepppy/weppcloud/controllers_js/baer.js`
  - Channel: `sbs_upload`
  - StatusStream is attached for logs; completion events (`SBS_UPLOAD_TASK_COMPLETE`, `SBS_REMOVE_TASK_COMPLETE`, `MODIFY_BURN_CLASS_TASK_COMPLETE`) are fired directly on HTTP success, not from StatusStream triggers.

### PATH Cost-Effective
- `wepppy/weppcloud/controllers_js/path_ce.js`
  - Completion is driven by polling `api/path_ce/status` (status transitions to `completed` or `failed`).
  - Triggers `job:completed`/`job:error` and emits `pathce:run:completed`/`pathce:run:error`.
  - No StatusStream channel.

## Known Duplicate-Trigger Paths (StatusStream)
- `wepppy/weppcloud/controllers_js/team.js`
  - Each passes `onTrigger` that re-calls `triggerEvent`, even though `controlBase.attach_status_stream()` already does this.
  - StatusStream triggers can fire completion handlers twice unless downstream code guards against duplicates.

## Run Controls Update Checklist (do these before fork/archive)
- [x] Subcatchment delineation (`wepppy/weppcloud/controllers_js/subcatchment_delineation.js`): per-event completion guards; `poll_completion_event = WATERSHED_ABSTRACTION_TASK_COMPLETED`; keep StatusStream for intermediate `BUILD_SUBCATCHMENTS_TASK_COMPLETED`; invalidate `subwta` on rebuild.
- [x] Rangeland cover (`wepppy/weppcloud/controllers_js/rangeland_cover.js`): `_completion_seen` guard; `poll_completion_event = "RANGELAND_COVER_BUILD_TASK_COMPLETED"`; report idempotent; invalidate covers on rebuild.
- [x] Landuse (`wepppy/weppcloud/controllers_js/landuse.js`): `_completion_seen` guard; `poll_completion_event = "LANDUSE_BUILD_TASK_COMPLETED"`; report idempotent.
- [x] Soils (`wepppy/weppcloud/controllers_js/soil.js`): `_completion_seen` guard; `poll_completion_event = "SOILS_BUILD_TASK_COMPLETED"`; report idempotent.
- [x] Climate (`wepppy/weppcloud/controllers_js/climate.js`): report idempotent; `poll_completion_event = "CLIMATE_BUILD_TASK_COMPLETED"` for build jobs only; keep StatusStream triggers for station/spatial tasks.
- [x] RAP time series (`wepppy/weppcloud/controllers_js/rap_ts.js`): remove duplicate `onTrigger` re-calling `triggerEvent`; add `_completion_seen` guard; set `poll_completion_event = "RAP_TS_TASK_COMPLETED"`.
- [x] Treatments (`wepppy/weppcloud/controllers_js/treatments.js`): add `_completion_seen` guard (or per-event); set `poll_completion_event` to the final completion event used for build jobs.
- [x] WEPP (`wepppy/weppcloud/controllers_js/wepp.js`): remove duplicate `onTrigger` re-calling `triggerEvent`; add `_completion_seen` guard; set `poll_completion_event = "WEPP_RUN_TASK_COMPLETED"`.
- [x] Ash (`wepppy/weppcloud/controllers_js/ash.js`): add `_completion_seen` guard; set `poll_completion_event = "ASH_RUN_TASK_COMPLETED"`.
- [x] RHEM (`wepppy/weppcloud/controllers_js/rhem.js`): remove duplicate `onTrigger` re-calling `triggerEvent`; add `_completion_seen` guard; set `poll_completion_event = "RHEM_RUN_TASK_COMPLETED"`.
- [x] Omni (`wepppy/weppcloud/controllers_js/omni.js`): add `_completion_seen` guard; set `poll_completion_event = "OMNI_SCENARIO_RUN_TASK_COMPLETED"`.
- [x] Debris flow (`wepppy/weppcloud/controllers_js/debris_flow.js`): add `_completion_seen` guard; set `poll_completion_event = "DEBRIS_FLOW_RUN_TASK_COMPLETED"`; ensure CustomEvent handler stays idempotent.
- [x] DSS export (`wepppy/weppcloud/controllers_js/dss_export.js`): add `_completion_seen` guard; set `poll_completion_event = "DSS_EXPORT_TASK_COMPLETED"`; ensure report loads once.

### Already compliant / no changes expected
- Channel delineation (`wepppy/weppcloud/controllers_js/channel_delineation.js`), Outlet (`wepppy/weppcloud/controllers_js/outlet.js`) already follow the hybrid pattern with `_completion_seen` + polling.
- Observed (`wepppy/weppcloud/controllers_js/observed.js`), Disturbed/BAER (`wepppy/weppcloud/controllers_js/disturbed.js`, `wepppy/weppcloud/controllers_js/baer.js`), PATH CE (`wepppy/weppcloud/controllers_js/path_ce.js`) do not need polling updates.

## Deferred (after run controls)
- [ ] Fork console (`wepppy/weppcloud/static/js/fork_console.js`)
- [ ] Archive dashboard (`wepppy/weppcloud/static/js/archive_console.js`)
