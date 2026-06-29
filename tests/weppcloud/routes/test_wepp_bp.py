from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import tempfile

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


@pytest.mark.parametrize(
    ("texture_slug", "rdmax", "xmxlai", "decfct"),
    [
        ("clay", 1.1, 2.1, 0.11),
        ("loam", 1.2, 2.2, 0.22),
        ("sand", 1.3, 2.3, 0.33),
        ("silt", 1.4, 2.4, 0.44),
    ],
)
def test_view_management_effective_returns_texture_specific_preview(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
    texture_slug: str,
    rdmax: float,
    xmxlai: float,
    decfct: float,
) -> None:
    client, _, run_dir = wepp_client

    class DummyManagement:
        def __init__(self) -> None:
            self.rdmax = -1.0
            self.xmxlai = -1.0
            self.overrides: Dict[str, float] = {}

        def set_rdmax(self, value: float) -> None:
            self.rdmax = value

        def set_xmxlai(self, value: float) -> None:
            self.xmxlai = value

        def __setitem__(self, key: str, value: float) -> None:
            self.overrides[key] = value

        def __repr__(self) -> str:
            return (
                "DummyManagement("
                f"rdmax={self.rdmax}, xmxlai={self.xmxlai}, "
                f"decfct={self.overrides.get('plant.data.decfct')}"
                ")"
            )

    class DummyManagementSummary:
        disturbed_class = "forest moderate sev fire-mulch_15"
        cancov_override = None

        @staticmethod
        def get_management() -> DummyManagement:
            return DummyManagement()

    class DummyLanduse:
        @classmethod
        def getInstance(cls, wd: str):
            assert wd == run_dir
            return type("LanduseObj", (), {"managements": {"42": DummyManagementSummary()}})()

    class DummyDisturbed:
        @classmethod
        def tryGetInstance(cls, wd: str):
            assert wd == run_dir
            replacements = {
                ("clay loam", "forest moderate sev fire"): {
                    "rdmax": 1.1,
                    "xmxlai": 2.1,
                    "plant.data.decfct": 0.11,
                },
                ("loam", "forest moderate sev fire"): {
                    "rdmax": 1.2,
                    "xmxlai": 2.2,
                    "plant.data.decfct": 0.22,
                },
                ("sand loam", "forest moderate sev fire"): {
                    "rdmax": 1.3,
                    "xmxlai": 2.3,
                    "plant.data.decfct": 0.33,
                },
                ("silt loam", "forest moderate sev fire"): {
                    "rdmax": 1.4,
                    "xmxlai": 2.4,
                    "plant.data.decfct": 0.44,
                },
            }
            return type("DisturbedObj", (), {"land_soil_replacements_d": replacements})()

    monkeypatch.setattr(wepp_module, "Landuse", DummyLanduse)
    monkeypatch.setattr(wepp_module, "nodb_mods", type("Mods", (), {"Disturbed": DummyDisturbed}))

    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/view/management_effective/42/{texture_slug}/"
    )

    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    body = response.get_data(as_text=True)
    assert f"rdmax={rdmax}" in body
    assert f"xmxlai={xmxlai}" in body
    assert f"decfct={decfct}" in body


def test_view_management_effective_rejects_invalid_texture(
    wepp_client,
) -> None:
    client, _, _ = wepp_client

    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/view/management_effective/42/invalid-texture/"
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "invalid_texture"
    assert "Invalid texture" in payload["error"]["message"]


def test_view_management_effective_requires_disturbed_mod(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client

    class DummyManagementSummary:
        disturbed_class = "forest"
        cancov_override = None

        @staticmethod
        def get_management():
            return type("DummyManagement", (), {})()

    class DummyLanduse:
        @classmethod
        def getInstance(cls, wd: str):
            assert wd == run_dir
            return type("LanduseObj", (), {"managements": {"42": DummyManagementSummary()}})()

    class DummyDisturbed:
        @classmethod
        def tryGetInstance(cls, wd: str):
            assert wd == run_dir
            return None

    monkeypatch.setattr(wepp_module, "Landuse", DummyLanduse)
    monkeypatch.setattr(wepp_module, "nodb_mods", type("Mods", (), {"Disturbed": DummyDisturbed}))

    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/view/management_effective/42/clay/"
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "disturbed_not_enabled"
    assert "Disturbed mod is not enabled" in payload["error"]["message"]


def test_view_management_effective_applies_lookup_xmxlai_when_cancov_override_exists(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client

    class DummyManagement:
        def __init__(self) -> None:
            self.rdmax = -1.0
            self.xmxlai = 3.6

        def set_rdmax(self, value: float) -> None:
            self.rdmax = value

        def set_xmxlai(self, value: float) -> None:
            self.xmxlai = value

        def __repr__(self) -> str:
            return f"DummyManagement(rdmax={self.rdmax}, xmxlai={self.xmxlai})"

    class DummyManagementSummary:
        disturbed_class = "tall grass"
        cancov_override = 0.6

        @staticmethod
        def get_management() -> DummyManagement:
            return DummyManagement()

    class DummyLanduse:
        @classmethod
        def getInstance(cls, wd: str):
            assert wd == run_dir
            return type("LanduseObj", (), {"managements": {"71": DummyManagementSummary()}})()

    class DummyDisturbed:
        @classmethod
        def tryGetInstance(cls, wd: str):
            assert wd == run_dir
            replacements = {("clay loam", "tall grass"): {"rdmax": 0.4, "xmxlai": 5.1}}
            return type("DisturbedObj", (), {"land_soil_replacements_d": replacements})()

    monkeypatch.setattr(wepp_module, "Landuse", DummyLanduse)
    monkeypatch.setattr(wepp_module, "nodb_mods", type("Mods", (), {"Disturbed": DummyDisturbed}))

    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/view/management_effective/71/clay/"
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "rdmax=0.4" in body
    assert "xmxlai=5.1" in body


def test_view_management_effective_does_not_persist_preview_artifacts(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client

    class DummyManagement:
        def set_rdmax(self, value: float) -> None:
            self.rdmax = value

        def set_xmxlai(self, value: float) -> None:
            self.xmxlai = value

        def __setitem__(self, key: str, value: float) -> None:
            setattr(self, key.replace(".", "_"), value)

        def __repr__(self) -> str:
            return "DummyManagement()"

    class DummyManagementSummary:
        disturbed_class = "forest"
        cancov_override = None

        @staticmethod
        def get_management() -> DummyManagement:
            return DummyManagement()

    class DummyLanduse:
        @classmethod
        def getInstance(cls, wd: str):
            assert wd == run_dir
            return type("LanduseObj", (), {"managements": {"42": DummyManagementSummary()}})()

    class DummyDisturbed:
        @classmethod
        def tryGetInstance(cls, wd: str):
            assert wd == run_dir
            replacements = {("clay loam", "forest"): {"rdmax": 2.5, "xmxlai": 3.5}}
            return type("DisturbedObj", (), {"land_soil_replacements_d": replacements})()

    original_open = open

    def guarded_open(path, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"Unexpected write-mode open during preview request: {path} ({mode})")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(wepp_module, "Landuse", DummyLanduse)
    monkeypatch.setattr(wepp_module, "nodb_mods", type("Mods", (), {"Disturbed": DummyDisturbed}))
    monkeypatch.setattr("builtins.open", guarded_open)
    monkeypatch.setattr(
        tempfile,
        "mkstemp",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Preview route must not create temporary files.")
        ),
    )

    before = sorted(str(p.relative_to(run_dir)) for p in Path(run_dir).rglob("*"))
    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/view/management_effective/42/clay/"
    )
    after = sorted(str(p.relative_to(run_dir)) for p in Path(run_dir).rglob("*"))

    assert response.status_code == 200
    assert before == after


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


def test_report_wepp_results_passes_export_relpaths(wepp_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, run_dir = wepp_client
    _touch_wepp_results(run_dir)

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

    relpaths = {
        "prep-details": "export/features/artifacts/a/features_export.csv.zip",
        "prep-wepp": "export/features/artifacts/b/features_export.geopackage.zip",
        "prep-wepp-geodatabase": "export/features/artifacts/b/features_export.gdb.zip",
    }
    monkeypatch.setattr(
        wepp_module,
        "_resolve_published_export_relpath",
        lambda _wd, profile: relpaths.get(profile),
    )

    captured: dict[str, Any] = {}

    def fake_render_template(template_name: str, **kwargs: Any) -> str:
        assert template_name == "controls/wepp_reports.htm"
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(wepp_module, "render_template", fake_render_template)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/results/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert (
        captured["prep_details_export_download_url"].rstrip("/")
        == f"/runs/{RUN_ID}/{CONFIG}/download/features/published/prep-details"
    )
    assert (
        captured["post_wepp_geopackage_export_download_url"].rstrip("/")
        == f"/runs/{RUN_ID}/{CONFIG}/download/features/published/prep-wepp"
    )
    assert (
        captured["post_wepp_geodatabase_export_download_url"].rstrip("/")
        == f"/runs/{RUN_ID}/{CONFIG}/download/features/published/prep-wepp-geodatabase"
    )
    assert (
        captured["ermit_export_download_url"].rstrip("/")
        == f"/runs/{RUN_ID}/{CONFIG}/download/ermit"
    )


def test_report_wepp_results_hides_ermit_export_for_rhem(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client
    _touch_wepp_results(run_dir)

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

    class DummyRon:
        @staticmethod
        def load_detached(wd: str, allow_nonexistent: bool = False):
            assert wd == run_dir
            assert allow_nonexistent is True
            return type("RonInstance", (), {"mods": ("rhem",)})()

    monkeypatch.setattr(wepp_module, "Ron", DummyRon)

    captured: dict[str, Any] = {}

    def fake_render_template(template_name: str, **kwargs: Any) -> str:
        assert template_name == "controls/wepp_reports.htm"
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(wepp_module, "render_template", fake_render_template)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/results/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured["ermit_export_download_url"] is None


def test_report_wepp_results_sets_storm_event_analyzer_ready_when_metric_csv_exists(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client
    _touch_wepp_results(run_dir)

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

    metric_path = Path(run_dir) / "climate" / "wepp_cli_pds_mean_metric.csv"
    metric_path.parent.mkdir(parents=True, exist_ok=True)
    metric_path.write_text("ari,metric\n2,0.1\n", encoding="utf-8")

    captured: dict[str, Any] = {}

    def fake_render_template(template_name: str, **kwargs: Any) -> str:
        assert template_name == "controls/wepp_reports.htm"
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(wepp_module, "render_template", fake_render_template)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/results/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured["storm_event_analyzer_ready"] is True


def test_report_wepp_results_sets_storm_event_analyzer_not_ready_when_metric_csv_missing(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client
    _touch_wepp_results(run_dir)

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

    captured: dict[str, Any] = {}

    def fake_render_template(template_name: str, **kwargs: Any) -> str:
        assert template_name == "controls/wepp_reports.htm"
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(wepp_module, "render_template", fake_render_template)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/results/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured["storm_event_analyzer_ready"] is False


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


def test_download_features_export_published_returns_file_with_canonical_filename(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client
    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    artifact_path = Path(run_dir) / "export" / "features" / "artifacts" / "a1" / "features_export.csv.zip"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("artifact", encoding="utf-8")
    artifact_relpath = artifact_path.relative_to(Path(run_dir)).as_posix()
    monkeypatch.setattr(
        wepp_module,
        "resolve_published_artifact_path",
        lambda wd, profile: (artifact_path, artifact_relpath),
    )

    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/download/features/published/prep-details"
    )
    assert response.status_code == 200
    assert "test-run.prep-details.csv.zip" in response.headers.get("Content-Disposition", "")


def test_download_ermit_export_returns_generated_file(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client
    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    export_path = Path(run_dir) / "export" / "ermit" / "ermit_input.csv"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text("topaz_id\n1\n", encoding="utf-8")

    import wepppy.export as export_pkg

    def _create_ermit_input(wd: str) -> str:
        assert wd == run_dir
        return str(export_path)

    monkeypatch.setattr(export_pkg, "create_ermit_input", _create_ermit_input)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/download/ermit")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "topaz_id\n1\n"
    assert "ermit_input.csv" in response.headers.get("Content-Disposition", "")


def test_download_features_export_published_stale_returns_service_error(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client
    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    def _resolve(wd: str, profile: str):
        assert wd == run_dir
        assert profile == "prep-wepp"
        raise wepp_module.FeaturesExportServiceError(
            "Published features export artifact is stale.",
            status_code=409,
            code="stale_publication",
            details="profile=prep-wepp: stale",
        )

    monkeypatch.setattr(wepp_module, "resolve_published_artifact_path", _resolve)

    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/download/features/published/prep-wepp"
    )

    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "stale_publication"
    assert payload["error"]["details"] == "profile=prep-wepp: stale"


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
    assert captured_query["payload"]["computed_columns"][0]["sql"] == "MAKE_DATE(stream.year, 1, 1) + (stream.julian - 1)"
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

    captured_report_kwargs: Dict[str, Any] = {}

    class DummyReport:
        return_periods = {"Peak Discharge": {2: 1.0, 5: 2.0}}

    class DummyWepp:
        chn_topaz_ids_of_interest = []

        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return DummyWepp()

        def report_return_periods(self, **kwargs: Any):
            captured_report_kwargs.update(kwargs)
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

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods?output_scope=roads&method=am")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured_report_kwargs["output_scope"] == "roads"
    assert captured_report_kwargs["method"] == "am"
    assert captured_template["template_name"] == "reports/wepp/return_periods.htm"
    assert captured_template["kwargs"]["output_scope"] == "roads"
    assert captured_template["kwargs"]["method"] == "am"


def test_return_periods_rejects_invalid_method(wepp_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, _ = wepp_client
    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods?method=invalid")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["error"]["message"] == "method must be either cta or am"


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


def test_get_wepp_prep_details_passes_disturbed_preview_context(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client
    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)
    monkeypatch.setattr(wepp_module, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyRon:
        mods = ("disturbed",)

        @classmethod
        def getInstance(cls, wd: str):
            assert wd == run_dir
            return cls()

        def subs_summary(self, abbreviated: bool = False):
            assert abbreviated is True
            return [{"meta": {"topaz_id": "1"}}]

        def chns_summary(self, abbreviated: bool = False):
            assert abbreviated is True
            return [{"meta": {"topaz_id": "2"}}]

    class DummyUnitizer:
        @staticmethod
        def getInstance(wd: str):
            assert wd == run_dir
            return object()

    captured: Dict[str, Any] = {}

    def fake_render_template(template_name: str, **kwargs: Any) -> str:
        captured["template_name"] = template_name
        captured["kwargs"] = kwargs
        return "rendered"

    monkeypatch.setattr(wepp_module, "Ron", DummyRon)
    monkeypatch.setattr(wepp_module, "Unitizer", DummyUnitizer)
    monkeypatch.setattr(wepp_module, "render_template", fake_render_template)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/prep_details/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert captured["template_name"] == "reports/wepp/prep_details.htm"
    assert captured["kwargs"]["disturbed_preview_available"] is True
    assert captured["kwargs"]["disturbed_preview_textures"] == (
        ("clay", "Clay"),
        ("loam", "Loam"),
        ("sand", "Sand"),
        ("silt", "Silt"),
    )


def test_report_ron_sub_summary_disables_disturbed_preview_without_mod(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, run_dir = wepp_client
    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)
    monkeypatch.setattr(wepp_module, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    class DummyRon:
        mods = ("rap",)

        @classmethod
        def getInstance(cls, wd: str):
            assert wd == run_dir
            return cls()

        @staticmethod
        def sub_summary(topaz_id: str):
            return {"meta": {"topaz_id": topaz_id}, "landuse": None}

    captured: Dict[str, Any] = {}

    def fake_render_template(template_name: str, **kwargs: Any) -> str:
        captured["template_name"] = template_name
        captured["kwargs"] = kwargs
        return "rendered"

    monkeypatch.setattr(wepp_module, "Ron", DummyRon)
    monkeypatch.setattr(wepp_module, "render_template", fake_render_template)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/sub_summary/10/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert captured["template_name"] == "reports/hill.htm"
    assert captured["kwargs"]["disturbed_preview_available"] is False
