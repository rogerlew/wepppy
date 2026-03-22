# Tracker - Peridot Watershed Parquet + Manifest Integration

> Living document tracking progress, decisions, risks, and verification.

## Quick Status

**Started**: 2026-03-21
**Current phase**: Closed
**Last updated**: 2026-03-21
**Next milestone**: None (package complete)

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created package scaffold (`package.md`, `tracker.md`, `prompts/active`, `artifacts`) (2026-03-21).
- [x] Created active ExecPlan per template requirements (2026-03-21).
- [x] Completed discovery of Peridot abstraction writers and WEPPpy CSV->parquet conversion callsites (2026-03-21).
- [x] Implemented Peridot direct parquet writes for `hillslopes`, `channels`, and conditional `flowpaths` in both abstraction paths (2026-03-21).
- [x] Implemented Peridot-generated `watershed/README.md` manifest with flags, file manifest, schema summaries, and conditional notes (2026-03-21).
- [x] Updated WEPPpy `post_abstract_watershed()` to parquet-first behavior with explicit legacy CSV fallback warnings (2026-03-21).
- [x] Preserved legacy CSV migration support via `migrate_watershed_outputs()` and added regression coverage (2026-03-21).
- [x] Added Rust tests for parquet generation and README manifest/schema content (2026-03-21).
- [x] Added/updated WEPPpy pytest coverage for parquet-first path, legacy fallback, and legacy CSV migration behavior (2026-03-21).
- [x] Ran required targeted Rust and pytest validation suites (2026-03-21).
- [x] Performed real-run verification on `/wc1/runs/un/unassailable-sensuousness` and confirmed direct Peridot parquet + README outputs plus slope sanity (2026-03-21).
- [x] Captured `reviewer` + `test_guardian` findings under `artifacts/` and performed re-review after fixes (2026-03-21).
- [x] Fixed README drift by refreshing manifest/schema sections after WEPPpy parquet post-processing (2026-03-21).
- [x] Reduced flowpaths parquet contention by moving export outside Peridot parallel output pool (2026-03-21).
- [x] Expanded WEPPpy fallback/migration tests and Peridot manifest conditional tests (2026-03-21).

## Timeline

- **2026-03-21** - Package created and activated.
- **2026-03-21** - Peridot producer + WEPPpy parquet-first integration implemented and validated.
- **2026-03-21** - Real-run verification completed on `/wc1/runs/un/unassailable-sensuousness`.

## Decisions

### 2026-03-21: Keep migration incremental with explicit legacy path
**Context**: New runs must avoid CSV conversion, but old runs may still only contain CSV artifacts.

**Decision**: Implement parquet-first behavior for new runs and preserve a clearly explicit legacy fallback path for old runs.

**Impact**: Enables immediate migration without breaking historical runs while keeping fallback behavior discoverable and auditable.

### 2026-03-21: Keep CSV outputs for compatibility, but make parquet canonical
**Context**: Peridot now writes parquet directly; removing CSV immediately could break unknown downstream scripts.

**Decision**: Keep CSV emission in Peridot for now, generate parquet in the same run, and switch WEPPpy post-processing to consume parquet first.

**Impact**: New runs no longer require CSV->parquet conversion while old tooling can still read CSV during transition.

### 2026-03-21: Preserve explicit legacy migration path
**Context**: User required old projects with `watershed/*.csv` to remain migratable.

**Decision**: Keep `migrate_watershed_outputs()` CSV upgrade behavior and add a dedicated regression test that starts from CSV-only inputs.

**Impact**: Historical run repair workflows remain intact and verifiable.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Schema mismatch between Peridot parquet and WEPPpy expectations | High | Medium | Audit existing schema usage and add contract tests | Mitigated |
| README manifest drift when flags change | Medium | Medium | Generate manifest from runtime config + directory scan + tests | Mitigated |
| Hidden reliance on CSV conversion in WEPPpy | High | Medium | Add explicit fallback path tests and remove only mandatory conversion call sites | Mitigated |
| Real-run environment drift causing false negatives | Medium | Medium | Log exact commands and compare only sanity-level invariants | Mitigated |
| Large flowpath-enabled runs may still peak high memory during parquet export | Low | Medium | Follow-up chunked/row-group parquet writer for subflows | Accepted residual |

## Verification Checklist

### Code Quality
- [x] Peridot targeted Rust tests pass.
- [x] WEPPpy targeted pytest suites pass via `wctl run-pytest`.

### Documentation
- [x] Work-package docs (`package.md`, `tracker.md`, ExecPlan) kept current.
- [x] Changed runtime contract docs updated.

### Testing and Reviews
- [x] Real-run verification completed on `/wc1/runs/un/unassailable-sensuousness`.
- [x] `reviewer` subagent artifact recorded and high/medium issues resolved or accepted.
- [x] `test_guardian` subagent artifact recorded and coverage gaps resolved or accepted.

### Final Acceptance
- [x] ExecPlan moved from `prompts/active/` to `prompts/completed/` with completion note.
- [x] Tracker/package marked completed.
- [x] Deliverables summarized with changed files and remaining risks.

## Progress Notes

### 2026-03-21: Package initialization
**Agent/Contributor**: Codex

**Work completed**:
- Created new work package directory and required baseline docs.
- Added active ExecPlan and prepared tracker for milestone execution.

**Blockers encountered**:
- None.

**Next steps**:
- Discover Peridot abstraction write paths and WEPPpy watershed ingestion/conversion paths.
- Implement Peridot parquet + README output and then WEPPpy parquet-first integration.

**Test results**:
- Not run yet (initialization stage).

### 2026-03-21: Implementation + validation
**Agent/Contributor**: Codex

**Work completed**:
- Implemented Peridot parquet writers and generated watershed manifest README output.
- Wired both `abstract_watershed` and `wbt_abstract_watershed` to emit parquet + README.
- Updated WEPPpy peridot integration to parquet-first loading with explicit CSV fallback warnings.
- Added Rust tests (`tests/watershed_parquet_manifest.rs`) and WEPPpy tests (`tests/topo/test_peridot_runner_wait.py`) covering new and legacy paths.
- Verified real-run behavior on `/wc1/runs/un/unassailable-sensuousness`.

**Blockers encountered**:
- `update_catalog_entry` rejects markdown assets; removed attempted `watershed/README.md` catalog update call.
- Host Python lacked `utm`; real-run scripts were executed inside the compose `weppcloud` container.

**Next steps**:
- Run mandatory `reviewer` and `test_guardian` subagent checks.
- Capture review artifacts and close package docs.

**Test results**:
- `cargo test --test watershed_parquet_manifest -- --nocapture` PASS.
- `cargo test --test hillslope_slope_scalar -- --nocapture` PASS.
- `wctl run-pytest tests/topo/test_peridot_runner_wait.py` PASS.
- `wctl run-pytest tests/tools/test_migrations_parquet_backfill.py -k watershed` PASS.
- Real-run verification PASS (`/wc1/runs/un/unassailable-sensuousness`): Peridot directly produced parquet outputs and `watershed/README.md`; post-step remained parquet-first with CSV legacy fallback.

### 2026-03-21: Review remediation + closeout
**Agent/Contributor**: Codex

**Work completed**:
- Incorporated subagent review findings and re-ran targeted checks.
- Added WEPPpy README refresh after post-processing to keep manifest/schema aligned with final parquet outputs.
- Moved Peridot flowpaths parquet export outside parallel output task pool to reduce contention.
- Expanded Peridot and WEPPpy tests for conditional notes, fallback behavior, and migration edge cases.
- Captured `reviewer`, `test_guardian`, and validation artifacts under `artifacts/`.

**Blockers encountered**:
- Requested run lacked `dem/wbt/subwta.tif`; real-run validation used Topaz abstraction path (`dem/topaz/SUBWTA.ARC`) for this run.

**Next steps**:
- Move ExecPlan to `prompts/completed/` and finish handoff summary.

**Test results**:
- `cargo test --test watershed_parquet_manifest -- --nocapture` PASS (`3 passed`).
- `cargo test --test hillslope_slope_scalar -- --nocapture` PASS (`1 passed`).
- `wctl run-pytest tests/topo/test_peridot_runner_wait.py` PASS (`11 passed`).
- `wctl run-pytest tests/tools/test_migrations_parquet_backfill.py -k watershed` PASS.
- Real-run verification PASS (`/wc1/runs/un/unassailable-sensuousness`).

## Communication Log

### 2026-03-21: End-to-end migration request received
**Participants**: User, Codex
**Topic**: Peridot direct watershed parquet output + manifest; WEPPpy parquet-first integration.
**Outcome**: Package created; execution started with active ExecPlan.
