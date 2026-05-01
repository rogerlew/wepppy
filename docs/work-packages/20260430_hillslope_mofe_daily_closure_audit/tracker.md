# Tracker – Hillslope MOFE Daily Closure Audit + Contract Definition

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-30 15:20 UTC  
**Current phase**: Milestone 4 evaluation refresh + Milestone 5 disposition  
**Last updated**: 2026-04-30 (full-physics rework)  
**Next milestone**: Milestone 4 evidence and Milestone 5 review closeout  
**Security impact**: `none`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Milestone 4: run `drilled-plight` exemplar audit set and capture artifacts.
- [ ] Milestone 5: independent code review and final disposition.

### In Progress
- [ ] Milestone 5: implementation review disposition artifact.

### Blocked
- [ ] Milestone 4 strict MOFE exemplar validation blocked by run data: `drilled-plight` has no multi-OFE hillslopes (`mofe_hillslopes=0`, `max_n_ofe=1`).

### Done
- [x] Package scaffold created (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `artifacts`) (2026-04-30 15:20 UTC).
- [x] Milestone 1 contract drafted: `docs/dev-notes/hillslope_mofe_water_balance_contract.md` with source-cited MOFE equations and interchange mapping (2026-04-30 16:02 UTC).
- [x] Milestone 1 gate completed: reviewer findings dispositioned in `artifacts/20260430_contract_review_disposition.md` (2026-04-30 16:10 UTC).
- [x] Milestone 2 implemented and reworked to full-physics closure terms plus implied-unresolved-term diagnostics (2026-04-30).
- [x] Milestone 3 regression tests updated and passing for full-physics closure behavior and selector/output contracts (2026-04-30).
- [x] Milestone 4 rerun/evidence refresh completed for selected `drilled-plight` hillslopes; strict MOFE-chain validation remains data-blocked due `n_ofe_max=1` in run (2026-04-30).

## Timeline

- **2026-04-30 15:20 UTC** - Package created with explicit contract-definition milestone and subagent review gate requirement.
- **2026-04-30 16:02 UTC** - Authored MOFE contract doc from `/workdir/wepp-forest` source; started required review gate.
- **2026-04-30 16:10 UTC** - Applied reviewer findings and closed Milestone 1 gate.
- **2026-04-30** - Hydrology review triggered scope pivot to full physical closure audit semantics.
- **2026-04-30** - Tool and tests reworked to compute exported-term full-physics closure residual and implied unresolved term diagnostics.
- **2026-04-30** - Re-ran drilled-plight evaluation artifacts for full-physics outputs; confirmed run-level MOFE exemplar blocker persists.

## Decisions Log

### 2026-04-30 15:20 UTC: Contract definition is an independent milestone before tool completion
**Context**: User requested MOFE water-balance contract derived directly from WEPP source and gated review.

**Options considered**:
1. Implement tool first and backfill contract text.
2. Define contract first, gate by review, then implement tool against contract.

**Decision**: Option 2.

**Impact**: Reduces risk of implementing incorrect MOFE accounting assumptions.

---

### 2026-04-30 15:20 UTC: Milestone 1 must include delegated subagent review gate
**Context**: User explicitly required a subagent review gate for the contract milestone.

**Decision**: Milestone 1 remains incomplete until reviewer artifact exists with disposition.

**Impact**: Adds formal quality gate before implementation.

---

### 2026-04-30 16:02 UTC: Surface MOFE adjacent-transfer checks are geometry-sensitive
**Context**: WEPP producer equations use `efflen`, `slplen`, and OFE widths for surface runon terms, but those geometry terms are not exported in interchange parquet.

**Decision**: Keep subsurface transfer residuals as strict closure checks and classify surface transfer residuals as geometry-sensitive diagnostics.

**Impact**: Prevents false-positive “non-closure” calls when OFE geometry varies across adjacent elements.

---

### 2026-04-30: Full-physics closure semantics replace legacy-only interpretation
**Context**: Hydrology review identified that `Total-Soil Water + frozwt + Snow-Water` closure residuals can be over-interpreted as strict physical mass-balance checks.

**Decision**:
1. Make full-physics exported-term closure equation first-class.
2. Report residual as `implied_unresolved_term_mm` rather than strict model-failure by default.
3. Prefer `SoilWaterTotal + Snow-Water` storage basis, with documented legacy fallback only when `SoilWaterTotal` is absent.

**Impact**: Aligns tool outputs with canonical WEPP interpretation and reduces scientific misreading.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Contract misreads WEPP source transfer semantics | High | Medium | Source-citation discipline + review gate before implementation | Open |
| MOFE tool overfits one run (`drilled-plight`) | Medium | Medium | Keep synthetic tests contract-driven and run-based checks as evidence only | Open |
| Missing/legacy interchange columns break audit flow | Medium | Medium | Define tolerant parser behavior and explicit fallback/null semantics in contract | Open |
| Ambiguous closure residual interpretation | Medium | Low | Full-physics residual labeling and explicit implied-unresolved-term reporting | Mitigated |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/tools/test_hillslope_mofe_daily_closure_audit.py`
- [ ] Regression guard:
  - `wctl run-pytest tests/tools/test_hillslope_daily_closure_audit.py`
  - `wctl run-pytest tests/tools/test_totalwatsed3_daily_closure_audit.py`

### Security
- [x] Security impact triage recorded (`none`) with rationale.
- [x] Dedicated security artifact not required.

### Documentation
- [x] Contract doc includes WEPP-source citations and equations.
- [x] Milestone 1 reviewer gate artifact exists with findings disposition.
- [ ] Package tracker and decision log remain current.

### Testing
- [x] Synthetic MOFE closure cases cover transfer/closure semantics.
- [x] Selector behavior validated (`--wepp-id`, `--topaz-id`, invalid combinations).
- [x] CLI output files generated and validated.

### Evaluation / Review
- [ ] `drilled-plight` exemplar outputs audited and captured.
- [ ] Independent reviewer findings dispositioned.

## Progress Notes

### 2026-04-30 15:20 UTC: Package initialization
**Agent/Contributor**: Codex

**Work completed**:
- Created new package scaffold and initial planning docs.
- Added explicit Milestone 1 contract-definition gate with required subagent review.

**Blockers encountered**:
- None.

**Next steps**:
1. Draft active ExecPlan with detailed milestones and commands.
2. Register package in root `PROJECT_TRACKER.md` backlog.

**Test results**:
- Planning-only session; no code tests executed.

### 2026-04-30 16:02 UTC: Contract authored, review gate pending
**Agent/Contributor**: Codex

**Work completed**:
- Authored `docs/dev-notes/hillslope_mofe_water_balance_contract.md`.
- Added explicit source-line citations from `/workdir/wepp-forest` for each contract rule.
- Defined required MOFE chain diagnostics, including strict subsurface transfer closure and geometry-sensitive surface transfer residuals.

**Blockers encountered**:
- None.

**Next steps**:
1. Dispatch required reviewer subagent on contract doc only.
2. Record findings disposition artifact and close Milestone 1 gate.

**Test results**:
- Documentation drafting only; no tests executed yet.

### 2026-04-30 16:10 UTC: Milestone 1 gate closure
**Agent/Contributor**: Codex

**Work completed**:
- Ran required reviewer subagent on the contract doc only.
- Addressed all returned findings in `docs/dev-notes/hillslope_mofe_water_balance_contract.md`.
- Wrote disposition artifact `artifacts/20260430_contract_review_disposition.md`.

**Blockers encountered**:
- None.

**Next steps**:
1. Finish implementing `tools/hillslope_mofe_daily_closure_audit.py`.
2. Add regression tests and run required validations.

**Test results**:
- Milestone gate/documentation-only step; no code tests executed yet.

### 2026-04-30: Full-physics contract/tool/test rework
**Agent/Contributor**: Codex

**Work completed**:
- Reworked `docs/dev-notes/hillslope_mofe_water_balance_contract.md` to define exported-term full-physics closure equations and implied unresolved-term interpretation.
- Updated `tools/hillslope_mofe_daily_closure_audit.py` to compute per-day/per-OFE full-physics closure diagnostics, while preserving MOFE chain checks and selector contract.
- Updated `tests/tools/test_hillslope_mofe_daily_closure_audit.py` for full-physics expectations and output contract assertions.
- Ran: `wctl run-pytest tests/tools/test_hillslope_mofe_daily_closure_audit.py --maxfail=1` (pass).

**Blockers encountered**:
- None on implementation; remaining package closure still depends on milestone-4/5 artifact bookkeeping.

**Next steps**:
1. Re-run required regression guard suites.
2. Refresh evaluation artifacts and implementation-review disposition docs.
3. Run doc-lint on updated package/contract docs.
