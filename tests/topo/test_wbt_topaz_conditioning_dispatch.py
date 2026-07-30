from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import pytest
from whitebox_tools import WhiteboxAppError

import wepppy.topo.wbt.wbt_topaz_emulator as wbt_topaz_emulator_module
from wepppy.topo.wbt.wbt_topaz_emulator import (
    TOPAZ_CONDITION_MAX_OBSTRUCTION_WIDTH,
    TOPAZ_CONDITION_TIMEOUT_SECONDS,
    WBT_UNRESOLVED_DEPRESSION_MESSAGE,
    WbtConditioningDiagnosticsError,
    WbtUnresolvedDepressionsError,
    WhiteboxToolsTopazEmulator,
    load_conditioning_diagnostics,
)

pytestmark = pytest.mark.unit


class _ConditioningRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _record(self, method: str, kwargs: dict[str, Any]) -> int:
        self.calls.append((method, kwargs))
        Path(kwargs["output"]).touch()
        tool = {
            "fill_depressions": "FillDepressions",
            "breach_depressions": "BreachDepressions",
            "breach_depressions_least_cost": "BreachDepressionsLeastCost",
            "topaz_condition_dem": "TopazConditionDem",
        }[method]
        conditioning = {
            "fill_depressions": {
                "detected_low_point_count": 0, "filled_depression_count": 0,
                "skipped_depression_count": 0, "flat_gradient_applied": True,
            },
            "breach_depressions": {
                "breached_depression_count": 0, "longest_breach_path_cells": 0,
                "longest_breach_path": 0.0, "single_cell_pits_filled": 0,
                "residual_fill_used": False, "residual_depression_count": 0,
            },
            "breach_depressions_least_cost": {
                "detected_low_point_count": 0, "resolved_low_point_count": 0,
                "unresolved_low_point_count": 0, "longest_breach_path_cells": 0,
                "longest_breach_path": 0.0, "fallback_fill_used": False,
                "fallback_filled_low_point_count": 0,
            },
            "topaz_condition_dem": {
                "depression_count": 0, "flat_count": 0, "filled_cell_count": 0,
                "lowered_cell_count": 0, "synthetic_relief_cell_count": 0,
                "obstruction_adjustments_width_1": 0,
                "obstruction_adjustments_width_2": 0, "maximum_fildep_fill": 0.0,
                "maximum_fildep_cut": 0.0, "maximum_synthetic_relief": 0.0,
            },
        }[method]
        parameters = {
            "fill_depressions": {"fix_flats": True, "flat_increment": 0.0, "max_depth": None},
            "breach_depressions": {"fill_pits": True, "flat_increment": 0.0, "max_depth": None, "max_length_cells": None},
            "breach_depressions_least_cost": {"search_distance_cells": 1, "search_distance": 30.0, "max_cost": None, "minimize_distance": False, "flat_increment": 0.0, "fill": False, "fail_on_unresolved": True},
            "topaz_condition_dem": {"max_obstruction_width": 2},
        }[method]
        Path(kwargs["diagnostics"]).write_text(json.dumps({
            "schema_version": 1,
            "tool": tool,
            "status": "success",
            "operation_id": kwargs["diagnostics_id"],
            "input_name": Path(kwargs["dem"]).name,
            "output_name": Path(kwargs["output"]).name,
            "units": {"elevation": "m", "horizontal": "m", "area": "m2", "volume": "m3"},
            "terrain_change": {
                "valid_cell_count": 1,
                "raised_cell_count": 0,
                "lowered_cell_count": 0,
                "raised_area": 0.0,
                "lowered_area": 0.0,
                "maximum_raise": 0.0,
                "maximum_cut": 0.0,
                "fill_volume": 0.0,
                "cut_volume": 0.0,
            },
            "conditioning": conditioning,
            "parameters": parameters,
        }), encoding="utf-8")
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

    assert runner.calls[0][0] == "topaz_condition_dem"
    kwargs = runner.calls[0][1]
    assert kwargs["dem"] == str(tmp_path / "dem.tif")
    assert kwargs["output"] == str(tmp_path / "relief.tif")
    assert kwargs["max_obstruction_width"] == TOPAZ_CONDITION_MAX_OBSTRUCTION_WIDTH
    assert kwargs["timeout"] == TOPAZ_CONDITION_TIMEOUT_SECONDS
    assert kwargs["diagnostics"] == str(tmp_path / "relief.diagnostics.json")
    assert len(kwargs["diagnostics_id"]) == 32
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

    assert runner.calls[0][0] == "breach_depressions_least_cost"
    kwargs = runner.calls[0][1]
    assert kwargs["dem"] == str(tmp_path / "dem.tif")
    assert kwargs["output"] == str(tmp_path / "relief.tif")
    assert kwargs["dist"] == 33
    assert kwargs["fill"] is False
    assert kwargs["fail_on_unresolved"] is True
    assert kwargs["diagnostics"] == str(tmp_path / "relief.diagnostics.json")
    assert len(kwargs["diagnostics_id"]) == 32


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


def test_missing_diagnostics_removes_native_output(tmp_path: Path) -> None:
    class _MissingDiagnosticsRunner(_ConditioningRunner):
        def fill_depressions(self, **kwargs: Any) -> int:
            self.calls.append(("fill_depressions", kwargs))
            Path(kwargs["output"]).touch()
            return 0

    emulator = _emulator(tmp_path, _MissingDiagnosticsRunner())

    with pytest.raises(WbtConditioningDiagnosticsError):
        emulator._create_relief(fill_or_breach="fill")

    assert not Path(emulator.relief).exists()
    assert not Path(emulator.conditioning_diagnostics).exists()


@pytest.mark.parametrize("mutation", ["unknown", "inconsistent"])
def test_conditioning_diagnostics_reject_invalid_schema(
    tmp_path: Path,
    mutation: str,
) -> None:
    emulator = _emulator(tmp_path, _ConditioningRunner())
    emulator._create_relief(fill_or_breach="fill")
    sidecar = Path(emulator.conditioning_diagnostics)
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    if mutation == "unknown":
        payload["unexpected"] = True
    else:
        payload["terrain_change"]["raised_cell_count"] = 2
    sidecar.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(WbtConditioningDiagnosticsError):
        load_conditioning_diagnostics(
            str(sidecar),
            method="fill",
            operation_id=payload["operation_id"],
            input_name=emulator.dem,
            output_name=emulator.relief,
        )


def test_conditioning_diagnostics_reject_duplicate_keys(tmp_path: Path) -> None:
    sidecar = tmp_path / "relief.diagnostics.json"
    sidecar.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")

    with pytest.raises(WbtConditioningDiagnosticsError):
        load_conditioning_diagnostics(
            str(sidecar),
            method="fill",
            operation_id=None,
            input_name="dem.tif",
            output_name="relief.tif",
        )


def test_conditioning_diagnostics_reject_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    sidecar = tmp_path / "relief.diagnostics.json"
    sidecar.symlink_to(target)

    with pytest.raises(WbtConditioningDiagnosticsError, match="could not be verified"):
        load_conditioning_diagnostics(
            str(sidecar),
            method="fill",
            operation_id=None,
            input_name="dem.tif",
            output_name="relief.tif",
        )


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
