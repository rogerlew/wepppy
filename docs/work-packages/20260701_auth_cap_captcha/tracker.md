# Tracker - Auth Cap.js CAPTCHA

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-01 15:40 UTC
**Current phase**: Closed
**Last updated**: 2026-07-01 16:35 UTC
**Next milestone**: Manual deployed smoke after rollout
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `docs/work-packages/20260701_auth_cap_captcha/artifacts/2026-07-01_security_review.md`

## Task Board

### Ready / Backlog
- [ ] Manual deployed login/register smoke after rollout.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created package scaffold, tracker, active ExecPlan, and security review artifact. (2026-07-01 15:40 UTC)
- [x] Added Flask-Security auth form module and wired custom login/register forms. (2026-07-01 16:05 UTC)
- [x] Added Cap.js prompt, token fields, scripts, and shared auth styling for login/register. (2026-07-01 16:05 UTC)
- [x] Added deterministic Cap solver to the Playwright smoke login helper. (2026-07-01 16:15 UTC)
- [x] Added focused auth Cap tests and updated Cap/smoke/operator docs. (2026-07-01 16:20 UTC)
- [x] Completed validation and closed package. (2026-07-01 16:35 UTC)

## Timeline

- **2026-07-01 15:40 UTC** - Package created to add Cap.js protection to public local auth pages.
- **2026-07-01 16:05 UTC** - Implementation completed for forms, templates, script partial, and auth CSS.
- **2026-07-01 16:15 UTC** - Smoke helper updated to solve login-page Cap challenges via challenge/redeem API.
- **2026-07-01 16:35 UTC** - Focused pytest, npm lint/test, JS syntax check, real app render check, and doc lint completed.

## Decisions Log

### 2026-07-01 15:40 UTC: Enforce Cap.js in Flask-Security forms
**Context**: Login and register POSTs are owned by Flask-Security, not custom WEPPcloud route handlers.

**Options considered**:
1. Wrap the `/login` and `/register` routes - risks duplicating or bypassing Flask-Security behavior.
2. Add client-only widget markup - improves UX but does not enforce the token.
3. Add custom Flask-Security form subclasses that validate `cap_token` while preserving existing form processing.

**Decision**: Use custom Flask-Security login/register forms with a shared Cap.js validation mixin.

**Impact**: Local auth POSTs reject missing/failed Cap.js verification while OAuth links and Flask-Security's existing account/password logic remain unchanged.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Missing Cap.js config blocks local login/register | High | Medium | Fail explicitly and document the dependency; tests patch verification and do not require network. | Open |
| Raw CAPTCHA tokens leak into logs or error text | High | Low | Do not log submitted token values; form error text is generic. | Mitigated |
| OAuth links accidentally gated | Medium | Low | Keep OAuth buttons as links outside the local password form and test OAuth-only login suppresses Cap assets. | Mitigated |

## Hardening Signal Log

- **Baseline health signals**: Login/register templates render without Cap.js prompts and local auth forms can be submitted without `cap_token`.
- **Post-change health signals**: Focused tests assert rendered widgets/assets, OAuth-only suppression, and form rejection/acceptance paths.
- **Danger signals observed**: Real app login has local password login disabled in the current container, so `/login` renders OAuth-only and correctly omits Cap assets; `/weppcloud/register` renders Cap token/widget.
- **Temporary callus register**: none.
- **Softening experiments**: none.

## Verification Checklist

### Code Quality
- [x] Focused pytest passes.
- [x] Frontend lint/test passes.
- [x] Docs lint passes for changed package/docs files.
- [x] No broad exception handlers introduced.

### Security
- [x] Security impact triage recorded as high with rationale.
- [x] Dedicated security review artifact is present and complete.
- [x] No unresolved medium/high security findings remain in the security artifact.
- [x] CSRF protections are preserved for browser session mutation paths.
- [x] Error paths do not disclose token contents or auth internals.

### Documentation
- [x] Cap.js auth docs updated.
- [x] Work package closure notes complete.

### Testing
- [x] Login template wiring covered.
- [x] Register template wiring covered.
- [x] Missing/failing/accepted Cap.js validation covered for local login/register forms.

### Deployment
- [x] Rollback plan documented.

## Progress Notes

### 2026-07-01 15:40 UTC: Package scaffold
**Agent/Contributor**: Codex

**Work completed**:
- Created package shell for auth Cap.js work.
- Recorded security triage and initial decision to use Flask-Security form validation.

**Blockers encountered**:
- None.

**Next steps**:
- Implement form validation and auth template wiring.
- Add focused tests and update docs.

**Test results**: Not run yet.

### 2026-07-01 16:35 UTC: Implementation and closeout
**Agent/Contributor**: Codex

**Work completed**:
- Added Cap.js validation forms in `wepppy/weppcloud/auth_forms.py` and wired them from `wepppy/weppcloud/app.py`.
- Updated local login/register templates and auth CSS.
- Updated Playwright smoke auth helper to fill `cap_token` through the Cap challenge/redeem API.
- Updated Cap.js docs, WEPPcloud README, and smoke playbook notes.
- Completed package/security review closeout.

**Blockers encountered**:
- WTForms did not collect `cap_token` when the field lived only on a plain mixin. Resolved by declaring the field directly on both concrete Flask-Security form classes.
- The running dev app currently renders OAuth-only login; resolved by adding a regression that skips Cap assets when `enable_local_login=False` and verifying `/weppcloud/register` still renders Cap UI.

**Next steps**:
- Manually smoke deployed login/register after rollout with a live Cap service.

**Test results**:
- `wctl run-pytest tests/weppcloud/test_auth_cap_captcha.py --maxfail=1` - 8 passed.
- `node --check wepppy/weppcloud/static-src/tests/smoke/a11y/axe-runs0.spec.js` - passed.
- `wctl run-npm lint` - passed.
- `wctl run-npm test` - 84 suites / 607 tests passed.
- Real app render check: `/login` OAuth-only omitted Cap assets; `/weppcloud/register` rendered `cap_token` and `cap-widget`.

## Watch List

- **Automated smoke login**: Playwright smoke docs say `dev-agent` bypasses CAP. If the live smoke login path starts failing, document whether a test-only bypass or Cap token solver is required.

## Communication Log

### 2026-07-01 15:40 UTC: Initial scope
**Participants**: User, Codex
**Question/Topic**: Add Cap.js to login and register pages with tests.
**Outcome**: Scoped as a high-security-impact auth form hardening package using existing Cap.js service contracts.
