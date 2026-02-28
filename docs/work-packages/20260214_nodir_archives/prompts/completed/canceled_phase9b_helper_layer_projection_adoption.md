# Phase 9B Helper-Layer Projection Adoption ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Phase 9A delivered projection lifecycle utilities, but helper-layer WEPP input access still defaulted to per-file behaviors and had no projection-first filesystem-path helper for path-heavy consumers. After this phase, helper-layer consumers can request canonical runtime paths through managed read projections (`WD/<root>`) while retaining explicit per-file materialization as a compatibility fallback.

Visible proof is: projection-first helper tests pass, fallback behavior remains explicit and controllable, and archive-native browse/files/download semantics stay unchanged.

## Progress

- [x] (2026-02-18 04:31Z) Read required startup sources (AGENTS, ExecPlan template, Phase 9 plan/contracts, runtime modules, and target tests) and confirmed Phase 9B cut line.
- [x] (2026-02-18 04:31Z) Authored active Phase 9B ExecPlan at `docs/work-packages/20260214_nodir_archives/prompts/active/phase9b_helper_layer_projection_adoption.md`.
- [x] (2026-02-18 04:39Z) Implemented projection-aware helper API `with_input_file_path(...)` in `wepppy/nodir/wepp_inputs.py` with projection-first behavior and explicit materialization fallback controls.
- [x] (2026-02-18 04:43Z) Added regression tests in `tests/nodir/test_wepp_inputs.py` for projection-first path resolution, projection-error fallback to materialization, and no-fallback canonical error propagation.
- [x] (2026-02-18 05:02Z) Added minimal follow-up tests for explicit fallback gating and direct `409`/`500` canonical error propagation through `with_input_file_path(...)`.
- [x] (2026-02-18 04:46Z) Ran required Phase 9B validation gates with `wctl` wrappers (all green).
- [x] (2026-02-18 04:49Z) Updated `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md` with Phase 9B completion status and evidence.
- [x] (2026-02-18 04:49Z) Finalized this ExecPlan with outcomes and revision note.

## Surprises & Discoveries

- Observation: `wepppy/nodir/wepp_inputs.py` had no projection-session helper even though `projections.py` lifecycle APIs were already available.
  Evidence: startup read of `wepppy/nodir/wepp_inputs.py` showed only open/copy/list/glob/exists/materialize helpers.

- Observation: helper-level projection failure handling needed explicit opt-in fallback to avoid silently masking lock/contention errors.
  Evidence: new test `test_with_input_file_path_projection_error_without_fallback_raises` verifies canonical `503 NODIR_LOCKED` propagation when fallback is disabled.

## Decision Log

- Decision: Keep Phase 9B strictly helper-layer scoped by adding projection-aware path helpers in `wepp_inputs` without broad WEPP/RQ orchestration migration.
  Rationale: matches implementation-plan cut line (`9B` only) and minimizes regression risk.
  Date/Author: 2026-02-18 / Codex.

- Decision: implement projection-first path resolution as a context manager (`with_input_file_path`) so projection lifecycle cleanup is deterministic and caller-safe.
  Rationale: projected mount paths are session-bound and must be released reliably on exit.
  Date/Author: 2026-02-18 / Codex.

## Outcomes & Retrospective

Phase 9B helper-layer adoption is complete for the requested cut line.

Delivered behavior:
- `wepp_inputs` now exposes `with_input_file_path(...)` for path-heavy consumers that need filesystem paths.
- Archive-form NoDir paths use projection-first behavior via `with_root_projection(...)`.
- `materialize_input_file(...)` remains intact and is used only when explicitly enabled via `allow_materialize_fallback=True`.
- Projection errors preserve canonical semantics by default (no silent fallback).

Validation outcome:
- `wctl run-pytest tests/nodir/test_projections.py tests/nodir/test_wepp_inputs.py` -> `36 passed`
- `wctl run-pytest tests/nodb/test_wepp_nodir_read_paths.py` -> `14 passed`
- `wctl run-pytest tests/rq/test_wepp_rq_nodir.py tests/microservices/test_rq_engine_wepp_routes.py` -> `18 passed`
- `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` -> `41 files validated, 0 errors, 0 warnings`

## Context and Orientation

Relevant modules:
- `wepppy/nodir/projections.py` provides lifecycle APIs for read/mutate sessions.
- `wepppy/nodir/wepp_inputs.py` is the high-fanout helper layer used by WEPP prep/read paths.
- `wepppy/nodir/materialize.py` remains the explicit per-file fallback path.
- `tests/nodir/test_wepp_inputs.py` and `tests/nodb/test_wepp_nodir_read_paths.py` hold helper and WEPP-path regression coverage.

Contract constraints:
- Preserve canonical NoDir status/code behavior (`409 NODIR_MIXED_STATE`, `500 NODIR_INVALID_ARCHIVE`, `503 NODIR_LOCKED`, `413 NODIR_LIMIT_EXCEEDED`).
- Keep archive-native browse/files/download semantics unaffected.
- Keep `materialize_input_file(...)` supported as explicit compatibility fallback.

## Plan of Work

Add a projection-aware helper context manager in `wepp_inputs` that resolves a logical path, acquires a read projection for archive-backed allowlisted roots, and yields a canonical filesystem path under `WD/<root>`. Keep fallback behavior explicit: if projection is disabled or projection acquire fails, callers can opt into `materialize_input_file(...)` fallback.

Add focused tests proving projection-first behavior and fallback controls, then run required validation gates and update plan evidence.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implement helper-layer projection-aware API and keep explicit fallback path.
2. Add regression coverage for projection-first + fallback controls.
3. Execute validation gates:
   - `wctl run-pytest tests/nodir/test_projections.py tests/nodir/test_wepp_inputs.py`
   - `wctl run-pytest tests/nodb/test_wepp_nodir_read_paths.py`
   - `wctl run-pytest tests/rq/test_wepp_rq_nodir.py tests/microservices/test_rq_engine_wepp_routes.py`
   - `wctl doc-lint --path docs/work-packages/20260214_nodir_archives`

## Validation and Acceptance

Phase 9B is accepted when:
- `wepp_inputs` exposes projection-aware helper behavior for path-heavy consumers.
- `materialize_input_file(...)` remains available as explicit fallback and is not removed.
- Tests verify projection-first behavior and fallback controls.
- Required validation commands pass.
- Implementation plan and this ExecPlan contain completion evidence.

## Idempotence and Recovery

Changes are additive and can be re-run safely. If a projection helper change regresses behavior, callers can keep using existing `materialize_input_file(...)` as compatibility fallback while helper-level fixes are adjusted.

## Artifacts and Notes

Phase 9B evidence is recorded in:
- `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md`
- This ExecPlan (`Progress`, `Outcomes & Retrospective`)

## Interfaces and Dependencies

Helper addition in `wepppy/nodir/wepp_inputs.py`:
- `with_input_file_path(...)` context manager for projection-first filesystem-path resolution.

Dependencies:
- `wepppy.nodir.projections.with_root_projection`
- Existing `wepppy.nodir.fs.resolve` and normalization behavior.
- Existing NoDir error model and response-contract alignment.

---
Revision Note (2026-02-18, Codex): Initial Phase 9B ExecPlan authored after required startup reads; implementation pending.
Revision Note (2026-02-18, Codex): Completed Phase 9B helper-layer projection adoption, landed tests, ran required gates, and captured evidence/outcomes.
Revision Note (2026-02-18, Codex): Added minimal follow-up Phase 9B tests for explicit fallback gating and direct 409/500 propagation coverage, then reran required gates.
