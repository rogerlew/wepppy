# Phase 9C Mutation Orchestration Contract Transition ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Phase 6 established root mutation ownership boundaries, but archive-form mutation orchestration still used thaw/freeze mechanics. Phase 9C transitions that orchestration contract to projection mutation sessions (`mode=mutate`) so archive-form mutations run through explicit session lifecycle (`acquire -> callback -> commit/abort -> release`) without introducing unmanaged persistent `WD/<root>/` state.

Visible proof is that existing mutation-owner routes/jobs continue to mutate the same roots, canonical NoDir error semantics remain intact, and Phase 9C validation gates pass.

## Progress

- [x] (2026-02-18 00:00Z) Read required startup sources in specified order (AGENTS, ExecPlan template, implementation plan Phase 9C/9E, active 9A/9B plans, contracts, runtime modules, and target tests).
- [x] (2026-02-18 00:00Z) Authored Phase 9C active ExecPlan at `docs/work-packages/20260214_nodir_archives/prompts/active/phase9c_mutation_orchestration_contract_transition.md`.
- [x] (2026-02-18 00:00Z) Implemented `wepppy/nodir/mutations.py` archive-form transition to projection mutation sessions using `mode="mutate"` acquire/commit/abort/release lifecycle while preserving maintenance lock ordering and dir-form default freeze behavior.
- [x] (2026-02-18 00:00Z) Updated `tests/nodir/test_mutations.py` for projection-session mutation semantics and patched projection/maintenance Redis lock stubs for deterministic unit coverage.
- [x] (2026-02-18 00:01Z) Ran required Phase 9C validation gates; all commands exited `0`.
- [x] (2026-02-18 00:01Z) Updated `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md` with Phase 9C completion status and evidence.

## Surprises & Discoveries

- Observation: Active Phase 9C ExecPlan file did not yet exist in `prompts/active/`.
  Evidence: initial file read returned `No such file or directory`.

- Observation: Mutation tests needed projection lock-client patching in addition to thaw/freeze lock-client patching once orchestration moved to projection sessions.
  Evidence: `acquire_root_projection(...)` consumes `wepppy.nodir.projections.redis_lock_client`; tests now patch both modules with the same Redis stub.

## Decision Log

- Decision: Keep Phase 9C scoped to orchestrator transition in `wepppy/nodir/mutations.py` and test/doc updates only.
  Rationale: The implementation plan explicitly defers broad WEPP/RQ consumer migration to Phase 9D.
  Date/Author: 2026-02-18 / Codex.

- Decision: Preserve maintenance lock acquisition and sorted lock ordering in `mutate_roots(...)` while transitioning only archive-form execution from thaw/freeze to projection sessions.
  Rationale: Meets Phase 9C contract transition cut line without changing Phase 6 root mutation ownership behavior.
  Date/Author: 2026-02-18 / Codex.

- Decision: On callback failure, explicitly abort active projection sessions and always release sessions, while preserving the original callback exception.
  Rationale: Enforces explicit no-commit failure semantics and prevents leaked managed `WD/<root>` projection state.
  Date/Author: 2026-02-18 / Codex.

## Outcomes & Retrospective

Phase 9C completed for the requested cut line.

Delivered behavior:
- Archive-form root mutations in `mutate_roots(...)` now run through projection mutation sessions (`acquire mode=mutate -> callback -> commit on success -> abort on callback failure -> release`).
- Existing maintenance-lock ordering and root-owner call sites remain unchanged.
- Directory-form post-callback default-archive freezing behavior remains unchanged.
- Callback-failure behavior for archive-form mutation no longer leaves thawed directory state behind.

Validation outcome:
- `wctl run-pytest tests/nodir/test_mutations.py tests/nodir/test_projections.py` -> `25 passed`
- `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py tests/microservices/test_rq_engine_soils_routes.py tests/microservices/test_rq_engine_landuse_routes.py tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py` -> `32 passed`
- `wctl run-pytest tests/rq/test_bootstrap_autocommit_rq.py tests/rq/test_wepp_rq_nodir.py` -> `15 passed`
- `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` -> `42 files validated, 0 errors, 0 warnings`

## Context and Orientation

Relevant files:
- Runtime orchestrator: `wepppy/nodir/mutations.py`
- Projection lifecycle API: `wepppy/nodir/projections.py`
- Existing maintenance primitives: `wepppy/nodir/thaw_freeze.py`
- Mutation owners to remain unchanged: `wepppy/rq/project_rq.py`
- Route wrappers touched by contract language/hooks: `wepppy/microservices/rq_engine/*_routes.py`
- Regression suites: `tests/nodir/test_mutations.py`, `tests/nodir/test_projections.py`

Contract constraints:
- Archive-form mutation path should use projection mutation sessions and explicit commit/abort.
- Keep Phase 6 mutation ownership map unchanged.
- Preserve canonical error semantics (`409/500/503/413`) and response payload contract.
- Avoid introducing persistent unmanaged `WD/<root>/` state.

## Plan of Work

Edit `wepppy/nodir/mutations.py` so archive-form roots no longer call thaw/freeze wrappers for mutation lifecycle. Instead, while holding maintenance locks in sorted order, acquire `mode="mutate"` projection sessions for archive roots, run the callback, commit sessions on success, abort sessions on callback failure, and always release sessions.

Keep directory-form handling and default-archive marker behavior intact: if configured defaults require archiving a directory-form root post-callback, continue using locked freeze for that dir-form conversion path.

Update `tests/nodir/test_mutations.py` to reflect projection-session semantics (especially failure behavior) and ensure projection lock stubs are patched so tests remain deterministic. Keep ownership call sites in `project_rq.py` and route modules unchanged unless wording/hook changes are strictly required.

## Concrete Steps

Run from `/workdir/wepppy`:

1. Implement orchestrator transition and tests.
2. Run required validation gates:
   - `wctl run-pytest tests/nodir/test_mutations.py tests/nodir/test_projections.py`
   - `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py tests/microservices/test_rq_engine_soils_routes.py tests/microservices/test_rq_engine_landuse_routes.py tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py`
   - `wctl run-pytest tests/rq/test_bootstrap_autocommit_rq.py tests/rq/test_wepp_rq_nodir.py`
   - `wctl doc-lint --path docs/work-packages/20260214_nodir_archives`

Observed results:
- `wctl run-pytest tests/nodir/test_mutations.py tests/nodir/test_projections.py` -> `25 passed, 2 warnings`
- `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py tests/microservices/test_rq_engine_soils_routes.py tests/microservices/test_rq_engine_landuse_routes.py tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py` -> `32 passed, 3 warnings`
- `wctl run-pytest tests/rq/test_bootstrap_autocommit_rq.py tests/rq/test_wepp_rq_nodir.py` -> `15 passed, 2 warnings`
- `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` -> `42 files validated, 0 errors, 0 warnings`

## Validation and Acceptance

Phase 9C is accepted when:
- `mutate_root`/`mutate_roots` archive-form mutation lifecycle is projection-session based.
- Mutation-owner map in `project_rq.py` remains unchanged.
- Canonical NoDir status/code behavior remains unchanged.
- Required Phase 9C validation commands pass.
- ExecPlan and implementation plan include completion evidence.

Acceptance status: complete.

## Idempotence and Recovery

Changes are additive and safe to rerun. Projection sessions are explicitly aborted on mutation callback failure and always released, which prevents leaked mount/session artifacts. Default directory-form freeze behavior remains as existing recovery-compatible behavior for configured new-run defaults.

## Artifacts and Notes

Primary evidence is captured in this ExecPlan and `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md` Phase 9C section.

## Interfaces and Dependencies

Interfaces consumed:
- `acquire_root_projection(...)`
- `commit_mutation_projection(...)`
- `abort_mutation_projection(...)`
- `release_root_projection(...)`

Locking dependencies:
- `maintenance_lock(...)` and sorted root lock acquisition in `mutate_roots(...)`.

Contract dependencies:
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`
- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/schemas/rq-response-contract.md`

---
Revision Note (2026-02-18, Codex): Initial Phase 9C ExecPlan authored after required startup reads.
Revision Note (2026-02-18, Codex): Completed Phase 9C orchestrator transition, validation gates, and implementation-plan evidence updates.
