from __future__ import annotations

import pytest

from wepppy.nodb.mods.ag_fields.concept1_inputs import (
    Concept1InputSynthesisError,
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
