# Authentication Session Persistence Hardening

## Status

In progress.

## Objective

Reduce unnecessary password reauthentication while restoring safe, durable
authentication diagnostics. Password login must visibly select remembered login
by default, respect opt-out, and use a rolling 90-day browser inactivity
lifetime.
Authentication logs must redact secrets and persist under `/wc1`.

## Scope

- Custom Flask-Security login form default behavior.
- Remember-cookie duration and opt-in-aware refresh behavior.
- Authentication log redaction, remember-action diagnostics, and durable path.
- Unit, template, route, configuration, and operational regression coverage.
- Session contract, parameterization ADR, operator documentation, and incident
  follow-up.

## Non-Goals

- Changing the rolling 12-hour Redis session inactivity window.
- Removing explicit logout or weakening cookie security attributes.
- Logging cookie values or user credentials.
- Changing OAuth provider authentication or authorization rules.
- Deploying production changes as part of this package execution.

## Authoritative Contracts

- `docs/schemas/weppcloud-session-contract.md`
- `docs/schemas/weppcloud-csrf-contract.md`
- `docs/standards/contract-first-change-standard.md`
- `docs/standards/parameterization-adr-standard.md`
- GOV-00A-M1C bounded-remediation authority:
  `docs/work-packages/20260716_pure_ui_contract_ratification/artifacts/2026-07-27_auth_session_bounded_remediation_decision.md`

## Success Criteria

- Login GET renders the remember checkbox checked.
- Login POST without `remember` preserves user opt-out.
- Remember-cookie default is 90 days and refreshes only for opted-in browsers.
- Redis session behavior remains rolling 12 hours.
- Password, CSRF, CAPTCHA, session, remember, OAuth, and bearer tokens never
  appear in authentication logs.
- Authentication logs initialize at
  `/wc1/logs/weppcloud/security.log` in production-compatible configuration.
- Diagnostics record only the safe remember action (`set`, `clear`, or absent).
- Focused tests, documentation lint, broad-exception enforcement, and applicable
  repository gates pass.
- Two independent checkpoint reviews and two independent post-implementation
  reviews have no unresolved medium/high findings.

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The package changes authentication persistence and
  security logging of credential-adjacent inputs.
- **Security review artifact**:
  `artifacts/2026-07-27_security_review.md`

## Parameterization ADR Gate

- **ADR required**: yes
- **ADR**: `docs/adrs/ADR-0028-rolling-remembered-login.md`
- **Reason**: Remember-cookie duration and refresh defaults change.

## Hardening Lifecycle

- **Failure signatures**: login checkbox rendered without `checked`; all 405
  inspected Redis sessions expired within 12 hours; security file logging
  reported permission denied; CAPTCHA tokens appeared in container logs.
- **Related work**:
  `docs/infrastructure/incident-2026-07-27-flask-security-double-prefix-csrf.md`,
  `docs/work-packages/20260701_auth_cap_captcha/`, and
  `docs/standards/hardening-lifecycle-standard.md`.
- **Hypothesis**: Checked-by-default rolling remembered login reduces credential
  prompts, while secret redaction and durable logs improve incident evidence
  without exposing tokens.
- **Health signals**: fewer reauthentication complaints; remember action `set`
  on opted-in successful logins; durable security log remains writable.
- **Danger signals**: logout fails to clear remembered identity; unchecked POST
  becomes remembered; any secret appears in logs; unexpected account access.
- **Observation window**: through 2026-10-25.
- **Temporary calluses**: none.

## Deliverables

- Active ExecPlan and living tracker.
- Contract decision and dual checkpoint reviews.
- ADR-0028 and session contract amendment.
- Implementation and regression tests.
- Dedicated security review, code review, QA review, and dispositions.
- Updated incident report and operator/developer documentation.

## References

- `wepppy/weppcloud/auth_forms.py`
- `wepppy/weppcloud/configuration.py`
- `wepppy/weppcloud/routes/_security/logging.py`
- `wepppy/weppcloud/templates/security/login_user.html`
- `tests/weppcloud/test_auth_cap_captcha.py`
- `tests/weppcloud/routes/test_security_logging_role_cache.py`
