# SURF-14 User Profile/Session Contract Matrix

| Boundary | Risk-bearing contract | Verified evidence |
| --- | --- | --- |
| Account details | escaped name, email, role list/empty state | ordinary, empty, privileged, and hostile actual renders |
| Navigation | password change, logout, Diagnostics browser reset | actual render; ProxyFix prefix; route/session suites |
| Providers | sorted escaped identity, canonical disconnect POST and CSRF | linked/hostile renders; OAuth route suite |
| Token visibility | Admin/PowerUser/Dev/Root only | ordinary/privileged renders and route role tests |
| Token mint | POST, same-origin credentials, CSRF, role gate, no-store | actual client; CSRF-before-role and route tests |
| Token output | readonly, explicit success only, no persistence/logging | actual client and direct markup render |
| Token copy | Clipboard API with bounded fallback and safe status | Clipboard success and both fallback outcomes |
| Role mutation | no profile role controls; Root-only SURF-15 owner | absence regression and retained Root route authority |
| Session/reset | authenticated profile, logout cookies, Diagnostics-owned reset | profile, cookie/logout, and Diagnostics suites |
| Security | no privilege, CSRF, token, identity, provider, or session widening | dedicated review PASS; no unresolved findings |
