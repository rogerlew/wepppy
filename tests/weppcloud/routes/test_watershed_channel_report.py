from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask, render_template

import wepppy.weppcloud.routes.nodb_api.watershed_bp as watershed_bp_module
from wepppy.topo.wbt.wbt_topaz_emulator import WbtConditioningDiagnosticsError


pytestmark = pytest.mark.unit


def test_conditioning_diagnostics_for_report_revalidates_and_formats_sidecar(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wbt_dir = tmp_path / "dem" / "wbt"
    wbt_dir.mkdir(parents=True)
    sidecar = wbt_dir / "relief.diagnostics.json"
    sidecar.write_text("{}")
    payload = {
        "terrain_change": {
            "valid_cell_count": 1000,
            "raised_cell_count": 108,
            "lowered_cell_count": 0,
            "maximum_raise": 379.227,
            "maximum_cut": 0.0,
        },
        "conditioning": {
            "detected_low_point_count": 352,
            "filled_depression_count": 352,
            "skipped_depression_count": 0,
            "flat_gradient_applied": False,
        },
        "parameters": {},
    }
    captured: dict[str, object] = {}

    def fake_load(path: str, **kwargs):
        captured["path"] = path
        captured.update(kwargs)
        return payload

    monkeypatch.setattr(watershed_bp_module, "load_conditioning_diagnostics", fake_load)
    diagnostics = watershed_bp_module._conditioning_diagnostics_for_report(
        str(tmp_path), "fill"
    )

    assert diagnostics is not None
    assert diagnostics["rows"] == [
        {"label": "Conditioning method", "value": "Fill"},
        {"label": "Maximum terrain raise", "value": "379 m"},
        {"label": "Maximum terrain cut", "value": "0.00 m"},
        {"label": "DEM area raised", "value": "10.8% of DEM (108 cells)"},
        {"label": "DEM area lowered", "value": "0.0% of DEM (0 cells)"},
        {"label": "Detected low points", "value": "352"},
        {"label": "Depressions filled", "value": "352"},
        {"label": "Depressions skipped", "value": "0"},
        {"label": "Flat-gradient adjustment", "value": "Not applied"},
    ]
    assert captured == {
        "path": str(sidecar),
        "method": "fill",
        "operation_id": None,
        "input_name": "dem.tif",
        "output_name": "relief.tif",
        "root_dir": str(wbt_dir),
    }


def test_conditioning_diagnostics_for_report_omits_invalid_sidecar(
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

    diagnostics = watershed_bp_module._conditioning_diagnostics_for_report(
        str(tmp_path), "fill"
    )

    assert diagnostics is None
    assert "Omitting invalid terrain-conditioning diagnostics" in caplog.text


def test_channel_report_renders_conditioning_in_its_own_summary_table() -> None:
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
    diagnostics = {
        "rows": [
            {"label": "Conditioning method", "value": "Fill"},
            {"label": "Maximum terrain raise", "value": "379 m"},
            {"label": "DEM area raised", "value": "10.8% of DEM (108 cells)"},
        ]
    }

    with app.app_context():
        rendered = render_template(
            "reports/channel.htm",
            map=map_state,
            conditioning_diagnostics=diagnostics,
        )

    assert "Terrain Conditioning Diagnostics" in rendered
    assert rendered.count('class="wc-summary-pane"') == 2
    assert rendered.index("Map Size (px)") < rendered.index(
        "Terrain Conditioning Diagnostics"
    )
    assert rendered.count('class="wc-summary-pane__definition"') == 8
    assert "Maximum terrain raise" in rendered
    assert "379 m" in rendered
    assert "10.8% of DEM (108 cells)" in rendered


def test_channel_report_omits_conditioning_table_without_diagnostics() -> None:
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

    with app.app_context():
        rendered = render_template(
            "reports/channel.htm",
            map=map_state,
            conditioning_diagnostics=None,
        )

    assert rendered.count('class="wc-summary-pane"') == 1
    assert "Terrain Conditioning Diagnostics" not in rendered
