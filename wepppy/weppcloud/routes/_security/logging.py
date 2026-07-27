"""Security logging blueprint and signal instrumentation."""

from __future__ import annotations

import logging
import os
import hashlib
from logging.handlers import WatchedFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Blueprint, current_app, has_request_context, request, session
import flask_security.signals as fs_signals

security_bp = Blueprint('security_logging', __name__)

_SECURITY_LOGGER_NAME = "weppcloud.security"
_DEFAULT_LOG_PATH = Path("/wc1/logs/weppcloud/security.log")


class _VisibleWatchedFileHandler(WatchedFileHandler):
    """Report post-startup write failures through the main service logger."""

    def handleError(self, record):
        logging.getLogger("gunicorn.error").error(
            "Security logging: unable to write %s",
            self.baseFilename,
            exc_info=True,
        )


def _get_security_logger():
    return logging.getLogger(_SECURITY_LOGGER_NAME)


def _resolve_log_path(app) -> Path:
    configured = app.config.get("SECURITY_LOG_FILE")
    if configured:
        path = Path(configured)
    else:
        path = _DEFAULT_LOG_PATH

    if not path.is_absolute():
        try:
            start = Path(app.root_path).resolve()
        except (OSError, RuntimeError, TypeError):
            start = Path.cwd()

        candidate_bases = [start] + list(start.parents)
        base = start
        for candidate in candidate_bases:
            if any((candidate / marker).exists() for marker in ("docker", ".docker-data", "pyproject.toml")):
                base = candidate
                break

        path = (base / path).resolve()

    return path


def _configure_security_file_logging(app) -> Optional[Path]:
    """Attach an append-only handler; the host coordinates log rotation."""
    logger = _get_security_logger()
    log_path = _resolve_log_path(app)

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(log_path.parent, 0o700)
        log_path.touch(mode=0o600, exist_ok=True)
        os.chmod(log_path, 0o600)
    except OSError as exc:
        logging.getLogger("gunicorn.error").warning(
            "Security logging: unable to create log directory %s: %s",
            log_path.parent,
            exc,
        )
        return None

    for handler in logger.handlers:
        if getattr(handler, "_security_log_path", None) == log_path:
            break
    else:
        try:
            handler = _VisibleWatchedFileHandler(log_path, encoding="utf-8")
        except OSError as exc:
            logging.getLogger("gunicorn.error").warning(
                "Security logging: unable to open %s: %s",
                log_path,
                exc,
            )
            return None
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        handler._security_log_path = log_path
        logger.addHandler(handler)

    return log_path


def _session_snapshot() -> Dict[str, Any]:
    if not has_request_context():
        return {}

    cookie_name = current_app.config.get('SESSION_COOKIE_NAME', 'session')
    return {
        'has_cookie': cookie_name in request.cookies,
        'fresh': session.get('_fresh'),
        'new': getattr(session, 'new', None),
        'modified': session.modified,
        'permanent': session.permanent,
        'remember_action': (
            session.get('_remember')
            if session.get('_remember') in {'set', 'clear'}
            else None
        ),
    }


def _extract_role_names(user) -> list[str]:
    if user is None:
        return []

    raw_roles = getattr(user, "roles", None) or []
    names: list[str] = []
    seen: set[str] = set()
    for role in raw_roles:
        candidate = role if isinstance(role, str) else getattr(role, "name", None)
        if candidate is None:
            continue
        role_name = str(candidate).strip()
        if not role_name:
            continue
        key = role_name.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(role_name)
    return names


def _cache_authenticated_role_state(user) -> None:
    if not has_request_context():
        return

    role_names = _extract_role_names(user)
    session["_roles_mask"] = role_names
    session["_roles"] = role_names
    session.modified = True


def _clear_cached_role_state() -> None:
    if not has_request_context():
        return

    changed = False
    for key in ("_roles_mask", "_roles"):
        if key in session:
            session.pop(key, None)
            changed = True
    if changed:
        session.modified = True


def _extract_identity(user, login_form, extra: Dict[str, Any]):
    if user is not None:
        for attr in ('email', 'username'):
            value = getattr(user, attr, None)
            if value:
                return value

    identity = extra.get('identity')
    if identity:
        return identity

    if login_form is not None:
        for field_name in ('email', 'username', 'identity'):
            field = getattr(login_form, field_name, None)
            if field is not None:
                value = getattr(field, "data", None)
                if value:
                    return value

        data_attr = getattr(login_form, "data", None) or {}
        data = dict(data_attr) if isinstance(data_attr, dict) else {}

        for key in ('email', 'username', 'identity'):
            value = data.get(key)
            if value:
                return value

    return None


def _identity_label(identity) -> str:
    if not identity:
        return "<unknown>"
    digest = hashlib.sha256(str(identity).encode("utf-8")).hexdigest()[:12]
    return f"sha256:{digest}"


def _sanitize_form(login_form):
    if login_form is None:
        return None

    data_attr = getattr(login_form, "data", None) or {}
    if not isinstance(data_attr, dict):
        return "<unavailable>"
    return {
        "remember_selected": bool(data_attr.get("remember"))
    }


def _sanitize_extra(extra: Dict[str, Any]):
    return sorted(
        str(key) for key in extra
        if key not in {'app', 'user', 'login_form'}
    )


def _log_event(event_name: str, *, user=None, login_form=None, extra: Optional[Dict[str, Any]] = None):
    extra = extra or {}
    logger = _get_security_logger()

    if has_request_context():
        identity = _extract_identity(user, login_form, extra)
        session_snapshot = _session_snapshot()
        extra_summary = _sanitize_extra(extra)
        form_snapshot = _sanitize_form(login_form)

        logger.info(
            "Security %s identity=%s user_id=%s active=%s ip=%s session=%s extra_keys=%s",
            event_name,
            _identity_label(identity),
            getattr(user, 'id', None),
            getattr(user, 'is_active', None) if user else None,
            request.remote_addr,
            session_snapshot,
            extra_summary,
        )

        if form_snapshot:
            logger.debug("Security %s sanitized_form=%s", event_name, form_snapshot)
    else:
        logger.info(
            "Security %s user_id=%s (no request context) extra_keys=%s",
            event_name,
            getattr(user, 'id', None),
            list(extra.keys()),
        )


LOGIN_ENDPOINTS = {'security.login', 'security_ui.login'}
LOGOUT_ENDPOINTS = {'security.logout'}


@security_bp.before_app_request
def _log_login_request():
    logger = _get_security_logger()
    if request.endpoint in LOGIN_ENDPOINTS and request.method == 'POST':
        sanitized_form = {
            "remember_selected": "remember" in request.form
        }
        session_snapshot = _session_snapshot()

        logger.info(
            "Security login POST received ip=%s has_session_cookie=%s session=%s form=%s",
            request.remote_addr,
            session_snapshot.get('has_cookie'),
            session_snapshot,
            sanitized_form,
        )
    elif request.endpoint in LOGOUT_ENDPOINTS:
        session_snapshot = _session_snapshot()
        logger.info(
            "Security logout request method=%s ip=%s has_session_cookie=%s session=%s",
            request.method,
            request.remote_addr,
            session_snapshot.get('has_cookie'),
            session_snapshot,
        )


@security_bp.after_app_request
def _log_login_response(response):
    endpoint = None
    try:
        endpoint = request.endpoint
    except RuntimeError:
        endpoint = None

    logger = _get_security_logger()

    if endpoint in LOGIN_ENDPOINTS:
        logger.info(
            "Security login response method=%s status=%s remember_action=%s mimetype=%s",
            request.method,
            response.status,
            _session_snapshot().get("remember_action"),
            response.mimetype,
        )
    elif endpoint in LOGOUT_ENDPOINTS:
        logger.info(
            "Security logout response method=%s status=%s remember_action=%s mimetype=%s",
            request.method,
            response.status,
            _session_snapshot().get("remember_action"),
            response.mimetype,
        )

    return response


def _connect_security_signals(app):
    def _make_handler(event_name: str):
        def _handler(sender, user=None, **extra):
            if event_name == "user_authenticated":
                _cache_authenticated_role_state(user)
            elif event_name == "user_unauthenticated":
                _clear_cached_role_state()

            extra_copy = dict(extra)
            login_form = extra_copy.pop('login_form', None)
            _log_event(event_name, user=user, login_form=login_form, extra=extra_copy)

        return _handler

    signal_event_map = {
        'user_authenticated': 'user_authenticated',
        'user_unauthenticated': 'user_unauthenticated',
        'user_not_registered': 'user_not_registered',
        'user_confirmed': 'user_confirmed',
        'login_instructions_sent': 'login_instructions_sent',
    }

    for signal_name, event_name in signal_event_map.items():
        signal = getattr(fs_signals, signal_name, None)
        if signal is None:
            continue
        signal.connect(_make_handler(event_name), app, weak=False)

_diagnostic_logger = logging.getLogger("gunicorn.error")
_diagnostic_logger.debug("Security logging module imported")

@security_bp.record_once
def _on_register(state):
    _diagnostic_logger.debug("Security logging blueprint registering")
    log_path = _configure_security_file_logging(state.app)
    if log_path is not None:
        _diagnostic_logger.debug("Security log file handler configured at %s", log_path)
    else:
        _diagnostic_logger.warning("Security log file handler setup skipped due to errors")
    _connect_security_signals(state.app)
    _diagnostic_logger.debug("Security blueprint registered")
