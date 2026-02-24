from __future__ import annotations

import pytest

from wepppy.nodb.core.wepp_input_parser import WeppInputParser

pytestmark = pytest.mark.unit


class _DummyOpts:
    def parse_inputs(self, _kwds):
        return None


class _DummyWepp:
    def __init__(self, *, delete_after_interchange: bool = False) -> None:
        self.baseflow_opts = _DummyOpts()
        self.phosphorus_opts = _DummyOpts()
        self.tcr_opts = _DummyOpts()
        self.snow_opts = _DummyOpts()
        self.frost_opts = _DummyOpts()
        self._delete_after_interchange = delete_after_interchange
        self.guard_calls = 0

    def _guard_unitized_bounds(self) -> None:
        self.guard_calls += 1

    @property
    def delete_after_interchange(self) -> bool:
        return self._delete_after_interchange

    @delete_after_interchange.setter
    def delete_after_interchange(self, value: bool) -> None:
        self._delete_after_interchange = bool(value)


class _GuardedDeleteSetterWepp(_DummyWepp):
    @property
    def delete_after_interchange(self) -> bool:
        return self._delete_after_interchange

    @delete_after_interchange.setter
    def delete_after_interchange(self, _value: bool) -> None:
        raise AssertionError("delete_after_interchange setter should not be called during parse_inputs")


def test_parse_sets_delete_after_interchange_from_boolean_payload() -> None:
    parser = WeppInputParser()
    wepp = _DummyWepp(delete_after_interchange=False)

    parser.parse(wepp, {"delete_after_interchange": True})

    assert wepp.delete_after_interchange is True
    assert wepp.guard_calls == 1


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("on", True),
        ("true", True),
        ("yes", True),
        ("1", True),
        ("off", False),
        ("false", False),
        ("no", False),
        ("0", False),
    ],
)
def test_parse_coerces_delete_after_interchange_string_tokens(
    raw_value: str, expected: bool
) -> None:
    parser = WeppInputParser()
    wepp = _DummyWepp(delete_after_interchange=not expected)

    parser.parse(wepp, {"delete_after_interchange": raw_value})

    assert wepp.delete_after_interchange is expected


def test_parse_ignores_invalid_delete_after_interchange_tokens() -> None:
    parser = WeppInputParser()
    wepp = _DummyWepp(delete_after_interchange=True)

    parser.parse(wepp, {"delete_after_interchange": "sometimes"})

    assert wepp.delete_after_interchange is True


def test_parse_sets_delete_after_interchange_without_invoking_property_setter() -> None:
    parser = WeppInputParser()
    wepp = _GuardedDeleteSetterWepp(delete_after_interchange=False)
    wepp._delete_after_interchange = False

    parser.parse(wepp, {"delete_after_interchange": True})

    assert wepp._delete_after_interchange is True
