# Auth Cap.js CAPTCHA

**Status**: Closed (2026-07-01)
**Timezone**: UTC

## Overview
The local password login and account registration pages are public authentication surfaces. This package adds the existing Cap.js verification flow to those pages so anonymous clients must solve a CAPTCHA before submitting password-login or registration forms.

## Objectives
- Render the existing Cap.js widget and assets on the WEPPcloud login page.
- Render the existing Cap.js widget and assets on the WEPPcloud registration page.
- Enforce `cap_token` server-side through Flask-Security form validation before local login or registration can succeed.
- Keep OAuth login links and authenticated bypass behavior unchanged.
- Add focused regression tests for template wiring and form validation.

## Scope

### Included
- Flask-Security login/register form subclasses in `wepppy/weppcloud/app.py`.
- Auth template wiring in `wepppy/weppcloud/templates/security/login_user.html`, `wepppy/weppcloud/templates/security/register_user.html`, and shared security layout/macros if needed.
- Documentation updates for the Cap.js auth contract.
- Focused pytest coverage under `tests/weppcloud/`.

### Explicitly Out of Scope
- Replacing the existing Cap.js service or widget implementation.
- Adding CAPTCHA to password reset, confirmation, passwordless login, or OAuth callback flows.
- Adding a new external dependency.
- Changing Cap.js key generation, storage, Caddy routing, or service deployment.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extraction
- **Authoritative source path(s)**: `docs/ui-docs/cap-js-captcha-auth.md`, `wepppy/weppcloud/utils/cap_verify.py`, `wepppy/weppcloud/templates/shared/cap_macros.htm`
- **Cutover proof required**: login and register templates render Cap.js assets/widgets and form tests prove missing or rejected tokens fail validation while accepted tokens allow the underlying Flask-Security form checks to proceed.
- **Acceptance evidence type**: fixture-only

## Stakeholders
- **Primary**: WEPPcloud operators and users of password-based authentication.
- **Reviewers**: WEPPcloud auth/UI maintainers.
- **Security Reviewer**: Required because public auth POST behavior changes.
- **Informed**: Operators maintaining Cap.js keys and service health.

## Success Criteria
- [x] Login page includes a Cap.js prompt, hidden `cap_token`, and widget asset scripts when local password login is enabled.
- [x] Register page includes a Cap.js prompt, hidden `cap_token`, and widget asset scripts.
- [x] Local password login rejects missing or failed Cap.js verification without logging raw tokens.
- [x] Local registration rejects missing or failed Cap.js verification without logging raw tokens.
- [x] OAuth provider links remain plain links and do not require a Cap.js token.
- [x] Focused tests and doc lint pass.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites
- Existing Cap.js service, widget assets, and server verification helper are available.
- Flask-Security remains the owner of local password login and registration processing.

### Blocks
- Reduced automated abuse exposure on password-login and registration POSTs.

## Related Packages
- **Related**: `docs/mini-work-packages/completed/20251223_interfaces_cap_floating_captcha.md`
- **Related**: `docs/ui-docs/cap-js-captcha-auth.md`
- **Related**: `docs/schemas/weppcloud-csrf-contract.md`

## Timeline Estimate
- **Expected duration**: 1 focused session
- **Complexity**: Medium
- **Risk level**: High

## Security Impact and Review Gate
- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The package changes public authentication forms and introduces an external verification dependency into login and registration POST validation.
- **Security review artifact**: `docs/work-packages/20260701_auth_cap_captcha/artifacts/2026-07-01_security_review.md`

## Hardening and Callus Softening
- **Failure signature(s)**: unauthenticated clients can currently submit local login/register POSTs without completing Cap.js verification.
- **Related prior hardening efforts**: interfaces create/fork Cap.js rollout and invisible anonymous route gating.
- **Health signals**: auth form tests reject missing/failed `cap_token`; rendered pages include expected Cap.js assets.
- **Danger signals**: OAuth links broken, CSRF removed, raw Cap tokens logged, missing Cap config silently permits login/register, or automated smoke `dev-agent` login is not updated if it needs a Cap bypass.
- **Observation window**: 14 days after deployment.
- **Temporary calluses introduced**: None planned.
- **Callus softening hypothesis (if applicable)**: N/A.

## References
- `wepppy/weppcloud/app.py` - Flask app setup and Flask-Security form registration.
- `wepppy/weppcloud/templates/security/login_user.html` - local login and OAuth provider UI.
- `wepppy/weppcloud/templates/security/register_user.html` - local account registration UI.
- `wepppy/weppcloud/templates/shared/cap_macros.htm` - existing Cap.js prompt macro.
- `wepppy/weppcloud/utils/cap_verify.py` - existing server-side token verification helper.
- `docs/ui-docs/cap-js-captcha-auth.md` - canonical Cap.js UI/server contract.

## Deliverables
- `wepppy/weppcloud/auth_forms.py` adds `ExtendedLoginForm` and `ExtendedRegisterForm` with shared Cap.js token validation.
- `wepppy/weppcloud/app.py` wires both custom forms into Flask-Security.
- `wepppy/weppcloud/templates/security/login_user.html` and `register_user.html` render Cap.js prompts, hidden token fields, and widget assets.
- `wepppy/weppcloud/templates/security/_cap_form_script.html` copies solved Cap tokens into local auth forms and opens the floating challenge on empty submit attempts.
- `wepppy/weppcloud/static/css/ui-foundation.css` adds shared Cap prompt styling for auth pages.
- `wepppy/weppcloud/static-src/tests/smoke/a11y/axe-runs0.spec.js` solves login-page Cap challenges programmatically for the `dev-agent` smoke login path.
- `tests/weppcloud/test_auth_cap_captcha.py` covers template wiring, OAuth-only script suppression, and Cap token validation paths.
- Cap.js auth documentation and smoke playbook notes were updated.

## Follow-up Work
- Manually smoke the browser login/register flow against a deployed Cap service after rollout, including OAuth-only and local-login-enabled configurations.

## Closure Notes

**Closed**: 2026-07-01

**Summary**: Local login and registration now use the existing Cap.js service contract. The local password forms render a prompt and hidden token field, and Flask-Security validation requires a successful `verify_cap_token()` result before login/register processing can continue. OAuth-only login remains free of Cap assets when the local password form is disabled.

**Lessons Learned**: WTForms does not collect fields declared only on a plain mixin for these Flask-Security subclasses, so the concrete login/register form classes declare `cap_token` directly and share only the validator method. The real app render check also exposed OAuth-only login asset loading, which is now gated behind `local_login_enabled`.

**Archive Status**: Work-package artifacts are retained under `docs/work-packages/20260701_auth_cap_captcha/`; the completed ExecPlan is in `prompts/completed/`.
