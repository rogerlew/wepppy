# Tracker - Admin Run-Scoped Token Minting for Sync and Debug Workflows

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-04-01  
**Current phase**: Complete  
**Last updated**: 2026-04-01  
**Next milestone**: None (package closed).

## Task Board

### Ready / Backlog
- [x] Run full QA gates after implementation and doc updates.

### In Progress
- [x] Implement admin-only run token endpoint and PowerUser panel controls.

### Blocked
- [x] None.

### Done
- [x] Created work-package scaffold and active ExecPlan (2026-04-01).
- [x] Added `POST /runs/<runid>/<config>/mint-run-token` with admin-only role gate and 24-hour run-scoped service-token issuance.
- [x] Added admin-only PowerUser Actions card for mint/copy run token using profile token styles.
- [x] Added route + template tests for auth/claims/TTL and admin-only visibility.
- [x] Updated auth contract and usersum docs.
- [x] Completed code and QA review artifacts with medium/high findings resolved.

## Timeline

- **2026-04-01** - Package created, scope and execution plan drafted.
- **2026-04-01** - Implemented route, template, and tests.
- **2026-04-01** - Completed docs updates, QA gates, and closure artifacts.

## Decisions Log

### 2026-04-01: Mint run-scoped token as `service` token class
**Context**: Token must work for server-to-server sync and run-scoped endpoint debugging beyond owner-bound user-token checks.

**Options considered**:
1. Issue `user` token bound to current admin subject.
2. Issue `service` token scoped to the target run.

**Decision**: Use `service` token class with explicit `runs=[runid]`, plus admin role claims and broad run-debug scopes.

**Impact**: Better portability for cross-server sync and consistent run-scope authorization behavior in browse/rq-engine.

### 2026-04-01: Preserve auth HTTP errors in mint endpoint
**Context**: A broad route-level exception catch can mask authorization failures (`403`) as `500`.

**Decision**: Preserve `HTTPException` by re-raising and remove newly introduced broad catch from `mint_run_token`.

**Impact**: Access-denied responses remain explicit and contract-aligned; unexpected failures are no longer silently translated.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Over-permissioned token scopes | High | Medium | Restrict endpoint to Admin/Root; fixed 24h TTL; document intended use | Mitigated |
| UI leakage to non-admin users | Medium | Low | Conditional rendering + template regression test | Mitigated |
| Contract drift with token spec docs | Medium | Medium | Update `docs/dev-notes/auth-token.spec.md` in same change | Mitigated |

## Verification Checklist

### Code Quality
- [x] Targeted route/template tests pass.
- [x] Broader `weppcloud` route smoke tests pass where impacted.
- [x] No medium/high review findings left unresolved.

### Documentation
- [x] Token contract docs updated.
- [x] Usersum/operator-facing note updated.
- [x] Work package docs updated for closure.

### Testing
- [x] Endpoint auth + claims + TTL covered by tests.
- [x] Admin-only control visibility covered by template test.
- [x] Manual mint/copy interaction reviewed in rendered markup/JS contract.

## Progress Notes

### 2026-04-01: Implementation + validation complete
**Agent/Contributor**: Codex

**Work completed**:
- Implemented admin-only run token endpoint and 24-hour service-token claims contract.
- Added admin-only PowerUser mint/copy controls with profile-token visual patterns.
- Added and extended tests in:
  - `tests/weppcloud/routes/test_user_profile_token.py`
  - `tests/weppcloud/routes/test_pure_controls_render.py`
- Updated docs in:
  - `docs/dev-notes/auth-token.spec.md`
  - `wepppy/weppcloud/routes/usersum/weppcloud/getting-started.md`
- Closed code/QA review findings and captured artifacts:
  - `artifacts/code_review_findings.md`
  - `artifacts/qa_review_findings.md`

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_user_profile_token.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `49 passed`
- `wctl run-pytest tests/weppcloud/routes --maxfail=1` -> `432 passed`
- `wctl doc-lint --path docs/dev-notes/auth-token.spec.md --path wepppy/weppcloud/routes/usersum/weppcloud/getting-started.md --path docs/work-packages/20260401_admin_run_token_minting` -> `5 files validated, 0 errors, 0 warnings`
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> `PASS`

## Communication Log

### 2026-04-01: Request framing
**Participants**: User, Codex  
**Topic**: Add 24-hour admin-only run-scoped token minting in PowerUser panel and complete as full work package with code/QA review.  
**Outcome**: Implemented and validated end-to-end; package closed.
