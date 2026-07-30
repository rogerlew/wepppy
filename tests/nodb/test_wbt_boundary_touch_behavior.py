from __future__ import annotations

from contextlib import nullcontext
import logging

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.core import (
    WatershedBoundaryTouchesEdgeError as PublicBoundaryError,
    watershed_mixins,
)
from wepppy.nodb.core.watershed import Watershed
from wepppy.nodb.core.watershed_errors import (
    WATERSHED_BOUNDARY_TOUCH_MESSAGE,
    WatershedBoundaryTouchesEdgeError,
)
from wepppy.nodb.redis_prep import TaskEnum
from wepppy.topo.watershed_abstraction.support import identify_edge_hillslopes
from wepppy.topo.topaz import (
    WatershedBoundaryTouchesEdgeError as TopazBoundaryError,
)

pytestmark = pytest.mark.unit


def _write_raster(path, data: np.ndarray) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        transform=from_origin(0, data.shape[0], 1, 1),
        nodata=-9999,
    ) as dst:
        dst.write(data, 1)


def test_identify_edge_hillslopes_is_positive_unique_and_deterministic(tmp_path) -> None:
    raster = tmp_path / "subwta.tif"
    data = np.array(
        [
            [3, 3, 0, 2],
            [4, 99, 99, -9999],
            [4, 99, 99, 2],
            [1, 1, -4, 2],
        ],
        dtype=np.int32,
    )
    _write_raster(raster, data)

    result = identify_edge_hillslopes(str(raster))

    assert sorted(int(value) for value in result) == [1, 2, 3, 4]


class _Prep:
    def __init__(self) -> None:
        self.removed: list[TaskEnum] = []
        self.written: list[TaskEnum] = []

    def remove_timestamp(self, task: TaskEnum) -> None:
        self.removed.append(task)

    def timestamp(self, task: TaskEnum) -> None:
        self.written.append(task)


class _Wbt:
    def __init__(self, subwta, edges: list[int]) -> None:
        self.subwta = subwta
        self.edges = edges

    def delineate_subcatchments(self, _logger) -> None:
        self.subwta.write_bytes(b"new-raster")


class _Watershed(watershed_mixins.WatershedOperationsMixin):
    class_name = "Watershed"

    def __init__(self, wd, behavior: str, edges: list[int]) -> None:
        self.wd = str(wd)
        self.subwta = wd / "subwta.tif"
        self.wbt_boundary_touch_behavior = behavior
        self._edge_hillslopes = []
        self._wbt_test = _Wbt(self.subwta, edges)
        self.logger = logging.getLogger(f"wbt-boundary-{behavior}")

    def islocked(self) -> bool:
        return False

    def locked(self):
        return nullcontext()

    @property
    def delineation_backend_is_topaz(self) -> bool:
        return False

    @property
    def delineation_backend_is_wbt(self) -> bool:
        return True

    def _ensure_wbt(self):
        return self._wbt_test

    def identify_edge_hillslopes(self) -> None:
        self._edge_hillslopes = sorted(set(self._wbt_test.edges))


def test_wbt_warn_keeps_raster_replaces_edge_ids_and_completes(
    tmp_path,
    monkeypatch,
    caplog,
) -> None:
    prep = _Prep()
    monkeypatch.setattr(
        watershed_mixins.RedisPrep,
        "getInstance",
        lambda _wd: prep,
    )
    watershed = _Watershed(tmp_path, "warn", [3, 1, 3])
    watershed.subwta.write_bytes(b"stale")

    with caplog.at_level(logging.WARNING):
        watershed.build_subcatchments()

    assert watershed.subwta.read_bytes() == b"new-raster"
    assert watershed.edge_hillslopes == [1, 3]
    assert prep.removed == [
        TaskEnum.build_subcatchments,
        TaskEnum.abstract_watershed,
    ]
    assert prep.written == [TaskEnum.build_subcatchments]
    assert (
        f"{WATERSHED_BOUNDARY_TOUCH_MESSAGE} Edge hillslope IDs: [1, 3]."
        in caplog.text
    )


def test_wbt_error_removes_raster_and_leaves_tasks_incomplete(
    tmp_path,
    monkeypatch,
) -> None:
    prep = _Prep()
    monkeypatch.setattr(
        watershed_mixins.RedisPrep,
        "getInstance",
        lambda _wd: prep,
    )
    watershed = _Watershed(tmp_path, "error", [2, 1, 2])
    watershed.subwta.write_bytes(b"stale")

    with pytest.raises(WatershedBoundaryTouchesEdgeError) as exc_info:
        watershed.build_subcatchments()

    assert str(exc_info.value) == WATERSHED_BOUNDARY_TOUCH_MESSAGE
    assert exc_info.value.edge_hillslope_ids == [1, 2]
    assert watershed.edge_hillslopes == [1, 2]
    assert not watershed.subwta.exists()
    assert prep.written == []


def test_wbt_no_edge_completes_without_warning(tmp_path, monkeypatch, caplog) -> None:
    prep = _Prep()
    monkeypatch.setattr(watershed_mixins.RedisPrep, "getInstance", lambda _wd: prep)
    watershed = _Watershed(tmp_path, "error", [])

    with caplog.at_level(logging.WARNING):
        watershed.build_subcatchments()

    assert watershed.subwta.exists()
    assert watershed.edge_hillslopes == []
    assert prep.written == [TaskEnum.build_subcatchments]
    assert WATERSHED_BOUNDARY_TOUCH_MESSAGE not in caplog.text


def test_wbt_boundary_behavior_setter_rejects_invalid_value(tmp_path) -> None:
    watershed = _Watershed(tmp_path, "warn", [])

    with pytest.raises(ValueError, match="Invalid wbt_boundary_touch_behavior"):
        Watershed.wbt_boundary_touch_behavior.fset(watershed, "stop")  # type: ignore[union-attr]


def test_legacy_config_baseline_is_read_only_until_explicitly_persisted() -> None:
    class _LegacyWatershed(Watershed):
        def config_get_str(self, section, option, default):
            assert (section, option, default) == (
                "watershed.wbt",
                "boundary_touch_behavior",
                "warn",
            )
            return "error"

        def locked(self):
            return nullcontext()

    watershed = object.__new__(_LegacyWatershed)
    baseline_property = Watershed.wbt_boundary_touch_config_behavior
    assert baseline_property.fget is not None

    assert baseline_property.fget(watershed) == "error"
    assert not hasattr(watershed, "_wbt_boundary_touch_config_behavior")

    assert Watershed.persist_wbt_boundary_touch_config_behavior(watershed) == "error"
    assert watershed._wbt_boundary_touch_config_behavior == "error"


def test_wbt_pre_detection_failure_replaces_stale_edge_ids(
    tmp_path,
    monkeypatch,
) -> None:
    prep = _Prep()
    monkeypatch.setattr(watershed_mixins.RedisPrep, "getInstance", lambda _wd: prep)
    watershed = _Watershed(tmp_path, "error", [])
    watershed._edge_hillslopes = [7, 9]

    def _fail_before_raster(_logger) -> None:
        raise RuntimeError("conditioning failed before edge detection")

    watershed._wbt_test.delineate_subcatchments = _fail_before_raster

    with pytest.raises(RuntimeError, match="before edge detection"):
        watershed.build_subcatchments()

    assert watershed.edge_hillslopes == []
    assert not watershed.subwta.exists()
    assert prep.removed == [
        TaskEnum.build_subcatchments,
        TaskEnum.abstract_watershed,
    ]
    assert prep.written == []


def test_boundary_exception_has_one_canonical_runtime_identity() -> None:
    assert PublicBoundaryError is TopazBoundaryError
    assert PublicBoundaryError is WatershedBoundaryTouchesEdgeError

    try:
        raise TopazBoundaryError([4, 2, 4])
    except PublicBoundaryError as exc:
        assert exc.edge_hillslope_ids == [2, 4]
        assert str(exc) == WATERSHED_BOUNDARY_TOUCH_MESSAGE
