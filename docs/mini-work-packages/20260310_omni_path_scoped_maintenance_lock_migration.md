# Mini Work Package: Omni Path-Scoped Runtime-Path Lock Migration
Status: Completed
Last Updated: 2026-03-10
Primary Areas: `wepppy/runtime_paths/thaw_freeze.py`, `wepppy/runtime_paths/mutations.py`, `wepppy/nodb/mods/omni/omni_mode_build_services.py`, `tests/runtime_paths/test_mutations_thaw_freeze_contract.py`, `tests/nodb/mods/test_omni_mode_build_services.py`, `tests/rq/test_omni_rq.py`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Omni sibling scenarios under `_pups/omni/scenarios/*` are copied workspaces, but runtime-path maintenance locks are currently keyed at parent-run scope. This causes artificial contention and 503 `NODIR_LOCKED` failures when many sibling scenarios run concurrently.

After this migration, lock scope will be derived from the effective root path (for example, the actual `landuse` or `soils` directory path), so sibling scenarios only contend when they truly share the same physical root. This gives lock behavior that scales with arbitrary numbers of sibling scenarios.

## Progress

- [x] (2026-03-10 07:05Z) Captured failure mechanics and lock-key root cause from production trace (`NODIR_LOCKED` owned by sibling worker during concurrent stage-2 mulch runs).
- [x] (2026-03-10 07:18Z) Drafted migration strategy and durability constraints for option 1 (path-scoped locking).
- [x] (2026-03-10 07:22Z) Authored this mini work-package with phased implementation plan and concrete regression test case.
- [x] (2026-03-10 07:10Z) Implemented phase 1 lock-key API additions in `wepppy/runtime_paths/thaw_freeze.py`:
  added scope-aware lock identity (`legacy_runid`, `effective_root_path`, `effective_root_path_compat`), path-scope key generation, and compatibility checks against legacy lock presence.
- [x] (2026-03-10 07:10Z) Implemented phase 2 Omni caller adoption in `wepppy/nodb/mods/omni/omni_mode_build_services.py`:
  Omni lock wrappers now compute and pass effective-path scope tokens for `landuse`/`soils`.
- [x] (2026-03-10 07:26Z) Landed milestone 3 regression coverage:
  - `LOCK_SCOPE_OMNI_SIBLING_ISOLATION`
  - `test_maintenance_lock_path_scope_allows_distinct_sibling_roots_and_blocks_shared_root`
  - Omni lock-wrapper assertions for scope token propagation.
- [x] (2026-03-10 07:26Z) Ran required validation command set successfully:
  - `wctl run-pytest tests/runtime_paths/test_mutations_thaw_freeze_contract.py --maxfail=1`
  - `wctl run-pytest tests/nodb/mods/test_omni_mode_build_services.py --maxfail=1`
  - `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1`
  - `wctl run-pytest tests --maxfail=1`
  - `wctl doc-lint --path docs/mini-work-packages/20260310_omni_path_scoped_maintenance_lock_migration.md`

## Surprises & Discoveries

- Observation: The lock key currently normalizes `_pups` paths to the parent runid, forcing sibling contention.
  Evidence: `maintenance_lock_key()` and `_runid_from_wd()` in `wepppy/runtime_paths/thaw_freeze.py`.

- Observation: Omni clones copy `landuse` and `soils` directories into each sibling scenario workspace, so most sibling scenarios do not physically share mutable roots.
  Evidence: clone logic in `wepppy/nodb/mods/omni/omni_clone_contrast_service.py` and `wepppy/nodb/mods/omni/omni.py`.

- Observation: Current contention timeout is fixed at 300 seconds in Omni mode build services, which turns artificial contention into hard job failures.
  Evidence: `_OMNI_LOCK_WAIT_SECONDS = 300.0` in `wepppy/nodb/mods/omni/omni_mode_build_services.py`.

- Observation: Compatibility mode can safely block when a legacy lock is already present without reintroducing sibling serialization for path-scoped callers.
  Evidence: `effective_root_path_compat` path in `acquire_maintenance_lock(...)` checks both path-scoped and legacy lock files before entering.

- Observation: End-to-end regression risk remained low after migration because default lock scope stayed legacy for unchanged callers, while Omni explicitly opted in.
  Evidence: `wctl run-pytest tests --maxfail=1` completed with `2286 passed, 34 skipped`.

## Decision Log

- Decision: Use effective-root-path lock scoping rather than stage serialization.
  Rationale: It preserves concurrency while restoring correct isolation semantics for copied sibling workspaces.
  Date/Author: 2026-03-10 / Codex

- Decision: Keep contention semantics for truly shared roots (for example, symlinked to same target).
  Rationale: This preserves safety when two workspaces mutate the same physical directory.
  Date/Author: 2026-03-10 / Codex

- Decision: Introduce migration compatibility mode before fully removing legacy runid-only behavior.
  Rationale: Prevents split-brain lock behavior during staggered deploys or mixed-worker windows.
  Date/Author: 2026-03-10 / Codex

- Decision: Set Omni lock wrappers to `effective_root_path_compat` (not legacy default).
  Rationale: This enables sibling isolation for copied workspaces while still honoring active legacy locks during migration windows.
  Date/Author: 2026-03-10 / Codex

## Outcomes & Retrospective

Completed outcomes:
- Runtime-path maintenance locks now support path-scoped identity via `effective_root_path` and `effective_root_path_compat`, while preserving legacy default behavior for unchanged callers.
- Omni mutation lock wrappers now pass path-scoped tokens for `landuse` and `soils`, so copied sibling scenarios can run concurrently unless they truly share the same effective root.
- Regression coverage now enforces both halves of the contract (distinct sibling roots do not contend; shared physical roots do contend with `NODIR_LOCKED`).
- Full repository regression sweep passed after the migration (`2286 passed, 34 skipped`), indicating no detected behavior regressions in unaffected subsystems.

Retrospective / follow-up:
- Production throughput and failure-rate deltas for high-cardinality sibling runs are not measured in this unit-test package and should be captured from staging or live telemetry.
- Compatibility mode currently checks legacy lock presence from path-scoped callers; mixed-worker windows should still be monitored during rollout for any residual edge races.

## Context and Orientation

Current lock files are created under `/tmp/wepppy-runtime-path-locks` using a filename derived from `(runid, root)`. For `_pups` scenarios, `runid` is coerced to the parent runid, so all siblings compete for the same `landuse`/`soils` lock slots.

Omni stage-2 scenarios (for example mulch variants) are enqueued concurrently from `run_omni_scenarios_rq`, and each scenario calls `apply_scenario_mode`, which wraps `landuse`/`soils` mutation steps in runtime-path maintenance locks. That interaction currently turns benign sibling parallelism into lock starvation/failure when one sibling holds lock longer than 300 seconds.

## Plan of Work

### Milestone 1: Introduce path-scoped lock identity with compatibility support

Add an explicit lock-scope abstraction in `wepppy/runtime_paths/thaw_freeze.py`:
- A helper that derives canonical scope identity from effective root path (`realpath` + normalized root context).
- Lock key/lock filename generation that can use this scope identity.
- Compatibility mode that can check legacy and path-scoped lock presence to avoid mixed-version split-brain.

Deliverable:
- New API surface that allows callers to request lock scope by effective path.
- Legacy behavior preserved for unchanged callers.

### Milestone 2: Adopt path-scoped locking in Omni mutation paths

Update `wepppy/nodb/mods/omni/omni_mode_build_services.py` lock entry points to compute and pass path scope for `landuse` and `soils`.

Deliverable:
- Sibling scenarios with distinct copied roots acquire independent locks.
- Scenarios that resolve to the same physical root still contend.

### Milestone 3: Strengthen lock contract tests and Omni regression tests

Add/adjust tests so the lock contract explicitly covers both cases:
- Distinct scenario roots do not contend.
- Shared effective roots do contend.

Deliverable:
- Test coverage that prevents regressions if scenario cardinality grows by an order of magnitude.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Runtime-path lock API and scope migration edits:
   - Edit `wepppy/runtime_paths/thaw_freeze.py`.
   - If shared helpers are needed, edit `wepppy/runtime_paths/mutations.py`.

2. Omni caller adoption:
   - Edit `wepppy/nodb/mods/omni/omni_mode_build_services.py` to pass scope identity when locking `landuse`/`soils`.

3. Tests:
   - Edit `tests/runtime_paths/test_mutations_thaw_freeze_contract.py`.
   - Edit `tests/nodb/mods/test_omni_mode_build_services.py`.
   - Add/adjust queue-level regression in `tests/rq/test_omni_rq.py` only if behavior assertions need update for lock contention handling.

4. Validation commands:
   - `wctl run-pytest tests/runtime_paths/test_mutations_thaw_freeze_contract.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/test_omni_mode_build_services.py --maxfail=1`
   - `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1`
   - `wctl run-pytest tests --maxfail=1`

5. Documentation lint:
   - `wctl doc-lint --path docs/mini-work-packages/20260310_omni_path_scoped_maintenance_lock_migration.md`

## Validation and Acceptance

Acceptance criteria:

1. Path isolation:
   - Two sibling scenario workspaces with different copied `landuse`/`soils` roots can enter lock-protected mutation blocks concurrently without `NODIR_LOCKED`.

2. Shared-root protection:
   - Two workspaces that resolve to the same effective `landuse` (or `soils`) root cannot concurrently acquire the same root lock.

3. Backward safety:
   - Existing non-Omni lock users continue to behave correctly under default behavior.

4. Omni behavior:
   - Concurrent stage-2 sibling scenario execution no longer fails due solely to parent-scoped runtime-path lock collisions.

## Idempotence and Recovery

- The migration is additive first: introduce new scope computation and compatibility behavior before switching callers.
- If regressions appear, rollback by reverting Omni caller to legacy lock scope while retaining new helpers behind non-default path.
- No schema/data migration is required; lock files are ephemeral and TTL-bounded.

## Concrete Test Case

Test Case ID: `LOCK_SCOPE_OMNI_SIBLING_ISOLATION`

Target file:
- `tests/runtime_paths/test_mutations_thaw_freeze_contract.py`

Name:
- `test_maintenance_lock_path_scope_allows_distinct_sibling_roots_and_blocks_shared_root`

Setup:
- Create `base_wd=/tmp/.../wc1/runs/ab/base-run`.
- Create sibling directories:
  - `s1=/tmp/.../wc1/runs/ab/base-run/_pups/omni/scenarios/s1`
  - `s2=/tmp/.../wc1/runs/ab/base-run/_pups/omni/scenarios/s2`
- Materialize `s1/landuse`, `s2/landuse` as real distinct directories.

Assertions:
1. Acquire `maintenance_lock(s1, "landuse", scope=effective_path)` and concurrently acquire `maintenance_lock(s2, "landuse", scope=effective_path)`; both succeed.
2. Replace `s2/landuse` with symlink to `s1/landuse` (shared physical root).
3. Acquire lock for `s1`; acquiring lock for `s2` now raises `NoDirError` with `code == "NODIR_LOCKED"`.

Why this is the durable guard:
- It encodes the scalability contract directly: lock cardinality tracks physical root cardinality, not number of sibling scenarios.

## Artifacts and Notes

Recorded artifacts:
- Before/after lock key samples for sibling scenarios (`s1`, `s2`):
  - Legacy key (`s1`): `nodb-lock:base-run:runtime-paths/landuse`
  - Legacy key (`s2`): `nodb-lock:base-run:runtime-paths/landuse`
  - Path-scoped key (`s1`): `nodb-lock:path-scope:268a84d41aab:runtime-paths/landuse`
  - Path-scoped key (`s2`): `nodb-lock:path-scope:9a860043d0b2:runtime-paths/landuse`
- Concurrency trace for distinct sibling roots:
  - `distinct-roots: acquired-both`
- Contention trace for intentionally shared root:
  - `shared-root: blocked NODIR_LOCKED`

## Interfaces and Dependencies

Expected interface changes:
- `maintenance_lock_key(...)` and `maintenance_lock(...)` gain a caller-controlled scope mode or scope token.
- Omni mutation lock calls pass effective-path scope explicitly.

No new external dependencies are expected.

## Revision Notes

- 2026-03-10 07:10Z (Codex): Updated status/progress, captured implementation decisions/discoveries, and recorded that phase 1/2 code plus regression tests are complete before running full validation.
- 2026-03-10 07:26Z (Codex): Marked plan complete, recorded validation results, and added concrete lock-key/trace artifacts from the implemented migration.
