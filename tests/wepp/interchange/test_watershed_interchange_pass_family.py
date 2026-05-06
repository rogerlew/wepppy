from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.wepp.interchange import watershed_interchange as watershed_interchange_module

pytestmark = pytest.mark.unit


def _install_stubbed_tasks(monkeypatch: pytest.MonkeyPatch, *, calls: list[str]) -> None:
    def _make_stub(name: str):
        def _stub(_base: Path, **_kwargs) -> None:
            calls.append(name)

        return _stub

    monkeypatch.setattr(
        watershed_interchange_module,
        "run_wepp_watershed_pass_interchange",
        _make_stub("pass"),
    )
    monkeypatch.setattr(
        watershed_interchange_module,
        "run_wepp_watershed_ebe_interchange",
        _make_stub("ebe"),
    )
    monkeypatch.setattr(
        watershed_interchange_module,
        "run_wepp_watershed_chanwb_interchange",
        _make_stub("chanwb"),
    )
    monkeypatch.setattr(
        watershed_interchange_module,
        "run_wepp_watershed_chan_peak_interchange",
        _make_stub("chan_peak"),
    )
    monkeypatch.setattr(
        watershed_interchange_module,
        "run_wepp_watershed_chnwb_interchange",
        _make_stub("chnwb"),
    )
    monkeypatch.setattr(
        watershed_interchange_module,
        "run_wepp_watershed_soil_interchange",
        _make_stub("soil"),
    )
    monkeypatch.setattr(
        watershed_interchange_module,
        "run_wepp_watershed_loss_interchange",
        _make_stub("loss"),
    )
    monkeypatch.setattr(
        watershed_interchange_module,
        "remove_incompatible_interchange",
        lambda _path: None,
    )
    monkeypatch.setattr(
        watershed_interchange_module,
        "write_version_manifest",
        lambda _path: None,
    )
    monkeypatch.setattr(
        watershed_interchange_module,
        "_update_catalog_entry",
        None,
    )


def test_run_watershed_interchange_hbp_skips_pass_and_writes_not_present_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    calls: list[str] = []
    _install_stubbed_tasks(monkeypatch, calls=calls)

    interchange_dir = watershed_interchange_module.run_wepp_watershed_interchange(
        output_dir,
        pass_family="hbp",
    )

    assert interchange_dir == output_dir / "interchange"
    assert "pass" not in calls
    assert set(calls) == {"ebe", "chanwb", "chan_peak", "chnwb", "soil", "loss"}

    status_payload = json.loads(
        (interchange_dir / watershed_interchange_module.PASS_STATUS_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert status_payload["artifact"] == "pass_pw0.txt"
    assert status_payload["status"] == "not_present"
    assert status_payload["pass_family"] == "hbp"


def test_run_watershed_interchange_hbp_marks_existing_pass_as_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "pass_pw0.txt").write_text("legacy\n", encoding="ascii")
    calls: list[str] = []
    _install_stubbed_tasks(monkeypatch, calls=calls)

    watershed_interchange_module.run_wepp_watershed_interchange(
        output_dir,
        pass_family="hbp",
    )

    status_payload = json.loads(
        (output_dir / "interchange" / watershed_interchange_module.PASS_STATUS_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert status_payload["status"] == "ignored"
    assert "pass" not in calls


def test_run_watershed_interchange_legacy_runs_pass_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    calls: list[str] = []
    _install_stubbed_tasks(monkeypatch, calls=calls)

    watershed_interchange_module.run_wepp_watershed_interchange(
        output_dir,
        pass_family="legacy_ascii",
    )

    assert "pass" in calls
    assert not (output_dir / "interchange" / watershed_interchange_module.PASS_STATUS_FILENAME).exists()
