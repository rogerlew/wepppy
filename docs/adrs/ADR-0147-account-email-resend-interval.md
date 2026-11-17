# ADR-0147: Account email resend interval

Date: 2026-11-17
Status: Accepted for implementation; not deployed

## Decision

Account verification/setup sends are limited to one attempt per account per 60 seconds, recorded in the existing account database under a row lock. Expose `ACCOUNT_EMAIL_RESEND_SECONDS` with default 60. Keep existing Flask-Security confirmation-link expiry rather than introducing a second expiry default. Signup retains CAPTCHA and recovery retains its current CSRF controls.

## Rationale

A short resend delay bounds accidental repeat clicks and account-targeted mail bursts without adding a service or CAPTCHA to recovery. Mail failure retains the delay to avoid retry storms; users receive a retry message. Alternative unbounded sends were rejected; long lockouts would impede signup. This is an operational abuse-control threshold, not scientific parameterization.

## Validation and recovery

Test concurrent attempts, cooldown boundary, delivery failure, and configurable interval. Token completion remains independently bound to purpose/account/email/revision and single use. Changing the interval does not change link expiry or reset credentials. No live configuration or deployment is authorized.
