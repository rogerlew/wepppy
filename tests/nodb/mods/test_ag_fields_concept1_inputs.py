from __future__ import annotations

import pytest

from wepppy.nodb.mods.ag_fields.concept1_inputs import (
    Concept1InputSynthesisError,
    _serialized_breakpoint_fractions,
    _serialized_ofe_lengths,
    _validated_rows,
)


pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def _rows() -> list[dict[str, object]]:
    return [
        {
            "parent_wepp_id": 7,
            "ofe_id": 1,
            "normalized_start": 0.0,
            "normalized_end": 0.25,
            "source_kind": "field",
            "sub_field_id": 31,
        },
        {
            "parent_wepp_id": 7,
            "ofe_id": 2,
            "normalized_start": 0.25,
            "normalized_end": 1.0,
            "source_kind": "background",
            "sub_field_id": None,
        },
    ]


def test_validated_rows_orders_complete_plan() -> None:
    rows = list(reversed(_rows()))

    result = _validated_rows(rows, parent_wepp_id=7)

    assert [row["ofe_id"] for row in result] == [1, 2]


def test_validated_rows_rejects_breakpoint_gap() -> None:
    rows = _rows()
    rows[1]["normalized_start"] = 0.5

    with pytest.raises(Concept1InputSynthesisError, match="not contiguous"):
        _validated_rows(rows, parent_wepp_id=7)


def test_validated_rows_rejects_field_without_subfield_id() -> None:
    rows = _rows()
    rows[0]["sub_field_id"] = None

    with pytest.raises(Concept1InputSynthesisError, match="lacks a finite"):
        _validated_rows(rows, parent_wepp_id=7)


def test_serialized_breakpoint_fractions_follow_two_decimal_ofe_lengths() -> None:
    breakpoints = [0.0, 0.010752688172043012, 0.2849462365591398, 1.0]

    result = _serialized_breakpoint_fractions(
        breakpoints,
        total_length_m=247.3,
    )

    lengths = [2.66, 67.81, 176.83]
    assert result == pytest.approx(
        [0.0, 2.66 / sum(lengths), (2.66 + 67.81) / sum(lengths), 1.0],
        rel=0.0,
        abs=1e-12,
    )


def test_serialized_ofe_lengths_expose_native_area_basis() -> None:
    assert _serialized_ofe_lengths(
        [0.0, 0.25, 1.0],
        total_length_m=10.03,
    ) == [2.51, 7.52]
