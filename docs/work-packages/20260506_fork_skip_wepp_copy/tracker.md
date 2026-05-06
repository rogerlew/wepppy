# Tracker - Fork Copy Optimization for `wepp/runs` and `wepp/output`

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-06 21:06 UTC  
**Current phase**: Completed for this session  
**Last updated**: 2026-05-06 21:20 UTC  
**Next milestone**: Handoff / user confirmation  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog

- [ ] Optional follow-up: add explicit fork-console route/template test for route->dataset->JS default propagation.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Work-package request accepted and scoped from user request (2026-05-06 21:06 UTC).
- [x] Package scaffold + active ExecPlan creation (2026-05-06 21:08 UTC).
- [x] Implemented fork-console/UI payload + rq-engine + worker skip wiring for `skip_wepp_runs_output` (2026-05-06 21:13 UTC).
- [x] Added helper behavior to ensure destination `wepp/runs` and `wepp/output` directories exist when skip mode is active (2026-05-06 21:13 UTC).
- [x] Updated schema-default endpoint metadata/defaults and fork architecture docs (2026-05-06 21:14 UTC).
- [x] Targeted tests passed (`90 passed`) for RQ helper and rq-engine schema/route paths (2026-05-06 21:14 UTC).
- [x] `wctl check-rq-graph` drift resolved and artifacts regenerated; verification passed (2026-05-06 21:15 UTC).
- [x] Doc lint passed for package docs, tracker, and UI doc updates (2026-05-06 21:15 UTC).
- [x] Subagent review passes completed and disposition artifact captured (2026-05-06 21:20 UTC).
- [x] Post-disposition focused validation passed (`96 passed`) (2026-05-06 21:20 UTC).

## Timeline

- **2026-05-06 21:06 UTC** - Package initialized with scope, tracker, and active ExecPlan.
- **2026-05-06 21:13 UTC** - UI/API/worker implementation landed for `skip_wepp_runs_output`.
- **2026-05-06 21:14 UTC** - Focused regression suite passed (`90 passed`).
- **2026-05-06 21:15 UTC** - RQ graph artifacts regenerated and verified up to date.
- **2026-05-06 21:20 UTC** - Review findings remediated; disposition artifact published; focused suite re-run (`96 passed`).

## Decisions Log

### 2026-05-06 21:06 UTC: Add an explicit user-facing skip toggle while preserving undisturbify optimization

**Context**: Operators want an explicit fork optimization for heavy WEPP directories and confirmation that undisturbify already benefits.

**Options considered**:
1. Keep optimization hidden and undisturbify-only.
2. Add UI toggle but skip API/schema updates.
3. Add full UI->API->worker flag with default false and explicit tests.

**Decision**: Option 3.

**Impact**: Users gain explicit control, API behavior remains backward-compatible, and regression coverage protects route/worker contracts.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Boolean argument wiring mismatch between route and worker | Medium | Medium | Add explicit route enqueue assertion tests | Mitigated |
| Skipped directories not created in destination | Medium | Medium | Add helper test for directory guarantee | Mitigated |
| Schema defaults docs drift from runtime behavior | Low | Medium | Update schema-default descriptor/defaults and assert in tests | Mitigated |

## Verification Checklist

### Code and Tests

- [x] `tests/rq/test_project_rq_fork.py` targeted cases pass.
- [x] `tests/microservices/test_rq_engine_fork_archive_routes.py` targeted cases pass.
- [x] `tests/microservices/test_rq_engine_schema_defaults_routes.py` targeted checks pass.
- [x] No existing fork tests regress.

### Documentation

- [x] `docs/ui-docs/weppcloud-project-forking.md` updated for new option and payload key.
- [x] Tracker + ExecPlan progress/decision logs updated at handoff.
- [x] Disposition artifact written: `artifacts/20260506_subagent_review_disposition.md`.

## Progress Notes

### 2026-05-06 21:06 UTC: Package Setup

**Agent/Contributor**: Codex

**Work completed**:
- Created package directory and scaffold files.
- Captured initial scope, risks, and decision baseline.
- Created active ExecPlan stub for implementation execution.

**Blockers encountered**:
- None.

**Next steps**:
- Implement the code changes and tests.
- Run focused validations.
- Execute subagent review passes and disposition.

**Test results**: Not run yet.

### 2026-05-06 21:15 UTC: Implementation + Validation Complete

**Agent/Contributor**: Codex

**Work completed**:
- Added fork-console checkbox and form payload field `skip_wepp_runs_output`.
- Added rq-engine route payload parsing and queue argument propagation for the new flag.
- Extended `fork_rq`/`prepare_fork_run` signatures and copy logic so skip mode excludes WEPP heavy trees while explicitly creating destination directories.
- Updated schema-default endpoint metadata/defaults and UI forking architecture docs.
- Updated regression coverage in `tests/rq/test_project_rq_fork.py`, `tests/microservices/test_rq_engine_fork_archive_routes.py`, and `tests/microservices/test_rq_engine_schema_defaults_routes.py`.
- Regenerated `wepppy/rq/job-dependency-graph.static.json` and `wepppy/rq/job-dependencies-catalog.md` after queue-wiring drift check.

**Blockers encountered**:
- `wctl check-rq-graph` initially reported drift after enqueue signature changes; resolved by running `python tools/check_rq_dependency_graph.py --write`.

**Next steps**:
- Complete subagent review passes and write disposition artifact.
- Finalize package notes with reviewer outcomes.

**Test results**:
- `wctl run-pytest tests/rq/test_project_rq_fork.py tests/microservices/test_rq_engine_fork_archive_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py` -> `90 passed`.
- `wctl check-rq-graph` -> drift detected then resolved (`RQ dependency graph artifacts are up to date`).
- `wctl doc-lint --path docs/work-packages/20260506_fork_skip_wepp_copy` -> clean.
- `wctl doc-lint --path docs/ui-docs/weppcloud-project-forking.md` -> clean.
- `wctl doc-lint --path PROJECT_TRACKER.md` -> clean.

### 2026-05-06 21:20 UTC: Subagent Review Closure

**Agent/Contributor**: Codex

**Work completed**:
- Received two independent subagent reviews (`reviewer`, `qa_reviewer`).
- Remediated all medium findings:
  - Added explicit default/false API boundary coverage for `skip_wepp_runs_output`.
  - Tightened helper skip-copy test to assert both exclude flags and non-copy of WEPP sentinel artifacts.
  - Extended schema-default auth/scope coverage and success-required response assertions.
- Updated forking UI docs for query-param parsing parity.
- Published review disposition at `docs/work-packages/20260506_fork_skip_wepp_copy/artifacts/20260506_subagent_review_disposition.md`.

**Blockers encountered**:
- None.

**Next steps**:
- Optional: add route/template harness coverage for UI default-propagation path if desired.

**Test results**:
- `wctl run-pytest tests/rq/test_project_rq_fork.py tests/microservices/test_rq_engine_fork_archive_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py` -> `96 passed`.
