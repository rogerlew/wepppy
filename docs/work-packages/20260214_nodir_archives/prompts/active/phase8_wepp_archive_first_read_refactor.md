# Phase 8 WEPP Archive-First NoDir Read Refactor ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this phase is complete, WEPP prep paths can consume `landuse`, `soils`, and `watershed` directly from `.nodir` archives without root-level thaw/freeze, and read-only RQ prep stages stop taking NoDir mutation locks solely to read inputs. The expected user-visible outcomes are fewer archived-run prep failures caused by missing directory-form roots and lower prep latency by removing unnecessary thaw/freeze cycles.

Visible proof:
- `wepppy/nodir/wepp_inputs.py` exists and is covered by focused unit tests.
- `wepppy/nodb/core/wepp.py` prep reads are archive-first or file-level materialized where path-only consumers require real files.
- `wepppy/rq/wepp_rq.py` read-only stages no longer wrap with `mutate_root(s)`.
- Phase 8 artifacts capture touchpoint inventory, reliability outcomes, perf before/after, and closeout review.
- Required pytest and docs lint gates pass.

## Progress

- [x] (2026-02-17 21:03Z) Completed required startup reads in order (`AGENTS.md`, exec-plan template, Phase 8 section in implementation plan, NoDir contracts, RQ response contract, target runtime files).
- [x] (2026-02-17 21:03Z) Created active Phase 8 ExecPlan at `docs/work-packages/20260214_nodir_archives/prompts/active/phase8_wepp_archive_first_read_refactor.md`.
- [x] (2026-02-17 21:11Z) Milestone 0 complete: published touchpoint inventory and baseline perf/reliability artifacts (`wepp_nodir_read_touchpoints_phase8a.md`, baseline section in `phase8_wepp_nodir_perf_results.md`, baseline delta in `phase8_wepp_nodir_reliability_runbook.md`, and scaffolded review artifact).
- [x] (2026-02-17 21:13Z) Milestone 1 complete: implemented `wepppy/nodir/wepp_inputs.py` and `tests/nodir/test_wepp_inputs.py` with dir/archive read helpers, scoped glob support, materialize passthrough, and canonical NoDir error tests (12 passed).
- [x] (2026-02-17 21:18Z) Milestone 2 complete: refactored `wepppy/nodb/core/wepp.py` prep read paths to use archive-first helper calls and file-level materialization for path-only consumers.
- [x] (2026-02-17 21:18Z) Milestone 3 complete: simplified read-only prep stages in `wepppy/rq/wepp_rq.py` to direct WEPP calls (no root thaw/freeze wrappers).
- [x] (2026-02-17 21:18Z) Milestone 4 complete: updated RQ NoDir wrapper tests and added `tests/nodb/test_wepp_nodir_read_paths.py` to cover archive-backed WEPP read paths.
- [x] (2026-02-17 21:33Z) Milestone 5 complete: finalized Phase 8 perf results, reliability runbook delta, and refactor review artifacts with before/after evidence.
- [x] (2026-02-17 21:40Z) Milestone 6 complete: all required validation/doc-lint gates passed and `implementation_plan.md` Phase 8 status/evidence updated to DONE.
- [x] (2026-02-18 00:17Z) Post-review remediation complete: restored `_prep_managements` override semantics (`get_management()` first), changed `_prep_channel_slopes` to archive-stream reads, and expanded WEPP NoDir read-touchpoint tests.
- [x] (2026-02-18 00:27Z) Re-ran required gates after remediation (`15 passed`, `17 passed`, `38 passed`, `1581 passed, 27 skipped`, docs lint clean).
- [x] (2026-02-18 00:41Z) Post-deploy hotfix: `_prep_managements` now resolves soil texture from materialized archive inputs before legacy `SoilSummary` path access to prevent `Invalid run identifier` failures in read-only archived prep.
- [x] (2026-02-18 01:14Z) Post-deploy reliability hardening: removed `_prep_remaining_rq` NoDir mutation wrapper (read-only stage), added run-start mixed-root recovery freeze in `run_wepp_rq`, patched disturbed `pmetpara_prep()` to resolve soil texture archive-first before legacy `_soil.path` access, and added mixed-state slope-clip fallback plus regression tests (full suite: `1585 passed, 27 skipped`).
- [x] (2026-02-18 01:32Z) Follow-up correction: moved mixed `watershed` recovery from `_prep_watershed_rq` to `run_wepp_watershed_rq` preflight so prep stages remain read-only; retained standalone watershed reliability via orchestrator preflight and re-ran RQ regression gates.
- [x] (2026-02-18 02:05Z) Mixed-state durability fix: changed `_recover_mixed_nodir_roots` to preserve existing `.nodir` archives and discard thawed dirs (no freeze overwrite), and added peridot slope fallback from `watershed/slope_files/hillslopes/hill_<id>.slp` to legacy `watershed/hill_<id>.slp`; validated RQ + WEPP NoDir tests.
- [x] (2026-02-18 02:24Z) Mixed-state read hardening: added opt-in mixed-tolerant archive-preferred reads in `wepp_inputs` and applied them to `_prep_channel_slopes`/`_prep_structure`; changed legacy channel slope branch to stream from the already-open source handle (no second mixed-state reopen), added regression tests, and re-ran RQ + route + NoDir suites (`37 passed`; `48 passed`).
- [x] (2026-02-18 02:40Z) Strategy pivot docs update: revised NoDir materialization contract to mount-first (FUSE zip canonical) and authored Phase 9 utility-first implementation phases in `implementation_plan.md`, including guidance to avoid blanket `wepp.py` revert.
- [x] (2026-02-18 03:05Z) Contract revision follow-up: replaced mount-first wording with canonical root projection sessions (`WD/<root>` projected runtime path, overlay-backed mutation commits), updated Phase 9 plan milestones, and added explicit Phase 6 artifact revision assessment in `implementation_plan.md`.
- [x] (2026-02-18 03:30Z) Follow-on planning package drafted: created active Phase 9A utility-first ExecPlan and applied Phase 9 contract-transition addenda to Phase 6 watershed/soils/landuse/climate Stage B/C/D review artifacts plus completed Phase 6 ExecPlan note.

## Surprises & Discoveries

- Observation: The active Phase 8 ExecPlan file did not yet exist.
  Evidence: `ls docs/work-packages/20260214_nodir_archives/prompts/active` listed only Phase 6A and Phase 7 plans.

- Observation: Baseline lock/thaw wrapper cost scales linearly with wrapped root count even for read-only callbacks.
  Evidence: synthetic benchmark p95 rose from 13.522 ms (`('watershed',)`) to 36.741 ms (`('climate','landuse','soils','watershed')`) with 360 lock acquisitions across 160 wrapper invocations.

- Observation: Introducing `wepp_inputs.py` created a package import cycle when it imported `materialize_file` at module load time.
  Evidence: pytest collection failed with `ImportError: cannot import name 'materialize_file' from partially initialized module 'wepppy.nodir.materialize'`; resolved by deferring the materialize import inside `materialize_input_file(...)`.

- Observation: During remediation, a transient bad edit left `_prep_channel_slopes` with an unterminated string literal and crashed `wepppy-browse` worker boot.
  Evidence: gunicorn boot log showed `SyntaxError: unterminated string literal (line 3031)`; corrected source now passes in-container `python -m py_compile /workdir/wepppy/wepppy/nodb/core/wepp.py`.

- Observation: callback failures in `_prep_remaining_rq` could leave thawed NoDir roots in mixed state (`dir + .nodir`), which then broke later archive-first prep reads (for example `_prep_slopes_rq`) with `NODIR_MIXED_STATE`.
  Evidence: production stack trace failed at `materialize_input_file(... watershed/...slp ...)` with `wepppy.nodir.errors.NoDirError: NODIR_MIXED_STATE (409)`.

- Observation: `run_wepp_rq` preflight recovery did not cover standalone `_prep_watershed_rq` invocations (directly enqueued job path), allowing mixed `watershed` state to surface later in `_prep_channel_slopes` via `input_exists(...)`.
  Evidence: production stack trace failed in `_prep_watershed_rq -> wepp.prep_watershed -> _prep_channel_slopes -> input_exists(...)` with `NODIR_MIXED_STATE (409)`.

- Observation: Recovering mixed watershed state inside `_prep_watershed_rq` violated the Phase 8 read-only stage constraint.
  Evidence: user validation required `_prep_watershed_rq` to remain non-mutating; recovery is now preflighted in `run_wepp_watershed_rq` instead.

- Observation: freezing mixed roots during preflight can overwrite a healthy archive with a partially-thawed directory tree after callback failure, dropping required inputs such as `watershed/slope_files/hillslopes/*.slp`.
  Evidence: production failures showed `FileNotFoundError: slope_files/hillslopes/hill_<id>.slp` after mixed-state recovery previously ran via `freeze(...)` in `_recover_mixed_nodir_roots`.

- Observation: `_prep_channel_slopes` legacy (<2023) branch still reopened sources through `copy_input_file(...)` after mixed-tolerant selection, re-triggering mixed-state resolution failures.
  Evidence: stage crashed in `_prep_channel_slopes` on `input_exists(...)`/reopen path with `NODIR_MIXED_STATE (409)` during `_prep_watershed_rq` despite upstream mixed-recovery preflight.

- Observation: per-file materialization is operationally noisy and difficult to reason about for high-fanout WEPP prep consumers; mount-scoped read sessions are easier to reason about and align with read-only stage semantics.
  Evidence: repeated mixed-state and missing-entry incidents required call-site-specific hardening despite archive-first helper adoption.

- Observation: direct writable zip-mount semantics would reintroduce archive corruption and recovery ambiguity under worker retries.
  Evidence: previous mixed-state incidents already demonstrated partial write surfaces are operationally fragile; projection sessions with explicit commit boundaries keep archive authority deterministic.

## Decision Log

- Decision: Keep Phase 8 scope narrow to archive-first read helpers plus targeted call-site refactors; avoid introducing generalized new NoDir mutation/state machinery.
  Rationale: Matches AGENTS change-scope discipline and Phase 8 requirement for smallest contract-correct implementation.
  Date/Author: 2026-02-17 / Codex.

- Decision: Use an in-container synthetic `mutate_roots(...)` benchmark as the baseline before/after reference for wrapper overhead.
  Rationale: It isolates thaw/freeze+lock overhead with deterministic inputs and does not depend on full WEPP end-to-end runtime variance.
  Date/Author: 2026-02-17 / Codex.

- Decision: Remove `mutate_roots(...)` from read-only prep stages (`_prep_slopes_rq`, `_prep_multi_ofe_rq`, `_prep_managements_rq`, `_prep_soils_rq`, `_prep_climates_rq`, `_run_flowpaths_rq`, `_prep_watershed_rq`); `_prep_remaining_rq` was temporarily retained pending disturbed pmet path hardening and then removed on 2026-02-18.
  Rationale: Archive-first read paths do not require root thaw/freeze wrappers and wrapper retention created avoidable lock/thaw churn plus mixed-state retry hazards.
  Date/Author: 2026-02-17 / Codex (updated 2026-02-18).

- Decision: In `_prep_managements`, always prefer `man_summary.get_management()` when present and only fallback to materialized `Management.load(...)` on `FileNotFoundError`, then apply summary overrides in fallback path.
  Rationale: Preserves canonical canopy/residue override semantics while remaining archive-safe for landuse roots that exist only as `.nodir`.
  Date/Author: 2026-02-18 / Codex.

- Decision: Treat `_prep_remaining_rq` as read-only for NoDir roots (remove `mutate_roots`), and add `run_wepp_rq` mixed-root preflight recovery before enqueuing stage jobs.
  Rationale: Prevents retry loops where prior callback failures strand roots in mixed state and immediately break archive-first readers on the next run.
  Date/Author: 2026-02-18 / Codex.

- Decision: Keep `_prep_watershed_rq` read-only and shift mixed `watershed` recovery to `run_wepp_watershed_rq` preflight (scoped to `roots=("watershed",)`).
  Rationale: Preserves Phase 8 read-only stage semantics while still repairing mixed-state failures before watershed prep jobs are enqueued.
  Date/Author: 2026-02-18 / Codex.

- Decision: Mixed-state preflight recovery must be archive-authoritative: when both `root/` and `root.nodir` exist, remove `root/` and keep `root.nodir` instead of freezing dir-form content back into the archive.
  Rationale: Callback failures can leave partially-mutated thawed trees; freezing them can destroy valid archived inputs (observed loss of `watershed/slope_files/hillslopes/*.slp`).
  Date/Author: 2026-02-18 / Codex.

- Decision: Add explicit opt-in mixed-tolerant read mode to `wepp_inputs` (`tolerate_mixed=True, mixed_prefer="archive"`) and use it only in read-only watershed prep probes (`_prep_channel_slopes`, `_prep_structure`).
  Rationale: Keeps canonical mixed-state errors as default behavior while allowing deterministic archive-first reads in targeted reliability-critical read stages.
  Date/Author: 2026-02-18 / Codex.

- Decision: For next implementation wave, make canonical root projection sessions (`WD/<root>`) the default for path-heavy archive-backed consumers, with file-level materialization retained as explicit compatibility fallback.
  Rationale: Projection sessions keep legacy path semantics while preserving archive authority and explicit commit boundaries; this avoids direct writable zip risks and reduces per-file cache churn.
  Date/Author: 2026-02-18 / Codex.

- Decision: Apply Phase 6 document updates as contract-transition addenda instead of rewriting historical execution evidence.
  Rationale: Preserves auditability of Phase 6 results while clearly marking superseded thaw/freeze wording for Phase 9+ implementation.
  Date/Author: 2026-02-18 / Codex.

## Outcomes & Retrospective

Phase 8 implementation remains complete with required milestones/artifacts and validation gates satisfied, with additional post-deploy hardening to prevent mixed-state retry failures via run-entry preflight recovery (`run_wepp_rq`, `run_wepp_noprep_rq`, `run_wepp_watershed_rq`) while keeping read-only prep stages non-mutating, adopting archive-authoritative mixed-state repair to avoid overwriting good `.nodir` archives with partial thawed trees, and keeping disturbed pmet soil-texture reads archive-safe.

A follow-on strategy pivot is now documented: Phase 9 utility-first canonical root projection adoption (`WD/<root>` projected sessions with overlay-backed mutation commits) to replace high-fanout per-file materialization patterns and stale thaw/freeze-era mutation wording.

## Context and Orientation

Phase 7 is complete; Phase 8 is marked complete in `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md` with post-deploy remediation notes.

Phase 8 scope is concentrated in:
- Runtime read behavior: `wepppy/nodb/core/wepp.py`
- RQ stage wrappers: `wepppy/rq/wepp_rq.py`
- NoDir read/materialize primitives: `wepppy/nodir/fs.py`, `wepppy/nodir/materialize.py`, `wepppy/nodir/mutations.py`

Contract references:
- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/schemas/rq-response-contract.md`

Phase 8 required artifacts:
- `docs/work-packages/20260214_nodir_archives/artifacts/wepp_nodir_read_touchpoints_phase8a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase8_wepp_nodir_perf_results.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase8_wepp_nodir_reliability_runbook.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase8_wepp_nodir_refactor_review.md`

## Plan of Work

### Milestone 0: Inventory + Baseline

Create a Phase 8A inventory of WEPP prep read touchpoints and classify each path read as archive-native, materialize-file, or refactor-required. Capture baseline reliability/perf observations for current wrapper-heavy behavior and document exact measurement method.

### Milestone 1: WEPP Inputs Helper

Add `wepppy/nodir/wepp_inputs.py` with narrow helper APIs for WEPP prep read patterns: archive/dir open, explicit copy-to-destination, constrained listing/glob helper for known WEPP patterns, and explicit materialization passthrough. Add `tests/nodir/test_wepp_inputs.py` covering dir-form, archive-form, and canonical NoDir errors.

### Milestone 2: `wepp.py` Refactor

Refactor WEPP prep methods listed in Phase 8 to use the helper and remove direct assumptions that `WD/landuse`, `WD/soils`, `WD/watershed` always exist as directories. Keep output paths in `wepp/runs` and `wepp/output` unchanged.

### Milestone 3: RQ Wrapper Simplification

Update read-only prep stages in `wepppy/rq/wepp_rq.py` to call WEPP prep directly once read paths are archive-native. Retain mutation wrappers only where a stage actually mutates NoDir roots.

### Milestone 4: Regression Coverage

Update existing RQ NoDir tests and add/adjust WEPP NoDir-focused tests to assert wrapper behavior and archived-root read correctness.

### Milestone 5: Evidence + Runbook Delta

Capture post-refactor reliability/perf evidence and write required artifact docs and rollout/runbook guidance.

### Milestone 6: Validation + Closeout

Run required Phase 8 gates, record exact outcomes, update `implementation_plan.md` Phase 8 status/evidence links, and finalize closeout review.

## Concrete Steps

Run commands from `/workdir/wepppy`.

1. Implement runtime and tests for milestones 1-4.
2. Run required validation gates:

    wctl run-pytest tests/nodir/test_wepp_inputs.py tests/nodb/test_soils_gridded_root_creation.py
    wctl run-pytest tests/rq/test_wepp_rq_nodir.py tests/microservices/test_rq_engine_wepp_routes.py
    wctl run-pytest tests/rq
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260214_nodir_archives

3. Publish artifacts and update implementation plan Phase 8 section.

## Validation and Acceptance

Phase 8 is accepted when all are true:
- WEPP prep reads for `landuse`/`soils`/`watershed` work for archive-backed roots without root thaw/freeze.
- Read-only RQ prep stages no longer use mutation wrappers solely for reads.
- Required artifacts are complete with before/after method notes and reliability outcomes.
- Required pytest/doc-lint gates pass.
- `implementation_plan.md` marks Phase 8 complete with links to evidence.

## Idempotence and Recovery

- Helper and call-site refactors are additive and can be rerun/retested safely.
- If regressions appear, rollback is limited to Phase 8 files (`wepp_inputs.py`, `wepp.py`, `wepp_rq.py`, related tests/docs) and does not require changing NoDir state-machine contracts.

## Artifacts and Notes

Phase 8 required outputs:
- `docs/work-packages/20260214_nodir_archives/artifacts/wepp_nodir_read_touchpoints_phase8a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase8_wepp_nodir_perf_results.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase8_wepp_nodir_reliability_runbook.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase8_wepp_nodir_refactor_review.md`

## Interfaces and Dependencies

The implementation must preserve canonical NoDir/RQ contracts:
- NoDir resolve/open/materialization behavior from `wepppy/nodir/fs.py` and `wepppy/nodir/materialize.py`.
- NoDir mutation/lock semantics in `wepppy/nodir/mutations.py` and thaw/freeze contracts.
- Error/status payload constraints in `docs/schemas/rq-response-contract.md`.

The new helper should consume existing NoDir APIs rather than bypassing them with ad hoc archive handling.

---
Change note (2026-02-17 / Codex): initial Phase 8 ExecPlan authored to execute milestones 0-6 with required artifacts, validation gates, and completion criteria.
Change note (2026-02-17 / Codex): updated Milestone 0 completion status and recorded baseline wrapper-overhead findings plus benchmarking decision.
Change note (2026-02-17 / Codex): completed Milestones 1-4 runtime/test refactor work and documented the circular-import fix plus wrapper-removal decision.
Change note (2026-02-17 / Codex): completed Milestones 5-6 including performance/reliability artifact finalization, required validation gates, and implementation-plan closeout.

Change note (2026-02-18 / Codex): post-review remediation addressed management override regression, removed unnecessary channel-slope materialization, expanded touchpoint tests, and re-ran full gates.
Change note (2026-02-18 / Codex): post-deploy hotfix added archive-first soil texture resolution in `_prep_managements` to prevent `Invalid run identifier` failures for archived soils during disturbed overrides.
Change note (2026-02-18 / Codex): removed `_prep_remaining_rq` read-stage mutation wrapper, added `run_wepp_rq` mixed-root recovery freeze, and patched disturbed `pmetpara_prep()`/slope clipping for resilient archive-first retries after mixed-state failures.
Change note (2026-02-18 / Codex): corrected watershed mixed-state handling by moving preflight recovery from `_prep_watershed_rq` to `run_wepp_watershed_rq`, keeping prep stage read-only while preserving resilience to prior `NODIR_MIXED_STATE` failures.
Change note (2026-02-18 / Codex): switched mixed-root recovery to archive-authoritative dir discard (no freeze overwrite) and added peridot slope legacy-path fallback + regression coverage for missing `slope_files` archives.
Change note (2026-02-18 / Codex): added mixed-tolerant archive-preferred read options to `wepp_inputs` and used them in `_prep_channel_slopes`/`_prep_structure`; legacy channel slope writes now stream from the selected source handle to avoid mixed-state reopen failures.
