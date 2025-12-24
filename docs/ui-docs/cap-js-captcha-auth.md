# Cap.js CAPTCHA Auth (UI + Server)
> Developer guide for the Cap.js microservice and floating CAPTCHA workflow used for anonymous run creation.

## Overview
The Cap.js integration has two parts:
- A lightweight Node service that wraps `@cap.js/server` and serves assets (widget + floating).
- A front-end pattern that shows an on-demand floating CAPTCHA, captures the token, and enables submit buttons.

This pattern is used on the interfaces landing page and will be replicated for other run page tasks.
The fork console uses the same pattern, with the submit button disabled until verification completes.

## Cap Service (Node)
Path: `services/cap/server.js`

### Routes
- `GET /cap/health` -> `{ "status": "ok" }`
- `GET /cap/assets/widget.js`
- `GET /cap/assets/floating.js`
- `GET /cap/assets/cap_wasm.js`
- `GET /cap/assets/cap_wasm_bg.wasm`
- `POST /cap/<siteKey>/challenge`
- `POST /cap/<siteKey>/redeem`
- `POST /cap/<siteKey>/siteverify`

### Environment
Required:
- `CAP_SITE_KEY` (public key)
- `CAP_SECRET` (private key)

Optional:
- `CAP_PORT` (default `3000`)
- `CAP_CORS_ORIGIN` (comma-separated allowlist or `*`)
- `CAP_DATA_DIR` (default `/var/lib/cap`)
- `CAP_ASSET_ROOT` (default `/workdir/cap`)
- `CAP_WIDGET_PATH` (defaults to `widget/src/cap.min.js`)
- `CAP_FLOATING_PATH` (defaults to `widget/src/cap-floating.min.js`)
- `CAP_WASM_JS_PATH` (defaults to `wasm/src/browser/cap_wasm.js`)
- `CAP_WASM_BG_PATH` (defaults to `wasm/src/browser/cap_wasm_bg.wasm`)

### Reverse Proxy
Caddy maps `/cap*` to the cap service. Verify with:
```
curl -H 'X-Forwarded-Proto: https' http://localhost:8080/cap/health
```

### Production Asset Mount
Production compose mounts `/workdir/cap` into the cap container and sets `CAP_ASSET_ROOT=/workdir/cap`. This is required because the server hard-fails on missing widget/wasm assets. If you want to remove the host mount, bake assets into the image or point `CAP_ASSET_ROOT` at a vendored asset path.

## Flask Template Wiring
The interfaces route passes these template vars:
- `cap_base_url` (ex: `/cap` or `https://<host>/cap`)
- `cap_asset_base_url` (ex: `/cap/assets`)
- `cap_site_key`

These come from `CAP_BASE_URL`, `CAP_ASSET_BASE_URL`, `CAP_SITE_KEY` in app config/env.

## Floating CAPTCHA Pattern
Floating mode hides the `cap-widget` until a trigger is clicked. The trigger must be clickable (do not disable it). We use a dedicated prompt button as the only floating trigger; create buttons stay disabled until a solve event.

### Macro
Use the shared macro:
```
{% import "shared/cap_macros.htm" as cap_macros %}
{{ cap_macros.cap_prompt("section-key", "cap-section-id", cap_base_url, cap_site_key) }}
```

Arguments:
- `section` (logical group key, used by JS to update all forms in a section)
- `widget_id` (DOM id for the `cap-widget`)
- `cap_base_url`, `cap_site_key`
- Optional: `floating_position`, `status_text`, `label_text`, `brand_text`

Macro file: `wepppy/weppcloud/templates/shared/cap_macros.htm`

### Scripts
Load only for anonymous users:
```
<script>
  window.CAP_CUSTOM_WASM_URL = "{{ cap_asset_base_url }}/cap_wasm.js";
</script>
<script src="{{ cap_asset_base_url }}/widget.js" defer></script>
<script src="{{ cap_asset_base_url }}/floating.js" defer></script>
```

### Form Wiring
Each protected action is a POST form with a hidden token.
```
<form method="post" action="..." data-cap-section="disturbed" data-cap-required="true">
  <input type="hidden" name="cap_token" value="" data-cap-token>
  <button type="button" class="wc-run-button is-disabled" disabled>Start</button>
</form>
```

The create buttons are disabled until a `cap-widget` solve event fires. Create buttons do not carry `data-cap-floating`; the prompt trigger does.
For fork console, the submit button is rendered with `disabled` + `is-disabled` for anonymous users and is enabled only after the `solve` event.

### JS Glue
The controller `wepppy/weppcloud/controllers_js/interfaces_captcha.js`:
- listens for `solve` on `cap-widget`
- copies the token into hidden inputs
- enables buttons for the section
- marks the prompt as verified (`data-cap-verified="true"`)

The built bundle is `wepppy/weppcloud/static/js/controllers-gl.js`.

Fork console uses `wepppy/weppcloud/static/js/fork_console.js` for the same flow:
- blocks submission and triggers the floating prompt if the token is missing
- enables the submit button after verification
- includes `cap_token` in the POST payload

## Server-Side Verification
Anonymous requests must verify the token:
1. Receive `cap_token` in the POST body.
2. POST to `POST /cap/<siteKey>/siteverify` with `{ secret, response }`.
3. Allow if `success` is true; reject otherwise.

Notes:
- `CAP_BASE_URL` can be relative (ex: `/cap`); the verifier resolves relative paths against the incoming request host.
- Missing `CAP_BASE_URL`, `CAP_SITE_KEY`, or `CAP_SECRET` should fail fast.
- Use `wepppy/weppcloud/utils/cap_verify.py` as the canonical verification helper.

Create endpoint behavior:
- Anonymous: `POST /create/<config>` requires `cap_token`.
- Authenticated: `GET /create/<config>` is allowed (no CAPTCHA).
- `/create/` index is restricted to authenticated users.

Authenticated users should bypass CAPTCHA.

## Troubleshooting
- If the widget never appears: confirm the prompt trigger has `data-cap-floating` and is not disabled.
- If the widget stays hidden: do not add CSS that forces `display:none` on `cap-widget`.
- If assets 404: check `CAP_BASE_URL`, `CAP_ASSET_BASE_URL`, and Caddy routing.
- Console errors: look for `[cap floating] "<selector>" doesn't exist`.
