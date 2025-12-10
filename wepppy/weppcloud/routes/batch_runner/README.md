# WEPPcloud Batch Runner (Pure UI Snapshot)

> **See also:** [AGENTS.md](../../../../AGENTS.md) for Working with NoDb Controllers and RQ Background Tasks sections.

The batch runner feature now lives as a proof-of-concept that stitches together existing NoDb primitives with a thin blueprint and controller shell. The goal is to stand up the end-to-end shape of the workflow before hardening it, with an emphasis on reusing the `_base` project controls and keeping the mental model familiar to power users. The UI now uses the Pure templates (`manage_pure.htm`, `batch_runner_pure.htm`); the legacy Bootstrap pages were removed.

## Intent
- Give admins a sandbox for preparing a canonical `_base` project and cloning it across many watersheds.
- Lean on existing controllers, templates, and NoDb singletons so the batch runner feels like "run_0 at scale" rather than a new subsystem.
- Favor rapid validation of the core flow (create → manage → geojson ingest → template preview) over polish or security gates during this phase.

## Key Components

### `batch_runner_bp`
- `/batch/create/` is gated by `roles_required("Admin")` and the `BATCH_RUNNER_ENABLED` flag. It collects a batch name and base config, then calls `_create_batch_project()`.
- `_create_batch_project()` resolves the batch root (`get_batch_root_dir()`), creates `<batch_name>/`, and instantiates `BatchRunner`, which immediately bootstraps `_base/` using the selected config.
- `/batch/_/<batch_name>/` resolves `BatchRunner.getInstanceFromBatchName()`, reaches into the `_base/` directory, and hydrates the same NoDb singletons that the run-0 blueprint exposes (Ron, Landuse, Soils, Watershed, Omni, etc.). The manage view renders `manage_pure.htm` which includes `batch_runner_pure.htm`.
- `/upload-geojson` accepts GeoJSON/JSON uploads, persists them into `<batch_name>/resources/`, instantiates a `WatershedCollection`, and lets `BatchRunner` record the analysis metadata.
- `/upload-sbs-map` (Admin) accepts a soil burn severity raster, validates it with `sbs_map_sanity_check`, stores it once under `<batch_name>/resources/`, and records metadata on the `BatchRunner` so each per-watershed run can crop it after DEM fetch.
- `/validate-template` replays the stored `WatershedCollection`, runs template evaluation, and persists the results on the `BatchRunner` instance before returning a JSON payload to the UI.

### `BatchRunner` (NoDb)
- Extends `NoDbBase` and stores its state in `batch_runner.nodb` inside the batch working directory.
- On initialization it records the chosen base config and prepares three directories: `_base/` (canonical project scaffold), `runs/` (future per-watershed clones), and `resources/` (uploads).
- `_init_base_project()` wipes and recreates `_base/`, then instantiates `Ron` with `run_group='batch'` and `group_name=<batch_name>`, which in turn cascades to the rest of the NoDb singletons when they initialize.
- Tracks two primary blobs of state today: `_geojson_state` (analysis metadata for the registered watershed collection) and `_runid_template_state` (last validation result). Both are guarded by the standard NoDb locking helpers via `nodb_setter`.
- Tracks optional `_sbs_map` + metadata when uploaded through the new UI; `_maybe_init_sbs_map` prefers this batch-level file over per-config `landuse.sbs_map`, crops it with `raster_stacker`, and re-validates Disturbed/Baer mods per run.
- Exposes helpers for rehydrating a `WatershedCollection` and for persisting template validation output so the UI can refresh without re-reading the upload.

### `WatershedCollection`
- Wraps a GeoJSON FeatureCollection and performs lightweight analysis (feature count, bounding box, CRS detection, property schema, checksum).
- Provides deterministic template evaluation with a curated set of formatting helpers (`slug`, `lower`, `zfill`, etc.), surfaced both for preview rows and duplicate detection.
- `load_from_analysis_results()` allows `BatchRunner` to persist only metadata while still reconstructing the full collection when validations are rerun.

### Run ID Semantics (`NoDbBase.runid`)
- `NoDbBase.runid` now prefixes run IDs with `<run_group>;;<group_name>;;` when those attributes are present. The `_base` project therefore resolves to `batch;;<batch_name>;;_base`, which keeps existing `/weppcloud/<runid>/<config>` routes working with no special casing.
- Per-watershed runs will inherit the same prefix once cloning logic lands, ensuring logs, redis channels, and HTTP routes can reuse established patterns.

## Request Lifecycle (Current PoC)
1. **Create** – Admin loads `/batch/create/`, submits a batch name and base config. The server validates inputs, scaffolds the workspace, and redirects to the manage view.
2. **Manage** – `/batch/_/<batch_name>/` renders the standard controls for the `_base` project. The page currently lacks bespoke batch-runner bootstrap data; the context rebuild is queued as a follow-up.
3. **GeoJSON Intake** – Upload endpoint stores the file under `resources/`, runs analysis via `WatershedCollection`, and persists the metadata through `BatchRunner.register_geojson()`.
4. **Template Preview** – Template validation rebuilds the `WatershedCollection`, generates prospective run IDs, records the summary (`_runid_template_state`), and returns duplicates/errors for UI display.

## Current Constraints & Gaps
- Controllers remain in a prototype shape—the bootstrap payload still mirrors run-0 and does not emit batch-aware data structures.
- RQ orchestration, `_base` cloning into per-run directories, and job submission are intentionally deferred.
- No durability beyond the persisted GeoJSON metadata and template snapshot; retries and resuming work are not wired up yet.
- Minimal input hardening: feature flag + admin check exist, but file validation stops at GeoJSON semantics.

## Next Steps (guided)
- [ ] Add batch-runner control context back into the manage view so the UI can read `BatchRunner` state.
- [ ] Bootstrap dedicated controllers/JS for the custom batch view instead of piggybacking on run-0 bootstrap data.
- [ ] Implement the batch execution path: clone `_base` into per-feature run directories, seed rq jobs, and wire progress reporting.

## Architectural Principles To Preserve
- Reuse NoDb singletons directly rather than layering dictionaries or DTOs—keeps runtime behavior aligned with long-standing patterns.
- Treat the batch runner as an orchestration layer over the familiar run controls; innovations should be in flow coordination, not new data models.
- Iterate in thin slices (create → manage → run) so we can steer the design before locking in interfaces or security posture.
