from __future__ import annotations

import logging
from contextlib import nullcontext
from pathlib import Path

import pytest

from wepppy.nodb.core.landuse import Landuse, LanduseMode
from wepppy.nodb.core.soils import Soils, SoilsMode

pytestmark = pytest.mark.unit


class _StopBuild(Exception):
    """Sentinel used to stop build() after preconditions are asserted."""


def test_soils_build_creates_root_before_spatial_api_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    soils = Soils.__new__(Soils)
    soils.wd = str(wd)
    soils.logger = logging.getLogger("tests.nodb.soils.root_materialization")
    soils._mode = SoilsMode.SpatialAPI
    soils.locked = lambda: nullcontext()

    def _fake_build_spatial_api(_self: Soils) -> None:
        assert Path(_self.soils_dir).is_dir(), "Soils root must exist before mode dispatch"
        raise _StopBuild()

    monkeypatch.setattr(Soils, "_build_spatial_api", _fake_build_spatial_api)

    with pytest.raises(_StopBuild):
        soils.build()

    assert (wd / "soils").is_dir()


def test_landuse_build_creates_root_before_spatial_api_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(wd)
    landuse.logger = logging.getLogger("tests.nodb.landuse.root_materialization")
    landuse._mode = LanduseMode.SpatialAPI
    landuse.locked = lambda: nullcontext()

    def _fake_build_spatial_api(_self: Landuse) -> None:
        assert Path(_self.lc_dir).is_dir(), "Landuse root must exist before mode dispatch"
        raise _StopBuild()

    monkeypatch.setattr(Landuse, "_build_spatial_api", _fake_build_spatial_api)

    with pytest.raises(_StopBuild):
        landuse.build()

    assert (wd / "landuse").is_dir()


def test_soils_clean_preserves_managed_projection_symlink_mount(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    mount_target = wd / ".nodir" / "upper" / "soils" / "token" / "data"
    mount_target.mkdir(parents=True, exist_ok=True)
    (mount_target / "old.sol").write_text("legacy", encoding="utf-8")

    soils_root = wd / "soils"
    soils_root.symlink_to(mount_target, target_is_directory=True)
    sidecar = wd / "soils.parquet"
    sidecar.write_text("stale", encoding="utf-8")

    soils = Soils.__new__(Soils)
    soils.wd = str(wd)
    soils._soils_is_vrt = True
    soils.islocked = lambda: True

    soils.clean()

    assert soils_root.is_symlink()
    assert mount_target.is_dir()
    assert list(mount_target.iterdir()) == []
    assert sidecar.exists()
    assert sidecar.read_text(encoding="utf-8") == "stale"
    assert soils._soils_is_vrt is False


def test_soils_clean_unlinks_unmanaged_symlink_without_deleting_target(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    mount_target = tmp_path / "external-soils"
    mount_target.mkdir(parents=True, exist_ok=True)
    mounted_file = mount_target / "old.sol"
    mounted_file.write_text("legacy", encoding="utf-8")

    soils_root = wd / "soils"
    soils_root.symlink_to(mount_target, target_is_directory=True)

    soils = Soils.__new__(Soils)
    soils.wd = str(wd)
    soils._soils_is_vrt = True
    soils.islocked = lambda: True

    soils.clean()

    assert not soils_root.is_symlink()
    assert soils_root.is_dir()
    assert mounted_file.exists()
    assert soils._soils_is_vrt is False


def test_landuse_clean_preserves_managed_projection_symlink_mount(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    mount_target = wd / ".nodir" / "upper" / "landuse" / "token" / "data"
    mount_target.mkdir(parents=True, exist_ok=True)
    (mount_target / "old.man").write_text("legacy", encoding="utf-8")

    landuse_root = wd / "landuse"
    landuse_root.symlink_to(mount_target, target_is_directory=True)
    sidecar = wd / "landuse.parquet"
    sidecar.write_text("stale", encoding="utf-8")

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(wd)
    landuse._landuse_is_vrt = True
    landuse.islocked = lambda: True

    landuse.clean()

    assert landuse_root.is_symlink()
    assert mount_target.is_dir()
    assert list(mount_target.iterdir()) == []
    assert sidecar.exists()
    assert sidecar.read_text(encoding="utf-8") == "stale"
    assert landuse._landuse_is_vrt is False


def test_landuse_clean_unlinks_unmanaged_symlink_without_deleting_target(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    mount_target = tmp_path / "external-landuse"
    mount_target.mkdir(parents=True, exist_ok=True)
    mounted_file = mount_target / "old.man"
    mounted_file.write_text("legacy", encoding="utf-8")

    landuse_root = wd / "landuse"
    landuse_root.symlink_to(mount_target, target_is_directory=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(wd)
    landuse._landuse_is_vrt = True
    landuse.islocked = lambda: True

    landuse.clean()

    assert not landuse_root.is_symlink()
    assert landuse_root.is_dir()
    assert mounted_file.exists()
    assert landuse._landuse_is_vrt is False
