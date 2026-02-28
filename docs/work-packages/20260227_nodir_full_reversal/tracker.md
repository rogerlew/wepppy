# Tracker – NoDir Full Reversal (Abandonment Program)

> Living document tracking status, decisions, risks, and handoff notes for NoDir rollback.

## Quick Status

**Started**: 2026-02-27  
**Current phase**: Phase 8 complete (Phases 1-7 complete)  
**Last updated**: 2026-02-28 04:52Z  
**Next milestone**: none (Phase 8 closeout complete).
**Implementation plan**: `docs/work-packages/20260227_nodir_full_reversal/prompts/completed/phase8_root_resource_unroll_batch_migration_execplan.md`

## Task Board

### Ready / Backlog
- [ ] (none)

### In Progress
- [ ] (none)

### Blocked
- [ ] (none)

### Done
- [x] Phase 8 (Phase 7): completed closeout/documentation updates, published final verification artifact, and closed mandatory subagent loop with unresolved high/medium = 0 (2026-02-28)
- [x] Phase 8 (Phase 6): executed approved wepp1 apply in container context (`--roots /wc1/runs,/wc1/batch`), copied `/tmp` apply artifacts to package artifacts, and published conflict/error verification report (`phase8_wepp1_apply_*`) (2026-02-28)
- [x] Phase 8 (Phase 5): explicit human approval recorded for wepp1 apply (`phase8_wepp1_approval.md`) (2026-02-28)
- [x] Phase 8 (Phase 4): executed wepp1 dry-run inventory using container root mapping (`/wc1/runs,/wc1/batch`) and published approval packet with real counts/conflict ledger (`phase8_wepp1_dry_run_*`, `phase8_wepp1_approval_packet.md`) (2026-02-28)
- [x] Phase 8 (partial): completed Phases 1-3 with migration script + tests, forest dry-run/apply artifacts, validation gates, and conflict ledger publication (`phase8_forest_*`, `phase8_validation_log.md`) (2026-02-27)
- [x] Phase 7: Executed root-resource rehome + root-support retirement end-to-end; published required artifacts (`phase7_scope_matrix.md`, `phase7_validation_log.md`, `phase7_subagent_review.md`, `phase7_findings_resolution.md`, `phase7_final_contract_verification.md`), passed required validation gates, and closed mandatory subagent loop with unresolved high/medium = 0 (2026-02-27)
- [x] Refined Phase 7 planning to include complete root-resource scope and additional implementation surfaces (`return_periods`, `run_sync_rq`, `skeletonize`, `omni`) and rewrote active ExecPlan for end-to-end execution fidelity (2026-02-27)
- [x] Authored Phase 7 root-resource rehome planning artifacts and active ExecPlan (`artifacts/phase7_root_resource_inventory.md`, `artifacts/phase7_apply_nodir_false_migration_spec.md`, `prompts/completed/nodir_full_reversal_execplan.md`) (2026-02-27)
- [x] Phase 6: Executed final closeout validation scope, published Phase 6 artifacts, resolved mandatory subagent high/medium findings to zero, and closed package/project tracking surfaces (2026-02-27)
- [x] Phase 5: Removed NoDir-only test surfaces, updated mixed-suite coverage to directory-only behavior, retired NoDir contract/schema docs, retired superseded active prompts, passed Step 5 validation gates, and closed mandatory subagent loop with zero unresolved high/medium findings (2026-02-27)
- [x] Authored active Phase 6 end-to-end ExecPlan for final rollback validation, verification artifact publication, and package/project closeout (`prompts/completed/nodir_full_reversal_execplan.md`) (2026-02-27)
- [x] Phase 4: Removed runtime `wepppy.nodir` package/integrations, retired carryover guards, passed required validation gates, and closed mandatory subagent findings loop with zero unresolved high/medium findings (2026-02-27)
- [x] Authored active Phase 5 end-to-end ExecPlan for NoDir test/contract/docs cleanup with mandatory subagent findings closure (`prompts/completed/nodir_full_reversal_execplan.md`) (2026-02-27)
- [x] Phase 3: Executed run-data rollback from `.nodir` roots with policy lock, rollback tooling updates, canary/bulk evidence artifacts, and mandatory subagent closure loop (2026-02-27)
- [x] Authored active Phase 4 end-to-end ExecPlan for runtime NoDir package removal and Phase 3 guard carryover retirement (`prompts/completed/nodir_full_reversal_execplan.md`) (2026-02-27)
- [x] Phase 2: Disabled new NoDir creation defaults and replaced Phase 2 mutation entrypoints with directory-only guard/lock behavior; mandatory subagent findings loop closed with zero unresolved high/medium findings (2026-02-27)
- [x] Authored active Phase 3 end-to-end ExecPlan for `.nodir` rollback, guard-policy disposition, and subagent findings closure (`prompts/completed/nodir_full_reversal_execplan.md`) (2026-02-27)
- [x] Created rollback work-package scaffold (`package.md`, `tracker.md`, active ExecPlan placeholder) (2026-02-27)
- [x] Marked prior NoDir package as canceled/superseded by this rollback package (2026-02-27)
- [x] Authored active Phase 1 end-to-end ExecPlan for inventory/classification/freeze handoff (`prompts/completed/nodir_full_reversal_execplan.md`) (2026-02-27)
- [x] Completed Phase 1 inventory/classification/handoff artifacts and phase state update (`artifacts/*`, active ExecPlan progress sections) (2026-02-27)
- [x] Authored active Phase 2 end-to-end ExecPlan with mandatory subagent review and findings-resolution workflow (`prompts/completed/nodir_full_reversal_execplan.md`) (2026-02-27)

## Timeline

- **2026-02-27** – Package created and rollback charter established.
- **2026-02-27** – Supersession of prior NoDir initiative recorded.
- **2026-02-27** – Active ExecPlan narrowed to Phase 1 end-to-end execution with artifact contract and acceptance checks.
- **2026-02-27** – Phase 1 artifacts published: inventory, matrix, subsystem summary, and handoff.
- **2026-02-27** – Active ExecPlan advanced to Phase 2 implementation with subagent review and findings-resolution gates.
- **2026-02-27** – Phase 2 executed end-to-end; required artifacts, validation gates, and subagent closure loop completed.
- **2026-02-27** – Active ExecPlan advanced to Phase 3 run-data rollback with policy lock and findings-resolution gates.
- **2026-02-27** – Phase 3 executed end-to-end with rollback tooling updates, canary/bulk audits, guard disposition records, validation gates, and subagent high/medium closure.
- **2026-02-27** – Active ExecPlan advanced to Phase 4 runtime-removal scope with Phase 3 carryover guard retirement requirements.
- **2026-02-27** – Phase 4 executed end-to-end: runtime `wepppy.nodir` removal, carryover guard retirement, required validation passes, and mandatory subagent high/medium closure.
- **2026-02-27** – Active ExecPlan advanced to Phase 5 cleanup scope for NoDir test/contract/docs retirement.
- **2026-02-27** – Phase 5 executed end-to-end with required artifacts, docs/contract retirement, validation gates, and subagent high/medium closure.
- **2026-02-27** – Active ExecPlan advanced to Phase 6 full closeout validation and package closure scope.
- **2026-02-27** – Phase 6 completed end-to-end; final rollback verification published and package moved to complete status.
- **2026-02-27** – Phase 7 planning refined with comprehensive root-sidecar scope lock and expanded implementation surfaces to prevent hidden fallback residue.
- **2026-02-27** – Phase 7 executed end-to-end: retired runtime root fallback support, rehomed producers to canonical directories, enforced migration-required boundaries, passed all required validation gates, and closed mandatory subagent loop with unresolved high/medium = 0.
- **2026-02-27** – Phase 8 Phases 1-3 executed end-to-end with new batch migration tooling, forest dry-run/apply artifacts, and full validation-gate pass; Phase 4 blocked by missing wepp1 host roots (`/geodata/wc1/runs`, `/geodata/wc1/batch`).
- **2026-02-28** – Phase 8 Phase 4 completed after confirming container path mapping (`/wc1 -> /geodata/wc1`) and executing wepp1 dry-run with real inventory outputs and approval packet updates.
- **2026-02-28** – Phase 8 Phase 6 completed: wepp1 apply executed with approval gate artifact, apply audit/summary copied from container `/tmp`, conflict/error ledgers verified, and Phase 6 status advanced while leaving Phase 7 closeout pending.
- **2026-02-28** – Phase 8 Phase 7 closeout completed: active ExecPlan and tracker marked complete, Phase 8 final verification artifact published, and subagent closeout loop revalidated with unresolved high/medium = 0.

## Decisions

### 2026-02-27: Full NoDir abandonment is the target state
**Context**: Product direction changed; team wants NoDir removed instead of stabilized.

**Decision**: Treat this as a full rollback program, not a partial compatibility effort.

**Impact**: Implementation prioritizes removal/reversion over incremental support.

---

### 2026-02-27: Historical Git commits remain intact
**Context**: “Pretend it never existed” could imply history rewrite, which is operationally risky.

**Decision**: Do not rewrite Git history in this package. Roll back runtime/docs/test surfaces to a NoDir-free active state.

**Impact**: Repository history remains auditable while live behavior returns to directory-only semantics.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Existing runs contain only `.nodir` roots and fail after code rollback | High | High | Phase 3 run-data rollback before hard code removal | Mitigated (Phase 3 complete) |
| Hidden NoDir dependencies cause late regressions | High | Medium | Inventory-first rollback with targeted and full gates | Mitigated (Phase 4-8 validation complete) |
| Queue/job flows drift during rollback | High | Medium | Validate critical RQ routes and update dependency catalog if edges change | Mitigated (RQ graph + suite checks passed) |
| Docs/contracts mismatch after cancellation | Medium | Medium | Single-source status updates in package + tracker + project board | Mitigated (Phase 7 closeout sync complete) |
| Residual manual resolution for explicit migration conflicts/config errors | Medium | Medium | Track operator follow-up ledger in `artifacts/phase8_final_verification.md` | Open |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests --maxfail=1`
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- [x] `python3 tools/code_quality_observability.py --base-ref origin/master`

### Documentation
- [x] `wctl doc-lint --path docs/work-packages/20260227_nodir_full_reversal`
- [x] `wctl doc-lint --path docs/work-packages/20260214_nodir_archives`
- [x] `wctl doc-lint --path PROJECT_TRACKER.md`
- [x] `wctl doc-lint --path docs/schemas`

### Rollback Validation
- [x] Existing `\.nodir` rollback procedure validated with repeatable canary/bulk restore tooling and audit artifacts (`phase3_migration_summary.md`, `phase3_bulk_*_audit.jsonl`, `phase3_quarantined_runs.md`, `phase4_quarantine_disposition.md`).
- [x] New run creation verified to enforce directory-only defaults (`phase2_execution_log.md`, `phase6_final_rollback_verification.md`).
- [x] Runtime browse/files/download and related active paths validated directory-only after NoDir package removal (`phase6_structural_assertions.md`, `phase6_nodir_import_scan.txt`, `phase6_validation_log.md`).

## Progress Notes

### 2026-02-28: Post-closeout documentation hygiene
**Agent/Contributor**: Codex

**Work completed**:
- Updated `package.md` completion metadata and summary artifacts to Phase 8 final closeout state.
- Moved completed ExecPlans from `prompts/active/` to `prompts/completed/` and synchronized references.
- Updated `phase8_wepp1_approval_packet.md` wording to explicit historical/post-apply context while preserving gate-time evidence content.

**Next steps**:
- None; documentation closeout hygiene complete.

### 2026-02-28: Phase 8 Phase 7 closeout complete
**Agent/Contributor**: Codex

**Work completed**:
- Marked Phase 7 complete in the active Phase 8 ExecPlan and synchronized living sections/outcomes.
- Published Phase 8 closeout artifact `phase8_final_verification.md` with acceptance checks, command ledger summary, and residual follow-up ledger.
- Updated package tracker status to Phase 8 complete and synchronized task board/timeline entries.
- Re-ran package doc lint and mandatory closeout subagent loop (`reviewer`, `test_guardian`) to confirm unresolved high/medium findings remain zero.

**Next steps**:
- None for Phase 8 within this work-package.

### 2026-02-28: Phase 8 Phase 6 execution complete
**Agent/Contributor**: Codex

**Work completed**:
- Executed wepp1 apply command with required approval gate artifact and container root mapping (`/wc1/runs,/wc1/batch`).
- Persisted Phase 6 apply outputs by copying container `/tmp` artifacts into package artifacts:
  - `phase8_wepp1_apply_audit.jsonl`
  - `phase8_wepp1_apply_summary.json`
  - `phase8_wepp1_apply_report.md`
- Verified outcomes and ledgers:
  - run-status counts: `ok=0`, `conflict_requires_manual_resolution=2`, `error=3`, `skipped=1848`
  - conflict runs: `ill-taco`, `real-time-preserver` (both soils hash mismatch)
  - run-error reason: missing cfg `/workdir/wepppy/wepppy/nodb/configs/ext-disturbed9002.cfg` (`3` runs)
- Reconciled prior Phase 4 dry-run snapshot drift with a same-root post-apply dry-run (`1858` discovered, `2` eligible, `2` predicted conflicts, `3` run errors) to confirm Phase 6 apply scope on current `/wc1` data.
- Passed required Phase 6 validation gates plus additional doc-lint gates (`docs/schemas`, `PROJECT_TRACKER.md`) to satisfy full active ExecPlan gate set.

**Next steps**:
- Execute Phase 7 closeout scope only (final package closeout artifacts and status publication).

### 2026-02-27: Phase 8 Phases 1-4 execution attempt
**Agent/Contributor**: Codex

**Work completed**:
- Implemented `wepppy/tools/migrations/unroll_root_resources_batch.py` with host/mode CLI gates, apply-nodir filtering, conflict-safe/idempotent actions, audit JSONL + summary JSON outputs, and wepp1 approval enforcement for apply mode.
- Added targeted unit tests in `tests/tools/test_migrations_unroll_root_resources_batch.py`.
- Published required Phase 8 artifacts for forest dry-run/apply and wepp1 dry-run/approval packet.
- Passed required validation gates (`wctl run-pytest tests --maxfail=1`, `check_broad_exceptions`, `code_quality_observability`, `wctl check-rq-graph`, package doc lint).

**Status update**:
- Initial Phase 4 blocker was resolved after confirming wepp1 container path mapping (`/wc1 -> /geodata/wc1`) and rerunning dry-run with `--roots /wc1/runs,/wc1/batch`.
- Phase 4 is complete; next step is Phase 5 explicit human approval for wepp1 apply.

### 2026-02-27: Package initialization
**Agent/Contributor**: Codex

**Work completed**:
- Created rollback package scaffold.
- Drafted detailed active ExecPlan for multi-phase NoDir reversal.
- Updated package/tracker metadata to mark NoDir initiative as superseded.

**Next steps**:
- Begin Phase 1 inventory command run and publish artifact.
- Land Phase 2 kill-switch edits for new run creation and marker writes.

### 2026-02-27: Phase 1 ExecPlan finalization
**Agent/Contributor**: Codex

**Work completed**:
- Reviewed package docs and current active plan.
- Rewrote `prompts/completed/nodir_full_reversal_execplan.md` as a Phase 1-only end-to-end execution plan.
- Added explicit artifact contracts, taxonomy validation checks, and tracker update requirements for Phase 1 handoff.

**Next steps**:
- Run the Phase 1 inventory and classification steps exactly as specified in the active ExecPlan.
- Publish `phase1_classification_matrix.csv`, `phase1_subsystem_summary.md`, and `phase1_handoff.md`.

### 2026-02-27: Phase 1 execution complete
**Agent/Contributor**: Codex

**Work completed**:
- Generated `artifacts/nodir_reference_inventory.txt` and `artifacts/nodir_reference_files.txt` from deterministic `rg` inventory commands.
- Produced `artifacts/phase1_reference_counts.txt` and complete `artifacts/phase1_classification_matrix.csv` with action/phase/priority/blocker/test metadata for all 130 files.
- Published `artifacts/phase1_subsystem_summary.md` and `artifacts/phase1_handoff.md` including first-PR Phase 2 cut line and unresolved blocker decisions.
- Updated active ExecPlan living sections (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`).
- Passed all Phase 1 validation/acceptance commands including package doc lint (`5 files validated, 0 errors, 0 warnings`).

**Next steps**:
- Execute Phase 2 first PR scope from `artifacts/phase1_handoff.md`.
- Resolve blocker decisions keyed in `phase1_classification_matrix.csv` before Phase 3/4 boundary edits.

### 2026-02-27: Phase 1 audit findings resolved
**Agent/Contributor**: Codex

**Work completed**:
- Aligned task board state so Phase 2 appears only under `In Progress` and not duplicated in `Ready / Backlog`.
- Expanded `Blocked` list to the five explicit human decision keys from the Phase 1 matrix/handoff with row counts and policy intent.

**Next steps**:
- Keep blocker decisions synchronized across tracker, handoff, and matrix as they are resolved.

### 2026-02-27: Phase 2 ExecPlan authoring
**Agent/Contributor**: Codex

**Work completed**:
- Replaced the completed Phase 1 active plan with a Phase 2 execution plan scoped to all 19 `target_phase=2` rows.
- Added explicit Wave A / Wave B sequencing, validation gates, and conditional RQ graph checks per repository contract.
- Added mandatory subagent review (`reviewer`, `test_guardian`) and findings-resolution loop as phase completion criteria.

**Next steps**:
- Execute the Phase 2 plan end-to-end and publish `phase2_scope.csv`, `phase2_subagent_review.md`, and `phase2_findings_resolution.md`.
- Keep high/medium findings at zero unresolved before marking Phase 2 complete.

### 2026-02-27: Phase 2 execution complete
**Agent/Contributor**: Codex

**Work completed**:
- Executed all 19 Phase 2 matrix targets and kept scope locked to `target_phase=2` rows.
- Published Phase 2 artifacts: `phase2_scope.csv`, `phase2_execution_log.md`, `phase2_subagent_review.md`, `phase2_findings_resolution.md`.
- Ran mandatory subagent review workflow (`reviewer`, `test_guardian`) through resolution loop to zero unresolved high/medium findings.
- Re-ran required validation commands (Wave A test command, Phase 2 service suite, `tests/rq`, nodb targeted suite, broad microservices+weppcloud sweep, policy checks, rq-graph drift regen/check, doc lint).

**Next steps**:
- Begin Phase 3 run-data rollback implementation once blocker-policy decisions are finalized.
- Keep tracker blocker keys synchronized as decisions land.

### 2026-02-27: Phase 3 ExecPlan authoring
**Agent/Contributor**: Codex

**Work completed**:
- Replaced the completed Phase 2 active plan with a Phase 3 execution plan scoped to all 18 `target_phase=3` matrix rows.
- Added explicit policy-decision locking, rollback audit artifact contracts, and canary/bulk execution milestones for `.nodir` -> directory conversion.
- Added mandatory subagent review (`reviewer`, `test_guardian`) and findings-resolution loop as phase completion criteria.

**Next steps**:
- Execute Phase 3 plan end-to-end and publish required Phase 3 artifacts.
- Keep blocker decision keys synchronized across tracker, policy decisions artifact, and guard disposition notes.

### 2026-02-27: Phase 3 execution complete
**Agent/Contributor**: Codex

**Work completed**:
- Locked Phase 3 scope to the exact 18 `target_phase=3` rows and published `artifacts/phase3_scope.csv`.
- Published all required Phase 3 artifacts, including policy decisions, canary/bulk audit logs, migration summary, guard disposition, subagent review, findings resolution, and quarantine ledger.
- Extended rollback tooling for restore-mode operations and directory-first parquet helper behavior in Phase 3 replace rows.
- Executed canary and bulk rollback runs via `wctl exec weppcloud ... /opt/venv/bin/python`; final single-pass audit counts were refreshed after truncating appended rerun logs.
- Completed mandatory subagent workflow (`reviewer`, `test_guardian`) and resolved all high/medium findings; rerun status is zero unresolved high/medium findings.
- Passed Phase 3 validation commands: targeted tool tests, microservices browse/diff tests, RQ guard tests, omni tests, `check_broad_exceptions`, `code_quality_observability`, `wctl check-rq-graph`, and package doc lint.

**Next steps**:
- Execute Phase 4 runtime NoDir removal scope while keeping Phase 3 quarantine/readonly evidence available for operations retry planning.
- Preserve Phase 3 artifacts as the baseline evidence set for Phase 4 acceptance/handoff.

### 2026-02-27: Phase 4 ExecPlan authoring
**Agent/Contributor**: Codex

**Work completed**:
- Replaced the completed Phase 3 active plan with a Phase 4 runtime-removal execution plan.
- Locked Phase 4 to all 40 `target_phase=4` matrix rows and explicitly included 14 deferred Phase 3 guard files.
- Added explicit runtime import-removal acceptance gates, quarantine disposition artifact requirement, and mandatory subagent review (`reviewer`, `test_guardian`) with findings-resolution loop.

**Next steps**:
- Execute the Phase 4 plan end-to-end and publish required Phase 4 artifacts.
- Close all high/medium review findings before marking Phase 4 complete.

### 2026-02-27: Phase 4 execution complete
**Agent/Contributor**: Codex

**Work completed**:
- Executed all Phase 4 matrix/carryover scope edits, removed `wepppy/nodir/`, and migrated runtime imports to directory-only runtime path modules.
- Published required Phase 4 artifacts: `phase4_scope.csv`, `phase4_carryover_guard_scope.txt`, `phase4_quarantine_disposition.md`, `phase4_nodir_imports_before.txt`, `phase4_nodir_imports_after.txt`, `phase4_subagent_review.md`, and `phase4_findings_resolution.md`.
- Retired deferred Phase 3 guard behavior in browse/rq/diff/clone surfaces; enforced explicit archive-boundary rejection contracts and replaced skip-heavy legacy tests with directory-only coverage.
- Completed mandatory subagent workflow (`reviewer`, `test_guardian`) through findings-resolution loop; Cycle 2 closed with zero unresolved high/medium findings.
- Passed required Phase 4 validation commands (`tests/nodb`, `tests/rq`, query-engine targets, weppcloud route targets, microservices targets, `check_broad_exceptions`, `code_quality_observability`).

**Next steps**:
- Execute Phase 5 cleanup of remaining NoDir-focused test/docs surfaces not required for active directory-only runtime contracts.
- Execute Phase 6 full closeout validation and publish package-final rollback verification artifact.

### 2026-02-27: Phase 5 ExecPlan authoring
**Agent/Contributor**: Codex

**Work completed**:
- Replaced the completed Phase 4 active plan with a Phase 5 cleanup execution plan.
- Locked Phase 5 scope to all 53 `target_phase=5` matrix rows (`remove=20`, `replace=33`) and added cleanup-manifest/doc-disposition artifact requirements.
- Added explicit cleanup steps for retiring `tests/nodir`, NoDir-only mixed-suite tests, superseded package active prompts, and NoDir schema docs from active contract flow.
- Added mandatory subagent review (`reviewer`, `test_guardian`) with findings-resolution loop as phase completion criteria.

**Next steps**:
- Execute the Phase 5 plan end-to-end and publish required Phase 5 artifacts.
- Close all high/medium findings before marking Phase 5 complete and moving to Phase 6 closeout.

### 2026-02-27: Phase 5 execution complete
**Agent/Contributor**: Codex

**Work completed**:
- Locked Phase 5 scope to matrix `target_phase=5` rows and published `phase5_scope.csv` plus `phase5_cleanup_manifest.md` (`53` rows: `20 remove`, `33 replace`).
- Removed NoDir-only test surfaces (`tests/nodir/`, `test_diff_nodir.py`, `test_wepp_nodir_read_paths.py`, `test_wepp_rq_nodir.py`, `test_migrations_nodir_bulk.py`).
- Updated mixed-suite contract assertions for directory-only fail-fast behavior in `tests/microservices/test_rq_engine_omni_routes.py` and reran targeted suite.
- Retired/archived NoDir docs/contracts: updated scoped READMEs, added archived/deprecated/historical banners to four NoDir schema docs, and retired superseded package prompts from `prompts/active/` to `prompts/completed/canceled_*.md`.
- Published required Phase 5 artifacts: `phase5_docs_contract_disposition.md`, `phase5_subagent_review.md`, `phase5_findings_resolution.md`.
- Passed all required Phase 5 validation gates (pytest sets, quality checks, and doc lint paths).
- Completed mandatory subagent loop (`reviewer`, `test_guardian`) with rerun closure to zero unresolved high/medium findings.

**Next steps**:
- Execute Phase 6 full closeout validation and publish final rollback verification artifact.
- Keep tracker/ExecPlan synchronized through package closure handoff.

### 2026-02-27: Phase 6 ExecPlan authoring
**Agent/Contributor**: Codex

**Work completed**:
- Replaced the completed Phase 5 active plan with a Phase 6 closeout execution plan.
- Defined Phase 6 scope from package success criteria and tracker closeout requirements (matrix `target_phase=6` rows = `0`).
- Added explicit full-gate validation, final rollback verification artifact, and mandatory subagent findings-resolution closure requirements.
- Added package/project closeout update requirements (`tracker.md`, `package.md`, `PROJECT_TRACKER.md`) as completion gates.

**Next steps**:
- Execute the Phase 6 plan end-to-end and publish required Phase 6 artifacts.
- Close all high/medium findings and mark package/project tracking surfaces complete.

### 2026-02-27: Phase 6 execution complete
**Agent/Contributor**: Codex

**Work completed**:
- Published Phase 6 closeout artifacts (`phase6_closeout_scope.md`, `phase6_nodir_import_scan.txt`, `phase6_structural_assertions.md`, `phase6_validation_log.md`, `phase6_final_rollback_verification.md`, `phase6_subagent_review.md`, `phase6_findings_resolution.md`).
- Ran required validation gates including full-suite `wctl run-pytest tests --maxfail=1` pass after resolving one integration fixture regression found during initial run.
- Executed mandatory subagent loop (`reviewer`, `test_guardian`) through fallback in-band packet rerun; final unresolved high/medium findings = 0.
- Updated package/tracker/project status surfaces to completed state and synchronized ExecPlan living sections.

**Next steps**:
- Optional follow-up hardening: add extra negative/edge-case coverage around grouped-runid fixture alias boundaries in `tests/integration/conftest.py`.

### 2026-02-27: Phase 7 planning artifacts authored
**Agent/Contributor**: Codex

**Work completed**:
- Identified comprehensive in-root resource set requiring rehome (`landuse.parquet`, `soils.parquet`, `climate.*.parquet`, `watershed.*.parquet`, `wepp_cli_pds_mean_metric.csv`).
- Published inventory artifact: `artifacts/phase7_root_resource_inventory.md`.
- Published migration specification artifact for follow-on bulk phase targeting `apply_nodir=false` runs: `artifacts/phase7_apply_nodir_false_migration_spec.md`.
- Replaced active ExecPlan with detailed Phase 7 end-to-end refactor plan in `prompts/completed/nodir_full_reversal_execplan.md`.

**Next steps**:
- Execute Phase 7 plan milestone-by-milestone (remove root fallback support, rehome producers, add migration-required fail-fast boundaries, run full validation + mandatory subagent closure loop).

### 2026-02-27: Phase 7 planning refinement (comprehensive scope lock)
**Agent/Contributor**: Codex

**Work completed**:
- Expanded the root-resource inventory to include complete in-scope wildcard classes and explicit known concrete filenames.
- Added additional implementation surfaces to the scope lock (`wepp/reports/return_periods.py`, `rq/run_sync_rq.py`, `nodb/skeletonize.py`, `nodb/mods/omni/omni.py`) to prevent residual root-fallback behavior.
- Upgraded the `apply_nodir=false` migration spec with staged workflow, conflict policy, audit schema, idempotence rules, and explicit postconditions.
- Rewrote the active Phase 7 ExecPlan with milestone-level execution steps, validation gates, artifact contract, and closeout criteria.

**Next steps**:
- Execute Phase 7 implementation milestones using the refined active ExecPlan.
- Preserve `apply_nodir=true` exclusion in migration workflows until a dedicated follow-up phase is chartered.

### 2026-02-27: Phase 7 execution complete
**Agent/Contributor**: Codex

**Work completed**:
- Executed Phase 7 scope lock for retired root resources (`landuse.parquet`, `soils.parquet`, `climate.<name>.parquet`, `watershed.<name>.parquet`, `wepp_cli_pds_mean_metric.csv`) with directory-only runtime contract enforcement.
- Removed runtime/query fallback behavior and rehomed in-scope producers to canonical directory outputs.
- Aligned operational surfaces (`run_sync_rq`, `skeletonize`, `omni` clone paths, helper symlink behavior) and added explicit migration-required fail-fast boundaries.
- Updated docs/contracts to reflect directory-only query/catalog and RQ prerequisite behavior (`wepppy/query_engine/README.md`, `wepppy/rq/job-dependencies-catalog.md`).
- Published required Phase 7 artifacts: `phase7_scope_matrix.md`, `phase7_validation_log.md`, `phase7_subagent_review.md`, `phase7_findings_resolution.md`, `phase7_final_contract_verification.md`.
- Passed required validation gates (`wctl run-pytest tests --maxfail=1`, broad-exception gate, code quality observability, rq-graph check, doc-lint paths).
- Completed mandatory subagent loop (`reviewer`, `test_guardian`) with unresolved high/medium findings = 0.

**Next steps**:
- None required for Phase 7; package remains in completed state pending any new follow-on charter.
