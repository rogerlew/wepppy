from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask, render_template

import wepppy.weppcloud.routes.nodb_api.watershed_bp as watershed_bp_module
from wepppy.topo.wbt.wbt_topaz_emulator import WbtConditioningDiagnosticsError


pytestmark = pytest.mark.unit


def test_conditioning_summary_for_report_revalidates_sidecar(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wbt_dir = tmp_path / "dem" / "wbt"
    wbt_dir.mkdir(parents=True)
    sidecar = wbt_dir / "relief.diagnostics.json"
    sidecar.write_text("{}")
    payload = {"terrain_change": {"maximum_raise": 379.0}}
    captured: dict[str, object] = {}

    def fake_load(path: str, **kwargs):
        captured["path"] = path
        captured.update(kwargs)
        return payload

    monkeypatch.setattr(watershed_bp_module, "load_conditioning_diagnostics", fake_load)
    monkeypatch.setattr(
        watershed_bp_module,
        "summarize_conditioning_diagnostics",
        lambda diagnostics, method: "Fill completed. Maximum terrain raise: 379 m.",
    )

    summary = watershed_bp_module._conditioning_summary_for_report(
        str(tmp_path), "fill"
    )

    assert summary == "Fill completed. Maximum terrain raise: 379 m."
    assert captured == {
        "path": str(sidecar),
        "method": "fill",
        "operation_id": None,
        "input_name": "dem.tif",
        "output_name": "relief.tif",
        "root_dir": str(wbt_dir),
    }


def test_conditioning_summary_for_report_omits_invalid_sidecar(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    wbt_dir = tmp_path / "dem" / "wbt"
    wbt_dir.mkdir(parents=True)
    (wbt_dir / "relief.diagnostics.json").write_text("{}")
    monkeypatch.setattr(
        watershed_bp_module,
        "load_conditioning_diagnostics",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            WbtConditioningDiagnosticsError("schema")
        ),
    )

    summary = watershed_bp_module._conditioning_summary_for_report(
        str(tmp_path), "fill"
    )

    assert summary is None
    assert "Omitting invalid terrain-conditioning diagnostics" in caplog.text


def test_channel_report_renders_conditioning_in_summary_panel_once() -> None:
    template_root = Path(watershed_bp_module.__file__).parents[2] / "templates"
    app = Flask(__name__, template_folder=str(template_root))
    map_state = type(
        "MapState",
        (),
        {
            "extent": [1, 2, 3, 4],
            "center": [2, 3],
            "utm_zone": 11,
            "utm_letter": "T",
            "ul_x": 100.0,
            "ul_y": 200.0,
            "num_cols": 10,
            "num_rows": 20,
        },
    )()
    summary = "Fill completed. Maximum terrain raise: 379 m."

    with app.app_context():
        rendered = render_template(
            "reports/channel.htm",
            map=map_state,
            conditioning_summary=summary,
        )

    assert rendered.count(summary) == 1
    assert "Terrain conditioning" in rendered
    assert 'class="wc-summary-pane__definition"' in rendered
