from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pytest
from osgeo import gdal, osr

from wepppy.all_your_base.geo import get_utm_zone
from wepppy.topo.topaz import TopazRunner

gdal.UseExceptions()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
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
        pytest.param("ned1_2016_lg.tif", 10, marks=pytest.mark.skip(reason="DEM file is corrupted")),
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
    result = get_utm_zone(srs)
    assert result is None


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


#def test_create_dednm_input_matches_fixture(tmp_path: Path) -> None:
#    runner, wd = _make_runner(tmp_path)
#    runner._create_dednm_input()
#    _assert_same_file(wd / "DEDNM.INP", VERIFY_DIR / "DEDNM.INP")


def test_create_dnmcnt_input_matches_fixture(tmp_path: Path) -> None:
    runner, wd = _make_runner(tmp_path)
    runner._create_dnmcnt_input(1)
    _assert_same_file(wd / "DNMCNT.INP", VERIFY_DIR / "DNMCNT.INP")


def test_prep_dir_creates_expected_structure(tmp_path: Path) -> None:
    runner, wd = _make_runner(tmp_path)
    runner._prep_dir()

    # _prep_dir only copies control files, not creating subdirectories
    assert (wd / "RASFOR.INP").exists()
    assert (wd / "RASPRO.INP").exists()


def test_build_channels_generates_expected_arc_files(tmp_path: Path) -> None:
    runner, wd = _make_runner(tmp_path)
    runner.build_channels()

    # Check that required files are generated
    for name in ("NETFUL.ARC", "FLOPAT.ARC", "FLOVEC.ARC", "RELIEF.ARC"):
        assert (wd / name).exists()
    
    # Check projection file exists
    assert (wd / "NETFUL.PRJ").exists()
    
    # Verify NETFUL.ARC has expected header structure
    netful_content = (wd / "NETFUL.ARC").read_text()
    assert "ncols" in netful_content
    assert "nrows" in netful_content
    assert "xllcorner" in netful_content
    assert "yllcorner" in netful_content
    assert "cellsize" in netful_content


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
    result = runner.pixel_to_lnglat(*pixel)
    assert result[0] == pytest.approx(expected[0], abs=1e-8)
    assert result[1] == pytest.approx(expected[1], abs=1e-8)


# Removed deprecated find_closest_channel tests:
# - test_find_closest_channel_from_pixel_coords
# - test_find_closest_channel_from_pixel_coords_off_channel  
# - test_find_closest_channel_from_geographic_point
# - test_find_closest_channel_writes_chjnt_arc
# The find_closest_channel method is deprecated and will be removed


def test_build_subcatchments_generates_required_files(tmp_path: Path) -> None:
    runner, wd = _make_runner(tmp_path)
    runner.build_channels()
    
    # Use find_closest_channel2 to find a valid channel outlet
    # Using an interior channel location (not on DEM edges)
    # Pixel (43, 70) is a known interior channel from the NETFUL output
    lng, lat = -116.92949559048503, 46.80107414405755
    (outlet_x, outlet_y), distance = runner.find_closest_channel2(lng, lat)
    
    # Verify we found a channel (distance should be small)
    assert distance < 100, f"No channel found within reasonable distance (distance={distance})"
    
    runner.build_subcatchments([outlet_x, outlet_y])

    # Verify all required output files are generated
    required = [
        "BOUND.ARC",
        "FLOPAT.ARC",
        "FLOVEC.ARC",
        "FVSLOP.ARC",
        "NETW.ARC",
        "SUBWTA.ARC",
    ]
    for name in required:
        assert (wd / name).exists(), f"Missing required file: {name}"
    
    # Verify files have content (not empty)
    for name in required:
        assert (wd / name).stat().st_size > 0, f"File {name} is empty"


def test_build_channels_scales_to_larger_tile(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path, dem_name="ned1_2016_lg3.tif")
    runner.build_channels()  # Should complete without hanging


def test_build_subcatchments_raises_when_outside_boundary(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path)
    with pytest.raises(Exception):
        runner.build_subcatchments([50, 135])
