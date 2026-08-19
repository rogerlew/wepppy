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


def test_sample_pixel_indices_skips_empty_valid_strata() -> None:
    valid_cells = {
        0: [(0, 0), (0, 1)],
        3: [(3, 3), (3, 4)],
    }

    samples = _MODULE._sample_pixel_indices(
        4,
        4,
        4,
        seed=20260819,
        strata=(2, 2),
        valid_cells_by_stratum=valid_cells,
    )

    assert len(samples) == 4
    assert set(samples) == set(valid_cells[0] + valid_cells[3])


def test_inspect_sol_detects_nonordered_horizons(tmp_path: Path) -> None:
    sol_path = tmp_path / "invalid.sol"
    sol_path.write_text(
        "1200 1.4 28 1 0.1 0.05 25 30 5 15 10\n"
        "600 1.4 28 1 0.1 0.05 25 30 5 15 10\n",
        encoding="utf-8",
    )

    assert _MODULE._inspect_sol(sol_path) == ["sol.horizon_depth_order"]


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
