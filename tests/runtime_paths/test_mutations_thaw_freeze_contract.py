from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

import wepppy.runtime_paths.mutations as runtime_mutations
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.mutations import mutate_root, mutate_roots, preflight_root_forms
from wepppy.runtime_paths.thaw_freeze import (
    freeze_locked,
    maintenance_lock,
    maintenance_lock_key,
    thaw_locked,
)

pytestmark = pytest.mark.unit


def test_preflight_root_forms_reports_directory_archive_and_missing(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "landuse").mkdir()
    (wd / "soils.nodir").write_bytes(b"archive")

    forms = preflight_root_forms(str(wd), ("landuse", "soils", "climate"))
    assert forms == {
        "landuse": "dir",
        "soils": "archive",
        "climate": "missing",
    }


def test_mutate_root_rejects_archive_retired_root_without_running_callback(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "soils.nodir").write_bytes(b"archive")
    callback_calls: list[str] = []

    with pytest.raises(NoDirError) as exc_info:
        mutate_root(str(wd), "soils", lambda: callback_calls.append("called"), purpose="unit")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert callback_calls == []


def test_mutate_roots_sorts_lock_order_and_unwinds_reverse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "landuse").mkdir()
    (wd / "soils").mkdir()

    events: list[tuple[str, str, str]] = []

    @contextmanager
    def _lock(_wd: str, root: str, *, purpose: str):
        events.append(("enter", root, purpose))
        yield
        events.append(("exit", root, purpose))

    monkeypatch.setattr(runtime_mutations, "maintenance_lock", _lock)

    result = mutate_roots(
        str(wd),
        ("soils", "landuse", "soils"),
        lambda: "ok",
        purpose="mutate-many",
    )

    assert result == "ok"
    assert events == [
        ("enter", "landuse", "mutate-many/landuse"),
        ("enter", "soils", "mutate-many/soils"),
        ("exit", "soils", "mutate-many/soils"),
        ("exit", "landuse", "mutate-many/landuse"),
    ]


def test_maintenance_lock_key_scopes_grouped_paths_to_parent_runid(tmp_path: Path) -> None:
    wd = tmp_path / "wc1" / "runs" / "ab" / "base-run" / "_pups" / "omni" / "scenarios" / "s1"
    wd.mkdir(parents=True, exist_ok=True)

    key = maintenance_lock_key(str(wd), "landuse")
    assert key == "nodb-lock:base-run:runtime-paths/landuse"


# LOCK_SCOPE_OMNI_SIBLING_ISOLATION
def test_maintenance_lock_path_scope_allows_distinct_sibling_roots_and_blocks_shared_root(
    tmp_path: Path,
) -> None:
    base_wd = tmp_path / "wc1" / "runs" / "ab" / "base-run"
    s1 = base_wd / "_pups" / "omni" / "scenarios" / "s1"
    s2 = base_wd / "_pups" / "omni" / "scenarios" / "s2"
    s1_landuse = s1 / "landuse"
    s2_landuse = s2 / "landuse"
    s1_landuse.mkdir(parents=True, exist_ok=True)
    s2_landuse.mkdir(parents=True, exist_ok=True)

    with maintenance_lock(
        str(s1),
        "landuse",
        purpose="s1-distinct",
        ttl_seconds=30,
        scope="effective_root_path_compat",
    ):
        with maintenance_lock(
            str(s2),
            "landuse",
            purpose="s2-distinct",
            ttl_seconds=30,
            scope="effective_root_path_compat",
        ):
            pass

    s2_landuse.rmdir()
    s2_landuse.symlink_to(s1_landuse, target_is_directory=True)

    with maintenance_lock(
        str(s1),
        "landuse",
        purpose="s1-shared",
        ttl_seconds=30,
        scope="effective_root_path_compat",
    ):
        with pytest.raises(NoDirError) as exc_info:
            with maintenance_lock(
                str(s2),
                "landuse",
                purpose="s2-shared",
                ttl_seconds=30,
                scope="effective_root_path_compat",
            ):
                pass

    assert exc_info.value.code == "NODIR_LOCKED"


def test_maintenance_lock_raises_nodir_locked_on_contention(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    with maintenance_lock(str(wd), "landuse", purpose="outer", ttl_seconds=30):
        with pytest.raises(NoDirError) as exc_info:
            with maintenance_lock(str(wd), "landuse", purpose="inner", ttl_seconds=30):
                pass

    assert exc_info.value.code == "NODIR_LOCKED"

    with maintenance_lock(str(wd), "landuse", purpose="after-release", ttl_seconds=30):
        pass


def test_thaw_and_freeze_locked_raise_value_error_on_root_mismatch(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    with maintenance_lock(str(wd), "landuse", purpose="unit", ttl_seconds=30) as lock:
        with pytest.raises(ValueError, match="maintenance lock root mismatch"):
            thaw_locked(str(wd), "soils", lock=lock)

        with pytest.raises(ValueError, match="maintenance lock root mismatch"):
            freeze_locked(str(wd), "soils", lock=lock)


def test_maintenance_lock_contends_across_grouped_and_base_paths(tmp_path: Path) -> None:
    base_wd = tmp_path / "wc1" / "runs" / "ab" / "base-run"
    child_wd = base_wd / "_pups" / "omni" / "scenarios" / "s1"
    base_wd.mkdir(parents=True, exist_ok=True)
    child_wd.mkdir(parents=True, exist_ok=True)

    with maintenance_lock(str(base_wd), "landuse", purpose="base", ttl_seconds=30):
        with pytest.raises(NoDirError) as exc_info:
            with maintenance_lock(str(child_wd), "landuse", purpose="child", ttl_seconds=30):
                pass

    assert exc_info.value.code == "NODIR_LOCKED"


def test_maintenance_lock_path_scope_compat_checks_legacy_lock(tmp_path: Path) -> None:
    base_wd = tmp_path / "wc1" / "runs" / "ab" / "base-run"
    s1 = base_wd / "_pups" / "omni" / "scenarios" / "s1"
    s2 = base_wd / "_pups" / "omni" / "scenarios" / "s2"
    (s1 / "landuse").mkdir(parents=True, exist_ok=True)
    (s2 / "landuse").mkdir(parents=True, exist_ok=True)

    with maintenance_lock(str(s1), "landuse", purpose="legacy", ttl_seconds=30):
        with pytest.raises(NoDirError) as exc_info:
            with maintenance_lock(
                str(s2),
                "landuse",
                purpose="path-compat",
                ttl_seconds=30,
                scope="effective_root_path_compat",
            ):
                pass

    assert exc_info.value.code == "NODIR_LOCKED"
