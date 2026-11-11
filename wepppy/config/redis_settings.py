"""Redis endpoints and separately resolved credentials.

See docs/schemas/redis-credential-transport-contract.md. URL helpers are for
nonsecret endpoint display; construct authenticated clients with native kwargs.
"""
from __future__ import annotations

import os
from enum import IntEnum
from pathlib import Path
from functools import lru_cache
from typing import Any, Mapping, Optional, Union
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse

from wepppy.config.secrets import SecretConfigurationError, get_secret

try:
    import redis
except ImportError:  # redis is optional until a client is requested
    redis = None


class RedisDB(IntEnum):
    LOCK = 0
    STATUS = 2
    RQ = 9
    WD_CACHE = 11
    SESSION = 11
    NODB_CACHE = 13
    README = 14
    LOG_LEVEL = 15


class _Password(str):
    """Native Redis str input whose diagnostic forms never expose its bytes."""

    def __repr__(self):
        return '<redacted>'

    __str__ = __repr__

    def __format__(self, spec):
        return format("<redacted>", spec)


class ConnectionKwargs(dict):
    """Native constructor arguments with a nonsecret diagnostic representation."""

    def __repr__(self):
        return repr({k: ('<redacted>' if k in {'password', 'username'} else v)
                     for k, v in self.items()})

    __str__ = __repr__


def _validate_query(parsed):
    from redis.connection import parse_url, URL_QUERY_ARGUMENT_PARSERS
    allowed = set(URL_QUERY_ARGUMENT_PARSERS) | {
        'ssl_ca_certs', 'ssl_ca_data', 'ssl_cert_reqs', 'ssl_keyfile', 'ssl_certfile',
        'ssl_min_version', 'ssl_ciphers', 'encoding',
        'encoding_errors', 'client_name', 'lib_name', 'lib_version', 'decode_responses',
    }
    if any(k not in allowed for k, _ in parse_qsl(parsed.query)):
        raise ValueError('Invalid Redis connection options')
    # Native parser validates typed values; never surface parser input/errors.
    parse_url(urlunparse(parsed._replace(netloc='localhost', path='/0')))


def _raw_url(session=False):
    names = ('SESSION_REDIS_URL', 'REDIS_URL', 'RQ_REDIS_URL') if session else (
        'REDIS_URL', 'RQ_REDIS_URL', 'SESSION_REDIS_URL')
    return next((os.environ[n] for n in names if os.getenv(n)), None)


def _resolve(session=False, raw_url=None):
    """Parse userinfo only at ingestion; never cache the secret-bearing URL."""
    raw = raw_url if raw_url is not None else _raw_url(session)
    try:
        password = get_secret('REDIS_PASSWORD')
        if os.getenv('REDIS_PASSWORD_FILE', '').strip():
            framed = Path(os.environ['REDIS_PASSWORD_FILE'].strip()).read_bytes().decode('utf-8').rstrip('\n')
            if framed != password:
                raise ValueError('Invalid Redis password file framing')
    except (SecretConfigurationError, OSError, UnicodeError):
        raise ValueError('Redis password file is unavailable or empty') from None
    username = None
    try:
        if raw:
            parsed = urlparse(raw)
            if parsed.scheme not in ('redis', 'rediss', 'unix'):
                raise ValueError()
            if parsed.scheme != 'unix' and not parsed.hostname:
                raise ValueError()
            if parsed.scheme == 'unix' and not parsed.path:
                raise ValueError()
            if parsed.port is not None and not 1 <= parsed.port <= 65535:
                raise ValueError()
            username = unquote(parsed.username) if parsed.username else None
            legacy = unquote(parsed.password) if parsed.password is not None else None
            if password is not None and legacy is not None and password != legacy:
                raise ValueError()
            password = password if password is not None else legacy
            query = parse_qsl(parsed.query, keep_blank_values=True)
            _validate_query(parsed)
            if any(k in {'username', 'password', 'credential_provider', 'host', 'port',
                         'path', 'connection_class'} for k, _ in query):
                raise ValueError()
            if parsed.scheme != 'unix' and parsed.path not in ('', '/'):
                _db(parsed.path.lstrip('/'))
            for key, value in query:
                if key == 'db':
                    _db(value)
            if parsed.fragment:
                raise ValueError()
            host = parsed.hostname or ''
            if ':' in host:
                host = f'[{host}]'
            netloc = host + (f':{parsed.port}' if parsed.port else '')
            parsed = parsed._replace(netloc=netloc)
        else:
            host = os.getenv('REDIS_HOST', 'localhost')
            if not host or any(c in host for c in '/?#@\\') or any(c.isspace() for c in host):
                raise ValueError()
            if ':' in host and not host.startswith('['):
                host = f'[{host}]'
            port = int(os.getenv('REDIS_PORT', '6379'))
            if not 1 <= port <= 65535:
                raise ValueError()
            parsed = urlparse(f'redis://{host}:{port}/0')
        if password is not None and (not password or '\x00' in password or '\r' in password or '\n' in password):
            raise ValueError()
    except (ValueError, UnicodeError):
        raise ValueError('Invalid or conflicting Redis configuration') from None
    return parsed, username, password


@lru_cache(maxsize=1)
def _base_url():
    return _resolve()[0]


@lru_cache(maxsize=1)
def _session_base_url():
    return _resolve(True)[0]


@lru_cache(maxsize=1)
def redis_host() -> str:
    return _base_url().hostname or 'localhost'


@lru_cache(maxsize=1)
def redis_port() -> int:
    port = _base_url().port
    return port if port is not None else _environment_port()


def _environment_port() -> int:
    try:
        value = int(os.getenv('REDIS_PORT', '6379'))
        if not 1 <= value <= 65535:
            raise ValueError()
        return value
    except ValueError:
        raise ValueError('Invalid Redis port') from None


def _db(value):
    try:
        result = int(value)
        if result < 0:
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise ValueError('Invalid Redis database') from None


def _apply_db(parsed, db):
    db = _db(db)
    query = [(k, v) for k, v in parse_qsl(parsed.query) if k != 'db']
    if parsed.scheme == 'unix':
        query.append(('db', str(db)))
        path = parsed.path
    else:
        path = f'/{db}'
    if parsed.scheme == 'unix':
        return 'unix://' + path + '?' + urlencode(query)
    return urlunparse(parsed._replace(path=path, query=urlencode(query)))


@lru_cache(maxsize=None)
def redis_url(db: Union[int, RedisDB]):
    """Return a credential-free endpoint; not an authenticated connection URL."""
    return _apply_db(_base_url(), db)


def _session_db(default):
    if os.getenv('SESSION_REDIS_DB') is not None:
        return _db(os.environ['SESSION_REDIS_DB'])
    if os.getenv('SESSION_REDIS_URL'):
        parsed = _session_base_url()
        query = dict(parse_qsl(parsed.query))
        if 'db' in query:
            return _db(query['db'])
        if parsed.scheme != 'unix' and parsed.path not in ('', '/'):
            return _db(parsed.path.lstrip('/'))
    return _db(default)


@lru_cache(maxsize=1)
def session_redis_url(db_default=RedisDB.SESSION):
    return _apply_db(_session_base_url(), _session_db(db_default))


def redis_connection_kwargs(
    db: Union[int, RedisDB], *, decode_responses: Optional[bool] = None,
    extra: Optional[Mapping[str, Any]] = None, for_pool: bool = False,
    asynchronous: bool = False, session: bool = False,
    endpoint_url: Optional[str] = None,
) -> ConnectionKwargs:
    """Native Redis constructor kwargs; set for_pool for ConnectionPool callers."""
    if redis is None:
        raise RuntimeError('redis package is required to build a Redis client')
    from redis.connection import parse_url, URL_QUERY_ARGUMENT_PARSERS
    parsed, username, password = _resolve(session, endpoint_url)
    try:
        kwargs = ConnectionKwargs(parse_url(_apply_db(parsed, db)))
    except (ValueError, TypeError):
        raise ValueError('Invalid Redis connection options') from None
    # Native parser yields pool kwargs. Redis constructors use ssl/unix_socket_path.
    kwargs.pop('connection_class', None)
    if parsed.scheme == 'unix':
        if for_pool:
            from redis import asyncio as aioredis
            kwargs['connection_class'] = (aioredis.UnixDomainSocketConnection if asynchronous
                                          else redis.UnixDomainSocketConnection)
        else:
            kwargs['unix_socket_path'] = kwargs.pop('path')
    else:
        kwargs.setdefault('host', 'localhost')
        if 'port' not in kwargs:
            kwargs['port'] = 6379 if session else _environment_port()
        if not 1 <= kwargs['port'] <= 65535:
            raise ValueError('Invalid Redis port')
        if parsed.scheme == 'rediss':
            if for_pool:
                from redis import asyncio as aioredis
                kwargs['connection_class'] = aioredis.SSLConnection if asynchronous else redis.SSLConnection
            else:
                kwargs['ssl'] = True
    if username is not None:
        kwargs['username'] = username
    if password is not None:
        kwargs['password'] = _Password(password)
    if decode_responses is not None:
        kwargs['decode_responses'] = decode_responses
    if extra:
        kwargs.update(extra)
    return kwargs


def session_redis_connection_kwargs(db_default=RedisDB.SESSION):
    return redis_connection_kwargs(_session_db(db_default), session=True)


def redis_client(db, *, decode_responses=None, client_cls=None, extra_kwargs=None):
    kwargs = redis_connection_kwargs(db, decode_responses=decode_responses, extra=extra_kwargs)
    return (client_cls or redis.Redis)(**kwargs)


def redis_async_client(db, *, decode_responses=None, extra_kwargs=None):
    from redis import asyncio as aioredis
    return aioredis.Redis(**redis_connection_kwargs(
        db, decode_responses=decode_responses, extra=extra_kwargs, asynchronous=True))


def redis_endpoint_url(raw_url, db):
    """Normalize a legacy input endpoint without returning credentials."""
    return _apply_db(_resolve(raw_url=raw_url)[0], db)


def redis_async_url(db):
    """Compatibility endpoint helper; use redis_async_client for authentication."""
    return redis_url(db)
