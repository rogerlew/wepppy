# Resolve culvert outlets before pruning

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md.

## Purpose and context

Restore road-constrained CULVERT inputs without moving supplied points. Culvert_stream_selection currently tests supplied points against raster streams. The batch RQ job prunes streams before child run creation. Instead resolve native WBT outlets on the original network before pruning, record them, select networks preserving them, and use those fixed outlets downstream.

## Progress

- [x] Diagnose seven incident point-off-stream failures and establish operator direction.
- [x] Review and commit reconciled contract checkpoint (066b04755).
- [x] Implement original-outlet preparation, selection, downstream propagation, archive and admission guards.
- [x] Run real-raster regression tests and incident replay; complete correctness review. Full suite attempted but collection blocked by local Flask secret configuration.

## Surprises & Discoveries

All seven supplied points are road-snapped fallback points one cell from streams. January documentation permits this; November selection rejects it. SSURGO 502 failures affect the other 26 runs separately.

## Decision Log

2026-11-17 operator: resolve exact original-network outlets before pruning. Use existing FindOutlet rather than nearest-channel snapping. Keep original input points and retained policy semantics. Add an explicit selection basis to new batch admission so existing receipts cannot silently change meaning.

## Plan of Work

First amend the canonical stream-selection contract, ADR-0144, API spec and developer guide; obtain two read-only reviews and commit this checkpoint. Then add original-outlet preparation/readback to wepppy/nodb/culvert_stream_selection.py, call it from run_culvert_batch_rq before short-stream pruning, select by resolved outlet in CulvertsRunner, and install the recorded outlet in _process_culvert_run before subcatchment delineation. Preserve crop-relative pixel coordinates and actual stream-cell center. Add server artifact injection guard in culvert_routes.py and skeleton retention. Update affected tests and NoDb/RQ guidance. Do not change thresholds, SSURGO, queue topology or production data.

## Concrete Steps and Validation

Work in /home/workdir/wepppy-culvert-outlets on fix/culvert-original-outlets. Use wctl run-pytest for tests/culverts and affected RQ/API modules, then tests --maxfail=1; validate the actual candidate checkout in an isolated container if the shared stack mounts another checkout. Use existing native WhiteboxTools for all raster operations. Replay the copied incident payload in disposable local storage, retaining per-ID original/selected outlet coordinates, network membership and selected passes. Validate generated outlet GeoJSON and cropped pixel conversion, archive/restore identities, malformed artifacts, empty/no-outlet cases and old policy behavior. Unit success alone does not establish complete WEPP success. Run doc-lint and ADR date checks, followed by independent correctness review.

## Idempotence and Recovery

Prepare immutable source-bound records before candidate rasters. Reuse only matching verified inputs; partial state may rebuild before any selected receipts exist. Never mutate old production runs. Revert the new admission basis for rollback while preserving retained artifact semantics.

## Outcomes & Retrospective

Implemented and reviewed locally. All33 incident outlets resolve/select; all seven formerly rejected culverts generate native TOPAZ topology. Focused tests pass; full suite collection is environment-blocked. See artifacts/validation.md for commands, hashes and limits. No deployment performed.

## Interfaces and dependencies

Keep native WBT FindOutlet, Rasterio and existing watershed polygon rasterization. Add original_outlets.json at batch root with relative hashed input identities and per-ID resolved/failed results. New policy basis original_outlet_v1 makes this required. Selection receipts preserve supplied point fields and add resolved outlet identity. Existing models remain responsible for NoDb persistence and run-specific channel maps.

2026-11-17 completion update: retained native replay and independent approval; full-suite limit is explicit.
