from pathlib import Path

import pytest
from osgeo import gdal

from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap


pytestmark = pytest.mark.integration


def test_rattlesnake_fixture_converts_to_real_png_and_vrt(tmp_path: Path) -> None:
    source = Path("tests/sbs_map/data/Rattlesnake.tif").resolve()
    wgs = tmp_path / "Rattlesnake.wgs.tif"
    png = tmp_path / "baer.wgs.rgba.png"
    vrt = tmp_path / "Rattlesnake.wgs.rgb.vrt"

    sbs = SoilBurnSeverityMap(str(source))
    sbs.export_wgs_map(str(wgs))
    sbs.export_rgb_map(str(wgs), str(vrt), str(png))

    png_dataset = gdal.Open(str(png))
    vrt_dataset = gdal.Open(str(vrt))
    assert png_dataset is not None
    assert png_dataset.RasterCount == 4
    assert vrt_dataset is not None
    assert vrt_dataset.RasterCount == 4
    png_dataset = None
    vrt_dataset = None
