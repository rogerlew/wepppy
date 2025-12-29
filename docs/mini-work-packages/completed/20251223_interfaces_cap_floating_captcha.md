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
4. Add a visible CAPTCHA prompt per section and wire it as the only floating trigger:
   - Prompt uses `data-cap-floating="#<widget-id>"` and `data-cap-floating-position="top"`.
   - Create buttons remain disabled and do not carry floating attributes.
5. Disable create links until solved:
   - Replace links with POST forms and store the target in `data-run-action`.
   - Disable submit buttons (`disabled`, `aria-disabled`) and apply a disabled CSS class.
6. Add a small controller (new `wepppy/weppcloud/controllers_js/interfaces_captcha.js` or inline script):
   - On `solve`, enable submit buttons in the same section and inject `cap_token` into a hidden input.
   - Ensure right-click menu uses `data-run-action` (or another form-based source) for navigation.
7. Load Cap assets only for anonymous users:
   - `cap-widget` script and `cap-floating` from the Cap microservice asset paths.
   - Set `window.CAP_CUSTOM_WASM_URL` to `/cap/assets/cap_wasm.js`.

## Phase 2 Handoff Summary
- Added a shared CAPTCHA prompt macro (`wepppy/weppcloud/templates/shared/cap_macros.htm`) that renders a familiar checkbox-style tile plus the `cap-widget` per section.
- Updated `wepppy/weppcloud/templates/interfaces.htm` to use the macro for each interface section, convert anonymous create links into POST forms with hidden `cap_token`, and disable the create buttons until a solve event fires.
- Added themed CAPTCHA styles in `wepppy/weppcloud/templates/interfaces.htm` (`.wc-cap-prompt`, `.wc-cap-trigger`, checkbox/checkmark, verified state) to match existing UI tokens and themes.
- Added `wepppy/weppcloud/controllers_js/interfaces_captcha.js` to listen for `cap-widget` solve events, inject the token into hidden inputs, enable buttons, and mark sections verified.
- Wired Cap assets into the interfaces template for anonymous users only and passed `cap_base_url`, `cap_asset_base_url`, and `cap_site_key` from `wepppy/weppcloud/routes/weppcloud_site.py`.
- Manual test: anonymous create POST includes `cap_token` and is ready for Phase 3 validation work.
- Backend validation is implemented in Phase 3; anonymous create now requires a valid token.
- New developer guide drafted at `docs/ui-docs/cap-js-captcha-auth.md`.

### Agent Prompt: Phase 2 Review
You are a fresh agent reviewing Phase 2 (frontend only) of the Cap.js integration. Please:
1) Verify that anonymous users see a familiar CAPTCHA prompt per interface section and that the floating widget appears when the prompt is clicked.
2) Confirm that the create buttons remain disabled until the CAPTCHA solve event, then enable and submit a POST with `cap_token`.
3) Ensure authenticated users do not see CAPTCHA UI and can create runs normally.
4) Inspect for console errors (especially `[cap floating]` selector errors) and confirm assets load from `/cap/assets/*`.
5) Validate that the right-click unitizer menu still works with POST forms (uses `data-run-action` or form action).
Key files to review:
- `wepppy/weppcloud/templates/interfaces.htm`
- `wepppy/weppcloud/templates/shared/cap_macros.htm`
- `wepppy/weppcloud/controllers_js/interfaces_captcha.js`
- `wepppy/weppcloud/routes/weppcloud_site.py`
- `docs/ui-docs/cap-js-captcha-auth.md`
Notes:
- `wepppy/weppcloud/static/js/controllers-gl.js` is generated by `python wepppy/weppcloud/controllers_js/build_controllers_js.py` and is not tracked.
- Backend validation (POST `run_0.create`) is implemented in Phase 3; anonymous requests now 403 on missing/invalid tokens.

### Phase 3 - Backend token validation
1. Add a helper module (ex: `wepppy/weppcloud/utils/cap_verify.py`) to call:
   - `POST {CAP_BASE_URL}/{CAP_SITE_KEY}/siteverify` with `{secret, response}`.
   - Fail fast on missing config or non-200 responses.
2. Update `run_0.create`:
   - If `current_user.is_authenticated`, bypass Cap.
   - Otherwise require `cap_token` (POST body) and validate; return 403 on failure.
   - Switch to POST + 303 redirect after successful create.
3. Log validation failures with request metadata (no token value) for auditability.

## Phase 3 Handoff Summary
- Added `wepppy/weppcloud/utils/cap_verify.py` plus stubs to validate Cap tokens, resolve relative `CAP_BASE_URL`, and fail fast on missing config.
- Updated `wepppy/weppcloud/routes/run_0/run_0_bp.py` so anonymous create requires POST + valid `cap_token`, returns 403 on missing/invalid tokens, and redirects with 303 on success.
- Overrides now read from `request.values` and skip empty values (avoids blank `unitizer:is_english`).
- Documented server-side verification notes in `docs/ui-docs/cap-js-captcha-auth.md`.
- Manual test: anonymous create POST succeeds with valid `cap_token` and logged-in create works normally.

### Agent Prompt: Phase 3 Review (Static)
You are a fresh agent reviewing Phase 3 (backend token validation). Please:
1) Inspect `wepppy/weppcloud/utils/cap_verify.py` for config resolution, relative `CAP_BASE_URL` handling, and error paths.
2) Verify `run_0.create` now enforces POST + `cap_token` for anonymous users, returns 403 on missing/invalid tokens, and uses 303 redirect on success.
3) Confirm logging does not include raw token values and failure paths use `error_factory`/`exception_factory` consistently.
4) Check that overrides ignore `cap_token` and skip empty values (ex: blank `unitizer:is_english`).
5) Ensure stubs exist in both `wepppy/weppcloud/utils/cap_verify.pyi` and `stubs/wepppy/weppcloud/utils/cap_verify.pyi`.
Key files:
- `wepppy/weppcloud/utils/cap_verify.py`
- `wepppy/weppcloud/utils/cap_verify.pyi`
- `stubs/wepppy/weppcloud/utils/cap_verify.pyi`
- `wepppy/weppcloud/routes/run_0/run_0_bp.py`
- `docs/ui-docs/cap-js-captcha-auth.md`
Notes:
- No tests added in Phase 3; validate logic via static inspection.

### Phase 4 - Infra wiring (Docker + Caddy)
1. Add the Cap microservice to `docker/docker-compose.dev.yml` and `docker/docker-compose.prod.yml`:
   - Build from `services/cap` and mount `/workdir/cap` for assets.
   - Mount persistent data volume for Cap storage.
   - Set `CAP_SITE_KEY`, `CAP_SECRET`, and `CAP_CORS_ORIGIN`.
2. Add Caddy routing:
   - `handle /cap* { reverse_proxy cap:3000 }`
   - Preserve `X-Forwarded-Proto` headers.
3. Document required env vars in `docker/.env` and relevant README(s).

## Phase 4 Handoff Summary
- Cap service is wired into `docker/docker-compose.dev.yml` and `docker/docker-compose.prod.yml`, with `/workdir/cap` mounted for assets and `cap-data` for persistence.
- Caddy routes `/cap*` to the cap service (needed for widget + siteverify).
- Dev environment validated with real keys after restart; prod deployment intentionally out of scope for this work package.

### Phase 5 - Tests + validation
1. Add route tests for anonymous create:
   - missing token -> 403
   - invalid token -> 403
   - valid token -> 303 redirect to run page
2. Stub Cap verification responses (no network).
3. Manual smoke:
   - Anonymous: floating CAPTCHA appears, links enable after solve, create works.
   - Authenticated: no CAPTCHA, links work normally.

## Phase 5 Handoff Summary
- Added `tests/weppcloud/routes/test_run_0_create_cap.py` to cover missing token (403), invalid token (403), and valid token (303) using a stubbed verifier.
- Valid-token test asserts empty overrides (blank `unitizer:is_english`) are skipped to avoid Unitizer errors.
- Tests run and passing via `wctl run-pytest tests/weppcloud/routes/test_run_0_create_cap.py`.

### Phase 6 - Post-validation follow-ups (after Phase 5)
1. Require auth for `/create/` index; allow authenticated `GET /create/<config>` without CAPTCHA (anonymous still needs POST + token).
2. Add Cap gating for anonymous `fork` flows; authenticated users fork without CAPTCHA.
3. Verify `batch-runner` and `archive` endpoints require authentication; document any gaps.

## Phase 6 Handoff Summary
- `/create/` index is now `@login_required`, and authenticated `GET /create/<config>` bypasses CAPTCHA (anonymous still POST + token).
- Fork console uses a floating CAPTCHA prompt for anonymous users, disables submit until verification, and includes `cap_token` in `/rq/api/fork`; the backend now enforces token validation for anonymous requests.
- Batch runner remains `@roles_required("Admin")`; archive dashboard + archive API routes are now `@login_required`.

### Phase 7 - Docs + rollout
1. Document the Cap flow and config in `wepppy/weppcloud/README.md` or `docs/ui-docs/`.
2. Add operator notes for key rotation and Cap service health checks.

## Phase 7 Handoff Summary
- Documented Cap.js configuration and operational notes (health checks, key rotation, routing/asset verification) in `wepppy/weppcloud/README.md`.
- Added a UI docs index entry for `docs/ui-docs/cap-js-captcha-auth.md` in `docs/ui-docs/README.md`.

### Phase 8 - Invisible Cap.js (anonymous-only) rollout
1. Add a reusable decorator (ex: `@requires_cap`) that:
   - No-ops for authenticated users.
   - Reads `cap_token` from form data or `X-Cap-Token` header.
   - Calls `verify_cap_token()` and returns 403 on missing/invalid tokens (no raw token logging).
2. Apply the decorator to anonymous-sensitive action endpoints (reports downloads, exports, heavy compute triggers).
3. Optional session gate for page-render routes:
   - Invisible widget solves -> POST `/cap/verify` -> sets `session['cap_verified_at']`.
   - Decorator checks TTL (ex: 10–30 minutes) before requiring another solve.
4. UI wiring:
   - On targeted pages, load the invisible widget only for anonymous users.
   - Use the shared Cap.js helper to fetch a token on demand and submit it with protected actions.

## Phase 8 Handoff Summary
- Added `wepppy/weppcloud/utils/cap_guard.py` with `requires_cap` + session TTL gating and the `cap_gate.htm` template for invisible verification.
- Added `/cap/verify` endpoint in `wepppy/weppcloud/routes/weppcloud_site.py` to validate tokens and set the anonymous session flag.
- Applied `@requires_cap` to the run landing page and report routes (WEPP, RHEM, soils, landuse, climate, watershed, ash, observed, omni, rangeland, pivottable, jsoncrack, deval details) so anonymous users complete invisible verification before viewing reports.
