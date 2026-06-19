# SSURGO Project SQLite Cache

**Status**: Implementation complete; external full-suite blocker recorded (2026-06-19)
**Timezone**: UTC

## Overview
SSURGO tabular data is currently cached through module-level SQLite files in `wepppy/soils/ssurgo/ssurgo.py`, including a shared `/dev/shm` copy of bundled data when available. That cache can become stale relative to current NRCS SSURGO responses, so this package moves rebuild-time caching to each project under `<wd>/soils/` while making direct `ssurgo.py` use default to an in-memory database.

## Objectives
- Create and use a project-local SSURGO SQLite cache during `build_soils`, stored under the run's `soils` directory.
- Write a human-readable Markdown provenance sidecar next to each file-backed SSURGO/STATSGO cache.
- Preserve older project compatibility: rebuilding soils on an existing run should create the cache if it is missing, without requiring migration tooling.
- Serialize cache behavior parameters and UI-selected rebuild options through `wepppy/nodb/core/soils.py`, while deriving absolute cache paths from the active run directory at runtime.
- Add an Advanced Options checkbox in `wepppy/weppcloud/templates/controls/soil_pure.htm` labeled `Clear SSURGO cache on rebuild`, using the pure UI macro.
- Make `wepppy/soils/ssurgo/ssurgo.py` default to an in-memory SQLite cache unless a caller supplies an explicit cache path.
- Require two independent subagent reviews and written disposition of every finding before closure.

## Scope

### Included
- `wepppy/soils/ssurgo/ssurgo.py` cache-path refactor:
  - Remove shared module-level SSURGO cache as the default path for normal constructor use.
  - Support explicit file-backed cache paths for project builds.
  - Support in-memory default behavior for direct `SurgoSoilCollection(...)` callers.
  - Use `ssurgo_tabular_cache.sqlite` for project SSURGO caches and `statsgo_tabular_cache.sqlite` for project STATSGO caches.
  - Write `<cache>.meta.md` sidecars derived from cache runtime/source metadata; keep SQLite as the canonical machine-readable cache artifact.
  - Preserve existing table initialization, sync, bad-key table, worker-view, and write behavior.
- `wepppy/nodb/core/soils.py` NoDb serialization:
  - Add persisted fields/properties for `clear_ssurgo_cache_on_rebuild` and any cache metadata needed for compatibility, but do not serialize absolute cache paths.
  - Derive the project SSURGO cache path deterministically from `self.soils_dir` each time it is needed.
  - Expand loaded legacy instances safely so old `soils.nodb` files receive defaults on rebuild.
  - Ensure every current `Soils` build path that creates `SurgoSoilCollection` passes a project-local cache path when using SSURGO/STATSGO tabular data: `build_statsgo`, `_build_spatial_api` primary SSURGO, `_build_spatial_api` STATSGO fallback, `_build_single`, and `_build_gridded`.
  - Audit direct non-`Soils` callers. `wepppy/soils/ssurgo/spatializer.py` may stay intentionally in-memory; `wepppy/soils/ssurgo/data/surgo/build/surgo_tabular_db_builder.py` must pass its explicit builder database path so bundled DB generation remains file-backed.
- `build_soils` request flow:
  - Parse the new boolean from the build form in `wepppy/microservices/rq_engine/soils_routes.py`.
  - Persist it to `Soils` before enqueueing, and before the batch-mode no-enqueue return, so `build_soils_rq` or later batch processing can read the option.
  - If enabled, clear only the project-local SSURGO cache before rebuilding.
- Pure UI and controller wiring:
  - Render the new checkbox with `ui.checkbox_field(...)` in the Advanced Options block of `soil_pure.htm`.
  - Include the checkbox in the serialized build form payload.
  - Add or update controller tests so the posted `URLSearchParams` includes the option.
  - Rebuild generated frontend assets if the repo requires it for `controllers-gl.js`.
- Regression coverage:
  - Unit tests for in-memory default cache behavior and explicit project cache path behavior in `ssurgo.py`.
  - NoDb serialization tests proving old instances get defaults and rebuilt projects create `<wd>/soils/ssurgo_tabular_cache.sqlite` or `<wd>/soils/statsgo_tabular_cache.sqlite`.
  - RQ engine route tests proving boolean parsing and persistence for both normal enqueue and batch no-enqueue flows.
  - Template/controller tests proving the pure checkbox renders and posts.
- Documentation updates:
  - Update durable SSURGO cache documentation in `wepppy/soils/README.md` and `wepppy/soils/ssurgo/ssurgo.md` so they no longer describe shared `/dev/shm` SSURGO cache persistence as the default rebuild behavior.
- Review artifacts:
  - `artifacts/code_review_findings.md` from a `reviewer` subagent.
  - `artifacts/qa_review_findings.md` from a `qa_reviewer` subagent.
  - Disposition notes for every subagent finding: accepted/fixed, rejected with rationale, or deferred with owner and follow-up.

### Explicitly Out of Scope
- Changing SSURGO-to-WEPP parameter formulas, thresholds, unit conversions, or `ksflag` semantics.
- Replacing NRCS SDM Data Access requests or changing the upstream SSURGO query set.
- Adding a cross-project cache service or global cache invalidation mechanism.
- Migrating old projects before they rebuild soils.
- Broad RQ queue dependency rewiring beyond passing the new serialized option through the existing build-soils flow.
- Removing existing bundled SSURGO/STATSGO seed databases from the repository.

## Implementation Fidelity and Evidence
- **Fidelity target**: faithful extraction of existing SSURGO table/cache semantics into project-local storage.
- **Authoritative source path(s)**:
  - `wepppy/soils/ssurgo/ssurgo.py`
  - `wepppy/nodb/core/soils.py`
  - `wepppy/microservices/rq_engine/soils_routes.py`
  - `wepppy/rq/project_rq.py`
  - `wepppy/weppcloud/templates/controls/soil_pure.htm`
  - `wepppy/weppcloud/controllers_js/soil.js`
- **Cutover proof required**: a `Soils.build()` path must instantiate `SurgoSoilCollection` with a cache path under the active run's `soils` directory, and direct `SurgoSoilCollection(mukeys)` use must not write a shared module-level cache file.
- **Acceptance evidence type**: both generated-output and fixture-only. Generated-output means a test or smoke run creates the expected project-local SQLite file under a temporary run `soils` directory.

## Stakeholders
- **Primary**: WEPPcloud users rebuilding SSURGO soils for existing and new projects.
- **Reviewers**: implementation agent, `reviewer` subagent, and `qa_reviewer` subagent.
- **Security Reviewer**: implementation agent must complete a dedicated security review artifact; escalate to a `security_reviewer` subagent if either required subagent review raises unresolved security concerns.
- **Informed**: maintainers of `wepppy/soils/ssurgo`, `wepppy/nodb/core`, RQ engine routes, and frontend controls.

## Success Criteria
- [ ] New projects using SSURGO create a SQLite cache in `<wd>/soils/` during `build_soils`.
- [x] Project SSURGO cache filename is `<wd>/soils/ssurgo_tabular_cache.sqlite`; project STATSGO cache filename is `<wd>/soils/statsgo_tabular_cache.sqlite`.
- [x] File-backed SSURGO/STATSGO caches write adjacent `<cache>.meta.md` provenance sidecars without absolute host paths.
- [x] Older projects without the cache create it gracefully the next time soils are rebuilt.
- [x] The default `SurgoSoilCollection(...)` path in `ssurgo.py` uses an in-memory database and does not refresh or write shared `/dev/shm` SSURGO cache files.
- [x] Explicit project cache paths persist fetched SSURGO rows and are reused across rebuilds unless cleared.
- [x] `clear_ssurgo_cache_on_rebuild` is serialized by `Soils`, posted from the build form, and honored by `build_soils_rq`.
- [x] The Advanced Options panel renders a pure macro checkbox labeled `Clear SSURGO cache on rebuild`.
- [x] If the checkbox is enabled, only the run-scoped SSURGO cache, exact SQLite sidecars `<cache_path>-wal` and `<cache_path>-shm`, and the cache metadata sidecar are removed before rebuild; generated `.sol` files and unrelated run artifacts are not removed by the cache clear.
- [x] Targeted backend, RQ route, frontend controller, and template tests pass, including explicit coverage for all five current `Soils` `SurgoSoilCollection` constructor sites.
- [x] `wepppy/soils/README.md` and `wepppy/soils/ssurgo/ssurgo.md` document the new project-local/default in-memory cache behavior.
- [x] Both subagent review artifacts are present and every finding has a recorded disposition.
- [x] Dedicated security review artifact is present with no unresolved medium/high findings.
- [x] This package and `tracker.md` reflect implementation status and closure evidence; `PROJECT_TRACKER.md` was updated during package creation.

## Parameterization ADR Gate
- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes, in this package and tracker.

Reference: `docs/standards/parameterization-adr-standard.md`

## Compatibility and Regression Plan
Adding a project-local SQLite cache and Markdown provenance sidecar changes run-scoped artifacts and `Soils` NoDb serialization. The implementation must keep this additive: no existing serialized keys may be renamed or removed, and old `soils.nodb` files must load with default values for the new cache option fields. Absolute cache paths must not be serialized; project cache paths and metadata sidecar paths must be derived from the current `Soils.soils_dir` so moved, copied, or forked runs do not retain stale filesystem paths. Regression tests must cover a legacy-style `Soils` object missing the new attributes, the generated `<wd>/soils/` cache artifact and sidecar, batch and non-batch route persistence, and downstream generated `.sol` outputs from a representative build path or focused stubbed build.

## Dependencies

### Prerequisites
- Existing `Soils` NoDb controller locking and serialization behavior.
- Existing `SurgoSoilCollection` table initialization and sync behavior.
- Existing RQ engine `build-soils` endpoint and `build_soils_rq` worker path.
- Existing pure UI macros in `wepppy/weppcloud/templates/controls/_pure_macros.html`.

### Blocks
- None identified. This package reduces stale-cache risk for future SSURGO parameterization investigations.

## Related Packages
- **Related**: [20260522_ssurgo_corestrictions_kslast_viability](../20260522_ssurgo_corestrictions_kslast_viability/package.md)
- **Related**: [20260325_disturbed_lookup_hardening](../20260325_disturbed_lookup_hardening/package.md)

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium-High.

## Security Impact and Review Gate
- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The change modifies an authenticated build endpoint payload and introduces run-scoped SQLite file creation/deletion under the project `soils` directory. It must prove path confinement, avoid deleting unrelated files, and preserve RQ/build access controls.
- **Security review artifact**: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/security_review.md`

Use `docs/prompt_templates/security_review_template.md` to create `artifacts/security_review.md` during implementation. Because this package is triaged `high`, the dedicated security review artifact is mandatory before closure.

## Hardening and Callus Softening
- **Failure signature(s)**: Stale SSURGO tabular rows served from shared SQLite cache after upstream SSURGO changes.
- **Related prior hardening efforts**: `docs/work-packages/20260522_ssurgo_corestrictions_kslast_viability/`
- **Health signals**: New rebuilds populate project-local cache files; clearing the cache forces fresh SSURGO fetches for missing rows; direct module use leaves no shared persistent cache by default.
- **Danger signals**: Cache clear deletes non-cache artifacts, direct callers lose expected fixture behavior, multiprocessing worker view opens an in-memory database after the parent connection closes, or old projects fail to load missing serialized fields.
- **Observation window**: 14 days after production deployment.
- **Temporary calluses introduced**: None planned.
- **Callus softening hypothesis**: If project-local caches remove stale shared-cache incidents, future cleanup may remove remaining shared `/dev/shm` cache bootstrapping code after a separate compatibility audit.

## References
- `wepppy/soils/ssurgo/ssurgo.py` - Current SSURGO/STATSGO SQLite cache and `SurgoSoilCollection` implementation.
- `wepppy/nodb/core/soils.py` - Soils NoDb serialization and build dispatch.
- `wepppy/microservices/rq_engine/soils_routes.py` - RQ engine build-soils request parsing and enqueue.
- `wepppy/rq/project_rq.py` - Worker-side `build_soils_rq` execution.
- `wepppy/weppcloud/templates/controls/soil_pure.htm` - Soil Advanced Options UI.
- `wepppy/weppcloud/controllers_js/soil.js` - Soil build form serialization and event handling.
- `wepppy/soils/README.md` - Durable soils documentation that currently describes shared cache behavior.
- `wepppy/soils/ssurgo/ssurgo.md` - SSURGO conversion/cache notes that must be updated with the new cache contract.
- `tests/soils/test_ssurgo.py` and `tests/soils/test_ssurgo_request_errors.py` - Existing SSURGO tests.
- `tests/nodb/test_soils_gridded_root_creation.py` - Existing gridded soils build-path tests.
- `tests/microservices/test_rq_engine_soils_routes.py` - Existing RQ engine soils route tests.
- `tests/weppcloud/routes/test_pure_controls_render.py` - Existing pure template render tests.
- `wepppy/weppcloud/controllers_js/__tests__/soil.test.js` - Existing soil controller tests.

## Deliverables
- Updated cache implementation and call sites.
- Updated NoDb serialized fields/properties.
- Updated UI and controller build payload handling.
- Updated durable SSURGO cache documentation.
- Regression tests and validation output.
- Dual subagent review artifacts with disposition notes.
- Dedicated security review artifact.

## Follow-up Work
- Consider a later cleanup package to remove unused global SSURGO cache bootstrapping after all direct callers are audited.
- Consider operator documentation for when to enable cache clearing during suspected SSURGO stale-data incidents.
