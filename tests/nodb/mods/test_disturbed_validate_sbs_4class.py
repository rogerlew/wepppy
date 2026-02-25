from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pytest
from osgeo import gdal, osr

import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
from wepppy.nodb.mods.disturbed import Disturbed

pytestmark = pytest.mark.unit


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
