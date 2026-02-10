from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask, render_template


pytestmark = pytest.mark.unit


def _make_template_app() -> Flask:
    template_root = Path(__file__).resolve().parents[2] / "wepppy" / "weppcloud" / "templates"
    app = Flask(__name__, template_folder=str(template_root))
    # Minimal globals used by the omni report templates.
    app.jinja_env.globals["unitizer_units"] = lambda units: units
    app.jinja_env.globals["unitizer"] = lambda value, _units: value
    return app


def test_omni_scenarios_summary_preserves_composite_parent_runid() -> None:
    app = _make_template_app()
    scenarios = [
        {
            "name": "treated",
            "water_discharge": {"value": 1, "unit": "m^3/yr"},
            "soil_loss": {"value": 2, "unit": "tonne/yr"},
        }
    ]

    with app.app_context():
        rendered = render_template(
            "reports/omni/omni_scenarios_summary.htm",
            runid="batch;;spring-2025;;run-001;;omni;;undisturbed",
            config="cfg1",
            site_prefix="",
            scenarios=scenarios,
        )

    assert "/runs/batch;;spring-2025;;run-001;;omni;;treated/cfg1/" in rendered


def test_omni_contrasts_summary_preserves_composite_parent_runid() -> None:
    app = _make_template_app()
    report = {
        "selection_mode": "cumulative",
        "items": [
            {
                "contrast_id": 3,
                "topaz_id": "1",
                "water_discharge": {"value": 1, "unit": "m^3/yr"},
                "soil_loss": {"value": 2, "unit": "tonne/yr"},
            }
        ],
    }

    with app.app_context():
        rendered = render_template(
            "reports/omni/omni_contrasts_summary.htm",
            runid="batch;;spring-2025;;run-001",
            config="cfg1",
            site_prefix="",
            report=report,
        )

    assert "/runs/batch;;spring-2025;;run-001;;omni-contrast;;3/cfg1/" in rendered

