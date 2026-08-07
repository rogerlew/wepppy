from contextlib import nullcontext
from types import SimpleNamespace

import numpy as np
import pytest

from wepppy.nodb.mods.baer.baer import Baer
from wepppy.nodb.mods.disturbed.disturbed import Disturbed


pytestmark = pytest.mark.unit


class _FakeController:
    class_name = "FakeController"
    wd = "/synthetic/run"
    logger = SimpleNamespace(info=lambda *_args, **_kwargs: None)
    watershed_instance = SimpleNamespace(bound="synthetic-bound.tif")

    def locked(self):
        return nullcontext()


class _FakeSbs:
    def __init__(self, data, valid):
        self.data = np.asarray(data, dtype=np.uint8)
        self.source_valid_mask = np.asarray(valid, dtype=np.bool_)


@pytest.mark.parametrize("controller_cls", [Baer, Disturbed])
def test_sbs_coverage_excludes_masked_cells(monkeypatch, controller_cls):
    bounds = np.ones((2, 2), dtype=np.float64)
    sbs = _FakeSbs(
        [[130, 131], [132, 130]],
        [[True, True], [True, False]],
    )
    controller = _FakeController()

    if controller_cls is Baer:
        monkeypatch.setattr(
            "wepppy.nodb.mods.baer.baer.Watershed.getInstance",
            lambda _wd: SimpleNamespace(bound="synthetic-bound.tif"),
        )
        monkeypatch.setattr("wepppy.nodb.mods.baer.baer.read_raster", lambda _path: (bounds, None, None))
    else:
        monkeypatch.setattr(
            "wepppy.nodb.mods.disturbed.disturbed.read_raster",
            lambda _path: (bounds, None, None),
        )

    controller_cls._calc_sbs_coverage(controller, sbs)

    assert controller.sbs_coverage == {
        "noburn": pytest.approx(1 / 3),
        "low": pytest.approx(1 / 3),
        "moderate": pytest.approx(1 / 3),
        "high": 0.0,
    }


@pytest.mark.parametrize("controller_cls", [Baer, Disturbed])
def test_sbs_coverage_all_masked_is_four_zeros(monkeypatch, controller_cls):
    bounds = np.ones((1, 2), dtype=np.float64)
    sbs = _FakeSbs([[130, 130]], [[False, False]])
    controller = _FakeController()

    if controller_cls is Baer:
        monkeypatch.setattr(
            "wepppy.nodb.mods.baer.baer.Watershed.getInstance",
            lambda _wd: SimpleNamespace(bound="synthetic-bound.tif"),
        )
        monkeypatch.setattr("wepppy.nodb.mods.baer.baer.read_raster", lambda _path: (bounds, None, None))
    else:
        monkeypatch.setattr(
            "wepppy.nodb.mods.disturbed.disturbed.read_raster",
            lambda _path: (bounds, None, None),
        )

    controller_cls._calc_sbs_coverage(controller, sbs)

    assert controller.sbs_coverage == {
        "noburn": 0.0,
        "low": 0.0,
        "moderate": 0.0,
        "high": 0.0,
    }


def test_baer_color_table_uses_usgs_rgba_and_transparent_nodata(tmp_path):
    color_table_path = tmp_path / "baer-color-table.txt"
    controller = SimpleNamespace(
        breaks=[0, 1, 2, 3],
        class_map=[
            (0, "No Burn", 1),
            (1, "Low Severity Burn", 1),
            (2, "Moderate Severity Burn", 1),
            (3, "High Severity Burn", 1),
        ],
        color_tbl_path=str(color_table_path),
    )

    Baer.write_color_table(controller)

    assert color_table_path.read_text().splitlines() == [
        "0 0 128 128 255",
        "1 82 204 204 255",
        "2 255 232 32 255",
        "3 168 0 0 255",
        "nv 255 255 255 0",
    ]


def test_baer_color_map_generation_requests_alpha(monkeypatch, tmp_path):
    baer_wgs = tmp_path / "baer.wgs.tif"
    color_table_path = tmp_path / "color-table.txt"
    baer_rgb = tmp_path / "baer.rgb.vrt"
    baer_png = tmp_path / "baer.wgs.rgba.png"
    baer_wgs.touch()
    color_table_path.touch()
    commands = []

    class _Process:
        def __init__(self, cmd, **_kwargs):
            commands.append(cmd)
            open(cmd[-1], "a").close()

        def wait(self):
            return 0

    monkeypatch.setattr("wepppy.nodb.mods.baer.baer.Popen", _Process)
    controller = SimpleNamespace(
        baer_rgb=str(baer_rgb),
        baer_rgb_png=str(baer_png),
        baer_wgs=str(baer_wgs),
        color_tbl_path=str(color_table_path),
    )

    Baer.build_color_map(controller)

    assert commands[0][:5] == ["gdaldem", "color-relief", "-of", "VRT", "-alpha"]
