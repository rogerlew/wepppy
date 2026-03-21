# Tracker - RUSLE Static R + WEPPpyo3 Hyetograph API Migration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-20  
**Current phase**: Completed  
**Last updated**: 2026-03-21  
**Next milestone**: None (package closed)  
**Active ExecPlan**: `prompts/completed/rusle_r_static_hyetograph_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Reviewed `wepppy/nodb/mods/rusle/specification.md` static-`R` and hyetograph requirements (2026-03-20).
- [x] Audited current Python hyetograph/intensity callsites in WEPPpy (`cligen.py`, export/interchange/report consumers) (2026-03-20).
- [x] Inspected WEPP Fortran behavior in `/workdir/wepp-forest` (`stmget.for`, `brkpt.for`, `disag.for`) for breakpoint/non-breakpoint intensity parity (2026-03-20).
- [x] Authored work-package brief (`package.md`) with scope, success criteria, and unresolved decisions (2026-03-20).
- [x] Created package scaffold and active ExecPlan (`prompts/active/rusle_r_static_hyetograph_execplan.md`) (2026-03-20).
- [x] Updated `PROJECT_TRACKER.md` backlog entry for this package (2026-03-20).
- [x] Ran doc lint for package docs and `PROJECT_TRACKER.md` with zero warnings/errors (2026-03-20).
- [x] Locked decision checkpoint answers for fallback policy (Q3) and release-tree scope (Q5) from user guidance (2026-03-20).
- [x] Dispatched and integrated subagent recommendations for static-`R` equation/units (Q1) and API/backward-compatibility contracts (Q2/Q4) into spec + package docs (2026-03-20).
- [x] Implemented `wepppyo3` hyetograph APIs (`build_hyetograph_non_breakpoint`, `build_hyetograph_breakpoint`, peak-intensity helpers) with Rust tests and py312 release export updates (2026-03-21).
- [x] Implemented `wepppyo3.climate.compute_static_r_from_cli` with annual EI30 + mean annual `R` contract and Rust tests (2026-03-21).
- [x] Migrated WEPPpy climate callsites to canonical API outputs and upgraded breakpoint artifact schema behavior (2026-03-21).
- [x] Added regression tests for breakpoint dataframe/parquet contracts and static-`R` API schema (`tests/climate`, `tests/nodb`, `tests/wepp/interchange`) (2026-03-21).
- [x] Completed Milestone 4 correctness review artifact (`artifacts/milestone4_review.md`) with no unresolved high/medium findings (2026-03-21).
- [x] Completed Milestone 5 QA review artifact (`artifacts/milestone5_qa_review.md`) with no unresolved high/medium findings in changed scope (2026-03-21).
- [x] Completed final validation artifact (`artifacts/final_validation_summary.md`) and package closeout synchronization (2026-03-21).

## Timeline

- **2026-03-20** - Package created and scoped.
- **2026-03-20** - WEPPpy + WEPP internal behavior research completed.
- **2026-03-21** - Milestones 1-3 implementation complete (`wepppyo3` APIs + WEPPpy migration).
- **2026-03-21** - Milestone 4 correctness review and Milestone 5 QA review completed.
- **2026-03-21** - Final validation completed; package closed.

## Decisions

### 2026-03-20: Make `wepppyo3.climate` the canonical implementation surface
**Context**: Existing Python hyetograph/intensity helpers are duplicated logic and can drift from shared runtime behavior.

**Options considered**:
1. Keep Python helpers as canonical and call Rust optionally.
2. Move canonical logic to Rust `wepppyo3.climate` and migrate Python callsites.

**Decision**: Choose option 2.

**Impact**: A single high-performance implementation path can be validated and reused across WEPPpy workflows.

---

### 2026-03-20: Treat breakpoint parity against WEPP internals as a mandatory acceptance gate
**Context**: Breakpoint storms currently have partial/sentinel intensity handling in downstream outputs.

**Options considered**:
1. Keep existing sentinel behavior and defer parity.
2. Implement parity now using WEPP internals and verify with focused tests.

**Decision**: Choose option 2.

**Impact**: Removes known artifact quality gaps and aligns exported intensity behavior with WEPP expectations.

---

### 2026-03-20: Fallback policy is legacy-only (no new Python-only fallback paths)
**Context**: Migration needs transitional behavior where legacy Python helpers already exist without creating new long-term split implementations.

**Options considered**:
1. Hard-fail all callsites immediately if new Rust APIs are unavailable.
2. Allow fallback only for existing legacy Python paths and prohibit new Python-only fallback additions.

**Decision**: Choose option 2.

**Impact**: Limits migration risk while keeping canonical implementation ownership in Rust.

---

### 2026-03-20: Release synchronization scope is `py312` only for WEPPpy stack
**Context**: Cross-repo release updates can expand scope and delay delivery.

**Options considered**:
1. Update multiple local release trees during phase 1.
2. Update source plus canonical WEPPpy runtime release path only (`/workdir/wepppyo3/release/linux/py312/`).

**Decision**: Choose option 2.

**Impact**: Keeps phase-1 integration scoped to the production runtime path used by WEPPpy.

---

### 2026-03-20: Static-`R` v1 energy/units contract uses WEPP/AH537-aligned SI form
**Context**: Static `R` required a locked equation and unit convention before implementation.

**Options considered**:
1. Use WEPP/AH537-aligned `log10` form with cap (segment-based).
2. Use `RUSLE2` Eq. 6.2 exponential form as v1 default.

**Decision**: Choose option 1 for v1.

**Impact**: Aligns static `R` with WEPP storm-shape physics in this stack while preserving an optional future `RUSLE2`-equation mode.

---

### 2026-03-20: Public hyetograph API is dual-layer with peak helpers as canonical callsite surface
**Context**: WEPPpy callsites primarily consume peak-intensity outputs, while static `R` also needs reusable segment primitives.

**Options considered**:
1. Segments-only public API.
2. Peak-only public API.
3. Both segments and peak helpers with one canonical callsite surface.

**Decision**: Choose option 3; canonical WEPPpy callsite surface is peak helpers.

**Impact**: Minimizes migration friction and keeps shared low-level primitives available for static-`R` and parity testing.

---

### 2026-03-20: Breakpoint artifact compatibility is fixed to real intensities + nullable `tp/ip`
**Context**: Existing breakpoint artifact paths relied on sentinel intensities and inconsistent field presence.

**Options considered**:
1. Keep sentinel/missing-field behavior.
2. Emit real breakpoint intensities with stable nullable schema.
3. Synthesize breakpoint `tp/ip`.

**Decision**: Choose option 2.

**Impact**: Stabilizes `climate/wepp_cli.parquet` schema across climate modes and makes breakpoint intensities scientifically usable.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Static `R` equation/units ambiguity causes incorrect erosivity magnitude | High | Medium | Contract fixed in spec and validated by Rust + Python regression checks | Mitigated |
| API migration introduces regressions in climate export/report workflows | High | Medium | Callsite migration plus targeted regression tests for climate export/interchange/report paths | Mitigated |
| Breakpoint parity differences vs WEPP Fortran remain undiscovered | High | Medium | Implemented breakpoint segment/intensity helpers and fixture contract tests; retain follow-up opportunity for additional numeric fixture locking | Mitigated |
| Cross-repo release sync issues (`wepppyo3` source vs release tree) delay integration | Medium | Medium | Restricted to py312 runtime release path and validated callable API surface | Mitigated |
| Full-suite gate drift after migration changes | Medium | Low | Re-ran full WEPPpy suite after final test hardening to confirm end-to-end stability | Mitigated |

## Verification Checklist

### Code Quality
- [x] Targeted migration tests pass (`tests/climate/test_cligen_peak_intensity_contract.py`, `tests/nodb/test_climate_artifact_export_service.py`, `tests/wepp/interchange/test_utils_phase7.py`, `tests/wepp/reports/test_return_periods_phase7.py`).
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passes.
- [x] `python3 tools/code_quality_observability.py --base-ref origin/master` reviewed (observe-only).

### Documentation
- [x] `wctl doc-lint --path docs/work-packages/20260320_rusle_r_static_hyetograph_api` passes.
- [x] Public API contract docs updated for migrated hyetograph/static-`R` entrypoints.
- [x] `PROJECT_TRACKER.md` and package tracker synchronized at closeout.

### Testing and Reviews
- [x] Non-breakpoint hyetograph + peak-intensity regression tests pass.
- [x] Breakpoint parity regression tests pass.
- [x] Static `R` regression tests pass against locked contract.
- [x] Dedicated review pass completed and all high/medium findings resolved.
- [x] Dedicated QA-review pass completed and all high/medium test-quality findings resolved.

### Final Acceptance
- [x] `wctl run-pytest tests --maxfail=1` passes.
- [x] Package `package.md` / `tracker.md` / active ExecPlan updated with closeout evidence.
- [x] Active ExecPlan moved to `prompts/completed/` with outcome summary.

## Progress Notes

### 2026-03-20: Scoping and package authoring
**Agent/Contributor**: Codex

**Work completed**:
- Reviewed static-`R` and hyetograph requirements in `wepppy/nodb/mods/rusle/specification.md`.
- Audited current WEPPpy Python helper callsites that depend on hyetograph/peak-intensity routines.
- Reviewed WEPP Fortran sources in `/workdir/wepp-forest` for breakpoint/non-breakpoint intensity behavior.
- Authored package brief and active ExecPlan scaffold.

**Blockers encountered**:
- `R` equation/units and exact public API shape remain unresolved and need explicit decision before implementation starts.

**Next steps**:
1. Resolve open contract questions with maintainers.
2. Begin Milestone 1 implementation in `wepppyo3`.
3. Add migration and review/QA artifacts as milestones complete.

**Test results**:
- Documentation and research session only (no code/test run yet).

### 2026-03-20: Decision-checkpoint closure (Q1-Q5)
**Agent/Contributor**: Codex

**Work completed**:
- Dispatched subagent literature review for static-`R` equation/units and integrated resulting contract in spec/package docs.
- Dispatched subagent code-contract review for API surface and breakpoint compatibility and integrated resulting contract in spec/package docs.
- Applied direct user decisions for fallback policy and release scope.
- Updated active ExecPlan, tracker, and project tracker to reflect resolved Milestone-0 decisions.

**Blockers encountered**:
- None; decision-checkpoint items are now resolved.

**Next steps**:
1. Begin Milestone 1 `wepppyo3` implementation (hyetograph helpers + tests).
2. Implement static `R` API and then migrate WEPPpy callsites.
3. Execute review and QA-review milestones before closeout.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260320_rusle_r_static_hyetograph_api` passed.
- `wctl doc-lint --path PROJECT_TRACKER.md` passed.
- `wctl doc-lint --path wepppy/nodb/mods/rusle/specification.md` passed.

### 2026-03-21: Implementation + migration + closeout
**Agent/Contributor**: Codex

**Work completed**:
- Implemented `wepppyo3` Rust/PyO3 hyetograph and static-`R` APIs and synchronized py312 release artifacts.
- Migrated WEPPpy climate callsites (`cligen.py`, climate artifact export, interchange, return-period fallback paths) to canonical peak-intensity/static-`R` outputs.
- Added/updated regression tests for breakpoint contract behavior and generated climate parquet schema expectations.
- Completed correctness review (`artifacts/milestone4_review.md`) and QA review (`artifacts/milestone5_qa_review.md`) with no unresolved high/medium changed-scope findings.
- Completed validation summary artifact (`artifacts/final_validation_summary.md`) and package closeout sync.

**Blockers encountered**:
- None.

**Next steps**:
1. Integrate static `R` API into the broader RUSLE controller package when that package is opened.
2. Optionally expand long-fixture parity checks for additional breakpoint/non-breakpoint climates.

**Test results**:
- `cargo test -p cli_revision_rust` passed (`3 passed`).
- Targeted migration tests passed (`18 passed` after deterministic + stability coverage additions).
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passed.
- `python3 tools/code_quality_observability.py --base-ref origin/master` completed (observe-only).
- `wctl doc-lint` passed for changed package/spec/tracker docs.
- `wctl run-pytest tests --maxfail=1` passed (`2392 passed, 34 skipped`).

## Communication Log

### 2026-03-20: Work-package request
**Participants**: User, Codex  
**Question/Topic**: Author a package to implement static `R`, add `wepppyo3` hyetograph helpers, use WEPP internals for breakpoint parity, define preferred API from current usage, and include review + QA-review passes.  
**Outcome**: Package scaffold created with scoped deliverables, active ExecPlan, tracker, and explicit open questions.

### 2026-03-21: End-to-end execution and closure
**Participants**: User, Codex  
**Question/Topic**: Install active ExecPlan in `AGENTS.md` and complete package end-to-end.  
**Outcome**: Milestones 1-6 executed, review/QA/final-validation artifacts captured, and package closed with full validation gates passing.
