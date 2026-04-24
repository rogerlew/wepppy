from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

arc_export_module = importlib.import_module("wepppy.export.arc_export")

pytestmark = pytest.mark.unit


class _StopAfterAshPostLookup(RuntimeError):
    """Sentinel exception used to stop legacy export after setup."""


def test_legacy_arc_export_looks_up_ashpost_without_nameerror(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ash_post_lookup = {"called": False}
    ron = SimpleNamespace(
        name="demo-run",
        export_legacy_arc_dir=str(tmp_path / "legacy_arc"),
        topaz_wd=str(tmp_path / "topaz"),
        map=SimpleNamespace(srid=32611),
    )

    monkeypatch.setattr(
        arc_export_module,
        "Ron",
        SimpleNamespace(getInstance=lambda _wd: ron),
    )
    monkeypatch.setattr(
        arc_export_module,
        "Wepp",
        SimpleNamespace(getInstance=lambda _wd: SimpleNamespace()),
    )
    monkeypatch.setattr(
        arc_export_module,
        "Watershed",
        SimpleNamespace(
            getInstance=lambda _wd: SimpleNamespace(translator_factory=lambda: object())
        ),
    )
    monkeypatch.setattr(
        arc_export_module,
        "Ash",
        SimpleNamespace(tryGetInstance=lambda _wd: None),
    )

    def _lookup_ashpost(_wd: str) -> None:
        ash_post_lookup["called"] = True
        return None

    # Keep `raising=True` so this test fails if arc_export no longer defines `AshPost`.
    monkeypatch.setattr(
        arc_export_module,
        "AshPost",
        SimpleNamespace(tryGetInstance=_lookup_ashpost),
    )

    def _stop_after_lookup(_path: str) -> None:
        raise _StopAfterAshPostLookup

    monkeypatch.setattr(arc_export_module.os, "mkdir", _stop_after_lookup)

    with pytest.raises(_StopAfterAshPostLookup):
        arc_export_module.legacy_arc_export(str(tmp_path))

    assert ash_post_lookup["called"] is True
