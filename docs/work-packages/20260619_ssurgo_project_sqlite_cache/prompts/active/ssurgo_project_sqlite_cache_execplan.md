# Implement project-local SSURGO SQLite caches

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`. It is self-contained so an agent can implement the feature without relying on chat history.

## Purpose / Big Picture

WEPPcloud currently lets SSURGO soil rebuilds reuse a module-level SQLite cache from `wepppy/soils/ssurgo/ssurgo.py`. That cache can be stale relative to the current NRCS SSURGO service. After this change, every project rebuild that uses SSURGO tabular data creates or reuses a SQLite cache in its own `<wd>/soils/` directory, and the soil panel offers a checkbox to clear that project cache before rebuilding.

The visible proof is simple: start from a run directory without a project SSURGO cache, trigger `build_soils`, and observe a SQLite cache file under that run's `soils` directory. If `Clear SSURGO cache on rebuild` is checked, the old project cache is deleted first and recreated from fresh fetches as needed. Direct Python use of `SurgoSoilCollection(mukeys)` should use an in-memory SQLite database by default and should not write to shared `/dev/shm` cache files.

## Progress

- [x] (2026-06-19 19:04 UTC) Work package, tracker, review disposition template, and initial ExecPlan authored.
- [x] (2026-06-19 19:16 UTC) Scoping review findings patched into package, tracker, and ExecPlan.
- [x] (2026-06-19 19:24 UTC) QA scoping findings patched into package, tracker, ExecPlan, and security artifact.
- [ ] Refactor `wepppy/soils/ssurgo/ssurgo.py` to support explicit file-backed caches and in-memory default behavior.
- [ ] Update `wepppy/nodb/core/soils.py` serialization and build paths to use project-local cache files.
- [ ] Wire `clear_ssurgo_cache_on_rebuild` through the RQ engine route and worker-visible NoDb state.
- [ ] Add the pure macro checkbox and update frontend controller/test expectations.
- [ ] Add targeted backend, frontend, and route regression tests.
- [ ] Run validation commands and record results.
- [ ] Run `reviewer` and `qa_reviewer` subagents, write artifacts, and disposition every finding.
- [ ] Update tracker/package closure notes.

## Surprises & Discoveries

- Observation: `SurgoCollectionWorkerViewFactory` opens a read-only SQLite connection from `self._db_path` before process workers build individual soils.
  Evidence: `wepppy/soils/ssurgo/ssurgo.py` constructs `SurgoCollectionWorkerViewFactory(self._db_path)` in `SurgoSoilCollection.makeWeppSoils`.
- Observation: The RQ engine `build-soils` route currently persists `initial_sat` and disturbed `sol_ver` before enqueueing `build_soils_rq`; the worker later reloads `Soils` from NoDb.
  Evidence: `wepppy/microservices/rq_engine/soils_routes.py` sets `soils.initial_sat`, then enqueues `build_soils_rq(runid)`.

## Decision Log

- Decision: `ssurgo.py` should default to in-memory SQLite, while `Soils` passes a project-local cache path for project builds.
  Rationale: This satisfies the user's stale-cache requirement without removing cache reuse for rebuilds inside the same project.
  Date/Author: 2026-06-19 19:04 UTC / Codex.
- Decision: Cache clearing deletes only the named project-local SQLite file and exact SQLite sidecars `<cache_path>-wal` and `<cache_path>-shm`.
  Rationale: Deleting the whole `soils` directory would remove generated `.sol` outputs and unrelated artifacts.
  Date/Author: 2026-06-19 19:04 UTC / Codex.
- Decision: The new checkbox is serialized as NoDb state, not passed directly into the worker queue call.
  Rationale: Existing `build_soils_rq` accepts only `runid`, so persisting the option in `Soils` preserves current queue shape and avoids unnecessary dependency-edge changes.
  Date/Author: 2026-06-19 19:04 UTC / Codex.
- Decision: Use fixed project cache filenames `ssurgo_tabular_cache.sqlite` and `statsgo_tabular_cache.sqlite`.
  Rationale: Fixed names make generated artifacts easy to test, let cache clearing target exact files, and avoid serializing absolute paths.
  Date/Author: 2026-06-19 19:24 UTC / Codex.
- Decision: Preserve the bundled SSURGO DB builder as a file-backed direct caller by passing its explicit `_db` path, while treating `spatializer.py` as intentionally in-memory unless implementation evidence shows it needs persistence.
  Rationale: The builder exists to create a durable bundled database, but the spatializer sample path does not need persistent cache reuse.
  Date/Author: 2026-06-19 19:24 UTC / Codex.

## Outcomes & Retrospective

No implementation outcomes yet. Fill this section after each milestone with what changed, what was proven, and what remains.

## Context and Orientation

`wepppy/soils/ssurgo/ssurgo.py` contains the SSURGO tabular retrieval and SQLite cache logic. `SurgoSoilCollection` receives a set of SSURGO map unit keys, initializes cache tables, fetches missing rows from the NRCS SDM Tabular API, stores them in SQLite, and builds WEPP `.sol` files from the cached rows. Today the module sets `_ssurgo_cache_db` and `_statsgo_cache_db` near import time, copying bundled database files into `/dev/shm` when available.

`wepppy/nodb/core/soils.py` is the project-level NoDb controller. NoDb means the project stores controller state in files under the run directory rather than in a central relational database. `Soils.build()` dispatches to different soil build modes. Current `Soils` paths that construct `SurgoSoilCollection` are `build_statsgo`, `_build_spatial_api` primary SSURGO, `_build_spatial_api` STATSGO fallback, `_build_single`, and `_build_gridded`; all five must pass project-local cache paths.

`wepppy/microservices/rq_engine/soils_routes.py` handles `POST /rq-engine/api/runs/{runid}/{config}/build-soils`. The frontend soil controller serializes `form#soil_form` and posts it to that endpoint. The route persists build inputs on `Soils` and enqueues `build_soils_rq(runid)`. The worker in `wepppy/rq/project_rq.py` reloads `Soils` and calls `Soils.build()`.

`wepppy/weppcloud/templates/controls/soil_pure.htm` renders the soil panel. Its Advanced Options block already uses `ui.checkbox_field` for `checkbox_ksflag`; the new checkbox must use the same pure UI macro. `wepppy/weppcloud/controllers_js/soil.js` posts the whole form with `WCForms.serializeForm(formElement, { format: "url" })`, so a checked checkbox will appear in the `URLSearchParams`. Tests live in `wepppy/weppcloud/controllers_js/__tests__/soil.test.js`.

## Plan of Work

First, refactor `ssurgo.py` to decouple cache storage from module import. Add an explicit constructor argument to `SurgoSoilCollection`, for example `cache_db_path: Optional[str] = None`, and a mode flag or helper that selects an in-memory SQLite URI when no path is supplied. Preserve the existing schema creation and `_sync` behavior. The critical design point is that `makeWeppSoils` builds a `_SurgoCollectionWorkerView` before spawning worker processes, so the in-memory cache only needs to be readable during that pre-worker view build. If `SurgoCollectionWorkerViewFactory` still expects a filesystem path, update it to accept either a live connection export, a SQLite URI, or a small data-view builder method that can read from the parent connection before workers start. Do not let process workers open the in-memory cache directly after the parent connection closes.

Second, add cache behavior fields to `Soils`. Define deterministic cache filenames under `self.soils_dir`: `ssurgo_tabular_cache.sqlite` for SSURGO and `statsgo_tabular_cache.sqlite` for STATSGO. Add a boolean property `clear_ssurgo_cache_on_rebuild`, defaulting to `False`, and persist it through `nodb_setter`. Do not serialize absolute cache paths. In `_post_instance_loaded`, backfill missing option attributes for old serialized objects. Add a helper that returns the project-local cache path from the current `self.soils_dir` and creates `self.soils_dir` before use. Add a helper that clears only the cache file and exact sidecars `<cache_path>-wal` and `<cache_path>-shm` after resolving paths under `self.soils_dir`.

Third, update all `Soils` paths that create `SurgoSoilCollection`. For `build_statsgo`, `_build_spatial_api` primary SSURGO, `_build_spatial_api` STATSGO fallback, `_build_single`, and `_build_gridded`, pass the appropriate project cache path. At the beginning of a rebuild, if `clear_ssurgo_cache_on_rebuild` is true, clear the project-local cache before constructing `SurgoSoilCollection`. Keep cache clearing inside existing locking or directory-root locking so concurrent rebuilds do not interleave deletion and writes.

Fourth, update the build route and frontend. In `soils_routes.py`, parse the request with `boolean_fields={"clear_ssurgo_cache_on_rebuild"}` or the final field name chosen in the template. Persist the boolean on `Soils` before enqueueing and before the `run_group == "batch"` no-enqueue return. In `soil_pure.htm`, add `ui.checkbox_field("clear_ssurgo_cache_on_rebuild", "Clear SSURGO cache on rebuild", checked=soils.clear_ssurgo_cache_on_rebuild, attrs={"class": "disable-readonly"})` in Advanced Options. Because `soil.build()` already serializes the form, avoid adding bespoke JavaScript unless tests show the form helper omits unchecked checkboxes. Update tests to assert checked, absent, and batch-route behavior.

Fifth, add tests and durable docs. Keep tests hermetic and avoid real NRCS network calls. For `ssurgo.py`, monkeypatch fetch functions to return small rows and use `tmp_path` for explicit file cache tests. For in-memory default tests, assert no `/dev/shm/surgo_tabular.db` is created or touched by the direct constructor path; if direct filesystem observation is brittle, assert the selected connection path/mode through a test-visible helper. For `Soils`, use `Soils.__new__` stubs like `tests/nodb/test_soils_gridded_root_creation.py` to verify cache path creation and clearing without running full builds. Add explicit coverage or an inspection artifact proving all five current `Soils` constructor sites pass the appropriate cache path. For direct non-`Soils` callers, update `wepppy/soils/ssurgo/data/surgo/build/surgo_tabular_db_builder.py` to pass its explicit `_db` path, and either leave `wepppy/soils/ssurgo/spatializer.py` intentionally in-memory with a documented disposition or pass a cache path if implementation evidence shows persistence is required. For the RQ engine route, extend `tests/microservices/test_rq_engine_soils_routes.py` to assert the parsed boolean is stored on `DummySoils` in both normal enqueue and batch no-enqueue flows. For the template and controller, extend existing pure render and Jest tests. Update `wepppy/soils/README.md` and `wepppy/soils/ssurgo/ssurgo.md` so they describe project-local rebuild caches and in-memory direct defaults instead of shared `/dev/shm` persistence as the default rebuild behavior.

Sixth, run validation and reviews. Use the commands in `Validation and Acceptance`. Spawn `reviewer` and `qa_reviewer` subagents after implementation and tests pass locally. Save their findings to the required artifact files, then disposition each finding in the artifact or tracker. Accepted findings must be fixed and rechecked; rejected findings need a concrete rationale.

## Concrete Steps

Work from repository root:

    cd /home/workdir/wepppy

Inspect all relevant constructor sites before editing:

    rg -n "SurgoSoilCollection\\(|_ssurgo_cache_db|_statsgo_cache_db|build_soils_rq|checkbox_ksflag|soil.build|clear_ssurgo" \
      wepppy/soils/ssurgo \
      wepppy/nodb/core/soils.py \
      wepppy/microservices/rq_engine/soils_routes.py \
      wepppy/rq/project_rq.py \
      wepppy/weppcloud/templates/controls/soil_pure.htm \
      wepppy/weppcloud/controllers_js/soil.js

Implement milestone 1 in `wepppy/soils/ssurgo/ssurgo.py`. Keep the public behavior additive: callers may still pass `mukeys` and `use_statsgo`; new cache arguments must be optional. The direct default must not write a shared persistent cache file.

Implement milestone 2 in `wepppy/nodb/core/soils.py`. Add default fields in `__init__`, backfill in `_post_instance_loaded`, and use helper methods for cache filename resolution and cache clearing.

Implement milestone 3 in `wepppy/microservices/rq_engine/soils_routes.py`, `soil_pure.htm`, and `soil.js` tests. If the frontend build updates generated assets, follow the repo's existing npm build command and include `wepppy/weppcloud/static/js/controllers-gl.js` only if generated output is expected in this repo.

Run focused tests as they become relevant:

    wctl run-pytest tests/soils/test_ssurgo_request_errors.py --maxfail=1
    wctl run-pytest tests/nodb/test_soils_gridded_root_creation.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-npm test
    wctl run-npm lint

After implementation and targeted tests, run these pre-closure checks. If an external constraint prevents the full pytest suite, record explicit package-owner risk acceptance in `tracker.md`; otherwise the package is not closeable.

    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260619_ssurgo_project_sqlite_cache/package.md
    wctl doc-lint --path docs/work-packages/20260619_ssurgo_project_sqlite_cache/tracker.md
    wctl doc-lint --path wepppy/soils/README.md
    wctl doc-lint --path wepppy/soils/ssurgo/ssurgo.md

## Validation and Acceptance

Acceptance requires behavior, not just code structure. A passing implementation must prove these observations:

1. A new or legacy run directory without a project SSURGO cache can rebuild soils and produces `ssurgo_tabular_cache.sqlite` under `<wd>/soils/`.
2. A second rebuild reuses the project cache when the checkbox is not enabled.
3. A rebuild with `clear_ssurgo_cache_on_rebuild` enabled deletes only the project cache and SQLite sidecars `<cache_path>-wal` and `<cache_path>-shm` before rebuilding.
4. Direct `SurgoSoilCollection(mukeys)` usage defaults to in-memory SQLite and does not write a shared `/dev/shm` cache.
5. The soil panel renders `Clear SSURGO cache on rebuild` using `ui.checkbox_field`.
6. The RQ engine route persists the checkbox option to `Soils` before enqueueing `build_soils_rq`.
7. The RQ engine route also persists the checkbox option in batch mode before returning without enqueueing.
8. Durable SSURGO docs describe project-local rebuild caches and direct in-memory defaults.
9. All five current `Soils` constructor sites pass project-local cache paths, and direct non-`Soils` callers are updated or dispositioned.
10. Both subagent review artifacts exist and each finding is dispositioned.
11. `artifacts/security_review.md` exists and has no unresolved medium/high findings.

The new tests should fail before the implementation for the exact stale-cache and missing-serialization behaviors, and pass after the implementation.

## Idempotence and Recovery

The migration is additive. Old projects do not need a one-time migration; loading `Soils` should synthesize missing new fields, and the next rebuild should create the project cache. Cache clearing must be repeatable: if the cache file is absent, clearing should succeed without deleting unrelated files. If a rebuild fails after clearing, rerunning `build_soils` should recreate the cache through the normal fetch path.

Avoid destructive recovery commands. Do not delete a run's entire `soils` directory. Do not reset the git tree. If generated frontend assets change unexpectedly, inspect the source and generated diff before deciding whether to keep them.

## Artifacts and Notes

Required artifacts:

- `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/code_review_findings.md`
- `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/qa_review_findings.md`
- `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/security_review.md`

Use `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/subagent_review_disposition_template.md` for review artifact structure.

## Interfaces and Dependencies

The final implementation should expose these interfaces or equivalent names with the same responsibilities:

In `wepppy/soils/ssurgo/ssurgo.py`, `SurgoSoilCollection.__init__` should accept an optional explicit SQLite cache path. A direct caller that omits the path gets an in-memory cache. A project caller that supplies the path gets a file-backed cache that persists between rebuilds.

In `wepppy/nodb/core/soils.py`, `Soils` should expose `clear_ssurgo_cache_on_rebuild` as a persisted boolean property. It should expose or internally use a helper that derives the project SSURGO cache path under the current `self.soils_dir`, and a helper that clears only that cache plus exact sidecars `<cache_path>-wal` and `<cache_path>-shm`.

In `wepppy/microservices/rq_engine/soils_routes.py`, `build_soils` should parse the new boolean field and write it to `Soils` before queue enqueue.

In `wepppy/weppcloud/templates/controls/soil_pure.htm`, the new checkbox field id and name should match the route's boolean field name.

## Revision Notes

- 2026-06-19 19:04 UTC / Codex: Initial ExecPlan created from user request and source inspection.
- 2026-06-19 19:16 UTC / Codex: Patched scoping-review findings into the plan: mandatory security artifact, derived cache paths, exact SQLite sidecars, batch route coverage, and durable docs.
- 2026-06-19 19:24 UTC / Codex: Patched QA scoping-review findings into the plan: full-suite gate wording, all constructor sites, fixed cache filenames, STATSGO strategy, and non-`Soils` direct caller audit.
