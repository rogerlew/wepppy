# WP-3 Features Export Writers, Packaging, and Manifest

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` will be kept current as implementation proceeds.

This plan follows the repository template at `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Implement WP-3 only for `wepppy.nodb.mods.features_export`: format writers, single-layer packaging behavior, and manifest generation from a pre-resolved plan. After this change, callers with a `ResolvedExportPlan` and prepared per-layer payloads can generate export artifacts for all five formats (`geojson`, `geoparquet`, `kmz`, `geopackage`, `geodatabase`) and write a deterministic `manifest.json` without route/task/UI orchestration.

## Progress

- [x] (2026-03-26 17:22Z) Read required context: root/nodb/tests AGENTS, WP-3 spec sections, and existing WP-1/WP-2 modules.
- [x] (2026-03-26 17:22Z) Authored and activated this WP-3 ExecPlan at `docs/mini-work-packages/20260326_features_export_wp3_execplan.md`.
- [x] (2026-03-26 17:29Z) Implemented exporter contracts and format writer modules under `wepppy/nodb/mods/features_export/exporters/`.
- [x] (2026-03-26 17:30Z) Implemented manifest builder/writer split in `wepppy/nodb/mods/features_export/manifest.py`.
- [x] (2026-03-26 17:31Z) Updated package exports and WP-3 completion status in `specification.md`.
- [x] (2026-03-26 17:33Z) Added focused unit tests for exporters and manifest under `tests/nodb/mods/`.
- [x] (2026-03-26 17:39Z) Ran required validation commands; all passed.
- [x] (2026-03-26 17:39Z) Completed correctness self-review and QA-oriented review; patched one medium robustness finding.
- [x] (2026-03-26 17:39Z) Finalized retrospective and residual risks.

## Surprises & Discoveries

- Observation: No nested `AGENTS.md` exists under `wepppy/nodb/mods/features_export`; nearest applicable module guidance remains `wepppy/nodb/AGENTS.md` plus root `AGENTS.md`.
  Evidence: Repository search for `AGENTS.md` paths shows no `features_export/AGENTS.md` file.
- Observation: Payload and zip helpers accepted non-string mapping keys, which could produce key-type mismatch behavior at lookup time.
  Evidence: Self-review on `resolve_layer_payload_pairs` and `package_files_as_zip` found string coercion/lookup mismatch risk; fixed by enforcing explicit non-empty string keys with contract errors.

## Decision Log

- Decision: Keep WP-3 interfaces fully plan/payload driven and avoid any run-file resolution logic.
  Rationale: Specification section 14 isolates writer responsibilities and explicitly excludes orchestration/data resolution from WP-3 scope.
  Date/Author: 2026-03-26 / Codex

- Decision: Use deterministic filenames derived from `output_layer_id` for per-layer outputs and deterministic bundle/container names for artifacts.
  Rationale: Required by WP-3 deterministic naming contract and simplifies cache/manifest assertions.
  Date/Author: 2026-03-26 / Codex

- Decision: Keep geodatabase conversion behind injectable callbacks but enforce hard failure when backend capability is absent.
  Rationale: This preserves explicit capability failure semantics and enables hermetic unit tests without Docker/f_esri runtime.
  Date/Author: 2026-03-26 / Codex

- Decision: Treat non-string payload/zip mapping keys as contract violations.
  Rationale: Prevents ambiguous coercion and ensures deterministic key matching to `output_layer_id`.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

WP-3 implementation is complete and validated. The exporter surface now provides deterministic writer dispatch, typed request/payload/result contracts, single-layer zip packaging behavior for `geojson|geoparquet|kmz`, and multi-layer container behavior for `geopackage|geodatabase` with explicit backend capability checks for `f_esri`. Manifest generation is now split into a pure builder and a separate serializer/writer and includes the required artifact/cache/dependency/layer-count/warning fields. Focused tests were added and all required validation commands passed after a review-driven robustness fix.

## Context and Orientation

`wepppy/nodb/mods/features_export/contracts.py` and `planner.py` already provide canonical request normalization and `ResolvedExportPlan` generation. `dependency_tracker.py` and `cache_key.py` already provide deterministic dependency snapshots/fingerprints and cache-key/index helpers. WP-3 adds export artifact production and manifest writing on top of those completed contracts.

Primary files for this plan:

- New writer package: `wepppy/nodb/mods/features_export/exporters/`
- New manifest module: `wepppy/nodb/mods/features_export/manifest.py`
- Package API update: `wepppy/nodb/mods/features_export/__init__.py`
- Spec status update: `wepppy/nodb/mods/features_export/specification.md`
- Tests: `tests/nodb/mods/test_features_export_exporters.py` and `tests/nodb/mods/test_features_export_manifest.py`

## Plan of Work

Implement a typed writer contract in `exporters/base.py` that accepts a pre-resolved plan, deterministic output directory targets, and prepared per-layer payloads keyed by `output_layer_id`. Implement concrete writers for each format token plus a dispatcher. For single-layer formats (`geojson`, `geoparquet`, `kmz`), each resolved layer writes one deterministic file and then bundles those outputs into one zip artifact via `exporters/packaging.py`. For multi-layer formats, `geopackage` emits one container file; `geodatabase` emits one `.gdb.zip` by first building a temporary gpkg container and converting through `f_esri` with explicit capability errors.

Implement `manifest.py` with a pure builder function that assembles deterministic manifest payload mappings and a separate write function that serializes to disk. Include required fields: resolved request payload, catalog/version info, dependency snapshot/fingerprint input, per-layer scope metadata, row/feature counts, warnings, artifact/cache fields, source job linkage, and generation timestamp.

Add focused unit tests to verify dispatch, deterministic naming, packaging behavior, geodatabase conversion boundary mocking, and manifest shape determinism/warning propagation.

## Concrete Steps

From `/workdir/wepppy`:

1. Add new exporter modules and manifest module.
2. Update package exports and specification status notes.
3. Add unit tests for exporter + manifest behavior.
4. Run required validation commands:
   - `wctl run-pytest tests/nodb/mods/test_features_export_exporters.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/test_features_export_manifest.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/test_features_export_dependency_tracker.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/test_features_export_cache_key.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/test_features_export_planner.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods --maxfail=1`
   - `wctl run-stubtest wepppy.nodb.mods.features_export`
   - `wctl check-test-stubs`
   - `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md`
   - `wctl doc-lint --path docs/mini-work-packages/20260326_features_export_wp3_execplan.md`

## Validation and Acceptance

Acceptance for this plan is met when the writer APIs generate deterministic artifacts for all five formats from pre-resolved inputs, single-layer formats are zipped correctly, geodatabase uses the gpkg -> `f_esri` conversion path with explicit failure when unavailable, manifest generation includes all required minimum fields, and all required tests/lint commands pass.

## Idempotence and Recovery

All edits are additive and repeatable. Writer outputs are directed to caller-provided artifact directories so reruns replace deterministic targets. If a writer run fails, the caller can remove and recreate the artifact directory and rerun the same write request without mutating planner/cache state.

## Artifacts and Notes

Validation outcomes (post-fix rerun):

- `wctl run-pytest tests/nodb/mods/test_features_export_exporters.py --maxfail=1` -> pass (8 passed)
- `wctl run-pytest tests/nodb/mods/test_features_export_manifest.py --maxfail=1` -> pass (2 passed)
- `wctl run-pytest tests/nodb/mods/test_features_export_dependency_tracker.py --maxfail=1` -> pass (3 passed)
- `wctl run-pytest tests/nodb/mods/test_features_export_cache_key.py --maxfail=1` -> pass (4 passed)
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py --maxfail=1` -> pass (13 passed)
- `wctl run-pytest tests/nodb/mods --maxfail=1` -> pass (427 passed)
- `wctl run-stubtest wepppy.nodb.mods.features_export` -> pass (no issues in 15 modules)
- `wctl check-test-stubs` -> pass
- `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md` -> pass
- `wctl doc-lint --path docs/mini-work-packages/20260326_features_export_wp3_execplan.md` -> pass

Review/fix notes:

- Correctness self-review: one medium robustness finding (non-string mapping key handling in payload/zip helpers).
- QA-oriented review: no additional high/medium findings after applying the key-type enforcement fix.

## Interfaces and Dependencies

Planned WP-3 interfaces:

- `exporters.base`: typed writer request/payload/result dataclasses and writer protocol.
- `exporters.__init__`: writer dispatch map and `get_export_writer` helper.
- `manifest.py`: pure builder (`build_export_manifest`) and file writer (`write_export_manifest`).

Dependency boundary for geodatabase conversion:

- Use `wepppy.f_esri.has_f_esri` and `wepppy.f_esri.c2c_gpkg_to_gdb` via injectable callbacks in writer contracts to keep unit tests hermetic.
- Missing `f_esri` capability must raise explicit writer-capability error (no silent fallback wrapper).

---

Revision note (2026-03-26 17:22Z): Initial WP-3 ExecPlan created before implementation; seeded with explicit scope, milestones, and required validation/review loop.
Revision note (2026-03-26 17:39Z): Updated plan to completed state with implementation outcomes, validation evidence, and review/fix retrospective.
