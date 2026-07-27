# GOV-00A Bounded Authentication Remediation Decision

**Milestone**: GOV-00A-M1C

**Remediation**: REM-03

**Dated package**:
`docs/work-packages/20260727_auth_session_persistence_hardening/`

## Decision

Register the operator-authorized authentication session incident as a bounded
cross-owner remediation. REM-03 borrows only the password-login remember
checkbox GET default and POST opt-out, rolling remember-cookie inactivity
duration/refresh, login/logout cookie boundary, and authentication logging
surfaces from SURF-13, SHR-02, and SHR-04A.

The exact accepted behavior is a checked-by-default password login with
explicit opt-out, a rolling 90-day browser inactivity lifetime with
opt-in-aware refresh, unchanged rolling 12-hour Redis sessions, and
append-only persistent authentication diagnostics that never contain
credential or token values.

## Authority

The WEPPcloud operator authorized the fixes, a dedicated work package, dual
agent review, and the UX-first session principle with conventional rolling
remember cookies and accepted copied-token residual risk on 2026-07-27.
GOV-00A-M1C becomes effective only when the REM-03
contract checkpoint, this registration, both independent reviews, and their
disposition are committed as a standalone ancestor.

## Exclusions

REM-03 does not authorize OAuth authorization changes, account or role policy,
credential storage changes, Redis session lifetime changes, CSRF or CAP
verification policy changes, route-prefix changes, RQ behavior, database
schemas, or unrelated UI work. It does not advance any borrowed owner.

## Security and Compatibility

Security impact is `high`. Opt-in-aware refresh preserves explicit opt-out and
avoids Flask-Login's unsafe global refresh behavior. The browser inactivity
window is not a server-enforced replay maximum; copied-token replay is an
explicitly accepted residual risk unless an operator rotates the affected
user's `fs_uniquifier`.
