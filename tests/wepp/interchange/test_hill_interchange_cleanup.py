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
