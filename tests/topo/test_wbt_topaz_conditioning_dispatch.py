from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from whitebox_tools import WhiteboxAppError

import wepppy.topo.wbt.wbt_topaz_emulator as wbt_topaz_emulator_module
from wepppy.topo.wbt.wbt_topaz_emulator import (
    TOPAZ_CONDITION_MAX_OBSTRUCTION_WIDTH,
    TOPAZ_CONDITION_TIMEOUT_SECONDS,
    WBT_UNRESOLVED_DEPRESSION_MESSAGE,
    WbtUnresolvedDepressionsError,
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


def test_least_cost_fail_fast_dispatch_disables_fill(tmp_path: Path) -> None:
    runner = _ConditioningRunner()
    emulator = _emulator(tmp_path, runner)

    emulator._create_relief(
        fill_or_breach="breach_least_cost",
        blc_dist=1000,
        blc_fill=False,
        blc_fail_on_unresolved=True,
    )

    assert runner.calls == [
        (
            "breach_depressions_least_cost",
            {
                "dem": str(tmp_path / "dem.tif"),
                "output": str(tmp_path / "relief.tif"),
                "dist": 33,
                "fill": False,
                "fail_on_unresolved": True,
            },
        )
    ]


def test_native_unresolved_error_is_translated_without_output(tmp_path: Path) -> None:
    class _UnresolvedRunner(_ConditioningRunner):
        def breach_depressions_least_cost(self, **kwargs: Any) -> int:
            self.calls.append(("breach_depressions_least_cost", kwargs))
            raise WhiteboxAppError(
                'Error: Custom { kind: InvalidData, error: '
                '"WBT_UNRESOLVED_DEPRESSIONS count=377 max_dist_cells=33" }'
            )

    runner = _UnresolvedRunner()
    emulator = _emulator(tmp_path, runner)

    with pytest.raises(WbtUnresolvedDepressionsError) as exc_info:
        emulator._create_relief(
            fill_or_breach="breach_least_cost",
            blc_dist=1000,
            blc_fill=False,
            blc_fail_on_unresolved=True,
        )

    assert exc_info.value.unresolved_depression_count == 377
    assert exc_info.value.search_distance_m == 1000
    assert exc_info.value.search_distance_cells == 33
    assert str(exc_info.value) == WBT_UNRESOLVED_DEPRESSION_MESSAGE
    assert not (tmp_path / "relief.tif").exists()


def test_fail_fast_and_fill_cannot_both_be_enabled(tmp_path: Path) -> None:
    emulator = _emulator(tmp_path, _ConditioningRunner())

    with pytest.raises(ValueError, match="cannot both be enabled"):
        emulator._create_relief(
            fill_or_breach="breach_least_cost",
            blc_fill=True,
            blc_fail_on_unresolved=True,
        )


def test_conditioning_failure_cleanup_removes_stale_channel_products(
    tmp_path: Path,
) -> None:
    emulator = _emulator(tmp_path, _ConditioningRunner())
    artifact_paths = (
        emulator.relief,
        emulator.flovec,
        emulator.flovec_wgs,
        emulator.floaccum,
        emulator.netful0,
        emulator.netful,
        emulator.netful_json,
        emulator.netful_wgs_json,
        emulator.chnjnt,
    )
    for artifact_path in artifact_paths:
        Path(artifact_path).touch()

    emulator._remove_stale_channel_products_after_conditioning_failure()

    assert all(not Path(artifact_path).exists() for artifact_path in artifact_paths)


def test_unresolved_channel_build_cleans_stale_products_and_allows_retry(
    tmp_path: Path,
) -> None:
    class _RetryRunner(_ConditioningRunner):
        def breach_depressions_least_cost(self, **kwargs: Any) -> int:
            self.calls.append(("breach_depressions_least_cost", kwargs))
            raise WhiteboxAppError(
                'Error: Custom { kind: InvalidData, error: '
                '"WBT_UNRESOLVED_DEPRESSIONS count=3 max_dist_cells=33" }'
            )

    emulator = _emulator(tmp_path, _RetryRunner())
    stale_paths = (
        emulator.flovec,
        emulator.floaccum,
        emulator.netful,
        emulator.netful_json,
        emulator.chnjnt,
    )
    for artifact_path in stale_paths:
        Path(artifact_path).touch()

    with pytest.raises(WbtUnresolvedDepressionsError):
        emulator.delineate_channels(
            csa=5.0,
            mcl=60.0,
            stream_pruning_method="ifolp",
            fill_or_breach="breach_least_cost",
            blc_dist=1000,
        )

    assert all(not Path(artifact_path).exists() for artifact_path in stale_paths)

    retry_runner = _ConditioningRunner()
    emulator._wbt_runner = retry_runner
    emulator._create_relief(fill_or_breach="fill")

    assert Path(emulator.relief).exists()
    assert retry_runner.calls[0][0] == "fill_depressions"


def test_channel_delineation_enables_least_cost_fail_fast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emulator = _emulator(tmp_path, _ConditioningRunner())
    captured: dict[str, Any] = {}

    def _record_relief(fill_or_breach: str, **kwargs: Any) -> None:
        captured["fill_or_breach"] = fill_or_breach
        captured.update(kwargs)

    emulator._create_relief = _record_relief  # type: ignore[method-assign]
    emulator._create_flow_vector = lambda **_kwargs: None  # type: ignore[method-assign]
    emulator._create_flow_accumulation = lambda **_kwargs: None  # type: ignore[method-assign]
    emulator._extract_streams = lambda **_kwargs: None  # type: ignore[method-assign]
    emulator._identify_stream_junctions = lambda **_kwargs: None  # type: ignore[method-assign]
    monkeypatch.setattr(wbt_topaz_emulator_module, "polygonize_netful", lambda *_args: None)
    monkeypatch.setattr(wbt_topaz_emulator_module, "json_to_wgs", lambda *_args: None)

    emulator.delineate_channels(
        csa=5.0,
        mcl=60.0,
        stream_pruning_method="ifolp",
        fill_or_breach="breach_least_cost",
        blc_dist=1000,
    )

    assert captured["blc_fill"] is False
    assert captured["blc_fail_on_unresolved"] is True
