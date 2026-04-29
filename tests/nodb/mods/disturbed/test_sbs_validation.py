from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pytest
import rasterio
from osgeo import gdal, osr

import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
from wepppy.all_your_base.geo import raster_stacker
from wepppy.nodb.base import redis_lock_client
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.baer.sbs_map import get_sbs_color_table
from wepppy.nodb.mods.disturbed import Disturbed

pytestmark = pytest.mark.nodb


class _NoopLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return

    def log(self, *_args: object, **_kwargs: object) -> None:
        return


@contextmanager
def _null_context() -> None:
    yield


def _write_uint8_tif(path: Path, values: np.ndarray) -> None:
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(path), values.shape[1], values.shape[0], 1, gdal.GDT_Byte)
    assert ds is not None
    ds.SetGeoTransform((500000.0, 30.0, 0.0, 5200000.0, 0.0, -30.0))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32610)
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    band.SetNoDataValue(255)
    band.WriteArray(values)
    band.FlushCache()
    ds = None


def _disturbed_stub(run_dir: Path) -> Disturbed:
    disturbed = Disturbed.__new__(Disturbed)
    disturbed.wd = str(run_dir)
    disturbed.logger = _NoopLogger()
    disturbed._sbs_mode = 0
    disturbed._uniform_severity = None
    return disturbed


@pytest.mark.unit
def test_validate_exports_sbs_4class_with_source_dimensions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    disturbed_dir = run_dir / "disturbed"
    disturbed_dir.mkdir(parents=True)

    source = disturbed_dir / "source.tif"
    source_values = np.array(
        [
            [0, 1, 2, 3, 255],
            [3, 2, 1, 0, 255],
            [1, 2, 3, 0, 255],
        ],
        dtype=np.uint8,
    )
    _write_uint8_tif(source, source_values)

    disturbed = _disturbed_stub(run_dir)

    monkeypatch.setattr(Disturbed, "locked", lambda self, validate_on_success=True: _null_context())
    monkeypatch.setattr(Disturbed, "timed", lambda self, task_name, level=20: _null_context())
    monkeypatch.setattr(disturbed_module, "validate_srs", lambda _path: True)
    monkeypatch.setattr(
        disturbed_module.SoilBurnSeverityMap,
        "export_wgs_map",
        lambda self, fn: [[0.0, 0.0], [1.0, 1.0]],
    )
    monkeypatch.setattr(
        disturbed_module.SoilBurnSeverityMap,
        "export_rgb_map",
        lambda self, wgs_fn, fn, rgb_png: None,
    )
    monkeypatch.setattr(
        disturbed_module.RedisPrep,
        "getInstance",
        staticmethod(lambda _wd: (_ for _ in ()).throw(FileNotFoundError())),
    )

    disturbed.validate("source.tif", mode=0)

    sbs_4class = disturbed_dir / "sbs_4class.tif"
    assert sbs_4class.exists()

    src_ds = gdal.Open(str(source))
    out_ds = gdal.Open(str(sbs_4class))
    assert src_ds is not None
    assert out_ds is not None

    assert out_ds.RasterXSize == src_ds.RasterXSize
    assert out_ds.RasterYSize == src_ds.RasterYSize

    src_ds = None
    out_ds = None


class _PrepRecorder:
    def __init__(self) -> None:
        self.timestamps: list[object] = []
        self.has_sbs: bool | None = None

    def timestamp(self, task: object) -> None:
        self.timestamps.append(task)


@pytest.mark.unit
def test_validate_updates_landuse_and_sbs_prep_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    disturbed_dir = run_dir / "disturbed"
    disturbed_dir.mkdir(parents=True)

    source = disturbed_dir / "source.tif"
    source_values = np.array(
        [
            [0, 1, 2, 3, 255],
            [3, 2, 1, 0, 255],
            [1, 2, 3, 0, 255],
        ],
        dtype=np.uint8,
    )
    _write_uint8_tif(source, source_values)

    disturbed = _disturbed_stub(run_dir)
    prep = _PrepRecorder()

    monkeypatch.setattr(Disturbed, "locked", lambda self, validate_on_success=True: _null_context())
    monkeypatch.setattr(Disturbed, "timed", lambda self, task_name, level=20: _null_context())
    monkeypatch.setattr(disturbed_module, "validate_srs", lambda _path: True)
    monkeypatch.setattr(
        disturbed_module.SoilBurnSeverityMap,
        "export_wgs_map",
        lambda self, fn: [[0.0, 0.0], [1.0, 1.0]],
    )
    monkeypatch.setattr(
        disturbed_module.SoilBurnSeverityMap,
        "export_rgb_map",
        lambda self, wgs_fn, fn, rgb_png: None,
    )
    monkeypatch.setattr(
        disturbed_module.RedisPrep,
        "getInstance",
        staticmethod(lambda _wd: prep),
    )

    disturbed.validate("source.tif", mode=0)

    assert prep.timestamps == [
        disturbed_module.TaskEnum.landuse_map,
        disturbed_module.TaskEnum.init_sbs_map,
    ]
    assert prep.has_sbs is True


# Uses an existing integration run when available.
TEST_RUN_DIR = "/wc1/runs/le/legato-alkalinity"


@pytest.fixture
def disturbed_instance():
    if not os.path.exists(TEST_RUN_DIR):
        pytest.skip(f"Test run directory {TEST_RUN_DIR} not found")

    disturbed = Disturbed.getInstance(TEST_RUN_DIR)
    yield disturbed

    if redis_lock_client is not None:
        try:
            redis_lock_client.delete(disturbed._distributed_lock_key)  # type: ignore[attr-defined]
        except Exception:
            pass
    Disturbed._instances.clear()


@pytest.mark.integration
class TestUniformSBSGeneration:
    @pytest.mark.parametrize(
        "severity_value,expected_pixel",
        [
            (1, 1),
            (2, 2),
            (3, 3),
        ],
    )
    def test_uniform_sbs_pixel_values(self, disturbed_instance, severity_value, expected_pixel):
        sbs_fn = disturbed_instance.build_uniform_sbs(value=severity_value)

        with rasterio.open(sbs_fn) as src:
            data = src.read(1)
            unique_vals = np.unique(data)

        assert len(unique_vals) == 1
        assert unique_vals[0] == expected_pixel

    @pytest.mark.parametrize(
        "severity_value,expected_color",
        [
            (1, (127, 255, 212, 255)),
            (2, (255, 255, 0, 255)),
            (3, (255, 0, 0, 255)),
        ],
    )
    def test_uniform_sbs_color_table(self, disturbed_instance, severity_value, expected_color):
        sbs_fn = disturbed_instance.build_uniform_sbs(value=severity_value)

        ds = gdal.Open(sbs_fn, gdal.GA_ReadOnly)
        band = ds.GetRasterBand(1)
        ct = band.GetRasterColorTable()

        assert ct is not None

        actual_color = ct.GetColorEntry(severity_value)

        assert actual_color == expected_color

        band = None
        ds = None

    def test_uniform_sbs_all_standard_colors(self, disturbed_instance):
        sbs_fn = disturbed_instance.build_uniform_sbs(value=1)

        ds = gdal.Open(sbs_fn, gdal.GA_ReadOnly)
        band = ds.GetRasterBand(1)
        ct = band.GetRasterColorTable()

        expected_entries = {
            0: (0, 100, 0, 255),
            1: (127, 255, 212, 255),
            2: (255, 255, 0, 255),
            3: (255, 0, 0, 255),
            255: (255, 255, 255, 0),
        }

        for pixel_val, expected_color in expected_entries.items():
            actual_color = ct.GetColorEntry(pixel_val)
            assert actual_color == expected_color

        band = None
        ds = None


@pytest.mark.integration
class TestColorTablePreservation:
    def test_raster_stacker_preserves_color_table(self, tmp_path, disturbed_instance):
        sbs_fn = disturbed_instance.build_uniform_sbs(value=1)

        ron = Ron.getInstance(disturbed_instance.wd)
        dem_fn = ron.dem_fn

        cropped_fn = os.path.join(tmp_path, "cropped.tif")
        raster_stacker(sbs_fn, dem_fn, cropped_fn, resample="near")

        ct_src, _, _ = get_sbs_color_table(sbs_fn)
        ct_dst, _, _ = get_sbs_color_table(cropped_fn)

        assert ct_src is not None
        assert ct_dst is not None
        assert ct_src == ct_dst

    def test_get_sbs_preserves_color_table(self, disturbed_instance):
        sbs_fn = disturbed_instance.build_uniform_sbs(value=2)
        disturbed_instance.validate(sbs_fn, mode=1, uniform_severity=2)

        sbs = disturbed_instance.get_sbs()

        assert sbs.ct is not None

        cropped_fn = disturbed_instance.disturbed_cropped
        ct, _, _ = get_sbs_color_table(cropped_fn)
        assert ct is not None


@pytest.mark.integration
class TestBurnClassAssignment:
    @pytest.mark.parametrize(
        "severity_value,expected_burn_class",
        [
            (1, "131"),
            (2, "132"),
            (3, "133"),
        ],
    )
    def test_class_pixel_map_correct(self, disturbed_instance, severity_value, expected_burn_class):
        disturbed_instance.build_uniform_sbs(value=severity_value)
        sbs_map = disturbed_instance.get_sbs()
        class_pixel_map = sbs_map.class_pixel_map

        pixel_str = str(severity_value)
        assert pixel_str in class_pixel_map

        actual_burn_class = class_pixel_map[pixel_str]
        assert actual_burn_class == expected_burn_class

    def test_uniform_low_not_assigned_high(self, disturbed_instance):
        sbs_fn = disturbed_instance.build_uniform_sbs(value=1)
        disturbed_instance.validate(sbs_fn, mode=1, uniform_severity=1)

        sbs = disturbed_instance.get_sbs()
        class_pixel_map = sbs.class_pixel_map

        assert "1" in class_pixel_map
        assert class_pixel_map["1"] == "131"
        assert class_pixel_map["1"] != "133"

    def test_uniform_moderate_not_assigned_high(self, disturbed_instance):
        sbs_fn = disturbed_instance.build_uniform_sbs(value=2)
        disturbed_instance.validate(sbs_fn, mode=1, uniform_severity=2)

        sbs = disturbed_instance.get_sbs()
        class_pixel_map = sbs.class_pixel_map

        assert "2" in class_pixel_map
        assert class_pixel_map["2"] == "132"
        assert class_pixel_map["2"] != "133"


@pytest.mark.integration
class TestSBSModeAndUniformSeverity:
    def test_sbs_mode_set_to_uniform(self, disturbed_instance):
        disturbed_instance.build_uniform_sbs(value=1)
        assert disturbed_instance.sbs_mode == 1

    @pytest.mark.parametrize("severity_value", [1, 2, 3])
    def test_uniform_severity_set_correctly(self, disturbed_instance, severity_value):
        disturbed_instance.build_uniform_sbs(value=severity_value)
        assert disturbed_instance.uniform_severity == severity_value

    def test_validate_preserves_mode_and_severity(self, disturbed_instance):
        severity_value = 2
        sbs_fn = disturbed_instance.build_uniform_sbs(value=severity_value)
        disturbed_instance.validate(sbs_fn, mode=1, uniform_severity=severity_value)

        assert disturbed_instance.sbs_mode == 1
        assert disturbed_instance.uniform_severity == severity_value
