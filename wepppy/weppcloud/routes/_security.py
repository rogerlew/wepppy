"""Security logging blueprint and signal instrumentation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import Blueprint, current_app, has_request_context, request, session
import flask_security.signals as fs_signals

security_bp = Blueprint('security_logging', __name__)


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
    logger = current_app.logger

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


@security_bp.before_app_request
def _log_login_request():
    if request.endpoint == 'security.login' and request.method == 'POST':
        sanitized_form = request.form.to_dict(flat=True)
        sanitized_form.pop('password', None)
        sanitized_form.pop('csrf_token', None)
        session_snapshot = _session_snapshot()

        current_app.logger.info(
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
    elif request.endpoint == 'security.logout':
        session_snapshot = _session_snapshot()
        current_app.logger.info(
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

    if endpoint == 'security.login':
        set_cookie_present = any(header[0].lower() == 'set-cookie' for header in response.headers.items())
        current_app.logger.info(
            "Security login response method=%s status=%s location=%s set_cookie=%s mimetype=%s",
            request.method,
            response.status,
            response.headers.get('Location'),
            set_cookie_present,
            response.mimetype,
        )
    elif endpoint == 'security.logout':
        set_cookie_present = any(header[0].lower() == 'set-cookie' for header in response.headers.items())
        current_app.logger.info(
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

import logging
error_logger = logging.getLogger("gunicorn.error")
error_logger.setLevel(logging.DEBUG)
error_logger.debug("Security logging initialized")
@security_bp.record_once
def _on_register(state):
    global error_logger
    error_logger.debug("_on_register()")
    _connect_security_signals(state.app)
    error_logger.debug("_on_register:Security blueprint registered")
