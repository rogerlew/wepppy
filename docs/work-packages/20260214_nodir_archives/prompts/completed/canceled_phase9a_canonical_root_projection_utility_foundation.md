# Phase 9A NoDir Canonical Root Projection Utility Foundation ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this phase is complete, NoDir allowlisted archive roots can be projected at canonical runtime paths (`WD/<root>`) through a managed lifecycle API instead of requiring widespread per-file extraction. This enables path-heavy legacy consumers to keep using normal filesystem operations while NoDir still preserves archive authority and canonical lock/error behavior.

The visible proof is that projection utility tests pass, a read session can project and unproject a root deterministically, and a mutation session can commit or abort changes with explicit lifecycle state and canonical status-code semantics.

## Progress

- [x] (2026-02-18 03:24Z) Authored Phase 9A implementation ExecPlan under `docs/work-packages/20260214_nodir_archives/prompts/active/phase9a_canonical_root_projection_utility_foundation.md`.
- [x] (2026-02-18 16:04Z) Implemented `wepppy/nodir/projections.py` with projection handle model, read/mutate acquire/release lifecycle, stale metadata sweep, and explicit `commit`/`abort` mutation APIs.
- [x] (2026-02-18 16:12Z) Added `tests/nodir/test_projections.py` covering reuse/refcount, lock contention, mixed-state rejection, invalid archive/transition lock errors, mutate commit/abort, context-manager release, and stale sweep behavior.
- [x] (2026-02-18 16:14Z) Integrated projection utility exports in `wepppy/nodir/__init__.py` without broad helper/RQ consumer migration.
- [x] (2026-02-18 16:30Z) Ran Phase 9A validation gates and captured green evidence in this ExecPlan.
- [x] (2026-02-18 17:05Z) Closed initial post-review correctness gaps: cross-mode contention now returns `503 NODIR_LOCKED`, reuse refcount updates are serialized via a reuse lock, and duplicate release is token-idempotent.
- [x] (2026-02-18 18:02Z) Completed second-review hardening: mutation commit/abort now enforce live lock+session ownership, release uses reuse-lock serialization, stale sweep is fail-closed on Redis uncertainty with run-root path guards, and regression coverage expanded.

## Surprises & Discoveries

- Observation: Existing `resolve(..., view="archive")` already preserved canonical `503 NODIR_LOCKED` and `500 NODIR_INVALID_ARCHIVE` preflight behavior for projection acquire.
  Evidence: `tests/nodir/test_projections.py` includes transition lock and invalid archive assertions; both passed.

- Observation: Safe stale cleanup needed lock-value parity checks before metadata reuse.
  Evidence: Added stale sweep regression (`test_projection_acquire_sweeps_stale_metadata_and_orphan_mount`) with orphan metadata + orphan mount fixtures; acquire succeeded only after sweep.

- Observation: Opposite-mode contention was originally surfaced as `409 NODIR_MIXED_STATE` because managed mount conflicts were treated like unmanaged mixed directories.
  Evidence: Added `test_projection_cross_mode_conflict_returns_locked`; behavior now returns `503 NODIR_LOCKED`.

- Observation: Stale sweep needed stricter fail-closed behavior; Redis read errors must not trigger destructive cleanup, and metadata paths must be bounded to the run root before deletion.
  Evidence: Added `test_stale_sweep_fails_closed_on_redis_error`; stale metadata remains and acquire returns `503` under simulated Redis get failure.

## Decision Log

- Decision: Phase 9A remains utility-first with no broad WEPP/RQ call-site migration.
  Rationale: Keeps scope aligned with the cut line and minimizes contract risk.
  Date/Author: 2026-02-18 / Codex.

- Decision: Implement managed projection roots using symlink mountpoints at `WD/<root>` backed by extracted runtime layers under `WD/.nodir/(lower|upper|work)`.
  Rationale: Provides deterministic lifecycle behavior without introducing speculative FUSE dependencies in this phase.
  Date/Author: 2026-02-18 / Codex.

- Decision: Reuse existing freeze-side safety helpers for mutation commit and enforce fail-safe release semantics by auto-aborting active mutation sessions.
  Rationale: Preserves archive validation/parquet sidecar policy and guarantees release never implies commit.
  Date/Author: 2026-02-18 / Codex.

- Decision: Managed projection mount conflicts should map to lock contention (`503 NODIR_LOCKED`) rather than mixed unmanaged state (`409`).
  Rationale: Conflicts between active managed sessions are coordination failures, not mixed-state filesystem corruption.
  Date/Author: 2026-02-18 / Codex.

- Decision: Post-review hardening must enforce live lock/session ownership for mutation commit/abort and serialize release updates with the same reuse lock as acquire.
  Rationale: Prevents stale-handle mutation and acquire/release race windows that can drop session accounting.
  Date/Author: 2026-02-18 / Codex.

## Outcomes & Retrospective

Phase 9A implementation is complete for the utility foundation cut line. New projection APIs now provide deterministic read/mutate projection lifecycle management with canonical NoDir error propagation and explicit mutation commit/abort controls.

Validation outcome:
- `wctl run-pytest tests/nodir -k "state or thaw_freeze or resolve"` -> `43 passed, 81 deselected`
- `wctl run-pytest tests/nodir/test_projections.py` -> `16 passed`
- `wctl run-pytest tests/nodir/test_projections.py tests/nodir/test_wepp_inputs.py` -> `30 passed`
- `wctl run-pytest tests/rq/test_wepp_rq_nodir.py tests/microservices/test_rq_engine_wepp_routes.py` -> `18 passed`
- `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` -> `40 files validated, 0 errors, 0 warnings`

Remaining for later phases: helper-layer projection adoption, mutation-orchestrator transition, and WEPP/RQ consumer migration.

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

Observed: `43 passed, 77 deselected`.

2. Add and iterate projection tests.

    wctl run-pytest tests/nodir/test_projections.py

Observed: `12 passed`.

3. Run Phase 9A minimum gates.

    wctl run-pytest tests/nodir/test_projections.py tests/nodir/test_wepp_inputs.py
    wctl run-pytest tests/rq/test_wepp_rq_nodir.py tests/microservices/test_rq_engine_wepp_routes.py
    wctl doc-lint --path docs/work-packages/20260214_nodir_archives

Observed: all commands exit `0`.

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
Revision Note (2026-02-18, Codex): Implemented Phase 9A utility foundation, landed projection lifecycle/tests, and updated living sections with validation evidence.
Revision Note (2026-02-18, Codex): Addressed review findings for contention status mapping, refcount update serialization, and release token idempotence; expanded projection tests for these regressions.
Revision Note (2026-02-18, Codex): Completed second-review hardening for mutation ownership checks, release/acquire serialization, stale-sweep fail-closed behavior, and added targeted regression coverage.
