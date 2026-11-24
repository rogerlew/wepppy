"""Omni workspace cloning and NoDb path reconciliation tests."""

import errno
import json
import logging
import os
import types
from pathlib import Path

import pytest

from tests.nodb.mods._omni_test_support import omni_module as omni_module
from wepppy.runtime_paths.errors import NoDirError


pytestmark = pytest.mark.unit


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_omni_clone_links_directory_shared_inputs(tmp_path: Path, omni_module) -> None:
    base_wd = tmp_path / "run"
    base_wd.mkdir()
    (base_wd / "dem").mkdir()
    (base_wd / "climate").mkdir()
    (base_wd / "watershed").mkdir()

    scenario_def = {"type": "dummy"}
    scenario_wd = Path(omni_module._omni_clone(scenario_def, str(base_wd), runid="run-123"))

    assert (scenario_wd / "dem").is_symlink()
    assert os.readlink(scenario_wd / "dem") == "../../../../dem"
    assert (scenario_wd / "climate").is_symlink()
    assert os.readlink(scenario_wd / "climate") == "../../../../climate"
    assert (scenario_wd / "watershed").is_symlink()
    assert os.readlink(scenario_wd / "watershed") == "../../../../watershed"
    assert not (scenario_wd / "climate.nodir").exists()
    assert not (scenario_wd / "watershed.nodir").exists()
    assert not (scenario_wd / "climate.wepp_cli.parquet").exists()
    assert not (scenario_wd / "watershed.hillslopes.parquet").exists()
    assert not (scenario_wd / "watershed.channels.parquet").exists()


def test_update_nodb_wd_rehomes_disturbed_source_path(tmp_path: Path, omni_module) -> None:
    source_wd = tmp_path / "source"
    scenario_wd = tmp_path / "scenario"
    data = {
        "py/state": {
            "wd": str(source_wd),
            "_disturbed_fn": str(source_wd / "disturbed" / "source.tif"),
        }
    }

    omni_module._update_nodb_wd(data, str(scenario_wd), parent_wd=str(source_wd))

    assert data["py/state"]["wd"] == str(scenario_wd)
    assert data["py/state"]["_parent_wd"] == str(source_wd)
    assert data["py/state"]["_disturbed_fn"] == str(
        scenario_wd / "disturbed" / "source.tif"
    )


def test_update_nodb_wd_rehomes_sibling_disturbed_source_without_parent_metadata(
    tmp_path: Path,
    omni_module,
) -> None:
    sibling_wd = tmp_path / "scenarios" / "uniform_low"
    scenario_wd = tmp_path / "scenarios" / "mulch"
    data = {
        "wd": str(sibling_wd),
        "_disturbed_fn": str(sibling_wd / "disturbed" / "source.tif"),
    }

    omni_module._update_nodb_wd(data, str(scenario_wd), source_wd=str(sibling_wd))

    assert data["wd"] == str(scenario_wd)
    assert "_parent_wd" not in data
    assert data["_disturbed_fn"] == str(
        scenario_wd / "disturbed" / "source.tif"
    )


def test_omni_clone_rehomes_copied_disturbed_source_path(
    tmp_path: Path,
    omni_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_wd = tmp_path / "run"
    base_wd.mkdir()
    (base_wd / "dem").mkdir()
    (base_wd / "climate").mkdir()
    (base_wd / "watershed").mkdir()
    disturbed_dir = base_wd / "disturbed"
    disturbed_dir.mkdir()
    source = disturbed_dir / "source.tif"
    source.write_text("source", encoding="ascii")
    (base_wd / "disturbed.nodb").write_text(
        json.dumps(
            {
                "py/state": {
                    "wd": str(base_wd),
                    "_disturbed_fn": str(source),
                }
            }
        ),
        encoding="ascii",
    )

    monkeypatch.setattr(omni_module, "nodir_resolve", lambda *args, **kwargs: None)

    scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    copied_source = scenario_wd / "disturbed" / "source.tif"
    assert copied_source.read_text(encoding="ascii") == "source"
    state = json.loads((scenario_wd / "disturbed.nodb").read_text(encoding="ascii"))
    assert state["py/state"]["wd"] == str(scenario_wd)
    assert state["py/state"]["_parent_wd"] == str(base_wd)
    assert state["py/state"]["_disturbed_fn"] == str(copied_source)


def test_omni_clone_sibling_rehomes_copied_disturbed_source_path(
    tmp_path: Path,
    omni_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent_wd = tmp_path / "run"
    new_wd = parent_wd / "_pups" / "omni" / "scenarios" / "mulch"
    sibling_wd = parent_wd / "_pups" / "omni" / "scenarios" / "uniform_low"
    new_wd.mkdir(parents=True)
    sibling_wd.mkdir(parents=True)

    for name in ("disturbed", "landuse", "soils"):
        (new_wd / f"{name}.nodb").write_text(json.dumps({"wd": str(new_wd)}), encoding="ascii")
        (sibling_wd / f"{name}.nodb").write_text(json.dumps({"wd": str(sibling_wd)}), encoding="ascii")
        (new_wd / name).mkdir()
        (new_wd / name / "old.txt").write_text("old", encoding="ascii")
        (sibling_wd / name).mkdir()
        (sibling_wd / name / f"{name}.txt").write_text(name, encoding="ascii")

    sibling_source = sibling_wd / "disturbed" / "source.tif"
    sibling_source.write_text("source", encoding="ascii")
    (sibling_wd / "disturbed.nodb").write_text(
        json.dumps(
            {
                "py/state": {
                    "wd": str(sibling_wd),
                    "_disturbed_fn": str(sibling_source),
                }
            }
        ),
        encoding="ascii",
    )

    monkeypatch.setattr(omni_module, "copy_version_for_clone", lambda src, dst: None)
    monkeypatch.setattr(omni_module, "_clear_nodb_cache_and_locks", lambda runid, pup_relpath=None: None)

    def _resolve(wd: str, rel: str, view: str = "effective"):
        if Path(wd).resolve() == sibling_wd.resolve() and rel in {"landuse", "soils"}:
            return types.SimpleNamespace(
                form="dir",
                dir_path=str(sibling_wd),
                inner_path=rel,
            )
        return None

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)

    omni_module._omni_clone_sibling(
        str(new_wd),
        "uniform_low",
        runid="run-123",
        parent_wd=str(parent_wd),
    )

    copied_source = new_wd / "disturbed" / "source.tif"
    assert copied_source.read_text(encoding="ascii") == "source"
    state = json.loads((new_wd / "disturbed.nodb").read_text(encoding="ascii"))
    assert state["py/state"]["wd"] == str(new_wd)
    assert "_parent_wd" not in state["py/state"]
    assert state["py/state"]["_disturbed_fn"] == str(copied_source)


def test_omni_clone_survives_enotempty_on_existing_workspace_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    omni_module,
) -> None:
    import wepppy.nodb.mods.omni.omni_clone_contrast_service as clone_service_mod

    base_wd = tmp_path / "run"
    base_wd.mkdir()
    (base_wd / "dem").mkdir()
    (base_wd / "climate").mkdir()
    (base_wd / "watershed").mkdir()

    existing_wd = base_wd / "_pups" / "omni" / "scenarios" / "dummy"
    (existing_wd / "wepp" / "runs").mkdir(parents=True)
    (existing_wd / "wepp" / "runs" / "old.run").write_text("old", encoding="ascii")

    monkeypatch.setattr(omni_module, "nodir_resolve", lambda *args, **kwargs: None)

    real_rmtree = clone_service_mod.shutil.rmtree
    calls = {"enotempty_raised": 0}

    def _flaky_rmtree(path: str | Path, *args: object, **kwargs: object) -> None:
        path_obj = Path(path)
        if path_obj.name.startswith("dummy.stale.") and calls["enotempty_raised"] == 0:
            calls["enotempty_raised"] += 1
            raise OSError(errno.ENOTEMPTY, "Directory not empty", str(path_obj))
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(clone_service_mod.shutil, "rmtree", _flaky_rmtree)

    scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert calls["enotempty_raised"] == 1
    assert scenario_wd.is_dir()
    stale_dirs = list((base_wd / "_pups" / "omni" / "scenarios").glob("dummy.stale.*"))
    assert stale_dirs == []


def test_omni_clone_logs_directory_copy_permission_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    omni_module,
    caplog: pytest.LogCaptureFixture,
) -> None:
    base_wd = tmp_path / "run"
    source_dir = base_wd / "problem-dir"
    nested_dir = source_dir / "nested"
    nested_dir.mkdir(parents=True)

    monkeypatch.setattr(omni_module, "nodir_resolve", lambda *args, **kwargs: None)

    original_walk = omni_module.os.walk

    def _walk_with_permission_error(path: str):
        if str(path) == str(source_dir):
            raise PermissionError("blocked")
        return original_walk(path)

    monkeypatch.setattr(omni_module.os, "walk", _walk_with_permission_error)

    with caplog.at_level(logging.WARNING, logger=omni_module.LOGGER.name):
        scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert scenario_wd.exists()
    assert "Permission denied while creating Omni clone directory tree" in caplog.text


def test_omni_clone_logs_directory_copy_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    omni_module,
    caplog: pytest.LogCaptureFixture,
) -> None:
    base_wd = tmp_path / "run"
    source_dir = base_wd / "problem-dir"
    nested_dir = source_dir / "nested"
    nested_dir.mkdir(parents=True)

    monkeypatch.setattr(omni_module, "nodir_resolve", lambda *args, **kwargs: None)

    original_walk = omni_module.os.walk

    def _walk_with_oserror(path: str):
        if str(path) == str(source_dir):
            raise OSError("boom")
        return original_walk(path)

    monkeypatch.setattr(omni_module.os, "walk", _walk_with_oserror)

    with caplog.at_level(logging.WARNING, logger=omni_module.LOGGER.name):
        scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert scenario_wd.exists()
    assert "Error creating Omni clone directory tree" in caplog.text


def test_omni_clone_skips_archive_only_soils_source(tmp_path: Path, omni_module, monkeypatch):
    base_wd = tmp_path / "run"
    base_wd.mkdir()
    (base_wd / "dem").mkdir()
    (base_wd / "climate").mkdir()
    (base_wd / "watershed").mkdir()
    (base_wd / "soils.nodir").write_text("archive", encoding="ascii")
    (base_wd / "landuse.nodir").write_text("archive", encoding="ascii")

    def _resolve(wd: str, rel: str, view: str = "effective"):
        if wd == str(base_wd) and rel in {"soils", "landuse"}:
            return types.SimpleNamespace(form="archive")
        return None

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)

    scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert not (scenario_wd / "soils").exists()
    assert not (scenario_wd / "landuse").exists()
    assert not (scenario_wd / "soils.parquet").exists()
    assert not (scenario_wd / "landuse.parquet").exists()


def test_omni_clone_copies_soils_from_directory_source(tmp_path: Path, omni_module, monkeypatch):
    base_wd = tmp_path / "run"
    base_wd.mkdir()
    (base_wd / "dem").mkdir()
    (base_wd / "climate").mkdir()
    (base_wd / "watershed").mkdir()
    soils_src = base_wd / "soils"
    soils_src.mkdir()
    (soils_src / "763002.sol").write_text("soil-data", encoding="ascii")

    def _resolve(wd: str, rel: str, view: str = "effective"):
        if wd == str(base_wd) and rel == "soils":
            return types.SimpleNamespace(
                form="dir",
                dir_path=str(base_wd),
                inner_path="soils",
            )
        return None

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)

    scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert (scenario_wd / "soils").is_dir()
    assert (scenario_wd / "soils" / "763002.sol").read_text(encoding="ascii") == "soil-data"


def test_omni_clone_copies_landuse_from_directory_source(tmp_path: Path, omni_module, monkeypatch):
    base_wd = tmp_path / "run"
    base_wd.mkdir()
    (base_wd / "dem").mkdir()
    (base_wd / "climate").mkdir()
    (base_wd / "watershed").mkdir()
    landuse_src = base_wd / "landuse"
    landuse_src.mkdir()
    (landuse_src / "custom.man").write_text("management-data", encoding="ascii")

    def _resolve(wd: str, rel: str, view: str = "effective"):
        if wd == str(base_wd) and rel == "landuse":
            return types.SimpleNamespace(
                form="dir",
                dir_path=str(base_wd),
                inner_path="landuse",
            )
        return None

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)

    scenario_wd = Path(omni_module._omni_clone({"type": "dummy"}, str(base_wd), runid="run-123"))

    assert (scenario_wd / "landuse").is_dir()
    assert (scenario_wd / "landuse" / "custom.man").read_text(encoding="ascii") == "management-data"


def test_omni_clone_sibling_rejects_archive_landuse_and_soils(tmp_path: Path, omni_module, monkeypatch):
    parent_wd = tmp_path / "run"
    new_wd = parent_wd / "_pups" / "omni" / "scenarios" / "target"
    sibling_wd = parent_wd / "_pups" / "omni" / "scenarios" / "sibling"
    new_wd.mkdir(parents=True)
    sibling_wd.mkdir(parents=True)

    for name in ("disturbed", "landuse", "soils"):
        (new_wd / f"{name}.nodb").write_text(json.dumps({"wd": str(new_wd)}), encoding="ascii")
        (sibling_wd / f"{name}.nodb").write_text(json.dumps({"wd": str(sibling_wd)}), encoding="ascii")

    for dirname in ("disturbed", "landuse", "soils"):
        (new_wd / dirname).mkdir()
        (new_wd / dirname / "old.txt").write_text("old", encoding="ascii")

    (sibling_wd / "disturbed").mkdir()
    (sibling_wd / "disturbed" / "disturbed.txt").write_text("disturbed", encoding="ascii")

    monkeypatch.setattr(omni_module, "copy_version_for_clone", lambda src, dst: None)
    monkeypatch.setattr(omni_module, "_clear_nodb_cache_and_locks", lambda runid, pup_relpath=None: None)

    def _resolve(wd: str, rel: str, view: str = "effective"):
        if Path(wd).resolve() == sibling_wd.resolve() and rel in {"landuse", "soils"}:
            return types.SimpleNamespace(form="archive")
        return None

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)

    with pytest.raises(NoDirError) as exc_info:
        omni_module._omni_clone_sibling(str(new_wd), "sibling", runid="run-123", parent_wd=str(parent_wd))

    assert exc_info.value.code == "NODIR_MIGRATION_REQUIRED"
    assert exc_info.value.http_status == 409
    assert "migration" in exc_info.value.message.lower()


def test_omni_clone_sibling_rejects_path_traversal(tmp_path: Path, omni_module):
    parent_wd = tmp_path / "run"
    new_wd = parent_wd / "_pups" / "omni" / "scenarios" / "target"
    new_wd.mkdir(parents=True)

    with pytest.raises(ValueError, match="Invalid sibling scenario key"):
        omni_module._omni_clone_sibling(
            str(new_wd),
            "../escape",
            runid="run-123",
            parent_wd=str(parent_wd),
        )
