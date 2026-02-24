# Tracker - WEPPcloud CSRF Rollout with rq-engine API Compatibility

## Quick Status

**Started**: 2026-02-24  
**Current phase**: Milestone 7 closeout complete  
**Last updated**: 2026-02-24  
**Next milestone**: None (package complete).

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Work-package directory created at `docs/work-packages/20260224_weppcloud_csrf_rollout/`.
- [x] `package.md` authored with scope/objectives/success criteria.
- [x] Active ExecPlan drafted in `prompts/active/weppcloud_csrf_rollout_execplan.md`.
- [x] `PROJECT_TRACKER.md` updated to register this package as in-progress.
- [x] Route inventory + classification artifacts published (`route_inventory_raw.txt`, `route_classification.md`, `csrf_exemptions_register.md`).
- [x] Global CSRFProtect enabled in WEPPcloud app and config toggles added.
- [x] Base template CSRF token source + browser form/fetch token propagation implemented.
- [x] Bootstrap forward-auth verify endpoint exemption wired with explicit rationale.
- [x] OAuth disconnect migrated from manual validation to global CSRF + preserved UX handling.
- [x] rq-engine session-token cookie path same-origin enforcement implemented.
- [x] CSRF + same-origin regression coverage added/updated.
- [x] Required review artifacts published (`reviewer_findings.md`, `code_quality_review.md`).
- [x] Final validation summary published (`final_validation_summary.md`).
- [x] Base template inline CSRF bootstrap extracted to `static/js/csrf_bootstrap.js` with targeted Jest coverage.
- [x] Changed-file broad-exception enforcement restored to PASS by synchronizing allowlist line positions.
- [x] rq-engine proxy hardening applied: forwarded origin aliases now require explicit opt-in (`RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS=true`).
- [x] rq-engine API compatibility coverage expanded to verify bearer-token path remains functional with cross-origin/forwarded headers.
- [x] Post-closeout regression fix: `controlBase` job polling now upgrades to bearer-auth polling after 401/403 and surfaces `error.detail` inline in the run status panel.
- [x] Post-closeout compatibility fix: same-origin cookie/auth bridge checks now accept browser fetch metadata (`Sec-Fetch-Site: same-origin`) with regression coverage in rq-engine + WEPPcloud route tests.

## Milestones

- [x] Milestone 0: package scaffold + executable plan + project tracker registration.
- [x] Milestone 1: baseline route classification + exemption register.
- [x] Milestone 2: Flask CSRF middleware/configuration + base template token source.
- [x] Milestone 3: route hardening/exemptions + bridge endpoint alignment.
- [x] Milestone 4: targeted validation tests and docs sync.
- [x] Milestone 5: correctness review pass and disposition.
- [x] Milestone 6: code quality review pass and disposition.
- [x] Milestone 7: closeout artifacts + tracker/package synchronization.

## Decisions

### 2026-02-24: Preserve bearer-token API ergonomics for rq-engine/browse/files

**Context**: Third-party and agent clients depend on `Authorization: Bearer` flows that are not cookie-authenticated browser requests.

**Decision**: CSRF enforcement is scoped to WEPPcloud cookie-auth mutation routes. Bearer-token API routes remain CSRF-agnostic.

**Impact**: Security hardening lands without forcing CSRF-token handling changes on external API consumers.

### 2026-02-24: Use global CSRF middleware with explicit exemptions, not piecemeal per-route decorators

**Context**: WEPPcloud has many mutation routes; per-route add-only strategy is error-prone and can leave silent gaps.

**Decision**: Enable global CSRF middleware and maintain a narrow, documented exemption register for boundary routes.

**Impact**: Safer default posture with explicit exceptions and better long-term maintainability.

## Risks and Mitigations

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Regress third-party API clients by forcing CSRF on bearer routes | High | Low | Keep CSRF scoped to cookie-auth Flask routes; add rq-engine bearer regression tests | Mitigated |
| Break browser mutation flows due to missing token propagation | High | Medium | Base template token source + same-origin fetch/form propagation + CSRF route tests | Mitigated |
| Overuse `@csrf.exempt` and weaken protections | High | Medium | Single explicit exemption documented with rationale + regression coverage | Mitigated |
| CSRF enforcement causes noisy test failures | Medium | Medium | Added focused CSRF tests and adjusted rq-engine cookie-path tests for origin contract | Mitigated |

## Verification Checklist

- [x] Route inventory artifact captured.
- [x] Exemption register artifact captured with rationale and owner.
- [x] `wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py`
- [x] `wctl run-pytest tests/weppcloud/routes/test_bootstrap_bp.py tests/weppcloud/routes/test_bootstrap_auth_integration.py`
- [x] `wctl run-pytest tests/weppcloud/routes/test_user_profile_token.py`
- [x] `wctl run-pytest tests/microservices/test_rq_engine_session_routes.py`
- [x] `wctl run-npm test -- http`
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- [x] `python3 tools/code_quality_observability.py --base-ref origin/master`
- [x] Correctness review pass completed and findings dispositioned.
- [x] Code quality review pass completed and findings dispositioned.
- [x] `wctl doc-lint --path docs/work-packages/20260224_weppcloud_csrf_rollout`

## Progress Notes

### 2026-02-24: Package initialization

- Created package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- Registered package under `PROJECT_TRACKER.md` as in-progress.
- Defined explicit review gates (correctness + code quality) as required milestones.

### 2026-02-24: CSRF rollout implementation + closeout

- Implemented global WEPPcloud CSRF middleware + configuration toggles.
- Added base template CSRF token source and default browser propagation for same-origin form/fetch mutation requests.
- Preserved non-browser boundary behavior by explicitly exempting `/api/bootstrap/verify-token`.
- Added rq-engine cookie-path same-origin protection while preserving bearer-token compatibility.
- Completed required test and review gates.
- Extracted inline CSRF bootstrap logic to a dedicated static module (`static/js/csrf_bootstrap.js`) and added focused Jest coverage (`controllers_js/__tests__/csrf_bootstrap.test.js`).
- Re-synchronized broad-exception boundary allowlist line positions and restored changed-file enforcement to PASS.
- Added proxy hardening follow-up in `rq_engine/session_routes.py` and regression tests proving strict default + opt-in proxy alias behavior while preserving bearer API functionality.
- Published closeout artifacts (`final_validation_summary.md`, review findings docs) and synchronized plan/tracker state.

### 2026-02-24: Polling auth/detail regression patch

- Updated `controllers_js/control_base.js` polling to attempt unauthenticated reads first and automatically retry with `requestWithSessionToken` when rq-engine polling requires auth (401/403).
- Added inline rendering of `error.detail` for job-status refresh failures so backend messages such as `Authentication required.` are visible without waiting for delayed stacktrace backfill.
- Added Jest regression coverage in `controllers_js/__tests__/control_base.test.js` and rebuilt `wepppy/weppcloud/static/js/controllers-gl.js`.

### 2026-02-24: Same-origin fetch-metadata compatibility patch

- Updated same-origin checks in `wepppy/microservices/rq_engine/session_routes.py` and `wepppy/weppcloud/routes/weppcloud_site.py` to accept browser `Sec-Fetch-Site: same-origin` and reject explicit `cross-site` before falling back to `Origin`/`Referer`.
- Added microservice route coverage for fetch-metadata allow/block behavior and WEPPcloud auth-bridge coverage for the same metadata path.
