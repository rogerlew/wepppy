# Phase 6 NoDir Root-by-Root Mutation Adoption ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is complete, all Phase 6 NoDir mutation paths will work for both directory form and archive form across all four allowlisted roots (`watershed`, `soils`, `landuse`, `climate`) without persisting root representation in `.nodb` payloads. A user will be able to run normal RQ build flows and related mutations on archived runs, and the system will enforce canonical NoDir lock/state/error behavior (`409 NODIR_MIXED_STATE`, `500 NODIR_INVALID_ARCHIVE`, `503 NODIR_LOCKED`) while keeping browse/files/download extraction-free.

The visible proof is that each Phase 6 root-specific RQ mutation row in `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md` behaves as `materialize(root)+freeze` in archive form, passes targeted tests, and passes post-merge canary probes.

## Progress

- [x] (2026-02-17 05:50Z) Initial Phase 6 ExecPlan authored in `docs/work-packages/20260214_nodir_archives/prompts/completed/phase6_root_by_root_mutation_adoption.md` and linked from `AGENTS.md`.
- [x] (2026-02-17 06:06Z) Milestone 0 complete: baseline contract verification and reproducible baseline captured (`44 passed`; `22 passed`; docs lint clean).
- [x] (2026-02-17 06:10Z) Milestone 1 complete: shared mutation orchestration implemented (`wepppy/nodir/mutations.py`) and covered by `tests/nodir/test_mutations.py` plus state/thaw/freeze regressions.
- [x] (2026-02-17 06:16Z) Milestone 2 complete: Watershed Phase 6a waves implemented (constructor blocker removed, watershed mutation owners wrapped, `_structure` hazard cleaned) and validated by watershed gate suite.
- [x] (2026-02-17 06:20Z) Milestone 3 complete: Soils Stage A-D artifacts authored and soils mutation route/RQ behavior validated.
- [x] (2026-02-17 06:23Z) Milestone 4 complete: Landuse Stage A-D artifacts authored and landuse mutation route/RQ behavior validated.
- [x] (2026-02-17 06:25Z) Milestone 5 complete: Climate Stage A-D artifacts authored and climate mutation route/RQ/upload behavior validated.
- [x] (2026-02-17 06:37Z) Milestone 6 complete: cross-root hardening and final conformance closed (`wctl run-pytest tests --maxfail=1` -> `1531 passed, 27 skipped`; docs lint clean).
- [x] (2026-02-17 06:39Z) Final completion: Phase 6 marked done in `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md` with evidence and all-roots review artifact.

## Surprises & Discoveries

- Observation: `tests/weppcloud/routes/test_landuse_bp.py` failed in isolation with Flask blueprint setup assertions because `authorize()` imported `wepppy.weppcloud.app` before its `TESTING` short-circuit.
  Evidence: `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py tests/weppcloud/routes/test_landuse_bp.py tests/nodb/test_landuse_catalog.py -vv` showed repeated `url_value_preprocessor` setup assertions before patching.

- Observation: Deferring `get_run_owners` import until after login-manager/testing checks in `wepppy/weppcloud/utils/helpers.py` resolved the landuse gate without changing authorization behavior for non-testing flows.
  Evidence: Post-fix rerun of the same landuse gate command returned `16 passed`.

- Observation: RQ mutation ownership moved to shared orchestration wrappers, but enqueue dependencies/edges did not change.
  Evidence: `git diff -- wepppy/rq/project_rq.py` shows wrapper boundaries around existing job bodies with no new/deleted enqueue chains.

- Observation: Adding soils/landuse/climate Stage A-D artifacts increased NoDir package docs validation coverage from 16 files to 30 files.
  Evidence: `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` -> `30 files validated, 0 errors, 0 warnings`.

## Decision Log

- Decision: Use one shared mutation orchestrator for all Phase 6 roots instead of root-specific orchestration implementations.
  Rationale: The lock/state/error contract is shared and normative in `docs/schemas/nodir-thaw-freeze-contract.md`; shared orchestration reduces drift.
  Date/Author: 2026-02-17 / Codex.

- Decision: Keep browse/files/download and other request-serving read surfaces thaw-free, and fail fast with canonical NoDir codes in mixed/invalid/transitional states.
  Rationale: Behavior matrix explicitly classifies these surfaces as `native`; mutation ownership belongs to RQ/controller boundaries, not request-serving reads.
  Date/Author: 2026-02-17 / Codex.

- Decision: Apply route-level `nodir_resolve(..., view="effective")` preflight for each root mutation HTTP surface before enqueue/write.
  Rationale: Enforces consistent `409`/`500`/`503` semantics at the public boundary and prevents non-canonical enqueue behavior for archive/mixed/transitional states.
  Date/Author: 2026-02-17 / Codex.

- Decision: Defer `get_run_owners` import inside `authorize()` until after login-manager/testing short-circuits.
  Rationale: Prevents blueprint re-registration assertions in isolated blueprint tests while preserving authorization behavior for real app flows.
  Date/Author: 2026-02-17 / Codex.

- Decision: Do not update `wepppy/rq/job-dependencies-catalog.md` in this phase.
  Rationale: Mutation wrappers changed lock/thaw/freeze boundaries only; enqueue graph/dependency edges were unchanged.
  Date/Author: 2026-02-17 / Codex.

## Outcomes & Retrospective

Phase 6 is complete and behavior-visible goals were met:
- Archive-form mutation rows for all required root families now execute through shared lock/thaw/freeze orchestration (`build-landuse`, `build-soils`, `build-climate`, watershed RQ group, and `upload-cli`).
- Root mutation routes now enforce canonical NoDir preflight semantics (`409 NODIR_MIXED_STATE`, `500 NODIR_INVALID_ARCHIVE`, `503 NODIR_LOCKED`) before enqueue or write.
- Watershed Phase 6a execution waves are complete, including the constructor mixed-state blocker removal and `_structure` serialized-path hazard cleanup.
- Soils, landuse, and climate Stage A-D artifacts were authored and checked in; final all-roots review artifact is present.

Validation closeout:
- Required milestone gate commands are green, including full regression gate `wctl run-pytest tests --maxfail=1` (`1531 passed, 27 skipped`).
- Docs gate is green: `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` (`30 files validated, 0 errors, 0 warnings`).

Lessons learned:
- Root mutation ownership needs to remain centralized; route-layer preflight + shared mutation wrappers provide predictable semantics without duplicating state logic.
- Isolated blueprint tests are sensitive to eager app imports; keeping imports lazy in auth utilities prevents avoidable setup-order regressions.

## Context and Orientation

Phase 0 through Phase 5 are already complete. Phase 6 is the remaining root-by-root mutation adoption phase.

A NoDir root is one of `landuse`, `soils`, `climate`, `watershed`. Directory form means `WD/<root>/` exists and `WD/<root>.nodir` does not. Archive form means `WD/<root>.nodir` exists and `WD/<root>/` does not. Mixed state means both exist and must fail with `409` on non-admin request-serving surfaces. Transitional states (`thawing`, `freezing`, or temp sentinels) must fail with `503` for request-serving and materialization surfaces.

Key normative documents:

- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/schemas/nodir_interface_spec.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/touchpoints_inventory.md`

Key current planning status:

- Watershed, soils, landuse, and climate Stage A-D artifacts are complete and committed.
- Phase 6 implementation and validation evidence is captured in `docs/work-packages/20260214_nodir_archives/artifacts/phase6_all_roots_review.md` and reflected in `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md`.

Primary implementation surfaces by root:

- Watershed: `wepppy/nodb/core/watershed.py`, `wepppy/topo/peridot/peridot_runner.py`, `wepppy/topo/watershed_abstraction/`, `wepppy/rq/project_rq.py`, `wepppy/microservices/rq_engine/watershed_routes.py`, `wepppy/export/*`, `wepppy/nodb/mods/*` watershed consumers.
- Soils: `wepppy/nodb/core/soils.py`, `wepppy/rq/project_rq.py` (`build_soils_rq`), `wepppy/microservices/rq_engine/soils_routes.py`, `wepppy/export/export.py`, `wepppy/nodb/mods/*` soils writers.
- Landuse: `wepppy/nodb/core/landuse.py`, `wepppy/rq/project_rq.py` (`build_landuse_rq`), `wepppy/microservices/rq_engine/landuse_routes.py`, `wepppy/nodb/mods/treatments/treatments.py`, `wepppy/nodb/mods/omni/omni.py`.
- Climate: `wepppy/nodb/core/climate.py`, `wepppy/rq/project_rq.py` (`build_climate_rq`, `upload_cli_rq`), `wepppy/microservices/rq_engine/climate_routes.py`, `wepppy/microservices/rq_engine/upload_climate_routes.py`, `wepppy/export/export.py`.

## Plan of Work

### Milestone 0: Baseline, Safety, and Contract Freeze

Establish a reproducible baseline before code changes. Confirm current behavior matrix rows and existing tests, and pin the exact commands that must remain green throughout Phase 6.

During this milestone, do not change runtime behavior. Only gather baseline evidence and update this plan's `Progress`, `Surprises & Discoveries`, and `Decision Log` if discrepancies appear.

### Milestone 1: Shared Root-Mutation Orchestrator

Implement a small shared orchestration boundary in NoDir maintenance code that wraps existing mutation callbacks with lock acquisition, state preflight, thaw decision, callback execution, freeze, and canonical error propagation. Keep existing mutation logic in place and only change call boundaries.

Implementation focus:

- Add orchestration helper under `wepppy/nodir/` (preferred alongside `thaw_freeze.py`).
- Ensure lock order remains NoDir maintenance lock outermost, then existing NoDb locks inside callbacks.
- For archive form root mutations, enforce `archived -> thawing -> thawed -> freezing -> archived`.
- For callback failure after thaw, preserve thawed dirty state and return explicit failure without implicit cleanup.

### Milestone 2: Watershed Implementation (Phase 6a Execution)

Use existing watershed Stage A-D artifacts as the direct implementation spec. Execute the four watershed waves in order, updating artifacts as implementation evidence changes.

Wave goals:

- Wave 1: remove known blockers (`Watershed.__init__` eager directory creation, migration coupling).
- Wave 2: enforce shared thaw/modify/freeze around watershed mutation entry points.
- Wave 3: fix watershed consumer coupling at FS-boundaries and mod/export integrations.
- Wave 4: complete serialized-path cleanup and browse/files/download consistency hardening.

### Milestone 3: Soils Stage A-D + Implementation

Author soils-specific Stage A-D planning artifacts in the same style as watershed, then implement soils waves.

Required new planning artifacts:

- `docs/work-packages/20260214_nodir_archives/artifacts/soils_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/soils_mutation_surface_stage_b.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/soils_execution_waves_stage_c.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/soils_validation_rollout_stage_d.md`

Then implement soils mutation and consumer paths, including mod touchpoints and WinWEPP export FS-boundary handling.

### Milestone 4: Landuse Stage A-D + Implementation

Author landuse-specific Stage A-D planning artifacts, then implement landuse waves.

Required new planning artifacts:

- `docs/work-packages/20260214_nodir_archives/artifacts/landuse_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/landuse_mutation_surface_stage_b.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/landuse_execution_waves_stage_c.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/landuse_validation_rollout_stage_d.md`

Prioritize treatments and omni write paths because they are high-risk serialized-path and copytree touchpoints.

### Milestone 5: Climate Stage A-D + Implementation

Author climate-specific Stage A-D planning artifacts, then implement climate waves.

Required new planning artifacts:

- `docs/work-packages/20260214_nodir_archives/artifacts/climate_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/climate_mutation_surface_stage_b.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/climate_execution_waves_stage_c.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/climate_validation_rollout_stage_d.md`

Prioritize upload CLI and report-generation paths because they frequently require real file paths and currently assume `cli_dir` always exists.

### Milestone 6: Cross-Root Hardening, Final Conformance, and Closeout

After all four roots are implemented, run full conformance against the behavior matrix and close Phase 6 in implementation docs.

Deliverables:

- Update `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md` Phase 6 and root sub-sections to complete.
- Add a final all-roots review artifact summarizing conformance, residual risk, and readiness.
- Ensure any changed RQ wiring updates `wepppy/rq/job-dependencies-catalog.md`.

## Concrete Steps

Run commands from repository root.

1. Baseline before code changes.

    cd /workdir/wepppy
    wctl run-pytest tests/nodir/test_state.py tests/nodir/test_thaw_freeze.py tests/nodir/test_resolve.py tests/nodir/test_materialize.py
    wctl run-pytest tests/microservices/test_browse_routes.py tests/microservices/test_browse_security.py tests/microservices/test_diff_nodir.py
    wctl doc-lint --path docs/work-packages/20260214_nodir_archives

Expected result: all commands exit 0.

2. Implement shared mutation orchestrator and its unit tests, then re-run baseline plus orchestrator tests.

    cd /workdir/wepppy
    wctl run-pytest tests/nodir -k "thaw or freeze or state"

Expected result: no regression in existing NoDir state machine behavior.

3. Execute Watershed implementation waves using existing Stage D gate commands.

    cd /workdir/wepppy
    wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py
    wctl run-pytest tests/topo/test_peridot_runner_wait.py tests/topo/test_topaz_vrt_read.py tests/test_wepp_top_translator.py
    wctl run-pytest tests/nodir/test_materialize.py tests/microservices/test_rq_engine_export_routes.py tests/nodb/mods/test_swat_interchange.py

Expected result: wave-targeted commands remain green as each wave closes.

4. For each remaining root (`soils`, `landuse`, `climate`), author Stage A-D docs, then implement root changes, then execute root-specific gates.

Soils minimum gates:

    cd /workdir/wepppy
    wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py tests/weppcloud/routes/test_soils_bp.py tests/soils/test_ssurgo.py

Landuse minimum gates:

    cd /workdir/wepppy
    wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py tests/weppcloud/routes/test_landuse_bp.py tests/nodb/test_landuse_catalog.py

Climate minimum gates:

    cd /workdir/wepppy
    wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_upload_climate_routes.py tests/weppcloud/routes/test_climate_bp.py tests/nodb/test_climate_catalog.py

Expected result: each root's mutation routes, controller consumers, and key boundary integrations pass in directory and archive scenarios.

5. Final conformance and closeout.

    cd /workdir/wepppy
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260214_nodir_archives

Expected result: full test and docs gates pass; Phase 6 docs can be marked complete.

## Validation and Acceptance

Acceptance is behavior-first.

- RQ mutation families for all roots must run successfully against archive form without manual extraction steps:
  - `build-landuse`, `build-soils`, `build-climate`, watershed RQ group, and upload-cli where applicable.
- Request-serving surfaces (`/browse`, `/files`, `/download`) must remain extraction-free and continue to return canonical NoDir errors for mixed/invalid/transitional states.
- FS-boundary read surfaces (`dtale`, `gdalinfo`, export paths) must materialize only required files and must fail explicitly on lock/limit/invalid conditions.
- No `.nodb` payload may persist root representation as authoritative state.
- Phase 6 documentation must show completed evidence, commands, and final readiness.

Evidence to collect while executing this plan:

- Passing output for each wave/root gate command.
- Updated root-specific Stage A-D artifacts for soils/landuse/climate.
- Updated `implementation_plan.md` with final Phase 6 completion status.

## Idempotence and Recovery

This plan is safe to run incrementally.

- Re-running planning stages is idempotent if artifacts are reconciled rather than duplicated.
- Re-running gate commands is safe and expected after each code change.
- If a wave introduces regressions, revert only that wave's commits and keep subsequent waves blocked.
- If a mutation fails after thaw, follow the thaw/freeze contract: preserve state, capture forensics, and recover with controlled maintenance lock operations instead of ad-hoc cleanup.

Rollback pattern:

    gh pr view <pr-number> --json mergeCommit
    git revert <merge_commit_sha>

After rollback, rerun that root's pre-merge and post-merge gates before continuing.

## Artifacts and Notes

Authoritative artifacts already present:

- `docs/work-packages/20260214_nodir_archives/artifacts/watershed_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/watershed_mutation_surface_stage_b.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/watershed_execution_waves_stage_c.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/watershed_validation_rollout_stage_d.md`

Phase 6 artifacts produced in this execution:

- `docs/work-packages/20260214_nodir_archives/artifacts/soils_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/soils_mutation_surface_stage_b.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/soils_execution_waves_stage_c.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/soils_validation_rollout_stage_d.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/landuse_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/landuse_mutation_surface_stage_b.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/landuse_execution_waves_stage_c.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/landuse_validation_rollout_stage_d.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/climate_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/climate_mutation_surface_stage_b.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/climate_execution_waves_stage_c.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/climate_validation_rollout_stage_d.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase6_all_roots_review.md`

When this plan changes, append a dated note at the bottom of this file with what changed and why.

## Interfaces and Dependencies

The implementation must preserve and/or introduce these interface boundaries.

Shared mutation orchestrator API (location in `wepppy/nodir/`):

    def mutate_root(
        wd: str | Path,
        root: str,
        callback: Callable[[], T],
        *,
        purpose: str = "nodir-mutation",
    ) -> T:
        ...

    def mutate_roots(
        wd: str | Path,
        roots: Iterable[str],
        callback: Callable[[], T],
        *,
        purpose: str = "nodir-mutation",
    ) -> T:
        ...

Behavior requirements:

- Preflight each root with `resolve(view="effective")` so mixed/invalid/transitional states fail with canonical NoDir errors before mutation work.
- Acquire NoDir maintenance locks in deterministic sorted root order (NoDir lock outermost, existing NoDb locks inside callbacks).
- Thaw archive-form roots before callback execution and freeze on successful callback completion.
- On callback failure after thaw, preserve thawed/dirty state (no implicit cleanup).

RQ mutation entry points that must call shared orchestration when they mutate root content:

- `wepppy/rq/project_rq.py`:
  - `build_channels_rq`, `build_subcatchments_rq`, `set_outlet_rq`, `abstract_watershed_rq`, `build_subcatchments_and_abstract_watershed_rq`
  - `build_landuse_rq`, `build_soils_rq`, `build_climate_rq`, `upload_cli_rq`

Route layers remain enqueue/validation boundaries, not thaw/freeze owners:

- `wepppy/microservices/rq_engine/watershed_routes.py`
- `wepppy/microservices/rq_engine/landuse_routes.py`
- `wepppy/microservices/rq_engine/soils_routes.py`
- `wepppy/microservices/rq_engine/climate_routes.py`
- `wepppy/microservices/rq_engine/upload_climate_routes.py`

Cross-repo/process dependencies that must stay aligned:

- NoDir contracts and behavior matrix docs under `docs/schemas/` and `docs/work-packages/20260214_nodir_archives/artifacts/`.
- RQ dependency catalog at `wepppy/rq/job-dependencies-catalog.md` whenever queue edges change.

---

Revision Note (2026-02-17, Codex): Initial ExecPlan created to drive full Phase 6 completion across watershed, soils, landuse, and climate using a shared orchestration boundary and per-root Stage A-D plus implementation waves.
Revision Note (2026-02-17, Codex): Updated living sections to final completion state, recorded milestone evidence and decisions from execution, synchronized interface signatures with implemented `mutate_root`/`mutate_roots` APIs, and documented the final Phase 6 artifacts and validation outcomes.
