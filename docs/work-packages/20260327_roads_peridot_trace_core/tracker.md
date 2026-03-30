# Tracker - Roads Point-Source Flowpath Trace Core (Peridot + PyO3)

> Living document tracking progress, decisions, risks, and verification for Roads step-1 trace-core implementation.

## Quick Status

**Started**: 2026-03-27  
**Current phase**: Complete - Handoff Ready  
**Last updated**: 2026-03-27  
**Active ExecPlan**: `prompts/active/roads_peridot_trace_core_execplan.md`  
**Next milestone**: Package close + downstream Roads step-2 planning

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Authored package scaffold (`package.md`, `tracker.md`, active ExecPlan, notes/artifacts placeholders) (2026-03-27).
- [x] Added package listing to `PROJECT_TRACKER.md` and updated WIP metadata (2026-03-27).
- [x] Updated root `AGENTS.md` active work-package ExecPlan pointer to this package (2026-03-27).
- [x] Captured architecture decision: one Rust core in `peridot`, surfaced via `wepppyo3` binding (2026-03-27).
- [x] Ran docs lint + AGENTS size gate for authored package and tracker/pointer updates (2026-03-27).
- [x] Milestone 1: Implemented shared `peridot` trace core contract and algorithm (`src/roads_trace/trace_downslope.rs`) (2026-03-27).
- [x] Milestone 2: Added `peridot` CLI command `trace_downslope_flowpath` and JSON output surface (2026-03-27).
- [x] Milestone 3: Added `wepppyo3` `roads_flowpath_rust` binding crate calling shared `peridot` core (2026-03-27).
- [x] Milestone 4: Added cross-repo regression tests (`peridot` + `wepppyo3`) including CLI parity assertions (2026-03-27).
- [x] Milestone 5: Updated Roads spec trace-contract section with implemented v1 fields/termination labels (2026-03-27).
- [x] Milestone 6: Completed code review artifact with zero unresolved medium/high findings (2026-03-27).
- [x] Milestone 7: Completed QA review artifact with zero unresolved medium/high findings (2026-03-27).
- [x] Milestone 8: Executed final validation/doc-lint gates and prepared handoff notes (2026-03-27).

## Timeline

- **2026-03-27** - Package created and scoped for Roads step-1 flowpath tracing substrate.
- **2026-03-27** - Active ExecPlan drafted with concrete file targets, interfaces, and review gates.
- **2026-03-27** - Implemented `peridot` step-1 tracing core + CLI and validated deterministic termination semantics.
- **2026-03-27** - Added `wepppyo3` `roads_flowpath` binding, release module packaging, and parity tests against CLI output.
- **2026-03-27** - Updated Roads spec contract and completed code/QA review artifacts with medium/high closure.

## Decisions

### 2026-03-27: Keep one core implementation in `peridot`
**Context**: Roads needs routing logic in Rust with both CLI and Python-callable interfaces.

**Options considered**:
1. Implement tracer separately in `peridot` CLI and `wepppyo3`.
2. Keep one core in `peridot` and expose it via both CLI and `wepppyo3`.

**Decision**: Option 2.

**Impact**: Prevents algorithm drift and keeps validation focused on one implementation.

---

### 2026-03-27: Scope this package to step 1 only
**Context**: User requested immediate package for `peridot` core implementation; Roads point-source behavior changes are follow-on steps.

**Options considered**:
1. Include step 2+ Roads integration in the same package.
2. Complete only step 1 substrate, then stage follow-on packages for point-source and MOFE behavior.

**Decision**: Option 2.

**Impact**: Keeps scope bounded and makes acceptance criteria concrete.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Trace semantics diverge between CLI and `pyo3` interfaces | High | Medium | Enforce one shared core function and golden-output parity tests | Closed |
| CRS/seed-index mismatches produce false routing paths | High | Medium | Validate seed row/col bounds and document caller CRS expectations explicitly | Closed |
| Loop/edge/invalid-flow handling panics on real rasters | High | Medium | Add explicit termination reasons and synthetic-raster tests for each failure mode | Closed |
| Cross-repo build/release friction slows delivery | Medium | Medium | Keep file-level build commands in ExecPlan and stage commit checklist per repo | Closed |
| Contract churn from downstream Roads requirements | Medium | Medium | Lock a minimal stable v1 contract now and defer extra fields to additive follow-up | Monitoring |

## Verification Checklist

### Peridot Core and CLI
- [x] `cd /workdir/peridot && cargo test --test edge_flowpaths -- --nocapture` (pass)
- [x] `cd /workdir/peridot && cargo test --test roads_trace_downslope -- --nocapture` (pass)
- [x] `cd /workdir/peridot && cargo test -- --nocapture` (fail; pre-existing unrelated tests in `rasters::raster::*` and `support::support::*`)
- [x] `cd /workdir/peridot && cargo run --bin trace_downslope_flowpath -- --help` (pass)

### PyO3 Binding
- [x] `cd /workdir/wepppyo3 && cargo build --release -p roads_flowpath_rust` (pass)
- [x] `cd /workdir/wepppyo3 && pytest tests/roads_flowpath -q` (pass; 3 tests)
- [x] Release tree updated for new module under `release/linux/py312/wepppyo3/roads_flowpath/`.

### WEPPpy Integration Smoke and Docs
- [x] `cd /workdir/wepppy && wctl run-pytest tests/topo -k peridot --maxfail=1` (pass; 11 tests)
- [x] `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/roads/specification.md` (pass)
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/package.md` (pass)
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/tracker.md` (pass)
- [x] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/prompts/active/roads_peridot_trace_core_execplan.md` (pass)

### Review Gates
- [x] Code review artifact complete: `artifacts/20260327_code_review.md` (no unresolved medium/high).
- [x] QA review artifact complete: `artifacts/20260327_qa_review.md` (no unresolved medium/high).

## Progress Notes

### 2026-03-27: Package authoring and activation
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold and active ExecPlan for Roads step-1 flowpath tracing substrate.
- Updated `PROJECT_TRACKER.md` with in-progress package entry and WIP metadata.
- Updated root `AGENTS.md` active ExecPlan pointer for this package.
- Captured milestone order, cross-repo touchpoints, and review-gate expectations.

**Blockers encountered**:
- None.

**Next steps**:
- Execute Milestone 1 core contract + tests in `peridot`.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/package.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/tracker.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/prompts/active/roads_peridot_trace_core_execplan.md` (pass)
- `wctl doc-lint --path AGENTS.md` (pass)
- `wctl doc-lint --path PROJECT_TRACKER.md` (pass)
- `tools/check_agents_size.sh AGENTS.md` (pass; 141 lines)

### 2026-03-27: End-to-end implementation, review, and validation closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented shared `peridot` roads tracer core with explicit termination semantics and shape/seed validation.
- Added `peridot` CLI `trace_downslope_flowpath` and wired JSON output directly from shared core struct.
- Added `wepppyo3` `roads_flowpath_rust` crate with Python dict API mapped from shared core output.
- Added deterministic tests in `peridot` and `wepppyo3`, including CLI-vs-`pyo3` parity assertions.
- Updated Roads specification trace-contract section with implemented v1 fields and termination labels.
- Authored required code review and QA review artifacts with no unresolved medium/high findings.

**Blockers encountered**:
- `cargo test -- --nocapture` in `peridot` reported pre-existing failures in untouched modules (`src/rasters/raster.rs` unit tests and `src/support/support.rs` panic-expectation tests).

**Next steps**:
- Land commits in `peridot` and `wepppyo3`.
- Consume new tracer API in follow-on Roads step-2 package (`inslope` non-channel low-point routing).

**Test results**:
- `cd /workdir/peridot && cargo fmt` (pass)
- `cd /workdir/peridot && cargo test --test edge_flowpaths -- --nocapture` (pass)
- `cd /workdir/peridot && cargo test --test roads_trace_downslope -- --nocapture` (pass; 6 tests)
- `cd /workdir/peridot && cargo test -- --nocapture` (fail; pre-existing unrelated failures)
- `cd /workdir/peridot && cargo run --bin trace_downslope_flowpath -- --help` (pass)
- `cd /workdir/wepppyo3 && cargo fmt` (pass)
- `cd /workdir/wepppyo3 && cargo build --release -p roads_flowpath_rust` (pass)
- `cd /workdir/wepppyo3 && pytest tests/roads_flowpath -q` (pass; 3 tests)
- `cd /workdir/wepppy && wctl run-pytest tests/topo -k peridot --maxfail=1` (pass; 11 selected tests)
- `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/roads/specification.md` (pass)
- `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/package.md` (pass)
- `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/tracker.md` (pass)
- `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/prompts/active/roads_peridot_trace_core_execplan.md` (pass)
