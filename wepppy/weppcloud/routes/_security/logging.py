"""Security logging blueprint and signal instrumentation."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Blueprint, current_app, has_request_context, request, session
import flask_security.signals as fs_signals

security_bp = Blueprint('security_logging', __name__)

_SECURITY_LOGGER_NAME = "weppcloud.security"
_DEFAULT_LOG_PATH = Path(".docker-data/weppcloud/logs/security.log")
_DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB
_DEFAULT_BACKUP_COUNT = 5


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
        except Exception:
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
    """Attach a rotating file handler to the security logger."""
    logger = _get_security_logger()
    log_path = _resolve_log_path(app)

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
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
        handler = RotatingFileHandler(
            log_path,
            maxBytes=app.config.get("SECURITY_LOG_MAX_BYTES", _DEFAULT_MAX_BYTES),
            backupCount=app.config.get("SECURITY_LOG_BACKUP_COUNT", _DEFAULT_BACKUP_COUNT),
            encoding="utf-8",
        )
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
    }


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
                try:
                    value = field.data
                except Exception:
                    value = None
                if value:
                    return value

        try:
            data = dict(getattr(login_form, 'data', {}) or {})
        except Exception:
            data = {}

        for key in ('email', 'username', 'identity'):
            value = data.get(key)
            if value:
                return value

    return None


def _sanitize_form(login_form):
    if login_form is None:
        return None

    try:
        data = dict(getattr(login_form, 'data', {}) or {})
    except Exception:
        return '<unavailable>'

    for sensitive in ('password', 'csrf_token'):
        data.pop(sensitive, None)

    return data


def _sanitize_extra(extra: Dict[str, Any]):
    sanitized = {}
    for key, value in extra.items():
        if key in {'app', 'user', 'login_form'}:
            continue
        try:
            sanitized[key] = repr(value)
        except Exception:
            sanitized[key] = '<unrepr>'
    return sanitized


def _log_event(event_name: str, *, user=None, login_form=None, extra: Optional[Dict[str, Any]] = None):
    extra = extra or {}
    logger = _get_security_logger()

    if has_request_context():
        identity = _extract_identity(user, login_form, extra)
        session_snapshot = _session_snapshot()
        extra_summary = _sanitize_extra(extra)
        form_snapshot = _sanitize_form(login_form)

        logger.info(
            "Security %s identity=%s user_id=%s active=%s ip=%s forwarded_for=%s next=%s session=%s extra=%s",
            event_name,
            identity or '<unknown>',
            getattr(user, 'id', None),
            getattr(user, 'is_active', None) if user else None,
            request.remote_addr,
            request.headers.get('X-Forwarded-For'),
            request.values.get('next'),
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
        sanitized_form = request.form.to_dict(flat=True)
        sanitized_form.pop('password', None)
        sanitized_form.pop('csrf_token', None)
        session_snapshot = _session_snapshot()

        logger.info(
            "Security login POST received ip=%s forwarded_for=%s ua=%s referrer=%s next=%s has_session_cookie=%s session=%s form=%s",
            request.remote_addr,
            request.headers.get('X-Forwarded-For'),
            request.headers.get('User-Agent'),
            request.headers.get('Referer'),
            request.values.get('next'),
            session_snapshot.get('has_cookie'),
            session_snapshot,
            sanitized_form,
        )
    elif request.endpoint in LOGOUT_ENDPOINTS:
        session_snapshot = _session_snapshot()
        logger.info(
            "Security logout request method=%s ip=%s forwarded_for=%s ua=%s referrer=%s has_session_cookie=%s session=%s",
            request.method,
            request.remote_addr,
            request.headers.get('X-Forwarded-For'),
            request.headers.get('User-Agent'),
            request.headers.get('Referer'),
            session_snapshot.get('has_cookie'),
            session_snapshot,
        )


@security_bp.after_app_request
def _log_login_response(response):
    endpoint = None
    try:
        endpoint = request.endpoint
    except Exception:
        endpoint = None

    logger = _get_security_logger()

    if endpoint in LOGIN_ENDPOINTS:
        set_cookie_present = any(header[0].lower() == 'set-cookie' for header in response.headers.items())
        logger.info(
            "Security login response method=%s status=%s location=%s set_cookie=%s mimetype=%s",
            request.method,
            response.status,
            response.headers.get('Location'),
            set_cookie_present,
            response.mimetype,
        )
    elif endpoint in LOGOUT_ENDPOINTS:
        set_cookie_present = any(header[0].lower() == 'set-cookie' for header in response.headers.items())
        logger.info(
            "Security logout response method=%s status=%s location=%s set_cookie=%s mimetype=%s",
            request.method,
            response.status,
            response.headers.get('Location'),
            set_cookie_present,
            response.mimetype,
        )

    return response


def _connect_security_signals(app):
    def _make_handler(event_name: str):
        def _handler(sender, user=None, **extra):
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
        signal.connect(_make_handler(event_name), app)

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
