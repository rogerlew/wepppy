from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from .module_loader import cleanup_import_state, load_module

pytestmark = pytest.mark.unit


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


def test_cleanup_hillslope_sources_removes_pass_and_core_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodb_pkg = types.ModuleType("wepppy.nodb")
    nodb_pkg.__path__ = []
    core_pkg = types.ModuleType("wepppy.nodb.core")
    core_pkg.__path__ = []
    watershed_stub = types.ModuleType("wepppy.nodb.core.watershed")

    class _Watershed:
        @staticmethod
        def getInstance(_wd: str):
            raise RuntimeError("stub")

    watershed_stub.Watershed = _Watershed

    monkeypatch.setitem(sys.modules, "wepppy.nodb", nodb_pkg)
    monkeypatch.setitem(sys.modules, "wepppy.nodb.core", core_pkg)
    monkeypatch.setitem(sys.modules, "wepppy.nodb.core.watershed", watershed_stub)

    hill_interchange = load_module(
        "wepppy.wepp.interchange.hill_interchange",
        "wepppy/wepp/interchange/hill_interchange.py",
    )
    cleanup_hillslope_sources = hill_interchange._cleanup_hillslope_sources

    _touch(tmp_path / "H1.pass.dat")
    _touch(tmp_path / "H2.pass.dat")
    _touch(tmp_path / "H1.ebe.dat")
    _touch(tmp_path / "H1.element.dat")
    _touch(tmp_path / "H1.loss.dat")
    _touch(tmp_path / "H1.soil.dat")
    _touch(tmp_path / "H1.wat.dat")

    try:
        cleanup_hillslope_sources(
            tmp_path,
            run_loss_interchange=False,
            run_soil_interchange=False,
            run_wat_interchange=False,
        )
    finally:
        cleanup_import_state()

    assert not (tmp_path / "H1.pass.dat").exists()
    assert not (tmp_path / "H2.pass.dat").exists()
    assert not (tmp_path / "H1.ebe.dat").exists()
    assert not (tmp_path / "H1.element.dat").exists()

    # Optional outputs are only removed when their interchange writers are enabled.
    assert (tmp_path / "H1.loss.dat").exists()
    assert (tmp_path / "H1.soil.dat").exists()
    assert (tmp_path / "H1.wat.dat").exists()


def test_cleanup_hillslope_sources_for_completed_interchange_only_removes_completed_families(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodb_pkg = types.ModuleType("wepppy.nodb")
    nodb_pkg.__path__ = []
    core_pkg = types.ModuleType("wepppy.nodb.core")
    core_pkg.__path__ = []
    watershed_stub = types.ModuleType("wepppy.nodb.core.watershed")

    class _Watershed:
        @staticmethod
        def getInstance(_wd: str):
            raise RuntimeError("stub")

    watershed_stub.Watershed = _Watershed

    monkeypatch.setitem(sys.modules, "wepppy.nodb", nodb_pkg)
    monkeypatch.setitem(sys.modules, "wepppy.nodb.core", core_pkg)
    monkeypatch.setitem(sys.modules, "wepppy.nodb.core.watershed", watershed_stub)

    hill_interchange = load_module(
        "wepppy.wepp.interchange.hill_interchange",
        "wepppy/wepp/interchange/hill_interchange.py",
    )
    cleanup_hillslope_sources_for_completed_interchange = (
        hill_interchange.cleanup_hillslope_sources_for_completed_interchange
    )

    for path in (
        tmp_path / "H1.pass.dat",
        tmp_path / "H1.ebe.dat",
        tmp_path / "H1.element.dat",
        tmp_path / "H1.loss.dat",
        tmp_path / "H1.soil.dat",
        tmp_path / "H1.wat.dat",
    ):
        _touch(path)

    for path in (
        tmp_path / "interchange" / "H.pass.parquet",
        tmp_path / "interchange" / "H.ebe.parquet",
        tmp_path / "interchange" / "H.element.parquet",
        tmp_path / "interchange" / "H.loss.parquet",
    ):
        _touch(path)

    try:
        cleaned_groups = cleanup_hillslope_sources_for_completed_interchange(tmp_path)
    finally:
        cleanup_import_state()

    assert cleaned_groups == ["pass", "ebe", "element", "loss"]
    assert not (tmp_path / "H1.pass.dat").exists()
    assert not (tmp_path / "H1.ebe.dat").exists()
    assert not (tmp_path / "H1.element.dat").exists()
    assert not (tmp_path / "H1.loss.dat").exists()
    assert (tmp_path / "H1.soil.dat").exists()
    assert (tmp_path / "H1.wat.dat").exists()


def test_cleanup_hillslope_sources_rejects_invalid_pass_family(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodb_pkg = types.ModuleType("wepppy.nodb")
    nodb_pkg.__path__ = []
    core_pkg = types.ModuleType("wepppy.nodb.core")
    core_pkg.__path__ = []
    watershed_stub = types.ModuleType("wepppy.nodb.core.watershed")

    class _Watershed:
        @staticmethod
        def getInstance(_wd: str):
            raise RuntimeError("stub")

    watershed_stub.Watershed = _Watershed

    monkeypatch.setitem(sys.modules, "wepppy.nodb", nodb_pkg)
    monkeypatch.setitem(sys.modules, "wepppy.nodb.core", core_pkg)
    monkeypatch.setitem(sys.modules, "wepppy.nodb.core.watershed", watershed_stub)

    hill_interchange = load_module(
        "wepppy.wepp.interchange.hill_interchange",
        "wepppy/wepp/interchange/hill_interchange.py",
    )
    cleanup_hillslope_sources = hill_interchange._cleanup_hillslope_sources

    with pytest.raises(ValueError, match="pass_family must be 'legacy_ascii' or 'hbp'"):
        cleanup_hillslope_sources(
            tmp_path,
            pass_family="auto",
            run_loss_interchange=False,
            run_soil_interchange=False,
            run_wat_interchange=False,
        )
    cleanup_import_state()


def test_hillslope_interchange_forwards_worker_bound_to_every_converter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hill_interchange = load_module(
        "wepppy.wepp.interchange.hill_interchange",
        "wepppy/wepp/interchange/hill_interchange.py",
    )
    calls: list[tuple[str, int | None]] = []

    def _writer(name: str):
        def _fake_writer(base: Path, **kwargs):
            calls.append((name, kwargs.get("max_workers")))
            target = Path(base) / "interchange" / f"H.{name}.parquet"
            _touch(target)
            return target

        return _fake_writer

    for name in ("pass", "ebe", "element", "loss", "soil", "wat"):
        monkeypatch.setattr(
            hill_interchange,
            f"run_wepp_hillslope_{name}_interchange",
            _writer(name),
        )
    monkeypatch.setattr(hill_interchange, "_expected_hillslopes", lambda _base: 3)
    monkeypatch.setattr(hill_interchange, "remove_incompatible_interchange", lambda _path: None)
    monkeypatch.setattr(hill_interchange, "write_version_manifest", lambda _path: None)
    monkeypatch.setattr(hill_interchange, "_update_catalog_entry", None)

    try:
        result = hill_interchange.run_wepp_hillslope_interchange(
            tmp_path,
            max_workers=7,
        )
    finally:
        cleanup_import_state()

    assert result == tmp_path / "interchange"
    assert calls == [
        ("pass", 7),
        ("ebe", 7),
        ("element", 7),
        ("loss", 7),
        ("soil", 7),
        ("wat", 7),
    ]
