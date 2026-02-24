# CSRF Exemptions Register - WEPPcloud

Date: 2026-02-24

## Policy

- Exemptions must be explicit and route-level.
- Each exemption must document boundary rationale and compensating controls.
- Broad blueprint-level exemptions are not permitted for this rollout.

## Active Exemptions

| Route | File | Status | Rationale | Compensating Controls |
| --- | --- | --- | --- | --- |
| `/api/bootstrap/verify-token` (`GET`,`POST`) | `wepppy/weppcloud/routes/bootstrap.py` | Approved | Infrastructure `forward_auth` boundary for Caddy/git-agent traffic; not a browser cookie-mutation UI route | `verify_forward_auth_context(...)`, bootstrap eligibility checks, opt-in checks, fixed 401 deny contract |

## Rejected Exemption Candidates

| Route | Decision | Reason |
| --- | --- | --- |
| `/api/auth/rq-engine-token` | Rejected | Browser cookie-auth token bridge; should remain CSRF-protected plus same-origin-gated. |
| `/api/auth/session-heartbeat` | Rejected | Browser session mutation endpoint; should remain CSRF-protected plus same-origin-gated. |
| `/api/auth/reset-browser-state` | Rejected | Browser cookie/session clear endpoint; should remain CSRF-protected plus same-origin-gated. |
| `/cap/verify` | Rejected | Browser flow can provide CSRF token; route remains protected. |
