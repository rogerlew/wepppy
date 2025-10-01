# WEPPcloud Batch Runner

A developer and administrator tool to orchestrate large numbers of watersheds that share a configuration. The feature builds on the existing NoDb architecture and rq infrastructure while keeping privileged operations behind a guarded workflow.

## Overview
- Provide a sandbox where a privileged user can assemble a canonical `_base` project and fan it out to many watersheds.
- Persist batch metadata, validation results, and task progress so runs are resumable.
- Keep batch execution isolated from normal user traffic while reusing the same WEPPcloud components and rq workers.

## Goals
- Streamline creation of hundreds of identical projects without touching individual controls.
- Guarantee that every derived run inherits the same Omni and project configuration.
- Offer idempotent batch operations with clear resubmission and recovery semantics.
- Surface enough telemetry to monitor progress and troubleshoot failures.

## Non-Goals
- General availability for all users; this remains an elevated-permission capability.
- Abstracting away WEPP task internals; the batch runner coordinates existing controls.
- Replacing `run_0` flows; the `_base` project continues to use the standard controls UI.

## Personas
- **Batch Admin:** Limited number of power users with credentials that unlock `/batch/create/` and `/batch/_/<name>/` routes.
- **Ops Engineer:** Reviews logs, manages rq workers, and can SSH into the batch directories when escalated support is required.

## Workflow
1. Batch admin opens `Create Batch Runs`, selects a stored config, and provides a `batch_name`.
2. Backend scaffolds `/wc1/batch/<batch_name>/` with `_base/`, `resources/`, and `logs/`, then persists a `batch_runner.nodb` state file.
3. User is redirected to `/batch/_/<batch_name>/`, which boots the `_base` project controls alongside the Batch Runner control.
4. Admin prepares the `_base` project (Omni scenarios, climate options, etc.) through the standard controls; run buttons remain hidden except on SBS Upload where file operations must stay available.
5. Admin uploads a `.geojson` into `resources/`; backend stores a canonical relative path in `BatchRunner.nodb` and validates geometry plus feature attributes.
6. Admin defines a template for `runid` generation and runs validation; system emits proposed run ids, uniqueness report, and rejected features.
7. Admin selects the tasks to run, toggles `Force Rebuild` when required, and triggers `Run Batch`.
8. `BatchRunner(NoDbBase)` snapshots the `_base` state, materializes workspace directories for each run id (including geospatial preprocessing), and enqueues rq jobs with dependencies per task.
9. Worker pool processes runs; progress feeds back into `BatchRunner` state so the UI can stream status updates, show partial success, and allow re-drives.

## Current Status
- Phase 1 scaffolding is implemented and gated by the Admin feature flag. `/batch/create/` provisions the batch workspace, instantiates the `_base/` project via the selected configuration, and persists creation metadata directly on the `BatchRunner` NoDb singleton.
- `/batch/_/<name>/` loads the NoDb instance through `BatchRunner.getInstance`, exposing a state snapshot that downstream controls consume.
- Base project creation reuses the existing `NoDbBase` pipeline; `nodb/configs/batch/default_batch.cfg` is a placeholder that keeps config semantics aligned with the standard run flow until batch-specific knobs arrive, which ideally is never.
- Directory layout now includes `_base/` and `resources/`, giving Phase 2 a concrete landing zone for GeoJSON intake and state enrichment.
- Phase 2 resource intake is now live: GeoJSON uploads land in `resources/`, metadata (feature count, bbox, checksum, EPSG) persists under `resources['watershed_geojson']`, `state_version` advances to `2`, and template validation snapshots (summary, duplicates, sample rows) live on `BatchRunner.template_validation` with stale detection when resources change.

## State Design (codex)
- **NoDb attributes.** `BatchRunner` persists state as first-class attributes (`batch_name`, `resources`, `template_validation`, etc.), so callers leverage the standard NoDb property paradigm instead of an intermediate manifest object.
- **Core fields.**
  - `state_version`: schema migrations for persisted attributes.
  - `batch_name` / `base_config` / `batch_config`: identifiers for the workspace and selected configuration (immutable after creation).
  - `config`: mirrors `base_config` to keep bootstrap payloads consistent while controls migrate.
  - `created_at` / `created_by`: ISO8601 timestamp and user string stamped during setup.
  - `runid_template`: formatting string for Phase 2 run-id expansion.
  - `selected_tasks`, `force_rebuild`, `runs`, `history`, `resources`, and `control_hashes`: shared bookkeeping for orchestration.
  - `metadata`: scratchpad for prototype data; `update_state` continues to route unknown keys here so experiments stay isolated.
- **Lifecycle.** `BatchRunner.__init__` seeds default attributes and persists via standard NoDb locking/dump semantics. `update_state(**updates)` applies structured changes, while helpers such as `register_resource`, `record_template_validation`, and `add_history` encapsulate common mutations.
- **Access patterns.** Routes call `BatchRunner.getInstance(batch_wd)` and serialize via `state_dict()`. Future phases should add targeted helpers (`register_resource`, `record_validation`, `enqueue_runs`) rather than ad-hoc mutations so schema changes remain centralised.

## Filesystem
- `/wc1/batch/<batch_name>/batch_runner.nodb` — persisted BatchRunner NoDb state with metadata, selected tasks, and run ledger.
- `/wc1/batch/<batch_name>/_base/` — canonical project built with normal controls; holds NoDb singletons (`ron.nodb`, `climate.nodb`, etc.).
- `/wc1/batch/<batch_name>/<runid>/` — per-watershed directory cloned from `_base` before each run.
- `/wc1/batch/<batch_name>/resources/` — staging area for geojson plus ancillary uploads referenced by tasks.
- `/wc1/batch/<batch_name>/runs/` — where the batch runs live.
- `/wc1/batch/<batch_name>/logs/` (optional) — consolidated stdout/stderr symlinks or harvested rq logs for quick troubleshooting.

## State
- `BatchRunner(NoDbBase)` serializes:
  - `batch_name`, base `config`, `created_at`, `created_by`.
  - `watershed_geojson` metadata (`relative_path`, `feature_count`, bounding boxes, checksum).
  - `runid_template`, validation summary, rejected features.
  - `selected_tasks`, `force_rebuild`, and per-task dependency graph.
  - `runs`: map of `runid -> {tasks: {name: status, job_id}, last_update, attempts, errors}`.
  - `history`: audit trail of submissions, user, trigger reason.
- Run state doubles as the guard for idempotency; a task only re-enqueues when forced or when prior status != success.

## UI
- **Create Batch Runs Page:** Config selector plus `batch_name` field (validated for length, casing, filesystem safety) and submit button; also lists existing batches for navigation.
- **Batch Runner Page:** Renders standard `_base` controls (SBS Upload, Delineations, Landuse, Soils, Climate, WEPP, Omni) with build/run buttons hidden except where file uploads are required; forms stay usable and autosave.
- **Batch Runner Control Panel:**
  - File uploader with drag-and-drop, progress bar, and geojson schema hints.
  - Template editor with helper functions (property auto-complete, sample evaluation against first feature).
  - Validation report with run id list, duplicates, missing attributes, and sanitized names.
  - Task checklist, `Force Rebuild` toggle, estimated job count, and `Run Batch` button.
  - Status dashboard showing aggregate counts (pending/running/succeeded/failed) plus a virtualized table of per-run task progress using the existing websocket update pattern from Omni and the rq `jobstatus`/`jobinfo` APIs for server polling.
  - Action buttons for retrying failed runs, downloading logs, and filtering by run id slice (all runs, single run, index range).

## Hydrologic Preprocessing
- GeoJSON drives map extent, delineation, and outlet placement for each run to mirror the manual workflow.
- For every feature:
  - Derive bounding boxes and buffering rules to request DEM tiles and ancillary datasets.
  - Invoke a new `Watershed.determine_outlet()` helper that identifies and sets the outlet automatically.
- Extend the internal WhiteBoxTools fork with a utility that ingests watershed outlines and returns outlet coordinates; persist outputs for audit (implemented in the fork; wrapper shown below).
- Store preprocessing artifacts alongside each run so later steps can reuse them or inspect mismatches.

WhiteBoxTools wrapper
```
    def find_outlet(self, d8_pntr, streams, watershed, output, esri_pntr=False, callback=None):
        """Identifies an outlet stream cell for a watershed mask and writes a pour point GeoJSON.

        Keyword arguments:

        d8_pntr -- Input raster D8 pointer file. 
        streams -- Input raster streams file (1=stream, 0=non-stream). 
        watershed -- Input watershed mask raster file (1=inside, 0=outside). 
        output -- Output GeoJSON pour point file. 
        esri_pntr -- D8 pointer uses the ESRI style scheme. 
        callback -- Custom function for handling tool text outputs.
        """
```


## Backend

### BatchRunner(NoDbBase)
- Owns reading/writing `batch_runner.nodb` and exposes mutation helpers (`register_geojson`, `update_tasks`, `enqueue_runs`, `record_outlet`).
- Provides utilities for cloning `_base` projects, sanitizing run ids, clearing locks/caches, and orchestrating hydrologic preprocessing before job submission.
- Calculates dependency chains per run (e.g., delineation -> landuse -> soils -> climate -> wepp -> watar -> omni) and records job ids for traceability.

### BatchRunner(ControlBase)
- Supplies serialized state to the JS singleton, mirroring other controls.
- Accepts AJAX posts for geojson upload, template validation, task selection, and batch execution; hydrologic preprocessing occurs within each run job rather than via a standalone endpoint.
- Emits websocket events (via existing `ws_client.js`) to push incremental status updates as jobs transition.

### `batch_runner_bp`
- `GET /batch/create/` — guarded view displaying the create form and listing existing batches.
- `POST /batch/create/` — validates input, scaffolds directories, initializes `_base`, redirects to batch page.
- `GET /batch/_/<name>/` — renders Batch Runner page with `_base` forms and initial state payload.
- `POST /batch/_/<name>/upload-geojson` — handles file upload, checksum storage, and structural validation.
- `POST /batch/_/<name>/validate-template` — evaluates template across features, returns run id list and errors.
- `POST /batch/_/<name>/run` — snapshots `_base`, updates BatchRunner state, enqueues jobs, responds with parent job id.

### RQ Worker Pool
- Deploy dedicated queue `batch` with 2–3 workers initially, configurable via environment variable.
- Parent rq job (`batch:<name>:<timestamp>`) groups all per-task jobs for traceability; children reference the parent for cancellations.
- Each worker job logs to a shared location; errors bubble up to BatchRunner state with truncated stack traces for UI display.

## Orchestration
- Snapshot `_base` to a temp directory; copy into run directories to avoid partial states if cloning fails mid-copy.
- Precompute per-run state before enqueueing any job to catch validation issues early; include outlet coordinates and DEM provenance so downstream tasks remain deterministic.
- For each run id:
  1. Create working directory and inject sanitized `_base` NoDb files (`wd`, caches, locks cleared).
  2. Derive hydrologic context: compute extent from GeoJSON, download DEM, run WhiteBox outlet tool, and persist outlet via `Watershed.determine_outlet()`.
  3. Schedule tasks per dependency graph with rq `depends_on` so sequential execution happens within a run while different run ids execute in parallel.
  4. Persist job ids back onto the run record immediately after enqueue for later introspection or cancellation.
- Periodically refresh job statuses (polling or websocket subscription) to keep UI synchronized; throttle updates to avoid hammering Redis.

## Difficult Areas
- **Credentials & Auditing:** Limit access to the `Admin` role, capture user id/IP/payload hashes, and surface the audit trail in `history`.
- **Filesystem Safety:** Sanitize batch names and run ids, reserve keywords, and perform atomic directory creation with retries to prevent collision.
- **GeoJSON Robustness:** Validate structure on upload, reject oversized inputs, and expose per-feature errors so admins can correct data without manual inspection.
- **Template Execution:** Restrict to `string.Template` or equivalent sandbox, provide dry-run output, and assert uniqueness before accepting run ids.
- **Automated Extent & Outlet Detection:** Converting polygon features into reliable extents, obtaining DEM tiles, and auto-placing outlets introduces new failure modes; must handle poor-quality inputs and inconsistent CRS.
- **State Consistency:** Concurrent UI interactions and worker updates can corrupt `batch_runner.nodb`; use file locks or redis-backed CAS with transactional writes.
- **Job Coordination:** Large batches risk overwhelming Redis; queue jobs in chunks, monitor queue depth, and back off when more than N jobs are pending.
- **Observability & Recovery:** Failed runs require actionable diagnostics; surface logs, support targeted retries, and keep retries idempotent.

## Mitigations
- Implement shared utilities for slugging names, computing checksums, locking, and CRS normalization to stay consistent with Omni.
- Ship `state_version` migrations so schema changes (e.g., new tasks) can be migrated without breaking older batches.
- Add hydrologic preprocessing safeguards: CRS detection, buffered extents, DEM size limits, and retries with coarser tiles when fine resolution fails.
- Extend the WhiteBoxTools fork with the outlet-detection helper; wrap it with structured error reporting and unit tests that compare to known outlets.
- Create integration tests that simulate end-to-end batch creation, run id generation, preprocessing, and job enqueueing using mocked rq workers and DEM fetch stubs.
- Provide feature flags or environment toggles to disable the control entirely in non-admin deployments.
- Offer run filters (all, single, index range) in the UI to throttle job submission for very large batches when needed.

## Phases
1. **Phase 0 – Foundations:** Define data structures, add authorization hooks (limit to Admin), scaffold BatchRunner(NoDbBase)/Control skeletons, and stand up a dedicated `batch` rq queue with workers.
2. **Phase 1 – Batch Scaffolding:** Implement `/batch/create/`, directory creation, `_base` bootstrap, state persistence, and SBS upload support in `_base` context.
3. **Phase 2 – Resource Intake:** Deliver geojson upload pipeline, template validation service, and UI feedback loop for run id previews.
4. **Phase 3 – Hydrologic Preprocessing:** Build extent derivation, DEM acquisition, WhiteBox outlet detection, and `Watershed.determine_outlet()` integration; persist outputs per run.
5. **Phase 4 – Job Orchestration:** Wire task checklist, run state generation, directory cloning, and rq job submission with dependency graphs plus run filters.
6. **Phase 5 – Progress UI & Recovery:** Implement status dashboard, websocket updates, retry/force rebuild logic, log surfacing, and admin notifications.
7. **Phase 6 – Hardening:** Load testing, integration tests, observability (metrics, alerts), documentation, and production-readiness polish.

### Phase 0 Implementation Plan
- **Access Control & Feature Flagging**
  - Create a `batch_runner_bp` blueprint under `batch_runner/` with a dedicated templates folder to keep the feature isolated.
  - Extend the existing admin-only decorators to cover `/batch/create/` and `/batch/_/<name>/`; add unit tests that ensure non-admin users receive `403` responses.
  - Introduce a `BATCH_RUNNER_ENABLED` configuration toggle and surface graceful fallback messaging in templates when disabled.
  - Document the access requirements in the ops/security notes so credentials can be provisioned ahead of launch.
- **Manifest Schema Baseline**
  - Define the `BatchRunner` state shape (fields listed below) including placeholders for per-control hashes and hydrologic metadata.
  - Implement load/save helpers in a shared module that create versioned state snapshots with sensible defaults; write smoke tests confirming round-trip serialization.
  - Identify reusable checksum/slug utilities (likely from Omni) and refactor them into a shared helper to avoid duplication.
- **NoDb & Control Scaffolds**
  - Create `BatchRunner(NoDbBase)` with stubbed getters/setters returning the default state and emitting TODO logs for unimplemented mutators.
  - Add `BatchRunner(ControlBase)` that exposes the NoDb state via `get_state()` and accepts no-op POST handlers for the Phase 0 endpoints.
  - Register the blueprint so it renders placeholder templates and wires the control into server-side bootstrap data.
- **Frontend Skeleton**
  - Add `controllers_js/batch_runner.js` as a singleton that renders a “coming soon” panel, consumes feature flag state, and subscribes to websocket channels without emitting events yet.
  - Update the batch runner page template (or create a new one) to mount the control and inject initial state via the existing bootstrap pattern.
- **RQ Queue Configuration**
  - Reserve a `batch` queue in `wepp_rq` with configuration sourced from environment variables; ensure the queue is ignored when the feature flag is off.
  - Create an ops note/systemd template for launching dedicated batch workers; verify workers idle safely with no jobs.
- **Testing & Tooling**
  - Add minimal pytest coverage for state helpers, auth enforcement, and feature flag toggling.
  - Seed an integration test scaffold (skipped initially) outlining the end-to-end batch lifecycle to keep CI wiring ready.
- **Exit Criteria**
  - Admin-only routes exist and return placeholder responses; non-admins are blocked.
  - Manifest files can be created/read with default content and version headers.
  - The Batch Runner control renders in the UI behind the feature flag with a clear “coming soon” message.
  - Dedicated `batch` queue configuration is merged and workers can be launched without processing jobs.

### Phase 2 Implementation Plan
- **GeoJSON intake service**
  - Add `POST /batch/_/<name>/upload-geojson` endpoint that writes uploads into `<batch>/resources/` with conflict-aware naming and size limits. Assume if user uploads a file with the same name they are intending on replacing the file. Provide feedback this has occurred.
  - Validate file extension and MIME, reject multi-feature collections without `FeatureCollection` semantics, and stream to disk to avoid loading entire payloads into memory.
  - In `BatchRunner` compute checksum, feature count, bounding boxes, EPSG code, and attribute schema; persist in `resources['watershed_geojson']` along with upload timestamp and user.
  - Guard writes with `BatchRunner.locked()` to keep updates atomic and respect NoDb locking.
- **Template validation pipeline**
  - Implement `POST /batch/_/<name>/validate-template` that accepts a template string and optional filters, loads the stored GeoJSON, and evaluates run ids for each feature.
  - Surface duplicates, missing attributes, or invalid expressions; return proposed run ids, validation errors, and summary stats.
  - Cache the latest validation payload on `template_validation` with hashes of template + resource so the UI can detect when results are stale.
- **State helpers**
  - Extend `BatchRunner` with typed methods (`register_resource`, `record_template_validation`) that wrap `update_state` and enforce schema updates in one place.
  - Store resource metadata under `resources[resource_id]` and append a history entry (`event="resource_uploaded"` or `"template_validated"`).
  - Introduce `state_version` once resource metadata lands; add migration hook to backfill missing keys on older states.
- **Frontend integration**
- Build Dropzone-style uploader on `/batch/_/<name>/` showing progress, checksum, projection, and feature counts using the new API responses.
  - Add template editor with preview table (first N run ids) and error list; disable `Run Batch` when validation fails or results are stale.
  - Persist UI state in the bootstrap payload so refreshes do not lose the latest validation snapshot.
- **Validation + test coverage**
  - Write unit tests for new endpoints covering happy path, invalid files, oversized uploads, CRS mismatch, and stale template detection.
  - Add fixture GeoJSON samples (small square, invalid CRS, duplicate ids) under `tests/data/batch_runner/` for deterministic checks.
  - Provide integration test that simulates upload + template validation, asserting persisted fields (`resources`, `history`, `metadata`).
- **Operational guardrails**
  - Enforce per-file size limit via config (`BATCH_GEOJSON_MAX_MB`) and log drop reasons for future tuning. set default BATCH_GEOJSON_MAX_MB to 10 MB
  - Emit structured logs/events through BatchRunner.logger (see `base._init_logging`) when resources change to aid auditing; consider webhook to Ops channel when large uploads occur.
  - Document cleanup command to remove orphaned resources if state entries are pruned.
- **Exit Criteria**
  - Admin can upload GeoJSON, see validation details, and rerun validations after editing templates without manual filesystem access.
  - BatchRunner state tracks resource metadata, template results, and history entries for both actions.
  - Test suite covers success and failure modes for upload + validation flows with no regressions in Phase 1 scaffolding.

### Phase 3 Implementation Plan – Hydrologic Preprocessing
- **Resource preparation & state schema**
  - Introduce state entries for `preprocessing` (per-run inputs), `resources.dem` / `resources.hydrology` meta, and `control_hashes` entries for topo-sensitive controllers.
  - Add migration hook that backfills new keys on version `< 3`; bump `state_version` accordingly.
  - Define `BatchRunner.preprocess_context` describing DEM sources, buffers, reprojection hints, and WhiteBox settings.
- **Extent derivation pipeline**
  - Implement helper to project each GeoJSON feature to a target CRS (e.g., EPSG:5070), buffer by configurable margin, and compute bounding boxes for DEM requests.
  - Persist derived extents + target CRS per run in the BatchRunner state to avoid recomputation.
- **DEM acquisition & caching**
  - Integrate existing DEM fetch utilities (e.g., `wepppy.topo.dem_downloader`) with rate limiting and disk caching under `resources/dem/`.
  - Store metadata (source, resolution, checksum, storage path) in state; reuse across runs when extents overlap.
  - Add retry/ backoff logic for remote fetch failures; mark runs with degraded status when DEM cannot be acquired.
- **WhiteBox outlet detection & watershed abstraction**
  - Wire WhiteBoxTools helper (from Phase 2 mitigations) to derive pour points for each buffered extent; capture logs/errors.
  - Update stored state per run with outlet coordinates, tool status, and summary artifacts (e.g., GeoJSON pour point).
  - Generate watershed masks and store references for downstream controls.
- **Integration with `Watershed.determine_outlet()`**
  - Expose preprocessing outputs to existing watershed control; ensure outlets land in the NoDb state when runs materialize.
  - Record control hash/digest to detect drift between `_base` and preprocessing output.
- **Error handling & observability**
  - Track per-run preprocessing status (`pending`/`complete`/`failed`) in the BatchRunner history log.
  - Emit structured logs/metrics (duration, tile count, retries) via `BatchRunner.logger` and, if available, existing monitoring hooks.
  - Surface partial failures in UI with actionable messages (e.g., missing DEM coverage) so admins can adjust buffers or fall back.
- **Frontend updates**
  - Extend manage view with preprocessing progress indicators and buttons to rerun preprocessing for select runs.
  - Display derived extents/outlets preview (static map or data table) for quick verification before orchestration.
- **Testing strategy**
  - Unit tests for extent derivation, DEM metadata persistence, WhiteBox invocation (use stubs/mocks for external binaries).
  - Integration test that simulates end-to-end preprocessing for a small GeoJSON, verifying state fields and cached resources.
  - Add regression test ensuring migrating older states (<v3) preserves existing metadata and adds defaults.
- **Exit Criteria**
  - Each feature in the uploaded GeoJSON produces buffered extents, DEM artifacts, and outlet metadata stored in the BatchRunner state.
  - Failures surface in UI + state snapshot with clear remediation paths; rerun workflow supports retrying individual runs.
  - Automated tests cover extent calculations, state migrations, DEM caching, and error paths.

## Open Questions (Resolved)
- **Omni reuse:** Omni must execute per run after WEPP completes; no shared outputs.
- **Quotas:** Disk usage remains a manual responsibility for admins; consider alerts but no automated quotas yet.
- **Rollback after orchestration failure:** Leave directories intact for inspection; provide tooling to clean up manually when safe.
- **Reconfiguring `_base`:** Always update `_base` for new project creation. but configuration must be pushed individually to each run.

### Roger's Draft 0 (leave for reference)

# WEPPcloud Batch Runner

A developer and administrator tool to run batches of watersheds with the same configuration

## User Story

1. A user with very special credentials loads a "Create Batch Runs" page
2. On the "Create Batch Runs" page the user specifies
   - config to use for the batch runs
   - a name for the batch project
3. On submit the backend
   - creates a directory batch project in /wc1/batch/<project_name>
   - creates a Batch Runner instance /wc1/batch/<project_name>/batch_runner.nodb
   - creates a base project with the config in /wc1/batch/<project_name>/_base
     - we end up with the NoDb singletons in _base (ron.nodb, climate.nodb, etc.) and the directories
     - Omni should always be added to the project.
4. User is redirected to the "WEPPcloud Batch Runner" page `/batch/_/<project_name>/`
5. On the WEPPcloud Batch Runner
   - The user has a new Batch Runner Control where they
     - Upload a .geojson file to the resources directory  (`/wc1/batch/<project_name>/resources`
     - BatchRunner stores the relative path as the `watershed_geojson` property
     - The user specifies a template string generating the `runid` of the watersheds based on the feature properties in the geojson
       - e.g. the template string could be something like "{properties['HucName']}-{properties['Region']}"
       - User has a Validate button to generate the runids from the geojson and template string. The validation checks that they are unique and provides them in the view for review
     - The user has a list of checkboxes that are all checked by default specifying which tasks they want to run for each project
       - Watershed Delineation and Abstraction
       - Landuse
       - Soils
       - Climate
       - WEPP
       - WATAR
       - Omni Scenarios
     - User has a Force Rebuild option that will always run the task for the project
     - User has a "Run Batch" button
       - BatchRunner(ControlBase) serializes all _base controller forms and submits them to `batch_runner_bp`
       - creates a new rq parent job
       - Iterate over the watersheds
         - to create new runids
           - generate `runid` using template string 
           - create `wd` is `/wc1/batch/<project_name>/<runid>`
           - copy the contents of the `_base` project to `/wc1/batch/<project_name>/<runid>`
           - hijack using `json` set ['py/state']['wd'] to the correct runid (similiar to omni)
           - clear locks and nodb cache (similiar to omni)
         - based on run state data stored in BatchRunner and force_rebuild determine if the tasks need to be ran
         - adds jobs to rq parent job with rq job dependency set appropriately.
6. Below the Batch Runner Control will be the run view for the _base project in the same order as `run_0.runs_0`
   - Controls for _base project
     - SBS Upload
     - Channel Delineation
     - Subcatchment Delineation
     - Landuse
     - Soils
     - Climate
     - WEPP
     - Omni
   - The page will be bootstrapped to remove the Build/Run buttons of these controls
   - The user goes through and sets all the options as desired.
   - "Run Batch" updates the `_base` project before running tasks, then when the files are created all of this configuration will be configured to run

## Key Components

### `BatchRunner(NoDbBase)`

- Retains state related to the batch runner and tracks which projects have been ran
- runs the projects using rq worker pool

### `BatchRunner(ControlBase)`

- follows controller_js singleton model

### `batch_runner_bp` routes for the Batch Runner

#### Routes

##### `/batch/create/` Create New BatchRunner project
- specify the config to use
- specify a `batch_name` (must be less 30 characters, lowercase, no special characters)

#####

- View based on `run_0.runs_0` with `BatchRunner(ControlBase)`

## RQ Worker Pool

- spin up limited number of workers e.g. 3 on a special batch channel. Then BatchRunner submits jobs to these worker to limit the number that are processed. greatly scalable via kubernetes.
