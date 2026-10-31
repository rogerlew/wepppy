from __future__ import annotations

import io
from pathlib import Path

import pytest

from wepppy.microservices.upload_boundary import (
    UploadBoundaryError,
    enforce_extension,
    prepare_filename,
    save_upload_from_stream,
    write_stream_to_destination,
)


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
    from tests.factories.raster import sbs_raster_bytes
    from osgeo import gdal
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
