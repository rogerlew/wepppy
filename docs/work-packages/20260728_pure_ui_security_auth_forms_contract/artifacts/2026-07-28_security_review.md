# Security Review - SURF-13 Security/Auth Forms Contract

## Metadata

- **Package**:
  `docs/work-packages/20260728_pure_ui_security_auth_forms_contract/`
- **Reviewer**: `/root/surf08_security_review` (independent, read-only)
- **Date**: 2026-07-28
- **Scope reviewed**: Flask-Security form templates and configuration, custom
  CAP forms, CSRF composition, email output, inline clients, cookies/session,
  OAuth boundaries, logging, and the SURF-13 test-only diff
- **Commit/branch context**: uncommitted SURF-13 diff on `master`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: yes
- **Triage rationale**: The package verifies authentication, account mutation,
  CSRF/CAP, credential-adjacent output, cookies/session, and logging boundaries.
- **Threat model assumptions**:
  - Flask-Security remains the route, form, credential, and token authority;
  - WEPPcloud CSRF and CAP controls must compose on local public login and
    registration; and
  - user-controlled values, credentials, tokens, CAPTCHA values, OAuth codes,
    and session identifiers must not be rendered or logged unsafely.

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Login/registration submission | Initial synthetic render and form tests did not prove CSRF and CAP composition at actual Flask-Security endpoints. | Add minimal real `/login` and `/register` POST tests proving missing CSRF is rejected before valid-CSRF/missing-CAP validation. | Resolved |
| SEC-02 | Low | Closeout records | Test totals and the required dedicated review artifact lagged the added route regressions. | Record 11 package Python tests as 9 renders plus 2 route cases and publish this artifact. | Resolved |

## Verdict

- **Gate status**: pass
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: ship

## Surface Checks

- Exact form actions, fields, hidden CSRF controls, CAP wiring, autocomplete,
  values, errors, and continuations are rendered from the real templates.
- Actual Flask-Security login and registration routes reject missing CSRF with
  HTTP 400; valid CSRF cannot bypass missing CAP validation.
- HTML form and email identity output is escaped and required continuation
  links remain present.
- The actual CAP and password-toggle inline scripts are executed under Jest.
- Existing cookie tests retain secure issuance, restoration, opt-out, logout,
  and identity-rotation behavior.
- Existing security-log tests retain identity hashing, form allowlisting,
  token/credential non-disclosure, and restricted append-only file handling.
- No production route, form, template, session, OAuth, logging, queue, worker,
  dependency, secret, or external integration behavior changed.

## Validation Evidence

- `wctl run-pytest` focused auth boundary: 85 passed.
- `wctl run-pytest tests/weppcloud/test_configuration.py --maxfail=1`:
  16 passed.
- `wctl run-npm test -- security_auth_inline`: 2 passed.
- `wctl run-npm lint` and full `wctl run-npm test`: 95 suites/694 tests passed.
- Final broad Python gate: 5,517 passed, 58 skipped.
- Child/parent/root documentation lint and `git diff --check`: passed.

## Residual Risk

External CAP, email, and OAuth providers and production Redis-backed sessions
remain represented by hermetic boundary tests rather than live integrations.
This package does not change those production integrations.

## Sign-off

- **Security reviewer**: `/root/surf08_security_review`, 2026-07-28
- **Package owner**: Codex, 2026-07-28
