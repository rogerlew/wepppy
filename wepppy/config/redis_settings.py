"""
Centralized Redis configuration helpers.

The helpers in this module shim over the various environment variables we have
used historically (`REDIS_HOST`, `REDIS_PORT`, `REDIS_URL`, etc.) so that every
component resolves the same effective host, port, and database numbers.  This
is especially important in containerized deployments where the Redis hostname
is provided by Docker (`redis`, `cache`, ...), not `localhost`.
"""

from __future__ import annotations

import os
from enum import IntEnum
from functools import lru_cache
from typing import Any, Dict, Iterable, Mapping, Optional, Union
from urllib.parse import ParseResult, quote, urlparse, urlunparse

from wepppy.config.secrets import get_secret

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover - redis is optional for typing
    redis = None  # type: ignore


class RedisDB(IntEnum):
    """Semantic names for Redis logical databases used across the project."""

    LOCK = 0
    STATUS = 2
    RQ = 9
    WD_CACHE = 11
    SESSION = 11  # alias; Flask session storage shares WD cache
    NODB_CACHE = 13
    README = 14
    LOG_LEVEL = 15


def _parse_url(raw_url: str) -> Optional[ParseResult]:
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.hostname:
        return None
    return parsed


def _redis_password() -> Optional[str]:
    password = get_secret("REDIS_PASSWORD")
    if password:
        return password
    return None


def _format_netloc(parsed: ParseResult) -> str:
    hostname = parsed.hostname
    if not hostname:
        return ""
    host = hostname
    if ":" in hostname and not hostname.startswith("["):
        host = f"[{hostname}]"
    if parsed.port:
        return f"{host}:{parsed.port}"
    return host


def _apply_password(parsed: ParseResult, password: Optional[str]) -> ParseResult:
    if not password or parsed.password:
        return parsed
    netloc = _format_netloc(parsed)
    if not netloc:
        return parsed
    username = parsed.username or ""
    password_enc = quote(password, safe="")
    if username:
        username_enc = quote(username, safe="")
        auth = f"{username_enc}:{password_enc}"
    else:
        auth = f":{password_enc}"
    return parsed._replace(netloc=f"{auth}@{netloc}")


def _auth_from_parsed(parsed: Optional[ParseResult]) -> tuple[Optional[str], Optional[str]]:
    if parsed is None:
        return None, None
    username = parsed.username or None
    password = parsed.password
    if password:
        return username, password
    return username, None


@lru_cache(maxsize=1)
def _base_url() -> Optional[ParseResult]:
    """
    Cache the parsed base Redis URL, if provided.

    When `REDIS_URL` (or legacy `RQ_REDIS_URL`) is defined we preserve the
    scheme, credentials, host, port, and query parameters while swapping the
    database index as needed.
    """

    raw_url = (
        os.getenv("REDIS_URL")
        or os.getenv("RQ_REDIS_URL")
        or os.getenv("SESSION_REDIS_URL")
    )
    if not raw_url:
        return None

    parsed = _parse_url(raw_url)
    if parsed is None:
        return None
    return _apply_password(parsed, _redis_password())


@lru_cache(maxsize=1)
def _session_base_url() -> Optional[ParseResult]:
    raw_url = (
        os.getenv("SESSION_REDIS_URL")
        or os.getenv("REDIS_URL")
        or os.getenv("RQ_REDIS_URL")
    )
    if not raw_url:
        return None
    parsed = _parse_url(raw_url)
    if parsed is None:
        return None
    return _apply_password(parsed, _redis_password())


@lru_cache(maxsize=1)
def redis_host() -> str:
    """Resolve the Redis hostname, preferring URL-based configuration."""

    parsed = _base_url()
    if parsed and parsed.hostname:
        return parsed.hostname

    return os.getenv("REDIS_HOST", "localhost")


@lru_cache(maxsize=1)
def redis_port() -> int:
    """Resolve the Redis port, respecting URL overrides."""

    parsed = _base_url()
    if parsed and parsed.port:
        return parsed.port

    return int(os.getenv("REDIS_PORT", "6379"))


def _apply_db(parsed: ParseResult, db: int) -> str:
    """Return a new URL string with the supplied database index."""

    path = f"/{int(db)}"
    return urlunparse(parsed._replace(path=path))


@lru_cache(maxsize=None)
def redis_url(db: Union[int, RedisDB]) -> str:
    """
    Build a connection URL for the specified logical database.

    If `REDIS_URL` was provided we reuse its scheme, credentials, and port while
    updating only the database number in the path segment.  Otherwise we fall
    back to `redis://<host>:<port>/<db>`.
    """

    parsed = _base_url()
    if parsed is not None:
        return _apply_db(parsed, int(db))

    password = _redis_password()
    if password:
        password_enc = quote(password, safe="")
        return f"redis://:{password_enc}@{redis_host()}:{redis_port()}/{int(db)}"
    return f"redis://{redis_host()}:{redis_port()}/{int(db)}"


def redis_connection_kwargs(
    db: Union[int, RedisDB],
    *,
    decode_responses: Optional[bool] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Produce a kwargs dict for redis.Redis / StrictRedis constructors.

    This mirrors the parameters we usually pass (`host`, `port`, `db`, and
    optionally `decode_responses`) while allowing callers to provide extra
    keyword arguments through `extra`.
    """

    username, password = _auth_from_parsed(_base_url())
    if not password:
        password = _redis_password()
    kwargs: Dict[str, Any] = {
        "host": redis_host(),
        "port": redis_port(),
        "db": int(db),
    }

    if password:
        kwargs["password"] = password
        if username:
            kwargs["username"] = username

    if decode_responses is not None:
        kwargs["decode_responses"] = decode_responses

    if extra:
        kwargs.update(extra)

    return kwargs


def _session_db(default: Union[int, RedisDB]) -> int:
    raw = os.getenv("SESSION_REDIS_DB")
    if raw is not None:
        return int(raw)
    return int(default)


@lru_cache(maxsize=1)
def session_redis_url(db_default: Union[int, RedisDB] = RedisDB.SESSION) -> str:
    """
    Build a Redis URL for Flask session storage.

    - Prefer SESSION_REDIS_URL when provided.
    - Respect SESSION_REDIS_DB overrides.
    - Fall back to REDIS_URL/RQ_REDIS_URL host settings with the session DB.
    """

    session_url = os.getenv("SESSION_REDIS_URL")
    session_db_raw = os.getenv("SESSION_REDIS_DB")
    db = _session_db(db_default)

    if session_url:
        parsed = _session_base_url()
        if parsed is not None:
            if session_db_raw is None and parsed.path and parsed.path != "/":
                return urlunparse(parsed)
            return _apply_db(parsed, db)

    parsed = _session_base_url()
    if parsed is not None:
        return _apply_db(parsed, db)

    return f"redis://{redis_host()}:{redis_port()}/{db}"


def redis_client(
    db: Union[int, RedisDB],
    *,
    decode_responses: Optional[bool] = None,
    client_cls: Optional[Any] = None,
    extra_kwargs: Optional[Mapping[str, Any]] = None,
):
    """
    Instantiate a Redis client using the centralized configuration.

    Parameters
    ----------
    db:
        Logical Redis database number or `RedisDB` enum member.
    decode_responses:
        Defaults to whichever choice the caller needs; we pass it through for
        convenience.
    client_cls:
        Allows callers to override the constructor (e.g. `redis.StrictRedis`).
        If omitted we use `redis.Redis`.
    extra_kwargs:
        Optional mapping merged into the constructor kwargs.
    """

    if redis is None:
        raise RuntimeError("redis package is required to build a Redis client")

    cls = client_cls or redis.Redis
    kwargs = redis_connection_kwargs(
        db,
        decode_responses=decode_responses,
        extra=extra_kwargs,
    )
    return cls(**kwargs)


def redis_async_url(db: Union[int, RedisDB]) -> str:
    """
    Convenience helper for async services that prefer URL-style connection
    strings.  We expose it separately so we do not have to import redis.asyncio
    in synchronous processes.
    """

    return redis_url(db)
