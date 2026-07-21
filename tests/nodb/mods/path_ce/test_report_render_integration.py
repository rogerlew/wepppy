"""Real Quarto render integration test (container-only; ~2 min).

Runs the full controller pipeline including an actual `quarto render` against
the austere-inaction fixtures (real geojsons committed under
tests/data/path_ce). Skipped wherever the Quarto CLI is unavailable.

This is the regression net for the seams mocks cannot cover: kernel
discovery, QMD execution, payload/env delivery, local browser assets, and —
critically — that the report's re-solve (with configured slope filters)
reproduces the job's numbers (Codex Phase 3 findings 1 and 11).
"""

from __future__ import annotations

import json
import logging
import shutil
from contextlib import nullcontext
from pathlib import Path

import pytest

pytest.importorskip("pulp")
pd = pytest.importorskip("pandas")

pytestmark = [pytest.mark.integration, pytest.mark.slow]

if shutil.which("quarto") is None:
    pytest.skip("quarto CLI not available", allow_module_level=True)

from wepppy.nodb.mods.path_ce.path_cost_effective import (
    PathCostEffective,
    _normalize_config,
)

FIXTURES = Path(__file__).resolve().parents[3] / "data" / "path_ce" / "austere_inaction"


def _assemble_run_dir(tmp_path: Path) -> Path:
    wd = tmp_path / "run"
    (wd / "omni").mkdir(parents=True)
    (wd / "watershed").mkdir()
    for name in (
        "scenarios.hillslope_summaries.parquet",
        "contrasts.out.parquet",
        "scenarios.out.parquet",
        "contrast_id_definitions.psv",
    ):
        shutil.copy(FIXTURES / name, wd / "omni" / name)
    shutil.copy(FIXTURES / "hillslopes.parquet", wd / "watershed" / "hillslopes.parquet")
    geo = wd / "dem" / "wbt"
    geo.mkdir(parents=True)
    shutil.copy(FIXTURES / "subcatchments.WGS.geojson", geo / "subcatchments.WGS.geojson")
    shutil.copy(FIXTURES / "channels.WGS.geojson", geo / "channels.WGS.geojson")
    return wd


def test_real_render_end_to_end(tmp_path):
    wd = _assemble_run_dir(tmp_path)
    controller = PathCostEffective.__new__(PathCostEffective)
    controller.wd = str(wd)
    controller.logger = logging.getLogger("tests.nodb.path_ce.render_integration")
    (wd / "path").mkdir(exist_ok=True)
    controller._path_dir = str(wd / "path")
    controller._config = _normalize_config(
        {
            "sdyd_threshold": 15.0,
            "sddc_threshold": 48.2,
            # slope filter keeps all three austere groups (26.4-31.2 deg) but
            # exercises the filter plumbing through solve + sweep + report
            "slope_range": [20.0, 35.0],
        }
    )
    controller._results = {}
    controller._status = "idle"
    controller._status_message = ""
    controller._progress = 0.0
    controller.locked = lambda: nullcontext()

    payload = controller.run()

    assert payload["report"]["html"] == "path/report/PATH_CE_Report.html"
    report_dir = wd / "path" / "report"
    html = (report_dir / "PATH_CE_Report.html").read_text(encoding="utf-8")
    assert "PATH_REPORT_CONFIG" in html
    assert "path-cost-surface" in html
    assert "treatmentLabels" in html
    # local assets shipped alongside; no papermill/-P dependency
    assert (report_dir / "static" / "js" / "vendor" / "plotly.min.js").exists()
    assert (report_dir / "static" / "js" / "vendor" / "deck.gl-8.9.31.min.js").exists()

    # the exact configured-threshold row must reproduce the job's numbers —
    # this is the filtered-consistency regression (report re-solve == job solve)
    sweep_csv = pd.read_csv(report_dir / "static" / "downloads" / "PATH_threshold_analysis_results.csv")
    exact = sweep_csv[
        (sweep_csv["sdyd_threshold"] == 15.0) & (sweep_csv["sddc_threshold"] == 48.2)
    ]
    assert len(exact) == 1, "exact configured-threshold row must be present"
    assert float(exact["total_cost"].iloc[0]) == pytest.approx(payload["total_cost"], rel=1e-9)
    assert json.loads(exact["selected_hillslopes"].iloc[0]) == payload["selected_hillslopes"]


def test_sweep_columns_parse_per_browser_contract(tmp_path, monkeypatch):
    """Fast contract check: every sweep row's JSON columns must parse.

    Rendering is unconditional now, so stub the Quarto stage — this test is
    about the sweep artifact, not the report."""
    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective.render_report",
        lambda *args, **kwargs: "path/report/PATH_CE_Report.html",
    )
    wd = _assemble_run_dir(tmp_path)
    controller = PathCostEffective.__new__(PathCostEffective)
    controller.wd = str(wd)
    controller.logger = logging.getLogger("tests.nodb.path_ce.render_integration")
    (wd / "path").mkdir(exist_ok=True)
    controller._path_dir = str(wd / "path")
    controller._config = _normalize_config(
        {"sdyd_threshold": 15.0, "sddc_threshold": 48.2}
    )
    controller._results = {}
    controller._status = "idle"
    controller._status_message = ""
    controller._progress = 0.0
    controller.locked = lambda: nullcontext()

    controller.run()
    sweep = pd.read_parquet(wd / "path" / "sweep.parquet")
    for column in ("selected_hillslopes", "treatment_hillslopes", "untreatable_ids",
                   "hillslopes_sdyd", "untreatable_sdyd_increase"):
        assert column in sweep.columns
        for value in sweep[column]:
            parsed = json.loads(value)
            assert isinstance(parsed, list)
    pairs = json.loads(sweep["hillslopes_sdyd"].iloc[0])
    assert all(len(pair) == 2 for pair in pairs)
