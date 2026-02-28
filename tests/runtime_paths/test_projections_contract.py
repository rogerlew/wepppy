from __future__ import annotations

from pathlib import Path

import pytest

import wepppy.runtime_paths.projections as projections
from wepppy.runtime_paths.projections import (
    abort_mutation_projection,
    acquire_root_projection,
    commit_mutation_projection,
    release_root_projection,
    with_root_projection,
)

pytestmark = pytest.mark.unit


def test_acquire_root_projection_returns_directory_handle(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    (wd / "watershed").mkdir(parents=True, exist_ok=True)

    handle = acquire_root_projection(
        str(wd),
        "watershed",
        mode="read",
        purpose="unit",
    )

    assert handle.wd == str(wd.resolve())
    assert handle.root == "watershed"
    assert handle.mode == "read"
    assert handle.purpose == "unit"
    assert handle.mount_path == str((wd / "watershed").resolve())
    assert handle.lower_path == str((wd / "watershed").resolve())
    assert handle.archive_path == str((wd / "watershed.nodir").resolve())
    assert handle.session_token


def test_acquire_root_projection_raises_for_missing_root(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    with pytest.raises(FileNotFoundError):
        acquire_root_projection(str(wd), "watershed")


def test_acquire_root_projection_raises_for_file_root(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "watershed").write_text("not-dir", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        acquire_root_projection(str(wd), "watershed")


def test_with_root_projection_releases_projection_handle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wd = tmp_path / "run"
    (wd / "watershed").mkdir(parents=True, exist_ok=True)
    released: list[str] = []

    def _release(handle):
        released.append(handle.session_token)

    monkeypatch.setattr(projections, "release_root_projection", _release)

    with with_root_projection(str(wd), "watershed", purpose="unit") as handle:
        assert handle.root == "watershed"
        assert released == []

    assert released == [handle.session_token]


def test_projection_mutation_lifecycle_helpers_are_noop(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    (wd / "watershed").mkdir(parents=True, exist_ok=True)
    handle = acquire_root_projection(str(wd), "watershed", mode="mutate", purpose="unit")

    commit_mutation_projection(handle)
    abort_mutation_projection(handle)
    release_root_projection(handle)
