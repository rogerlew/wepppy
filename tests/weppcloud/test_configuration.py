from __future__ import annotations

import pytest

import wepppy.weppcloud.configuration as configuration
from wepppy.config import redis_settings

pytestmark = pytest.mark.unit


def test_build_session_redis_uses_session_url_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_session_url(db_default: int = 11) -> str:
        captured["db_default"] = db_default
        return "redis://session-cache:6380/11"

    def fake_from_url(url: str):
        captured["url"] = url
        return "client"

    monkeypatch.setattr(redis_settings, "session_redis_url", fake_session_url)
    monkeypatch.setattr(configuration.redis, "from_url", fake_from_url)

    result = configuration._build_session_redis()

    assert result == "client"
    assert captured["db_default"] == 11
    assert captured["url"] == "redis://session-cache:6380/11"
