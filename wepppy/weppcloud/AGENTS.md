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
