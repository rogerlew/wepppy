from __future__ import annotations

import pytest

from wepppy.microservices.rq_engine import auth


pytestmark = pytest.mark.microservice


def test_authorize_run_access_rejects_service_without_run_scope() -> None:
    with pytest.raises(auth.AuthError) as exc_info:
        auth.authorize_run_access({"token_class": "service"}, "run-1")

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"
    assert "run scope" in exc_info.value.message.lower()


def test_authorize_run_access_rejects_mcp_without_run_scope() -> None:
    with pytest.raises(auth.AuthError) as exc_info:
        auth.authorize_run_access({"token_class": "mcp"}, "run-1")

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"
    assert "run scope" in exc_info.value.message.lower()


def test_authorize_run_access_allows_service_with_matching_run_scope() -> None:
    auth.authorize_run_access({"token_class": "service", "runs": ["run-1", "run-2"]}, "run-1")


def test_authorize_run_access_rejects_service_with_wrong_run_scope() -> None:
    with pytest.raises(auth.AuthError) as exc_info:
        auth.authorize_run_access({"token_class": "service", "runs": ["run-2"]}, "run-1")

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"
    assert "not authorized" in exc_info.value.message.lower()


def test_require_session_marker_returns_unauthorized_when_marker_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingMarkerRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def exists(self, key: str) -> bool:
            return False

    monkeypatch.setattr(auth.redis, "Redis", lambda **kwargs: MissingMarkerRedis())

    with pytest.raises(auth.AuthError) as exc_info:
        auth.require_session_marker(
            {
                "token_class": "session",
                "session_id": "sid-1",
                "runid": "run-1",
            },
            "run-1",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "unauthorized"
    assert "session token invalid or expired" in exc_info.value.message.lower()
