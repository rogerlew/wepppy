from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, Tuple

import pytest

pytest.importorskip("flask")
from flask import Flask

pytestmark = pytest.mark.unit

RUN_ID = "demo-run"
CONFIG = "live"

try:
    import wepppy.weppcloud.routes.nodb_api.rhem_bp as rhem_module
except ImportError:  # pragma: no cover - blueprint dependencies missing
    pytest.skip("RHEM blueprint dependencies missing", allow_module_level=True)


@pytest.fixture()
def rhem_client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Tuple[Any, Dict[str, Any], Any]:
    captured: Dict[str, Any] = {"render_calls": [], "authorize": [], "glob_patterns": []}
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    captured["wd"] = str(run_dir)

    def fake_authorize(runid: str, config: str) -> None:
        captured["authorize"].append((runid, config))

    monkeypatch.setattr(rhem_module, "authorize", fake_authorize)

    def fake_render_template(template: str, *args: Any, **kwargs: Any) -> str:
        captured["render_calls"].append((template, args, kwargs))
        return f"render:{template}"

    monkeypatch.setattr(rhem_module, "render_template", fake_render_template)

    def fake_glob(pattern: str):
        captured["glob_patterns"].append(pattern)
        return ["sum1", "sum2"]

    monkeypatch.setattr(rhem_module, "glob", fake_glob)
    monkeypatch.setattr(rhem_module, "get_wd", lambda runid: str(run_dir))

    class DummyRon:
        _instances: Dict[str, "DummyRon"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.mods = ["rhem"]

        @classmethod
        def getInstance(cls, wd: str) -> "DummyRon":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(rhem_module, "Ron", DummyRon)

    class DummyRhemPost:
        _instances: Dict[str, "DummyRhemPost"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.queries: list[str] = []

        @classmethod
        def getInstance(cls, wd: str) -> "DummyRhemPost":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def query_sub_val(self, metric: str) -> Dict[str, str]:
            self.queries.append(metric)
            return {"metric": metric}

    monkeypatch.setattr(rhem_module, "RhemPost", DummyRhemPost)

    class DummyUnitizer:
        _instances: Dict[str, "DummyUnitizer"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd

        @classmethod
        def getInstance(cls, wd: str) -> "DummyUnitizer":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(rhem_module, "Unitizer", DummyUnitizer)
    monkeypatch.setattr(rhem_module, "UNITIZER_PRECISIONS", {"depth": 2})
    monkeypatch.setattr(rhem_module, "current_user", SimpleNamespace(name="tester"))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(rhem_module.rhem_bp)

    with app.test_client() as client:
        yield client, captured, DummyRhemPost


def latest_render(captured: Dict[str, Any]) -> Tuple[str, Tuple[Any, ...], Dict[str, Any]]:
    assert captured["render_calls"], "Expected render_template to be called."
    return captured["render_calls"][-1]


def test_report_rhem_results_renders_template(rhem_client):
    client, captured, _ = rhem_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/rhem/results/")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "render:controls/rhem_reports.htm"
    template, args, kwargs = latest_render(captured)
    assert template == "controls/rhem_reports.htm"
    assert kwargs == {"runid": RUN_ID, "config": CONFIG}
    assert captured["authorize"] == [(RUN_ID, CONFIG)]


def test_report_rhem_run_summary_provides_context(rhem_client):
    client, captured, DummyRhemPost = rhem_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/rhem/run_summary/")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "render:reports/rhem_run_summary.htm"
    template, args, kwargs = latest_render(captured)
    assert template == "reports/rhem_run_summary.htm"
    assert args == ()
    assert kwargs["runid"] == RUN_ID
    assert kwargs["config"] == CONFIG
    assert kwargs["subs_n"] == 2
    assert isinstance(kwargs["rhempost"], DummyRhemPost)
    assert kwargs["ron"].wd.endswith(RUN_ID)
    assert captured["glob_patterns"][-1].endswith("rhem/output/*.sum")


def test_report_rhem_avg_annuals_includes_unitizer(rhem_client):
    client, captured, _ = rhem_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/rhem/summary/")

    assert response.status_code == 200
    template, args, kwargs = latest_render(captured)
    assert template == "reports/rhem/avg_annual_summary.htm"
    assert kwargs["unitizer_nodb"].wd.endswith(RUN_ID)
    assert kwargs["precisions"] == {"depth": 2}
    assert kwargs["user"].name == "tester"


def test_report_rhem_return_periods_uses_unitizer(rhem_client):
    client, captured, _ = rhem_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/rhem/return_periods/")

    assert response.status_code == 200
    template, args, kwargs = latest_render(captured)
    assert template == "reports/rhem/return_periods.htm"
    assert kwargs["unitizer_nodb"].wd.endswith(RUN_ID)
    assert kwargs["ron"].wd.endswith(RUN_ID)


def test_query_rhem_runoff_uses_rhempost(rhem_client):
    client, captured, DummyRhemPost = rhem_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/rhem/runoff/subcatchments/")

    assert response.status_code == 200
    assert response.get_json() == {"metric": "runoff"}
    instance = DummyRhemPost.getInstance(captured["wd"])
    assert "runoff" in instance.queries


def test_query_rhem_sediment_and_soil_loss(rhem_client):
    client, captured, DummyRhemPost = rhem_client

    response_sed = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/rhem/sed_yield/subcatchments/")
    response_soil = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/rhem/soil_loss/subcatchments/")

    assert response_sed.get_json() == {"metric": "sed_yield"}
    assert response_soil.get_json() == {"metric": "soil_loss"}
    instance = DummyRhemPost.getInstance(captured["wd"])
    assert "sed_yield" in instance.queries
    assert "soil_loss" in instance.queries
