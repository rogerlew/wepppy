# SURF-13 Security/Auth Forms Contract Matrix

| Boundary | Risk-bearing contract | Required evidence |
| --- | --- | --- |
| Shared shell | title, messages, menu, safe navigation, no duplicate assets | `test_security_auth_forms.py` actual inheritance renders |
| Login | email/username, current password, remember, next, CSRF, CAP, safe failure | direct matrix + `test_auth_cap_captcha.py` |
| Registration | names/email, new password confirmation, CSRF, CAP, validation | direct matrix + CAP/name-validation suites |
| Confirmation | resend email, CSRF, generic Flask-Security continuation | direct matrix + unchanged configured endpoint |
| Password request | email, CSRF, non-enumerating Flask-Security response | direct matrix + unchanged configured endpoint |
| Password reset | token-owned action, new password confirmation, CSRF | direct matrix with exact token action |
| Password change | authenticated current/new password, CSRF, session effects | direct matrix + unchanged Flask-Security authorization |
| Magic login | email request and login continuation, CSRF | direct matrix; canonical `/login` action verified against installed template |
| Messages | user values/errors escaped; secrets never reflected | hostile value, field-error, and form-error render |
| Email | confirmation/reset/recovery URLs and safe identity presentation | 14-template smoke + 7 hostile HTML renders |
| Cookies/session | scoped login/logout/remember behavior | `test_auth_remember_cookie.py` (10 tests) |
| Logging | no password, token, CAPTCHA, OAuth code, or session value | `test_security_logging_role_cache.py` |
| OAuth boundary | local auth changes do not widen provider callbacks or redirects | OAuth route/callback suites |
| CSRF | browser mutation remains protected; CAP is additive | actual `/login` and `/register` POSTs + `test_csrf_rollout.py` |
| Security | no auth, CSRF, CAP, token, redirect, enumeration, or disclosure widening | `artifacts/2026-07-28_security_review.md` |

SURF-14 profile/session UI, SURF-15 root user mutation, OAuth provider behavior,
and account deletion are excluded.
