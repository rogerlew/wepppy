# `build_soils_rq` Stale NoDb Cache Guard

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Completion Outcome

Closed on 2026-04-28. `build_soils_rq` now clears the scoped `soils.nodb` NoDb cache inside the existing soils directory-root lock callback and immediately before mutable soils hydration/build. Targeted regression coverage proves guard ordering, scoped cache key usage, unchanged archive-root rejection, and unchanged success-path status/timestamp behavior.

## Purpose / Big Picture

After this change, `build_soils_rq` should no longer fail from known stale NoDb cache payload reuse for `soils.nodb` in the confirmed incident path. The behavior change is observable when targeted regression tests pass and the guarded path explicitly clears scoped cache before hydrating/building soils.

## Progress

- [x] (2026-04-28 15:30 UTC) Created package scaffold and active ExecPlan.
- [x] (2026-04-28 15:30 UTC) Captured initiating production failure signature and bounded scope.
- [x] (2026-04-28 15:53 UTC) Implemented scoped stale-cache guard in `wepppy/rq/project_rq.py::build_soils_rq`.
- [x] (2026-04-28 15:53 UTC) Added targeted regression coverage in `tests/rq/test_project_rq_mutation_guards.py`.
- [x] (2026-04-28 15:58 UTC) Ran scoped validation (`pytest`, `doc-lint`, `git diff --check`) and captured results in tracker/package docs.
- [x] (2026-04-28 15:58 UTC) Archived ExecPlan to `prompts/completed/` at package closure with outcome notes.

## Surprises & Discoveries

- Observation: The failure path showed `NoDbStaleWriteError` in `build_soils_rq` with expected signature older than on-disk `soils.nodb`.
  Evidence: wepp1 incident context for `job_id=40ded984-4d89-44a2-a41e-f253d9dc1bd0` (`runid=northwestern-yes`), with `expected (mtime=1777348218.626585, size=754)` and `observed (mtime=1777348433.520623, size=807)`.

- Observation: `project_rq.py` already uses a cache-clear guard pattern in a nearby mutation path (`modify_landuse_mapping_rq`), which is a local precedent for this mitigation style.
  Evidence: inline comment and call to `clear_nodb_file_cache(runid, pup_relpath="landuse.nodb")` around `modify_landuse_mapping_rq`.

- Observation: The existing directory-root lock callback shape makes it possible to add the soils cache guard without changing the lock, status, or timestamp contract.
  Evidence: `tests/rq/test_project_rq_mutation_guards.py::test_build_soils_rq_clears_scoped_cache_before_hydration_and_build` passed and asserts root checks, cache clear, hydration, build, status messages, and `TaskEnum.build_soils` timestamp order.

## Decision Log

- Decision: Add a scoped cache-clear guard in `build_soils_rq` instead of expanding into a broad cache re-architecture package.
  Rationale: User requested a work package for adding the guard, and incident evidence is specific to one path.
  Date/Author: 2026-04-28 / Codex

- Decision: Keep this package focused on one code path + targeted tests + package docs.
  Rationale: Change-scope discipline and low blast radius for production hot path reliability.
  Date/Author: 2026-04-28 / Codex

- Decision: Place the guard inside the existing soils directory-root lock callback rather than before lock acquisition.
  Rationale: This keeps archive-backed soils roots rejected before cache clear or hydration, while still clearing the stale cache immediately before mutable `Soils` hydration/build.
  Date/Author: 2026-04-28 / Codex

## Outcomes & Retrospective

Closed. `build_soils_rq` now clears scoped `soils.nodb` cache before mutable soils hydration/build, and the targeted tests lock that behavior down without changing archive-root rejection or success-path status/timestamp ordering. The package lifecycle docs and `PROJECT_TRACKER.md` record validation evidence. No immediate follow-up package is recommended; broader cache-guard rollout should remain evidence-driven if another mutation path shows the same stale-cache signature.

## Context and Orientation

`wepppy/rq/project_rq.py` implements RQ tasks including `build_soils_rq`. `build_soils_rq` currently resolves the run working directory, publishes status, acquires the soils directory-root lock via `_run_with_directory_root_lock(...)`, and invokes `Soils.getInstance(wd).build()`. `clear_nodb_file_cache` is imported in the module and already used by other mutation flows to avoid stale cache signatures during write paths. Targeted route/mutation tests for this file live in `tests/rq/test_project_rq_mutation_guards.py`.

The goal is to ensure the soils build path clears stale Redis cache for `soils.nodb` before hydrating a mutable `Soils` instance that will later dump state under lock.

## Plan of Work

Edit `wepppy/rq/project_rq.py` in `build_soils_rq` to add a scoped `clear_nodb_file_cache(runid, pup_relpath="soils.nodb")` call before `Soils.getInstance(wd).build()` executes inside the locked callback path. Keep existing status messaging, lock-root checks, and timestamp behavior intact.

Then add regression coverage in `tests/rq/test_project_rq_mutation_guards.py` to assert:
- the guard is called for `build_soils_rq`,
- it is scoped to `soils.nodb`,
- and existing archive-root rejection behavior still holds.

Do not broaden this package into unrelated queue or cache architecture changes.

## Concrete Steps

Run from `/workdir/wepppy`:

1. Edit `wepppy/rq/project_rq.py`:
   - in `build_soils_rq`, insert scoped cache clear before soils hydration/build call.

2. Edit `tests/rq/test_project_rq_mutation_guards.py`:
   - add/update tests asserting the scoped guard call and preserved boundary behavior.

3. Run validation:
   - `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1`
   - `wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1`
   - `wctl doc-lint --path docs/work-packages/20260428_build_soils_rq_stale_cache_guard --path PROJECT_TRACKER.md`
   - `git diff --check`

4. Update package docs:
   - reflect test outputs and completion status in `tracker.md` and `package.md`,
   - move this ExecPlan to `prompts/completed/` with a closure outcome note.

## Validation and Acceptance

Acceptance requires all of the following:
- `build_soils_rq` contains the scoped stale-cache guard for `soils.nodb` before mutable soils hydration/build.
- Archive-root rejection contract for `build_soils_rq` remains unchanged.
- Targeted pytest commands pass for touched tests.
- Package docs are updated and lint-clean.

## Idempotence and Recovery

The edits are additive and safe to rerun. If validation fails:
- revert only the specific guard insertion or test assertions causing drift,
- keep package docs up to date with the failure reason,
- rerun scoped tests until behavior and contract alignment are restored.

## Artifacts and Notes

At closure, include concise evidence snippets in `tracker.md`:
- pytest pass summaries for scoped suites,
- doc-lint summary,
- `git diff --check` summary.

Final validation evidence:
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` passed with `26 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1` passed with `3 passed`.
- `wctl doc-lint --path docs/work-packages/20260428_build_soils_rq_stale_cache_guard --path PROJECT_TRACKER.md` passed with `5 files validated, 0 errors, 0 warnings`.
- `git diff --check` passed.

## Revision Notes

- 2026-04-28: Initial ExecPlan authored during package preparation.
- 2026-04-28: Updated with implementation outcome, guard placement decision, validation evidence, and closure notes before archival.
