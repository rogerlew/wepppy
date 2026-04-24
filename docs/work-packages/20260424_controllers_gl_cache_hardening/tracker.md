# Tracker - Controllers-GL Cache Hardening Rollout

> Living document tracking progress, decisions, risks, and verification for this package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-24 17:03 UTC  
**Current phase**: Complete / Closed  
**Last updated**: 2026-04-24 18:33 UTC  
**Next milestone**: None (package closed).  
**Security impact**: `low`  
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
- [x] Package scaffold created (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `artifacts`, `notes`) (2026-04-24 17:03 UTC).
- [x] Active ExecPlan created with explicit code review and QA review milestones (2026-04-24 17:03 UTC).
- [x] Review artifact stubs created for implementation follow-through (2026-04-24 17:03 UTC).
- [x] Built authoritative inventory of WEPPcloud templates that load `controllers-gl.js` (19 templates) (2026-04-24 18:05 UTC).
- [x] Replaced all legacy `controllers-gl.js` includes with `static_url('js/controllers-gl.js')` in the inventory set (2026-04-24 18:12 UTC).
- [x] Added missing `controllers_gl_stale_check.js` include immediately after `controllers-gl.js` in the inventory set (2026-04-24 18:12 UTC).
- [x] Added/updated regression tests for include invariants (`tests/weppcloud/test_stale_controllers_gl_template_wiring.py`) (2026-04-24 18:17 UTC).
- [x] Ran required validation commands and captured evidence (2026-04-24 18:26 UTC).
- [x] Completed code review artifact (`artifacts/2026-04-24_code_review.md`) with no unresolved medium/high findings (2026-04-24 18:30 UTC).
- [x] Completed QA review artifact (`artifacts/2026-04-24_qa_review.md`) with no unresolved medium/high findings (2026-04-24 18:32 UTC).
- [x] Updated package docs + `PROJECT_TRACKER.md` lifecycle to closure state (2026-04-24 18:33 UTC).

## Timeline

- **2026-04-24 17:03 UTC** - Package and ExecPlan created.
- **2026-04-24 18:05 UTC** - Inventory completed; 19 WEPPcloud templates identified with `controllers-gl.js` includes.
- **2026-04-24 18:12 UTC** - Include remediation complete across all non-compliant templates.
- **2026-04-24 18:17 UTC** - Regression invariant test expanded to full template inventory.
- **2026-04-24 18:26 UTC** - Required + targeted validation commands passed.
- **2026-04-24 18:30 UTC** - Code review gate completed and findings dispositioned.
- **2026-04-24 18:32 UTC** - QA review gate completed and findings dispositioned.
- **2026-04-24 18:33 UTC** - Documentation lifecycle updates completed; package closed.

## Decisions Log

### 2026-04-24 17:03 UTC: Scope only include-hygiene hardening
**Context**: Incident triage indicated stale frontend bundle drift; immediate remediation should be low-risk and deployable.

**Options considered**:
1. Bundle include hardening only (`static_url` + stale-check include coverage).
2. Include hardening plus backend API/validation behavior changes.

**Decision**: Option 1.

**Impact**: Keeps this package narrowly focused and safe; backend hardening can be separate if needed.

---

### 2026-04-24 17:03 UTC: Require both code and QA review milestones
**Context**: Request explicitly requires code and QA review.

**Options considered**:
1. Single review pass.
2. Separate correctness-focused code review and QA-focused review gates.

**Decision**: Option 2.

**Impact**: Ensures both behavioral correctness and regression-test quality are independently validated.

---

### 2026-04-24 18:12 UTC: Preserve per-template script execution mode while hardening includes
**Context**: Some templates loaded `controllers-gl.js` with `defer` and some without.

**Options considered**:
1. Normalize all script tags to `defer` while hardening includes.
2. Preserve existing `defer`/non-`defer` behavior and only change include source + stale-check pairing.

**Decision**: Option 2.

**Impact**: Avoids unrelated behavior changes while meeting package hardening goals.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| A template may not have `static_url` available in render context | Medium | Low | Confirmed WEPPcloud context processors provide `static_url`; targeted render tests passed | Closed |
| Missing stale-check include on a niche page causes future silent stale-client drift | High | Medium | Repository-wide inventory remediation + inventory-wide regression test | Closed |
| Over-broad edits change unrelated script loading order | Medium | Low | Kept edits to include lines only; preserved local ordering/execution attributes | Closed |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- [x] `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/controllers_gl_stale_check.test.js`
- [x] Additional targeted tests for touched templates/routes passed: `wctl run-pytest tests/weppcloud/test_stale_controllers_gl_template_wiring.py --maxfail=1`

### Security
- [x] Security impact triage recorded (`low`) with rationale.
- [x] Dedicated security review not required.
- [x] Confirmed no new attack-surface changes introduced.

### Documentation
- [x] `package.md`, `tracker.md`, and active ExecPlan kept current.
- [x] `PROJECT_TRACKER.md` reflects package lifecycle state.

### Testing
- [x] Regression coverage added/updated for include invariant.
- [x] Inventory verifies all templates loading `controllers-gl.js` now pair stale-check immediately.

### Review Gates
- [x] Code review completed and recorded in `artifacts/2026-04-24_code_review.md`.
- [x] QA review completed and recorded in `artifacts/2026-04-24_qa_review.md`.
- [x] No unresolved medium/high findings remain.

## Progress Notes

### 2026-04-24 18:33 UTC: Execution closure
**Agent/Contributor**: Codex

**Work completed**:
- Remediated all non-compliant `controllers-gl.js` includes to `static_url('js/controllers-gl.js')`.
- Added `controllers_gl_stale_check.js` immediately after `controllers-gl.js` across the full inventory.
- Added inventory-driven invariant regression coverage.
- Completed required validations and both review gates.
- Updated package lifecycle docs and project tracker state.

**Blockers encountered**:
- None.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> **46 passed**.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/controllers_gl_stale_check.test.js` -> **1 suite passed, 9 tests passed**.
- `wctl run-pytest tests/weppcloud/test_stale_controllers_gl_template_wiring.py --maxfail=1` -> **26 passed**.

## Watch List

- None for this closed package scope.

## Communication Log

### 2026-04-24 17:03 UTC: Package requested
**Participants**: User, Codex  
**Question/Topic**: Execute include-hygiene hardening package end-to-end with explicit code + QA review gates.  
**Outcome**: Package executed and closed with required validations and artifacts complete.
