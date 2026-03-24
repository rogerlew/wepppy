from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask
from wepppy.weppcloud.utils import cap_guard

pytestmark = pytest.mark.unit

import wepppy.weppcloud.routes.nodb_api.wepp_bp as wepp_module

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def wepp_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(wepp_module.wepp_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    class DummyContext:
        def __init__(self, root_path: str) -> None:
            self.active_root = root_path

    monkeypatch.setattr(wepp_module, "load_run_context", lambda runid, config: DummyContext(str(run_dir)))
    monkeypatch.setattr(wepp_module, "get_wd", lambda runid: str(run_dir))

    class DummyWepp:
        _instances: Dict[str, "DummyWepp"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.calls: Dict[str, Any] = {}

        @classmethod
        def getInstance(cls, wd: str) -> "DummyWepp":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def set_run_wepp_ui(self, value: bool) -> None:
            self.calls["wepp_ui"] = value

        def set_run_pmet(self, value: bool) -> None:
            self.calls["pmet"] = value

        def set_run_frost(self, value: bool) -> None:
            self.calls["frost"] = value

        def set_run_tcr(self, value: bool) -> None:
            self.calls["tcr"] = value

        def set_run_snow(self, value: bool) -> None:
            self.calls["snow"] = value

        def set_run_wepp_watershed(self, value: bool) -> None:
            self.calls["wepp_watershed"] = value

    monkeypatch.setattr(wepp_module, "Wepp", DummyWepp)

    with app.test_client() as client:
        yield client, DummyWepp, str(run_dir)

    DummyWepp._instances.clear()


@pytest.mark.parametrize(
    ("routine", "method_name"),
    [
        ("wepp_ui", "wepp_ui"),
        ("wepp_watershed", "wepp_watershed"),
        ("pmet", "pmet"),
        ("frost", "frost"),
        ("tcr", "tcr"),
        ("snow", "snow"),
    ],
)
def test_set_run_wepp_routine_accepts_json_boolean(wepp_client, routine, method_name):
    client, DummyWepp, run_dir = wepp_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_run_wepp_routine/",
        json={"routine": routine, "state": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Content": {"routine": routine, "state": True}}

    controller = DummyWepp.getInstance(run_dir)
    assert controller.calls[method_name] is True


def test_set_run_wepp_routine_rejects_non_boolean_state(wepp_client):
    client, DummyWepp, _ = wepp_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_run_wepp_routine/",
        json={"routine": "pmet", "state": "maybe"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["error"]["message"] == "state must be boolean"


def test_set_run_wepp_routine_requires_known_routine(wepp_client):
    client, DummyWepp, _ = wepp_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_run_wepp_routine/",
        json={"routine": "unknown", "state": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "routine not in" in payload["error"]["message"]


def test_set_run_wepp_routine_rejects_flowpaths_toggle(wepp_client):
    client, _, _ = wepp_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_run_wepp_routine/",
        json={"routine": "run_flowpaths", "state": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "routine not in" in payload["error"]["message"]


def test_flowpaths_loss_resource_route_is_retired(wepp_client):
    client, _, _ = wepp_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/resources/flowpaths_loss.tif")

    assert response.status_code == 404


def test_query_subcatchments_summary_returns_500_when_controller_raises(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client

    class DummyRon:
        @classmethod
        def getInstance(cls, wd: str):
            assert wd == run_dir
            return cls()

        def subs_summary(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(wepp_module, "Ron", DummyRon)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/subcatchments_summary/")
    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"]["message"] == "Error building summary"


def _touch_wepp_results(run_dir: str) -> None:
    output_dir = Path(run_dir) / "wepp" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "loss_pw0.txt").write_text("results")


def _touch_rusle_results(run_dir: str) -> None:
    rusle_dir = Path(run_dir) / "rusle"
    rusle_dir.mkdir(parents=True, exist_ok=True)
    (rusle_dir / "a_observed_rap_polaris_nomograph.tif").write_text("results")


def test_report_wepp_results_marks_stale_when_invalidated(wepp_client, monkeypatch: pytest.MonkeyPatch):
    client, _, run_dir = wepp_client
    _touch_wepp_results(run_dir)

    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyClimate:
        @classmethod
        def getInstance(cls, wd: str):
            return type("ClimateInstance", (), {"is_single_storm": False, "ss_batch_storms": None})()

    monkeypatch.setattr(wepp_module, "Climate", DummyClimate)

    class DummyRedis:
        def __init__(self, values: Dict[str, str]) -> None:
            self._values = values

        def hget(self, run_id: str, key: str):
            return self._values.get(key)

    class DummyRedisPrep:
        def __init__(self, values: Dict[str, str]) -> None:
            self.run_id = RUN_ID
            self.redis = DummyRedis(values)

        @staticmethod
        def getInstance(wd: str):
            return DummyRedisPrep(
                {
                    "timestamps:build_landuse": "200",
                    "timestamps:build_soils": "200",
                    "timestamps:build_climate": "200",
                    "timestamps:run_wepp_watershed": "100",
                }
            )

    monkeypatch.setattr(wepp_module, "RedisPrep", DummyRedisPrep)

    def fake_render_template(template_name: str, **kwargs: Any) -> str:
        assert template_name == "controls/wepp_reports.htm"
        return str(kwargs["run_results_title"])

    monkeypatch.setattr(wepp_module, "render_template", fake_render_template)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/results/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "Run Results (stale)"


def test_report_wepp_results_not_stale_when_current(wepp_client, monkeypatch: pytest.MonkeyPatch):
    client, _, run_dir = wepp_client
    _touch_wepp_results(run_dir)

    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyClimate:
        @classmethod
        def getInstance(cls, wd: str):
            return type("ClimateInstance", (), {"is_single_storm": False, "ss_batch_storms": None})()

    monkeypatch.setattr(wepp_module, "Climate", DummyClimate)

    class DummyRedis:
        def __init__(self, values: Dict[str, str]) -> None:
            self._values = values

        def hget(self, run_id: str, key: str):
            return self._values.get(key)

    class DummyRedisPrep:
        def __init__(self, values: Dict[str, str]) -> None:
            self.run_id = RUN_ID
            self.redis = DummyRedis(values)

        @staticmethod
        def getInstance(wd: str):
            return DummyRedisPrep(
                {
                    "timestamps:build_landuse": "200",
                    "timestamps:build_soils": "200",
                    "timestamps:build_climate": "200",
                    "timestamps:run_wepp_watershed": "300",
                }
            )

    monkeypatch.setattr(wepp_module, "RedisPrep", DummyRedisPrep)

    def fake_render_template(template_name: str, **kwargs: Any) -> str:
        assert template_name == "controls/wepp_reports.htm"
        return str(kwargs["run_results_title"])

    monkeypatch.setattr(wepp_module, "render_template", fake_render_template)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/results/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "Run Results"


def test_report_wepp_results_returns_500_when_template_render_raises(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client

    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyClimate:
        @classmethod
        def getInstance(cls, wd: str):
            assert wd == run_dir
            return type("ClimateInstance", (), {"is_single_storm": False, "ss_batch_storms": None})()

    monkeypatch.setattr(wepp_module, "Climate", DummyClimate)

    def _raise_file_not_found(_wd: str):
        raise FileNotFoundError()

    monkeypatch.setattr(wepp_module.RedisPrep, "getInstance", _raise_file_not_found)

    def _explode(*_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(wepp_module, "render_template", _explode)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/results/")
    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"]["message"] == "Error building reports template"


@pytest.mark.parametrize(
    "path",
    [
        f"/runs/{RUN_ID}/{CONFIG}/report/wepp/summary?output_scope=invalid",
        f"/runs/{RUN_ID}/{CONFIG}/plot/wepp/streamflow?output_scope=invalid",
        f"/runs/{RUN_ID}/{CONFIG}/report/wepp/yearly_watbal?output_scope=invalid",
        f"/runs/{RUN_ID}/{CONFIG}/report/wepp/avg_annual_watbal?output_scope=invalid",
        f"/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods?output_scope=invalid",
    ],
)
def test_wepp_report_routes_reject_invalid_output_scope(wepp_client, path, monkeypatch: pytest.MonkeyPatch):
    client, _, _ = wepp_client

    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    response = client.get(path)
    assert response.status_code == 400
    payload = response.get_json()
    assert "Invalid output_scope" in payload["error"]["message"]


def test_wepp_loss_summary_supports_roads_output_scope(wepp_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, run_dir = wepp_client

    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)
    monkeypatch.setattr(wepp_module, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyClimate:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return type("ClimateObj", (), {"is_single_storm": False})()

    class DummyRon:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return object()

    class DummyUnitizer:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return object()

    monkeypatch.setattr(wepp_module, "Climate", DummyClimate)
    monkeypatch.setattr(wepp_module, "Ron", DummyRon)
    monkeypatch.setattr(wepp_module, "Unitizer", DummyUnitizer)
    monkeypatch.setattr(wepp_module, "RonViewModel", lambda _ron: object())

    captured_scopes: Dict[str, Any] = {}

    class _DummyOutlet:
        def rows(self, include_extraneous: bool = False):
            return []

    class _DummyTabular:
        hdr = []
        units = []

        def __iter__(self):
            return iter([])

    def _outlet(wd: str, *, output_scope: str | None = None):
        captured_scopes["outlet"] = output_scope
        return _DummyOutlet()

    def _hill(wd: str, *, output_scope: str | None = None):
        captured_scopes["hill"] = output_scope
        return _DummyTabular()

    def _channel(wd: str, *, output_scope: str | None = None):
        captured_scopes["channel"] = output_scope
        return _DummyTabular()

    monkeypatch.setattr(wepp_module, "OutletSummaryReport", _outlet)
    monkeypatch.setattr(wepp_module, "HillSummaryReport", _hill)
    monkeypatch.setattr(wepp_module, "ChannelSummaryReport", _channel)

    captured_template: Dict[str, Any] = {}

    def _fake_render(template_name: str, **kwargs: Any) -> str:
        captured_template["template_name"] = template_name
        captured_template["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(wepp_module, "render_template", _fake_render)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/summary?output_scope=roads")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured_scopes == {"outlet": "roads", "hill": "roads", "channel": "roads"}
    assert captured_template["template_name"] == "reports/wepp/summary.htm"
    assert captured_template["kwargs"]["output_scope"] == "roads"


def test_avg_annual_watbal_supports_roads_output_scope(wepp_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, run_dir = wepp_client

    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)
    monkeypatch.setattr(wepp_module, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyRon:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return object()

    class DummyUnitizer:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return object()

    captured_scopes: Dict[str, Any] = {}

    class DummyWepp:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return DummyWepp()

        def report_hill_watbal(self, *, output_scope: str = "baseline"):
            captured_scopes["hill"] = output_scope
            return object()

        def report_chn_watbal(self, *, output_scope: str = "baseline"):
            captured_scopes["channel"] = output_scope
            return object()

    monkeypatch.setattr(wepp_module, "Ron", DummyRon)
    monkeypatch.setattr(wepp_module, "Unitizer", DummyUnitizer)
    monkeypatch.setattr(wepp_module, "Wepp", DummyWepp)

    captured_template: Dict[str, Any] = {}

    def _fake_render(template_name: str, **kwargs: Any) -> str:
        captured_template["template_name"] = template_name
        captured_template["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(wepp_module, "render_template", _fake_render)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/avg_annual_watbal?output_scope=roads")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured_scopes == {"hill": "roads", "channel": "roads"}
    assert captured_template["template_name"] == "reports/wepp/avg_annual_watbal.htm"
    assert captured_template["kwargs"]["output_scope"] == "roads"


def test_yearly_watbal_supports_roads_output_scope(wepp_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, run_dir = wepp_client

    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)
    monkeypatch.setattr(wepp_module, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyRon:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return object()

    class DummyUnitizer:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return object()

    captured_scopes: Dict[str, Any] = {}

    class DummyTotWatBal:
        pass

    def _totwatbal(wd: str, *, exclude_yr_indxs=None, output_scope: str = "baseline"):
        assert wd == run_dir
        captured_scopes["yearly"] = output_scope
        captured_scopes["exclude_yr_indxs"] = exclude_yr_indxs
        return DummyTotWatBal()

    monkeypatch.setattr(wepp_module, "Ron", DummyRon)
    monkeypatch.setattr(wepp_module, "Unitizer", DummyUnitizer)
    monkeypatch.setattr(wepp_module, "TotalWatbalReport", _totwatbal)

    captured_template: Dict[str, Any] = {}

    def _fake_render(template_name: str, **kwargs: Any) -> str:
        captured_template["template_name"] = template_name
        captured_template["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(wepp_module, "render_template", _fake_render)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/yearly_watbal?output_scope=roads")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured_scopes["yearly"] == "roads"
    assert captured_template["template_name"] == "reports/wepp/yearly_watbal.htm"
    assert captured_template["kwargs"]["output_scope"] == "roads"


def test_streamflow_supports_roads_output_scope(wepp_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, run_dir = wepp_client

    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)
    monkeypatch.setattr(wepp_module, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyRon:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return object()

    class DummyUnitizer:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return object()

    monkeypatch.setattr(wepp_module, "Ron", DummyRon)
    monkeypatch.setattr(wepp_module, "Unitizer", DummyUnitizer)
    monkeypatch.setattr(wepp_module, "_exists", lambda path: True)
    monkeypatch.setattr(wepp_module, "resolve_run_context", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(wepp_module, "QueryRequest", lambda **kwargs: kwargs)

    captured_query: Dict[str, Any] = {}

    def _fake_run_query(_run_context: Any, query: Dict[str, Any]):
        captured_query["payload"] = query
        return type("QueryResult", (), {"formatted": {"series": []}, "sql": "SELECT 1"})()

    monkeypatch.setattr(wepp_module, "run_query", _fake_run_query)

    captured_template: Dict[str, Any] = {}

    def _fake_render(template_name: str, **kwargs: Any) -> str:
        captured_template["template_name"] = template_name
        captured_template["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(wepp_module, "render_template", _fake_render)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/plot/wepp/streamflow?output_scope=roads")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured_query["payload"]["datasets"][0]["path"] == "wepp/roads/output/interchange/totalwatsed3.parquet"
    assert captured_template["template_name"] == "reports/wepp/daily_streamflow_graph.htm"
    assert captured_template["kwargs"]["output_scope"] == "roads"


def test_return_periods_supports_roads_output_scope(wepp_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, run_dir = wepp_client

    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)
    monkeypatch.setattr(wepp_module, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyClimate:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return type("ClimateObj", (), {"years": 30})()

    class DummyRon:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return object()

    class DummyUnitizer:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return object()

    class DummyWatershed:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return type("WatershedObj", (), {"translator_factory": staticmethod(lambda: object())})()

    captured_scopes: Dict[str, Any] = {}

    class DummyReport:
        return_periods = {"Peak Discharge": {2: 1.0, 5: 2.0}}

    class DummyWepp:
        chn_topaz_ids_of_interest = []

        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return DummyWepp()

        def report_return_periods(self, **kwargs: Any):
            captured_scopes["return_periods"] = kwargs.get("output_scope")
            return DummyReport()

    monkeypatch.setattr(wepp_module, "Climate", DummyClimate)
    monkeypatch.setattr(wepp_module, "Ron", DummyRon)
    monkeypatch.setattr(wepp_module, "Unitizer", DummyUnitizer)
    monkeypatch.setattr(wepp_module, "Watershed", DummyWatershed)
    monkeypatch.setattr(wepp_module, "Wepp", DummyWepp)
    monkeypatch.setattr(wepp_module, "parse_rec_intervals", lambda *_args, **_kwargs: [2, 5])

    captured_template: Dict[str, Any] = {}

    def _fake_render(template_name: str, **kwargs: Any) -> str:
        captured_template["template_name"] = template_name
        captured_template["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(wepp_module, "render_template", _fake_render)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods?output_scope=roads")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured_scopes["return_periods"] == "roads"
    assert captured_template["template_name"] == "reports/wepp/return_periods.htm"
    assert captured_template["kwargs"]["output_scope"] == "roads"


def test_report_rusle_results_returns_empty_when_outputs_missing(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = wepp_client
    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/rusle/results/")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == ""


def test_report_rusle_results_marks_stale_when_invalidated(wepp_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, run_dir = wepp_client
    _touch_rusle_results(run_dir)

    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyRedis:
        def __init__(self, values: Dict[str, str]) -> None:
            self._values = values

        def hget(self, run_id: str, key: str):
            return self._values.get(key)

    class DummyRedisPrep:
        def __init__(self, values: Dict[str, str]) -> None:
            self.run_id = RUN_ID
            self.redis = DummyRedis(values)

        @staticmethod
        def getInstance(wd: str):
            return DummyRedisPrep(
                {
                    "timestamps:build_climate": "200",
                    "timestamps:build_rusle": "100",
                }
            )

    monkeypatch.setattr(wepp_module, "RedisPrep", DummyRedisPrep)

    def fake_render_template(template_name: str, **kwargs: Any) -> str:
        assert template_name == "controls/rusle_reports.htm"
        return str(kwargs["run_results_title"])

    monkeypatch.setattr(wepp_module, "render_template", fake_render_template)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/rusle/results/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "Run Results (stale)"


def test_report_rusle_results_not_stale_when_current(wepp_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, run_dir = wepp_client
    _touch_rusle_results(run_dir)

    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyRedis:
        def __init__(self, values: Dict[str, str]) -> None:
            self._values = values

        def hget(self, run_id: str, key: str):
            return self._values.get(key)

    class DummyRedisPrep:
        def __init__(self, values: Dict[str, str]) -> None:
            self.run_id = RUN_ID
            self.redis = DummyRedis(values)

        @staticmethod
        def getInstance(wd: str):
            return DummyRedisPrep(
                {
                    "timestamps:build_climate": "200",
                    "timestamps:build_rusle": "300",
                }
            )

    monkeypatch.setattr(wepp_module, "RedisPrep", DummyRedisPrep)

    def fake_render_template(template_name: str, **kwargs: Any) -> str:
        assert template_name == "controls/rusle_reports.htm"
        return str(kwargs["run_results_title"])

    monkeypatch.setattr(wepp_module, "render_template", fake_render_template)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/rusle/results/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "Run Results"


def test_query_channels_summary_returns_500_when_controller_raises(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client

    class DummyRon:
        @classmethod
        def getInstance(cls, wd: str):
            assert wd == run_dir
            return cls()

        def chns_summary(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(wepp_module, "Ron", DummyRon)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/channels_summary/")
    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"]["message"] == "Error building summary"
