# NoDir Full Reversal (Abandonment Program)

**Status**: Complete (2026-02-28)

## Overview
This package defines a full rollback of NoDir (`.nodir`) from WEPPpy and WEPPcloud. The objective is to return the system to directory-only run-tree semantics (`landuse/`, `soils/`, `climate/`, `watershed/`) and retire all NoDir runtime, API, schema, and workflow assumptions.

This package intentionally prioritizes complete reversal over compatibility retention. Any residual operational fallout is treated as follow-up work after the rollback lands.

## Objectives
- Stop creating new NoDir artifacts for all new runs.
- Convert existing `.nodir` roots back to canonical directory form.
- Remove NoDir code paths from runtime modules and queue workers.
- Remove NoDir-specific tests, contracts, and docs from active surfaces.
- Close/supersede NoDir work packages so execution ownership is unambiguous.

## Scope

### Included
- Runtime rollback across `wepppy/microservices/**`, `wepppy/rq/**`, `wepppy/nodb/**`, and related helpers that reference NoDir.
- Data rollback tooling and procedure for existing runs containing `.nodir` roots.
- Test-suite rollback for `tests/nodir/**` and NoDir-focused assertions elsewhere.
- Documentation rollback for active contracts and work-package status.
- Tracker updates (`PROJECT_TRACKER.md`, package trackers) to mark NoDir initiatives as canceled/superseded.

### Explicitly Out of Scope
- Rewriting Git history to erase all evidence of prior NoDir work.
- Post-rollback feature hardening or optimization unrelated to removing NoDir.
- Broad redesign of run storage beyond restoring directory-only behavior.

## Stakeholders
- **Primary**: Roger
- **Reviewers**: Ops + maintainers of browse/rq-engine/NoDb surfaces
- **Informed**: Contributors working in `wepppy/nodb`, `wepppy/rq`, `wepppy/microservices`, and docs/work-packages

## Success Criteria
- [x] New run creation no longer seeds NoDir defaults or `.nodir` policy markers.
- [x] Existing `.nodir` roots can be reverted to directory form with a repeatable rollback command sequence.
- [x] NoDir runtime package (`wepppy/nodir/`) and its call sites are removed or inert with explicit failures.
- [x] NoDir-specific tests and contracts are removed or archived from active validation flow.
- [x] `wctl run-pytest tests --maxfail=1` passes after rollback.
- [x] Work-package and tracker surfaces clearly show NoDir effort as canceled/superseded.

## Completion Summary
- Final package closeout verification artifact: `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_final_verification.md`
- Final rollback validation evidence: `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_validation_log.md`
- Final rollback subagent closure evidence: `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_subagent_review.md`, `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_findings_resolution.md`
- Post-closeout cleanup evidence: `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase9_cleanup_report.md`, `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase9_validation_log.md`, `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase9_subagent_review.md`, `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase9_findings_resolution.md`
- Final execution plan records: `docs/work-packages/20260227_nodir_full_reversal/prompts/completed/phase8_root_resource_unroll_batch_migration_execplan.md`, `docs/work-packages/20260227_nodir_full_reversal/prompts/completed/phase9_vestigial_complexity_cleanup_execplan.md`

## Dependencies

### Prerequisites
- Operational window for run-tree migration where rollback tooling can safely mutate run roots.
- Agreement that compatibility breakage for residual NoDir artifacts is acceptable during transition.

### Blocks
- Any future storage strategy work is blocked until this rollback lands and baseline directory semantics are stable again.

## Related Packages
- **Supersedes**: [20260214_nodir_archives](../20260214_nodir_archives/package.md)
- **Related**: [20260223_project_config_nodir_policy](../../mini-work-packages/20260223_project_config_nodir_policy.md)

## Timeline Estimate
- **Expected duration**: 3-7 days (multi-PR)
- **Complexity**: High
- **Risk level**: High (storage and queue workflow rollback)

## References
- `wepppy/nodir/` - NoDir runtime package to retire.
- `tests/nodir/` - NoDir-specific test suite to retire.
- `docs/work-packages/20260214_nodir_archives/` - superseded implementation history.
- `docs/schemas/nodir-contract-spec.md` - contract to deprecate/archive.
- `PROJECT_TRACKER.md` - package lifecycle and status board.

## Deliverables
- Rollback ExecPlan with phase-by-phase execution and validation gates.
- Updated package/tracker docs marking NoDir abandoned and superseded.
- Final package verification artifact published at `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_final_verification.md`.
- Post-closeout Phase 9 cleanup artifact published at `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase9_cleanup_report.md`.
