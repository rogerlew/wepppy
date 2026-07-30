from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from wepppy.topo.wbt.wbt_topaz_emulator import (
    TOPAZ_CONDITION_MAX_OBSTRUCTION_WIDTH,
    TOPAZ_CONDITION_TIMEOUT_SECONDS,
    WhiteboxToolsTopazEmulator,
)

pytestmark = pytest.mark.unit


class _ConditioningRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _record(self, method: str, kwargs: dict[str, Any]) -> int:
        self.calls.append((method, kwargs))
        Path(kwargs["output"]).touch()
        return 0

    def fill_depressions(self, **kwargs: Any) -> int:
        return self._record("fill_depressions", kwargs)

    def breach_depressions(self, **kwargs: Any) -> int:
        return self._record("breach_depressions", kwargs)

    def breach_depressions_least_cost(self, **kwargs: Any) -> int:
        return self._record("breach_depressions_least_cost", kwargs)

    def topaz_condition_dem(self, **kwargs: Any) -> int:
        return self._record("topaz_condition_dem", kwargs)


def _emulator(tmp_path: Path, runner: _ConditioningRunner) -> WhiteboxToolsTopazEmulator:
    dem = tmp_path / "dem.tif"
    dem.touch()
    emulator = object.__new__(WhiteboxToolsTopazEmulator)
    emulator.wbt_wd = str(tmp_path)
    emulator._dem = str(dem)
    emulator._wbt_runner = runner
    emulator._flovec_netful_relief_are_vrt = False
    emulator._build_hooks = {}
    emulator.verbose = False
    emulator.cellsize = 30.0
    return emulator


def test_topaz_conditioning_dispatch_pins_width_and_timeout(tmp_path: Path) -> None:
    runner = _ConditioningRunner()
    emulator = _emulator(tmp_path, runner)

    emulator._create_relief(fill_or_breach="topaz")

    assert runner.calls == [
        (
            "topaz_condition_dem",
            {
                "dem": str(tmp_path / "dem.tif"),
                "output": str(tmp_path / "relief.tif"),
                "max_obstruction_width": TOPAZ_CONDITION_MAX_OBSTRUCTION_WIDTH,
                "timeout": TOPAZ_CONDITION_TIMEOUT_SECONDS,
            },
        )
    ]
    assert TOPAZ_CONDITION_MAX_OBSTRUCTION_WIDTH == 2
    assert TOPAZ_CONDITION_TIMEOUT_SECONDS == 540


@pytest.mark.parametrize(
    ("mode", "method"),
    (
        ("fill", "fill_depressions"),
        ("breach", "breach_depressions"),
        ("breach_least_cost", "breach_depressions_least_cost"),
    ),
)
def test_legacy_conditioning_dispatch_is_preserved(
    tmp_path: Path,
    mode: str,
    method: str,
) -> None:
    runner = _ConditioningRunner()
    emulator = _emulator(tmp_path, runner)

    emulator._create_relief(fill_or_breach=mode, blc_dist=900)

    assert [call[0] for call in runner.calls] == [method]
