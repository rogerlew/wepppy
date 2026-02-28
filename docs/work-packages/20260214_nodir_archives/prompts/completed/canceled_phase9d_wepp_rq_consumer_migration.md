# Phase 9D WEPP + RQ Consumer Migration ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Phase 9A-9C delivered projection lifecycle utilities, helper-level path support, and mutation-orchestrator contract transition. Phase 9D migrates WEPP read-heavy, path-dependent consumers and their RQ stage wrappers so archive-backed runs use projection sessions instead of default per-file materialization, while keeping read-only stages non-mutating and preserving canonical NoDir error semantics.

Visible proof is: targeted WEPP prep stages use projection-aware path acquisition, RQ stages wrap those reads in explicit acquire/release boundaries with exception-safe cleanup, and Phase 9D validation gates pass.

## Progress

- [x] (2026-02-18 00:00Z) Read required startup sources in the requested order through runtime modules and target tests.
- [x] (2026-02-18 00:00Z) Authored active Phase 9D ExecPlan at `docs/work-packages/20260214_nodir_archives/prompts/active/phase9d_wepp_rq_consumer_migration.md`.
- [x] (2026-02-18 00:00Z) Implemented WEPP consumer migration in `wepppy/nodb/core/wepp.py` for `_prep_slopes_peridot`, `_prep_multi_ofe`, `_prep_channel_slopes`, and `prep_and_run_flowpaths` using projection-aware input paths with fallback-only materialization where paths are required.
- [x] (2026-02-18 00:00Z) Added explicit stage-scoped projection acquire/release boundaries in `wepppy/rq/wepp_rq.py` for migrated WEPP read stages with exception-safe cleanup.
- [x] (2026-02-18 00:00Z) Extended regression tests for WEPP consumer path behavior and RQ stage lifecycle boundaries in `tests/nodb/test_wepp_nodir_read_paths.py` and `tests/rq/test_wepp_rq_nodir.py`.
- [x] (2026-02-18 00:00Z) Ran Phase 9D minimum validation gates and docs lint; all commands exited `0`.
- [x] (2026-02-18 00:00Z) Updated `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md` with Phase 9D completion evidence.
- [x] (2026-02-18 00:00Z) Addressed review finding by enforcing unmanaged mixed-state failure (`409 NODIR_MIXED_STATE`) in stage projection wrappers and added regression coverage in `tests/rq/test_wepp_rq_nodir.py`.
- [x] (2026-02-18 00:00Z) Closed low-severity observability test gap by adding projection-disabled fallback logging coverage in `tests/nodir/test_wepp_inputs.py`.
- [x] (2026-02-18 00:00Z) Refreshed Phase 9D handoff evidence with strict mixed-state + fallback-observability final rerun gates in implementation-plan docs.

## Surprises & Discoveries

- Observation: `wepppy/rq/wepp_rq.py` currently has no projection-session boundaries around WEPP read-only prep stages.
  Evidence: startup read of `_prep_multi_ofe_rq`, `_prep_slopes_rq`, `_run_flowpaths_rq`, `_prep_watershed_rq` shows direct `Wepp` calls only.

- Observation: projection mountpoints at `WD/<root>` can appear as mixed state to `resolve(..., view="effective")` call sites that are not mixed-tolerant.
  Evidence: `wepppy/nodir/fs.py` resolves `dir_exists + archive_present` as `NODIR_MIXED_STATE` in `view="effective"`; migrated consumers must use mixed-tolerant helper paths while projection sessions are active.

- Observation: `_prep_channel_slopes` must keep mixed-tolerant archive streaming behavior to preserve existing mixed-state test semantics.
  Evidence: targeted regression initially failed when projection helper fallback reentered materialization under mixed state; restoring `open_input_text(..., tolerate_mixed=True, mixed_prefer="archive")` preserved expected behavior.

- Observation: stage wrappers originally skipped projection when unmanaged `WD/<root>/` existed, which could silently bypass canonical mixed-state handling.
  Evidence: review found `_with_stage_read_projections(...)` `continue` path on non-symlink roots; fixed to raise canonical `NODIR_MIXED_STATE` and covered with regression test.

- Observation: fallback logging requirements needed explicit test coverage for both fallback branches.
  Evidence: added `test_with_input_file_path_projection_disabled_fallback_logs_warning` to cover the `use_projection=False` fallback warning path.

## Decision Log

- Decision: Keep Phase 9D scoped to the required WEPP path-heavy stages and their direct RQ read-stage wrappers; do not broaden to Phase 9E perf/runbook artifacts.
  Rationale: matches implementation-plan cut line and avoids speculative behavior expansion.
  Date/Author: 2026-02-18 / Codex.

- Decision: Use existing helper-layer API `with_input_file_path(...)` for path-required reads and enable fallback only via explicit `allow_materialize_fallback=True` at migrated call sites.
  Rationale: satisfies projection-first + fallback-only policy while minimizing new abstractions.
  Date/Author: 2026-02-18 / Codex.

## Outcomes & Retrospective

Phase 9D is complete for the requested cut line.

Delivered behavior:
- WEPP path-heavy stages now use projection-aware path contexts (`with_input_file_path`) for filesystem-path consumers, with explicit fallback-only materialization enabled where projection cannot be used.
- Flowpath slope extraction keeps projected source paths alive for the extraction worker window via scoped context lifetime management.
- RQ stage wrappers now own explicit read-session boundaries (`with_root_projection`) for migrated WEPP read stages and release automatically on both success and exception paths.
- Read-only stages remain non-mutating and no thaw/freeze mutation wrappers were introduced.

Validation outcome:
- `wctl run-pytest tests/nodir/test_projections.py tests/nodir/test_wepp_inputs.py` -> `37 passed`
- `wctl run-pytest tests/nodb/test_wepp_nodir_read_paths.py tests/rq/test_wepp_rq_nodir.py` -> `27 passed`
- `wctl run-pytest tests/nodir/test_wepp_inputs.py` -> `22 passed`
- `wctl run-pytest tests/rq tests/microservices/test_rq_engine_wepp_routes.py` -> `52 passed`
- `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` -> `43 files validated, 0 errors, 0 warnings`

Phase 9D handoff posture:
- Stage wrappers enforce strict canonical mixed-state failure (`409`) for unmanaged root+archive collisions.
- Projection fallback observability warnings are covered for both disabled-projection and projection-error branches.
- Latest rerun gates remain green and are mirrored in `implementation_plan.md`.

## Context and Orientation

Primary runtime files:
- `wepppy/nodb/core/wepp.py` (path-heavy WEPP prep consumers)
- `wepppy/rq/wepp_rq.py` (stage-level WEPP RQ wrappers)
- `wepppy/nodir/wepp_inputs.py` (projection-aware helper layer)
- `wepppy/nodir/projections.py` (projection lifecycle utility)

Primary tests:
- `tests/nodb/test_wepp_nodir_read_paths.py`
- `tests/rq/test_wepp_rq_nodir.py`
- `tests/nodir/test_wepp_inputs.py`
- `tests/nodir/test_projections.py`
- `tests/microservices/test_rq_engine_wepp_routes.py`

Contract constraints:
- Preserve canonical NoDir status/code behavior (`409`, `500`, `503`, `413`).
- Read-only WEPP prep stages remain non-mutating and thaw-free.
- Per-file materialization in migrated stages is fallback-only.

## Plan of Work

Update the target WEPP functions so path-consuming operations resolve through projection-aware helper contexts rather than defaulting to per-file materialization. For flowpath prep, keep projection-backed source paths alive across threaded extraction work via scoped context lifetimes.

Add RQ helper boundaries that acquire read projections per stage where archive-backed roots are present, then release deterministically on success and exceptions using context management.

Add/adjust tests to assert stage behavior and projection lifecycle semantics, then run the required gate commands and record results in this ExecPlan and the implementation plan.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Edit `wepppy/nodb/core/wepp.py` migrated stages.
2. Edit `wepppy/rq/wepp_rq.py` stage-scoped projection wrappers.
3. Update regression tests in `tests/nodb/test_wepp_nodir_read_paths.py` and `tests/rq/test_wepp_rq_nodir.py` as needed.
4. Execute required validation gates:
   - `wctl run-pytest tests/nodir/test_projections.py tests/nodir/test_wepp_inputs.py`
   - `wctl run-pytest tests/nodb/test_wepp_nodir_read_paths.py tests/rq/test_wepp_rq_nodir.py`
   - `wctl run-pytest tests/rq tests/microservices/test_rq_engine_wepp_routes.py`
   - `wctl doc-lint --path docs/work-packages/20260214_nodir_archives`

## Validation and Acceptance

Phase 9D is accepted when:
- Migrated WEPP path-heavy stages use projection-aware input paths.
- `wepp_rq` stages hold explicit projection acquire/release boundaries where needed.
- Release is exception-safe.
- Canonical NoDir status/code behavior is preserved.
- Required validation gates pass.
- Implementation plan and this ExecPlan capture exact evidence.

## Idempotence and Recovery

Changes are additive and safe to rerun. Projection wrappers must always release via context exit; failures should surface normally while ensuring no leaked projection sessions remain from the stage wrappers.

## Artifacts and Notes

Evidence for this phase will be captured in:
- `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md`
- This ExecPlan (`Progress`, `Outcomes & Retrospective`)

## Interfaces and Dependencies

Interfaces consumed:
- `wepppy.nodir.wepp_inputs.with_input_file_path`
- `wepppy.nodir.projections.with_root_projection`
- `wepppy.nodir.fs.resolve`

Dependencies:
- Existing WEPP prep call graph in `wepppy/nodb/core/wepp.py`.
- Existing RQ orchestration in `wepppy/rq/wepp_rq.py`.

---
Revision Note (2026-02-18, Codex): Initial Phase 9D ExecPlan authored after required startup reads; implementation pending.

Revision Note (2026-02-18, Codex): Completed Phase 9D WEPP/RQ consumer migration, landed regression updates, and recorded validation evidence.

Revision Note (2026-02-18, Codex): Addressed review finding by enforcing canonical mixed-state failure in stage projection wrappers and adding targeted regression coverage.

Revision Note (2026-02-18, Codex): Added missing projection-disabled fallback warning test coverage and reran focused NoDir helper validation.

Revision Note (2026-02-18, Codex): Refreshed Phase 9D handoff summary and final rerun gate evidence after strict mixed-state and fallback-observability hardening.
