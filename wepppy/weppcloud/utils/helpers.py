"""Shared helpers for Flask routes, run resolution, and error handling."""

from __future__ import annotations

from ast import literal_eval
from datetime import datetime
from functools import wraps
import inspect
import json
import logging
import os
import socket
import traceback
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from typing import Any, Callable, Optional, ParamSpec, TypeVar

import redis
from flask import Request, Response, current_app, g, jsonify, make_response, url_for
from werkzeug.exceptions import HTTPException

from wepppy.all_your_base.all_your_base import isint
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

_hostname = socket.gethostname()
P = ParamSpec("P")
ResponseValue = TypeVar("ResponseValue")

logger = logging.getLogger(__name__)

redis_wd_cache_client: Optional[redis.Redis] = None
REDIS_HOST = redis_host()
REDIS_WD_CACHE_DB = int(RedisDB.WD_CACHE)
try:
    pool_kwargs = redis_connection_kwargs(
        RedisDB.WD_CACHE,
        decode_responses=True,
        extra={"max_connections": 50},
    )
    redis_wd_cache_pool = redis.ConnectionPool(**pool_kwargs)
    redis_wd_cache_client = redis.StrictRedis(connection_pool=redis_wd_cache_pool)
    redis_wd_cache_client.ping()
except Exception as e:
    print(f'Error connecting to Redis: {e}')
    redis_wd_cache_client = None

_PLAYBACK_USE_CLONE = os.getenv("PROFILE_PLAYBACK_USE_CLONE", "false").lower() in {"1", "true", "yes", "on"}


def _playback_path(env_var: str, subdir: str) -> str:
    """Resolve a playback directory from environment overrides.

    Args:
        env_var: Specific environment variable for the run context.
        subdir: Default fallback sub-directory name.

    Returns:
        Absolute path to the playback asset directory.
    """
    base = os.environ.get("PROFILE_PLAYBACK_BASE", "/workdir/wepppy-test-engine-data/playback")
    return os.environ.get(env_var, _join(base, subdir))


def get_wd(runid: str, *, prefer_active: bool = True) -> str:
    """Return the working directory path for a run, caching lookups in Redis.

    Args:
        runid: Run identifier to resolve.
        prefer_active: When True, prefer the active Flask context (when available)
            before hitting Redis or the filesystem.

    Returns:
        Absolute filesystem path for the requested run.

    Raises:
        ValueError: If the run identifier encodes an unknown group prefix.
    """
    global redis_wd_cache_client

    context_override = None
    if prefer_active:
        try:
            ctx = getattr(g, 'run_context', None)
        except RuntimeError:
            ctx = None

        if ctx is not None and getattr(ctx, 'runid', None) == runid:
            pup_root = getattr(ctx, 'pup_root', None)
            if pup_root is not None:
                return str(pup_root)

            run_root = getattr(ctx, 'run_root', None)
            if run_root is not None:
                context_override = str(run_root)

    # 1. Attempt to fetch the working directory from the cache
    if redis_wd_cache_client:
        try:
            cached_wd = redis_wd_cache_client.get(runid)
            if cached_wd:
                return context_override or cached_wd
        except redis.exceptions.ConnectionError as e:
            print(f"Warning: Redis connection error during GET. Falling back to filesystem. Error: {e}")


    path = None

    if ';;' in runid:
        parts = runid.split(';;')
        if len(parts) != 3:
            raise ValueError(f'Invalid grouped run identifier: {runid}')
        _group, _name, _runid = parts
        if _group == 'batch':
            path = get_batch_run_wd(_name, _runid)
        elif _group == 'profile' and _name == 'tmp':
            playback_root = _playback_path("PROFILE_PLAYBACK_RUN_ROOT", "runs")
            path = _join(playback_root, _runid)
        elif _group == 'profile' and _name == 'fork':
            playback_root = _playback_path("PROFILE_PLAYBACK_FORK_ROOT", "fork")
            path = _join(playback_root, _runid)
        elif _group == 'profile' and _name == 'archive':
            playback_root = _playback_path("PROFILE_PLAYBACK_ARCHIVE_ROOT", "archive")
            path = _join(playback_root, _runid)
        else:
            raise ValueError(f'Unknown group prefix: {_group}')
    elif path is None:
        playback_root = _playback_path("PROFILE_PLAYBACK_RUN_ROOT", "runs") if _PLAYBACK_USE_CLONE else None
        if playback_root:
            playback_candidate = _join(playback_root, runid)
            if _exists(playback_candidate):
                path = playback_candidate

    if path is None:
        # Primary location: /wc1/runs/<prefix>/<runid> (current)
        # Legacy location: /geodata/weppcloud_runs/<runid> (deprecated)
        prefix = runid[:2]
        path = _join('/wc1/runs', prefix, runid)

        # Fall back to legacy location if not found in primary
        if not _exists(path):
            path = _join('/geodata/weppcloud_runs', runid)
            
    if context_override:
        path = context_override

    # 3. Store the determined path in the cache for future requests
    if redis_wd_cache_client:
        try:
            # Cache the result with a 72-hour (259200 seconds) expiration
            redis_wd_cache_client.set(runid, path, ex=72 * 3600)
        except redis.exceptions.ConnectionError as e:
            # If caching fails, the function still succeeds. Just log the issue.
            print(f"Warning: Redis connection error during SET. Error: {e}")

    return path

    
def get_batch_wd(batch_name: str) -> str:
    """Return the run root for a batch job.

    Args:
        batch_name: Batch identifier from the request.

    Returns:
        Absolute path to the batch directory.
    """
    return _join(get_batch_root_dir(), batch_name)


def get_batch_base_wd(batch_name: str) -> str:
    """Return the `_base` directory for a batch job.

    Args:
        batch_name: Batch identifier from the request.

    Returns:
        Absolute path to the batch's `_base` directory.
    """
    return _join(get_batch_root_dir(), batch_name, '_base')


def get_batch_root_dir() -> str:
    """Resolve the base directory for batch runner execution.

    Returns:
        Filesystem root for batch jobs as configured in Flask.
    """
    if current_app:
        root = current_app.config.get("BATCH_RUNNER_ROOT")
        if root:
            return os.fspath(root)
    return "/wc1/batch"


def get_batch_run_wd(batch_name: str, runid: str) -> str:
    """Return the working directory for a run that belongs to a batch job.

    Args:
        batch_name: Parent batch identifier.
        runid: Specific run identifier (or `_base`).

    Returns:
        Absolute path to the batch run's working directory.
    """
    batch_wd = get_batch_wd(batch_name)

    if runid == '_base':
        return _join(batch_wd, '_base')
    else:
        return _join(batch_wd, 'runs', runid)


def url_for_run(endpoint: str, **values: Any) -> str:
    """Generate a URL for run-scoped routes, including microservices.

    Args:
        endpoint: Flask endpoint name or blueprint route.
        **values: Parameters passed to `url_for`, plus optional helpers such as
            `pup` and `subpath`.

    Returns:
        Fully qualified path rooted at the optional site prefix.

    Raises:
        ValueError: If required run identifiers are missing for specialized endpoints.
    """

    site_prefix = current_app.config.get('SITE_PREFIX', '') if current_app else ''

    def _apply_site_prefix(path: str) -> str:
        if path.startswith(('http://', 'https://')):
            return path
        if not path.startswith('/'):
            path = '/' + path
        if site_prefix:
            prefix = site_prefix.rstrip('/')
            if prefix and not path.startswith(prefix + '/'):
                return prefix + path
        return path

    def _require(keys):
        missing = [k for k in keys if not values.get(k)]
        if missing:
            raise ValueError(f'Missing values for {endpoint}: {", ".join(missing)}')

    if endpoint == 'browse.browse_tree':
        _require(['runid', 'config'])
        subpath = (values.get('subpath') or '').lstrip('/')
        path = f"/runs/{values['runid']}/{values['config']}/browse/"
        if subpath:
            path += subpath
        return _apply_site_prefix(path)
    if endpoint == 'download.download_with_subpath':
        _require(['runid', 'config'])
        subpath = (values.get('subpath') or '').lstrip('/')
        path = f"/runs/{values['runid']}/{values['config']}/download/"
        if subpath:
            path += subpath
        return _apply_site_prefix(path)
    if endpoint == 'gdalinfo.gdalinfo_with_subpath':
        _require(['runid', 'config', 'subpath'])
        subpath = values['subpath'].lstrip('/')
        return _apply_site_prefix(f"/runs/{values['runid']}/{values['config']}/gdalinfo/{subpath}")
    if endpoint == 'download.aria2c_spec':
        _require(['runid', 'config'])
        return _apply_site_prefix(f"/runs/{values['runid']}/{values['config']}/aria2c.spec")

    if 'pup' not in values:
        pup_relpath = getattr(g, 'pup_relpath', None)
        if pup_relpath:
            values['pup'] = pup_relpath

    url = url_for(endpoint, **values)
    return _apply_site_prefix(url)


def error_factory(msg: str = 'Error Handling Request') -> Response:
    """Return a consistent JSON error payload for lightweight failures.

    Args:
        msg: Human-readable error message.

    Returns:
        Flask `Response` object with a JSON body.
    """
    return jsonify({'Success': False,
                    'Error': msg})


def _ensure_text(value: Any) -> str:
    """Return a safe text representation for logging/JSON payloads.

    Args:
        value: Arbitrary value that needs to be logged.

    Returns:
        String representation that best describes the value.
    """
    try:
        return str(value)
    except Exception:  # pragma: no cover - extremely defensive
        return repr(value)


def _format_error_message(msg: BaseException | str) -> str:
    """Normalize exception objects or strings into a single-line message."""
    if isinstance(msg, BaseException):
        detail = _ensure_text(msg)
        if detail and detail != msg.__class__.__name__:
            return f'{msg.__class__.__name__}: {detail}'
        return msg.__class__.__name__
    return _ensure_text(msg)


def exception_factory(
    msg: BaseException | str = 'Error Handling Request',
    stacktrace: Optional[str] = None,
    runid: Optional[str] = None,
) -> Response:
    """Log an exception and return the standard error payload.

    Args:
        msg: Exception or string describing the failure.
        stacktrace: Optional pre-rendered stack trace.
        runid: Optional run identifier to help locate context.

    Returns:
        Flask `Response` with the JSON error payload and HTTP 500 status.
    """
    if stacktrace is None:
        stacktrace = traceback.format_exc()

    message = _format_error_message(msg)
    stacktrace_text = stacktrace if isinstance(stacktrace, str) else _ensure_text(stacktrace)
    stacktrace_lines = stacktrace_text.splitlines() if isinstance(stacktrace_text, str) else [_ensure_text(stacktrace_text)]

    log_suffix = f' for run {runid}' if runid else ''
    logger.error('Exception handling request%s: %s\n%s', log_suffix, message, stacktrace_text)

    if runid is not None:
        wd = get_wd(runid)
        if _exists(wd):
            try:
                with open(_join(wd, 'exception_factory.log'), 'a') as fp:
                    fp.write(f'[{datetime.now()}]\n')
                    fp.write(stacktrace_text)
                    fp.write('\n\n')
            except OSError as log_error:
                logger.warning('Error writing run exception log for %s: %s', runid, log_error)

    payload = {
        'Success': False,
        'Error': message,
        'StackTrace': stacktrace_lines,
    }

    try:
        return make_response(jsonify(payload), 500)
    except TypeError:
        fallback = make_response(json.dumps(payload), 500)
        fallback.mimetype = 'application/json'
        return fallback


def success_factory(kwds: Optional[dict[str, Any]] = None) -> Response:
    """Return a success response optionally embedding content.

    Args:
        kwds: Optional dictionary attached under the `Content` key.

    Returns:
        Flask `Response` with a JSON body and success flag.
    """
    if kwds is None:
        return jsonify({'Success': True})
    else:
        return jsonify({'Success': True,
                        'Content': kwds})


def authorize(runid: str, config: str, require_owner: bool = False) -> None:
    """Validate that the current user can access a run's resources.

    Args:
        runid: Run identifier to check.
        config: Configuration slug used in the request.
        require_owner: Reserved flag for future owner-only enforcement.

    Raises:
        werkzeug.exceptions.HTTPException: Propagated when Flask aborts.
    """
    from flask_login import current_user
    from flask import abort
    from wepppy.nodb.core import Ron
    from wepppy.weppcloud.app import get_run_owners

    login_manager = getattr(current_app, "login_manager", None)
    if login_manager is None:
        return

    try:
        if current_user.has_role("Admin"):
            return
    except Exception:
        return

    wd = get_wd(runid)
    owners = get_run_owners(runid)

    if not owners:
        return  # No owners means public run
    
    if current_user in owners:
        return
    
    if  Ron.ispublic(wd):
        return

    abort(403)


def get_run_owners_lazy(runid: str) -> Any:
    """Import-on-demand helper for retrieving run owners.

    Args:
        runid: Target run identifier.

    Returns:
        Whatever `get_run_owners` returns (typically a collection of users).
    """
    from wepppy.weppcloud.app import get_run_owners
    return get_run_owners(runid)


def get_user_models() -> tuple[Any, Any, Any]:
    """Import the ORM models used for user/run metadata.

    Returns:
        Tuple of `(Run, User, user_datastore)` objects from the Flask app.
    """
    from wepppy.weppcloud.app import Run, User, user_datastore
    return Run, User, user_datastore

def authorize_and_handle_with_exception_factory(
    func: Callable[..., ResponseValue],
) -> Callable[..., Response | ResponseValue]:
    """Decorate run-scoped routes with auth checks and exception handling.

    Args:
        func: Route callable that expects `runid` and `config` as the first two
            positional arguments.

    Returns:
        Wrapped callable that enforces authorization and standard error payloads.
    """

    @wraps(func)
    def wrapper(runid: str, config: str, *args: Any, **kwargs: Any) -> Response | ResponseValue:
        try:
            # Authorize request before executing the route; aborts raise HTTPException.
            authorize(runid, config)
            
            # Execute the wrapped route once authorization succeeds.
            return func(runid, config, *args, **kwargs)
            
        except HTTPException:
            # Preserve Flask/Werkzeug HTTP errors such as abort(403).
            raise
        except Exception:
            # For unexpected errors, return the standard exception payload.
            return exception_factory(runid=runid)
            
    return wrapper

def handle_with_exception_factory(
    func: Callable[P, ResponseValue],
) -> Callable[P, Response | ResponseValue]:
    """Wrap a callable to return the standard error payload on failure.

    Args:
        func: Callable that may raise unexpected exceptions.

    Returns:
        Wrapped callable that downgrades errors into JSON responses.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Response | ResponseValue:
        # Prefer an explicit runid kwarg; otherwise inspect the signature to find one.
        runid = kwargs.get('runid')
        if runid is None:
            try:
                bound = inspect.signature(func).bind_partial(*args, **kwargs)
                runid = bound.arguments.get('runid')
            except Exception:
                runid = None

        try:
            # Call the wrapped function and bubble up successful responses.
            return func(*args, **kwargs)

        except HTTPException:
            # Preserve deliberate HTTP errors such as abort(404) / abort(403).
            raise
        except Exception:
            # Anything else becomes our standard error response, optionally tagged with runid.
            return exception_factory(runid=runid)

    return wrapper


def parse_rec_intervals(request: Request, years: int) -> list[int]:
    """Parse recurrence intervals from query parameters.

    Args:
        request: Active Flask request containing `rec_intervals`.
        years: Total simulation span used to determine default intervals.

    Returns:
        List of recurrence intervals sorted from largest to smallest.
    """
    rec_intervals = request.args.get('rec_intervals', None)
    if rec_intervals is None:
        rec_intervals = [2, 5, 10, 20, 25]
        if years >= 50:
            rec_intervals.append(50)
        if years >= 100:
            rec_intervals.append(100)
        if years >= 200:
            rec_intervals.append(200)
        if years >= 500:
            rec_intervals.append(500)
        if years >= 1000:
            rec_intervals.append(1000)
        rec_intervals = rec_intervals[::-1]
    else:
        rec_intervals = literal_eval(rec_intervals)
        assert all([isint(x) for x in rec_intervals])

    return rec_intervals
