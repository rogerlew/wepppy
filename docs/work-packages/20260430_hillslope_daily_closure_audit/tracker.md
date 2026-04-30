# Tracker – Hillslope Daily Closure Audit Tool (MOFE + Single OFE)

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-30 08:18 UTC  
**Current phase**: Completed  
**Last updated**: 2026-04-30 11:06 UTC  
**Next milestone**: Optional follow-up package for batch hillslope closure thresholds  
**Security impact**: `none`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Work-package scaffold created (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `artifacts`) (2026-04-30 08:18 UTC).
- [x] Exemplar hill selection confirmed from mounted runs:
  - MOFE run `/wc1/runs/un/uninsured-deformation`: `wepp_id` {78, 43, 97} (`topaz_id` {341, 201, 411}).
  - single-OFE run `/wc1/runs/bo/bovine-clipboard`: `wepp_id` {1, 2, 3} (`topaz_id` {22, 23, 31}).
  (2026-04-30 08:18 UTC)
- [x] Root `PROJECT_TRACKER.md` registration updated with this package in Backlog (2026-04-30 08:18 UTC).
- [x] Implemented `tools/hillslope_daily_closure_audit.py` with selector contract (`--wepp-id` XOR `--topaz-id`), MOFE outlet-OFE lateral handling, PASS `runvol` runoff basis, and optional `TSMF`/`QRain`/`QSnow` diagnostics (2026-04-30 10:31 UTC).
- [x] Added regression tests in `tests/tools/test_hillslope_daily_closure_audit.py` covering single-OFE closure, MOFE closure, `--topaz-id` and `--wepp-id` paths, and invalid selector combinations (2026-04-30 10:43 UTC).
- [x] Captured real-run evaluation artifacts for `uninsured-deformation` hillslopes {78,43,97} and `bovine-clipboard` hillslopes {1,2,3}; consolidated summary in `artifacts/evaluation_summary.{md,csv}` (2026-04-30 10:57 UTC).
- [x] Independent review completed and findings dispositioned in `artifacts/20260430_code_review_disposition.md` (2026-04-30 11:06 UTC).

## Timeline

- **2026-04-30 08:18 UTC** - Package created and scoped with MOFE + single-OFE validation matrix.
- **2026-04-30 10:31 UTC** - Tool implementation landed.
- **2026-04-30 10:43 UTC** - Unit/regression tests expanded and passing.
- **2026-04-30 10:57 UTC** - Real-run evaluation artifacts captured for six exemplar hillslopes.
- **2026-04-30 11:06 UTC** - Independent review findings resolved/dispositioned; package closed.

## Decisions Log

### 2026-04-30 08:18 UTC: Keep tool contract parallel to totalwatsed3 audit
**Context**: We already have stable stakeholder-aligned semantics in `totalwatsed3_daily_closure_audit.py`.

**Options considered**:
1. Create a new hillslope closure contract from scratch.
2. Mirror totalwatsed3 audit naming/equations and narrow scope to one hillslope.

**Decision**: Option 2.

**Impact**: Results are directly comparable between watershed and hillslope closure diagnostics.

---

### 2026-04-30 08:18 UTC: Require both MOFE and single-OFE run exemplars in initial evaluation
**Context**: Stakeholder concern explicitly calls out MOFE behavior while needing single-OFE baseline comparison.

**Options considered**:
1. Validate only on synthetic fixtures.
2. Validate only MOFE real run.
3. Validate both MOFE and single-OFE real runs plus synthetic fixtures.

**Decision**: Option 3.

**Impact**: Package closure requires artifact evidence for both run types.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| MOFE double-counting regression (`latqcc`/OFE handling) | High | Medium | Outlet-OFE lateral rule implemented and covered by synthetic MOFE test | Mitigated |
| `topaz_id` resolution ambiguity across runs | Medium | Medium | Deterministic run-root translator lookup; broad catch removed from wepp→topaz helper | Mitigated |
| Real-run evaluation artifacts become non-reproducible | Medium | Low | Saved concrete artifact directories + consolidated summary files under package artifacts | Mitigated |
| Closure interpretation drift (precipitation vs rain+melt basis) | Medium | Medium | Dual-basis outputs retained with explicit basis keys in summaries | Mitigated |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/tools/test_hillslope_daily_closure_audit.py`
- [x] Existing closure-audit regression suite remains green:
  - `wctl run-pytest tests/tools/test_totalwatsed3_daily_closure_audit.py`

### Security
- [x] Security impact triage recorded (`none`) with rationale.
- [x] Dedicated security artifact not required.

### Documentation
- [x] Tool usage/help text is explicit for `wepp_id` vs `topaz_id`.
- [x] `docs/dev-notes/totalwatsed-interchange.spec.md` update not required (no contract divergence from existing totalwatsed semantics).
- [x] Package tracker and decision log remain current.

### Testing
- [x] Single-OFE synthetic closure scenario passes with expected closure arithmetic.
- [x] MOFE synthetic closure scenario passes with outlet-OFE lateral-flow handling.
- [x] Selector behavior validated (`--wepp-id`, `--topaz-id`, and invalid combinations).
- [x] CLI output files (`summary.json`, `top_days.csv`) generated and validated.

### Evaluation / Review
- [x] MOFE evaluation artifacts captured for hillslopes {78, 43, 97} from `uninsured-deformation`.
- [x] Single-OFE evaluation artifacts captured for hillslopes {1, 2, 3} from `bovine-clipboard`.
- [x] Independent code review completed.
- [x] Review findings dispositioned and recorded.

## Progress Notes

### 2026-04-30 08:18 UTC: Package scaffolding and exemplar definition
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold and seeded scope/acceptance criteria.
- Verified run mounts and selected concrete MOFE/single-OFE exemplar hillslopes.
- Prepared execution plan prompt file for implementation phase.

**Blockers encountered**:
- None.

**Next steps**:
1. Implement tool skeleton and selection contract.
2. Add synthetic tests, then run targeted real-run evaluations.
3. Dispatch independent reviewer and disposition findings.

**Test results**:
- Discovery-only session; no new test suite executed.

### 2026-04-30 11:06 UTC: Package completion and review disposition
**Agent/Contributor**: Codex

**Work completed**:
- Implemented and validated `tools/hillslope_daily_closure_audit.py`.
- Added and passed regression tests (`5` tests in hillslope tool suite).
- Captured and summarized six real-run exemplar evaluations plus a topaz-selector verification run.
- Completed independent review and fixed/dispositioned findings.

**Blockers encountered**:
- None.

**Final artifacts**:
1. `artifacts/uninsured_deformation_H78`, `..._H43`, `..._H97`
2. `artifacts/bovine_clipboard_H1`, `..._H2`, `..._H3`
3. `artifacts/uninsured_deformation_top341`
4. `artifacts/evaluation_summary.md`
5. `artifacts/evaluation_summary.csv`
6. `artifacts/20260430_code_review_disposition.md`

**Test results**:
- `wctl run-pytest tests/tools/test_hillslope_daily_closure_audit.py --maxfail=1` (5 passed)
- `wctl run-pytest tests/tools/test_totalwatsed3_daily_closure_audit.py --maxfail=1` (3 passed)
