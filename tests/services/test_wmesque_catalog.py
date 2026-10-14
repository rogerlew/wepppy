from __future__ import annotations

import json
import multiprocessing
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import numpy as np
from osgeo import gdal, osr
import pytest
from fastapi.testclient import TestClient

from wepppy.webservices import wmesque_catalog as catalog
from wepppy.webservices import wmesque2

pytestmark = pytest.mark.integration


def make_dataset(root, name="test/map", value=7):
    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    raster = gdal.GetDriverByName("GTiff").Create(str(path / "tile.tif"), 8, 8, 1, gdal.GDT_Byte)
    raster.SetGeoTransform((500000, 30, 0, 5100240, 0, -30))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32611)
    raster.SetProjection(srs.ExportToWkt())
    raster.GetRasterBand(1).WriteArray(np.full((8, 8), value, dtype=np.uint8))
    raster = None
    gdal.BuildVRT(str(path / ".vrt"), [str(path / "tile.tif")])
    (path / "metadata.json").write_text(json.dumps({"source": "fixture"}))
    return path


def test_publish_sync_adoption_and_legacy(tmp_path, monkeypatch):
    master, replica = tmp_path / "master", tmp_path / "replica"
    master.mkdir(); replica.mkdir()
    make_dataset(master)
    make_dataset(replica, value=3)
    make_dataset(replica, "local/only", 9)
    first = catalog.publish_dataset(master, "test/map")
    old_source, old_rev = catalog.resolve_dataset(master, "test/map")
    assert old_rev == first["revision"]
    before = (replica / "test/map/tile.tif").read_bytes()
    dry = catalog.sync_catalog(str(master), replica, dry_run=True)
    assert dry["updates"] == {"test/map": first["revision"]}
    assert catalog.read_catalog(replica)["datasets"] == {}
    catalog.sync_catalog(str(master), replica)
    current, revision = catalog.resolve_dataset(replica, "test/map")
    assert revision == first["revision"]
    assert gdal.Open(str(current)).ReadAsArray()[0, 0] == 7
    assert (replica / "test/map/tile.tif").read_bytes() == before
    assert catalog.resolve_dataset(replica, "local/only")[1] is None
    assert catalog.sync_catalog(str(master), replica)["updates"] == {}
    make_dataset(master, value=11)
    second = catalog.publish_dataset(master, "test/map")
    assert first["revision"] != second["revision"]
    assert gdal.Open(str(old_source)).ReadAsArray()[0, 0] == 7
    catalog.sync_catalog(str(master), replica)
    assert gdal.Open(str(catalog.resolve_dataset(replica, "test/map")[0])).ReadAsArray()[0, 0] == 11
    # Existing unversioned clients retain logical catalog paths, not release internals.
    legacy = tmp_path / "catalog.txt"
    legacy.write_text(str(replica / "test/map/.vrt") + "\n")
    monkeypatch.setattr(wmesque2, "geodata_dir", str(replica))
    monkeypatch.setattr(wmesque2, "_catalog", str(legacy))
    with TestClient(wmesque2.app) as client:
        assert client.get("/catalog").json() == [str(replica / "test/map/.vrt")]
        assert client.get("/catalog/manifest").json()["datasets"]["test/map"] == second["revision"]
        params = {"bbox": "500000,5100000,500240,5100240", "bbox_crs": "EPSG:32611", "cellsize": 30}
        assert client.get("/retrieve/test/map", params={**params, "expected_revision": first["revision"]}).status_code == 409
        response = client.get("/retrieve/test/map", params=params)
        assert response.status_code == 200
        assert wmesque2.from_b64url(response.headers["WMesque-Meta"])["wmesque"]["revision"] == second["revision"]
        out = tmp_path / "response.tif"
        out.write_bytes(response.content)
        assert np.all(gdal.Open(str(out)).ReadAsArray() == 11)


def test_nested_sibling_dependencies_and_stable_revision(tmp_path):
    root = tmp_path / "root"; root.mkdir()
    path = make_dataset(root, "tiles/source")
    entry = root / "composite/map"; entry.mkdir(parents=True)
    gdal.BuildVRT(str(entry / ".vrt"), [str(path / ".vrt")])
    one = catalog.publish_dataset(root, "composite/map")
    two = catalog.publish_dataset(root, "composite/map")
    assert one == two
    assert any(".." in node.text for node in ET.parse(catalog.resolve_dataset(root, "composite/map")[0]).iter("SourceFilename"))


def test_unavailable_legacy_source_is_retryable_server_failure(tmp_path, monkeypatch):
    root = tmp_path / "root"
    path = make_dataset(root)
    (path / "tile.tif").unlink()
    monkeypatch.setattr(wmesque2, "geodata_dir", str(root))
    with TestClient(wmesque2.app) as client:
        response = client.get("/retrieve/test/map", params={
            "bbox": "500000,5100000,500240,5100240", "bbox_crs": "EPSG:32611",
            "cellsize": 30, "resample": "near"})
    assert response.status_code == 500
    assert "gdalwarp failed" in response.json()["detail"]["Error"]


@pytest.mark.parametrize("option", ["resample", "gdaldem", "format"])
def test_invalid_processing_option_is_not_retryable(option, monkeypatch):
    monkeypatch.setattr(wmesque2, "resolve_dataset", lambda *args: pytest.fail("Validate options before source IO"))
    with TestClient(wmesque2.app) as client:
        response = client.get("/retrieve/test/map", params={
            "bbox": "500000,5100000,500240,5100240", "bbox_crs": "EPSG:32611",
            "cellsize": 30, option: "not-a-valid-option"})
    assert response.status_code == 400


def test_external_source_rejected_before_gdal(tmp_path, monkeypatch):
    root = tmp_path / "root"; root.mkdir()
    make_dataset(root)
    manifest = catalog.publish_dataset(root, "test/map")
    release = root / ".wmesque/releases" / manifest["revision"]
    entry = release / manifest["entrypoint"]
    tree = ET.parse(entry)
    tree.find(".//SourceFilename").text = "/vsicurl/https://example.invalid/data.tif"
    tree.write(entry)
    for item in manifest["files"]:
        p = release / item["path"]
        item.update(size=p.stat().st_size, sha256=catalog._hash(p))
    manifest["revision"] = __import__('hashlib').sha256(catalog._json_bytes({k:v for k,v in manifest.items() if k != "revision"})).hexdigest()
    (release / "manifest.json").write_bytes(catalog._json_bytes(manifest))
    monkeypatch.setattr(gdal, "Open", lambda *a, **k: pytest.fail("GDAL must not open hostile dependencies"))
    with pytest.raises(ValueError, match="virtual/network"):
        catalog.verify_release(release)


def test_corrupt_transfer_preserves_previous_catalog(tmp_path, monkeypatch):
    master, replica = tmp_path / "master", tmp_path / "replica"
    master.mkdir(); replica.mkdir()
    make_dataset(master)
    catalog.publish_dataset(master, "test/map")
    catalog.sync_catalog(str(master), replica)
    before = catalog.read_catalog(replica)
    make_dataset(master, value=12)
    catalog.publish_dataset(master, "test/map")
    original = catalog._copy
    def broken(source, relative, target):
        original(source, relative, target)
        if target.is_dir():
            next(target.rglob("tile.tif")).write_bytes(b"broken")
    monkeypatch.setattr(catalog, "_copy", broken)
    with pytest.raises(ValueError, match="integrity"):
        catalog.sync_catalog(str(master), replica)
    assert catalog.read_catalog(replica) == before
    assert json.loads((replica / ".wmesque/sync-status.json").read_text())["status"] == "failed"
    monkeypatch.setattr(catalog, "_copy", original)
    assert catalog.sync_catalog(str(master), replica)["status"] == "success"


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a/../b", "a//b", "a?b", "a\\b"])
def test_bad_ids_rejected(name):
    with pytest.raises(ValueError):
        catalog.dataset_id(name)


def test_symlink_and_lock_rejection(tmp_path):
    root = tmp_path / "root"; root.mkdir()
    make_dataset(root)
    manifest = catalog.publish_dataset(root, "test/map")
    release = root / ".wmesque/releases" / manifest["revision"]
    file = release / "data/test/map/tile.tif"
    file.unlink(); file.symlink_to(root / "test/map/tile.tif")
    with pytest.raises(ValueError, match="Symlinks"):
        catalog.verify_release(release)
    replica = tmp_path / "replica"; replica.mkdir()
    state = catalog._state(replica)
    with catalog._lock(state / "sync.lock"):
        with pytest.raises(BlockingIOError):
            catalog.sync_catalog(str(root), replica)


def test_concurrent_publish_and_sync_preserve_extensions(tmp_path):
    master, replica = tmp_path / "master", tmp_path / "replica"
    master.mkdir(); replica.mkdir()
    make_dataset(master); catalog.publish_dataset(master, "test/map")
    make_dataset(replica, "local/extension", 4)
    context = multiprocessing.get_context("fork")
    processes = [context.Process(target=catalog.sync_catalog, args=(str(master), replica)),
                 context.Process(target=catalog.publish_dataset, args=(replica, "local/extension"))]
    for process in processes: process.start()
    for process in processes:
        process.join(20)
        assert process.exitcode == 0
    assert set(catalog.read_catalog(replica)["datasets"]) == {"test/map", "local/extension"}


def test_empty_and_malformed_catalog(tmp_path):
    assert catalog.read_catalog(tmp_path)["datasets"] == {}
    state = catalog._state(tmp_path)
    (state / "catalog.json").write_text('{"schema_version":1,"datasets":{}}')
    assert catalog.read_catalog(tmp_path)["datasets"] == {}
    (state / "catalog.json").write_text('[]')
    with pytest.raises(ValueError): catalog.read_catalog(tmp_path)


def test_ssh_transfer_uses_verified_host_and_protected_arguments(tmp_path, monkeypatch):
    calls=[]
    monkeypatch.setattr(catalog.subprocess, "run", lambda args, **kwargs: calls.append((args,kwargs)))
    catalog._copy("sync@wepp1:/geodata", ".wmesque/catalog.json", tmp_path / "catalog.json")
    assert "--protect-args" in calls[0][0]
    assert "StrictHostKeyChecking=yes" in calls[0][0][6]
    assert calls[0][1]["timeout"] == 330
    with pytest.raises(ValueError): catalog._copy("-bad:/tmp", "x", tmp_path / "x")


def test_disguised_nested_vrt_cannot_escape(tmp_path):
    root = tmp_path / "root"; root.mkdir()
    make_dataset(root)
    outside = tmp_path / "outside"
    outside.mkdir()
    make_dataset(outside)
    disguised = root / "test/map/nested.bin"
    shutil.copyfile(outside / "test/map/.vrt", disguised)
    tree = ET.parse(disguised)
    node = tree.find(".//SourceFilename")
    node.text = str(outside / "test/map/tile.tif")
    node.set("relativeToVRT", "0")
    tree.write(disguised)
    entry = root / "test/map/.vrt"
    tree = ET.parse(entry)
    tree.find(".//SourceFilename").text = "nested.bin"
    tree.write(entry)
    with pytest.raises(ValueError, match="escapes"):
        catalog.publish_dataset(root, "test/map")


@pytest.mark.parametrize("dangling", [False, True])
def test_symlink_catalog_is_not_absent_or_read(tmp_path, dangling):
    root=tmp_path/"root";root.mkdir()
    target=tmp_path/"outside.json"
    if not dangling:target.write_text('{"schema_version":1,"datasets":{}}')
    catalog._state(root).joinpath("catalog.json").symlink_to(target)
    with pytest.raises(ValueError, match="Symlinks"):
        catalog.read_catalog(root)


def test_corrupt_managed_state_is_server_failure(tmp_path, monkeypatch):
    root=tmp_path/"root";root.mkdir();make_dataset(root)
    manifest=catalog.publish_dataset(root,"test/map")
    (root/".wmesque/releases"/manifest["revision"]/"manifest.json").write_text('{}')
    monkeypatch.setattr(wmesque2,"geodata_dir",str(root))
    with TestClient(wmesque2.app,raise_server_exceptions=False) as client:
        response=client.get('/retrieve/test/map',params={"bbox":"500000,5100000,500240,5100240","bbox_crs":"EPSG:32611","cellsize":30})
        assert response.status_code==500
