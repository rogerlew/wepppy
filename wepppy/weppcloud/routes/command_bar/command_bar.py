"""Backend endpoints for the command bar.

The command bar is a run specific UI compoent with vim style command entry. It
can be opened with the `:` key when the focus is not in a text input. It is a power user
feature for various functions. It expedients tasks for advanced users. And provides a
simple method of adding features without implementing a full UI. 

Many of the commands can use existing endpoints, but some need new ones. This serves
as a home for those endpoints that are command bar specific and don't belong elsewhere.
The `command_bar/static/command-bar.js` file holds the companion frontend code.

Keep endpoints small and focused. Here are some guidelines:
1. Validate payload + authorization, always call `authorize()`
2. Delegate work to existing NoDB helpers or service objects (as needed)
3. Return `{Success, Content?, Error?}` JSON for the command bar to display

"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request
from flask_login import current_user

from wepppy.nodb.base import (
    LogLevel,
    lock_statuses,
    try_redis_get_log_level,
    try_redis_set_log_level,
)
from wepppy.weppcloud.utils.helpers import authorize
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.auth_tokens import JWTConfigurationError

from .._run_context import load_run_context


command_bar_bp = Blueprint(
    'command_bar',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/command_bar/static'
)

_ALLOWED_LEVELS = {level.name.lower(): level for level in LogLevel}


@command_bar_bp.route('/runs/<string:runid>/<config>/command_bar/loglevel', methods=['POST'])
def set_log_level(runid, config):
    authorize(runid, config)
    load_run_context(runid, config)

    payload = request.get_json(silent=True) or {}
    level = payload.get('level')

    if not level:
        return jsonify({'Success': False, 'Error': 'Missing "level" parameter.'}), 400

    level_key = str(level).lower()
    if level_key not in _ALLOWED_LEVELS:
        expected = ', '.join(sorted(_ALLOWED_LEVELS))
        return jsonify({'Success': False, 'Error': f'Invalid log level "{level}". Expected one of {expected}.'}), 400

    try:
        try_redis_set_log_level(runid, level_key)
        effective_value = try_redis_get_log_level(runid)
    except Exception as exc:
        logging.error('Unexpected error setting log level for %s: %s', runid, exc)
        return jsonify({'Success': False, 'Error': 'Failed to update log level. Please try again.'}), 500

    try:
        effective_label = LogLevel(effective_value).name.lower()
    except ValueError:
        effective_label = str(effective_value)

    return jsonify({
        'Success': True,
        'Content': {
            'log_level': effective_label,
            'log_level_value': effective_value
        }
    })


@command_bar_bp.route('/runs/<string:runid>/<config>/command_bar/locks', methods=['GET'])
def get_lock_statuses(runid, config):
    authorize(runid, config)
    load_run_context(runid, config)

    try:
        statuses = lock_statuses(runid)
    except RuntimeError as exc:
        logging.error('Lock status unavailable for %s: %s', runid, exc)
        return jsonify({'Success': False, 'Error': 'Lock service unavailable. Please try again later.'}), 503
    except Exception as exc:  # pragma: no cover - defensive logging
        logging.exception('Unexpected error retrieving lock statuses for %s', runid)
        return jsonify({'Success': False, 'Error': 'Unexpected error retrieving lock statuses.'}), 500

    locked_files = sorted([
        str(filename)
        for filename, is_locked in statuses.items()
        if is_locked
    ])

    return jsonify({
        'Success': True,
        'Content': {
            'locked_files': locked_files
        }
    })


def _build_mcp_markdown(
    *,
    runid: str,
    subject: str,
    token: str,
    scopes: list[str] | None,
    expires_at: int | None,
    spec_url: str,
    instructions: list[str],
) -> str:
    """Render a Markdown document with MCP integration instructions."""

    generated_at = datetime.now(timezone.utc).isoformat()
    expires_at_iso = None
    if isinstance(expires_at, (int, float)):
        try:
            expires_at_iso = datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
        except Exception:  # pragma: no cover - defensive
            expires_at_iso = None

    scope_text = ", ".join(scopes or [])
    if not scope_text:
        scope_text = "runs:read, queries:validate, queries:execute"

    header_lines = [
        "# Query Engine MCP Integration",
        "",
        f"- Generated at: {generated_at}",
        f"- Run ID: `{runid}`",
        f"- Token subject: `{subject}`",
        f"- Scopes: {scope_text}",
        f"- Expires: {expires_at_iso or 'unknown'}",
        "",
        "⚠️ Treat this document as sensitive. The token grants access to run data until it expires.",
        "",
        "## Authorization Header",
        "```http",
        f"Authorization: Bearer {token}",
        "```",
        "",
        "## Setup Steps",
    ]

    step_lines = [f"{index}. {step}" for index, step in enumerate(instructions, start=1)]

    reference_lines = [
        "",
        "## Resources",
        f"- OpenAPI spec: {spec_url}",
        "- Integration guide: `wepppy/query_engine/README.md`",
        "",
        "_This file is regenerated whenever a new Query Engine MCP token is issued from the command bar._",
        "",
    ]

    return "\n".join(header_lines + step_lines + reference_lines)


@command_bar_bp.route('/runs/<string:runid>/<config>/command_bar/query_engine_mcp_token', methods=['POST'])
def issue_query_engine_mcp_token(runid, config):
    authorize(runid, config)
    context = load_run_context(runid, config)

    subject = None
    if current_user and hasattr(current_user, 'get_id'):
        subject = current_user.get_id()
    if not subject:
        subject = getattr(current_user, 'email', None) or 'weppcloud-user'

    try:
        token_payload = auth_tokens.issue_token(
            str(subject),
            scopes=["runs:read", "queries:validate", "queries:execute"],
            runs=[runid],
            audience=["query-engine"],
        )
    except JWTConfigurationError as exc:
        return jsonify({'Success': False, 'Error': f'JWT configuration error: {exc}'}), 500
    except Exception as exc:  # pragma: no cover - defensive logging
        logging.exception("Failed to issue Query Engine MCP token for %s", runid)
        return jsonify({'Success': False, 'Error': 'Unexpected error generating MCP token.'}), 500

    claims = token_payload.get('claims', {})
    expires_at = claims.get('exp')
    scopes = claims.get('scope')

    instructions = [
        'ChatGPT Custom GPT: paste the OpenAPI spec, choose API key auth, and provide this token as the Bearer secret.',
        'Google Gemini Extensions: register the OpenAPI tool, configure API-key authentication, and supply this token as the Authorization header.',
        'Anthropic Claude Tool Use: handle tool invocation server-side, send this token as the Authorization header when proxying requests.'
    ]

    if isinstance(scopes, str):
        scope_list = scopes.split(auth_tokens.get_jwt_config().scope_separator)
    elif isinstance(scopes, (list, tuple)):
        scope_list = list(scopes)
    else:
        scope_list = ["runs:read", "queries:validate", "queries:execute"]

    token_value = token_payload.get('token') or ''

    host = (request.headers.get("Host") or request.host or "").rstrip("/")
    spec_url = f"https://{host}/query-engine/docs/mcp_openapi.yaml" if host else "https://query-engine/docs/mcp_openapi.yaml"
    markdown_body = _build_mcp_markdown(
        runid=runid,
        subject=str(subject),
        token=token_value,
        scopes=scope_list,
        expires_at=expires_at if isinstance(expires_at, (int, float)) else None,
        spec_url=spec_url,
        instructions=instructions,
    )

    instructions_relpath = Path("_query_engine") / "mcp_integration_instructions.md"
    instructions_path = Path(context.active_root) / instructions_relpath

    try:
        instructions_path.parent.mkdir(parents=True, exist_ok=True)
        instructions_path.write_text(markdown_body, encoding="utf-8")
    except Exception as exc:  # pragma: no cover - defensive logging
        logging.warning(
            "Failed to write MCP instructions for run %s at %s: %s",
            runid,
            instructions_path,
            exc,
        )

    return jsonify({
        'Success': True,
        'Content': {
            'token': token_value,
            'expires_at': expires_at,
            'scopes': scope_list,
            'instructions': instructions,
            'spec_url': spec_url,
            'instructions_path': str(instructions_relpath),
        }
    })
