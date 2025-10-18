# WEPPcloud OAuth 2.0 Integration Specification

## Context and Current State
- WEPPcloud relies on Flask-Security with a SQLAlchemy datastore for password-based authentication, exposing a `User` model that stores email, password hash, confirmation state, and login telemetry, and registers forms during app bootstrap.【F:wepppy/weppcloud/app.py†L167-L258】
- Runtime configuration is driven by `configuration.py`, which loads secrets from environment variables, enables registration, confirmation, and password recovery, and serves the app below a configurable `SITE_PREFIX` (default `/weppcloud`).【F:wepppy/weppcloud/configuration.py†L29-L79】
- The login template renders only username/password flows via Flask-Security helpers and lacks any social sign-in affordances.【F:wepppy/weppcloud/templates/security/login_user.html†L1-L98】
- The user profile page displays immutable account metadata and password change links, but has no concept of linked identities or social providers.【F:wepppy/weppcloud/templates/user/profile.html†L1-L61】
- Authentication routes are wrapped in `routes/_security/ui.py`, which proxies to Flask-Security views and renders welcome/goodbye pages, but does not yet expose OAuth entry points.【F:wepppy/weppcloud/routes/_security/ui.py†L1-L44】

## Goals
1. Allow existing users to authenticate with GitHub, Google, or Microsoft OAuth providers when the provider asserts the same verified email that exists in WEPPcloud.
2. Preserve classic password authentication to avoid breaking internal accounts and automation.
3. Support new-account creation through OAuth, populating the canonical `User` record from provider metadata (email, name) and marking the account confirmed.
4. Capture and persist OAuth identity metadata so users can manage linked providers and so the platform can prevent duplicate account creation.
5. Provide production-ready configuration for both `https://wepp.cloud` and the internal homelab domains (`https://wc.bearhive.duckdns.org`, `https://wc-prod.bearhive.duckdns.org`) so that redirect URIs and secrets are domain-specific.
6. Ensure audit logging, registration restrictions, and security controls remain intact when OAuth flows are used.

## Proposed Architecture
### Library and Flow Selection
- Adopt [Authlib](https://docs.authlib.org/) as the OAuth 2.0 client library. It integrates cleanly with Flask, supports provider-specific quirks, and keeps sensitive credentials out of templates. Add `authlib` to `docker/requirements-uv.txt` and the corresponding conda environment.
- Implement the Authorization Code Grant with PKCE for all providers. While confidential clients may omit PKCE, GitHub and Microsoft now recommend PKCE for additional protection.
- Store provider metadata in configuration, grouped under `OAUTH_PROVIDERS` with keys for `github`, `google`, and `microsoft` (Azure AD v2). Each entry will hold `client_id`, `client_secret`, `authorize_url`, `token_url`, `userinfo_url`, and `scope` defaults. Provide environment overrides such as `OAUTH_GITHUB_CLIENT_ID`, `OAUTH_GITHUB_CLIENT_SECRET`, etc.

### Phase 1: GitHub OAuth Rollout
- Register a GitHub OAuth application per domain. Use `https://wc.bearhive.duckdns.org/weppcloud/github-auth-callback` for the development stack; production will mirror the hostname swap.
- Align configuration with the existing docker `.env` entries: `GITHUB_OAUTH_CLIENTID`, `GITHUB_OAUTH_SECRET_KEY`, and `GITHUB_OAUTH_CALLBACK_URL` now ship with the dev compose file. The configuration loader should support these keys as well as the canonical `OAUTH_GITHUB_CLIENT_ID`/`SECRET`/`REDIRECT_URI` naming to keep backwards compatibility for local setups.
- Redirect base URLs derive from `OAUTH_REDIRECT_SCHEME` (default `https`) and `OAUTH_REDIRECT_HOST` (falls back to `EXTERNAL_HOST`). Document both in environment samples so deployers know how to override callbacks per domain without editing code.
- Seed the `OAUTH_PROVIDERS["github"]` definition with:
  - `authorize_url`: `https://github.com/login/oauth/authorize`
  - `token_url`: `https://github.com/login/oauth/access_token`
  - `userinfo_url`: `https://api.github.com/user`
  - `scope`: `["read:user", "user:email"]`
- Implement `/oauth/github/login` and `/oauth/github/callback` endpoints first. The callback must verify `state`/PKCE, fetch the primary verified email via `https://api.github.com/user/emails`, and link or create accounts following the email-matching rules below.
- Update the login template with a single "Continue with GitHub" button during this phase. Additional providers can be revealed once they are configured.
- Emit audit events tagged with `provider="github"` so early telemetry isolates GitHub usage while the feature is rolled out.

### Phase 2: Google OAuth Rollout
- Configure a Google “Web application” OAuth client per domain. Authorized JavaScript origins should include `https://wc.bearhive.duckdns.org`, `https://wc-prod.bearhive.duckdns.org`, and `https://wepp.cloud`. Authorized redirect URIs map to `/weppcloud/oauth/google/callback` on each host.
- Support both `OAUTH_GOOGLE_CLIENT_ID`/`OAUTH_GOOGLE_CLIENT_SECRET` and the legacy `GOOGLE_OAUTH_*` variables. The configuration loader uses `OAUTH_REDIRECT_SCHEME`/`HOST` to compute defaults when an explicit redirect URI is not provided.
- Default scopes should be `['openid', 'email', 'profile']`, and the client should request `access_type=offline` with `prompt=consent` so refresh tokens are issued for background session renewal.
- Register Authlib using Google’s OpenID configuration (`server_metadata_url=https://accounts.google.com/.well-known/openid-configuration`) so JWKS discovery and token verification happen automatically.
- Surface a Google button beside GitHub in the login template; match Google’s brand colors/iconography so users recognize the flow at a glance.

### Phase 3: ORCID OAuth Rollout
- Create separate ORCID developer applications (production + homelab) and capture `ORCID_OAUTH_CLIENTID`, `ORCID_OAUTH_SECRET_KEY`, and `ORCID_OAUTH_CALLBACK_URL` for each environment. The configuration layer also honors `OAUTH_ORCID_CLIENT_ID`/`OAUTH_ORCID_CLIENT_SECRET` overrides.
- ORCID requires the `/authenticate` scope to fetch the ORCID iD. Add the userinfo request header `Accept: application/json` so public profile data is returned in JSON.
- Parse email addresses from `emails.email[]`, preferring verified + primary entries. If ORCID does not expose an email, synthesize one as `<orcid-id>@orcid.null` so accounts can still be created. The ORCID iD remains the canonical identity and the synthetic address is only used to satisfy uniqueness constraints.
- Render a branded “Sign in with ORCID” button (green circle icon) alongside GitHub/Google. Disabled buttons remain visible so operators can spot misconfigurations quickly.

### Data Model Changes
Create a new table `oauth_account` with the following columns and constraints:
- `id` (PK)
- `user_id` → FK to `user.id`, cascade delete
- `provider` (enum or short string such as `github`, `google`, `microsoft`)
- `provider_uid` (string) unique per provider; stores the stable subject identifier returned by the provider
- `email` (string) last-seen email from the provider
- `access_token` (encrypted/hashed or short-lived storage)
- `refresh_token` (nullable, encrypted)
- `token_expiry` (nullable datetime)
- `scopes` (JSON/text array)
- `created_at` / `updated_at`
Add a uniqueness constraint on `(provider, provider_uid)` to prevent duplicate linkage. Expose a relationship on the `User` model (`oauth_accounts = db.relationship(...)`) to easily enumerate linked identities.【F:wepppy/weppcloud/app.py†L167-L187】 The Alembic migration must create the table, indexes, and relationship metadata.

### Account Linking Logic
- **Existing user, password login:** No change; existing forms continue to post to `security.login` and are handled by Flask-Security.【F:wepppy/weppcloud/templates/security/login_user.html†L14-L47】
- **Existing user, OAuth login:**
  1. User clicks "Continue with {Provider}" on the login page (copy should remind them to select the provider account that uses the same email address as their WEPPcloud profile). The client calls `/oauth/<provider>/login` to build the authorization URL and redirect.
  2. The callback verifies state/PKCE, exchanges the code for tokens, and normalizes the provider profile (email, email_verified flag, display name, subject ID).
  3. If the provider marks the email as verified and a matching confirmed `User` exists, link the provider by creating/updating `oauth_account` and call `login_user` with that user. Persist tokens for silent re-authentication.
  4. If the account exists but is unconfirmed or inactive, redirect to a message instructing them to finish confirmation or contact support.
- **New user via OAuth:**
  1. After callback, check for an existing `oauth_account` or user email; if none exists, create a new `User` record with `email`, `first_name`, `last_name` parsed from provider data, set `active=True`, `confirmed_at=datetime.utcnow()`, and generate a random 32-byte password hashed with Flask-Security to satisfy the model.
  2. Associate the new user to the `oauth_account` entry and log authentication via the existing security logging blueprint.【F:wepppy/weppcloud/routes/_security/logging.py†L1-L118】
  3. Send a welcome email (reuse existing `security_ui.welcome`) and redirect to the configured post-login view.
- **Provider mismatch cases:**
  - If the provider does not return an email (possible for GitHub without `user:email` scope), call the provider's user-email endpoint to retrieve the primary verified email. If still unavailable, prompt the user to supply an email address manually, then validate via confirmation email before creating a `User`.
  - If multiple users share the same email (should not happen because email is unique), abort and raise an audit log entry.

### Configuration and Secrets
- Extend `configuration.py` with helper functions to read OAuth client settings per provider. Provide defaults for scopes:
  - GitHub: `['read:user', 'user:email']`
  - Google: `['openid', 'email', 'profile']`
  - Microsoft: `['openid', 'email', 'profile', 'User.Read']`
- Introduce settings:
  - `OAUTH_REDIRECT_SCHEME`, `OAUTH_REDIRECT_HOST`, optionally derived from `SITE_PREFIX` and `EXTERNAL_HOST` env vars (already defined in `.env` for Docker deployments) to accommodate `wepp.cloud` vs homelab.
  - `OAUTH_ALLOWED_EMAIL_DOMAIN` if we need to enforce US-only registration.
- Register provider metadata inside `config_app` and expose it via `current_app.config['OAUTH_PROVIDERS']` for reuse across blueprints.【F:wepppy/weppcloud/configuration.py†L29-L79】
- Ensure secrets are stored in environment variables for each deployment environment. Document required variables in deployment docs.

### Flask Blueprint and Routing
- Add a new blueprint `security_oauth_bp` under `wepppy/weppcloud/routes/_security/oauth.py` with endpoints:
  - `GET /oauth/<provider>/login` – start authorization, build `redirect_uri` with `url_for('security_oauth.callback', provider=provider, _external=True, _scheme=OAUTH_REDIRECT_SCHEME)`.
  - `GET /oauth/<provider>/callback` – handle response, exchange code, call linking logic, and redirect to `SECURITY_POST_LOGIN_VIEW`.
  - `POST /oauth/<provider>/disconnect` – allow authenticated users to unlink providers (optional, gated behind password reentry for safety).
- Register the blueprint alongside `security_ui_bp` during app bootstrap in `_blueprints_context.register_blueprints` so routes inherit the same `SITE_PREFIX` prefix.
- Integrate with Flask-Security by:
  - Calling `login_user(user, remember=True)` once the OAuth identity is validated.
  - Emitting the same signals (`user_authenticated`, etc.) so that `routes/_security/logging.py` captures events automatically.【F:wepppy/weppcloud/routes/_security/logging.py†L1-L205】

### Template and UI Updates
- Update `templates/security/login_user.html` to render OAuth buttons above the existing form. Each button should be a simple POST/GET to `/oauth/<provider>/login`, styled consistently with provider branding, and separated from the password form with copy like "Or continue with". Include helper text reminding users to choose the provider account that uses the same email address registered with WEPPcloud.【F:wepppy/weppcloud/templates/security/login_user.html†L1-L98】
- Ensure the login page keeps working when JavaScript is disabled; buttons should be plain anchor tags.
- Extend `templates/user/profile.html` to list linked providers, their last login time, and include controls to unlink (when at least one other authentication method remains).【F:wepppy/weppcloud/templates/user/profile.html†L1-L61】
- Provide user messaging for linking errors (e.g., "Your GitHub email is unverified; please confirm your GitHub email or sign in with your password.")

### Deployment and Provider Registration
- **Redirect URIs (register three separate OAuth clients per provider):**
  - Production: `https://wepp.cloud/weppcloud/oauth/<provider>/callback`
  - Homelab (dev): `https://wc.bearhive.duckdns.org/weppcloud/oauth/<provider>/callback`
  - Homelab (test production): `https://wc-prod.bearhive.duckdns.org/weppcloud/oauth/<provider>/callback`
- Provider-specific registration notes:
  - **GitHub:** Register three OAuth apps (production, homelab dev, homelab test production) via GitHub Developer Settings. Configure callback URIs as above. Request `read:user` and `user:email` scopes.
  - **Google:** Use Google Cloud Console > Credentials > OAuth 2.0 Client IDs. Create three web application credentials and add authorized redirect URIs per domain. Enable the "People API" to retrieve profile fields.
  - **Microsoft:** Register an application in Azure AD (single tenant or multitenant as required). Configure three redirect URIs (one per domain), expose permissions `openid`, `profile`, `email`, and `User.Read`. Generate client secret and store securely.
- Document environment variables and secret rotation processes for DevOps.

### Security and Compliance Considerations
- Enforce HTTPS redirect URIs in production/homelab. Production terminates TLS with Caddy (Let's Encrypt certificates); homelab traffic terminates at pfSense/HAProxy with redirects already enforcing HTTPS. Leverage existing `ProxyFix` configuration so Flask sees the correct scheme.【F:wepppy/weppcloud/app.py†L37-L58】
- Validate `state` and `nonce` on callbacks to mitigate CSRF and replay.
- Limit token storage to the minimum necessary; prefer encrypting tokens at rest or storing only refresh tokens. Consider using `itsdangerous.URLSafeTimedSerializer` or database-level encryption if available.
- Respect the existing US-only registration policy by checking the country claim when available (Google `hd`, Microsoft `tenant`, GitHub location) or by adding a manual assertion checkbox after first login if signals are weak.
- Maintain audit logging by emitting Flask-Security signals and optionally adding structured logs for OAuth events in `routes/_security/logging.py`; coordinate with the planned Codex task to ensure security signal logging writes to `.docker-data/weppcloud/logs/security.log` (assumed to exist on each host).

### Email Delivery Improvements
- Current transactional email delivery through `uidaho.edu` SMTP has intermittent delivery issues. Evaluate moving to a dedicated, low-cost service that supports verified domains, SMTP submission, and API access:
  - **Zoho Mail** offers a forever-free tier (up to 5 users, 5 GB each, 250 daily sends) suitable for WEPPcloud's modest notification volume.
  - **Amazon SES** provides a pay-as-you-go model with low per-email cost and 62k free emails/month when sent from an EC2 instance in the same region; requires DNS verification and bounce handling setup.
  - **Mailjet Free** tier (6k emails/month, 200/day) can serve as an alternative with straightforward SMTP credentials.
- Recommendation: pilot Zoho Mail for the quickest path to a reliable SMTP relay while keeping costs minimal, and reassess volume after OAuth rollout.

### Session Management and Long-Term Authentication Strategy
- Continue using `Flask-Session` in the near term: server-side sessions remain necessary for Flask-Security (login state, CSRF tokens) and the planned OAuth state/PKCE storage while the OAuth flows are rolled out to the core Flask UI.【F:wepppy/weppcloud/app.py†L167-L258】
- **Address observed instability after library upgrades:** the Redis-backed `Flask-Session` store preserves pickled session payloads that may reference modules whose import paths changed during dependency bumps, resulting in blank/failed page loads until the session is cleared.【F:wepppy/weppcloud/configuration.py†L72-L79】 Mitigations:
  - Keep session payloads framework-neutral (store only primitive data) and avoid caching serializer-specific objects in the session.
  - Version the `SESSION_KEY_PREFIX` (e.g., `session:v2:`) when deploying releases that change authentication libraries so legacy payloads are logically quarantined and expire naturally.
  - Automate Redis session eviction as part of blue/green deployment or container restarts to guarantee a clean slate after significant auth stack upgrades.
- **Account for Redis persistence and availability:** unexpected Redis restarts or misconfigured persistence (disabled AOF/RDB snapshots) can drop session state, forcing silent logouts or partially initialized views that present as "blank" pages. Verify that the homelab and production Redis instances:
  - Enable at least periodic RDB snapshots (or append-only files) so sessions survive host restarts when desired.
  - Run with `save` intervals tuned to acceptable data loss windows (e.g., `save 300 10`), or run in a managed mode where ephemeral sessions are acceptable but the UI communicates impending logouts.
  - Expose health checks so the Flask layer can detect Redis unavailability, surface a friendly maintenance banner, and short-circuit confusing stack traces.
  - Flush sessions intentionally during deploys using `redis-cli FLUSHDB` or key-prefix deletion rather than relying on unplanned Redis restarts, which can happen mid-request and exacerbate flaky UX.
- Inventory the session consumers outside the monolith and document their interfaces:
  - The Starlette-based browse microservice serves file browsing, download, and metadata routes and currently trusts the upstream proxy for authentication context.【F:wepppy/microservices/browse.py†L1-L70】
  - `preflight2` is a Go WebSocket service that streams checklist updates over Redis and does not yet enforce first-party authentication beyond origin checks.【F:services/preflight2/internal/server/server.go†L1-L118】
  - `status2` is a Go WebSocket service with the same deployment model, subscribing to Redis status channels for browsers.【F:services/status2/README.md†L1-L85】
- Establish a shared JWT authority inside the Flask app once OAuth sign-in succeeds:
  - Mint short-lived (15–30 minute) access tokens signed with RS256 using keys stored in the existing secret management workflow. Embed user ID, email, and role claims plus a `session_id` to correlate with server-side session entries.
  - Publish the public key set via `/.well-known/jwks.json` so Starlette and Go services can validate tokens without calling back to Flask.
- Deliver JWTs to the browser alongside the existing session cookie:
  - Issue the token after each successful login/refresh and store it in a secure, HTTP-only cookie scoped to the site prefix (or return via a one-time POST message that front-end code can store in memory for WebSocket headers).
  - For WebSocket clients (browse, preflight2, status2), require `Authorization: Bearer <token>` during handshake and reject unauthenticated connections.
- Add token verification middleware to each service:
  - Browse: implement a Starlette middleware that validates the JWT, loads the user context, and enforces authorization before serving filesystem routes.【F:wepppy/microservices/browse.py†L18-L66】
  - Preflight2 and Status2: extend the Go servers to parse and verify JWTs (using a JWKS cache) before accepting WebSocket upgrades; surface user context in structured logs for auditing.【F:services/preflight2/internal/server/server.go†L75-L118】【F:services/status2/README.md†L58-L112】
- Introduce refresh tokens (server-side session bound) to renew JWTs without forcing password/OAuth reauth; reuse Flask-Security’s remember token table or add an `oauth_session` table keyed by device to manage revocation.
- Plan for deprecation of direct session coupling once JWT enforcement is proven:
  - Gradually move browse, preflight2, and status2 to treat JWT as the primary credential and fall back to Flask sessions only for the legacy UI.
  - Consider issuing service-specific scopes so future microservices can authorize granular actions without new session flags.

## Implementation Plan
1. **Dependencies & Configuration**
   - Add `authlib` to Python dependencies and update deployment images.
   - Extend `configuration.py` to load provider definitions and expose derived redirect base URLs.
   - Update documentation (.env.example) with new environment variables.
2. **Database Migration**
   - Add the `oauth_account` model and relationship to `User` in `app.py`.
   - Generate an Alembic migration creating the table, FK constraints, indexes, and default timestamps.
   - Provide data backfill script (optional) to pre-associate known OAuth users if applicable.
3. **Blueprint & Service Layer**
   - Create `routes/_security/oauth.py` implementing login, callback, and disconnect endpoints.
   - Add an `OAuthService` helper (`wepppy/weppcloud/utils/oauth.py`) to wrap provider configuration, Authlib client creation, and token exchange.
   - Integrate with Flask-Security by calling `login_user` and emitting signals.
4. **Templates & UI**
   - Update `security/login_user.html` with OAuth buttons and explanatory copy.
   - Enhance `user/profile.html` to surface linked providers and unlink options.
   - Add CSS (in `static-src` if needed) for provider buttons.
5. **Logging & Telemetry**
   - Extend `routes/_security/logging.py` to record OAuth login attempts, including provider, email, and outcome (success/failure) without exposing tokens.
6. **Testing**
   - Unit tests for the OAuth service logic (mock provider responses, ensure linking rules are enforced).
   - Integration tests for the Flask blueprint using Werkzeug test client with mocked Authlib responses.
   - Manual end-to-end validation in staging against GitHub/Google/Microsoft sandboxes.
7. **Deployment**
   - Create provider applications and gather client IDs/secrets for both production and homelab domains.
   - Update infrastructure secrets and restart services.
   - Monitor logs for authentication anomalies after rollout.

## Testing Strategy
- Automated tests should cover:
  - Email-matching logic (existing user vs. new user flows).
  - Error handling when providers omit email or return unverified addresses.
  - CSRF/state validation and redirect correctness under `SITE_PREFIX` configurations.【F:wepppy/weppcloud/configuration.py†L39-L64】
- Manual QA checklist:
  - Password login regression.
  - OAuth login for each provider (existing + new user) on both domains.
  - Unlink/relink from the profile page.
  - Audit log entries present for OAuth events.

## Rollout Considerations
- Perform a phased rollout: enable GitHub first (least risk for internal developers), monitor, then enable Google and Microsoft.
- Provide user communication explaining new login options and how email matching works.
- Maintain a fallback support process for users whose provider email differs from their WEPPcloud email (support can update the canonical email or link accounts manually).
- Review legal/privacy requirements for storing provider tokens and user profile data, updating privacy policies accordingly.


## Registration
- **Github** Settings -> Developer Settings https://github.com/settings/developers
- **Google** hopes and prays https://console.cloud.google.com/auth/overview?project=dev-weppcloud
- **ORCID** Developer Tools https://orcid.org/developer-tools

### env test 
- wctl exec weppcloud env | grep -i OAUTH_GOOGLE
- wctl exec weppcloud env | grep -i ORCID_OAUTH
