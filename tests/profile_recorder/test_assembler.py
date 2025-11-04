from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from wepppy.profile_recorder.assembler import ProfileAssembler


def _install_stub_module(monkeypatch: pytest.MonkeyPatch, name: str, **attrs: Any) -> None:
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)


def _singleton(clazz: type) -> type:
    instance = clazz()

    @classmethod  # type: ignore[misc]
    def get_instance(cls, *_: Any, **__: Any) -> Any:
        return instance

    clazz.getInstance = get_instance  # type: ignore[attr-defined]
    return clazz


@pytest.mark.unit
def test_capture_file_upload_writes_expected_seeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    data_repo_root = tmp_path / "data"
    draft_root = data_repo_root / "profiles" / "_drafts" / "run-a" / "stream"
    run_dir = tmp_path / "run_a"
    draft_root.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    disturbed_dir = run_dir / "disturbed"
    disturbed_dir.mkdir(parents=True, exist_ok=True)
    disturbed_file = disturbed_dir / "disturbed_sbs.tif"
    disturbed_file.write_bytes(b"disturbed")

    reveg_dir = run_dir / "revegetation"
    reveg_dir.mkdir(parents=True, exist_ok=True)
    cover_file = reveg_dir / "cover_transform.csv"
    cover_file.write_text("cover,transform\n")

    climate_dir = run_dir / "climate"
    climate_dir.mkdir(parents=True, exist_ok=True)
    cli_file = climate_dir / "demo.cli"
    cli_file.write_text("cli")

    ash_dir = run_dir / "ash"
    ash_dir.mkdir(parents=True, exist_ok=True)
    ash_load = ash_dir / "ash_load.tif"
    ash_load.write_bytes(b"ash-load")
    ash_type = ash_dir / "ash_type.tif"
    ash_type.write_bytes(b"ash-type")

    omni_limbo = run_dir / "omni" / "_limbo"
    omni_limbo.mkdir(parents=True, exist_ok=True)
    omni_seed = omni_limbo / "limbo_seed.tif"
    omni_seed.write_bytes(b"limbo")

    @_singleton
    class StubDisturbed:
        def __init__(self) -> None:
            self.disturbed_path = str(disturbed_file)
            self.burn_shrubs = False
            self.burn_grass = False
            self.sol_ver = 5.0

    @_singleton
    class StubBaer:
        def __init__(self) -> None:
            self.baer_path = None

    @_singleton
    class StubRevegetation:
        def __init__(self) -> None:
            self.cover_transform_path = str(cover_file)

    @_singleton
    class StubClimate:
        def __init__(self) -> None:
            self.orig_cli_fn = str(cli_file)
            self.cli_dir = str(cli_file.parent)

    @_singleton
    class StubAsh:
        def __init__(self) -> None:
            self.ash_load_fn = str(ash_load)
            self.ash_type_map_fn = str(ash_type)

    _install_stub_module(monkeypatch, "wepppy.nodb.mods.disturbed", Disturbed=StubDisturbed)
    _install_stub_module(monkeypatch, "wepppy.nodb.mods.baer", Baer=StubBaer)
    _install_stub_module(monkeypatch, "wepppy.nodb.mods.revegetation", Revegetation=StubRevegetation)
    _install_stub_module(monkeypatch, "wepppy.nodb.core.climate", Climate=StubClimate)
    _install_stub_module(monkeypatch, "wepppy.nodb.mods.ash_transport", Ash=StubAsh)

    assembler = ProfileAssembler(data_repo_root)

    def make_event(path: str) -> dict[str, Any]:
        return {"endpoint": f"/runs/demo/config/{path}", "stage": "response", "category": "file_upload"}

    assembler._capture_file_upload(make_event("tasks/upload_sbs"), draft_root, run_dir)
    assembler._capture_file_upload(make_event("tasks/upload_cover_transform"), draft_root, run_dir)
    assembler._capture_file_upload(make_event("tasks/upload_cli"), draft_root, run_dir)
    assembler._capture_file_upload(make_event("rq/api/run_ash"), draft_root, run_dir)
    assembler._capture_file_upload(make_event("rq/api/run_omni"), draft_root, run_dir)

    seed_root = draft_root / "seed" / "uploads"

    sbs_dir = seed_root / "sbs"
    assert (sbs_dir / disturbed_file.name).read_bytes() == disturbed_file.read_bytes()
    assert (sbs_dir / "input_upload_sbs.tif").read_bytes() == disturbed_file.read_bytes()

    cover_dir = seed_root / "revegetation"
    assert (cover_dir / cover_file.name).read_text() == cover_file.read_text()
    assert (cover_dir / "input_upload_cover_transform.csv").read_text() == cover_file.read_text()

    cli_dir_seed = seed_root / "climate"
    assert (cli_dir_seed / cli_file.name).read_text() == cli_file.read_text()
    assert (cli_dir_seed / "input_upload_cli.cli").read_text() == cli_file.read_text()

    ash_seed_dir = seed_root / "ash"
    assert (ash_seed_dir / ash_load.name).read_bytes() == ash_load.read_bytes()
    assert (ash_seed_dir / "input_upload_ash_load.tif").read_bytes() == ash_load.read_bytes()
    assert (ash_seed_dir / ash_type.name).read_bytes() == ash_type.read_bytes()
    assert (ash_seed_dir / "input_upload_ash_type_map.tif").read_bytes() == ash_type.read_bytes()

    omni_seed_dir = seed_root / "omni" / "_limbo"
    assert (omni_seed_dir / omni_seed.name).read_bytes() == omni_seed.read_bytes()
