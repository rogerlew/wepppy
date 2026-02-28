from __future__ import annotations

from pathlib import Path

import pytest

import wepppy.runtime_paths.wepp_inputs as wepp_inputs
from wepppy.runtime_paths.wepp_inputs import (
    copy_input_file,
    glob_input_files,
    input_exists,
    list_input_files,
    materialize_input_file,
    open_input_text,
    with_input_file_path,
)

pytestmark = pytest.mark.unit


def test_with_input_file_path_accepts_legacy_materialize_kwargs(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    rel = "watershed/example.slp"
    src = wd / rel
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("slope", encoding="utf-8")

    with with_input_file_path(
        str(wd),
        rel,
        purpose="compat",
        tolerate_mixed=True,
        mixed_prefer="archive",
        allow_materialize_fallback=True,
        use_projection=True,
    ) as materialized_path:
        assert materialized_path == str(src)


def test_materialize_input_file_raises_for_missing_or_directory(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "watershed").mkdir()

    with pytest.raises(FileNotFoundError):
        materialize_input_file(str(wd), "watershed/missing.slp")

    with pytest.raises(IsADirectoryError):
        materialize_input_file(str(wd), "watershed")


def test_list_input_files_returns_sorted_files_only(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    src = wd / "watershed"
    src.mkdir(parents=True, exist_ok=True)
    (src / "B.txt").write_text("b", encoding="utf-8")
    (src / "a.txt").write_text("a", encoding="utf-8")
    (src / "nested").mkdir()

    assert list_input_files(str(wd), "watershed") == ["a.txt", "B.txt"]


def test_glob_input_files_matches_final_segment_only(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    src = wd / "watershed"
    src.mkdir(parents=True, exist_ok=True)
    (src / "a.slp").write_text("a", encoding="utf-8")
    (src / "b.txt").write_text("b", encoding="utf-8")

    assert glob_input_files(str(wd), "watershed/*.slp") == ["watershed/a.slp"]
    assert glob_input_files(str(wd), "watershed/a.slp") == ["watershed/a.slp"]
    assert glob_input_files(str(wd), "watershed/missing.slp") == []

    with pytest.raises(ValueError, match="final segment"):
        glob_input_files(str(wd), "waters*/a.slp")


def test_copy_input_file_falls_back_to_copy_when_hardlink_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wd = tmp_path / "run"
    src_dir = wd / "watershed"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "a.slp").write_text("a", encoding="utf-8")
    dst = tmp_path / "out" / "copied.slp"

    monkeypatch.setattr(wepp_inputs.os, "link", lambda _src, _dst: (_ for _ in ()).throw(OSError("no link")))

    written = copy_input_file(str(wd), "watershed/a.slp", dst, prefer_hardlink=True)
    assert written == str(dst)
    assert dst.read_text(encoding="utf-8") == "a"


def test_open_input_text_and_input_exists(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    src_dir = wd / "watershed"
    src_dir.mkdir(parents=True, exist_ok=True)
    target = src_dir / "a.slp"
    target.write_text("line", encoding="utf-8")

    assert input_exists(str(wd), "watershed/a.slp") is True
    assert input_exists(str(wd), "watershed/missing.slp") is False

    with open_input_text(str(wd), "watershed/a.slp") as handle:
        assert handle.read() == "line"
