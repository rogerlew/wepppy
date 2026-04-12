from __future__ import annotations

import io
import stat
import zipfile

import pytest

from tests.shape_converter.helpers.archive_builder import (
    build_minimal_point_dataset,
    build_zip_bytes,
    mark_zip_as_encrypted,
)
from wepppy.microservices.shape_converter.archive_validation import ArchiveLimits, validate_and_extract_zip_archive
from wepppy.microservices.shape_converter.errors import ShapeConverterError


pytestmark = [pytest.mark.unit, pytest.mark.microservice]


def test_validate_and_extract_zip_archive_accepts_valid_dataset(tmp_path) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="parcel"))

    extracted = validate_and_extract_zip_archive(
        archive_name="parcel.zip",
        archive_bytes=archive_bytes,
        extraction_root=tmp_path / "extract",
    )

    extracted_names = sorted(path.name for path in extracted.extracted_files)
    assert extracted_names == ["parcel.dbf", "parcel.prj", "parcel.shp", "parcel.shx"]


def test_validate_and_extract_zip_archive_removes_shp_xml_sidecar(tmp_path) -> None:
    entries = build_minimal_point_dataset(prefix="parcel")
    entries["parcel.shp.xml"] = b"<metadata><creator>alice</creator></metadata>"
    archive_bytes = build_zip_bytes(entries)

    extracted = validate_and_extract_zip_archive(
        archive_name="parcel.zip",
        archive_bytes=archive_bytes,
        extraction_root=tmp_path / "extract",
    )

    extracted_names = sorted(path.name for path in extracted.extracted_files)
    assert extracted_names == ["parcel.dbf", "parcel.prj", "parcel.shp", "parcel.shx"]
    assert extracted.removed_shp_xml_sidecars == ("parcel.shp.xml",)
    assert not (extracted.extraction_root / "parcel.shp.xml").exists()


def test_validate_and_extract_zip_archive_removes_qmd_sidecar(tmp_path) -> None:
    entries = build_minimal_point_dataset(prefix="parcel")
    entries["parcel.qmd"] = b"metadata"
    archive_bytes = build_zip_bytes(entries)

    extracted = validate_and_extract_zip_archive(
        archive_name="parcel.zip",
        archive_bytes=archive_bytes,
        extraction_root=tmp_path / "extract",
    )

    extracted_names = sorted(path.name for path in extracted.extracted_files)
    assert extracted_names == ["parcel.dbf", "parcel.prj", "parcel.shp", "parcel.shx"]
    assert extracted.removed_shp_xml_sidecars == ()
    assert not (extracted.extraction_root / "parcel.qmd").exists()


def test_validate_and_extract_zip_archive_rejects_generic_xml_sidecar(tmp_path) -> None:
    entries = build_minimal_point_dataset(prefix="parcel")
    entries["parcel.xml"] = b"<metadata/>"
    archive_bytes = build_zip_bytes(entries)

    with pytest.raises(ShapeConverterError) as exc_info:
        validate_and_extract_zip_archive(
            archive_name="parcel.zip",
            archive_bytes=archive_bytes,
            extraction_root=tmp_path / "extract",
        )

    assert exc_info.value.code == "invalid_archive"
    assert "unsupported file extension" in exc_info.value.message.lower()


def test_validate_and_extract_zip_archive_rejects_non_zip_signature(tmp_path) -> None:
    with pytest.raises(ShapeConverterError) as exc_info:
        validate_and_extract_zip_archive(
            archive_name="bad.zip",
            archive_bytes=b"NOTAZIP",
            extraction_root=tmp_path / "extract",
        )

    assert exc_info.value.code == "invalid_archive"


def test_validate_and_extract_zip_archive_rejects_traversal_member(tmp_path) -> None:
    archive_bytes = build_zip_bytes(
        {
            "../escape.shp": b"x",
            "ok.shx": b"y",
            "ok.dbf": b"z",
        }
    )

    with pytest.raises(ShapeConverterError) as exc_info:
        validate_and_extract_zip_archive(
            archive_name="traversal.zip",
            archive_bytes=archive_bytes,
            extraction_root=tmp_path / "extract",
        )

    assert exc_info.value.code == "archive_path_traversal"


def test_validate_and_extract_zip_archive_rejects_symlink_member(tmp_path) -> None:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_STORED) as archive:
        link_info = zipfile.ZipInfo("sample.shp")
        link_info.create_system = 3
        link_info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link_info, "target")
        archive.writestr("sample.shx", b"ok")
        archive.writestr("sample.dbf", b"ok")

    with pytest.raises(ShapeConverterError) as exc_info:
        validate_and_extract_zip_archive(
            archive_name="symlink.zip",
            archive_bytes=zip_buffer.getvalue(),
            extraction_root=tmp_path / "extract",
        )

    assert exc_info.value.code == "invalid_archive"


def test_validate_and_extract_zip_archive_rejects_encrypted_member(tmp_path) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="secure"))
    encrypted_archive = mark_zip_as_encrypted(archive_bytes)

    with pytest.raises(ShapeConverterError) as exc_info:
        validate_and_extract_zip_archive(
            archive_name="encrypted.zip",
            archive_bytes=encrypted_archive,
            extraction_root=tmp_path / "extract",
        )

    assert exc_info.value.code == "invalid_archive"
    assert "encrypted" in exc_info.value.details.lower()


def test_validate_and_extract_zip_archive_rejects_nested_archive(tmp_path) -> None:
    archive_bytes = build_zip_bytes(
        {
            "sample.shp": b"a",
            "sample.shx": b"b",
            "sample.dbf": b"c",
            "nested.zip": b"payload",
        }
    )

    with pytest.raises(ShapeConverterError) as exc_info:
        validate_and_extract_zip_archive(
            archive_name="nested.zip",
            archive_bytes=archive_bytes,
            extraction_root=tmp_path / "extract",
        )

    assert exc_info.value.code == "invalid_archive"
    assert "nested archive" in exc_info.value.details.lower()


def test_validate_and_extract_zip_archive_enforces_member_quota(tmp_path) -> None:
    archive_bytes = build_zip_bytes(
        {
            "one.shp": b"a",
            "one.shx": b"b",
            "one.dbf": b"c",
        }
    )

    with pytest.raises(ShapeConverterError) as exc_info:
        validate_and_extract_zip_archive(
            archive_name="quota.zip",
            archive_bytes=archive_bytes,
            extraction_root=tmp_path / "extract",
            limits=ArchiveLimits(max_member_count=2),
        )

    assert exc_info.value.code == "archive_quota_exceeded"


def test_validate_and_extract_zip_archive_enforces_path_depth_limit(tmp_path) -> None:
    deep_path = "a/b/c/d/e/f/sample.shp"
    archive_bytes = build_zip_bytes(
        {
            deep_path: b"a",
            "a/b/c/d/e/f/sample.shx": b"b",
            "a/b/c/d/e/f/sample.dbf": b"c",
        }
    )

    with pytest.raises(ShapeConverterError) as exc_info:
        validate_and_extract_zip_archive(
            archive_name="depth.zip",
            archive_bytes=archive_bytes,
            extraction_root=tmp_path / "extract",
            limits=ArchiveLimits(max_path_depth=3),
        )

    assert exc_info.value.code == "invalid_archive"
