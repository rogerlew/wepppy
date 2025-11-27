from __future__ import annotations

from contextlib import nullcontext

import pytest

from wepppy.nodb.unitizer import Unitizer


pytestmark = pytest.mark.unit


class DummyLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def warning(self, msg: str, *args, **kwargs) -> None:
        formatted = msg % args if args else msg
        self.messages.append(formatted)


class DummyUnitizer(Unitizer):
    def __init__(self) -> None:
        self._preferences = {}
        self._logger = DummyLogger()

    def locked(self):
        return nullcontext()


def test_set_preferences_accepts_known_category_when_non_strict() -> None:
    unitizer = DummyUnitizer()

    prefs = unitizer.set_preferences({"currency-area": "$/acre"}, strict=False)

    assert prefs["currency-area"] == "$/acre"


def test_set_preferences_skips_unknown_when_non_strict() -> None:
    unitizer = DummyUnitizer()

    prefs = unitizer.set_preferences(
        {
            "currency-area": "$/acre",
            "mystery": "value",
        },
        strict=False,
    )

    assert prefs["currency-area"] == "$/acre"
    assert "mystery" not in prefs
    assert any("mystery" in message for message in unitizer._logger.messages)


def test_set_preferences_skips_invalid_value_when_non_strict() -> None:
    unitizer = DummyUnitizer()

    prefs = unitizer.set_preferences({"area": "bogus"}, strict=False)

    assert "area" not in prefs
    assert any("area=bogus" in message for message in unitizer._logger.messages)


def test_set_preferences_raises_on_unknown_when_strict() -> None:
    unitizer = DummyUnitizer()

    with pytest.raises(KeyError):
        unitizer.set_preferences({"mystery": "value"})
