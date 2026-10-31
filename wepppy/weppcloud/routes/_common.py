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
from flask_security import current_user, login_required, roles_accepted, roles_required
from werkzeug.utils import secure_filename

from wepppy.weppcloud.utils.helpers import (
    authorize,
    authorize_and_handle_with_exception_factory,
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
    'authorize_and_handle_with_exception_factory',
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
    'roles_accepted',
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

from wepppy.request_payload import (
    RequestPayloadError, decode_json, is_json_media, media_type, normalize_payload,
    normalize_value,
)


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
    except (OSError, RuntimeError, ValueError):
        # Never interfere with Flask's exception propagation
        return


class LoggedBlueprint(_FlaskBlueprint):
    """Blueprint that logs exceptions to the run workspace before propagation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_error_handler(Exception, self._log_and_propagate)
        self.register_error_handler(RequestPayloadError, lambda exc: (jsonify(exc.envelope()), 400))

    @staticmethod
    def _log_and_propagate(exc: Exception):
        if not getattr(exc, "_logged_to_exceptions", False):
            setattr(exc, "_logged_to_exceptions", True)
            _maybe_log_exception(exc)
        raise


# Default export: use LoggedBlueprint for all route modules importing Blueprint
Blueprint = LoggedBlueprint


def parse_json_payload(req, *, allow_list=False, boolean_fields=()):
    if getattr(req, "payload_error", None) is not None:
        raise req.payload_error
    content_type = media_type(req.content_type or "")
    if content_type in {"multipart/form-data", "application/x-www-form-urlencoded"}:
        raise RequestPayloadError()
    body = req.get_data(cache=True)
    if body and content_type and not is_json_media(content_type):
        raise RequestPayloadError()
    data = decode_json(body, allow_list=allow_list)
    if boolean_fields and isinstance(data, dict):
        flags = normalize_payload({key: data[key] for key in boolean_fields if key in data},
                                  boolean_fields=boolean_fields)
        data = {**data, **flags}
    return data


def parse_request_payload(req: 'flask.Request', *, boolean_fields=None, trim_strings=True,
                          allow_list=False, preserve_structure=False):
    content_type = media_type(req.content_type or "")
    if content_type in {"application/x-www-form-urlencoded", "multipart/form-data"}:
        if content_type == "multipart/form-data":
            # Werkzeug's silent multipart mode would otherwise accept a truncated body.
            req.form_data_parser_class = StrictFormDataParser
        raw = req.form
        if getattr(req, "payload_error", None) is not None:
            raise req.payload_error
        data = raw.to_dict(flat=False)
        return normalize_payload(data, boolean_fields=boolean_fields or (),
                                 trim_strings=trim_strings, form=True)
    body = req.get_data(cache=True)
    if body and content_type and not is_json_media(content_type):
        raise RequestPayloadError()
    data = decode_json(body, allow_list=allow_list)
    if isinstance(data, list):
        return data
    if preserve_structure:
        flags = normalize_payload({key: data[key] for key in boolean_fields or () if key in data},
                                  boolean_fields=boolean_fields or (), trim_strings=trim_strings)
        return {**data, **flags}
    return normalize_payload(data, boolean_fields=boolean_fields or (), trim_strings=trim_strings)


from wepppy.weppcloud.request import StrictFormDataParser


__all__.extend(['parse_request_payload', 'parse_json_payload', 'RequestPayloadError'])
