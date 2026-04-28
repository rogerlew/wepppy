from __future__ import annotations

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.f_esri as f_esri

pytestmark = pytest.mark.unit


def _has_required_bits(path: Path, required_bits: int) -> bool:
    return (path.lstat().st_mode & required_bits) == required_bits


def test_docker_exec_includes_user_flag_when_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f_esri, "has_f_esri", lambda _container_name: True)

    captured: dict[str, object] = {}

    def _fake_run_docker_command(args, *, timeout=None):
        captured["args"] = list(args)
        captured["timeout"] = timeout
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(f_esri, "_run_docker_command", _fake_run_docker_command)

    f_esri._docker_exec(
        "wepppy-f-esri",
        ["echo", "ok"],
        timeout=42,
        user="1000:1000",
    )

    assert captured["args"] == [
        "exec",
        "--user",
        "1000:1000",
        "wepppy-f-esri",
        "echo",
        "ok",
    ]
    assert captured["timeout"] == 42


def test_c2c_gpkg_to_gdb_uses_current_user_for_container_exec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gpkg_path = tmp_path / "input.gpkg"
    gpkg_path.write_bytes(b"gpkg")
    gdb_path = tmp_path / "features_export.gdb"

    calls: list[dict[str, object]] = []

    def _fake_docker_exec(container_name, exec_args, *, timeout=None, user=None):
        calls.append(
            {
                "container_name": container_name,
                "exec_args": list(exec_args),
                "timeout": timeout,
                "user": user,
            }
        )
        gdb_path.mkdir(parents=True, exist_ok=True)
        (gdb_path / "a.gdbtable").write_text("stub", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(f_esri, "_docker_exec", _fake_docker_exec)

    result = f_esri.c2c_gpkg_to_gdb(
        str(gpkg_path),
        str(gdb_path),
        zip_output=False,
    )

    assert result == str(gdb_path.resolve())
    assert len(calls) == 1
    assert calls[0]["user"] == f_esri._resolve_current_user_spec()


def test_c2c_gpkg_to_gdb_sets_writable_permissions_on_created_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gpkg_path = tmp_path / "input.gpkg"
    gpkg_path.write_bytes(b"gpkg")
    gdb_path = tmp_path / "features_export.gdb"

    def _fake_docker_exec(_container_name, _exec_args, *, timeout=None, user=None):
        _ = timeout
        _ = user
        inner_dir = gdb_path / "inner"
        inner_dir.mkdir(parents=True, exist_ok=True)
        output_file = inner_dir / "table.gdbtable"
        output_file.write_text("stub", encoding="utf-8")
        os.chmod(gdb_path, 0o500)
        os.chmod(inner_dir, 0o500)
        os.chmod(output_file, 0o400)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(f_esri, "_docker_exec", _fake_docker_exec)

    f_esri.c2c_gpkg_to_gdb(
        str(gpkg_path),
        str(gdb_path),
        zip_output=True,
    )

    output_file = gdb_path / "inner" / "table.gdbtable"
    zip_path = gdb_path.with_suffix(".gdb.zip")

    assert zip_path.exists()
    assert _has_required_bits(gdb_path, f_esri._DIR_PERMISSION_BITS)
    assert _has_required_bits(gdb_path / "inner", f_esri._DIR_PERMISSION_BITS)
    assert _has_required_bits(output_file, f_esri._FILE_PERMISSION_BITS)
    assert _has_required_bits(zip_path, f_esri._FILE_PERMISSION_BITS)
    assert _has_required_bits(gdb_path.parent, f_esri._DIR_PERMISSION_BITS)

