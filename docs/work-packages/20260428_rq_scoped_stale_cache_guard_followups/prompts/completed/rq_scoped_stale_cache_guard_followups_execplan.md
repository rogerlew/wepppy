# RQ Scoped Stale NoDb Cache Guard Follow-Ups

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, RQ worker jobs with the same hydrate-then-mutate shape as the fixed `build_soils_rq` path should clear the relevant NoDb cache entry before hydrating mutable controller state. This reduces the chance that a stale Redis-cached `.nodb` payload carries an old file signature into a write and triggers `NoDbStaleWriteError`.

The behavior is observable through targeted tests that assert each guarded RQ path calls `clear_nodb_file_cache(runid, pup_relpath="<controller>.nodb")` after any root/archive precondition checks and before controller hydration/build.

This plan executes as contract conformance against `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`.

## Progress

- [x] (2026-04-28 16:01 UTC) Scanned `wepppy/rq/*` for adjacent `_rq` hydrate-then-mutate candidates.
- [x] (2026-04-28 16:01 UTC) Created follow-up package docs and candidate matrix.
- [x] (2026-04-28 16:22 UTC) Codified canonical contract in `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md` and corrected candidate matrix from independent review.
- [x] (2026-04-28 16:32 UTC) Synced `PROJECT_TRACKER.md` scope to the audited matrix and clarified standard wording for multi-controller scope semantics.
- [x] (2026-04-28 16:42 UTC) Implemented Priority 0 guards in `wepppy/rq/project_rq.py`.
- [x] (2026-04-28 16:42 UTC) Added targeted regression coverage for Priority 0 guard ordering and exact scopes.
- [x] (2026-04-28 16:42 UTC) Audited and implemented simple Priority 1 `project_rq.py` mod call sites.
- [x] (2026-04-28 16:42 UTC) Audited Priority 2 orchestration paths and recorded split/defer disposition.
- [x] (2026-04-28 16:42 UTC) Ran scoped validation and captured evidence in package docs.

## Surprises & Discoveries

- Observation: The scan found many `getInstance(...)` calls in RQ code, but only a subset are true mutation paths.
  Evidence: `wepppy/rq/wepp_rq_stage_post.py` contains several post-processing jobs that hydrate `Wepp` or `Climate` to read paths/settings, while `wepppy/rq/project_rq.py` contains direct build/update jobs that call mutating controller methods.

- Observation: The existing `modify_landuse_mapping_rq` and `build_soils_rq` guard placements provide the local pattern for preserving root rejection before cache clearing.
  Evidence: both guards call `clear_nodb_file_cache(..., pup_relpath=...)` immediately before mutable controller hydration inside a mutation callback.

- Observation: Initial candidate matrix included a few false positives and scope mistakes.
  Evidence: independent reviewer audit flagged `set_run_readonly_rq` and `run_rhem_rq` as non-qualifying under the contract, corrected `build_treatments_rq` scope to `landuse.nodb` + `soils.nodb`, and added missing `init_sbs_map_rq`/SWAT call sites.

- Observation: The standard needed explicit wording that multi-controller guards are multiple per-file calls, not one multi-value `pup_relpath`.
  Evidence: updated scope rule now names two explicit `clear_nodb_file_cache` calls for `landuse.nodb` and `soils.nodb`.

- Observation: Priority 1 `project_rq.py` mod paths were small enough to include without touching additional RQ modules.
  Evidence: `build_rangeland_cover_rq`, `build_treatments_rq`, `run_ash_rq`, `run_debris_flow_rq`, RAP TS, OpenET TS, POLARIS, and RUSLE all had direct mutable controller boundaries and were covered in `tests/rq/test_project_rq_mutation_guards.py`.

- Observation: Priority 2 candidates need module-specific packages rather than one broad mixed-module edit.
  Evidence: WEPP, SWAT, Omni, PATH CE, Roads, Geneva, and fork-undisturbify paths each combine mutable NoDb state with queue orchestration, single-flight locks, clone/deletion semantics, autocommit, or new-runid cache keys.

## Decision Log

- Decision: Prioritize direct top-level project-prep mutation paths before broad module-family orchestration paths.
  Rationale: These paths have the closest shape to the confirmed incident and can be tested with the existing mutation-guard test harness.
  Date/Author: 2026-04-28 / Codex

- Decision: Do not guard every RQ `getInstance(...)` call mechanically.
  Rationale: Read-only hydration paths do not benefit from cache clearing and broad cache churn can disrupt unrelated in-flight workers.
  Date/Author: 2026-04-28 / Codex

- Decision: Treat this package as contract conformance, not hardening.
  Rationale: user direction established scoped stale-cache guards as canonical write-path behavior under explicit qualifying conditions.
  Date/Author: 2026-04-28 / Codex

- Decision: Implement Priority 1 only where existing `project_rq.py` tests can prove the contract, and split/defer Priority 2 module families.
  Rationale: The package objective is conformance for confirmed stale-cache shapes without changing unrelated queue topology or module-specific orchestration contracts.
  Date/Author: 2026-04-28 / Codex

## Outcomes & Retrospective

Completed on 2026-04-28. `wepppy/rq/project_rq.py` now clears exact scoped NoDb cache entries before mutable hydration for all Priority 0 paths and the simple Priority 1 mod paths. `tests/rq/test_project_rq_mutation_guards.py` covers exact scope values, archive/root rejection before cache clear, cache clear before hydration, and representative status/timestamp/enqueue preservation.

Priority 2 module families were split/deferred with rationale in `package.md`: WEPP, SWAT, Omni, PATH CE, Roads, Geneva, and fork-undisturbify require dedicated fixtures for orchestration, single-flight locks, clone/deletion behavior, or new-runid cache keys. Validation evidence: `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` passed with `44 passed, 15 warnings`; package docs lint and `git diff --check` passed at closure.

## Context and Orientation

`clear_nodb_file_cache(runid, pup_relpath=...)` lives in `wepppy/nodb/base.py` and clears Redis cache entries for a run-scoped `.nodb` file or subtree. The completed package `docs/work-packages/20260428_build_soils_rq_stale_cache_guard/package.md` added a scoped guard to `wepppy/rq/project_rq.py::build_soils_rq`. The pattern is to clear the one target `.nodb` cache entry immediately before mutable hydration, not as a broad run-wide cache clear.

The governing contract for qualifying conditions, placement, exclusions, and validation is `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`.

The key production risk is stale write rejection. A NoDb controller loaded from stale Redis cache can retain an old file signature; if the task later writes to disk after the real `.nodb` file changed, the NoDb stale-write guard rejects the write. Clearing the scoped cache before hydration forces the worker to load current on-disk state for that controller.

## Plan of Work

Start with Priority 0 in `wepppy/rq/project_rq.py`. For each function listed in `package.md`, insert a scoped cache clear before the mutable controller hydration. Where the function already uses `_run_with_directory_root_lock(...)` or `_run_with_directory_roots_lock(...)`, put the cache clear inside the callback after root checks and before `Controller.getInstance(...)`. Where no directory-root lock exists, place the cache clear immediately before the mutating `getInstance(...)` call and add tests proving status/timestamp behavior is unchanged.

Then update `tests/rq/test_project_rq_mutation_guards.py` with focused tests. Reuse the existing `_stub_rq_context(...)` helper for archive-root paths. Tests should assert exact call order for representative grouped paths rather than duplicating every possible branch when a shared pattern is proven.

Next audit Priority 1 mod call sites. If method-level inspection confirms the call mutates the listed `.nodb`, add the guard and targeted tests. If a path needs separate fixtures or broader module behavior validation, record a split/defer disposition in `tracker.md` and package closure notes.

Finally audit Priority 2 orchestration paths. Do not implement speculative changes in large orchestration modules without a clear mutation boundary and test plan.

## Concrete Steps

Run from `/workdir/wepppy`:

1. Edit `wepppy/rq/project_rq.py`:
   - add scoped guards for Priority 0 call sites from `package.md`.
   - keep root/archive checks before cache clear where lock helpers are used.

2. Edit `tests/rq/test_project_rq_mutation_guards.py`:
   - add exact-scope assertions for `ron.nodb`, `watershed.nodb`, `landuse.nodb`, and `climate.nodb` groups.
   - add archive-root negative assertions for root-locked paths where missing.

3. Audit Priority 1 and Priority 2:
   - inspect the called controller methods for `with self.locked()`, `@nodb_setter`, or other persistence behavior.
   - implement confirmed simple guards or record explicit split/defer decisions.

4. Run validation:
   - `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` passed with `44 passed, 15 warnings`.
   - Additional non-`project_rq.py` pytest suites were not required because no non-`project_rq.py` implementation files were touched.
   - `wctl doc-lint --path docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups --path PROJECT_TRACKER.md` passed.
   - `git diff --check` passed.

5. Update lifecycle docs:
   - keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.
   - update `tracker.md`, `package.md`, and `PROJECT_TRACKER.md` at closure.
   - move this ExecPlan to `prompts/completed/` when the package closes.

## Validation and Acceptance

Acceptance requires all of the following:
- Priority 0 RQ mutation paths clear their exact scoped NoDb cache entries before mutable hydration.
- Existing archive-root rejection, lock-root, status, timestamp, and enqueue behavior remains unchanged.
- Priority 1/2 candidates have implementation or written disposition.
- Targeted pytest and docs lint pass.

## Idempotence and Recovery

The changes should be additive and safe to iterate. If a guard breaks a path because the function does not have a normal runid-backed working directory, do not add a fallback wrapper; record the path as deferred or not applicable with the reason. If validation fails, keep package docs current with the failure and adjust the scoped guard or tests until the existing contract is preserved.

## Artifacts and Notes

At closure, record:
- guard matrix with implemented/deferred status,
- pytest pass summaries,
- docs lint summary,
- `git diff --check` summary,
- any split packages created for Priority 2 module families.

Closure artifacts were recorded in `package.md` and `tracker.md`. No split packages were created during this package; Priority 2 module-family follow-ups remain backlog work.

## Revision Notes

- 2026-04-28: Initial ExecPlan authored from follow-up `_rq` call-site scan.
- 2026-04-28: Wording tightened to remove matrix/tracker drift and make multi-controller guard semantics explicit.
- 2026-04-28: Closed implementation, validation, Priority 2 disposition, and archival notes.
