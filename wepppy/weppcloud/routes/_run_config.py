"""Canonical stored config identity for Flask run routes only."""

from dataclasses import replace
import json
import re
from urllib.parse import quote

from flask import abort, current_app, g, redirect, request
from werkzeug.exceptions import NotFound

from ._run_context import load_run_context, _store_run_context


_TOKEN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*\Z")


def register_run_config_hooks(app):
    """Normalize arguments before blueprint hooks; redirect guarded successes."""

    @app.url_value_preprocessor
    def normalize_run_config(endpoint, values):
        rule = request.url_rule
        if (request.method == "OPTIONS" or rule is None
                or not rule.rule.startswith("/runs/") or not values
                or "runid" not in values or "config" not in values):
            return
        g.requested_run_config = values["config"]
        try:
            ctx = load_run_context(values["runid"], values["config"])
            with (ctx.active_root / "ron.nodb").open(encoding="utf-8") as stream:
                payload = json.load(stream)
            state = payload.get("py/state", payload) if isinstance(payload, dict) else None
            stored = state.get("_config") if isinstance(state, dict) else None
            token = stored.split("?", 1)[0].removesuffix(".cfg") if isinstance(stored, str) else ""
            if not _TOKEN.fullmatch(token):
                raise ValueError("Invalid stored run config identity")
        except (NotFound, OSError, ValueError) as exc:
            # Lookup boundary: fail before dispatch without revealing private metadata.
            current_app.logger.warning("Run config lookup failed for %s: %s", values["runid"], exc)
            abort(404, description="Run not found")
        values["config"] = token
        _store_run_context(replace(ctx, config=token))
        if token != g.requested_run_config:
            # Build this exact rule, not another alias for the same endpoint.
            _, path = rule.build(values, append_unknown=False)
            target = quote(request.script_root, safe="/") + path
            if request.query_string:
                target += "?" + request.query_string.decode("latin-1")
            g.canonical_run_config_url = target

    @app.after_request
    def redirect_canonical_run_config(response):
        target = getattr(g, "canonical_run_config_url", None)
        if target and request.method in {"GET", "HEAD"} and 200 <= response.status_code < 300:
            canonical = redirect(target, code=302)
            # Preserve endpoint-issued cookies; Flask session saving occurs afterward.
            for cookie in response.headers.getlist("Set-Cookie"):
                canonical.headers.add("Set-Cookie", cookie)
            canonical.headers["Cache-Control"] = "no-store"
            response.close()
            return canonical
        return response
