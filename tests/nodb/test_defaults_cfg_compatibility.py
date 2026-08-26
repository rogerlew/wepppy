from __future__ import annotations

import configparser
import os
from pathlib import Path

import jsonpickle
import pytest

import wepppy.nodb.base as base

pytestmark = pytest.mark.unit


def _write_defaults(path: Path, value: str) -> None:
    path.write_text(f"[compatibility]\nsource = {value}\n", encoding="utf-8")


def _install_shared_paths(
    monkeypatch: pytest.MonkeyPatch,
    shared_root: Path,
) -> tuple[Path, Path]:
    shared_root.mkdir()
    canonical = shared_root / "_defaults.cfg"
    legacy = shared_root / "_defaults.toml"
    monkeypatch.setattr(base, "_default_config", str(canonical))
    monkeypatch.setattr(base, "_legacy_default_config", str(legacy))
    return canonical, legacy


@pytest.mark.parametrize(
    ("present", "expected"),
    [
        (("local_cfg", "local_toml", "shared_cfg", "shared_toml"), "local_cfg"),
        (("local_toml", "shared_cfg", "shared_toml"), "local_toml"),
        (("shared_cfg", "shared_toml"), "shared_cfg"),
        (("shared_toml",), "shared_toml"),
    ],
)
def test_defaults_resolution_uses_contract_precedence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    present: tuple[str, ...],
    expected: str,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    canonical, legacy = _install_shared_paths(monkeypatch, tmp_path / "shared")
    paths = {
        "local_cfg": project_root / "_defaults.cfg",
        "local_toml": project_root / "_defaults.toml",
        "shared_cfg": canonical,
        "shared_toml": legacy,
    }
    for name in present:
        _write_defaults(paths[name], name)

    resolved = Path(base.resolve_defaults_path(project_root))

    assert resolved == paths[expected]


def test_config_parser_layers_preset_over_project_local_legacy_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    canonical, _legacy = _install_shared_paths(monkeypatch, tmp_path / "shared")
    _write_defaults(canonical, "shared")
    (project_root / "_defaults.toml").write_text(
        "[compatibility]\nsource = local_legacy\ndefault_only = retained\n",
        encoding="utf-8",
    )
    preset = tmp_path / "preset.cfg"
    preset.write_text("[compatibility]\nsource = preset\n", encoding="utf-8")
    controller = object.__new__(base.NoDbBase)
    controller.wd = str(project_root)
    controller._config = str(preset)

    parser = controller._configparser

    assert parser.get("compatibility", "source") == "preset"
    assert parser.get("compatibility", "default_only") == "retained"


def test_missing_defaults_retains_explicit_file_not_found(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    canonical, _legacy = _install_shared_paths(monkeypatch, tmp_path / "shared")
    preset = tmp_path / "preset.cfg"
    preset.write_text("[compatibility]\nsource = preset\n", encoding="utf-8")
    controller = object.__new__(base.NoDbBase)
    controller.wd = str(project_root)
    controller._config = str(preset)

    with pytest.raises(FileNotFoundError) as exc_info:
        _ = controller._configparser

    assert Path(exc_info.value.filename) == canonical


def test_malformed_selected_defaults_retains_parser_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    canonical, _legacy = _install_shared_paths(monkeypatch, tmp_path / "shared")
    canonical.write_text("not-an-ini-section\n", encoding="utf-8")
    preset = tmp_path / "preset.cfg"
    preset.write_text("[compatibility]\nsource = preset\n", encoding="utf-8")
    controller = object.__new__(base.NoDbBase)
    controller.wd = str(project_root)
    controller._config = str(preset)

    with pytest.raises(configparser.MissingSectionHeaderError):
        _ = controller._configparser


def test_repository_legacy_name_is_relative_symlink_for_older_reader() -> None:
    config_root = Path(base.get_config_dir())
    canonical = config_root / "_defaults.cfg"
    legacy = config_root / "_defaults.toml"

    assert canonical.is_file()
    assert legacy.is_symlink()
    assert os.readlink(legacy) == "_defaults.cfg"
    assert legacy.read_bytes() == canonical.read_bytes()

    old_reader = base.CaseSensitiveRawConfigParser(allow_no_value=True)
    with legacy.open(encoding="utf-8") as handle:
        old_reader.read_file(handle)
    assert old_reader.getboolean("nodb", "apply_nodir") is False


def test_get_default_config_path_prefers_canonical_shared_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    canonical, legacy = _install_shared_paths(monkeypatch, tmp_path / "shared")
    _write_defaults(legacy, "legacy")
    _write_defaults(canonical, "canonical")

    assert Path(base.get_default_config_path()) == canonical


def test_canonical_defaults_is_not_advertised_as_named_preset() -> None:
    configs = base.get_configs()

    assert "_defaults" not in configs
    assert len(configs) == 128


def test_serialized_nodb_payload_retains_token_without_defaults_basename() -> None:
    controller = object.__new__(base.NoDbBase)
    controller._config = "disturbed9002?general:dem_db=wbt"

    payload = jsonpickle.encode(controller)

    assert "disturbed9002?general:dem_db=wbt" in payload
    assert "_defaults.cfg" not in payload
    assert "_defaults.toml" not in payload
