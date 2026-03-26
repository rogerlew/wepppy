from __future__ import annotations

from contextlib import nullcontext

import pytest

import wepppy.nodb.unitizer as unitizer_module
from wepppy.nodb.unitizer import Unitizer


pytestmark = pytest.mark.unit


class DummyUnitizer(Unitizer):
    def __init__(self, preferences: dict[str, str] | None = None) -> None:
        self._preferences = preferences or {}

    def locked(self):
        return nullcontext()


def test_resolve_target_unit_project_mode_uses_preferences() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    resolution = unitizer.resolve_target_unit("m", units_mode="project")

    assert resolution.source_unit == "m"
    assert resolution.target_unit == "ft"
    assert resolution.unit_class == "sm-distance"
    assert resolution.precision_policy == 2
    assert resolution.pass_through_reason is None


def test_resolve_target_unit_allows_ambiguous_target_name_in_same_class() -> None:
    unitizer = DummyUnitizer({"sm-concentration": "ppm"})

    resolution = unitizer.resolve_target_unit("mg/L", target_unit="ppm")

    assert resolution.source_unit == "mg/L"
    assert resolution.target_unit == "ppm"
    assert resolution.unit_class == "sm-concentration"
    assert resolution.precision_policy == 2
    assert resolution.pass_through_reason is None


def test_resolve_target_unit_rejects_target_outside_source_class() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    with pytest.raises(ValueError):
        unitizer.resolve_target_unit("m", target_unit="degc")


def test_resolve_target_unit_rejects_unknown_units_mode() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    with pytest.raises(ValueError):
        unitizer.resolve_target_unit("m", units_mode="metric")


def test_resolve_target_unit_normalizes_si_mode_string() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    resolution = unitizer.resolve_target_unit("ft", units_mode=" SI ")

    assert resolution.source_unit == "ft"
    assert resolution.target_unit == "m"
    assert resolution.pass_through_reason is None


def test_resolve_target_unit_signals_missing_source_unit() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    resolution = unitizer.resolve_target_unit(None)

    assert resolution.pass_through_reason == "source_unit_missing"
    assert resolution.target_unit is None
    assert resolution.unit_class is None


def test_resolve_target_unit_signals_unknown_source_unit() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    resolution = unitizer.resolve_target_unit("not-a-unit")

    assert resolution.pass_through_reason == "unit_class_not_found"
    assert resolution.target_unit is None
    assert resolution.unit_class is None


def test_resolve_target_unit_signals_project_preference_missing() -> None:
    unitizer = DummyUnitizer({})

    resolution = unitizer.resolve_target_unit("m", units_mode="project")

    assert resolution.pass_through_reason == "preference_missing"
    assert resolution.unit_class == "sm-distance"
    assert resolution.target_unit is None


def test_resolve_target_unit_signals_ambiguous_source_unit_class() -> None:
    unitizer = DummyUnitizer({})

    resolution = unitizer.resolve_target_unit("lb")

    assert resolution.pass_through_reason == "ambiguous_unit_class"
    assert resolution.unit_class is None
    assert resolution.target_unit is None


def test_resolve_target_unit_signals_ambiguous_class_with_explicit_target() -> None:
    unitizer = DummyUnitizer({})

    resolution = unitizer.resolve_target_unit("g/cm^3", target_unit="lb/ft^3")

    assert resolution.pass_through_reason == "ambiguous_unit_class"
    assert resolution.unit_class is None
    assert resolution.target_unit == "lb/ft^3"


def test_convert_scalar_converts_numeric_value_and_returns_metadata() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    result = unitizer.convert_scalar(2.0, "m", units_mode="project")

    assert result.value == pytest.approx(6.56168)
    assert result.metadata.source_unit == "m"
    assert result.metadata.target_unit == "ft"
    assert result.metadata.unit_class == "sm-distance"
    assert result.metadata.precision_policy == 2
    assert result.metadata.conversion_applied is True
    assert result.metadata.pass_through_reason is None


def test_convert_scalar_reports_no_mapping_for_pass_through(monkeypatch: pytest.MonkeyPatch) -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})
    patched_class_converters = dict(unitizer_module.converters["sm-distance"])
    patched_class_converters.pop(("m", "ft"))
    monkeypatch.setitem(unitizer_module.converters, "sm-distance", patched_class_converters)

    result = unitizer.convert_scalar(5.0, "m", units_mode="english")

    assert result.value == 5.0
    assert result.metadata.source_unit == "m"
    assert result.metadata.target_unit == "ft"
    assert result.metadata.unit_class == "sm-distance"
    assert result.metadata.precision_policy == 2
    assert result.metadata.conversion_applied is False
    assert result.metadata.pass_through_reason == "no_mapping"


def test_convert_scalar_reports_non_numeric_pass_through() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    result = unitizer.convert_scalar("not-a-number", "m", units_mode="english")

    assert result.value == "not-a-number"
    assert result.metadata.target_unit == "ft"
    assert result.metadata.conversion_applied is False
    assert result.metadata.pass_through_reason == "non_numeric"


def test_convert_scalar_reports_conversion_error_pass_through(monkeypatch: pytest.MonkeyPatch) -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    def _raise_value_error(_value: float) -> float:
        raise ValueError("boom")

    patched_class_converters = dict(unitizer_module.converters["sm-distance"])
    patched_class_converters[("m", "ft")] = _raise_value_error
    monkeypatch.setitem(unitizer_module.converters, "sm-distance", patched_class_converters)

    result = unitizer.convert_scalar(1.0, "m", units_mode="english")

    assert result.value == 1.0
    assert result.metadata.conversion_applied is False
    assert result.metadata.pass_through_reason == "conversion_error"


def test_convert_sequence_converts_each_value_in_order() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    result = unitizer.convert_sequence([1.0, 2.0], "m", units_mode="english")

    assert result.values == pytest.approx([3.28084, 6.56168])
    assert result.metadata.source_unit == "m"
    assert result.metadata.target_unit == "ft"
    assert result.metadata.conversion_applied is True
    assert result.metadata.pass_through_reason is None


def test_convert_sequence_reports_identity_when_no_values_need_conversion() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    result = unitizer.convert_sequence([1.0, 2.0], "m", units_mode="si")

    assert result.values == pytest.approx([1.0, 2.0])
    assert result.metadata.conversion_applied is False
    assert result.metadata.pass_through_reason == "identity"


def test_convert_sequence_reports_non_numeric_when_no_values_convert() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    result = unitizer.convert_sequence(["a", "b"], "m", units_mode="english")

    assert result.values == ["a", "b"]
    assert result.metadata.conversion_applied is False
    assert result.metadata.pass_through_reason == "non_numeric"


def test_convert_sequence_reports_partial_non_numeric_pass_through() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    result = unitizer.convert_sequence([1.0, "n/a"], "m", units_mode="english")

    assert result.values[0] == pytest.approx(3.28084)
    assert result.values[1] == "n/a"
    assert result.metadata.conversion_applied is True
    assert result.metadata.pass_through_reason == "partial_non_numeric"


def test_convert_sequence_reports_partial_conversion_error(monkeypatch: pytest.MonkeyPatch) -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    def _raise_for_two(value: float) -> float:
        if value == 2.0:
            raise ValueError("boom")
        return value * 3.28084

    patched_class_converters = dict(unitizer_module.converters["sm-distance"])
    patched_class_converters[("m", "ft")] = _raise_for_two
    monkeypatch.setitem(unitizer_module.converters, "sm-distance", patched_class_converters)

    result = unitizer.convert_sequence([1.0, 2.0], "m", units_mode="english")

    assert result.values[0] == pytest.approx(3.28084)
    assert result.values[1] == 2.0
    assert result.metadata.conversion_applied is True
    assert result.metadata.pass_through_reason == "partial_conversion_error"


def test_convert_sequence_reports_conversion_error_when_all_values_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    def _always_raise(_value: float) -> float:
        raise ValueError("boom")

    patched_class_converters = dict(unitizer_module.converters["sm-distance"])
    patched_class_converters[("m", "ft")] = _always_raise
    monkeypatch.setitem(unitizer_module.converters, "sm-distance", patched_class_converters)

    result = unitizer.convert_sequence([1.0, 2.0], "m", units_mode="english")

    assert result.values == [1.0, 2.0]
    assert result.metadata.conversion_applied is False
    assert result.metadata.pass_through_reason == "conversion_error"


def test_convert_table_supports_mapping_shape_and_missing_column_metadata() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})
    table = {"runoff": [1.0, 2.0], "label": ["a", "b"]}

    result = unitizer.convert_table(
        table,
        {
            "runoff": "m",
            "missing": "m",
        },
        units_mode="english",
    )

    assert result.data["runoff"] == pytest.approx([3.28084, 6.56168])
    assert result.metadata_by_column["runoff"].conversion_applied is True
    assert result.metadata_by_column["missing"].conversion_applied is False
    assert result.metadata_by_column["missing"].pass_through_reason == "missing_column"


def test_convert_table_supports_mapping_scalar_column_values() -> None:
    unitizer = DummyUnitizer({"xs-distance": "in"})
    table = {"depth": 25.4}

    result = unitizer.convert_table(table, {"depth": "mm"}, units_mode="english")

    assert result.data["depth"] == pytest.approx(1.0)
    assert result.metadata_by_column["depth"].conversion_applied is True
    assert result.metadata_by_column["depth"].target_unit == "in"


def test_convert_table_applies_target_units_override() -> None:
    unitizer = DummyUnitizer({"xs-distance": "in"})
    table = {"depth": [25.4, 50.8]}

    result = unitizer.convert_table(
        table,
        {"depth": "mm"},
        units_mode="english",
        target_units={"depth": "in"},
    )

    assert result.data["depth"] == pytest.approx([1.0, 2.0])
    assert result.metadata_by_column["depth"].target_unit == "in"
    assert result.metadata_by_column["depth"].conversion_applied is True


def test_convert_table_supports_record_sequence_shape() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})
    rows = [
        {"length": 1.0, "id": 1},
        {"length": 2.0, "id": 2},
    ]

    result = unitizer.convert_table(rows, {"length": "m"}, units_mode="english")

    assert result.data[0]["length"] == pytest.approx(3.28084)
    assert result.data[1]["length"] == pytest.approx(6.56168)
    assert result.metadata_by_column["length"].conversion_applied is True


def test_convert_table_supports_sparse_record_columns() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})
    rows = [
        {"length": 1.0, "id": 1},
        {"id": 2},
    ]

    result = unitizer.convert_table(rows, {"length": "m", "missing": "m"}, units_mode="english")

    assert result.data[0]["length"] == pytest.approx(3.28084)
    assert "length" not in result.data[1]
    assert result.metadata_by_column["length"].conversion_applied is True
    assert result.metadata_by_column["missing"].pass_through_reason == "missing_column"


def test_convert_table_supports_pandas_dataframe_when_available() -> None:
    pd = pytest.importorskip("pandas")
    unitizer = DummyUnitizer({"sm-distance": "ft"})
    table = pd.DataFrame({"length": [1.0, 2.0], "id": [1, 2]})

    result = unitizer.convert_table(table, {"length": "m"}, units_mode="english")

    assert isinstance(result.data, pd.DataFrame)
    assert result.data["length"].tolist() == pytest.approx([3.28084, 6.56168])
    assert result.metadata_by_column["length"].conversion_applied is True


def test_convert_table_raises_for_unsupported_shape() -> None:
    unitizer = DummyUnitizer({"sm-distance": "ft"})

    with pytest.raises(TypeError):
        unitizer.convert_table(42, {"length": "m"})


def test_preferences_fingerprint_is_stable_across_key_order() -> None:
    left = DummyUnitizer({"distance": "km", "area": "acre"})
    right = DummyUnitizer({"area": "acre", "distance": "km"})

    assert left.preferences_fingerprint() == right.preferences_fingerprint()

    right._preferences["area"] = "ha"
    assert left.preferences_fingerprint() != right.preferences_fingerprint()


def test_context_processor_package_preserves_legacy_keys_and_html_shapes() -> None:
    package = Unitizer.context_processor_package()

    assert {"unitizer", "unitizer_units", "unitizer_with_units"} <= set(package)
    assert "unitizer-wrapper" in package["unitizer"](1.0, "m")
    assert "unitizer-wrapper" in package["unitizer_units"]("m")
    assert "unitizer-wrapper" in package["unitizer_with_units"](1.0, "m")
