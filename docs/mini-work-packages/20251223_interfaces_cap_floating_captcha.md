# Mini Work Package: Interfaces floating Cap.js gate

**Status:** Draft  
**Last Updated:** 2025-12-24  
**Primary Areas:** `wepppy/weppcloud/templates/interfaces.htm`, `wepppy/weppcloud/controllers_js/*`, `wepppy/weppcloud/routes/run_0/run_0_bp.py`, `wepppy/weppcloud/configuration.py`, `services/cap`, `docker/docker-compose.*.yml`, `docker/caddy/Caddyfile`, `/workdir/cap`

---

## Objective
Add Cap.js floating CAPTCHA to the interfaces page for anonymous users. Each interface section has its own widget. Create actions remain disabled until a CAPTCHA solve, then POST the Cap token to the create endpoint. The `/create/<config>` route must accept valid Cap tokens for anonymous users or allow authenticated users without a token.

## Review Notes
- `run_0.create` will move to POST; confirm all create entry points migrate before tightening GET behavior.
- `interfaces.htm` uses a right-click unitizer menu that reads `activeLink.href`; moving to POST needs a new data source for menu navigation.
- Cap requires a backend plus widget assets; the plan uses a new microservice wrapping `@cap.js/server` and serves assets from the Cap clone.
- No silent fallback for missing Cap configuration; fail fast with explicit errors for anonymous create.

## Plan (multi-phase)

### Phase 1 - Design + config
1. Add a Cap microservice in `services/cap` that wraps `@cap.js/server` and exposes:
   - `POST /cap/<site_key>/challenge`
   - `POST /cap/<site_key>/redeem`
   - `POST /cap/<site_key>/siteverify`
   - `GET /cap/assets/*` for widget, floating, and wasm assets sourced from `/workdir/cap`
2. Define config names and defaults (env placeholders now; app config wiring during backend integration):
   - `CAP_BASE_URL` (server base, ex: `https://<host>/cap`)
   - `CAP_SITE_KEY` and `CAP_SECRET`
   - `CAP_ASSET_BASE_URL`
   - `CAP_CORS_ORIGIN`

## Phase 1 Handoff Summary
- Implemented the Cap microservice wrapper in `services/cap/server.js` with `/cap/health`, challenge/redeem/siteverify, and asset endpoints backed by `/workdir/cap`.
- Added service Dockerfiles for dev/prod at `services/cap/Dockerfile.dev` and `services/cap/Dockerfile`.
- Added Cap env placeholders in `docker/.env` and verified the service responds on `/cap/health`.

### Phase 2 - Frontend integration (interfaces page)
1. Use `POST` form with token in body and 303 redirect to run page (no tokens in URLs).
2. Lock the integration scope: only interfaces page and `/create/<config>`.
3. Render a Cap widget per interface section for anonymous users only:
   - Insert `<cap-widget>` above `.wc-feature__actions` with unique ids.
   - Set `data-cap-api-endpoint` to `CAP_BASE_URL + "/" + CAP_SITE_KEY + "/"`.
4. Add `data-cap-floating="#<widget-id>"` to each create action trigger and set `data-cap-floating-position="top"` to float above the buttons.
5. Disable create links until solved:
   - Replace links with POST forms and store the target in `data-run-action`.
   - Disable submit buttons (`disabled`, `aria-disabled`) and apply a disabled CSS class.
6. Add a small controller (new `wepppy/weppcloud/controllers_js/interfaces_captcha.js` or inline script):
   - On `solve`, enable submit buttons in the same section and inject `cap_token` into a hidden input.
   - Ensure right-click menu uses `data-run-action` (or another form-based source) for navigation.
7. Load Cap assets only for anonymous users:
   - `cap-widget` script and `cap-floating` from the Cap microservice asset paths.
   - Set `window.CAP_CUSTOM_WASM_URL` to `/cap/assets/cap_wasm.js`.

### Phase 3 - Backend token validation
1. Add a helper module (ex: `wepppy/weppcloud/utils/cap_verify.py`) to call:
   - `POST {CAP_BASE_URL}/{CAP_SITE_KEY}/siteverify` with `{secret, response}`.
   - Fail fast on missing config or non-200 responses.
2. Update `run_0.create`:
   - If `current_user.is_authenticated`, bypass Cap.
   - Otherwise require `cap_token` (POST body) and validate; return 403 on failure.
   - Switch to POST + 303 redirect after successful create.
3. Log validation failures with request metadata (no token value) for auditability.

### Phase 4 - Infra wiring (Docker + Caddy)
1. Add the Cap microservice to `docker/docker-compose.dev.yml` and `docker/docker-compose.prod.yml`:
   - Build from `services/cap` and mount `/workdir/cap` for assets.
   - Mount persistent data volume for Cap storage.
   - Set `CAP_SITE_KEY`, `CAP_SECRET`, and `CAP_CORS_ORIGIN`.
2. Add Caddy routing:
   - `handle /cap* { reverse_proxy cap:3000 }`
   - Preserve `X-Forwarded-Proto` headers.
3. Document required env vars in `docker/.env` and relevant README(s).

### Phase 5 - Tests + validation
1. Add route tests for anonymous create:
   - missing token -> 403
   - invalid token -> 403
   - valid token -> 303 redirect to run page
2. Stub Cap verification responses (no network).
3. Manual smoke:
   - Anonymous: floating CAPTCHA appears, links enable after solve, create works.
   - Authenticated: no CAPTCHA, links work normally.

### Phase 6 - Post-validation follow-ups (after Phase 5)
1. Update `/create/` index to use POST-based flow (no tokenized links).
2. Add Cap gating for anonymous `fork` flows; authenticated users fork without CAPTCHA.
3. Verify `batch-runner` and `archive` endpoints require authentication; document any gaps.

### Phase 7 - Docs + rollout
1. Document the Cap flow and config in `wepppy/weppcloud/README.md` or `docs/ui-docs/`.
2. Add operator notes for key rotation and Cap service health checks.
