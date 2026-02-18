# Phase 9A NoDir Canonical Root Projection Utility Foundation ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this phase is complete, NoDir allowlisted archive roots can be projected at canonical runtime paths (`WD/<root>`) through a managed lifecycle API instead of requiring widespread per-file extraction. This enables path-heavy legacy consumers to keep using normal filesystem operations while NoDir still preserves archive authority and canonical lock/error behavior.

The visible proof is that projection utility tests pass, a read session can project and unproject a root deterministically, and a mutation session can commit or abort changes with explicit lifecycle state and canonical status-code semantics.

## Progress

- [x] (2026-02-18 03:24Z) Authored Phase 9A implementation ExecPlan under `docs/work-packages/20260214_nodir_archives/prompts/active/phase9a_canonical_root_projection_utility_foundation.md`.
- [ ] Implement `wepppy/nodir/projections.py` with acquire/release and commit/abort APIs.
- [ ] Add `tests/nodir/test_projections.py` for reuse, locking, lifecycle, and canonical error behavior.
- [ ] Integrate projection preflight with existing NoDir state/error contracts without broad call-site migration.
- [ ] Run Phase 9A minimum validation gates and publish initial evidence.

## Surprises & Discoveries

- Observation: Mixed-state failures in Phase 8 came from partial directory remnants colliding with archive-first readers, not from missing read helpers alone.
  Evidence: Runtime failures included repeated `NODIR_MIXED_STATE` and missing slope file fallout after mixed-state recovery events.

- Observation: Direct writable zip-mount semantics would weaken deterministic recovery because writes are not naturally bounded by explicit commit phases.
  Evidence: Phase 8 reliability incidents already showed that partially mutated filesystem surfaces are operationally fragile under retries.

## Decision Log

- Decision: Phase 9A will introduce projection lifecycle utilities first, with no broad consumer rewrites in the same milestone.
  Rationale: Utility-first scope keeps contract risk bounded and aligns with change-scope discipline.
  Date/Author: 2026-02-18 / Codex.

- Decision: `materialize(file)` remains supported but is explicitly fallback-only, not default path-heavy behavior.
  Rationale: Preserves compatibility while reducing cache churn and call-site complexity.
  Date/Author: 2026-02-18 / Codex.

- Decision: Mutation projections require explicit `commit`/`abort` APIs and cannot imply auto-commit on release.
  Rationale: Explicit transaction boundaries are required for deterministic failure handling and forensics.
  Date/Author: 2026-02-18 / Codex.

## Outcomes & Retrospective

Phase 9A planning is now implementation-ready. Runtime code is not changed yet by this document; this plan defines the utility-first cut line, interfaces, and validation path so implementation can proceed without revisiting architecture decisions.

## Context and Orientation

Current NoDir operations support native archive reads, stateful thaw/freeze mutation orchestration, and file-level materialization. Phase 8 improved WEPP read reliability but exposed that high-fanout path consumers still incur complexity when every path operation is translated into per-file extraction behavior.

In this repository, a "projection" means making `WD/<root>` a managed runtime mountpoint backed by `WD/<root>.nodir`. A "read session" means read-only projection reuse. A "mutation session" means a writable upper/work layer over a read-only archive lower layer, with explicit commit or abort to finalize archive changes.

Primary files for Phase 9A implementation:
- `wepppy/nodir/projections.py` (new)
- `wepppy/nodir/mutations.py` (contract-integration touchpoint only, not full migration)
- `wepppy/nodir/fs.py` (projection-aware state checks where required)
- `wepppy/nodir/materialize.py` (fallback relationship only)
- `tests/nodir/test_projections.py` (new)

Contract references:
- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`
- `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md` (Phase 9 + Phase 6 revision assessment)

## Plan of Work

Milestone 1 defines the projection utility module and handle data model. The API must support idempotent acquire/release for read and mutation modes, deterministic lock keying, and explicit metadata persistence under `WD/.nodir/projections/...`.

Milestone 2 implements lifecycle control. For read mode, acquire should mount or reuse, and release should unmount only when refcount reaches zero. For mutation mode, acquire should create lower/upper/work layout, and `commit`/`abort` should finalize or discard upper changes explicitly.

Milestone 3 adds tests for the utility in isolation: same-key reuse, lock contention, invalid archive behavior, mixed unmanaged directory rejection, stale metadata cleanup, and release semantics under exceptions.

Milestone 4 performs limited integration wiring so the projection utility can be called by future helper-layer migrations without changing broad call-site behavior in this phase.

Milestone 5 validates and records evidence with targeted pytest and docs lint, then updates this plan's living sections and Phase 9 evidence stub docs.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implement projection utility skeleton and handle schema.

    wctl run-pytest tests/nodir -k "state or thaw_freeze or resolve"

Expected: baseline NoDir state/lock tests remain green.

2. Add and iterate projection tests.

    wctl run-pytest tests/nodir/test_projections.py

Expected: new utility lifecycle tests pass and validate canonical errors.

3. Run Phase 9A minimum gates.

    wctl run-pytest tests/nodir/test_projections.py tests/nodir/test_wepp_inputs.py
    wctl run-pytest tests/rq/test_wepp_rq_nodir.py tests/microservices/test_rq_engine_wepp_routes.py
    wctl doc-lint --path docs/work-packages/20260214_nodir_archives

Expected: all commands exit `0` with no docs lint errors.

## Validation and Acceptance

Phase 9A is accepted when all are true:
- Projection utility APIs exist with documented signatures and deterministic behavior.
- Same projection key acquire calls reuse one live projection with refcount tracking.
- Canonical NoDir errors remain consistent (`409`, `500`, `503`, `413`) at utility boundaries.
- Mutation projection lifecycle is explicit (`acquire -> commit|abort -> release`) and test-covered.
- Targeted tests and docs lint pass.

## Idempotence and Recovery

Phase 9A steps are repeatable. Re-running acquire/release tests must not leak mounts when release executes. Failed mutation sessions must be recoverable by explicit abort, and stale metadata sweep must remain best-effort and nondestructive.

If a test run leaves a stale projection artifact, clear only the run-local projection metadata path under `WD/.nodir/projections/...` after collecting logs; do not delete `WD/<root>.nodir`.

## Artifacts and Notes

Phase 9A evidence targets (initial stubs can be created during implementation):
- `docs/work-packages/20260214_nodir_archives/artifacts/phase9_projection_sessions_perf_results.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase9_projection_sessions_reliability_runbook.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase9_projection_sessions_rollout_review.md`

## Interfaces and Dependencies

Utility interface to implement in `wepppy/nodir/projections.py`:

    def acquire_root_projection(
        wd: str | Path,
        root: str,
        *,
        mode: Literal["read", "mutate"],
        purpose: str,
    ) -> ProjectionHandle:
        ...

    def release_root_projection(handle: ProjectionHandle) -> None:
        ...

    @contextmanager
    def with_root_projection(
        wd: str | Path,
        root: str,
        *,
        mode: Literal["read", "mutate"],
        purpose: str,
    ) -> Iterator[ProjectionHandle]:
        ...

    def commit_mutation_projection(handle: ProjectionHandle) -> None:
        ...

    def abort_mutation_projection(handle: ProjectionHandle) -> None:
        ...

Dependencies:
- Reuse existing NoDir lock/state conventions in `wepppy/nodir/thaw_freeze.py` and `wepppy/nodir/mutations.py`.
- Preserve canonical error semantics and response contract compatibility (`docs/schemas/rq-response-contract.md`).
- Do not change RQ enqueue dependency graph in Phase 9A.

---
Revision Note (2026-02-18, Codex): Initial Phase 9A utility-first ExecPlan authored to implement canonical root projection lifecycle APIs and tests before broad consumer migration.
