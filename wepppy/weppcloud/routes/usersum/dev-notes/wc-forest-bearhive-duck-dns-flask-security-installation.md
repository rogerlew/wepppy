# WEPPcloud Auth Stack on forest.bearhive.internal

Environment: `forest.bearhive.internal` behind pfSense/HAProxy terminating TLS and path-prefixing all application traffic at `/weppcloud`. Flask runs in the `wepppy310-env` conda environment (Python 3.10) with Gunicorn. Sessions backed by Redis, database in PostgreSQL.

## Flask-Security + Flask-Session configuration

* **Blueprint prefixing** — because HAProxy forwards `/weppcloud/*`, Flask must treat `/weppcloud` as the application root. We set:
  * `APPLICATION_ROOT = '/weppcloud'`
  * `SITE_PREFIX = '/weppcloud'`
  * `SECURITY_URL_PREFIX = '/weppcloud'`
  * Custom post-login/logout redirect endpoints (`security_ui.welcome` / `security_ui.goodbye`).
  * `SECURITY_LOGIN_USER_TEMPLATE = 'security/login_user.html'` for the branded template.

* **Session store** — server-side sessions rely on Redis. Settings that mattered:
  * `SESSION_TYPE = 'redis'`
  * `SESSION_REDIS = redis.from_url(...)` (falls back to local Redis with `db=11`).
  * `SESSION_USE_SIGNER = True` to guard against cookie tampering.
  * `SESSION_PERMANENT = False` plus `PERMANENT_SESSION_LIFETIME = 12 hours` to align with operator requirements.
  * For reverse proxy compatibility we leave Flask’s cookie configuration alone, letting HAProxy handle HTTPS. (We previously forced `SESSION_COOKIE_SAMESITE='None'`/`SECURE=True` but that was not required once TLS termination stayed upstream.)

* **Password hashing** — the production database contains bcrypt hashes. We pinned `bcrypt==3.2.2` inside the conda env because newer wheels pulled in incompatible ABI flags on this host. Without that pin Flask-Security refused to verify existing passwords.

## Blueprint layout

* The original single `_security` blueprint only logged Flask-Security signal activity. We split it into a package:
  * `routes/_security/logging.py` (unchanged, still registers at `/security_logging`).
  * `routes/_security/ui.py` with our welcome/goodbye pages plus a delegating login route.
* We register both blueprints explicitly:
  ```python
  app.register_blueprint(security_logging_bp)
  app.register_blueprint(security_ui_bp)
  ```
  and rely on `APPLICATION_ROOT` to place everything under `/weppcloud`. Earlier we tried `url_prefix=SITE_PREFIX`, but that produced `/weppcloud/weppcloud/...` URLs once the proxy path rules were combined. Removing the extra prefix fixed the 404s.

## Templates

* We replaced the stock `security/login_user.html` with a WEPPcloud-themed page (password visibility toggle, inline status messaging). The template still extends `security/base.html` and imports macros from `security/_macros.html`.
* Catch: our legacy `_macros.html` lacked the helpers Flask-Security expects (`render_field_errors`, `render_form_errors`, `prop_next`). Missing functions caused a 500 when the template rendered. Adding those macros restored parity with the upstream Flask-Security templates.
* We added simple `security/welcome.html` and `security/goodbye.html` views for post-auth transitions so users know when they have signed in/out of WEPPcloud.

## Routing gotchas

* Because the proxy adds `/weppcloud`, Flask-Security’s default `/login` still resolves correctly as long as `APPLICATION_ROOT` is set and we expose a blueprint path at `/login`. Our custom blueprint simply calls the core Flask-Security view, avoiding duplicate logic while letting us serve branded templates.
* The initial attempt to alias the login route using `add_url_rule('/weppcloud/login', ...)` failed once Gunicorn reloaded—Flask registered both `/login` and `/weppcloud/login`, but the proxy already prepended `/weppcloud`, resulting in `/weppcloud/weppcloud/login`. Registering the blueprint without an extra prefix is the correct approach.

## Service management tips

* Gunicorn caches templates; always restart after editing Jinja files: `sudo systemctl restart gunicorn-weppcloud.service`.
* Logs live in `/var/log/weppcloud/gunicorn-weppcloud-error.log`. The HAProxy health checks spam `/health` with OPTIONS requests—filter those when hunting for auth issues.

## Validation checklist

1. Navigate to `https://wc.bearhive.duckdns.org/weppcloud/login` — expect the custom login page.
2. Log in with a known account and verify redirected to `/weppcloud/welcome`.
3. Log out — redirected to `/weppcloud/goodbye` with a working “Return to sign in” link.
4. Confirm session cookies originate from our domain and Redis tracks server-side session data.

These settings have been stable across restarts and survive the PfSense/HAProxy reverse proxy path rewriting. 