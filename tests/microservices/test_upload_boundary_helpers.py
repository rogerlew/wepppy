from __future__ import annotations

import io
from pathlib import Path

import pytest

from wepppy.microservices.upload_boundary import (
    UploadBoundaryError, assert_raster_upload_identity, enforce_extension,
    prepare_filename, resolve_contained_raster_path, save_upload_from_stream,
    validate_raster_upload, write_stream_to_destination)

pytestmark = pytest.mark.microservice


def test_prepare_filename_sanitizes_and_lowercases_by_default() -> None:
    assert prepare_filename("My Raster.TIF") == "my_raster.tif"


def test_prepare_filename_rejects_empty_name() -> None:
    with pytest.raises(UploadBoundaryError, match="no filename specified"):
        prepare_filename("   ")


def test_enforce_extension_rejects_unknown_suffix() -> None:
    with pytest.raises(UploadBoundaryError, match="Invalid file extension"):
        enforce_extension("roads.json", ("geojson",))


def test_write_stream_to_destination_rejects_oversize_and_cleans_partial(tmp_path: Path) -> None:
    destination = tmp_path / "uploads" / "payload.bin"

    with pytest.raises(UploadBoundaryError, match="File exceeds maximum allowed size") as exc_info:
        write_stream_to_destination(
            io.BytesIO(b"abcdef"),
            destination,
            max_bytes=4,
        )

    assert exc_info.value.status_code == 413
    assert not destination.exists()


def test_save_upload_from_stream_cleans_file_on_post_save_failure(tmp_path: Path) -> None:
    destination_dir = tmp_path / "uploads"

    def _post_save(_path: Path) -> None:
        raise RuntimeError("post-save failed")

    with pytest.raises(RuntimeError, match="post-save failed"):
        save_upload_from_stream(
            raw_filename="roads.geojson",
            stream=io.BytesIO(b"{}"),
            dest_dir=destination_dir,
            allowed_extensions=("geojson",),
            overwrite=True,
            post_save=_post_save,
        )

    assert list(destination_dir.glob("*")) == []


@pytest.mark.parametrize('invalid', ['size', 'extension', 'content'])
def test_invalid_replacement_preserves_accepted_source(tmp_path, invalid):
    destination = tmp_path/'source.tif'
    destination.write_bytes(b'accepted source')
    def reject(path):
        assert path.read_bytes() == b'invalid input'
        raise UploadBoundaryError('Invalid source content')
    with pytest.raises(UploadBoundaryError):
        save_upload_from_stream(raw_filename='source.tif', stream=io.BytesIO(b'invalid input'),
            dest_dir=tmp_path, allowed_extensions=('txt',) if invalid=='extension' else ('tif',),
            overwrite=True, max_bytes=2 if invalid=='size' else None,
            post_save=reject if invalid=='content' else None)
    assert destination.read_bytes() == b'accepted source'
    assert list(tmp_path.iterdir()) == [destination]
    save_upload_from_stream(raw_filename='source.tif', stream=io.BytesIO(b'valid'),
                            dest_dir=tmp_path, allowed_extensions=('tif',), overwrite=True)
    assert destination.read_bytes() == b'valid'


@pytest.mark.parametrize('failure', ['seek', 'read'])
def test_stream_failure_preserves_existing_source(tmp_path, failure):
    destination = tmp_path / 'source.tif'
    destination.write_bytes(b'accepted')
    class BrokenStream(io.BytesIO):
        def seek(self, *args):
            if failure == 'seek':
                raise OSError('injected seek failure')
            return super().seek(*args)
        def read(self, *args):
            if failure == 'read':
                raise OSError('injected read failure')
            return super().read(*args)
    with pytest.raises(OSError):
        write_stream_to_destination(BrokenStream(b'replacement'), destination, overwrite=True)
    assert destination.read_bytes() == b'accepted'
    assert list(tmp_path.iterdir()) == [destination]


def test_staged_vrt_preserves_relative_raster_dependencies(tmp_path):
    from osgeo import gdal

    from tests.factories.raster import sbs_raster_bytes
    from wepppy.nodb.mods.baer.sbs_map import sbs_map_sanity_check
    sbs_raster_bytes(tmp_path / 'source.tif')
    vrt = tmp_path / 'map.vrt'
    dataset = gdal.Translate(str(vrt), str(tmp_path / 'source.tif'), format='VRT')
    dataset = None
    raw = vrt.read_bytes()
    assert b'relativeToVRT="1"' in raw
    def validate(path):
        assert sbs_map_sanity_check(str(path))[0] == 0
    save_upload_from_stream(raw_filename='map.vrt', stream=io.BytesIO(raw),
        dest_dir=tmp_path, allowed_extensions=('vrt',), overwrite=True, post_save=validate)
    assert vrt.read_bytes() == raw
    assert sorted(p.name for p in tmp_path.iterdir()) == ['map.vrt', 'source.tif']


@pytest.mark.parametrize(
    ("suffix", "driver"),
    ((".tif", "GTiff"), (".tiff", "GTiff"), (".img", "HFA")),
)
def test_validate_raster_upload_accepts_exact_driver(tmp_path, suffix, driver):
    from tests.factories.raster import raster_bytes

    path = tmp_path / f"source{suffix}"
    raster_bytes(path, driver=driver)

    identity = validate_raster_upload(path)

    assert identity.driver == driver
    assert_raster_upload_identity(path, identity)


@pytest.mark.parametrize(
    ("actual_driver", "declared_suffix"),
    (("GTiff", ".img"), ("HFA", ".tif")),
)
def test_validate_raster_upload_rejects_driver_extension_mismatch(
    tmp_path, actual_driver, declared_suffix
):
    from tests.factories.raster import raster_bytes

    actual_suffix = ".tif" if actual_driver == "GTiff" else ".img"
    source = tmp_path / f"source{actual_suffix}"
    raster_bytes(source, driver=actual_driver)
    renamed = tmp_path / f"renamed{declared_suffix}"
    renamed.write_bytes(source.read_bytes())

    with pytest.raises(UploadBoundaryError, match="does not match"):
        validate_raster_upload(renamed)


def test_validate_raster_upload_rejects_companion_dependent_hfa(tmp_path):
    from tests.factories.raster import raster_bytes

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = source_dir / "spill.img"
    raster_bytes(source, driver="HFA", spill=True)
    assert (source_dir / "spill.ige").is_file()
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    detached = isolated / "spill.img"
    detached.write_bytes(source.read_bytes())

    with pytest.raises(UploadBoundaryError, match="companion files"):
        validate_raster_upload(detached)


@pytest.mark.parametrize("suffix", (".tif", ".img"))
def test_validate_raster_upload_rejects_malformed_and_truncated_content(
    tmp_path, suffix
):
    malformed = tmp_path / f"malformed{suffix}"
    malformed.write_bytes(b"not a raster")
    with pytest.raises(UploadBoundaryError, match="does not match"):
        validate_raster_upload(malformed)

    from tests.factories.raster import raster_bytes

    driver = "GTiff" if suffix == ".tif" else "HFA"
    valid = tmp_path / f"valid{suffix}"
    raw = raster_bytes(valid, driver=driver)
    truncated = tmp_path / f"truncated{suffix}"
    truncated.write_bytes(raw[: max(1, len(raw) // 3)])
    with pytest.raises(UploadBoundaryError):
        validate_raster_upload(truncated)


def test_validate_raster_upload_rejects_vrt_disguised_as_tiff(tmp_path):
    from osgeo import gdal
    from tests.factories.raster import raster_bytes

    source = tmp_path / "source.tif"
    raster_bytes(source, driver="GTiff")
    vrt = tmp_path / "source.vrt"
    dataset = gdal.Translate(str(vrt), str(source), format="VRT")
    dataset = None
    disguised = tmp_path / "disguised.tif"
    disguised.write_bytes(vrt.read_bytes())

    with pytest.raises(UploadBoundaryError, match="does not match"):
        validate_raster_upload(disguised)


@pytest.mark.parametrize("companion_suffix", (".aux.xml", ".ovr", ".ige", ".rrd"))
def test_raster_boundary_rejects_destination_companions(
    tmp_path, companion_suffix
):
    from tests.factories.raster import raster_bytes

    source = tmp_path / "source" / "map.tif"
    source.parent.mkdir()
    raw = raster_bytes(source, driver="GTiff")
    destination_dir = tmp_path / "accepted"
    destination_dir.mkdir()
    destination = destination_dir / "map.tif"
    companion = (
        Path(f"{destination}{companion_suffix}")
        if companion_suffix in {".aux.xml", ".ovr"}
        else destination.with_suffix(companion_suffix)
    )
    companion.write_text("untrusted sidecar")

    with pytest.raises(UploadBoundaryError, match="companion files"):
        save_upload_from_stream(
            raw_filename="map.tif",
            stream=io.BytesIO(raw),
            dest_dir=destination_dir,
            allowed_extensions=("tif",),
            overwrite=True,
            post_save=validate_raster_upload,
            isolated_post_save=True,
        )

    assert not destination.exists()
    assert companion.read_text() == "untrusted sidecar"


def test_assert_raster_upload_identity_rejects_replacement(tmp_path):
    from tests.factories.raster import raster_bytes

    path = tmp_path / "source.tif"
    raster_bytes(path, driver="GTiff")
    identity = validate_raster_upload(path)
    replacement = tmp_path / "replacement.tif"
    raster_bytes(replacement, driver="GTiff")
    path.unlink()
    replacement.rename(path)

    with pytest.raises(UploadBoundaryError, match="changed after validation"):
        assert_raster_upload_identity(path, identity)


def test_isolated_post_save_hides_sibling_files(tmp_path):
    from tests.factories.raster import raster_bytes

    source = tmp_path / "source.tif"
    raw = raster_bytes(source, driver="GTiff")
    sibling = tmp_path / "unrelated.txt"
    sibling.write_text("unrelated")

    def validate(path):
        assert sorted(item.name for item in path.parent.iterdir()) == ["source.tif"]
        validate_raster_upload(path)

    saved = save_upload_from_stream(
        raw_filename="source.tif",
        stream=io.BytesIO(raw),
        dest_dir=tmp_path,
        allowed_extensions=("tif",),
        overwrite=True,
        post_save=validate,
        isolated_post_save=True,
    )

    assert saved == source
    assert sorted(item.name for item in tmp_path.iterdir()) == [
        "source.tif",
        "unrelated.txt",
    ]


def test_resolve_contained_raster_path_rejects_escape_and_symlink(tmp_path):
    from tests.factories.raster import raster_bytes

    root = tmp_path / "uploads"
    root.mkdir()
    outside = tmp_path / "outside.tif"
    raster_bytes(outside, driver="GTiff")
    symlink = root / "linked.tif"
    symlink.symlink_to(outside)

    with pytest.raises(UploadBoundaryError, match="outside the approved"):
        resolve_contained_raster_path(outside, root)
    with pytest.raises(UploadBoundaryError, match="outside the approved"):
        resolve_contained_raster_path(symlink, root)
