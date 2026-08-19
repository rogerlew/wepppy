from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_TOOL_PATH = Path(__file__).parents[3] / "tools" / "eu_invalid_soil_search.py"
_SPEC = importlib.util.spec_from_file_location("eu_invalid_soil_search", _TOOL_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_sample_pixel_indices_is_deterministic_and_stratified() -> None:
    samples_a = _MODULE._sample_pixel_indices(
        100,
        80,
        400,
        seed=20260819,
    )
    samples_b = _MODULE._sample_pixel_indices(
        100,
        80,
        400,
        seed=20260819,
    )

    assert samples_a == samples_b
    assert len(samples_a) == 400
    assert len(set(samples_a)) == 400
    assert {row // 4 for row, _ in samples_a} == set(range(20))
    assert {col // 5 for _, col in samples_a} == set(range(20))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"width": 0, "height": 80, "sample_count": 1},
        {"width": 100, "height": 80, "sample_count": 0},
        {"width": 2, "height": 2, "sample_count": 5},
    ],
)
def test_sample_pixel_indices_rejects_invalid_requests(kwargs) -> None:
    with pytest.raises(ValueError):
        _MODULE._sample_pixel_indices(seed=1, **kwargs)
