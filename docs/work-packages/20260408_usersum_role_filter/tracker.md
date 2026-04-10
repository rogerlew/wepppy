# Tracker - Usersum Header ROLE Filter and Threshold Search Ceiling

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-04-08  
**Current phase**: Closed (2026-04-09)  
**Last updated**: 2026-04-09  
**Next milestone**: None.

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created work-package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- [x] Closed package lifecycle docs (`package.md`, `tracker.md`, `PROJECT_TRACKER.md`) and moved ExecPlan to `prompts/completed/` with outcome summary.
- [x] Loaded required AGENTS/process/spec guidance and scoped required file touchpoints.
- [x] Implemented usersum role-ceiling backend contract alignment (`Root` mapping + threshold semantics + 403 behavior).
- [x] Implemented shared header `ROLE` select and `/usersum/search` role preservation wiring.
- [x] Added/updated route and template regressions for role/UI contract.
- [x] Ran required targeted usersum pytest gate successfully.
- [x] Completed explicit QA review pass and dispositioned findings.
- [x] Fixed shell discovery mismatch so selected `ROLE` ceiling also filters usersum nav visibility.
- [x] Verified behavior with the real `dev-agent@example.com` role set via in-container app test-client check.
- [x] Updated `wepppy/weppcloud/routes/usersum/specification.md` to match implemented role/nav/search behavior.
- [x] Ran docs lint for updated usersum spec.
- [x] Ran dedicated security review trial artifact and captured findings.
- [x] Remediated `SEC-01` src/raw non-canonical path bypass and re-ran security gate.

## Timeline

- **2026-04-08** - Package created and scoped.
- **2026-04-08** - Active ExecPlan drafted and activated.
- **2026-04-08** - Implementation/testing/QA pass in progress.
- **2026-04-08** - Backend/template/test implementation completed.
- **2026-04-08** - Required pytest validation passed (`46 passed`).
- **2026-04-08** - Explicit QA review pass completed with no open medium/high findings.
- **2026-04-08** - Follow-up fix shipped for role-ceiling nav discovery filtering; required targeted pytest re-run passed (`50 passed`).
- **2026-04-08** - In-container validation run against `dev-agent@example.com` confirmed role-dependent API/search/nav behavior.
- **2026-04-08** - Usersum specification synced to implemented behavior; `wctl doc-lint --path wepppy/weppcloud/routes/usersum/specification.md` passed.
- **2026-04-08** - Dedicated security review artifact added; gate failed on high finding `SEC-01` (src/raw role-bypass via non-canonical path variants).
- **2026-04-08** - `SEC-01` fixed by canonical path enforcement before source/raw visibility checks; security gate now passes.
- **2026-04-09** - Package lifecycle closed; ExecPlan moved from `prompts/active` to `prompts/completed`, package status set to closed, and `PROJECT_TRACKER.md` moved package to Done.

## Decisions Log

### 2026-04-08: Execute as single-session end-to-end package with mandatory QA second pass
**Context**: User requested full work-package execution including implementation, tests, and explicit QA review.

**Options considered**:
1. Split into two sessions (implementation then later QA pass).
2. Execute in one continuous session with tracker/ExecPlan updates and final QA pass before handoff.

**Decision**: Option 2.

**Impact**: Tracker and ExecPlan must be maintained as living docs throughout implementation and QA.

### 2026-04-08: Preserve repeated/comma `role` parsing by collapsing to the highest requested ceiling
**Context**: Existing usersum API accepted repeated/comma-separated `role` values under exact-match semantics. Updated contract requires threshold ceiling semantics.

**Options considered**:
1. Reject repeated/comma role inputs as invalid under single-ceiling contract.
2. Keep repeated/comma parsing, but interpret inputs as one effective ceiling by taking the highest requested role rank.

**Decision**: Option 2.

**Impact**: Existing clients using repeated/comma role inputs remain accepted, while behavior aligns with threshold ceiling semantics and caller-ceiling authorization checks.

### 2026-04-08: Apply selected usersum `ROLE` ceiling to shell discovery nav visibility
**Context**: Privileged users reported the selector appearing ineffective because nav discovery was still rendered at full caller visibility, even when header `ROLE` selected a lower ceiling.

**Options considered**:
1. Keep nav at caller max and scope `ROLE` to search results only.
2. Apply selected discovery ceiling to shell nav filtering while keeping authorization gates unchanged.

**Decision**: Option 2.

**Impact**: Header selection now has immediate, visible impact on usersum discovery surfaces (nav + search) without changing direct URL authorization behavior.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Role mapping regressions alter usersum visibility unexpectedly | High | Medium | Added explicit route tests for PowerUser/Admin/Root role ceilings and 403 cases | Closed |
| Header role selector drops value during search refinement | Medium | Medium | Added role-preservation wiring + search-page regression coverage | Closed |
| Dirty generated index artifact accidentally modified | Medium | Medium | Avoid edits to `wepppy/weppcloud/routes/usersum/generated/docs_index.json` | Mitigated |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1`

### Documentation
- [x] `wctl doc-lint --path wepppy/weppcloud/routes/usersum/specification.md` (spec updated in follow-up)
- [x] Update package tracker and active ExecPlan with final outcomes

### Testing
- [x] Route tests cover threshold matching semantics.
- [x] Route tests cover unauthorized requested role ceilings.
- [x] Route tests cover PowerUser/Admin/Root mapping behavior.
- [x] Route tests cover `/usersum/search` behavior with role selection.
- [x] Template tests cover header role selector visibility + option sets.

### Review Gates
- [x] Perform second-pass QA review in code-review mindset.
- [x] Record findings/disposition in tracker.
- [x] Fix all discovered correctness/contract issues before handoff.
- [x] Run dedicated security review artifact for trial gate.
- [x] Resolve open high security finding `SEC-01` before package closeout.

## Progress Notes

### 2026-04-08: Package setup and implementation planning
**Agent/Contributor**: Codex

**Work completed**:
- Created package skeleton at `docs/work-packages/20260408_usersum_role_filter/`.
- Read required guidance:
  - `AGENTS.md`
  - `wepppy/weppcloud/AGENTS.md`
  - `wepppy/weppcloud/routes/usersum/AGENTS.md`
  - `docs/prompt_templates/codex_exec_plans.md`
  - `docs/work-packages/README.md`
  - `wepppy/weppcloud/routes/usersum/specification.md`
- Scoped current usersum implementation details and identified key deltas:
  - role filter currently exact-match set semantics,
  - `Root` mapping missing in caller role resolution,
  - no header role selector wiring,
  - search page refinement currently drops role.

**Blockers encountered**:
- None.

**Next steps**:
- Implement backend role/search contract updates and header/search template wiring.
- Add targeted route/template regression coverage.
- Run required tests, then QA second pass and fix findings.

**Test results**: Not run yet (implementation pending).

### 2026-04-08: Implementation, validation, and QA review closure
**Agent/Contributor**: Codex

**Work completed**:
- Backend usersum role/search contract updates in `wepppy/weppcloud/routes/usersum/usersum.py`:
  - explicit WEPPcloud role token extraction and caller max-role mapping (`PowerUser -> operator`, `Admin -> developer`, `Root -> internal`),
  - threshold role-ceiling filter semantics (`min_role <= requested_ceiling`),
  - authorization guard for requested ceiling above caller max (`403` / error path),
  - repeated/comma role parsing preserved via highest-ceiling collapse.
- Header/search template updates:
  - conditional header `ROLE` selector in `wepppy/weppcloud/routes/usersum/templates/usersum/header.htm`,
  - role selector style parity using shared theme-select classes,
  - `/usersum/search` refinement role preservation in `wepppy/weppcloud/routes/usersum/templates/usersum/search.htm`.
- Test updates:
  - `tests/weppcloud/routes/test_usersum_bp.py`
  - `tests/weppcloud/test_usersum_template_wiring.py`
  - Added coverage for threshold semantics, caller-ceiling authorization, PowerUser/Admin/Root mappings, header selector visibility/options, and search-page role persistence.
- Follow-up UI tweak:
  - Usersum document pages now self-report doc `min_role` directly under breadcrumbs in `wepppy/weppcloud/routes/usersum/templates/usersum/view.htm`.
  - Added styling in `wepppy/weppcloud/routes/usersum/templates/usersum/layout.j2`.
  - Added regression coverage for breadcrumb ordering and per-doc role rendering.

**QA review findings**:
- No open medium/high correctness, regression, or contract-mismatch findings after second-pass review.
- Residual low risk: role-token detection relies on `current_user.roles`/role attributes; environments with only custom `has_role()` implementations may need follow-up if encountered.

**Next steps**:
- Handoff complete package summary and residual risk note.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` -> `46 passed`.

### 2026-04-08: Follow-up layout refinement - role self-report under breadcrumb
**Agent/Contributor**: Codex

**Work completed**:
- Implemented role self-report readout under breadcrumb on usersum doc pages:
  - `wepppy/weppcloud/routes/usersum/templates/usersum/view.htm`
  - `wepppy/weppcloud/routes/usersum/templates/usersum/layout.j2`
- Added regression tests:
  - `tests/weppcloud/routes/test_usersum_bp.py` (position/value assertions, including operator doc)
  - `tests/weppcloud/test_usersum_template_wiring.py` (template wiring assertion)

**Blockers encountered**:
- None.

**Next steps**:
- Handoff summary.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` -> `49 passed`.

### 2026-04-08: Follow-up UX fix - role select auto-submits
**Agent/Contributor**: Codex

**Work completed**:
- Added change-triggered submit to the usersum header `ROLE` select so selection changes immediately run the existing `/usersum/search` flow without requiring a second click.
- Added compatibility fallback: use `form.submit()` when `form.requestSubmit()` is unavailable.
- Added template wiring assertion in `tests/weppcloud/test_usersum_template_wiring.py`.

**Blockers encountered**:
- None.

**Next steps**:
- Handoff summary.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` -> `49 passed`.

### 2026-04-08: Follow-up fix - selected role now filters shell discovery nav
**Agent/Contributor**: Codex

**Work completed**:
- Implemented discovery-role-aware nav filtering in `wepppy/weppcloud/routes/usersum/usersum.py` so the selected header `ROLE` ceiling is applied to usersum shell navigation rendering.
- Added route regression `test_usersum_shell_nav_respects_selected_role_ceiling` in `tests/weppcloud/routes/test_usersum_bp.py`.
- Re-ran required usersum tests and completed an explicit QA re-review pass.
- Executed an in-container verification using the real `dev-agent@example.com` user object and roles to confirm:
  - API threshold behavior (`user` -> user docs only, `operator` -> user+operator, `developer` -> user+operator+developer).
  - Shell nav discovery visibility mirrors selected role ceiling.

**QA review findings**:
- Finding addressed: selected role previously did not affect shell/nav discovery for privileged users.
- Post-fix QA status: no open medium/high findings.

**Next steps**:
- Handoff with behavior summary and verification evidence.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` -> `50 passed`.

### 2026-04-08: Spec sync follow-up - usersum specification aligned to implementation
**Agent/Contributor**: Codex

**Work completed**:
- Updated `wepppy/weppcloud/routes/usersum/specification.md` to reflect currently implemented behavior:
  - role-resolution mapping (`Root`/`Admin`/`PowerUser`),
  - header `ROLE` selector behavior and option sets,
  - threshold role semantics including repeated/comma role ceiling handling,
  - shell/nav discovery filtering by selected role ceiling,
  - doc role self-report under breadcrumbs.
- Removed stale "specified follow-up" and "known follow-up" items that are now implemented.

**Validation results**:
- `wctl doc-lint --path wepppy/weppcloud/routes/usersum/specification.md` -> `✅ 1 files validated, 0 errors, 0 warnings`.

### 2026-04-08: Security review trial gate
**Agent/Contributor**: Codex

**Work completed**:
- Added dedicated security review artifact:
  - `docs/work-packages/20260408_usersum_role_filter/artifacts/20260408_security_review.md`
- Ran expanded usersum test set:
  - `tests/weppcloud/routes/test_usersum_bp.py`
  - `tests/weppcloud/routes/test_usersum_docs_contracts.py`
  - `tests/weppcloud/routes/test_usersum_docs_index.py`
  - `tests/weppcloud/test_usersum_template_wiring.py`
- Performed manual exploit reproduction against source/raw routes for a developer-only doc.

**Findings**:
- High severity `SEC-01` opened: `/usersum/src` and `/usersum/raw` perform manifest role checks before path canonicalization; non-canonical `..` variants bypass `min_role` visibility.
- Security gate status: `fail` until remediation.

**Next steps**:
- Canonicalize source/raw `rel_path` before manifest lookup and role checks.
- Add regression tests to prevent non-canonical bypass for restricted docs.
- Re-run security artifact and close `SEC-01`.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/routes/test_usersum_docs_contracts.py tests/weppcloud/routes/test_usersum_docs_index.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` -> `56 passed`.

### 2026-04-08: Security remediation - close SEC-01 source/raw canonicalization bypass
**Agent/Contributor**: Codex

**Work completed**:
- Updated `wepppy/weppcloud/routes/usersum/usersum.py` so `/usersum/src` and `/usersum/raw`:
  - resolve to canonical repo-relative markdown paths first,
  - reject non-canonical request variants,
  - perform manifest visibility checks against canonical paths.
- Added route regressions in `tests/weppcloud/routes/test_usersum_bp.py`:
  - `test_usersum_src_route_rejects_noncanonical_path_variant`
  - `test_usersum_raw_route_rejects_noncanonical_path_variant`
- Re-ran dedicated security artifact and marked `SEC-01` resolved.

**Findings**:
- `SEC-01` is closed: non-canonical traversal variants no longer bypass role visibility for manifested restricted docs.
- Security gate status: `pass`.

**Next steps**:
- Optional follow-up: add explicit telemetry/alerting for repeated denied non-canonical source/raw path probes.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/routes/test_usersum_docs_contracts.py tests/weppcloud/routes/test_usersum_docs_index.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` -> `58 passed`.
- Manual repro (anonymous context):
  - `src_normal 404`
  - `src_bypass 404`
  - `raw_normal 404`
  - `raw_bypass 404`

### 2026-04-09 19:10 UTC: Package closeout
**Agent/Contributor**: Codex

**Work completed**:
- Closed `package.md` status and checked all success criteria.
- Moved ExecPlan from `prompts/active/usersum_role_filter_execplan.md` to `prompts/completed/usersum_role_filter_execplan.md`.
- Added closeout outcome summary and final lifecycle notes.
- Updated `PROJECT_TRACKER.md` to move this package from `In Progress` to `Done`.

**Validation results**:
- `wctl doc-lint --path docs/work-packages/20260408_usersum_role_filter --path PROJECT_TRACKER.md` -> pass (`5 files validated, 0 errors, 0 warnings`).

## Watch List

- Keep usersum role filter behavior as discovery-only; do not bypass doc visibility authorization gates.
- Preserve current `/usersum/search` error-path behavior for unauthorized role ceiling requests.

## Communication Log

### 2026-04-08: Work package kickoff
**Participants**: User, Codex  
**Question/Topic**: Execute usersum role-filter package end-to-end with implementation, tests, and QA review.  
**Outcome**: Package opened and implementation started.
