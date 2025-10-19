from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Dict, Tuple

import pytest

MODULE_PATH = (
    Path(__file__)
    .resolve()
    .parents[3]
    / "wepppy"
    / "weppcloud"
    / "controllers_js"
    / "unitizer_map_builder.py"
)
spec = importlib.util.spec_from_file_location("unitizer_map_builder_test", MODULE_PATH)
if spec is None or spec.loader is None:  # pragma: no cover - defensive
    raise RuntimeError("Unable to load unitizer_map_builder for tests")
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)


def _category_index(map_data: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    categories = map_data["categories"]
    return {category["key"]: category for category in categories}  # type: ignore[return-value]


def _token_index(map_data: Dict[str, object]) -> Dict[str, str]:
    return map_data["tokenToUnit"]  # type: ignore[return-value]


def test_unitizer_map_categories_match_precisions() -> None:
    module = builder.load_unitizer_module()
    map_data = builder.build_unitizer_map_data()

    expected_keys = list(module.precisions.keys())
    produced_keys = [category["key"] for category in map_data["categories"]]  # type: ignore[index]
    assert produced_keys == expected_keys


def test_conversions_cover_each_pair() -> None:
    module = builder.load_unitizer_module()
    map_data = builder.build_unitizer_map_data()
    categories = _category_index(map_data)

    for category_key, units in module.precisions.items():
        category = categories[category_key]
        unit_keys = list(units.keys())
        conversions = {
            (entry["from"], entry["to"])
            for entry in category["conversions"]  # type: ignore[index]
        }
        for src in unit_keys:
            for dst in unit_keys:
                if src == dst:
                    continue
                assert (src, dst) in conversions, (
                    f"Missing conversion for {category_key}: {src} -> {dst}"
                )


@pytest.mark.parametrize("sample", [0.0, 1.0, -3.5, 42.0, 123.456])
def test_conversion_matches_runtime(sample: float) -> None:
    module = builder.load_unitizer_module()
    map_data = builder.build_unitizer_map_data()
    categories = _category_index(map_data)

    for category_key, converters in module.converters.items():
        unit_precisions = module.precisions[category_key]
        valid_units = set(unit_precisions.keys())
        category = categories[category_key]
        conversion_index: Dict[Tuple[str, str], Dict[str, float]] = {
            (entry["from"], entry["to"]): entry  # type: ignore[index]
            for entry in category["conversions"]  # type: ignore[index]
        }

        for (src, dst), func in converters.items():
            if src not in valid_units or dst not in valid_units:
                continue
            transform = conversion_index[(src, dst)]
            produced = transform["scale"] * sample + transform["offset"]
            expected = func(sample)
            assert produced == pytest.approx(expected, rel=1e-9, abs=1e-9)


def test_token_index_covers_units() -> None:
    module = builder.load_unitizer_module()
    map_data = builder.build_unitizer_map_data()
    token_map = _token_index(map_data)

    seen_units = set()
    for category in map_data["categories"]:  # type: ignore[index]
        for unit in category["units"]:  # type: ignore[index]
            token = unit["token"]  # type: ignore[index]
            key = unit["key"]  # type: ignore[index]
            assert token_map[token] == key
            seen_units.add(key)

    all_units = {
        unit_key for category in module.precisions.values() for unit_key in category.keys()
    }
    assert seen_units == all_units
