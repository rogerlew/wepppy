# Disturbed Lookup Hardening and Preservation

**Status**: Closed (2026-03-26, reopened addendum completed)

## Overview
This work package hardens disturbed lookup CSV persistence so user-edited values are not silently lost after UI edits, follow-on build operations, or scope mismatches. The package focuses on safe persistence semantics, stale-page/double-submit safeguards, schema upgrade behavior, and regression coverage for disturbed lookup save/read/build flows.

## Objectives
- Preserve user-defined disturbed lookup modifications across save, landuse/soils build, and WEPP prep paths.
- Detect stale editor pages, lock edits when stale, and provide explicit reload/refresh recovery actions.
- Prevent duplicate submissions from in-flight save interactions.
- Eliminate silent destructive save behavior from malformed or partial payloads.
- Keep `?pup` compatibility and ensure disturbed lookup editor reads and writes within the same run scope.
- Add independent subagent code review and QA review artifacts as closure gates.

## Scope
Implements backend and editor hardening in disturbed lookup save/read paths, adds schema-upgrade safeguards, and updates tests/docs/work-package artifacts.

### Included
- Disturbed lookup writer validation and atomic persistence safeguards.
- Disturbed lookup schema upgrade behavior tuned to avoid losing user edits.
- Disturbed editor CSV load/save scope alignment while keeping `?pup` support.
- Disturbed editor stale polling, lockout controls, and in-flight save lock behavior.
- Extended lookup export behavior updated to avoid clobbering editable lookup source.
- Regression tests for disturbed lookup persistence behavior.
- Subagent code and QA review artifacts with findings closure.

### Explicitly Out of Scope
- Removing `?pup` from the platform.
- Broad rq-engine pup/composite runid redesign beyond disturbed lookup hardening.
- Unrelated disturbed/baer raster workflows.

## Stakeholders
- **Primary**: WEPPcloud users editing disturbed parameters.
- **Reviewers**: AI coding agent + subagent reviewer (`reviewer`) + subagent QA reviewer (`qa_reviewer`).
- **Informed**: Maintainers of `wepppy/nodb/mods/disturbed` and `wepppy/weppcloud/routes/nodb_api`.

## Success Criteria
- [x] Disturbed lookup save endpoint rejects malformed payloads and does not truncate persisted data.
- [x] Disturbed lookup save endpoint enforces optimistic concurrency (`if_match_sha256`) and blocks stale overwrites.
- [x] Disturbed editor marks stale pages, locks editing, and provides \"Load Current Table\" and \"Refresh Page\" recovery controls.
- [x] Disturbed editor save flow blocks in-flight duplicate submission interactions.
- [x] User-edited disturbed lookup values persist after `build_landuse`, `build_soils`, and disturbed pmet prep flows.
- [x] Extended lookup generation no longer overwrites the editable disturbed lookup CSV.
- [x] Disturbed lookup editor read/write operates on a consistent scope and preserves `?pup` behavior.
- [x] Targeted regression suites pass.
- [x] Subagent code review and QA review artifacts are recorded and medium/high findings are resolved.

## Dependencies

### Prerequisites
- Existing disturbed route/controller and disturbed NoDb module behavior.
- Existing tests under `tests/weppcloud/routes/test_disturbed_bp.py`.

### Blocks
- None.

## Related Packages
- **Related**: `docs/work-packages/20260124_sbs_map_refactor/`
- **Related**: `docs/work-packages/20260224_weppcloud_csrf_rollout/`

## Timeline Estimate
- **Expected duration**: Single end-to-end implementation session.
- **Complexity**: Medium.
- **Risk level**: Medium.

## References
- `wepppy/nodb/mods/disturbed/disturbed.py` - Disturbed lookup read/write/migration logic.
- `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` - Disturbed editor and save endpoints.
- `wepppy/weppcloud/templates/controls/edit_csv.htm` - Disturbed lookup editor UI.
- `wepppy/weppcloud/utils/helpers.py` - `url_for_run` scope behavior.
- `docs/prompt_templates/codex_exec_plans.md` - ExecPlan standard.

## Deliverables
- Active ExecPlan + tracker updates.
- Disturbed lookup hardening code changes.
- Regression tests covering save/build persistence and scope-safe editor behavior.
- Subagent review artifacts (code + QA).

## Follow-up Work
- Evaluate broader browse/rq-engine scope unification for non-omni `pup` flows.

## Closure Notes
- Disturbed lookup writes now enforce strict row-shape validation, duplicate-key rejection, and a complete-table guard that blocks partial payload truncation.
- Disturbed lookup writes now enforce optimistic concurrency preconditions (`if_match_sha256`) and return explicit stale/version-unavailable contracts.
- Legacy lookup schema upgrades are now additive/idempotent while preserving readability for `disturbed_class`/`texid` legacy rows.
- Extended lookup generation now writes to `disturbed_land_soil_lookup_extended.csv` and no longer clobbers editable lookup data.
- Editor CSV column definitions are now header-driven (supports current 18-column schema without truncation assumptions).
- Editor now loads CSV+hash snapshot atomically, polls for stale updates, locks edits when stale, and disables in-flight save editing.
- `?pup` compatibility was preserved by keeping editor CSV download on the existing `download.download_with_subpath` route family.
- Subagent findings were captured and closed:
  - `artifacts/code_review_findings.md`
  - `artifacts/qa_review_findings.md`
