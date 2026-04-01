from __future__ import annotations

import pytest

from wepppy.tools import scheduler


pytestmark = pytest.mark.unit


def test_as_int_resolves_env_token_with_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("USERSUM_INDEX_INTERVAL_SECONDS", raising=False)
    value = scheduler._as_int("${USERSUM_INDEX_INTERVAL_SECONDS:-14400}", name="interval")
    assert value == 14400


def test_as_int_resolves_env_token_with_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USERSUM_INDEX_INTERVAL_SECONDS", "1200")
    value = scheduler._as_int("${USERSUM_INDEX_INTERVAL_SECONDS:-14400}", name="interval")
    assert value == 1200


def test_as_int_rejects_missing_env_token_without_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("USERSUM_INDEX_INTERVAL_SECONDS", raising=False)
    with pytest.raises(ValueError, match="references USERSUM_INDEX_INTERVAL_SECONDS"):
        scheduler._as_int("${USERSUM_INDEX_INTERVAL_SECONDS}", name="interval")
