# WEPPcloud Blueprint Checklist

> Quick reminders for adding or adjusting Flask blueprints inside `wepppy/weppcloud/routes/`.

## Why this exists
Caddy fronts the app with `handle_path /weppcloud*`, which **strips the `/weppcloud` prefix** before requests hit Flask. We have regressed a few times by keeping a `url_prefix="/weppcloud"` inside the blueprint, which makes Flask look for `/weppcloud/...` while it actually receives `/...`. Use this checklist every time you touch a blueprint to stay aligned.

## Blueprint creation
- [ ] Define the blueprint with **no URL prefix** unless the route intentionally lives outside the main app: `Blueprint("your_name", __name__)`.
- [ ] For run-scoped routes, use the canonical pattern: `/runs/<runid>/<config>/...`.
- [ ] Guard optional auth (`login_required`) consciously—recorder endpoints, for example, write audit logs for page unload events and must respond 204 without a redirect.

## Registration steps
- [ ] Import the blueprint in `wepppy/weppcloud/routes/__init__.py`, append it to `__all__`, and (if needed) register the run-context preprocessor.
- [ ] Register the blueprint in `_blueprints_context.py` (`app.register_blueprint(...)`). Keep the ordering consistent with similar modules.
- [ ] Restart `weppcloud` (or run `build_controllers_js.py` when front-end changes accompany the route) so the new routes load.

## Smoke checks
- [ ] `wctl exec weppcloud python - <<'PY' ...` and list routes containing your blueprint name to make sure Flask sees it.
- [ ] `curl -i http://127.0.0.1:8000/runs/test/config/...` from inside the container to verify the route answers before testing externally.

Keep this doc handy—future you will thank you.

## Query-engine integration
- Do **not** add Flask routes that simply wrap query-engine payloads; the Starlette `/query-engine/*` app is the canonical surface. Wrapping it in `weppcloud` defeats the async path, doubles maintenance, and reintroduces the coupling we are trying to remove. Front-ends should call the query-engine directly.

## Front-end bundles
- Rebuild `controllers.js` with `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py` whenever you touch files under `controllers_js/` (this now also emits `static/js/status_stream.js`).
- Pages that only need StatusStream logging should load `static/js/status_stream.js`; reserve the full `controllers.js` bundle for screens that rely on the modern controller stack.
- Any console-style control must supply its own config node (hidden `<div data-*-config …>`) so scripts can read run-scoped URLs even when optional wrappers are skipped—do not rely on side effects from other bundles.
- Front-end scripts can call `WCConsoleConfig.readConfig(container, "[data-*-config]")` (provided by `static/js/console_utils.js`) to merge the hidden config node with the wrapper’s dataset and coerce boolean flags.
- When wiring a new control, add a quick smoke step (Playwright, controller unit test, or manual checklist) to click primary actions and confirm the expected fetch fires; missing config or wrong bundle choice will surface immediately.
