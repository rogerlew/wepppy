from __future__ import annotations

import errno
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

import wepppy.rq.project_rq_archive as archive_helpers

pytestmark = pytest.mark.unit


def test_normalize_relpath_and_exclusion_rules() -> None:
    assert archive_helpers._normalize_relpath("./archives/demo") == "archives/demo"
    assert archive_helpers._normalize_relpath(".\\nodir\\cache\\watershed") == "nodir/cache/watershed"

    assert archive_helpers._is_archive_excluded_relpath("archives")
    assert archive_helpers._is_archive_excluded_relpath("archives/demo.zip")
    assert not archive_helpers._is_archive_excluded_relpath(".nodir/cache/watershed/123")
    assert not archive_helpers._is_archive_excluded_relpath(".nodir/projections/read.json")


def test_assert_sufficient_disk_space_allows_reclaimable_headroom(tmp_path: Path) -> None:
    wd = tmp_path / "demo"
    wd.mkdir(parents=True)

    disk_usage = lambda _path: SimpleNamespace(free=100)

    archive_helpers._assert_sufficient_disk_space(
        wd,
        required_bytes=150,
        purpose="test",
        reclaimable_bytes=60,
        disk_usage=disk_usage,
    )

    with pytest.raises(OSError) as exc_info:
        archive_helpers._assert_sufficient_disk_space(
            wd,
            required_bytes=150,
            purpose="test",
            reclaimable_bytes=40,
            disk_usage=disk_usage,
        )

    assert exc_info.value.errno == errno.ENOSPC


def test_collect_restore_members_rejects_path_traversal(tmp_path: Path) -> None:
    wd = tmp_path / "demo"
    wd.mkdir(parents=True)

    archive_path = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive_path, mode="w") as zf:
        zf.writestr("../outside.txt", "bad")

    with zipfile.ZipFile(archive_path, mode="r") as zf:
        with pytest.raises(ValueError, match="Unsafe archive member path"):
            archive_helpers._collect_restore_members(zf, wd)
