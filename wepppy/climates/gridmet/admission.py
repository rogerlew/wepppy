"""Opt-in, process-local clients for the shared GridMET Redis admission pool.

The durable contract is docs/schemas/gridmet-redis-admission-contract.md.
Redis leases coordinate cooperative clients; they do not fence upstream sockets.
"""
from __future__ import annotations

import json
import logging
import math
import os
import random
import re
import secrets
import threading
import time
from dataclasses import dataclass, replace

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from .acquisition import GridMetAcquisitionError

__all__ = [
    "GridMetAdmissionConfig", "GridMetAdmissionSnapshot", "GridMetAdmissionController",
    "GridMetPermit", "GridMetAdmissionError", "GridMetAdmissionConfigError",
    "GridMetAdmissionConflict", "GridMetAdmissionTimeout", "GridMetAdmissionUnavailable",
    "GridMetAdmissionLostLease",
]

_LOG = logging.getLogger(__name__)
_SOCKET_TIMEOUT = 2.0
DEFAULT_KEY = "wepppy:gridmet:admission:v1"
_KEY_PATTERN = re.compile(r"[A-Za-z0-9:_.-]{1,160}", re.ASCII)


class GridMetAdmissionError(GridMetAcquisitionError):
    """Admission failed; callers must not retry this as an upstream failure."""


class GridMetAdmissionConfigError(GridMetAdmissionError):
    """Admission configuration is invalid."""


class GridMetAdmissionConflict(GridMetAdmissionConfigError):
    """A live namespace is using a different admission policy."""


class GridMetAdmissionTimeout(GridMetAdmissionError):
    """The overall monotonic admission deadline has elapsed."""


class GridMetAdmissionUnavailable(GridMetAdmissionError):
    """Redis did not provide a trustworthy admission result."""


class GridMetAdmissionLostLease(GridMetAdmissionError):
    """The caller no longer owns live admission state."""


@dataclass(frozen=True)
class GridMetAdmissionConfig:
    enabled: bool = True
    key: str = DEFAULT_KEY
    limit: int = 4
    wait_timeout_seconds: float = 900.0
    lease_seconds: float = 300.0
    queue_ttl_seconds: float = 60.0
    poll_interval_seconds: float = 0.25

    def __post_init__(self) -> None:
        if self.enabled is not True:
            raise GridMetAdmissionConfigError("Pass None to disable GridMET admission")
        if not isinstance(self.key, str) or not _KEY_PATTERN.fullmatch(self.key):
            raise GridMetAdmissionConfigError("Admission key must be a 1–160 character ASCII identifier")
        if isinstance(self.limit, bool) or not isinstance(self.limit, int) or self.limit <= 0 or self.limit > 2**53 - 1:
            raise GridMetAdmissionConfigError("Admission limit must be a positive exact Redis integer")
        for name in ("wait_timeout_seconds", "lease_seconds", "queue_ttl_seconds", "poll_interval_seconds"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0 or value > threading.TIMEOUT_MAX or not math.isfinite(value):
                raise GridMetAdmissionConfigError(f"Admission {name} must be a finite positive number within platform timeout bounds")
        if 2 * max(self.lease_seconds, self.queue_ttl_seconds) * 1000 + 1000 > 2**53 - 1:
            raise GridMetAdmissionConfigError("Admission retention exceeds exact Redis millisecond bounds")
        if self.lease_seconds <= 3 * (self.renewal_interval_seconds + _SOCKET_TIMEOUT):
            raise GridMetAdmissionConfigError("Admission lease is too short for bounded renewal")
        if self.queue_ttl_seconds <= 3 * (1.5 * self.poll_interval_seconds + _SOCKET_TIMEOUT):
            raise GridMetAdmissionConfigError("Admission queue TTL is too short for bounded polling")

    @property
    def renewal_interval_seconds(self) -> float:
        return min(self.lease_seconds / 3, 5.0)

    def validate_http_timeout(self, timeout: tuple[float, float]) -> None:
        if self.lease_seconds <= max(timeout) + self.renewal_interval_seconds + _SOCKET_TIMEOUT:
            raise GridMetAdmissionConfigError("Admission lease is too short for the GridMET HTTP timeout")

    @property
    def fingerprint(self) -> str:
        return json.dumps([
            1, self.limit, float(self.lease_seconds), float(self.queue_ttl_seconds),
            float(self.wait_timeout_seconds), float(self.poll_interval_seconds),
        ], separators=(",", ":"))

    @classmethod
    def from_env(cls) -> GridMetAdmissionConfig | None:
        raw = os.environ.get("GRIDMET_REDIS_ADMISSION_ENABLED")
        if raw is None or raw.strip().lower() in {"false", "0", "no", "off"}:
            return None
        if raw.strip().lower() not in {"true", "1", "yes", "on"}:
            raise GridMetAdmissionConfigError("GRIDMET_REDIS_ADMISSION_ENABLED must be a recognized boolean")
        prefix = "GRIDMET_REDIS_ADMISSION_"
        defaults = cls()
        values = {"key": os.environ.get(prefix + "KEY", defaults.key)}
        for name in ("limit", "wait_timeout_seconds", "lease_seconds", "queue_ttl_seconds", "poll_interval_seconds"):
            try:
                parser = int if name == "limit" else float
                values[name] = parser(os.environ.get(prefix + name.upper(), str(getattr(defaults, name))))
            except (ValueError, OverflowError):
                raise GridMetAdmissionConfigError(f"Invalid {prefix}{name.upper()}") from None
        return cls(**values)


@dataclass(frozen=True)
class GridMetAdmissionSnapshot:
    state: str
    position: int | None
    queued: int
    active: int
    limit: int
    waited_seconds: float
    server_time_seconds: float = 0.0
    fingerprint: str = ""
    sequence: int | None = None


# All keys share one hash tag. Policy checks precede mutation of any live state.
# Sequence INCR is an atomic FIFO ordinal, never an occupancy counter.
_SCRIPT = r'''
local meta, seq, queue, live, active, owners = unpack(KEYS)
local op, id, token, policy = ARGV[1], ARGV[2], ARGV[3], ARGV[4]
local limit, lease, ttl, retention = tonumber(ARGV[5]), tonumber(ARGV[6]), tonumber(ARGV[7]), tonumber(ARGV[8])
local clock = redis.call('TIME')
local now = tonumber(clock[1]) * 1000 + tonumber(clock[2]) / 1000
-- Validate every structural invariant before pruning: Redis does not roll back
-- writes made by a script that subsequently encounters malformed state.
for index, expected in ipairs({'hash', 'string', 'zset', 'zset', 'zset', 'hash'}) do
    local actual = redis.call('TYPE', KEYS[index]).ok
    if actual ~= 'none' and actual ~= expected then
        return redis.error_reply('CORRUPT admission key type')
    end
end
local oldpolicy = redis.call('HGET', meta, 'policy')
local oldlimit = tonumber(redis.call('HGET', meta, 'limit'))
local rawsequence = redis.call('GET', seq)
local sequence = tonumber(rawsequence)
local qcount, acount = redis.call('ZCARD', queue), redis.call('ZCARD', active)
if redis.call('EXISTS', meta) == 1 and (not oldpolicy or not oldlimit or oldlimit < 1 or oldlimit > 9007199254740991 or oldlimit ~= math.floor(oldlimit)) then
    return redis.error_reply('CORRUPT admission metadata')
end
if (redis.call('EXISTS', seq) == 1 or qcount + acount > 0) and
   (not rawsequence or not string.match(rawsequence, '^[1-9][0-9]*$') or not sequence or sequence < 1 or sequence > 9007199254740991 or sequence ~= math.floor(sequence)) then
    return redis.error_reply('CORRUPT admission sequence')
end
if op == 'enqueue' and sequence and sequence >= 9007199254740991 then
    return redis.error_reply('Admission sequence exhausted')
end
if qcount ~= redis.call('ZCARD', live) or redis.call('HLEN', owners) ~= qcount + acount then
    return redis.error_reply('CORRUPT admission ownership counts')
end
for _, expirykey in ipairs({live, active}) do
    local entries = redis.call('ZRANGE', expirykey, 0, -1, 'WITHSCORES')
    for index = 2, #entries, 2 do
        local expiry = tonumber(entries[index])
        if not expiry or expiry <= 0 or expiry > 9007199254740991 then
            return redis.error_reply('CORRUPT admission expiry')
        end
    end
end
local previous_rank = 0
local queued = redis.call('ZRANGE', queue, 0, -1, 'WITHSCORES')
for index = 1, #queued, 2 do
    local member, rank = queued[index], tonumber(queued[index + 1])
    if not redis.call('ZSCORE', live, member) or not redis.call('HGET', owners, member) or
       redis.call('ZSCORE', active, member) or rank <= previous_rank or rank > sequence or rank ~= math.floor(rank) then
        return redis.error_reply('CORRUPT admission queue membership')
    end
    previous_rank = rank
end
for _, member in ipairs(redis.call('ZRANGE', active, 0, -1)) do
    if not redis.call('HGET', owners, member) or redis.call('ZSCORE', live, member) then
        return redis.error_reply('CORRUPT admission active membership')
    end
end
local livecount = redis.call('ZCOUNT', live, '(' .. now, '+inf') + redis.call('ZCOUNT', active, '(' .. now, '+inf')
if livecount > 0 and (not oldpolicy or not oldlimit or oldlimit < 1) then
    return redis.error_reply('CORRUPT admission metadata')
end
if op ~= 'snapshot' and livecount > 0 and oldpolicy ~= policy then
    return {'conflict', 'unknown', -1, 0, 0, oldlimit, tostring(now), oldpolicy, -1}
end
local wasexpired = false
for _, key in ipairs({live, active}) do
    for _, stale in ipairs(redis.call('ZRANGEBYSCORE', key, '-inf', now)) do
        if stale == id then wasexpired = true end
        redis.call('ZREM', key, stale)
        redis.call('ZREM', queue, stale)
        redis.call('HDEL', owners, stale)
    end
end
if redis.call('ZCARD', queue) ~= redis.call('ZCARD', live) or
   redis.call('HLEN', owners) ~= redis.call('ZCARD', queue) + redis.call('ZCARD', active) then
    return redis.error_reply('CORRUPT admission ownership')
end
if op ~= 'snapshot' then
    if livecount == 0 then
        redis.call('HSET', meta, 'policy', policy, 'limit', limit)
        oldpolicy, oldlimit = policy, limit
    end
end
local code = 'ok'
local ordinal = redis.call('ZSCORE', queue, id)
local owner = redis.call('HGET', owners, id)
if op == 'enqueue' then
    if owner then
        code = 'ownership'
    else
        ordinal = redis.call('INCR', seq)
        redis.call('ZADD', queue, ordinal, id)
        redis.call('ZADD', live, now + ttl, id)
        redis.call('HSET', owners, id, token)
        owner = token
    end
elseif op == 'poll' then
    if not owner then code = 'ok'
    elseif owner ~= token then code = 'ownership'
    elseif redis.call('ZSCORE', live, id) then redis.call('ZADD', live, now + ttl, id)
    else code = 'ownership' end
elseif op == 'renew' then
    if owner ~= token or not redis.call('ZSCORE', active, id) then code = 'ownership'
    else redis.call('ZADD', active, now + lease, id) end
elseif op == 'release' or op == 'cancel' then
    if owner and owner ~= token then code = 'ownership'
    elseif owner then
        redis.call('ZREM', queue, id)
        redis.call('ZREM', live, id)
        redis.call('ZREM', active, id)
        redis.call('HDEL', owners, id)
    end
elseif op ~= 'snapshot' then
    return redis.error_reply('Unknown admission operation')
end
if code == 'ok' and (op == 'enqueue' or op == 'poll') then
    local head = redis.call('ZRANGE', queue, 0, 0)[1]
    if head == id and redis.call('ZCARD', active) < limit then
        if not redis.call('ZSCORE', live, id) or redis.call('HGET', owners, id) ~= token then
            return redis.error_reply('CORRUPT admission head')
        end
        redis.call('ZREM', queue, id)
        redis.call('ZREM', live, id)
        redis.call('ZADD', active, now + lease, id)
    end
end
if op ~= 'snapshot' then
    for _, key in ipairs(KEYS) do redis.call('PEXPIRE', key, retention) end
end
local state = wasexpired and 'expired' or 'absent'
local position = redis.call('ZRANK', queue, id)
if position then state = 'queued'
elseif redis.call('ZSCORE', active, id) then state = 'active' end
return {code, state, position or -1, redis.call('ZCARD', queue), redis.call('ZCARD', active),
        oldlimit or limit, tostring(now), oldpolicy or '', ordinal or -1}
'''


class GridMetAdmissionController:
    """A lazy Redis client owned by one process; pass config across processes."""

    def __init__(self, config: GridMetAdmissionConfig):
        self.config = config
        self._redis = None
        self._pid = None
        self._wait_started = {}
        self._keys = tuple(f"{{{config.key}}}:v1:{suffix}" for suffix in ("meta", "sequence", "queue", "liveness", "active", "owners"))

    def _connection(self):
        import redis
        from redis.backoff import NoBackoff
        from redis.retry import Retry

        if self._redis is None or self._pid != os.getpid():
            self._redis = redis.Redis(**redis_connection_kwargs(
                RedisDB.LOCK, decode_responses=True,
                extra={"socket_connect_timeout": _SOCKET_TIMEOUT, "socket_timeout": _SOCKET_TIMEOUT,
                       "retry": Retry(NoBackoff(), 0), "retry_on_timeout": False},
            ))
            self._pid = os.getpid()
        return self._redis

    def _transition(self, operation: str, ticket_id: str = "", token: str = "", *, waited: float | None = None):
        import redis

        started = time.monotonic()
        config = self.config
        if waited is None:
            timing = self._wait_started.get(ticket_id)
            waited = 0.0 if timing is None else max(0.0, (started if timing[1] is None else timing[1]) - timing[0])
        try:
            result = self._connection().eval(
                _SCRIPT, len(self._keys), *self._keys, operation, ticket_id, token,
                config.fingerprint, config.limit, config.lease_seconds * 1000,
                config.queue_ttl_seconds * 1000,
                math.ceil(2 * max(config.lease_seconds, config.queue_ttl_seconds) * 1000 + 1000),
            )
        except (redis.exceptions.RedisError, OSError, ValueError) as exc:
            raise GridMetAdmissionUnavailable(
                f"GridMET admission {operation} unavailable ({type(exc).__name__})"
            ) from None
        try:
            code, state, position, queued, active, limit, server_time, fingerprint, sequence = result
            snapshot = GridMetAdmissionSnapshot(
                str(state), None if int(position) < 0 else int(position), int(queued), int(active),
                int(limit), waited, float(server_time) / 1000, str(fingerprint),
                None if int(sequence) < 0 else int(sequence),
            )
        except (TypeError, ValueError, OverflowError):
            raise GridMetAdmissionUnavailable("GridMET admission returned invalid state") from None
        if code == "conflict":
            raise GridMetAdmissionConflict("GridMET admission namespace has a conflicting live policy")
        if code == "ownership":
            raise GridMetAdmissionLostLease(f"GridMET admission {operation} rejected ownership")
        if code != "ok":
            raise GridMetAdmissionUnavailable("GridMET admission returned an unknown status")
        if operation in {"release", "cancel"}:
            self._wait_started.pop(ticket_id, None)
        return snapshot, started

    def snapshot(self, ticket_or_permit_id: str = "") -> GridMetAdmissionSnapshot:
        return self._transition("snapshot", ticket_or_permit_id)[0]

    def acquire(self, *, request_kind: str, deadline: float | None = None) -> GridMetPermit:
        if not re.fullmatch(r"[A-Za-z0-9 _.()-]{1,80}", request_kind):
            raise GridMetAdmissionConfigError("Admission request kind must be a bounded operation label")
        started = time.monotonic()
        deadline = started + self.config.wait_timeout_seconds if deadline is None else deadline
        if not math.isfinite(deadline):
            raise GridMetAdmissionConfigError("Admission deadline must be finite")
        ticket_id, token = secrets.token_hex(16), secrets.token_hex(32)
        self._wait_started[ticket_id] = (started, None)
        snapshot = None
        operation = "enqueue"
        acquired = False
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    context = "" if snapshot is None else f" (queued={snapshot.queued}, active={snapshot.active}, limit={snapshot.limit})"
                    raise GridMetAdmissionTimeout(f"GridMET {request_kind} admission deadline exhausted{context}")
                snapshot, command_started = self._transition(operation, ticket_id, token, waited=time.monotonic() - started)
                if time.monotonic() >= deadline:
                    raise GridMetAdmissionTimeout(f"GridMET {request_kind} admission deadline exhausted")
                if snapshot.state == "active":
                    ended = time.monotonic()
                    self._wait_started[ticket_id] = (started, ended)
                    snapshot = replace(snapshot, waited_seconds=ended - started)
                    permit = GridMetPermit(self, ticket_id, token, command_started + self.config.lease_seconds, snapshot)
                    permit.check()
                    permit._start_renewal()
                    acquired = True
                    return permit
                if snapshot.state in {"absent", "expired"}:
                    self._wait_started.pop(ticket_id, None)
                    ticket_id, token = secrets.token_hex(16), secrets.token_hex(32)
                    self._wait_started[ticket_id] = (started, None)
                    operation = "enqueue"
                else:
                    operation = "poll"
                pause = min(deadline - time.monotonic(), self.config.poll_interval_seconds * random.uniform(0.5, 1.5))
                if pause > 0:
                    time.sleep(pause)
        finally:
            # Also reclaim owned tickets during cancellation without replacing its error.
            if not acquired:
                try:
                    self._transition("cancel", ticket_id, token)
                except GridMetAdmissionError as cleanup_error:
                    _LOG.warning("GridMET admission acquire cleanup failed (%s)", type(cleanup_error).__name__)
                self._wait_started.pop(ticket_id, None)


class GridMetPermit:
    """An ownership token with background renewal and conservative local expiry."""

    def __init__(self, controller, ticket_id, token, valid_until, snapshot):
        self.controller = controller
        self.ticket_id = ticket_id
        self._token = token
        self._valid_until = valid_until
        self.snapshot = snapshot
        self._failure = None
        self._closed = False
        self._stop = threading.Event()
        self._guard = threading.Lock()
        self._thread = None

    def _start_renewal(self):
        self._thread = threading.Thread(target=self._renew_loop, name="gridmet-admission-renew", daemon=True)
        self._thread.start()

    def _renew_loop(self):
        while not self._stop.wait(self.controller.config.renewal_interval_seconds):
            try:
                self.renew()
            except GridMetAdmissionError as exc:
                with self._guard:
                    self._failure = exc
                self._stop.set()
                return

    def check(self) -> None:
        with self._guard:
            if self._failure is not None:
                raise self._failure
            if self._closed or time.monotonic() >= self._valid_until:
                raise GridMetAdmissionLostLease("GridMET admission permit is no longer locally valid")

    def renew(self) -> None:
        self.check()
        if self._stop.is_set():
            return
        try:
            _, started = self.controller._transition("renew", self.ticket_id, self._token)
            with self._guard:
                if not self._closed:
                    self._valid_until = started + self.controller.config.lease_seconds
            self.check()
        except GridMetAdmissionError as exc:
            with self._guard:
                self._failure = exc
            self._stop.set()
            raise

    def release(self) -> None:
        self._stop.set()
        with self._guard:
            if self._closed:
                return
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2 * _SOCKET_TIMEOUT + 0.5)
            if self._thread.is_alive():
                with self._guard:
                    self._failure = GridMetAdmissionUnavailable("GridMET admission renewal did not stop within its bound")
        with self._guard:
            self._closed = True
        self.controller._transition("release", self.ticket_id, self._token)

    def __enter__(self) -> GridMetPermit:
        try:
            self.check()
        except GridMetAdmissionError:
            try:
                self.release()
            except GridMetAdmissionError as cleanup_error:
                _LOG.warning("GridMET admission entry cleanup failed (%s)", type(cleanup_error).__name__)
            raise
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        failure = None
        try:
            self.check()
        except GridMetAdmissionError as admission_error:
            failure = admission_error
        try:
            self.release()
        except GridMetAdmissionError as cleanup_error:
            if exc is None and failure is None:
                raise
            _LOG.warning("GridMET admission permit cleanup failed (%s)", type(cleanup_error).__name__)
        with self._guard:
            failure = self._failure or failure
        if failure is not None:
            raise failure
        return False
