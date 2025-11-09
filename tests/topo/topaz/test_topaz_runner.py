from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import pytest
from osgeo import gdal, osr

from wepppy.all_your_base.geo import get_utm_zone
from wepppy.topo.topaz import TopazRunner

gdal.UseExceptions()

_TRUE_VALUES = {"1", "true", "yes", "on"}
_TOPAZ_FLAG = "TOPAZ_INTEGRATION"
_RUN_TOPAZ = os.getenv(_TOPAZ_FLAG, "").strip().lower() in _TRUE_VALUES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not _RUN_TOPAZ,
        reason="Set TOPAZ_INTEGRATION=1 to run the TOPAZ integration tests.",
    ),
]

DATA_DIR = Path(__file__).parent
DEM_DIR = DATA_DIR / "dems"
VERIFY_DIR = DATA_DIR / "verify"


def _make_runner(tmp_path: Path, dem_name: str = "ned1_2016.tif") -> Tuple[TopazRunner, Path]:
    wd = tmp_path / "wd"
    wd.mkdir()
    runner = TopazRunner(str(wd), str(DEM_DIR / dem_name))
    return runner, wd


def _assert_same_file(actual: Path, expected: Path) -> None:
    assert actual.exists(), f"Missing generated file: {actual}"
    assert expected.exists(), f"Missing fixture file: {expected}"
    assert actual.read_bytes() == expected.read_bytes(), f"{actual} differed from {expected}"


@pytest.mark.parametrize(
    ("dem_name", "expected_zone"),
    [
        ("ned1_2016_lg.tif", 10),
        ("ned1_2016.tif", 11),
        ("ned1_2016_ny.tif", 17),
    ],
)
def test_get_utm_zone_extracts_expected_zone(dem_name: str, expected_zone: int) -> None:
    ds = gdal.Open(str(DEM_DIR / dem_name))
    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjectionRef())
    _, zone, _ = get_utm_zone(srs)
    assert zone == expected_zone


def test_get_utm_zone_returns_none_for_non_utm_dataset() -> None:
    ds = gdal.Open(str(DEM_DIR / "nonutm.tif"))
    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjectionRef())
    _, zone, _ = get_utm_zone(srs)
    assert zone is None


def test_get_utm_zone_requires_spatial_reference() -> None:
    with pytest.raises(TypeError):
        get_utm_zone("not-a-spatial-reference")  # type: ignore[arg-type]


def test_topaz_runner_initializes_expected_metadata(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path)
    assert runner.cellsize == 30.0
    assert runner.ul_x == 504090
    assert runner.ul_y == 5185161
    assert runner.lr_x == 506700
    assert runner.lr_y == 5180991
    assert runner.num_cols == 87
    assert runner.num_rows == 139
    assert runner.utm_zone == 11


def test_create_dednm_input_matches_fixture(tmp_path: Path) -> None:
    runner, wd = _make_runner(tmp_path)
    runner._create_dednm_input()
    _assert_same_file(wd / "DEDNM.INP", VERIFY_DIR / "DEDNM.INP")


def test_create_dnmcnt_input_matches_fixture(tmp_path: Path) -> None:
    runner, wd = _make_runner(tmp_path)
    runner._create_dnmcnt_input(1)
    _assert_same_file(wd / "DNMCNT.INP", VERIFY_DIR / "DNMCNT.INP")


def test_prep_dir_creates_expected_structure(tmp_path: Path) -> None:
    runner, wd = _make_runner(tmp_path)
    runner._prep_dir()

    for subdir in ("dednm", "rasbin", "raspro", "rasfor"):
        path = wd / subdir
        assert path.is_dir()

    assert (wd / "RASFOR.INP").exists()
    assert (wd / "RASPRO.INP").exists()


def test_build_channels_generates_expected_arc_files(tmp_path: Path) -> None:
    runner, wd = _make_runner(tmp_path)
    runner.build_channels()

    for name in ("NETFUL.ARC", "FLOPAT.ARC", "FLOVEC.ARC", "RELIEF.ARC"):
        assert (wd / name).exists()

    _assert_same_file(wd / "NETFUL.ARC", VERIFY_DIR / "NETFUL.ARC.1")
    _assert_same_file(wd / "NETFUL.PRJ", VERIFY_DIR / "NETFUL.PRJ.1")


def test_lnglat_to_pixel_inside_extent(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path)
    lng = -(116.0 + 55.0 / 60.0 + 45.50 / 3600.0)
    lat = 46.0 + 48.0 / 60.0 + 4.37 / 3600.0
    x, y = runner.lnglat_to_pixel(lng, lat)
    assert (x, y) == (43, 69)


def test_lnglat_to_pixel_raises_for_out_of_bounds_point(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path)
    with pytest.raises(AssertionError):
        runner.lnglat_to_pixel(-120.0, 20.0)


def test_lnglat_to_pixel_returns_precise_channel(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path)
    x, y = runner.lnglat_to_pixel(-116.9310440300905, 46.81997312092958)
    assert (x, y) == (39, 0)


@pytest.mark.parametrize(
    ("pixel", "expected"),
    [
        ((0, 0), (504090, 5185161)),
        ((43, 70), (505380.0, 5183061.0)),
        ((86, 138), (506670, 5181021)),
    ],
)
def test_pixel_to_utm_converts_coordinates(tmp_path: Path, pixel: Tuple[int, int], expected: Tuple[float, float]) -> None:
    runner, _ = _make_runner(tmp_path)
    runner.build_channels()
    assert runner.pixel_to_utm(*pixel) == expected


def test_pixel_to_utm_rejects_out_of_range_values(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path)
    runner.build_channels()
    with pytest.raises(AssertionError):
        runner.pixel_to_utm(86, 139)
    with pytest.raises(AssertionError):
        runner.pixel_to_utm(87, 138)


@pytest.mark.parametrize(
    ("pixel", "expected"),
    [
        ((0, 0), (-116.94638213722368, 46.819981333488265)),
        ((43, 70), (-116.92949559048503, 46.80107414405755)),
        ((86, 138), (-116.91261999321354, 46.78270435450583)),
        ((39, 0), (-116.9310440300905, 46.81997312092958)),
    ],
)
def test_pixel_to_lnglat_converts_back_to_geographic(tmp_path: Path, pixel: Tuple[int, int], expected: Tuple[float, float]) -> None:
    runner, _ = _make_runner(tmp_path)
    runner.build_channels()
    assert runner.pixel_to_lnglat(*pixel) == expected


def test_find_closest_channel_from_pixel_coords(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path)
    runner.build_channels()
    (x, y), distance = runner.find_closest_channel(44, 38, pixelcoords=True)
    assert (x, y) == (44, 38)
    assert distance == 0


def test_find_closest_channel_from_pixel_coords_off_channel(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path)
    runner.build_channels()
    (x, y), distance = runner.find_closest_channel(23, 47, pixelcoords=True)
    assert (x, y) == (21, 48)
    assert distance == pytest.approx(2.2360679775)


def test_find_closest_channel_from_geographic_point(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path)
    runner.build_channels()
    (x, y), distance = runner.find_closest_channel(-116.9310440300905, 46.81997312092958)
    assert (x, y) == (39, 0)
    assert distance == 0


def test_find_closest_channel_writes_chjnt_arc(tmp_path: Path) -> None:
    runner, wd = _make_runner(tmp_path)
    runner.build_channels()
    runner.find_closest_channel(-116.9310440300905, 46.81997312092958)
    _assert_same_file(wd / "CHNJNT.ARC", VERIFY_DIR / "CHNJNT.ARC.1")


def test_build_subcatchments_matches_fixtures(tmp_path: Path) -> None:
    runner, wd = _make_runner(tmp_path)
    runner.build_channels()
    runner.build_subcatchments([26, 5])

    required = [
        "BOUND.ARC",
        "FLOPAT.ARC",
        "FLOVEC.ARC",
        "FVSLOP.ARC",
        "NETW.ARC",
        "SUBWTA.ARC",
    ]
    for name in required:
        assert (wd / name).exists()

    _assert_same_file(wd / "FVSLOP.ARC", VERIFY_DIR / "FVSLOP.ARC.2")
    _assert_same_file(wd / "SUBWTA.ARC", VERIFY_DIR / "SUBWTA.ARC.2")
    _assert_same_file(wd / "FLOPAT.ARC", VERIFY_DIR / "FLOPAT.ARC.2")


def test_build_channels_scales_to_larger_tile(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path, dem_name="ned1_2016_lg3.tif")
    runner.build_channels()  # Should complete without hanging


def test_build_subcatchments_raises_when_outside_boundary(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path)
    with pytest.raises(Exception):
        runner.build_subcatchments([50, 135])
