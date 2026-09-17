"""Small real GDAL/filesystem probes; loopback only, disposable inputs."""
from contextlib import contextmanager
import errno
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading

from osgeo import gdal, osr
import pytest

from wepppy.all_your_base import raster_freshness as freshness

pytestmark = pytest.mark.integration


def raster(path, driver="GTiff", value=1):
    memory = gdal.GetDriverByName("MEM").Create("", 4, 4, 1, gdal.GDT_Byte)
    memory.SetGeoTransform((500000, 30, 0, 5000000, 0, -30))
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32611)
    memory.SetProjection(spatial.ExportToWkt())
    memory.GetRasterBand(1).Fill(value)
    dataset = gdal.GetDriverByName(driver).CreateCopy(str(path), memory)
    dataset = None
    memory = None


def warped(path, child, remote):
    dataset = gdal.Warp(str(path), str(child), format="VRT", dstSRS="EPSG:4326")
    dataset = None
    xml = path.read_text()
    start = xml.index("<SourceDataset")
    end = xml.index("</SourceDataset>", start) + len("</SourceDataset>")
    xml = xml[:start] + f'<SourceDataset relativeToVRT="0">{remote}</SourceDataset>' + xml[end:]
    path.write_text(xml)


@contextmanager
def http_fixture(root):
    requests = []

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, format, *args):
            pass

        def do_HEAD(self):
            requests.append({"method": "HEAD", "path": self.path})
            return super().do_HEAD()

        def do_GET(self):
            requests.append({"method": "GET", "path": self.path})
            return super().do_GET()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"/vsicurl/http://127.0.0.1:{server.server_address[1]}/child.tif", requests
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def retain(name, result):
    record = {"case": name, "gdal": gdal.VersionInfo(), "uid": os.geteuid(), **result}
    Path(__file__).with_name(f"raster_implementation_security_{name}.json").write_text(
        json.dumps(record, indent=2) + "\n")
    print("RASTER_SECURITY " + json.dumps(record))


@pytest.mark.parametrize("kind", ["vrt", "mask", "overview", "internal", "alias_mask", "stem_uppercase", "aaigrid_mask"])
def test_preflight_has_no_remote_discovery(tmp_path, kind):
    child = tmp_path / "child.tif"
    raster(child)
    source = tmp_path / ("source.asc" if kind == "aaigrid_mask" else "source.tif")
    raster(source, "AAIGrid" if kind == "aaigrid_mask" else "GTiff")
    selected = source
    with http_fixture(tmp_path) as (remote, requests):
        if kind == "vrt":
            selected = tmp_path / "root.vrt"
            warped(selected, child, remote)
        elif kind == "internal":
            dataset = gdal.Open(str(source), gdal.GA_Update)
            dataset.SetMetadataItem("OVERVIEW_FILE", remote, "OVERVIEWS")
            dataset = None
        else:
            companion = Path(str(source) + (".ovr" if kind == "overview" else ".msk"))
            if kind == "stem_uppercase":
                companion = tmp_path / "SOURCE.MSK"
            if kind == "alias_mask":
                alias_parent = tmp_path / "aliases"
                alias_parent.mkdir()
                selected = alias_parent / "visible.tif"
                selected.symlink_to(source)
            warped(companion, child, remote)
        signature = freshness.raster_dependency_signature(selected)
        retain(kind, {"unverified": signature is None, "requests": requests})
        assert signature is None
        assert requests == []


@pytest.mark.parametrize("key,value", [
    ("GDAL_PAM_PROXY_DIR", "/unused-review-proxy"),
    ("GDAL_PAM_ENABLED", "NO"),
    ("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR"),
    ("GDAL_READDIR_LIMIT_ON_OPEN", "0"),
    ("GDAL_GEOREF_SOURCES", "INTERNAL"),
    ("USE_RRD", "YES"),
    ("TIFF_USE_OVR", "TRUE"),
])
def test_effective_thread_configuration_is_not_mutated(tmp_path, monkeypatch, key, value):
    source = tmp_path / "source.tif"
    raster(source)
    previous = gdal.GetThreadLocalConfigOption(key)
    calls = []
    original = gdal.OpenEx
    monkeypatch.setattr(gdal, "OpenEx", lambda *args, **kwargs: (calls.append(args), original(*args, **kwargs))[1])
    try:
        gdal.SetThreadLocalConfigOption(key, value)
        assert freshness.raster_dependency_signature(source) is None
        assert gdal.GetThreadLocalConfigOption(key) == value
        assert calls == []
    finally:
        gdal.SetThreadLocalConfigOption(key, previous)


def test_source_alias_retarget_and_same_bytes(tmp_path):
    source = tmp_path / "source.tif"
    other = tmp_path / "other.tif"
    raster(source)
    other.write_bytes(source.read_bytes())
    selected = tmp_path / "selected.tif"
    selected.symlink_to(source)
    first = freshness.raster_dependency_signature(selected)
    assert first is not None
    selected.unlink()
    selected.symlink_to(other)
    second = freshness.raster_dependency_signature(selected)
    assert second is not None
    assert first != second


@pytest.mark.parametrize("kind", ["file_denied", "directory_execute_only"])
def test_access_preserves_native_boundary(tmp_path, kind):
    from wepppy.nodb.mods.baer import sbs_map
    assert os.geteuid() != 0, "real mode test requires ordinary container identity"
    directory = tmp_path / "data"
    directory.mkdir()
    source = directory / "source.tif"
    raster(source)
    accepted = sbs_map._summarize_sbs_raster(str(source))
    assert accepted is not None
    target, mode = (source, 0) if kind == "file_denied" else (directory, 0o111)
    before = target.stat().st_mode & 0o777
    target.chmod(mode)
    try:
        assert freshness.raster_dependency_signature(source) is None
        if kind == "file_denied":
            with pytest.raises(RuntimeError) as direct:
                sbs_map._summarize_sbs_raster_rust(str(source))
            with pytest.raises(type(direct.value)) as wrapped:
                sbs_map._summarize_sbs_raster(str(source))
            assert str(direct.value) == str(wrapped.value)
        else:
            assert sbs_map._summarize_sbs_raster(str(source)) == accepted
    finally:
        target.chmod(before)


def test_auxiliary_replacement_between_preflight_and_inventory(tmp_path, monkeypatch):
    source, child = tmp_path / "source.tif", tmp_path / "child.tif"
    raster(source)
    raster(child)
    mask = Path(str(source) + ".msk")
    raster(mask)
    original = gdal.OpenEx
    changed = False
    with http_fixture(tmp_path) as (remote, requests):
        def open_after_companion_change(path, *args, **kwargs):
            nonlocal changed
            if str(path) == str(source) and not changed:
                changed = True
                replacement = tmp_path / "replacement.vrt"
                warped(replacement, child, remote)
                os.replace(replacement, mask)
            return original(path, *args, **kwargs)
        monkeypatch.setattr(gdal, "OpenEx", open_after_companion_change)
        error = None
        try:
            result = freshness.raster_dependency_signature(source)
        except OSError as exc:
            result = None
            error = {"type": type(exc).__name__, "errno": exc.errno, "message": str(exc)}
        retain("preflight_replacement", {"requests": requests, "unverified": result is None, "error": error})
        assert changed
        assert result is None
        # Characterize discovery authority before the final rejection, not a
        # success condition for the implementation. This retains the finding.
        assert requests
