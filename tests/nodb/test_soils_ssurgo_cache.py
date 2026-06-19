from __future__ import annotations

import ast
import inspect
import os
from pathlib import Path

import pytest

import wepppy.nodb.core.soils as soils_module
from wepppy.nodb.core.soils import Soils
from wepppy.soils.ssurgo import (
    SSURGO_PROJECT_CACHE_FILENAME,
    STATSGO_PROJECT_CACHE_FILENAME,
)

pytestmark = pytest.mark.unit


def _soils_stub(wd: Path) -> Soils:
    soils = Soils.__new__(Soils)
    soils.wd = str(wd)
    return soils


def test_project_ssurgo_cache_paths_are_derived_from_soils_dir(tmp_path: Path) -> None:
    soils = _soils_stub(tmp_path / "run")

    assert soils.ssurgo_cache_db_path == str(
        tmp_path / "run" / "soils" / SSURGO_PROJECT_CACHE_FILENAME
    )
    assert soils.statsgo_cache_db_path == str(
        tmp_path / "run" / "soils" / STATSGO_PROJECT_CACHE_FILENAME
    )


def test_clear_project_surgo_cache_removes_only_sqlite_sidecars(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    soils = _soils_stub(wd)
    soils_dir = wd / "soils"
    soils_dir.mkdir(parents=True)

    cache_path = Path(soils.ssurgo_cache_db_path)
    sidecars = [cache_path, Path(f"{cache_path}-wal"), Path(f"{cache_path}-shm")]
    for path in sidecars:
        path.write_text("stale", encoding="utf-8")
    unrelated = soils_dir / "p1.sol"
    unrelated.write_text("keep", encoding="utf-8")

    soils._clear_project_surgo_cache(use_statsgo=False)

    assert all(not path.exists() for path in sidecars)
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_clear_project_surgo_cache_rejects_soils_dir_symlink_outside_project(
    tmp_path: Path,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir()
    outside_soils_dir = tmp_path / "external-soils"
    outside_soils_dir.mkdir()
    try:
        os.symlink(outside_soils_dir, wd / "soils")
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    soils = _soils_stub(wd)
    outside_cache = outside_soils_dir / SSURGO_PROJECT_CACHE_FILENAME
    outside_cache.write_text("outside", encoding="utf-8")

    with pytest.raises(ValueError, match="outside project directory"):
        soils._clear_project_surgo_cache(use_statsgo=False)

    assert outside_cache.read_text(encoding="utf-8") == "outside"


def test_legacy_soils_instances_default_cache_clear_to_false(tmp_path: Path) -> None:
    soils = _soils_stub(tmp_path / "run")
    soils._soils_map = None
    soils._ssurgo_db = None
    soils.soils = None
    soils._expand_config_path_tokens = lambda value: value

    loaded = Soils._post_instance_loaded(soils)

    assert loaded.clear_ssurgo_cache_on_rebuild is False
    assert loaded._clear_ssurgo_cache_on_rebuild is False


def test_all_soils_surgo_collection_calls_pass_project_cache_path() -> None:
    tree = ast.parse(inspect.getsource(soils_module.Soils))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "SurgoSoilCollection"
    ]

    assert len(calls) == 5
    assert all(
        any(keyword.arg == "cache_db_path" for keyword in call.keywords)
        for call in calls
    )
