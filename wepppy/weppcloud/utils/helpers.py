from ast import literal_eval
import traceback

import logging
import json
import os
import csv
import inspect

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from pathlib import Path
from functools import wraps

from flask import current_app, g, jsonify, make_response, render_template, url_for
from werkzeug.exceptions import HTTPException

from datetime import datetime

import socket

from wepppy.all_your_base.all_your_base import isint
_hostname = socket.gethostname()

import redis
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

logger = logging.getLogger(__name__)

redis_wd_cache_client = None
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
    

def get_wd(runid: str, *, prefer_active: bool = True) -> str:
    """
    Gets the working directory path for a given run ID, using a Redis cache
    to speed up lookups.
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


    if ';;' in runid:
        _group, _name, _runid = runid.split(';;')
        if _group == 'batch':
            path = get_batch_run_wd(_name, _runid)
        else:
            raise ValueError(f'Unknown group prefix: {_group}')
    else:
        # Check the primary, non-prefixed location first
        path = _join('/geodata/weppcloud_runs', runid)

        # If not found, fall back to the prefixed, partitioned locations
        if not _exists(path):
            prefix = runid[:2]
            path = _join('/wc1/runs', prefix, runid)
            
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
    return _join(get_batch_root_dir(), batch_name)


def get_batch_base_wd(batch_name: str) -> str:
    return _join(get_batch_root_dir(), batch_name, '_base')


def get_batch_root_dir() -> str:
    if current_app:
        root = current_app.config.get("BATCH_RUNNER_ROOT")
        if root:
            return os.fspath(root)
    return "/wc1/batch"


def get_batch_run_wd(batch_name: str, runid: str) -> str:
    batch_wd = get_batch_wd(batch_name)

    if runid == '_base':
        return _join(batch_wd, '_base')
    else:
        return _join(batch_wd, 'runs', runid)


def url_for_run(endpoint: str, **values) -> str:
    """Generate a URL for run-scoped routes, including microservices."""

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


def error_factory(msg='Error Handling Request'):
    return jsonify({'Success': False,
                    'Error': msg})


def _ensure_text(value):
    """Return a safe text representation for logging/JSON payloads."""
    try:
        return str(value)
    except Exception:  # pragma: no cover - extremely defensive
        return repr(value)


def _format_error_message(msg):
    if isinstance(msg, BaseException):
        detail = _ensure_text(msg)
        if detail and detail != msg.__class__.__name__:
            return f'{msg.__class__.__name__}: {detail}'
        return msg.__class__.__name__
    return _ensure_text(msg)


def exception_factory(msg='Error Handling Request',
                      stacktrace=None,
                      runid=None):
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


def success_factory(kwds=None):
    if kwds is None:
        return jsonify({'Success': True})
    else:
        return jsonify({'Success': True,
                        'Content': kwds})


def authorize(runid, config, require_owner=False):
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


def get_run_owners_lazy(runid):
    from wepppy.weppcloud.app import get_run_owners
    return get_run_owners(runid)


def get_user_models():
    from wepppy.weppcloud.app import Run, User, user_datastore
    return Run, User, user_datastore

def authorize_and_handle_with_exception_factory(func):
    """
    A decorator for Flask routes that handles authorization and
    exceptions for a given runid.
    
    Expects 'runid' and 'config' to be arguments in the decorated route.
    """
    @wraps(func)
    def wrapper(runid, config, *args, **kwargs):
        try:
            # Authorize request before executing the route; aborts raise HTTPException.
            authorize(runid, config)
            
            # Execute the wrapped route once authorization succeeds.
            return func(runid, config, *args, **kwargs)
            
        except HTTPException:
            # Preserve Flask/Werkzeug HTTP errors such as abort(403).
            raise
        except Exception as e:
            # For unexpected errors, return the standard exception payload.
            return exception_factory(runid=runid)
            
    return wrapper

def handle_with_exception_factory(func):
    """Wrap a route/helper to send our standard error payload for unexpected failures."""

    @wraps(func)
    def wrapper(*args, **kwargs):
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


def parse_rec_intervals(request, years):
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
