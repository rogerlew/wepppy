# Phase 3 Policy Decisions

## Policy 1
- decision_key: `decide_legacy_archive_browse_window`
- decision: Keep legacy `.nodir` browse/download/diff access boundaries in place for Phase 3 cutover; do not remove runtime compatibility in this phase.
- effective_phase: `3`
- impacted_files:
  - `wepppy/microservices/_gdalinfo.py`
  - `wepppy/microservices/browse/_download.py`
  - `wepppy/microservices/browse/browse.py`
  - `wepppy/microservices/browse/dtale.py`
  - `wepppy/microservices/browse/files_api.py`
  - `wepppy/microservices/browse/flow.py`
  - `wepppy/microservices/browse/listing.py`
  - `wepppy/weppcloud/routes/diff/diff.py`
- rationale: Phase 3 performs data rollback while runs may still be mixed across `.nodir` and directory states. Keeping this boundary avoids operational regressions during canary and bulk conversion. Runtime removal remains Phase 4 scope.

## Policy 2
- decision_key: `decide_mixed_state_recovery_cutoff`
- decision: Retain mixed-state recovery safeguards in RQ workers throughout Phase 3; remove only after rollback evidence confirms no legacy mixed-state runs remain.
- effective_phase: `3`
- impacted_files:
  - `wepppy/rq/omni_rq.py`
  - `wepppy/rq/wepp_rq.py`
  - `wepppy/rq/wepp_rq_stage_helpers.py`
- rationale: Worker entrypoints still encounter legacy runs during migration windows. Recovery guards prevent partial-run failures and preserve queue reliability until Phase 4 runtime cleanup.

## Policy 3
- decision_key: `decide_nodir_cache_handling_during_cutover`
- decision: Keep `.nodir/cache` exclusions in archive/fork paths during Phase 3.
- effective_phase: `3`
- impacted_files:
  - `wepppy/rq/project_rq_archive.py`
  - `wepppy/rq/project_rq_fork.py`
- rationale: `.nodir/cache` artifacts are ephemeral materialization outputs and should not be persisted into archives or cloned workspaces while rollback is active.

## Policy 4
- decision_key: `decide_cli_retention_for_one_time_migration`
- decision: Retain `wepppy/tools/migrations/nodir_bulk.py` as a Phase 3 operations tool, and add explicit restore mode (`--mode restore`) with optional archive removal (`--remove-archive-on-restore`).
- effective_phase: `3`
- impacted_files:
  - `wepppy/tools/migrations/nodir_bulk.py`
  - `tests/tools/test_migrations_nodir_bulk.py`
- rationale: Phase 3 requires deterministic canary/bulk rollback execution with resumable audit logs. Removing the CLI before cutover completion would reduce operator control and evidence quality.

## Policy 5
- decision_key: `decide_clone_support_for_legacy_archive_runs`
- decision: Keep legacy archive-aware clone compatibility through Phase 3; defer removal to Phase 4 after data rollback is complete.
- effective_phase: `3`
- impacted_files:
  - `wepppy/nodb/mods/omni/omni_clone_contrast_service.py`
- rationale: Clone and contrast workflows may still target unconverted runs during migration. Preserving compatibility avoids breakage while bulk restore completes.
