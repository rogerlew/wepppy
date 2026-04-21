from __future__ import annotations

from random import Random
from typing import Any

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
        self._dtchr_override: int | None = None
        self._ichout_override: int | None = None
        self._chn_topaz_ids_of_interest: list[int] = []
        self._channel_critical_shear_overridden = False
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


def _extract_parser_state(wepp: _DummyWepp) -> dict[str, object]:
    return {
        "dtchr_override": wepp._dtchr_override,
        "ichout_override": wepp._ichout_override,
        "chn_topaz_ids_of_interest": list(wepp._chn_topaz_ids_of_interest),
        "delete_after_interchange": bool(wepp._delete_after_interchange),
    }


def _serialize_parser_state(state: dict[str, object]) -> dict[str, object]:
    payload: dict[str, object] = {
        "delete_after_interchange": "true" if bool(state["delete_after_interchange"]) else "false",
    }

    dtchr_override = state["dtchr_override"]
    if dtchr_override is not None:
        payload["dtchr_override"] = str(dtchr_override)

    ichout_override = state["ichout_override"]
    if ichout_override is not None:
        payload["ichout_override"] = str(ichout_override)

    channel_ids = state["chn_topaz_ids_of_interest"]
    if channel_ids:
        payload["chn_topaz_ids_of_interest"] = ",".join(str(value) for value in channel_ids)

    return payload


def _generated_valid_parser_payloads() -> list[dict[str, object]]:
    rng = Random(20260421)
    payloads: list[dict[str, object]] = []
    for idx in range(20):
        channel_ids = [rng.randint(1, 999) for _ in range(rng.randint(1, 4))]
        channel_encoding: object
        if idx % 4 == 0:
            channel_encoding = channel_ids
        elif idx % 4 == 1:
            channel_encoding = ",".join(str(value) for value in channel_ids)
        elif idx % 4 == 2:
            channel_encoding = " ".join(str(value) for value in channel_ids)
        else:
            channel_encoding = tuple(channel_ids)

        payloads.append(
            {
                "dtchr_override": str(rng.randint(60, 600)),
                "ichout_override": str(rng.choice((1, 3))),
                "chn_topaz_ids_of_interest": channel_encoding,
                "delete_after_interchange": "on" if idx % 2 == 0 else "off",
            }
        )
    return payloads


INVALID_DTCHR_OVERRIDES: tuple[Any, ...] = (59, 0, -1, "59", "-10", 59.9)
INVALID_ICHOUT_OVERRIDES: tuple[Any, ...] = (0, 2, 4, -1, "2", "4")
INVALID_CHANNEL_ID_PAYLOADS: tuple[Any, ...] = (
    "1,bad",
    "1 2 bad",
    ["7", "oops"],
    ("3", "bad"),
)


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


@pytest.mark.parametrize("payload", _generated_valid_parser_payloads())
def test_parse_round_trip_preserves_canonical_wrapper_state(payload: dict[str, object]) -> None:
    parser = WeppInputParser()

    initial = _DummyWepp()
    parser.parse(initial, payload)
    canonical_state = _extract_parser_state(initial)
    serialized_payload = _serialize_parser_state(canonical_state)

    clone = _DummyWepp()
    parser.parse(clone, serialized_payload)

    assert _extract_parser_state(clone) == canonical_state
    assert serialized_payload == _serialize_parser_state(canonical_state)


@pytest.mark.parametrize(
    "raw_value",
    ([24, 34, 44], "24,34,44", "24 34 44", ("24", "34", "44")),
)
def test_parse_channel_ids_canonicalizes_supported_payload_shapes(raw_value: object) -> None:
    parser = WeppInputParser()
    wepp = _DummyWepp()

    parser.parse(wepp, {"chn_topaz_ids_of_interest": raw_value})

    assert wepp._chn_topaz_ids_of_interest == [24, 34, 44]


@pytest.mark.parametrize("raw_value", INVALID_DTCHR_OVERRIDES)
def test_parse_rejects_dtchr_override_below_supported_minimum(raw_value: object) -> None:
    parser = WeppInputParser()
    wepp = _DummyWepp()

    with pytest.raises(ValueError, match="dtchr_override must be at least 60"):
        parser.parse(wepp, {"dtchr_override": raw_value})


@pytest.mark.parametrize("raw_value", INVALID_ICHOUT_OVERRIDES)
def test_parse_rejects_unsupported_ichout_override_values(raw_value: object) -> None:
    parser = WeppInputParser()
    wepp = _DummyWepp()

    with pytest.raises(
        ValueError,
        match="ichout_override must be 1 \\(peak only\\) or 3 \\(full timestep hydrograph\\)",
    ):
        parser.parse(wepp, {"ichout_override": raw_value})


@pytest.mark.parametrize("raw_value", INVALID_CHANNEL_ID_PAYLOADS)
def test_parse_rejects_malformed_channel_id_payloads(raw_value: object) -> None:
    parser = WeppInputParser()
    wepp = _DummyWepp()

    with pytest.raises(ValueError):
        parser.parse(wepp, {"chn_topaz_ids_of_interest": raw_value})


def test_parse_marks_channel_critical_shear_as_overridden_when_value_is_valid() -> None:
    parser = WeppInputParser()
    wepp = _DummyWepp()

    parser.parse(wepp, {"channel_critical_shear": "42.5"})

    assert wepp._channel_critical_shear == pytest.approx(42.5)
    assert wepp._channel_critical_shear_overridden is True


def test_parse_does_not_mark_channel_critical_shear_override_for_invalid_value() -> None:
    parser = WeppInputParser()
    wepp = _DummyWepp()

    parser.parse(wepp, {"channel_critical_shear": "not-a-number"})

    assert not hasattr(wepp, "_channel_critical_shear")
    assert wepp._channel_critical_shear_overridden is False
