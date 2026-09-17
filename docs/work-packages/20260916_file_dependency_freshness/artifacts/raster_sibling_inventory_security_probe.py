"""Evaluate explicit GDAL discovery sibling lists; actual native calls only."""
import errno
import json
import os
from pathlib import Path

from osgeo import gdal
import pytest

from raster_implementation_security_probe import raster, warped, http_fixture
from wepppy.all_your_base import raster_freshness as freshness

pytestmark = pytest.mark.integration


def sibling_names(path):
    return [os.path.basename(path), *[
        os.path.basename(member) for member, suffix in freshness._companions(path)
        if suffix in freshness._ORDINARY and os.path.dirname(member) == os.path.dirname(path)
    ]]


def retain(name, result):
    record = {"case": name, "gdal": gdal.VersionInfo(), **result}
    Path(__file__).with_name(f"raster_sibling_inventory_{name}.json").write_text(json.dumps(record, indent=2)+"\n")
    print("SIBLING_INVENTORY " + json.dumps(record))


@pytest.mark.parametrize("driver", ["GTiff", "AAIGrid"])
@pytest.mark.parametrize("suffix", [".msk", ".ovr"])
@pytest.mark.parametrize("replacement", [False, True])
def test_discovery_sibling_authority(tmp_path, monkeypatch, driver, suffix, replacement):
    source = tmp_path / ("source.asc" if driver == "AAIGrid" else "source.tif")
    child = tmp_path / "child.tif"
    raster(source, driver)
    raster(child)
    auxiliary = Path(str(source)+suffix)
    raster(auxiliary)
    original = gdal.OpenEx
    calls = []
    changed = False
    with http_fixture(tmp_path) as (remote, requests):
        if not replacement:
            auxiliary.unlink()
            warped(auxiliary, child, remote)

        def bounded_open(path, *args, **kwargs):
            nonlocal changed
            names = sibling_names(path)
            if replacement and str(path) == str(source) and not changed:
                changed = True
                staged = tmp_path / "replacement.vrt"
                warped(staged, child, remote)
                os.replace(staged, auxiliary)
            calls.append({"path": os.path.basename(path), "siblings": names})
            return original(path, *args, sibling_files=names, **kwargs)

        monkeypatch.setattr(gdal, "OpenEx", bounded_open)
        error = None
        try:
            result = freshness.raster_dependency_signature(source)
        except OSError as exc:
            result = None
            error = {"errno": exc.errno, "message": str(exc)}
        name = f"{driver}_{suffix[1:]}_{'replacement' if replacement else 'stationary'}"
        retain(name, {"requests": requests, "calls": calls, "unverified": result is None, "error": error})
        assert result is None
        assert not requests
        if replacement:
            assert changed
            assert error and error["errno"] == errno.ESTALE


@pytest.mark.parametrize("kind", ["gtiff_plain", "aaigrid_prj", "gtiff_world", "gtiff_local_mask", "gtiff_local_overview"])
def test_local_ordinary_inventory_and_geometry(tmp_path, kind):
    driver = "AAIGrid" if kind.startswith("aaigrid") else "GTiff"
    source = tmp_path / ("source.asc" if driver == "AAIGrid" else "source.tif")
    raster(source, driver)
    if kind == "gtiff_world":
        source.unlink()
        dataset = gdal.GetDriverByName("GTiff").Create(str(source), 4, 4, 1, gdal.GDT_Byte)
        dataset.GetRasterBand(1).Fill(1)
        dataset = None
        source.with_suffix(".tfw").write_text("30\n0\n0\n-30\n500015\n4999985\n")
    if kind == "gtiff_local_mask":
        raster(Path(str(source)+".msk"))
    if kind == "gtiff_local_overview":
        raster(Path(str(source)+".ovr"))
    states = []
    for restricted in [False, True]:
        kwargs = {"sibling_files": sibling_names(str(source))} if restricted else {}
        dataset = gdal.OpenEx(str(source), gdal.OF_RASTER | gdal.OF_READONLY,
                              allowed_drivers=["GTiff", "AAIGrid"], **kwargs)
        states.append({"restricted": restricted, "members": dataset.GetFileList(),
                       "transform": dataset.GetGeoTransform(), "projection": dataset.GetProjection()})
        dataset = None
    retain(kind, {"states": states, "siblings": sibling_names(str(source))})
    assert states[0]["transform"] == states[1]["transform"]
    assert states[0]["projection"] == states[1]["projection"]
    if kind not in ("gtiff_local_mask", "gtiff_local_overview"):
        assert states[0]["members"] == states[1]["members"]
    else:
        assert states[1]["members"] == [str(source)]
