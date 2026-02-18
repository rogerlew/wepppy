# Phase 7 NoDir Bulk Migration + Default-to-NoDir Rollout ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this phase is complete, operators can migrate existing runs to NoDir archive form safely at scale using a resumable audited crawler, and all newly created runs will prefer `.nodir` representation for allowlisted roots without mixed-state regressions. Users and operators will have measurable evidence that browse/listing/download/materialization/archive workflows perform acceptably under archive-backed roots, plus an operational runbook for rollback and forensics.

Visible proof:
- A production-safe bulk migration CLI exists with readonly/lock safety, resume, audit logs, and required filters.
- New runs naturally converge to archive-backed roots through existing thaw/freeze and mutation contracts.
- Phase 7 perf targets are documented with measured before/after results.
- Phase 7 docs are complete and `implementation_plan.md` marks the phase as done with evidence links.

## Progress

- [x] (2026-02-17 17:19Z) Read required startup sources in order (`AGENTS.md`, exec-plan template, Phase 7 normative plan section, Phase 6 handoff, NoDir contracts/artifacts, migration tooling, thaw/freeze and mutation code).
- [x] (2026-02-17 17:19Z) Created active Phase 7 ExecPlan scaffold at `docs/work-packages/20260214_nodir_archives/prompts/active/phase7_bulk_migration_default_nodir_rollout.md`.
- [x] (2026-02-17 18:11Z) Milestone 0 complete: baseline implementation map finalized; mutation/creation touchpoints and migration-extension surface locked for Phase 7 execution.
- [x] (2026-02-17 18:36Z) Milestone 1 complete: perf targets and reproducible benchmark method captured with measured baseline/after values (synthetic large-run harness).
- [x] (2026-02-17 18:28Z) Milestone 2 complete: implemented `wepppy/tools/migrations/nodir_bulk.py` with required filters, JSONL auditing, and resume behavior.
- [x] (2026-02-17 18:28Z) Milestone 3 complete: enforced `READONLY` mutation gate, run-lock fail-fast, per-root maintenance lock fail-fast, and canonical NoDir error capture in audit events.
- [x] (2026-02-17 18:28Z) Milestone 4 complete: new-run creation paths now persist default NoDir root policy marker; mutation orchestration auto-freezes configured dir-form roots post-mutation without mixed-state persistence.
- [x] (2026-02-17 18:54Z) Milestone 5 complete: Phase 7 artifacts authored (perf targets/results, operational runbook, rollout review) and `implementation_plan.md` Phase 7 marked DONE with evidence links.
- [x] (2026-02-17 19:09Z) Milestone 6 complete: required pytest + docs lint gates passed, including full-suite regression and explicit new/modified Phase 7 test set.
- [x] (2026-02-17 19:34Z) Post-closeout doc polish complete: authored a dedicated Phase 7 handoff summary and inlined target-vs-result performance metrics in `implementation_plan.md` for one-page operator handoff.
- [x] (2026-02-17 20:12Z) Review-remediation pass complete: fixed rollback runbook correctness (`export` usage + existing-marker rollback guidance), added missing marker-seeding coverage (`upload_huc_fire` and test-support create-run), and added explicit bulk-migrator regression coverage for `root_lock_failed` and no-resume replay behavior.

## Surprises & Discoveries

- Observation: The Phase 7 active ExecPlan file did not yet exist.
  Evidence: `ls docs/work-packages/20260214_nodir_archives/prompts/active` returned only `phase6a_watershed_touchpoint_plan.md`.

- Observation: The materialization benchmark initially failed with `NODIR_LIMIT_EXCEEDED` due a highly compressible synthetic raster exceeding the compression-ratio guard.
  Evidence: first perf probe run raised `NODIR_LIMIT_EXCEEDED (413): archive entry compression ratio exceeds materialization safety limit`; switching benchmark payload generation to random bytes resolved it.

- Observation: Independent review identified rollback correctness gaps: shell-to-Python environment handoff in the runbook omitted export, and disabling WEPP_NODIR_DEFAULT_NEW_RUNS alone does not neutralize existing per-run marker files.
  Evidence: rollback snippet consumed os.environ values while assigning non-exported shell variables; mutation orchestration always consumes existing WD/.nodir/default_archive_roots.json markers.

## Decision Log

- Decision: Use existing NoDir state/lock primitives (`resolve`, `maintenance_lock`, `freeze_locked`, `mutate_root(s)`) and extend migration tooling under `wepppy/tools/migrations/` instead of introducing a new lock system.
  Rationale: Matches AGENTS change-scope discipline and Phase 7 requirement to preserve canonical NoDir error behavior.
  Date/Author: 2026-02-17 / Codex.

- Decision: Represent “new runs prefer NoDir” as a run-local marker file (`WD/.nodir/default_archive_roots.json`) and apply archiving in shared `mutate_root(s)` post-callback flow.
  Rationale: Keeps representation state out of `.nodb`, avoids route-specific mutation branching, and scopes behavior to explicitly marked runs.
  Date/Author: 2026-02-17 / Codex.

- Decision: Seed the default marker in explicit new-run creation surfaces (`rq_engine project create`, HUC fire upload create path, test-support create-run) instead of global constructor-only side effects.
  Rationale: Minimizes unintended rollout scope while still covering operational run creation entry points.
  Date/Author: 2026-02-17 / Codex.

- Decision: Implement the bulk crawler as a dedicated migration module in `wepppy/tools/migrations/` with JSONL event logging and resume semantics keyed by run/root outcome records.
  Rationale: Keeps bulk-ops concerns isolated while reusing existing migration/thaw/freeze contracts.
  Date/Author: 2026-02-17 / Codex.

- Decision: Address rollback toggling risk operationally by explicitly disabling/renaming per-run default_archive_roots markers in the runbook, rather than expanding runtime mutation semantics.
  Rationale: Smallest safe change for Phase 7 closeout; preserves existing contract behavior while making rollback steps operationally complete.
  Date/Author: 2026-02-17 / Codex.

## Outcomes & Retrospective

Phase 7 completed with all required deliverables implemented and validated.

Achieved outcomes:
- Bulk crawler CLI is landed with required filters, resumable JSONL audit logs, readonly gating, and fail-fast lock checks.
- New-run default NoDir policy is active through run-local marker seeding on create flows and shared mutation orchestration auto-freeze behavior.
- Perf targets were defined and measured with documented before/after evidence in the Phase 7 perf artifact.
- Rollback/forensics/audit interpretation operational guidance is documented in the Phase 7 runbook.
- Required validation gates, including full-suite regression and docs lint, are green.

Residual risk:
- Perf evidence is based on a synthetic large-run harness; staged production canary verification on representative NAS-backed runs remains recommended before broad unattended migration waves.

## Context and Orientation

Phase 0-6 work is complete and Phase 7 is the only remaining plan item in `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md`.

NoDir allowlisted roots are `landuse`, `soils`, `climate`, and `watershed`. Directory form and archive form semantics, mixed/invalid/transitional errors, thaw/freeze state, and materialization limits are normative in:
- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`

Existing mutation orchestration and thaw/freeze operations already exist in:
- `wepppy/nodir/mutations.py`
- `wepppy/nodir/thaw_freeze.py`

Existing migration tooling is centered in:
- `wepppy/tools/migrations/runner.py`
- `wepppy/tools/migrations/run_migrations.py`
- `wepppy/rq/migrations_rq.py`

Phase 7 adds:
- Bulk crawler for existing runs (safety-gated, resumable, audited).
- New-run default NoDir representation rollout.
- Performance evidence and operational runbook.

## Plan of Work

### Milestone 0: Baseline + Implementation Map

Capture current code touchpoints for migration tooling, NoDir lock/state helpers, and new-run creation paths (`rq_engine project create`, run bootstrap). Identify minimal-change integration points and establish the active plan and evidence artifacts.

### Milestone 1: Perf Targets + Measurement Method

Define Phase 7 targets and measurement process first. The method will cover:
- browse listing p95 for HTML and `/files` JSON;
- download throughput (stream, no extraction);
- `materialize(file)` wall time;
- archive build time by root;
- inode reduction and stat-pressure notes.

The method must be reproducible and documented in the perf artifact.

### Milestone 2: Bulk Migration Crawler CLI

Implement a crawler module under `wepppy/tools/migrations/` that discovers run directories, filters by runid/root/limit, logs JSONL audit records, and supports resume by skipping already-successful run/root work from prior audit logs.

### Milestone 3: Safety Gates (Readonly + Fail-Fast Locking)

Enforce `WD/READONLY` before mutation, fail fast on active run/root locks, and preserve canonical NoDir error/status details in audit records. Ensure no cleanup is attempted by request-serving code and no implicit lock bypass occurs.

### Milestone 4: New-Run Default-to-NoDir

Wire new-run defaults so allowlisted root mutations prefer archive end-state by default for newly created runs, while preserving compatibility for existing runs and avoiding mixed-state regressions.

### Milestone 5: Tests + Docs + Evidence

Add focused regression tests for crawler filters/dry-run/resume/audit and safety gates, plus new-run default behavior and canonical error propagation at touched boundaries. Produce required artifacts:
- `docs/work-packages/20260214_nodir_archives/artifacts/phase7_perf_targets_and_results.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase7_operational_runbook.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase7_bulk_migration_rollout_review.md`

Update Phase 7 status in `implementation_plan.md` to complete with evidence links.

### Milestone 6: Full Validation + Closeout

Run required pytest/doc lint gates, capture exact outputs, and finalize verdict.

## Concrete Steps

Run commands from `/workdir/wepppy`.

1. Implement bulk crawler and default-to-NoDir wiring with focused unit/integration tests.
2. Run required targeted gates:

    wctl run-pytest tests/nodir
    wctl run-pytest tests/microservices/test_browse_routes.py tests/microservices/test_browse_security.py tests/microservices/test_files_routes.py tests/microservices/test_download.py tests/microservices/test_diff_nodir.py
    wctl run-pytest tests/microservices/test_rq_engine_migration_routes.py tests/tools/test_migrations_runner.py tests/tools/test_migrations_parquet_backfill.py

3. Run all new/modified Phase 7 tests explicitly.
4. Run full regression + docs gate:

    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260214_nodir_archives

## Validation and Acceptance

Phase 7 is accepted when all are true:
- Bulk crawler enforces readonly and fail-fast lock safety, supports required filters, and writes resumable JSONL audit logs.
- New runs default to archive-backed NoDir root representation without mixed-state regressions.
- Performance evidence is documented with before/after measurements and method notes.
- Rollout/runbook docs include rollback, forensics (including admin raw `.nodir` download), and audit log interpretation.
- Required validation commands pass.
- `implementation_plan.md` marks Phase 7 complete with linked artifacts.

## Idempotence and Recovery

- Crawler runs are idempotent with resume semantics driven by JSONL audit history.
- Fail-fast lock behavior avoids long waits and unsafe partial mutations.
- Rollback path must be documented and tested in the runbook (including reverting default-to-NoDir wiring and pausing crawler execution).

## Artifacts and Notes

Required artifacts for this phase:
- `docs/work-packages/20260214_nodir_archives/artifacts/phase7_perf_targets_and_results.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase7_operational_runbook.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase7_bulk_migration_rollout_review.md`

Phase status source:
- `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md` (Phase 7 section).

## Interfaces and Dependencies

Implementation must preserve canonical contracts for NoDir errors and thaw/freeze states:
- `NoDirError` shape and `{status, code}` mapping from `wepppy/nodir/errors.py`.
- `resolve(..., view="effective")` behavior from `wepppy/nodir/fs.py`.
- Maintenance lock key and lock ownership from `wepppy/nodir/thaw_freeze.py`.
- State transition semantics from `wepppy/nodir/state.py` and `docs/schemas/nodir-thaw-freeze-contract.md`.

Bulk crawler should live in existing migration tooling namespace (`wepppy/tools/migrations/`) and expose a CLI entrypoint via `python -m`.

---
Change note (2026-02-17 / Codex): initial Phase 7 ExecPlan authored to start implementation with explicit milestones, gates, and required deliverables.
Change note (2026-02-17 / Codex): completed Phase 7 implementation, documentation artifacts, and validation gate evidence; updated milestones and retrospective to final state.
Change note (2026-02-17 / Codex): added a dedicated Phase 7 handoff summary and inline performance metrics table to `implementation_plan.md` for direct operator handoff context.
Change note (2026-02-17 / Codex): addressed post-review gaps in rollback runbook correctness and added missing Phase 7 regression coverage (upload_huc_fire marker seeding, test-support marker seeding, root_lock_failed, no-resume).
