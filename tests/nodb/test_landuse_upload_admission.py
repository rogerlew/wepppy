import logging
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.core.landuse import Landuse, UserDefinedLanduseIncompatible
from wepppy.rq.landuse_upload_attempt import LanduseUploadAttempt
from wepppy.wepp.management import load_map

pytestmark = pytest.mark.unit


def _raster(path, values, nodata):
    array = np.array(values, dtype="int16")
    with rasterio.open(
        path, "w", driver="GTiff", height=array.shape[0], width=array.shape[1], count=1,
        dtype="int16", crs="EPSG:32631", transform=from_origin(500000, 4500000, 5, 5),
        nodata=nodata,
    ) as raster:
        raster.write(array, 1)
    return path


@pytest.fixture
def landuse_with_geometry(monkeypatch, tmp_path):
    landuse = object.__new__(Landuse)
    watershed = SimpleNamespace(
        is_abstracted=True,
        subs_summary={"11": {}, "21": {}},
        subwta=str(_raster(tmp_path / "subwta.tif", [[11, 11, 11], [21, 21, 21]], -1)),
        mofe_map=str(_raster(tmp_path / "mofe.tif", [[1, 1, 2], [1, 1, 2]], -1)),
        mofe_nsegments={"11": 2, "21": 2},
    )
    monkeypatch.setattr(Landuse, "watershed_instance", property(lambda self: watershed))
    monkeypatch.setattr(Landuse, "multi_ofe", property(lambda self: False))
    monkeypatch.setattr(Landuse, "mods", property(lambda self: ("disturbed",)))
    landuse.logger = logging.getLogger(__name__)
    monkeypatch.setattr(Landuse, "_resolve_effective_mapping_reference", lambda self, name: name)
    monkeypatch.setattr(Landuse, "get_mapping_dict", lambda self, **kw: load_map(kw["upload_mapping"]))
    return landuse


def test_native_hillslope_class_must_have_a_management(landuse_with_geometry, tmp_path):
    raster = _raster(tmp_path / "uploaded.tif", [[25, 25, 25], [23, 23, 23]], -1)
    landuse_with_geometry.inspect_user_defined_raster(
        raster, mapping="eu-disturbed", dataset=None, buffer_code=None,
    )
    raster = _raster(tmp_path / "uploaded.tif", [[999, 999, 999], [23, 23, 23]], -1)
    with pytest.raises(UserDefinedLanduseIncompatible, match="Unmapped land-use codes: 999"):
        landuse_with_geometry.inspect_user_defined_raster(
            raster, mapping="eu-disturbed", dataset=None, buffer_code=None,
        )


def test_native_mofe_class_is_checked_when_it_is_not_hillslope_dominant(
    landuse_with_geometry, monkeypatch, tmp_path,
):
    monkeypatch.setattr(Landuse, "multi_ofe", property(lambda self: True))
    raster = _raster(tmp_path / "uploaded.tif", [[25, 25, 999], [23, 23, 23]], -1)
    with pytest.raises(UserDefinedLanduseIncompatible, match="Unmapped land-use codes: 999"):
        landuse_with_geometry.inspect_user_defined_raster(
            raster, mapping="eu-disturbed", dataset=None, buffer_code=None,
        )


def test_aligned_nodata_rejects_uncovered_hill_and_preserves_genuine_code_zero(
    landuse_with_geometry, tmp_path,
):
    raw = _raster(tmp_path / "raw.tif", [[0, 0, 0]], None)
    raster = tmp_path / "aligned.tif"
    landuse_with_geometry.align_user_defined_raster(raw, landuse_with_geometry.watershed_instance.subwta, raster)
    with rasterio.open(raster) as aligned:
        assert aligned.read(1)[0].tolist() == [0, 0, 0]
        assert aligned.read_masks(1)[1].tolist() == [0, 0, 0]
    with pytest.raises(UserDefinedLanduseIncompatible, match="1 modeled hillslopes"):
        landuse_with_geometry.inspect_user_defined_raster(
            raster, mapping="eu-disturbed", dataset=None, buffer_code=None,
        )


def test_nodata_only_mofe_is_rejected_before_native_mode_fallback(
    landuse_with_geometry, monkeypatch, tmp_path,
):
    monkeypatch.setattr(Landuse, "multi_ofe", property(lambda self: True))
    raster = _raster(tmp_path / "uploaded.tif", [[25, 25, -1], [23, 23, 23]], -1)
    with pytest.raises(UserDefinedLanduseIncompatible, match="modeled OFE segments on 1 hillslopes"):
        landuse_with_geometry.inspect_user_defined_raster(
            raster, mapping="eu-disturbed", dataset=None, buffer_code=None,
        )


def test_snapshot_rejects_changed_raw_receipt_or_alignment(tmp_path):
    attempt = LanduseUploadAttempt(tmp_path, "fixture-run", str(uuid4()), "cover.tif")
    attempt.create()
    attempt.raw.write_bytes(b"raw input")
    attempt.aligned.write_bytes(b"aligned input")
    receipt_hash = attempt.record({"mapping": "eu-disturbed"})
    with attempt.snapshot(receipt_hash) as accepted:
        assert accepted.raw.read_bytes() == b"raw input"
        assert accepted.aligned.read_bytes() == b"aligned input"

    attempt.aligned.write_bytes(b"changed input")
    with pytest.raises(ValueError, match="staged land-use raster changed"):
        with attempt.snapshot(receipt_hash):
            pytest.fail("changed alignment reached publication")

    receipt = attempt.directory / "build-status.json"
    receipt.write_bytes(receipt.read_bytes() + b" ")
    with pytest.raises(ValueError, match="receipt changed"):
        with attempt.snapshot(receipt_hash):
            pytest.fail("changed receipt reached publication")


def test_attempt_does_not_follow_a_run_artifact_symlink(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "landuse_artifacts").symlink_to(outside, target_is_directory=True)
    attempt = LanduseUploadAttempt(tmp_path, "fixture-run", str(uuid4()), "cover.tif")
    with pytest.raises(OSError):
        attempt.create()
    assert list(outside.iterdir()) == []


def test_valid_managed_landuse_projection_and_external_link(tmp_path):
    run = tmp_path / "run"
    managed = run / ".nodir/upper/landuse/token/data"
    managed.mkdir(parents=True)
    active = run / "landuse"
    active.symlink_to(managed, target_is_directory=True)

    landuse = object.__new__(Landuse)
    landuse.wd = str(run)
    assert landuse.user_defined_raster_destination() == active

    outside = tmp_path / "outside"
    outside.mkdir()
    active.unlink()
    active.symlink_to(outside, target_is_directory=True)
    with pytest.raises(UserDefinedLanduseIncompatible, match="run-owned land-use directory"):
        landuse.user_defined_raster_destination()


def test_compact_receipt_can_retry_from_verified_applied_inputs(tmp_path):
    attempt = LanduseUploadAttempt(tmp_path, "fixture-run", str(uuid4()), "cover.tif")
    attempt.create()
    attempt.raw.write_bytes(b"raw input")
    attempt.aligned.write_bytes(b"aligned input")
    receipt_hash = attempt.record({"mapping": "eu-disturbed"})

    applied = tmp_path / "landuse"
    applied.mkdir()
    (applied / "_cover.tif").write_bytes(attempt.raw.read_bytes())
    (applied / "nlcd.tif").write_bytes(attempt.aligned.read_bytes())
    attempt.remove_completed_rasters()
    assert not attempt.raw.exists() and not attempt.aligned.exists()
    with attempt.snapshot(receipt_hash, applied=applied) as accepted:
        assert accepted.raw.read_bytes() == b"raw input"
        assert accepted.aligned.read_bytes() == b"aligned input"

    (applied / "_cover.tif").write_bytes(b"not the admitted source")
    with pytest.raises(ValueError, match="staged land-use raster changed"):
        with attempt.snapshot(receipt_hash, applied=applied):
            pytest.fail("a different applied source reached publication")
