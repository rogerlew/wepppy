# Copyright (c) 2016-2025, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import functools
import importlib
import inspect
import multiprocessing as mp
import socket
import re
import sys
import uuid
from concurrent.futures import ProcessPoolExecutor
from dotenv import load_dotenv
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import os

__all__ = [
    'NoDbAlreadyLockedError',
    'redis_nodb_cache_client',
    'redis_status_client',
    'redis_log_level_client',
    'REDIS_HOST',
    'REDIS_PORT',
    'REDIS_NODB_CACHE_DB',
    'REDIS_STATUS_DB',
    'REDIS_LOCK_DB',
    'REDIS_NODB_EXPIRY',
    'REDIS_LOG_LEVEL_DB',
    'LogLevel',
    'try_redis_get_log_level',
    'try_redis_set_log_level',
    'createProcessPoolExecutor',
    'get_config_dir',
    'CaseSensitiveRawConfigParser',
    'get_configs',
    'get_legacy_configs',
    'nodb_setter',
    'nodb_timed',
    'TriggerEvents',
    'NoDbBase',
    'iter_nodb_mods_subclasses',
    'clear_locks',
    'lock_statuses',
    'clear_nodb_file_cache',
]

_thisdir = os.path.dirname(__file__)
load_dotenv(_join(_thisdir, '.env'))

import ast
from time import time
from enum import Enum, IntEnum
from glob import glob
from contextlib import contextmanager
from pathlib import Path
from typing import ClassVar, Optional
from weakref import WeakKeyDictionary
from collections import defaultdict

import json

# non-standard
import jsonpickle

from configparser import (
    RawConfigParser,
    NoOptionError,
    NoSectionError
)

import logging
import queue
from logging.handlers import QueueHandler, QueueListener
import atexit
from logging import FileHandler, StreamHandler
from wepppy.nodb.status_messenger import StatusMessengerHandler


class NoDbAlreadyLockedError(Exception):
    """Raised when attempting to lock a NoDb instance that is already locked."""
    pass

from wepppy.all_your_base import isfloat, isint, isbool
from .redis_prep import RedisPrep
# Configure redis
import redis
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
    redis_port,
)
from .version import CURRENT_VERSION, ensure_version, write_version


def _discover_legacy_module_redirects():
    """Build lookup of legacy module stems to their relocated modules."""
    base_dir = Path(__file__).resolve().parent
    redirects = {}

    def register(stem, module_path):
        if stem in ('', '__init__'):
            return
        redirects.setdefault(stem, module_path)

    # Prefer package-level modules when available.
    for init_path in base_dir.rglob('__init__.py'):
        rel = init_path.relative_to(base_dir)
        parts = rel.with_suffix('').parts[:-1]
        if not parts:
            continue
        module_path = 'wepppy.nodb.' + '.'.join(parts)
        register(init_path.parent.name, module_path)

    for py_path in base_dir.rglob('*.py'):
        if py_path.name == '__init__.py':
            continue
        rel = py_path.relative_to(base_dir)
        module_path = 'wepppy.nodb.' + '.'.join(rel.with_suffix('').parts)
        register(py_path.stem, module_path)

    return redirects


_LEGACY_MODULE_REDIRECTS = _discover_legacy_module_redirects()

redis_nodb_cache_client = None
redis_status_client = None
redis_log_level_client = None
REDIS_HOST = redis_host()
REDIS_PORT = redis_port()
REDIS_NODB_CACHE_DB = int(RedisDB.NODB_CACHE)
REDIS_STATUS_DB = int(RedisDB.STATUS)
REDIS_LOCK_DB = int(RedisDB.LOCK)
REDIS_NODB_EXPIRY = 72 * 3600  # 72 hours
REDIS_LOG_LEVEL_DB = int(RedisDB.LOG_LEVEL)


def _default_lock_ttl():
    try:
        return int(os.getenv('WEPPPY_LOCK_TTL_SECONDS', 6 * 3600))
    except (TypeError, ValueError):
        return 6 * 3600


LOCK_KEY_PREFIX = 'nodb-lock'
LOCK_DEFAULT_TTL = max(1, _default_lock_ttl())
_ACTIVE_LOCK_TOKENS: WeakKeyDictionary = WeakKeyDictionary()


def _normalize_lock_relpath(relpath: str) -> str:
    return relpath.replace('\\', '/')


def _lock_key_for(runid: str, relpath: str) -> str:
    norm_rel = _normalize_lock_relpath(relpath)
    return f'{LOCK_KEY_PREFIX}:{runid}:{norm_rel}'


def _lock_owner_id() -> str:
    return f'{socket.gethostname()}:{os.getpid()}'


def _serialize_lock_payload(token: str, ttl: int) -> str:
    now = int(time())
    payload = {
        'token': token,
        'owner': _lock_owner_id(),
        'acquired_at': now,
        'expires_at': now + ttl,
        'ttl': ttl,
    }
    return json.dumps(payload, separators=(',', ':'))


def _parse_lock_payload(raw: str) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    # Legacy payloads may simply be the token string.
    return {'token': raw}


def _extract_token(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    data = _parse_lock_payload(raw)
    token = data.get('token')
    if token is None and raw:
        return raw
    return token


def _set_local_lock_token(instance, token: Optional[str]):
    if token is None:
        _ACTIVE_LOCK_TOKENS.pop(instance, None)
    else:
        _ACTIVE_LOCK_TOKENS[instance] = token


def _get_local_lock_token(instance) -> Optional[str]:
    return _ACTIVE_LOCK_TOKENS.get(instance)


def _matches_scope(relpath: str, scope: Optional[str]) -> bool:
    if scope is None:
        return True
    rel_norm = _normalize_lock_relpath(relpath)
    scope_norm = _normalize_lock_relpath(scope)
    return rel_norm == scope_norm or rel_norm.startswith(scope_norm + '/')


def _relpath_from_lock_key(runid: str, lock_key: str) -> str:
    prefix = f'{LOCK_KEY_PREFIX}:{runid}:'
    if lock_key.startswith(prefix):
        rel = lock_key[len(prefix):]
        return rel.replace('/', os.sep)
    return lock_key


try:
    pool_kwargs = redis_connection_kwargs(
        RedisDB.NODB_CACHE,
        decode_responses=True,
        extra={"max_connections": 50},
    )
    redis_nodb_cache_pool = redis.ConnectionPool(**pool_kwargs)
    redis_nodb_cache_client = redis.StrictRedis(connection_pool=redis_nodb_cache_pool)
    redis_nodb_cache_client.ping()
except Exception as e:
    logging.critical(f'Error connecting to Redis with pool: {e}')
    redis_nodb_cache_client = None

try:
    pool_kwargs = redis_connection_kwargs(
        RedisDB.STATUS,
        decode_responses=True,
        extra={"max_connections": 50},
    )
    redis_status_pool = redis.ConnectionPool(**pool_kwargs)
    redis_status_client = redis.StrictRedis(connection_pool=redis_status_pool)
    redis_status_client.ping()
except Exception as e:
    logging.critical(f'Error connecting to Redis with pool: {e}')
    redis_status_client = None

try:
    pool_kwargs = redis_connection_kwargs(
        RedisDB.LOCK,
        decode_responses=True,
        extra={"max_connections": 50},
    )
    redis_lock_pool = redis.ConnectionPool(**pool_kwargs)
    redis_lock_client = redis.StrictRedis(connection_pool=redis_lock_pool)
    redis_lock_client.ping()
except Exception as e:
    logging.critical(f'Error connecting to Redis with pool: {e}')
    redis_lock_client = None

try:
    pool_kwargs = redis_connection_kwargs(
        RedisDB.LOG_LEVEL,
        decode_responses=True,
        extra={"max_connections": 50},
    )
    redis_log_level_pool = redis.ConnectionPool(**pool_kwargs)
    redis_log_level_client = redis.StrictRedis(connection_pool=redis_log_level_pool)
    redis_log_level_client.ping()
except Exception as e:
    logging.critical(f'Error connecting to Redis with pool: {e}')
    redis_log_level_client = None

class LogLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    @staticmethod
    def parse(x: str):
        x = x.lower()
        if x == 'debug':
            return LogLevel.DEBUG
        elif x == 'info':
            return LogLevel.INFO
        elif x == 'warning':
            return LogLevel.WARNING
        elif x == 'error':
            return LogLevel.ERROR
        elif x == 'critical':
            return LogLevel.CRITICAL
        return LogLevel.INFO
    
    def __str__(self):
        return super().__str__().replace('LogLevel.', '').lower()


def try_redis_get_log_level(runid, default=logging.INFO):
    if redis_log_level_client is None:
        return default
    try:
        level = redis_log_level_client.get(f'loglevel:{runid}')
        if level is None:
            return default
        try:
            return int(LogLevel.parse(level))
        except ValueError:
            logging.error(f'Invalid log level in Redis: {level}')
            return default
    except Exception as e:
        logging.error(f'Error getting log level from Redis: {e}')
        return default
    

def try_redis_set_log_level(runid, level: str):
    if redis_log_level_client is None:
        return

    try:
        level = LogLevel.parse(level)
        redis_log_level_client.set(f'loglevel:{runid}', str(level))
    except Exception as e:
        logging.error(f'Error setting log level in Redis: {e}')

    try:
        logging.getLogger(f'wepppy.run.{runid}').setLevel(int(level))
    except Exception as e:
        logging.error(f'Error setting log level for logger: {e}')


def createProcessPoolExecutor(max_workers, logger=None, prefer_spawn=True):
    """Create a `ProcessPoolExecutor`, preferring the spawn context when requested.

    Falls back to the default context when spawn is unavailable, restricted,
    or explicitly disabled (for example, when pickling non-spawn-safe objects).

    Args:
        max_workers (int): Required worker count for the pool.
        logger: Optional logger used for warning messages.
        prefer_spawn (bool): If True (default), attempt to use the spawn start
            method before falling back to the platform default.

    Returns:
        ProcessPoolExecutor: Configured executor instance.
    """
    if max_workers is None:
        raise ValueError('max_workers is required')

    log = logger or logging.getLogger(__name__)

    if prefer_spawn:
        ctx = None
        try:
            ctx = mp.get_context('spawn')
        except (AttributeError, ValueError, RuntimeError):
            ctx = None

        if ctx is not None:
            try:
                return ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx)
            except (OSError, PermissionError) as exc:
                log.warning(
                    'Spawn start method unavailable for ProcessPoolExecutor (%s); using default context instead.',
                    exc)
            except Exception as exc:  # pragma: no cover - unexpected spawn errors
                log.warning(
                    'Spawn start method failed for ProcessPoolExecutor (%s); using default context instead.',
                    exc)

    return ProcessPoolExecutor(max_workers=max_workers)

_thisdir = os.path.dirname(__file__)
_config_dir = _join(_thisdir, 'configs')
_default_config = _join(_config_dir, '_defaults.toml')

def get_config_dir():
    return _config_dir

class CaseSensitiveRawConfigParser(RawConfigParser):
    def optionxform(self, s): return s

def get_configs():
    return [Path(fn).stem for fn in glob(_join(_config_dir, '*.cfg'))]

def get_legacy_configs():
    return [Path(fn).stem for fn in glob(_join(_config_dir, 'legacy', '*.toml'))]

def nodb_setter(setter_func):
    """
    A decorator that logs the setter call and wraps the operation
    in a 'locked' context.
    """
    @functools.wraps(setter_func)
    def wrapper(self, value):
        # setter_func.__name__ will correctly be 'input_years'
        # thanks to @functools.wraps
        func_name = setter_func.__name__
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')
        
        with self.locked():
            # Call the original setter function to perform the assignment
            return setter_func(self, value)
            
    return wrapper

def nodb_setter(setter_func):
    """
    A decorator that logs the setter call and wraps the operation
    in a 'locked' context.
    """
    @functools.wraps(setter_func)
    def wrapper(self, value):
        # setter_func.__name__ will correctly be 'input_years'
        # thanks to @functools.wraps
        func_name = setter_func.__name__
        self.logger.info(f'{self.class_name}.{func_name} -> {value}')
        
        with self.locked():
            # Call the original setter function to perform the assignment
            return setter_func(self, value)
            
    return wrapper

def nodb_timed(method_func):
    """
    A decorator that wraps a method call in the instance's `timed` 
    context manager, using the method's name as the task name.
    """
    @functools.wraps(method_func)
    def wrapper(self, *args, **kwargs):
        # method_func.__name__ correctly gets the decorated function's name
        func_name = method_func.__name__
        
        with self.timed(func_name):
            # Call the original method and return its result
            return method_func(self, *args, **kwargs)
            
    return wrapper

class TriggerEvents(Enum):
    ON_INIT_FINISH = 1
    LANDUSE_DOMLC_COMPLETE = 2
    LANDUSE_BUILD_COMPLETE = 5
    SOILS_BUILD_COMPLETE = 3
    PREPPING_PHOSPHORUS = 4
    WATERSHED_ABSTRACTION_COMPLETE = 5
    CLIMATE_BUILD_COMPLETE = 6
    WEPP_PREP_WATERSHED_COMPLETE = 7
    FORK_COMPLETE = 8


class NoDbBase(object):
    DEBUG = 0
    _js_decode_replacements = ()

    filename: ClassVar[str] = None # just the basename
    _legacy_module_redirects: ClassVar[dict[str, str]] = _LEGACY_MODULE_REDIRECTS

    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        wd = os.path.abspath(wd)
        assert _exists(wd)

        if not _exists(_join(wd, 'READONLY')):
            ensure_version(wd)

        if run_group is not None:
            self._run_group = run_group

        if group_name is not None:
            self._group_name = group_name

        self.wd = wd
        self._config = cfg_fn
        self._load_mods()

        commit_hash_fn = _join(os.path.dirname(__file__), 'commit_hash')
        if _exists(commit_hash_fn):
            with open(commit_hash_fn) as fp:
                self.commit_hash = fp.read().strip()
        else:
            self.commit_hash = 'unknown'
        
        # noinspection PyUnresolvedReferences
        if _exists(self._nodb):  # absolute path to .nodb file
            raise Exception('NoDb has already been initialized')

        self._init_logging()

    @property
    def _nodb(self):
        """
        Absolute path to the .nodb file from the runid working directory.
        """
        return _join(self.wd, self.filename)
    
    @property
    def _rel_nodb(self):
        """
        Relative path to the .nodb file from the runid working directory.

        e.g. 'wepp.nodb', 'ron.nodb', 'landuse.nodb', etc.
        or for pup (child) runs: '_pups/omni/scenarios/undisturbed/wepp.nodb'
        """
        _rel_path = self.pup_relpath
        if _rel_path is None:
            return self.filename
        return _join(_rel_path, self.filename)

    @property
    def _file_lock_key(self):
        return f'locked:{self._rel_nodb}'
    
    @property
    def _distributed_lock_key(self):
        return _lock_key_for(self.runid, self._rel_nodb)
            
    @property
    def parent_wd(self):
        return getattr(self, '_parent_wd', None)
    
    @parent_wd.setter
    def parent_wd(self, value: str):
        self._parent_wd = value

    @property
    def is_child_run(self):
        if self.parent_wd is None:
            return False
        
        return self.pup_relpath.startswith('_pups/')

    @property
    def pup_relpath(self):  # relative path to the parent or None
        if self.parent_wd is None:
            return None
        
        parent_wd = os.path.abspath(self.parent_wd)
        wd = os.path.abspath(self.wd)

        if wd.startswith(parent_wd):
            relpath = os.path.relpath(wd, parent_wd)
            return relpath
        
        return None
    
        
    @property
    def _logger_base_name(self):
        _rel_path = self.pup_relpath
        if _rel_path is None:
            return f'wepppy.run.{self.runid}'
        _rel_path = _rel_path.split('/')
        return f'wepppy.run.{self.runid}' + '.' + ','.join(_rel_path)
    
    @property
    def class_name(self):
        return type(self).filename.removesuffix(".nodb")

    @property
    def _status_channel(self):
        """
        Redis channel name for status messages.
        """
        # this is a router
        _rel_path = self.pup_relpath
        if _rel_path is None:    
            return f'{self.runid}:{self.class_name}'
    
        if _rel_path.startswith('_pups/omni/'):
            return f'{self.runid}:omni'

    def _init_logging(self):
        # Initialize loggers
        self.runid_logger = logging.getLogger(f'wepppy.run.{self.runid}')  # project logger
        self.logger = logging.getLogger(f'{self._logger_base_name}.{self.class_name}')  # project component logger

        # Check if queue handler exists
        queue_handler = getattr(self.runid_logger, '_queue_handler', None)

        # Define a standard log format
        log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'  # Local time with milliseconds and timezone
        formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

        if queue_handler is None:
            # Initialize queue and queue handler
            self._log_queue = queue.Queue(-1)
            self._queue_handler = QueueHandler(self._log_queue)

            # Clear existing handlers from runid_logger
            for handler in list(self.logger.handlers):
                self.logger.removeHandler(handler)

            self.logger.setLevel(logging.INFO)
            self.logger.propagate = True  # allow to propagate to runid_logger
            self.logger.addHandler(self._queue_handler)

            # Redis handler to proxy to web clients
            self._redis_handler = StatusMessengerHandler(
                channel=self._status_channel
            )
            self._redis_handler.setLevel(logging.DEBUG)

            # File handler for run logs
            log_path = self._nodb.replace('.nodb', '.log')  # absoloute path to log file
            self._run_file_handler = FileHandler(log_path)
            self._run_file_handler.setLevel(try_redis_get_log_level(self.runid, logging.INFO))
            self._run_file_handler.setFormatter(formatter)
            Path(log_path).touch(exist_ok=True)

            # Console handler
            self._console_handler = StreamHandler()
            self._console_handler.setLevel(logging.ERROR)
            self._console_handler.setFormatter(formatter)

            # RunID exceptions handler
            exceptions_path = _join(self.wd, 'exceptions.log')  # absolute path to exceptions log
            self._exception_file_handler = FileHandler(exceptions_path)
            self._exception_file_handler.setLevel(try_redis_get_log_level(self.runid, logging.ERROR))
            self._exception_file_handler.setFormatter(formatter)
            Path(exceptions_path).touch(exist_ok=True)

            # Initialize queue listener with all handlers
            self._queue_listener = QueueListener(
                self._log_queue,
                self._redis_handler,
                self._run_file_handler,
                self._console_handler
            )
            self._queue_listener.start()
            atexit.register(self._queue_listener.stop)

            self.runid_logger.setLevel(logging.ERROR)
            self.runid_logger.propagate = True  # allow propagation to root logger
            self.runid_logger.addHandler(self._exception_file_handler)

            # Attach handlers to component logger for reuse
            self.logger._log_queue = self._log_queue
            self.logger._queue_handler = self._queue_handler
            self.logger._queue_listener = self._queue_listener
            self.logger._redis_handler = self._redis_handler
            self.logger._run_file_handler = self._run_file_handler
            self.logger._exception_file_handler = self._exception_file_handler
            self.logger._console_handler = self._console_handler
        else:
            # Reuse existing handlers
            self._queue_handler = self.logger.queue_handler
            self._log_queue = self.logger._log_queue
            self._queue_listener = self.logger._queue_listener
            self._redis_handler = self.logger._redis_handler
            self._run_file_handler = self.logger._run_file_handler
            self._exception_file_handler = self.logger._exception_file_handler
            self._console_handler = self.logger._console_handler

    def __getstate__(self):
        state = self.__dict__.copy()
        for attr in (
            'runid_logger',
            'logger',
            '_queue_handler',
            '_log_queue',
            '_queue_listener',
            '_redis_handler',
            '_run_file_handler',
            '_exception_file_handler',
            '_console_handler',
        ):
            state.pop(attr, None)
        return state

    @contextmanager
    def timed(self, task_name: str, level=logging.INFO):
        """Context manager to log the start, end, and duration of a task."""
        from time import perf_counter

        self.logger.log(level, f"{task_name}...")
        start_time = perf_counter()
        try:
            yield
        finally:
            end_time = perf_counter()
            duration = end_time - start_time
            self.logger.log(level, f"{task_name}... done. ({duration:.2f}s)")

    @classmethod
    def getInstance(cls, wd='.', allow_nonexistent=False, ignore_lock=False):
        global redis_nodb_cache_client, REDIS_NODB_EXPIRY

        wd = os.path.abspath(wd)
        filepath = cls._get_nodb_path(wd)
        readonly = _exists(_join(wd, 'READONLY'))

        if not readonly and _exists(filepath):
            ensure_version(wd)

        # if redis_nodb_cache_client is available try to load from cache
        if redis_nodb_cache_client is not None:
            cached_data = redis_nodb_cache_client.get(filepath)
            if cached_data is not None:
                try:
                    db = cls._decode_jsonpickle(cached_data)
                    if isinstance(db, cls):
                        db = cls._post_instance_loaded(db)
                        db._init_logging()
                        db.logger.debug(f'Loaded NoDb instance from redis://{REDIS_HOST}/{REDIS_NODB_CACHE_DB}{filepath}')
                        return db
                except Exception as e:
                    print(f'Error decoding cached data for {filepath}: {e}')
                    redis_nodb_cache_client.delete(filepath)

        # fall back to loading from file
        if not _exists(filepath):
            if allow_nonexistent:
                return None
            raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            json_text = fp.read()

        json_text = cls._preprocess_json_for_decode(json_text)
        cls._ensure_legacy_module_imports(json_text)
        db = cls._decode_jsonpickle(json_text)

        # update cache if it is available
        if redis_nodb_cache_client:
            try:
                # Cache the newly loaded object for next time
                redis_nodb_cache_client.set(filepath, jsonpickle.encode(db), ex=REDIS_NODB_EXPIRY)
            except Exception as e:
                print(f"Warning: Could not update Redis cache for {filepath}: {e}")

        # validate and return
        if not isinstance(db, cls):
            raise TypeError(f"Decoded object type {type(db)} does not match expected {cls}")

        db = cls._post_instance_loaded(db)

        abs_wd = os.path.abspath(wd)
        db_wd = db.wd

        if readonly or ignore_lock:
            db.wd = abs_wd
            db._init_logging()
            return db

        if abs_wd != os.path.abspath(db_wd):
            logging.error(f"Warning: working directory mismatch: {abs_wd} != {db_wd}")
            db.wd = abs_wd
#            if not db.islocked():
#                with db.locked():
#                    db.wd = wd

        db._init_logging()
        return db
    
    @classmethod
    def tryGetInstance(cls, wd='.', allow_nonexistent=True, ignore_lock=False):
        try:
            return cls.getInstance(wd, allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)
        except FileNotFoundError:
            return None

    @classmethod
    def getInstanceFromRunID(cls, runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd

        return cls.getInstance(
            get_wd(runid), allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock
        )

    @contextmanager
    def locked(self, validate_on_success=True):
        """
        A context manager to handle the lock -> modify -> dump/unlock pattern.

        Usage:
            with self.locked():
                # modify attributes here
                self.foo = 'bar'
        
        On successful exit from the 'with' block, it calls dump_and_unlock().
        If an exception occurs, it calls unlock() and re-raises the exception.
        """
        if self.readonly:
            raise Exception('Cannot use locked context on a readonly project.')

        self.lock()
        try:
            yield
        except Exception:
            self.unlock()
            raise
        self.dump_and_unlock()

    def dump_and_unlock(self, validate=True):
        self.dump()
        self.unlock()

        if validate:
            nodb = type(self)

            # noinspection PyUnresolvedReferences
            nodb.getInstance(self.wd)

        self = type(self)._post_dump_and_unlock(self)
                
    @classmethod
    def _post_dump_and_unlock(cls, instance):
        # hook for subclasses needing to mutate the decoded instance
        return instance

    def dump(self):
        global redis_nodb_cache_client, REDIS_NODB_EXPIRY

        if not self.islocked():
            raise RuntimeError("cannot dump to unlocked db")

        js = jsonpickle.encode(self)

        # Write-then-sync
        with open(self._nodb, "w") as fp:  # absolute path to .nodb file
            fp.write(js)
            fp.flush()                 # flush Python’s userspace buffer
            os.fsync(fp.fileno())      # fsync forces kernel page-cache to disk

        write_version(self.wd, CURRENT_VERSION)

        if redis_nodb_cache_client is not None:
            try:
                redis_nodb_cache_client.set(self._nodb, js, ex=REDIS_NODB_EXPIRY) 
            except Exception as e:
                print(f'Error caching NoDb instance to Redis: {e}')

        try:
            from wepppy.weppcloud.db_api import update_last_modified
            update_last_modified(self.runid)
        except Exception:
            pass

    @classmethod
    def _get_nodb_path(cls, wd):
        if cls.filename is None:
            raise AttributeError(f"{cls.__name__} must define a class attribute 'filename'")
        return _join(wd, cls.filename)

    @classmethod
    def _preprocess_json_for_decode(cls, json_text):
        for old, new in getattr(cls, '_js_decode_replacements', ()):
            json_text = json_text.replace(old, new)
        return json_text

    @classmethod
    def _decode_jsonpickle(cls, json_text):
        return jsonpickle.decode(json_text)

    @classmethod
    def _ensure_legacy_module_imports(cls, json_text: str):
        if 'wepppy.nodb.' not in json_text:
            return

        legacy_modules = {
            token.rsplit('.', 1)[0]
            for token in re.findall(r'"py/(?:object|class)":\s*"(wepppy\.nodb\.[^"]+)"', json_text)
        }

        for legacy_module in legacy_modules:
            if legacy_module in sys.modules:
                continue

            simple_name = legacy_module.rsplit('.', 1)[-1]
            target_module = cls._legacy_module_redirects.get(simple_name)
            if not target_module:
                continue

            try:
                module = importlib.import_module(target_module)
            except ModuleNotFoundError:
                continue

            sys.modules.setdefault(legacy_module, module)

    @classmethod
    def _import_mod_module(cls, mod_name: str):
        """Ensure the NoDb mod module that defines ``mod_name`` is imported."""
        target_module = cls._legacy_module_redirects.get(mod_name)
        if not target_module:
            return

        if target_module in sys.modules:
            return

        try:
            importlib.import_module(target_module)
        except ModuleNotFoundError:
            logging.getLogger(__name__).warning(
                "NoDb mod '%s' module '%s' not found during import", mod_name, target_module
            )

    @classmethod
    def _post_instance_loaded(cls, instance):
        # hook for subclasses needing to mutate the decoded instance
        return instance

    @property
    def watershed_instance(self):
        from .core.watershed import Watershed
        return Watershed.getInstance(self.wd)
    
    @property
    def wepp_instance(self):
        from .core.wepp import Wepp
        return Wepp.getInstance(self.wd)
    
    @property
    def climate_instance(self):
        from .core.climate import Climate
        return Climate.getInstance(self.wd)
    
    @property
    def soils_instance(self):
        from .core.soils import Soils
        return Soils.getInstance(self.wd)
    
    @property
    def landuse_instance(self):
        from .core.landuse import Landuse
        return Landuse.getInstance(self.wd)
    
    @property
    def ron_instance(self):
        from .core.ron import Ron
        return Ron.getInstance(self.wd)
    
    @property
    def redis_prep_instance(self):
        return RedisPrep.getInstance(self.wd)
    
    @property
    def disturbed_instance(self):
        from .mods.disturbed import Disturbed
        return Disturbed.getInstance(self.wd)
    
    @property
    def has_sbs(self):
        from wepppy.nodb.mods.disturbed import Disturbed
        from wepppy.nodb.mods.baer import Baer

        try:
            baer = Disturbed.getInstance(self.wd)
            return baer.has_map
        except:
            pass

        try:
            baer = Baer.getInstance(self.wd)
            return baer.has_map
        except:
            pass

        return False

    @property
    def config_stem(self):
        return self._config.split('.cfg')[0]

    def config_get_bool(self, section: str, option: str, default=None):
        assert default is None or isbool(default)
        try:

            val = self._configparser.get(section, option).lower()
            if val.startswith('none') or val == '' or val.startswith('null'):
                return default
            return val.startswith('true')
        except (NoSectionError, NoOptionError):
            return default

    def config_get_float(self, section: str, option: str, default=None):
        assert default is None or isfloat(default)

        try:
            val = self._configparser.get(section, option).lower()
            if val.startswith('none') or val == '' or val.startswith('null'):
                return default
            return float(val)
        except (NoSectionError, NoOptionError):
            return default

    def config_get_int(self, section: str, option: str, default=None):
        assert default is None or isint(default)

        try:
            val = self._configparser.get(section, option).lower()
            if val.startswith('none') or val == '' or val.startswith('null'):
                return default
            return int(val)
        except (NoSectionError, NoOptionError):
            return default

    def config_iter_section(self, section):
        try:
            options = self._configparser.options(section)
            for option in options:
                yield option, self.config_get_str(section, option)
        except NoSectionError:
            return

    def config_get_str(self, section: str, option: str, default=None):

        try:
            val = self._configparser.get(section, option)
            val = val.replace("'", '').replace('"', '')
            if val.lower().startswith('none') or val == '' or val.startswith('null'):
                return default

            if val.startswith("'") and val.endswith("'"):
                val = val[1:-1]

            elif val.startswith('"') and val.endswith("'"):
                val = val[1:-1]

            return val
        except (NoSectionError, NoOptionError):
            return default

    def config_get_path(self, section: str, option: str, default=None):
        from .mods import MODS_DIR
        path = self.config_get_str(section, option, default)
        if path is None:
            return None
        path = path.replace('MODS_DIR', MODS_DIR)
        return path

    def config_get_raw(self, section: str, option: str, default=None):
        val = self._configparser.get(section, option, fallback=default)
        return val

    def config_get_list(self, section: str, option: str, default=None):
        val = self._configparser.get(section, option, fallback=default)

        if val is not None:
            # if val is a list return val
            if isinstance(val, list):
                return val
            
            # if val is a string, try to convert it to a list
            if isinstance(val, str):
                val = ast.literal_eval(val)

        if val is None:
            val = []
        return val

    def set_attrs(self, attrs):
        if attrs is None:
            return

        if len(attrs) == 0:
            return

        if self.islocked():
            for k, v in attrs.items():
                setattr(self, k, v)
        else:
            with self.locked():
                for k, v in attrs.items():
                    setattr(self, k, v)

    @property
    def locales(self):
        ron = self.ron_instance

        if hasattr(ron, '_locales'):
            return ron._locales

        config_stem = self.config_stem

        if config_stem in ('au', 'au-fire'):
            return 'au',
        elif config_stem in ('eu', 'eu-75', 'eu-fire', 'eu-fire2'):
            return 'eu',
        elif config_stem in ('lt', 'lt-fire-future-snow', 'lt-wepp_347f3bd', 'lt-wepp_bd16b69-snow'):
            return 'us', 'lt',
        elif config_stem in ('portland', 'portland-simfire-eagle-snow', 'portland-simfire-norse-snow',
                             'portland-snow', 'portland-wepp_64bf5aa_snow', 'portland-wepp_347f3bd',
                             'portland-wepp_bd16b69'):
            return 'us', 'portland'
        elif config_stem in ('seattle-simfire-eagle-snow', 'seattle-simfire-norse-snow', 'seattle-snow'):
            return 'us', 'seattle'
        else:
            return 'us',

    @property
    def stub(self):

        js = jsonpickle.encode(self)
        obj = json.loads(js)
        del js

        exclude = getattr(self, '__exclude__', None)

        if exclude is not None:
            for attr in exclude:
                if attr in obj:
                    del obj[attr]
        return obj

    def islocked(self):
        if redis_lock_client is None:
            raise RuntimeError('Redis lock client is unavailable')

        lock_key = self._distributed_lock_key
        payload = redis_lock_client.get(lock_key)
        if payload is not None:
            return True

        # No active distributed lock—normalize legacy flags if needed.
        v = redis_lock_client.hget(self.runid, self._file_lock_key)
        if v is None:
            return False

        if v != 'false':
            redis_lock_client.hset(self.runid, self._file_lock_key, 'false')
        return False

    def lock(self, ttl: Optional[int] = None):
        if self.readonly:
            raise Exception('lock() called on readonly project')

        if redis_lock_client is None:
            raise RuntimeError('Redis lock client is unavailable')

        ttl_seconds = LOCK_DEFAULT_TTL if ttl is None else max(1, int(ttl))
        lock_key = self._distributed_lock_key

        token = uuid.uuid4().hex
        payload = _serialize_lock_payload(token, ttl_seconds)
        acquired = redis_lock_client.set(lock_key, payload, nx=True, ex=ttl_seconds)
        if not acquired:
            existing_payload = redis_lock_client.get(lock_key)
            existing_data = _parse_lock_payload(existing_payload) if existing_payload else {}
            message = 'lock() called on an already locked nodb'
            owner = existing_data.get('owner')
            if owner:
                message += f' (owner={owner})'
            else:
                existing_token = existing_data.get('token')
                if existing_token:
                    message += f' (token={existing_token})'
            raise NoDbAlreadyLockedError(message)

        redis_lock_client.hset(self.runid, self._file_lock_key, 'true')
        _set_local_lock_token(self, token)

    def unlock(self, flag=None):
        if redis_lock_client is None:
            raise RuntimeError('Redis lock client is unavailable')

        lock_key = self._distributed_lock_key
        stored_payload = redis_lock_client.get(lock_key)
        stored_token = _extract_token(stored_payload)
        local_token = _get_local_lock_token(self)

        force = flag in ('-f', '--force')

        if stored_payload is None:
            redis_lock_client.hset(self.runid, self._file_lock_key, 'false')
            _set_local_lock_token(self, None)
            return

        if not force:
            if local_token is None:
                raise RuntimeError('unlock() called without owning the lock; use flag "-f" to force release')
            if stored_token is not None and stored_token != local_token:
                raise RuntimeError('unlock() called with non-matching token; use flag "-f" to force release')

        redis_lock_client.delete(lock_key)
        redis_lock_client.hset(self.runid, self._file_lock_key, 'false')
        _set_local_lock_token(self, None)

    @property
    def run_group(self):  # e.g. batch
        return getattr(self, '_run_group', None)
    
    @run_group.setter
    @nodb_setter
    def run_group(self, value: str):
        self._run_group = value

    @property
    def group_name(self):  # e.g. my_batch_01
        return getattr(self, '_group_name', None)
    
    @group_name.setter
    @nodb_setter
    def group_name(self, value: str):
        self._group_name = value

    @property
    def runid(self):
        group_prefix = ''
        if self.run_group is not None:
            if self.group_name is None:
                raise ValueError('run_group is set but group_name is None')
            group_prefix = f'{self.run_group};;{self.group_name};;'

        wd = self.wd
        split_wd = wd.split(os.sep)
        if '_pups' in split_wd:
            return group_prefix + split_wd[split_wd.index('_pups') -1]
        return group_prefix + split_wd[-1]

    @property
    def multi_ofe(self):
        return getattr(self.wepp_instance, '_multi_ofe', False)

    @property
    def readonly(self):
        return _exists(_join(self.wd, 'READONLY'))

    @readonly.setter
    def readonly(self, value):
        assert value in [False, True]

        path = _join(self.wd, 'READONLY')
        if value:
            with open(path, 'w') as fp:
                fp.write('')

            assert self.readonly

        else:
            if self.readonly:
                os.remove(path)

            assert not self.readonly

    @staticmethod
    def ispublic(wd):
        return _exists(_join(wd, 'PUBLIC'))

    @property
    def public(self):
        return _exists(_join(self.wd, 'PUBLIC'))

    @public.setter
    def public(self, value):
        assert value in [False, True]

        path = _join(self.wd, 'PUBLIC')
        if value:
            with open(path, 'w') as fp:
                fp.write('')

            assert self.public

        else:
            if self.public:
                os.remove(path)

            assert not self.public

    @property
    def DEBUG(self):
        return _exists(_join(self.wd, 'DEBUG'))

    @DEBUG.setter
    def DEBUG(self, value):
        assert value in [False, True]

        path = _join(self.wd, 'DEBUG')
        if value:
            with open(path, 'w') as fp:
                fp.write('')

            assert self.DEBUG

        else:
            if self.readonly:
                os.remove(path)

            assert not self.DEBUG

    @property
    def VERBOSE(self):
        return _exists(_join(self.wd, 'VERBOSE'))

    @VERBOSE.setter
    def VERBOSE(self, value):
        assert value in [False, True]

        path = _join(self.wd, 'VERBOSE')
        if value:
            with open(path, 'w') as fp:
                fp.write('')

            assert self.VERBOSE

        else:
            if self.VERBOSE:
                os.remove(path)

            assert not self.VERBOSE

    @property
    def _configparser(self):
        _config = self._config.split('?')

        cfg = _join(_config_dir, _config[0])

        parser = CaseSensitiveRawConfigParser(allow_no_value=True)
        with open(_default_config) as fp:
            parser.read_file(fp)

        with open(cfg) as fp:
            parser.read_file(fp)

        if len(_config) == 2:
            overrides = _config[1].split('&')
            overrides_d = {}
            for override in overrides:
                key, value = override.split('=')
                section, name = key.split(':')

                if section not in overrides_d:
                    overrides_d[section] = {}
                overrides_d[section][name] = value

            parser.read_dict(overrides_d)

        return parser

    def _load_mods(self):
        config_parser = self._configparser
        mods = self.config_get_raw('nodb', 'mods')

        if mods is not None:
            mods = ast.literal_eval(mods)

        self._mods = mods

    def trigger(self, evt):
        # TODO: refactor to use reflection to get NoDbBase subclasses in wepppy.nodb.mods
        # and call on(evt) if the subclass name is in self.mods
        assert isinstance(evt, TriggerEvents)
        import wepppy.nodb.mods

        from wepppy.nodb.mods.baer import Baer
        from wepppy.nodb.mods.disturbed import Disturbed
        from wepppy.nodb.mods.revegetation import Revegetation
        from wepppy.nodb.mods.rred import Rred
        from wepppy.nodb.mods.shrubland import Shrubland

        if 'lt' in self.mods:
            from wepppy.nodb.mods.locations import LakeTahoe
            lt = LakeTahoe.getInstance(self.wd)
            lt.on(evt)

        if 'portland' in self.mods:
            from wepppy.nodb.mods.locations import PortlandMod
            portland = PortlandMod.getInstance(self.wd)
            portland.on(evt)

        if 'seattle' in self.mods:
            try:
                from wepppy.nodb.mods.locations import SeattleMod
                seattle = SeattleMod.getInstance(self.wd)
                seattle.on(evt)
            except:
                pass
        if 'general' in self.mods:
            from wepppy.nodb.mods.locations import GeneralMod
            general = GeneralMod.getInstance(self.wd)
            general.on(evt)

        if 'baer' in self.mods:
            baer = Baer.getInstance(self.wd)
            baer.on(evt)

        if 'disturbed' in self.mods:
            disturbed = Disturbed.getInstance(self.wd)
            disturbed.on(evt)

        if 'revegetation' in self.mods:
            reveg = Revegetation.getInstance(self.wd)
            reveg.on(evt)

        if 'rred' in self.mods:
            rred = Rred.getInstance(self.wd)
            rred.on(evt)

        if 'shrubland' in self.mods:
            shrubland = Shrubland.getInstance(self.wd)
            shrubland.on(evt)

    @property
    def mods(self):
        return self._mods

    @property
    def dem_dir(self):
        return _join(self.wd, 'dem')

    @property
    def dem_fn(self):
        return _join(self.wd, 'dem', 'dem.tif')

    @property
    def topaz_wd(self):
        return _join(self.wd, 'dem', 'topaz')

    @property
    def taudem_wd(self):
        return _join(self.wd, 'dem', 'taudem')

    @property
    def wbt_wd(self):
        return _join(self.wd, 'dem', 'wbt')

    @property
    def wat_dir(self):
        return _join(self.wd, 'watershed')

    @property
    def wat_js(self):
        return _join(self.wd, 'watershed', 'wat.json')

    @property
    def lc_dir(self):
        return _join(self.wd, 'landuse')

    @property
    def lc_fn(self):
        return _join(self.wd, 'landuse', 'nlcd.tif')

    @property
    def domlc_fn(self):
        return _join(self.wd, 'landuse', 'landcov.asc')

    @property
    def soils_dir(self):
        return _join(self.wd, 'soils')

    @property
    def ssurgo_fn(self):
        return _join(self.wd, 'soils', 'ssurgo.tif')

    @property
    def domsoil_fn(self):
        return _join(self.wd, 'soils', 'soilscov.asc')

    @property
    def cli_dir(self):
        return _join(self.wd, 'climate')

    @property
    def wepp_dir(self):
        return _join(self.wd, 'wepp')

    @property
    def runs_dir(self):
        return _join(self.wd, 'wepp', 'runs')
    
    @property
    def output_dir(self):
        return _join(self.wd, 'wepp', 'output')

    @property
    def wepp_interchange_dir(self):
        return _join(self.wd, 'wepp', 'output', 'interchange')
    
    @property
    def fp_runs_dir(self):
        return _join(self.wd, 'wepp', 'flowpaths', 'runs')

    @property
    def fp_output_dir(self):
        return _join(self.wd, 'wepp', 'flowpaths', 'output')

    @property
    def plot_dir(self):
        return _join(self.wd, 'wepp', 'plots')

    @property
    def stats_dir(self):
        return _join(self.wd, 'wepp', 'stats')

    @property
    def export_dir(self):
        return _join(self.wd, 'export')

    @property
    def export_winwepp_dir(self):
        return _join(self.wd, 'export', 'winwepp')

    @property
    def export_arc_dir(self):
        return _join(self.wd, 'export', 'arcmap')

    @property
    def export_legacy_arc_dir(self):
        return _join(self.wd, 'export', 'legacy_arcmap')

    @property
    def observed_dir(self):
        return _join(self.wd, 'observed')

    @property
    def observed_fn(self):
        return _join(self.observed_dir, 'observed.csv')

    @property
    def ash_dir(self):
        return _join(self.wd, 'ash')

    @property
    def wmesque_version(self) -> int:
        return self.config_get_int('wmesque', 'version', 1)

    @property
    def wmesque_endpoint(self) -> None|str:
        return self.config_get_str('wmesque', 'endpoint', None)


def _iter_nodb_subclasses():
    seen = set()
    stack = [NoDbBase]
    while stack:
        cls = stack.pop()
        for subcls in cls.__subclasses__():
            if subcls not in seen:
                seen.add(subcls)
                stack.append(subcls)
                yield subcls

def iter_nodb_mods_subclasses():
    seen = set()
    stack = [NoDbBase]
    while stack:
        cls = stack.pop()
        for subcls in cls.__subclasses__():
            if subcls not in seen:
                seen.add(subcls)
                stack.append(subcls)
                _module = subcls.__module__
                if 'mods' in _module:
                    yield subcls.filename.removesuffix('.nodb'), subcls


def clear_locks(runid, pup_relpath=None):
    """
    Clear locks for the given runid.
    If ``pup_relpath`` is provided, only locks whose relative paths fall under that
    subtree are cleared.
    Low-level function that interacts directly with Redis.
    """
    if redis_lock_client is None:
        raise RuntimeError('Redis lock client is unavailable')

    cleared: list[str] = []
    seen: set[str] = set()

    def _record(relpath: str):
        field_name = f'locked:{relpath}'
        if field_name not in seen:
            seen.add(field_name)
            cleared.append(field_name)

    scope = None
    if pup_relpath:
        scope = pup_relpath.rstrip(os.sep)
        if scope == '.':
            scope = None

    hashmap = redis_lock_client.hgetall(runid)

    for lock_key, v in hashmap.items():
        if not lock_key.startswith('locked:'):
            continue

        rel_path = lock_key.split('locked:', 1)[1]
        if not _matches_scope(rel_path, scope):
            continue

        if v != 'false':
            redis_lock_client.hset(runid, lock_key, 'false')
        redis_lock_client.delete(_lock_key_for(runid, rel_path))
        _record(rel_path)

    pattern = f'{LOCK_KEY_PREFIX}:{runid}:*'
    for distributed_key in redis_lock_client.scan_iter(match=pattern):
        rel_path = _relpath_from_lock_key(runid, distributed_key)
        if not _matches_scope(rel_path, scope):
            continue
        redis_lock_client.delete(distributed_key)
        field = f'locked:{rel_path}'
        redis_lock_client.hset(runid, field, 'false')
        _record(rel_path)

    return cleared


def lock_statuses(runid) -> defaultdict[str, bool]:
    """
    Return the lock status for each known `.nodb` file under the run.
    Distributed locks (SETNX keys) are considered the source of truth; legacy
    `locked:*` hash fields are normalized as needed for compatibility.
    """
    if redis_lock_client is None:
        raise RuntimeError('Redis lock client is unavailable')

    statuses = defaultdict(bool)

    # distributed locks are authoritative
    active_norm_paths: dict[str, str] = {}
    pattern = f'{LOCK_KEY_PREFIX}:{runid}:*'
    for distributed_key in redis_lock_client.scan_iter(match=pattern):
        rel_path = _relpath_from_lock_key(runid, distributed_key)
        statuses[rel_path] = True
        active_norm_paths[_normalize_lock_relpath(rel_path)] = rel_path

    # legacy hash flags are kept for UI compatibility
    hashmap = redis_lock_client.hgetall(runid)
    for lock_key, v in hashmap.items():
        if lock_key.startswith('locked:'):
            filename = lock_key.split('locked:')[1]
            norm = _normalize_lock_relpath(filename)
            if norm in active_norm_paths:
                # already marked as active from the distributed lock
                continue

            locked = False
            if v == 'true':
                locked = True
            elif v not in (None, 'false'):
                payload = _parse_lock_payload(v)
                if payload.get('expires_at'):
                    try:
                        locked = int(payload['expires_at']) > int(time())
                    except (TypeError, ValueError):
                        locked = bool(payload.get('token'))
                else:
                    locked = bool(payload.get('token'))

            if locked:
                # Mirror authoritative state; if distributed lock is gone, clear stale flag.
                if norm not in active_norm_paths:
                    redis_lock_client.hset(runid, lock_key, 'false')
                    locked = False

            statuses[filename] = locked

    return statuses


def clear_nodb_file_cache(runid, pup_relpath=None) -> list[Path]:
    """Clear Redis cache entries for `.nodb` files under a run (optionally scoped)."""
    if redis_nodb_cache_client is None:
        raise RuntimeError('Redis NoDb cache client is unavailable')

    from wepppy.weppcloud.utils.helpers import get_wd

    wd = Path(get_wd(runid)).resolve()
    if not wd.exists():
        raise FileNotFoundError(f'Working directory not found for runid {runid}: {wd}')

    def _validate_relpath(relpath: str) -> Path:
        candidate = Path(relpath)
        if candidate.is_absolute():
            raise ValueError(f"pup_relpath must be relative to the run root: {relpath}")
        if any(part == '..' for part in candidate.parts):
            raise ValueError(f"pup_relpath cannot traverse outside the run root: {relpath}")
        target = (wd / candidate).resolve()
        if target != wd and wd not in target.parents:
            raise ValueError(f"pup_relpath resolves outside the run root: {relpath}")
        return target

    def _gather_filesystem_nodbs(root: Path) -> set[Path]:
        paths: set[Path] = set()
        if root.is_file() and root.suffix == '.nodb':
            paths.add(root)
            return paths

        if not root.exists():
            return paths

        if root.is_dir():
            for path in root.rglob('*.nodb'):
                paths.add(path)

        return paths

    def _gather_cached_paths(prefix_root: Path) -> set[Path]:
        paths: set[Path] = set()
        prefix = str(prefix_root)
        raw_keys: set[str] = set()

        # include keys that match the directory prefix as well as a direct file
        patterns = [prefix, f"{prefix}{os.sep}*"]
        for pattern in patterns:
            try:
                for key in redis_nodb_cache_client.scan_iter(match=f"{pattern}"):
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    raw_keys.add(key)
            except redis.exceptions.RedisError as exc:
                logging.error(f'Error scanning NoDb cache keys with pattern {pattern}: {exc}')
                return paths

        for key in raw_keys:
            path = Path(key)
            # only keep entries that remain within the run root
            try:
                path.relative_to(wd)
            except ValueError:
                continue
            if path.suffix == '.nodb':
                paths.add(path)

        return paths

    nodb_paths: set[Path] = set()

    if pup_relpath:
        scoped_root = _validate_relpath(pup_relpath)
        nodb_paths.update(_gather_filesystem_nodbs(scoped_root))
        nodb_paths.update(_gather_cached_paths(scoped_root))
    else:
        # Top-level `.nodb` files (e.g., wepp.nodb, soils.nodb)
        nodb_paths.update(wd.glob('*.nodb'))

        # Immediate subdirectories (excluding `_pups`, handled below)
        for child in wd.glob('*/*.nodb'):
            if '_pups' in child.parts:
                continue
            nodb_paths.add(child.resolve())

        # Recursive search within `_pups` hierarchy, tracking relative paths
        pups_dir = wd / '_pups'
        if pups_dir.is_dir():
            nodb_paths.update(path.resolve() for path in pups_dir.rglob('*.nodb'))

        # Also include any cached entries that might remain for deleted nodb files
        nodb_paths.update(_gather_cached_paths(wd))

    cleared = []
    for nodb_path in sorted(nodb_paths):
        cache_key = str(nodb_path)
        try:
            removed = redis_nodb_cache_client.delete(cache_key)
        except redis.exceptions.RedisError as exc:
            logging.error(f'Error clearing NoDb cache for {cache_key}: {exc}')
            continue

        if removed:
            try:
                cleared.append(nodb_path.relative_to(wd))
            except ValueError:
                cleared.append(nodb_path)

    return cleared
