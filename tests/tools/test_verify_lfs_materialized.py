from pathlib import Path

import pytest

from tools.verify_lfs_materialized import LFS_POINTER_HEADER, is_lfs_pointer, verify


pytestmark = pytest.mark.unit


def test_pointer_header_is_detected(tmp_path: Path) -> None:
    pointer = tmp_path / "asset.db"
    pointer.write_bytes(LFS_POINTER_HEADER + b"oid sha256:abc\nsize 42\n")

    assert is_lfs_pointer(pointer)
    assert verify([pointer]) == (1, [pointer])


def test_materialized_binary_is_accepted(tmp_path: Path) -> None:
    asset = tmp_path / "asset.db"
    asset.write_bytes(b"SQLite format 3\x00" + b"\x00" * 64)

    assert not is_lfs_pointer(asset)
    assert verify([asset]) == (1, [])


def test_missing_tracked_file_is_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing.bin"

    assert verify([missing]) == (1, [missing])
