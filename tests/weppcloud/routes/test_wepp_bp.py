from __future__ import annotations

from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask

pytestmark = pytest.mark.unit

import wepppy.weppcloud.routes.nodb_api.wepp_bp as wepp_module
import wepppy.weppcloud.routes.rq.api.api as wepp_rq_module

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

        def set_run_flowpaths(self, value: bool) -> None:
            self.calls["run_flowpaths"] = value

    monkeypatch.setattr(wepp_module, "Wepp", DummyWepp)

    with app.test_client() as client:
        yield client, DummyWepp, str(run_dir)

    DummyWepp._instances.clear()


@pytest.mark.parametrize(
    ("routine", "method_name"),
    [
        ("wepp_ui", "wepp_ui"),
        ("pmet", "pmet"),
        ("frost", "frost"),
        ("tcr", "tcr"),
        ("snow", "snow"),
        ("run_flowpaths", "run_flowpaths"),
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
    assert payload == {"Success": True, "Content": {"routine": routine, "state": True}}

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
    assert payload["Success"] is False
    assert payload["Error"] == "state must be boolean"


def test_set_run_wepp_routine_requires_known_routine(wepp_client):
    client, DummyWepp, _ = wepp_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_run_wepp_routine/",
        json={"routine": "unknown", "state": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is False
    assert "routine not in" in payload["Error"]


@pytest.fixture()
def run_wepp_api_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    rq_environment,
):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(wepp_rq_module.rq_api_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    monkeypatch.setattr(wepp_rq_module, "get_wd", lambda runid: str(run_dir))

    class DummyLock:
        def __init__(self, owner):
            self.owner = owner

        def __enter__(self):
            return self.owner

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWepp:
        _instances: Dict[str, "DummyWepp"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.parse_inputs_payload: Dict[str, Any] | None = None
            self._prep_details_on_run_completion = None
            self._arc_export_on_run_completion = None
            self._legacy_arc_export_on_run_completion = None
            self._dss_export_on_run_completion = None
            self._dss_excluded_channel_orders: list[int] | None = None

        @classmethod
        def getInstance(cls, wd: str) -> "DummyWepp":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def parse_inputs(self, payload: Dict[str, Any]) -> None:
            self.parse_inputs_payload = payload

        def locked(self):
            return DummyLock(self)

    monkeypatch.setattr(wepp_rq_module, "Wepp", DummyWepp)

    class DummySoils:
        _instances: Dict[str, "DummySoils"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.clip_soils: bool | None = None
            self.clip_soils_depth: int | None = None
            self.initial_sat: float | None = None

        @classmethod
        def getInstance(cls, wd: str) -> "DummySoils":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(wepp_rq_module, "Soils", DummySoils)

    class DummyWatershed:
        _instances: Dict[str, "DummyWatershed"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.clip_hillslopes: bool | None = None
            self.clip_hillslope_length: int | None = None

        @classmethod
        def getInstance(cls, wd: str) -> "DummyWatershed":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(wepp_rq_module, "Watershed", DummyWatershed)

    import wepppy.nodb.mods.revegetation as reveg_module

    class DummyRevegetation:
        _instances: Dict[str, "DummyRevegetation"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.last_loaded: str | None = None

        @classmethod
        def getInstance(cls, wd: str) -> "DummyRevegetation":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def load_cover_transform(self, scenario: str) -> None:
            self.last_loaded = scenario

    monkeypatch.setattr(reveg_module, "Revegetation", DummyRevegetation)

    env = rq_environment
    env.patch_module(monkeypatch, wepp_rq_module, default_job_id="job-123")

    class DummyTaskEnum:
        run_wepp_hillslopes = "run_wepp_hillslopes"
        run_wepp_watershed = "run_wepp_watershed"
        run_omni_scenarios = "run_omni_scenarios"
        run_path_cost_effective = "run_path_cost_effective"

    monkeypatch.setattr(wepp_rq_module, "TaskEnum", DummyTaskEnum)

    def dummy_run_wepp_rq(runid: str) -> None:
        return None

    monkeypatch.setattr(wepp_rq_module, "run_wepp_rq", dummy_run_wepp_rq)

    with app.test_client() as client:
        yield client, {
            "run_dir": str(run_dir),
            "wepp_cls": DummyWepp,
            "soils_cls": DummySoils,
            "watershed_cls": DummyWatershed,
            "reveg_cls": reveg_module.Revegetation,
            "env": env,
            "run_wepp_rq": dummy_run_wepp_rq,
        }

    DummyWepp._instances.clear()
    DummySoils._instances.clear()
    DummyWatershed._instances.clear()
    reveg_module.Revegetation._instances.clear()


def test_run_wepp_accepts_json_payload(run_wepp_api_client):
    client, ctx = run_wepp_api_client

    payload = {
        "clip_soils": True,
        "clip_soils_depth": 42,
        "clip_hillslopes": False,
        "clip_hillslope_length": 15,
        "initial_sat": 0.67,
        "reveg_scenario": "user_cover_transform",
        "prep_details_on_run_completion": True,
        "arc_export_on_run_completion": False,
        "legacy_arc_export_on_run_completion": True,
        "dss_export_on_run_completion": True,
        "dss_export_exclude_order_1": True,
        "dss_export_exclude_order_3": True,
        "channel_critical_shear": "12.5",
        "kslast": "None",
    }

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/run_wepp",
        json=payload,
    )

    assert response.status_code == 200
    assert response.get_json() == {"Success": True, "job_id": "job-123"}

    run_dir = ctx["run_dir"]
    wepp_instance = ctx["wepp_cls"].getInstance(run_dir)
    assert wepp_instance.parse_inputs_payload is not None
    assert wepp_instance.parse_inputs_payload.get("channel_critical_shear") == "12.5"
    assert "clip_soils" not in wepp_instance.parse_inputs_payload
    assert wepp_instance._prep_details_on_run_completion is True
    assert wepp_instance._arc_export_on_run_completion is False
    assert wepp_instance._legacy_arc_export_on_run_completion is True
    assert wepp_instance._dss_export_on_run_completion is True
    assert wepp_instance._dss_excluded_channel_orders == [1, 3]

    soils = ctx["soils_cls"].getInstance(run_dir)
    assert soils.clip_soils is True
    assert soils.clip_soils_depth == 42
    assert soils.initial_sat == pytest.approx(0.67)

    watershed = ctx["watershed_cls"].getInstance(run_dir)
    assert watershed.clip_hillslopes is False
    assert watershed.clip_hillslope_length == 15

    env = ctx["env"]
    prep = env.redis_prep_class.getInstance(run_dir)
    assert prep.removed == [
        "run_wepp_hillslopes",
        "run_wepp_watershed",
        "run_omni_scenarios",
        "run_path_cost_effective",
    ]
    assert prep.job_history == [("run_wepp_rq", "job-123")]

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.func is ctx["run_wepp_rq"]
    assert queue_call.args == (RUN_ID,)
    assert queue_call.timeout == wepp_rq_module.TIMEOUT


def test_run_wepp_returns_json_error_on_unhandled_exception(run_wepp_api_client, monkeypatch):
    client, ctx = run_wepp_api_client

    def explode(self, payload: Dict[str, Any]) -> None:
        raise RuntimeError("forced failure for testing")

    monkeypatch.setattr(ctx["wepp_cls"], "parse_inputs", explode, raising=True)

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/run_wepp",
        json={"clip_soils": False},
    )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["Success"] is False
    assert "forced failure" in payload["Error"]
    assert isinstance(payload.get("StackTrace"), list)

    env = ctx["env"]
    assert env.recorder.queue_calls == []
