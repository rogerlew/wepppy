"""Bounded, framework-neutral browser session cookie migration helpers."""

from __future__ import annotations

from dataclasses import dataclass
import pickle
from typing import Any, Callable, Mapping, Sequence

from flask_session.sessions import RedisSessionInterface, total_seconds, want_bytes
from itsdangerous import BadSignature
from redis.exceptions import RedisError
from werkzeug.datastructures import MultiDict
from werkzeug.http import parse_cookie


MAX_COOKIE_HEADER_BYTES = 8192
MAX_COOKIE_CANDIDATES = 64
MAX_SIGNED_SESSION_CANDIDATES = 8
MAX_COOKIE_VALUE_BYTES = 512
DEFAULT_PRIMARY_COOKIE_NAME = "__Host-weppcloud_session"
DEFAULT_LEGACY_COOKIE_NAME = "session"
REVOCATION_KEY_PREFIX = "auth:session:revoked:"
REVOCATION_TTL_SECONDS = 4 * 24 * 60 * 60
_ORIGINAL_PRINCIPAL_UNKNOWN = object()


class SessionSelectionError(RuntimeError):
    """A presented cookie set cannot safely authorize a session."""


class SessionCookieBoundsError(SessionSelectionError):
    """The raw Cookie header exceeds the ratified migration bounds."""


class SessionStateError(SessionSelectionError):
    """The authoritative session state is missing, corrupt, or unavailable."""


class SessionRevokedError(SessionStateError):
    """The authoritative session was explicitly revoked."""


class SessionConflictError(SessionSelectionError):
    """Presented live sessions do not represent one compatible principal."""


@dataclass(frozen=True)
class SelectedSession:
    sid: str
    payload: Mapping[str, Any]
    source: str
    signed_sids: tuple[str, ...]
    invalid_signatures: int


def cookie_values(raw_cookie_headers: Sequence[bytes | str], name: str) -> list[str]:
    encoded_headers = [
        value if isinstance(value, bytes) else value.encode("latin-1", "strict")
        for value in raw_cookie_headers
    ]
    if sum(len(value) for value in encoded_headers) > MAX_COOKIE_HEADER_BYTES:
        raise SessionCookieBoundsError("Cookie header exceeds migration limit")
    combined = b"; ".join(encoded_headers).decode("latin-1", "strict")
    parsed = parse_cookie(combined, cls=MultiDict)
    values = [str(value) for value in parsed.getlist(name)]
    if len(values) > MAX_COOKIE_CANDIDATES:
        raise SessionCookieBoundsError("Too many session cookie candidates")
    if any(len(value.encode("utf-8")) > MAX_COOKIE_VALUE_BYTES for value in values):
        raise SessionCookieBoundsError("Session cookie candidate exceeds limit")
    return values


def _principal(payload: Mapping[str, Any]) -> tuple[str, str | None]:
    user_id = payload.get("_user_id")
    if user_id is None:
        return ("anonymous", None)
    return ("authenticated", str(user_id))


def select_session(
    raw_cookie_headers: Sequence[bytes | str],
    *,
    primary_name: str,
    legacy_name: str,
    unsign: Callable[[str], str],
    load: Callable[[str], Mapping[str, Any] | None],
    is_revoked: Callable[[str], bool] | None = None,
) -> SelectedSession | None:
    primary_values = cookie_values(raw_cookie_headers, primary_name)
    source = "primary" if primary_values else "legacy"
    values = primary_values or cookie_values(raw_cookie_headers, legacy_name)
    if not values:
        return None

    authoritative_sid: str | None = None
    authoritative_payload: Mapping[str, Any] | None = None
    signed_sids: list[str] = []
    live_principals: list[tuple[str, str | None]] = []
    invalid_signatures = 0

    for raw_value in values:
        if not raw_value:
            continue
        try:
            sid = unsign(raw_value)
        except (BadSignature, UnicodeDecodeError):
            invalid_signatures += 1
            continue
        if not sid:
            continue
        signed_sids.append(sid)
        if len(set(signed_sids)) > MAX_SIGNED_SESSION_CANDIDATES:
            raise SessionCookieBoundsError("Too many signed session candidates")
        if is_revoked is not None and is_revoked(sid):
            if authoritative_sid is None:
                raise SessionRevokedError("Authoritative session is revoked")
            continue
        if sid in signed_sids[:-1]:
            continue
        payload = load(sid)
        if authoritative_sid is None:
            authoritative_sid = sid
            if payload is None:
                raise SessionStateError("Authoritative session is missing")
            authoritative_payload = payload
            live_principals.append(_principal(payload))
            continue
        if payload is not None:
            live_principals.append(_principal(payload))

    if authoritative_sid is None or authoritative_payload is None:
        raise SessionStateError("No valid signed session candidate")

    first_principal = live_principals[0]
    if first_principal[0] == "anonymous" and len(live_principals) > 1:
        raise SessionConflictError("Multiple anonymous sessions are ambiguous")
    if any(principal != first_principal for principal in live_principals[1:]):
        raise SessionConflictError("Session principals conflict")

    return SelectedSession(
        sid=authoritative_sid,
        payload=authoritative_payload,
        source=source,
        signed_sids=tuple(signed_sids),
        invalid_signatures=invalid_signatures,
    )


def presented_signed_sids(
    raw_cookie_headers: Sequence[bytes | str],
    *,
    names: Sequence[str],
    unsign: Callable[[str], str],
    max_signed_candidates: int | None = MAX_SIGNED_SESSION_CANDIDATES,
) -> tuple[str, ...]:
    result: list[str] = []
    for name in names:
        for raw_value in cookie_values(raw_cookie_headers, name):
            try:
                sid = unsign(raw_value)
            except (BadSignature, UnicodeDecodeError):
                continue
            if sid and sid not in result:
                result.append(sid)
                if (
                    max_signed_candidates is not None
                    and len(result) > max_signed_candidates
                ):
                    raise SessionCookieBoundsError(
                        "Too many signed session candidates"
                    )
    return tuple(result)


class MigratingRedisSessionInterface(RedisSessionInterface):
    """Flask-Session 0.4 Redis interface with bounded dual-name migration."""

    @classmethod
    def from_interface(
        cls, interface: RedisSessionInterface
    ) -> "MigratingRedisSessionInterface":
        return cls(
            interface.redis,
            interface.key_prefix,
            use_signer=interface.use_signer,
            permanent=interface.permanent,
        )

    def _unsign(self, app: Any, raw_value: str) -> str:
        if not self.use_signer:
            return raw_value
        signer = self._get_signer(app)
        if signer is None:
            raise BadSignature("Session signer unavailable")
        return signer.unsign(raw_value).decode("utf-8")

    def _load_payload(self, sid: str) -> Mapping[str, Any] | None:
        raw_value = self.redis.get(self.key_prefix + sid)
        if raw_value is None:
            return None
        try:
            payload = self.serializer.loads(raw_value)
        except (
            AttributeError,
            EOFError,
            ImportError,
            IndexError,
            pickle.UnpicklingError,
            TypeError,
            ValueError,
        ) as exc:
            raise SessionStateError("Invalid session payload") from exc
        if not isinstance(payload, Mapping):
            raise SessionStateError("Invalid session payload type")
        return payload

    def _is_revoked(self, sid: str) -> bool:
        return bool(self.redis.exists(REVOCATION_KEY_PREFIX + sid))

    @staticmethod
    def _track_original_principal(session: Any) -> Any:
        session._wepp_original_user_id = session.get("_user_id")
        return session

    def _delete_primary_cookie_if_distinct(
        self, app: Any, response: Any, *, domain: str, path: str
    ) -> None:
        primary_name = app.config.get(
            "SESSION_COOKIE_PRIMARY_NAME", app.config["SESSION_COOKIE_NAME"]
        )
        if primary_name == app.session_cookie_name:
            return
        primary_is_host_owned = primary_name.startswith("__Host-")
        response.delete_cookie(
            primary_name,
            domain=None if primary_is_host_owned else domain,
            path="/" if primary_is_host_owned else path,
            secure=True if primary_is_host_owned else self.get_cookie_secure(app),
            httponly=self.get_cookie_httponly(app),
            samesite=(
                self.get_cookie_samesite(app)
                if self.has_same_site_capability
                else None
            ),
        )

    def open_session(self, app: Any, request: Any) -> Any:
        if not app.config.get("SESSION_COOKIE_MIGRATION_ENABLED", False):
            return super().open_session(app, request)
        raw_headers = [request.headers.get("Cookie", "")]
        try:
            selected = select_session(
                raw_headers,
                primary_name=app.config.get(
                    "SESSION_COOKIE_PRIMARY_NAME", app.config["SESSION_COOKIE_NAME"]
                ),
                legacy_name=app.config["SESSION_COOKIE_LEGACY_NAME"],
                unsign=lambda value: self._unsign(app, value),
                load=self._load_payload,
                is_revoked=self._is_revoked,
            )
        except (SessionSelectionError, RedisError) as exc:
            app.logger.warning(
                "session migration rejected presented state",
                extra={"migration_outcome": type(exc).__name__},
            )
            sid = self._generate_sid()
            initial = {}
            if isinstance(
                exc,
                (SessionConflictError, SessionCookieBoundsError, SessionRevokedError),
            ):
                initial = {
                    "_session_migration_conflict": True,
                    "_remember": "clear",
                }
            session = self._track_original_principal(
                self.session_class(initial, sid=sid, permanent=self.permanent)
            )
            session._wepp_clear_primary_cookie = True
            return session
        if selected is None:
            sid = self._generate_sid()
            return self._track_original_principal(
                self.session_class(sid=sid, permanent=self.permanent)
            )
        if selected.source == "legacy":
            app.logger.info(
                "session migration adopted legacy state",
                extra={
                    "migration_outcome": "legacy_adopted",
                    "invalid_signatures": selected.invalid_signatures,
                },
            )
        return self._track_original_principal(
            self.session_class(dict(selected.payload), sid=selected.sid)
        )

    def save_session(self, app: Any, session: Any, response: Any) -> Any:
        if not app.config.get("SESSION_COOKIE_MIGRATION_ENABLED", False):
            return super().save_session(app, session, response)

        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        if not session:
            if session.modified:
                self.redis.delete(self.key_prefix + session.sid)
                response.delete_cookie(app.session_cookie_name, domain=domain, path=path)
                self._delete_primary_cookie_if_distinct(
                    app, response, domain=domain, path=path
                )
            elif getattr(session, "_wepp_clear_primary_cookie", False):
                self._delete_primary_cookie_if_distinct(
                    app, response, domain=domain, path=path
                )
            return None

        serialized = self.serializer.dumps(dict(session))
        ttl_seconds = total_seconds(app.permanent_session_lifetime)
        original_user_id = getattr(
            session,
            "_wepp_original_user_id",
            _ORIGINAL_PRINCIPAL_UNKNOWN,
        )
        if original_user_id is None and session.get("_user_id") is not None:
            old_sid = session.sid
            new_sid = self._generate_sid()
            rotated = self.redis.eval(
                """
                if redis.call('EXISTS', KEYS[1]) == 1 then
                    redis.call('DEL', KEYS[2])
                    return 0
                end
                redis.call('DEL', KEYS[2])
                redis.call('SETEX', KEYS[1], ARGV[1], '1')
                redis.call('SETEX', KEYS[3], ARGV[2], ARGV[3])
                return 1
                """,
                3,
                REVOCATION_KEY_PREFIX + old_sid,
                self.key_prefix + old_sid,
                self.key_prefix + new_sid,
                REVOCATION_TTL_SECONDS,
                ttl_seconds,
                serialized,
            )
            if not rotated:
                response.delete_cookie(app.session_cookie_name, domain=domain, path=path)
                self._delete_primary_cookie_if_distinct(
                    app, response, domain=domain, path=path
                )
                response.delete_cookie(
                    app.config.get("REMEMBER_COOKIE_NAME", "remember_token"),
                    domain=app.config.get("REMEMBER_COOKIE_DOMAIN"),
                    path=app.config.get("REMEMBER_COOKIE_PATH", "/"),
                )
                return None
            session.sid = new_sid
            self._delete_primary_cookie_if_distinct(
                app, response, domain=domain, path=path
            )

        saved = self.redis.eval(
            """
            if redis.call('EXISTS', KEYS[1]) == 1 then
                redis.call('DEL', KEYS[2])
                return 0
            end
            redis.call('SETEX', KEYS[2], ARGV[1], ARGV[2])
            return 1
            """,
            2,
            REVOCATION_KEY_PREFIX + session.sid,
            self.key_prefix + session.sid,
            ttl_seconds,
            serialized,
        )
        if not saved:
            response.delete_cookie(app.session_cookie_name, domain=domain, path=path)
            self._delete_primary_cookie_if_distinct(
                app, response, domain=domain, path=path
            )
            response.delete_cookie(
                app.config.get("REMEMBER_COOKIE_NAME", "remember_token"),
                domain=app.config.get("REMEMBER_COOKIE_DOMAIN"),
                path=app.config.get("REMEMBER_COOKIE_PATH", "/"),
                secure=app.config.get("REMEMBER_COOKIE_SECURE", False),
                httponly=app.config.get("REMEMBER_COOKIE_HTTPONLY", True),
                samesite=app.config.get("REMEMBER_COOKIE_SAMESITE"),
            )
            return None

        cookie_value: Any = session.sid
        if self.use_signer:
            cookie_value = self._get_signer(app).sign(want_bytes(session.sid))
        if isinstance(cookie_value, bytes):
            cookie_value = cookie_value.decode("utf-8")
        if getattr(session, "_wepp_clear_primary_cookie", False):
            self._delete_primary_cookie_if_distinct(
                app, response, domain=domain, path=path
            )
        cookie_kwargs = {
            "expires": self.get_expiration_time(app, session),
            "httponly": self.get_cookie_httponly(app),
            "domain": domain,
            "path": path,
            "secure": self.get_cookie_secure(app),
        }
        if self.has_same_site_capability:
            cookie_kwargs["samesite"] = self.get_cookie_samesite(app)
        response.set_cookie(app.session_cookie_name, cookie_value, **cookie_kwargs)
        return None


def revoke_presented_sessions(app: Any, request: Any) -> int:
    """Invalidate and fence bounded signed SIDs carried by a logout/reset request."""
    interface = app.session_interface
    if (
        not isinstance(interface, MigratingRedisSessionInterface)
        or not app.config.get("SESSION_COOKIE_MIGRATION_ENABLED", False)
    ):
        return 0
    raw_headers = [request.headers.get("Cookie", "")]
    try:
        sids = presented_signed_sids(
            raw_headers,
            names=(
                app.config.get(
                    "SESSION_COOKIE_PRIMARY_NAME", app.config["SESSION_COOKIE_NAME"]
                ),
                app.config["SESSION_COOKIE_NAME"],
                app.config["SESSION_COOKIE_LEGACY_NAME"],
            ),
            unsign=lambda value: interface._unsign(app, value),
            max_signed_candidates=None,
        )
    except SessionSelectionError as exc:
        app.logger.warning(
            "session logout candidate parsing rejected",
            extra={"migration_outcome": type(exc).__name__},
        )
        return 0
    ttl_seconds = max(
        int(app.permanent_session_lifetime.total_seconds()),
        REVOCATION_TTL_SECONDS,
    )
    pipeline = interface.redis.pipeline()
    for sid in sids:
        pipeline.delete(interface.key_prefix + sid)
        pipeline.setex(REVOCATION_KEY_PREFIX + sid, ttl_seconds, "1")
    if sids:
        pipeline.execute()
    return len(sids)


__all__ = [
    "DEFAULT_LEGACY_COOKIE_NAME",
    "DEFAULT_PRIMARY_COOKIE_NAME",
    "REVOCATION_KEY_PREFIX",
    "REVOCATION_TTL_SECONDS",
    "MAX_SIGNED_SESSION_CANDIDATES",
    "SelectedSession",
    "SessionConflictError",
    "SessionCookieBoundsError",
    "SessionSelectionError",
    "SessionRevokedError",
    "SessionStateError",
    "cookie_values",
    "presented_signed_sids",
    "MigratingRedisSessionInterface",
    "revoke_presented_sessions",
    "select_session",
]
