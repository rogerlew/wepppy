"""Shared imports and helpers for WEPPcloud blueprints."""

import csv
import io
import json
import logging
import os
import shutil
import traceback
from datetime import datetime
from pathlib import Path

from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from typing import Any, Dict, Iterable, Optional, Set, Union

from flask import (
    Blueprint as _FlaskBlueprint,
    abort,
    current_app,
    g,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    Response,
    send_file,
    stream_with_context,
    url_for,
    send_from_directory
)
from flask_security import current_user, login_required, roles_required
from werkzeug.utils import secure_filename

from wepppy.weppcloud.utils.helpers import (
    authorize,
    error_factory,
    exception_factory,
    get_wd,
    success_factory,
    url_for_run,
)

__all__ = [
    'Blueprint',
    'LoggedBlueprint',
    'abort',
    'authorize',
    'current_app',
    'g',
    'current_user',
    'error_factory',
    'exception_factory',
    'get_wd',
    'glob',
    'io',
    'json',
    'jsonify',
    'login_required',
    'make_response',
    'redirect',
    'render_template',
    'request',
    'Response',
    'roles_required',
    'send_file',
    'stream_with_context',
    'success_factory',
    'url_for',
    'url_for_run',
    'secure_filename',
    '_exists',
    '_join',
    '_split',
    'csv',
    'logging',
    'os',
    'shutil',
]

from ._run_context import RunContext, load_run_context, register_run_context_preprocessor

__all__.extend([
    'RunContext',
    'load_run_context',
    'register_run_context_preprocessor',
])

_TRUE_TOKENS: Set[str] = {'1', 'true', 'yes', 'on'}
_FALSE_TOKENS: Set[str] = {'0', 'false', 'no', 'off'}


def _maybe_log_exception(exc: Exception) -> None:
    """Best-effort append of route exceptions to exceptions.log under the run folder."""
    try:
        view_args = getattr(request, "view_args", None) or {}
        runid = view_args.get("runid") or view_args.get("run_id")
        if not isinstance(runid, str):
            return
        wd = Path(get_wd(runid))
        target = wd / "exceptions.log"
        target.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().isoformat() + "Z"
        endpoint = request.endpoint or "nodb_api"
        stream = [
            f"[{timestamp}] {endpoint}",
            traceback.format_exc(),
            "",
        ]
        with target.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(stream))
    except Exception:
        # Never interfere with Flask's exception propagation
        return


class LoggedBlueprint(_FlaskBlueprint):
    """Blueprint that logs exceptions to the run workspace before propagation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_error_handler(Exception, self._log_and_propagate)

    @staticmethod
    def _log_and_propagate(exc: Exception):
        if not getattr(exc, "_logged_to_exceptions", False):
            setattr(exc, "_logged_to_exceptions", True)
            _maybe_log_exception(exc)
        raise


# Default export: use LoggedBlueprint for all route modules importing Blueprint
Blueprint = LoggedBlueprint


def _normalise_scalar(
    value: Any,
    *,
    coerce_boolean: bool,
    trim_strings: bool,
) -> Any:
    if isinstance(value, str):
        token = value.strip() if trim_strings else value
        if coerce_boolean:
            lowered = token.lower()
            if lowered in _TRUE_TOKENS:
                return True
            if lowered in _FALSE_TOKENS:
                return False
        return token
    if coerce_boolean and isinstance(value, (int, float)):
        # Match HTML checkbox semantics: any non-zero value is True
        return bool(value)
    return value


def _normalise_payload_value(
    value: Any,
    *,
    coerce_boolean: bool,
    trim_strings: bool,
) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalise_payload_value(
                inner,
                coerce_boolean=coerce_boolean,
                trim_strings=trim_strings,
            )
            for key, inner in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        normalised = [
            _normalise_payload_value(
                item,
                coerce_boolean=coerce_boolean,
                trim_strings=trim_strings,
            )
            for item in value
        ]
        if len(normalised) == 1:
            return normalised[0]
        return normalised
    return _normalise_scalar(
        value,
        coerce_boolean=coerce_boolean,
        trim_strings=trim_strings,
    )


def parse_request_payload(
    req: 'flask.Request',
    *,
    boolean_fields: Optional[Iterable[str]] = None,
    trim_strings: bool = True,
) -> Dict[str, Any]:
    """
    Normalise incoming payloads for controllers that now post JSON bodies.

    - Attempts JSON deserialisation first via ``request.get_json(silent=True)``.
    - Falls back to ``request.form`` preserving multi-value entries.
    - Trims string values (unless ``trim_strings`` is False).
    - Normalises checkbox-style inputs to booleans when the key is included in
      ``boolean_fields``.
    """
    boolean_field_set: Set[str] = set(boolean_fields or [])

    data: Dict[str, Any] = {}
    raw_json = req.get_json(silent=True)
    if isinstance(raw_json, dict):
        data.update(raw_json)
    elif raw_json is None:
        # No JSON body supplied; fall back to form data below.
        pass
    else:
        # JSON body was provided but not a dict (array / scalar). Ignore it and
        # rely on form data so callers receive a predictable structure.
        pass

    if not data and req.form:
        form_dict: Dict[str, Union[str, Iterable[str]]] = req.form.to_dict(flat=False)  # type: ignore[attr-defined]
        data.update(form_dict)

    normalised: Dict[str, Any] = {}
    for key, value in data.items():
        coerce_boolean = key in boolean_field_set
        normalised[key] = _normalise_payload_value(
            value,
            coerce_boolean=coerce_boolean,
            trim_strings=trim_strings,
        )
    return normalised


__all__.append('parse_request_payload')
