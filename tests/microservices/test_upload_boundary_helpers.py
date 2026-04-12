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
