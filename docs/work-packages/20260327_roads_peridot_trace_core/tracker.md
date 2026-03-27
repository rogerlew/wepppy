# Tracker - Roads Point-Source Flowpath Trace Core (Peridot + PyO3)

> Living document tracking progress, decisions, risks, and verification for Roads step-1 trace-core implementation.

## Quick Status

**Started**: 2026-03-27  
**Current phase**: Planning Complete - Implementation Ready  
**Last updated**: 2026-03-27  
**Active ExecPlan**: `prompts/active/roads_peridot_trace_core_execplan.md`  
**Next milestone**: Milestone 1 - lock peridot trace contract and test matrix

## Task Board

### Ready / Backlog
- [ ] Milestone 1: Implement shared `peridot` trace contract and core algorithm.
- [ ] Milestone 2: Add `peridot` CLI command and JSON output contract.
- [ ] Milestone 3: Add `wepppyo3` binding that calls shared `peridot` core.
- [ ] Milestone 4: Add focused cross-repo regression tests and update docs/spec.
- [ ] Milestone 5: Execute independent code review and resolve medium/high findings.
- [ ] Milestone 6: Execute independent QA review and resolve medium/high findings.
- [ ] Milestone 7: Run final gates, update trackers, and publish handoff summary.

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

## Timeline

- **2026-03-27** - Package created and scoped for Roads step-1 flowpath tracing substrate.
- **2026-03-27** - Active ExecPlan drafted with concrete file targets, interfaces, and review gates.

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
| Trace semantics diverge between CLI and `pyo3` interfaces | High | Medium | Enforce one shared core function and golden-output parity tests | Open |
| CRS/seed-index mismatches produce false routing paths | High | Medium | Validate seed row/col bounds and document caller CRS expectations explicitly | Open |
| Loop/edge/invalid-flow handling panics on real rasters | High | Medium | Add explicit termination reasons and synthetic-raster tests for each failure mode | Open |
| Cross-repo build/release friction slows delivery | Medium | Medium | Keep file-level build commands in ExecPlan and stage commit checklist per repo | Open |
| Contract churn from downstream Roads requirements | Medium | Medium | Lock a minimal stable v1 contract now and defer extra fields to additive follow-up | Open |

## Verification Checklist

### Peridot Core and CLI
- [ ] `cd /workdir/peridot && cargo test --test edge_flowpaths -- --nocapture`
- [ ] `cd /workdir/peridot && cargo test --test roads_trace_downslope -- --nocapture`
- [ ] `cd /workdir/peridot && cargo test -- --nocapture`
- [ ] `cd /workdir/peridot && cargo run --bin trace_downslope_flowpath -- --help`

### PyO3 Binding
- [ ] `cd /workdir/wepppyo3 && cargo build --release -p roads_flowpath_rust`
- [ ] `cd /workdir/wepppyo3 && pytest tests/roads_flowpath -q`
- [ ] Release tree updated for new module under `release/linux/py312/wepppyo3/roads_flowpath/`.

### WEPPpy Integration Smoke and Docs
- [ ] `cd /workdir/wepppy && wctl run-pytest tests/topo -k peridot --maxfail=1`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/roads/specification.md`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/package.md`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/tracker.md`
- [ ] `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260327_roads_peridot_trace_core/prompts/active/roads_peridot_trace_core_execplan.md`

### Review Gates
- [ ] Code review artifact complete: `artifacts/20260327_code_review.md` (no unresolved medium/high).
- [ ] QA review artifact complete: `artifacts/20260327_qa_review.md` (no unresolved medium/high).

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
