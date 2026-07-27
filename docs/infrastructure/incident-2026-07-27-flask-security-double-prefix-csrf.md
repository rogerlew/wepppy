# Incident: Flask-Security Double-Prefix CSRF Failures

**Date:** 2026-07-27

**Environment:** WEPPcloud production (`wepp1`, `https://wepp.cloud`)

**Status:** Mitigated on `wepp1`; durable image deployment pending

**Severity:** Moderate

## Summary

WEPPcloud's Flask-Security forms generated actions such as
`/weppcloud/weppcloud/register` and `/weppcloud/weppcloud/login`. Caddy owns the
external `/weppcloud` mount, strips it before proxying to Flask, and supplies it
through `X-Forwarded-Prefix`. The application also configured
`SECURITY_URL_PREFIX` from `SITE_PREFIX`, causing Flask-Security to add the mount
a second time.

Registration submissions reached the wrong internal route and returned
`400 Bad Request` with `The CSRF tokens do not match.` Login and the other
Flask-Security endpoints shared the same routing defect.

## Impact

- New users could not submit the registration form.
- Password login forms loaded before mitigation submitted to a double-prefixed
  URL.
- Password recovery, confirmation, password change, and logout URL generation
  were susceptible to the same duplicated prefix.
- OAuth and non-Flask-Security WEPPcloud routes were not identified as affected.

## Scope

Fix Flask-Security route ownership without changing CSRF enforcement,
authentication rules, Caddy routing, session configuration, or unrelated
WEPPcloud endpoints.

## Timeline

All times are Pacific Daylight Time (UTC-07:00) on 2026-07-27.

- **Before 11:00:** Registration failure reported at
  `/weppcloud/weppcloud/register` with `The CSRF tokens do not match.`
- **11:00-11:05:** Source, templates, CSRF contract, proxy notes, and prior
  accessibility evidence inspected. The shared `SECURITY_URL_PREFIX` setting
  was identified as the source of double-prefixed Flask-Security URLs.
- **11:05:** Production preflight confirmed host `wepp1`, healthy Caddy and
  WEPPcloud containers, and two active default-queue jobs. The web-only restart
  did not affect RQ workers.
- **11:06:** The host checkout was patched and `weppcloud` restarted. Validation
  still showed the old route map because production code was contained in the
  image rather than bind-mounted from the host checkout.
- **11:07:** The same one-line patch was applied surgically inside the existing
  container with a timestamped backup. Only `weppcloud` was restarted.
- **11:08:** The container returned healthy. Flask registered `/login`,
  `/register`, `/reset`, `/confirm`, `/change`, `/logout`, and token routes
  without an internal mount prefix.
- **11:09:** Public registration, login, reset, and confirmation pages returned
  200 and rendered actions with exactly one `/weppcloud` prefix. A
  cookie-preserving registration POST using the rendered CSRF token returned
  200. Caddy did not require a restart.
- **11:10:** Repeated public login renders and an invalid-credential POST
  confirmed `/weppcloud/login`. A browser page loaded before the restart still
  retained the old form action until refreshed.

## Root Cause

`config_app()` set both of these concepts to the same value:

```python
app.config["SITE_PREFIX"] = "/weppcloud"
app.config["SECURITY_URL_PREFIX"] = app.config["SITE_PREFIX"]
```

They have different responsibilities in the deployed topology:

- `SITE_PREFIX` and `APPLICATION_ROOT` describe the external mount.
- Caddy strips that mount before forwarding and sets `X-Forwarded-Prefix`.
- `ProxyFix` restores the external prefix when Flask generates public URLs.
- `SECURITY_URL_PREFIX` controls the internal Flask-Security route rules and
  must therefore remain empty.

No automated test pinned this distinction. Existing template tests replaced
`url_for_security()` with a stub, so they could not detect production prefix
composition.

## Resolution

The durable source fix is:

```python
app.config["SECURITY_URL_PREFIX"] = ""
```

`SITE_PREFIX` and `APPLICATION_ROOT` remain unchanged. A configuration
regression test verifies that Flask-Security stays unprefixed for multiple
external mount values.

The live `wepp1` container has the same mitigation. Because that edit resides
in the current container's writable layer, it will be lost when the container
is recreated until a new image containing this commit is deployed.

## Validation

Production evidence:

- `weppcloud` healthy after targeted restart.
- Internal Flask-Security routes contain no `/weppcloud` prefix.
- Public form actions:
  - `/weppcloud/register`
  - `/weppcloud/login`
  - `/weppcloud/reset`
  - `/weppcloud/confirm`
- Legacy `/weppcloud/weppcloud/register` returned 404.
- Registration POST with the GET response's session cookie, referrer, and CSRF
  token returned 200 without a CSRF error.
- Caddy stayed up and was not restarted.

Repository validation is recorded in the commit handoff.

## Hardening Hypothesis and Signals

**Hypothesis:** If Flask-Security route rules remain unprefixed internally, its
public form actions will contain exactly one proxy-managed mount prefix and
valid-CSRF submissions will no longer fail from double-prefix routing.

**Health signals for 14 days:**

- No requests or user reports involving `/weppcloud/weppcloud/login`,
  `/weppcloud/weppcloud/register`, or related auth paths.
- No recurrence of `The CSRF tokens do not match.` on refreshed
  Flask-Security forms.

**Guardrails:**

- Canonical auth pages continue returning 200.
- Valid-CSRF form submissions pass CSRF validation.
- OAuth redirects and post-login/post-logout views retain one external prefix.

No retry, fallback, compatibility alias, or permanent defensive wrapper was
added, so there is no temporary callus requiring sunset.

## Rollback

Before durable deployment, the live container can be restored from:

```text
/workdir/wepppy/wepppy/weppcloud/configuration.py.bak.20260727T180728Z
```

After image deployment, rollback should redeploy the prior image. Restoring the
old configuration reintroduces the incident and is appropriate only if an
unexpected auth-routing regression is more severe.

## Follow-Up

1. Deploy an image containing the source fix to `wepp1`, then `wepp2`, using
   the production deployment runbook.
2. Repeat public GET and valid-CSRF POST validation after image deployment.
3. Monitor the health signals above through 2026-08-10.

## Related CAPTCHA Usability Change

During incident follow-up, users also reported that the Cap.js proof-of-work
step on local login took too long. This was not a cause of the double-prefix or
CSRF failure, but it compounded the authentication experience.

The Cap service previously used its library defaults of 50 challenges at
difficulty 4. The accepted parameterization is one challenge at difficulty 1,
making the interaction effectively click-only while retaining challenge
issuance, redemption, token validation, and fail-closed server verification.
`CAP_CHALLENGE_COUNT` and `CAP_CHALLENGE_DIFFICULTY` expose the values as
positive-integer environment settings and fail at startup if configured with an
invalid value.

The Cap service is shared. This change therefore applies to login,
registration, anonymous create/fork actions, and invisible CAPTCHA gates. It
reduces bot-computation cost substantially; token validation remains, but proof
of work should no longer be treated as a meaningful rate-control layer.
Operators should monitor automated auth abuse and add explicit rate limiting if
needed rather than increasing end-user computation without evidence.

Decision rationale, provenance, alternatives, and rollback are recorded in
`docs/adrs/ADR-0027-cap-click-only-challenge.md`.

## Related Authentication Persistence Change

User reports also established that repeated authentication was a product
defect. REM-03 amended the authoritative session contract so low-friction
ordinary use governs the authentication architecture:

- password login displays remembered login selected by default while preserving
  opt-out;
- opted-in browsers use a rolling 90-day inactivity window;
- refresh occurs only when a valid remember token is already present, avoiding
  Flask-Login's global-refresh behavior that defeats opt-out;
- opting out clears a preexisting remember cookie, and logout clears both
  session and remember cookies;
- the 12-hour rolling Redis session remains unchanged; and
- authentication diagnostics use safe-field allowlists and persist append-only
  under `/wc1/logs/weppcloud/security.log`.

Flask-Login's signed remember token has no server-validated issuance timestamp.
The 90-day value is consequently a browser inactivity policy, not a server-side
replay maximum. The operator accepted that residual risk in favor of the
reported UX requirement; suspected token theft is contained by rotating the
affected user's `fs_uniquifier`.

### Remember-token containment runbook

Use this only for a specific account with suspected remember-token theft:

1. Record the affected user id and incident authorization.
2. Preview the exact account with
   `wctl exec weppcloud python tools/rotate_user_fs_uniquifier.py EMAIL`.
3. Apply the rotation with
   `wctl exec weppcloud python tools/rotate_user_fs_uniquifier.py EMAIL --apply`.
4. Confirm the old remember token and existing browser session no longer
   authenticate, then have the user sign in again.
5. Record the rotation timestamp and affected account id without recording old
   or new token values.

This containment logs the user out on every device; it is intentionally scoped
to an affected account rather than rotating the application secret for all
users.

Production hosts must install `docker/logrotate/weppcloud-security` at
`/etc/logrotate.d/weppcloud-security`. The policy rotates daily or at 20 MiB,
retains 30 compressed archives, and creates the replacement as mode `0600`.
`WatchedFileHandler` makes each Gunicorn worker reopen the renamed file without
the record-loss window introduced by `copytruncate`.

## Related Evidence

- `docs/adrs/ADR-0027-cap-click-only-challenge.md`
- `docs/adrs/ADR-0028-rolling-remembered-login.md`
- `docs/schemas/weppcloud-session-contract.md`
- `docs/schemas/weppcloud-csrf-contract.md`
- `docs/dev-notes/wc-forest-bearhive-duck-dns-flask-security-installation.md`
- `docs/ui-docs/manual-at-pass-20260331.md`
- `docs/standards/hardening-lifecycle-standard.md`
