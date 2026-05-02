# Tracker - MOFE Flagged Hillslope Triage for Ablation Campaigns

> Living execution log for triaging MOFE closure-audit flagged hillslopes into ablation-ready defect families.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-02 15:54 UTC  
**Current phase**: Discovery/Scaffolding complete; implementation pending  
**Last updated**: 2026-05-02 15:54 UTC  
**Next milestone**: M1 triage table builder implementation and output validation  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] M2 deterministic D0-D5 taxonomy assignment generation.
- [ ] M3 cluster cross-check and disagreement disposition.
- [ ] M4 representative seed manifest generation.
- [ ] M5 precedent crosswalk against `/workdir/wepp-forest/docs/ablation` incidents.
- [ ] M6 campaign matrix and defect family closeout docs.

### In Progress
- [ ] M1 implement `tools/build_mofe_triage_table.py` and generate `triage_table_*` outputs.

### Blocked
- [ ] None.

### Done
- [x] Created full work-package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `artifacts`, `notes`) (2026-05-02 15:54 UTC).
- [x] Migrated active ExecPlan from mini-work-package to `prompts/active/mofe_flagged_hillslope_triage_execplan.md` (2026-05-02 15:54 UTC).
- [x] Added execution preconditions and autonomy-friction fixes in active ExecPlan (2026-05-02 15:54 UTC).

## Timeline

- **2026-05-02 15:54 UTC** - Work-package scaffold created and active ExecPlan migrated.
- **2026-05-02 15:54 UTC** - Tracker initialized; M1 identified as active milestone.

## Decisions Log

### 2026-05-02 15:54 UTC: Promote triage effort from mini-work-package to full work-package
**Context**: The triage effort needs a stable package home for generated artifacts and multi-session execution tracking.

**Options considered**:
1. Keep as mini-work-package with ad hoc artifacts.
2. Promote to `docs/work-packages` with standard scaffold and tracker.

**Decision**: Option 2.

**Impact**: Artifacts, active prompts, and execution logs now have a canonical package location suitable for autonomous multi-step execution.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Missing `/workdir/wepp-forest` protocol references at execution time | Medium | Medium | Enforce precondition checks before M1 | Open |
| Missing `/wc1/runs` mount blocks staged-input checks | Medium | Medium | Explicit precondition + blocker recording path | Open |
| Taxonomy thresholds require retune after cluster cross-check | Medium | Medium | Record retunes in Decision Log and rerun M2 | Open |

## Verification Checklist

### Documentation
- [x] `package.md` created and scoped.
- [x] `tracker.md` initialized.
- [x] Active ExecPlan migrated under `prompts/active/`.
- [x] `PROJECT_TRACKER.md` updated with package status.

### Execution
- [ ] M1-M6 outputs generated in package `artifacts/`.
- [ ] ExecPlan `Progress`, `Decision Log`, and `Outcomes & Retrospective` fully updated.

## Progress Notes

### 2026-05-02 15:54 UTC: Package migration setup
**Agent/Contributor**: Codex

**Work completed**:
- Created work-package scaffold at `docs/work-packages/20260502_mofe_flagged_hillslope_triage/`.
- Moved active triage ExecPlan into `prompts/active/`.
- Prepared package/tracker docs for autonomous execution.

**Blockers encountered**:
- None during scaffolding.

**Next steps**:
1. Implement `tools/build_mofe_triage_table.py` and execute M1 acceptance checks.
2. Execute M2-M6 and record threshold/label decisions in the Decision Log.
3. Prepare closeout recommendation set for downstream ablation package creation.

**Test results**:
- Documentation lint passed for package docs, ExecPlan, and tracker after migration.
