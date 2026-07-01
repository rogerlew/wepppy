# Security Review - Auth Cap.js CAPTCHA

## Metadata

- **Package**: `docs/work-packages/20260701_auth_cap_captcha/`
- **Reviewer**: Codex
- **Date**: 2026-07-01
- **Scope reviewed**: local login/register templates and Flask-Security form validation
- **Commit/branch context**: `master`, local working tree
- **Related artifacts**:
  - Code review: N/A
  - QA review: N/A

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: This package changes public authentication form submission behavior and introduces Cap.js verification as a required precondition for local password login and account registration.
- **Threat model assumptions**:
  - Attackers can submit arbitrary POSTs to local login and register endpoints.
  - Cap.js `CAP_SECRET` stays server-side and is never rendered into templates or logs.
  - OAuth authorization links remain controlled by their existing state/PKCE validation path and are outside this local form change.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Low | Auth form availability | Missing or broken Cap.js service config will block local login/register after this change. This is intended fail-closed behavior, but operators need clear docs. | `docs/ui-docs/cap-js-captcha-auth.md`, `wepppy/weppcloud/README.md`, package rollback notes | Document auth-page dependency and rollback. | Resolved |

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: pass
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: ship

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points enforce expected authn/authz checks for changed routes/services.
- [x] Role checks and scope checks are unchanged; local auth remains a public form with Cap.js precondition.
- [x] Session/JWT token validation paths preserve canonical contracts.
- [x] CSRF protections are preserved for browser session mutation paths.
- [x] Cross-service auth token mint/verify flows are not widened unintentionally.
- [x] Error paths do not disclose token contents or auth internals.

### 2) Secrets and Credential Handling

- [x] No new plaintext secrets in repository files, env defaults, or docs examples.
- [x] `*_FILE` secret-file contract is preserved where applicable.
- [x] No secrets passed in argv, query params, or logs.
- [x] No added/changed services mount secrets.
- [x] Rotation and rollback behavior are documented for existing Cap.js dependency.
- [x] Changed code avoids fallback wrappers that silently skip missing secrets.

### 3) Input Validation and Output Safety

- [x] Untrusted `cap_token` input is validated at the Flask-Security form boundary.
- [x] Rendered output paths avoid unsafe HTML/markdown/script injection.
- [x] Failing validation returns explicit generic form errors.

### 4) File System and Run-Tree Boundaries

- [x] No file-system or run-tree behavior changed.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] No queue, worker, or subprocess behavior changed.

### 6) Agentic Tooling and MCP Surfaces

- [x] No agentic tooling or MCP behavior changed.

### 7) Network and External Integrations

- [x] New outbound calls reuse existing `verify_cap_token()` with a six-second timeout.
- [x] Timeouts/retries avoid denial-of-service amplification and unsafe fallback loops.
- [x] Rate limits/throttles remain an operator concern for the public auth surface; this package adds proof-of-work friction but no separate rate limiter.

### 8) CI/CD and Supply Chain

- [x] No new third-party dependencies were added.

### 9) Data Integrity, Locking, and Concurrency

- [x] No NoDb, Redis, or shared-state mutation behavior changed.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Logs do not include raw `cap_token` values; Cap verification errors become generic form validation errors.
- [x] New error handlers do not swallow exceptions silently.
- [x] Rollback and containment steps are documented for the changed scope.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/weppcloud/test_auth_cap_captcha.py --maxfail=1` - 8 passed.
  - `node --check wepppy/weppcloud/static-src/tests/smoke/a11y/axe-runs0.spec.js` - passed.
  - `wctl run-npm lint` - passed.
  - `wctl run-npm test` - 84 suites / 607 tests passed.
  - `wctl doc-lint --path docs/ui-docs/cap-js-captcha-auth.md` - passed.
  - `wctl doc-lint --path wepppy/weppcloud/README.md` - passed.
  - `wctl doc-lint --path wepppy/weppcloud/static-src/tests/smoke/AGENTS.md` - passed.
  - `wctl doc-lint --path PROJECT_TRACKER.md` - passed.
  - `wctl doc-lint --path docs/work-packages/20260701_auth_cap_captcha/package.md` - passed.
  - `wctl doc-lint --path docs/work-packages/20260701_auth_cap_captcha/tracker.md` - passed.
  - `wctl doc-lint --path docs/work-packages/20260701_auth_cap_captcha/artifacts/2026-07-01_security_review.md` - passed.
  - `wctl doc-lint --path docs/work-packages/20260701_auth_cap_captcha/prompts/completed/implementation_exec_plan.md` - passed.
- Manual checks run:
  - Real app render check showed `/login` is OAuth-only in the current container and omits Cap assets; `/weppcloud/register` renders `cap_token` and `cap-widget`.

## Residual Risk

- **Accepted residual risks**:
  - A deployed Cap service outage blocks local password login/register. This is accepted fail-closed behavior for the new auth precondition; OAuth availability depends on configured providers.
- **Follow-up packages/issues**:
  - Manual deployed smoke after rollout.

## Sign-off

- **Security reviewer**: Codex, 2026-07-01
- **Package owner**: Codex, 2026-07-01
