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
    from types import SimpleNamespace
    monkeypatch.setattr(wepp_module.Ron, "getInstance", lambda wd: SimpleNamespace(
        mods=[], config_get_str=lambda section, key, default=None: default))
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
    client, _, run_dir = wepp_client

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


def test_download_ermit_export_renders_rq_engine_launcher(
    wepp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = wepp_client
    monkeypatch.setattr(cap_guard, "current_user", type("User", (), {"is_authenticated": True})(), raising=False)

    captured: dict[str, Any] = {}

    def fake_render_template(template_name: str, **kwargs: Any) -> str:
        assert template_name == "reports/ermit_export_download.htm"
        captured.update(kwargs)
        return "launcher"

    monkeypatch.setattr(wepp_module, "render_template", fake_render_template)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/download/ermit")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "launcher"
    assert captured["ermit_export_submit_url"] == f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/export/ermit"
    assert captured["ermit_export_session_token_url"] == f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/session-token"


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
    monkeypatch.setattr(
        wepp_module,
        "resolve_unitizer_presentation",
        DummyUnitizer.getInstance,
    )
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
    monkeypatch.setattr(
        wepp_module,
        "resolve_unitizer_presentation",
        DummyUnitizer.getInstance,
    )
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


@pytest.mark.parametrize(("year_query", "expected_exclusions"), [
    ("", [0, 1]), ("&exclude_yr_indxs=", []), ("&exclude_yr_indxs=0", [0]),
])
def test_yearly_watbal_supports_roads_output_scope(
    wepp_client, monkeypatch: pytest.MonkeyPatch, year_query, expected_exclusions,
) -> None:
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
    monkeypatch.setattr(
        wepp_module,
        "resolve_unitizer_presentation",
        DummyUnitizer.getInstance,
    )
    monkeypatch.setattr(wepp_module, "TotalWatbalReport", _totwatbal)

    captured_template: Dict[str, Any] = {}

    def _fake_render(template_name: str, **kwargs: Any) -> str:
        captured_template["template_name"] = template_name
        captured_template["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(wepp_module, "render_template", _fake_render)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/wepp/yearly_watbal?output_scope=roads{year_query}")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured_scopes["yearly"] == "roads"
    assert captured_scopes["exclude_yr_indxs"] == expected_exclusions
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
    monkeypatch.setattr(
        wepp_module,
        "resolve_unitizer_presentation",
        DummyUnitizer.getInstance,
    )
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
    monkeypatch.setattr(
        wepp_module,
        "resolve_unitizer_presentation",
        DummyUnitizer.getInstance,
    )
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
    assert captured_template["kwargs"]["measure_order"][:4] == [
        "Precipitation Depth",
        "Runoff",
        "Peak Discharge",
        "Sediment Yield",
    ]


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
    monkeypatch.setattr(
        wepp_module,
        "resolve_unitizer_presentation",
        DummyUnitizer.getInstance,
    )
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


def test_checked_project_rejects_disturbed_preview_before_hydration(wepp_client, monkeypatch):
    from types import SimpleNamespace
    client = wepp_client[0]
    monkeypatch.setattr(wepp_module.Ron, "getInstance", lambda wd: SimpleNamespace(
        config_get_str=lambda section, key, default=None: "True"))
    def forbidden(*args, **kwargs):
        pytest.fail("Excluded Disturbed controller was hydrated")
    monkeypatch.setattr(wepp_module.nodb_mods.Disturbed, "tryGetInstance", forbidden)
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/view/management_effective/42/clay/")
    assert response.status_code == 400
    assert response.get_json()['error']['code'] == 'unsupported_capability'


@pytest.fixture
def omni_return_period_client(wepp_client, monkeypatch):
    """Real staged datasets/report evaluation/CSV; isolate auth and NoDb loading."""
    from types import SimpleNamespace
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from wepppy.nodb.core.wepp_postprocess_service import WeppPostprocessService
    from wepppy.weppcloud.routes.nodb_api import return_period_scenarios as selection

    client, _, run_dir = wepp_client
    root = Path(run_dir)
    source = Path(__file__).parents[2] / 'wepp/interchange/fixtures/decimal-pleasing/wepp/output/interchange'
    names = ['undisturbed', 'uniform_low']
    roots = [root] + [root / '_pups/omni/scenarios' / name for name in names]
    for index, directory in enumerate(roots):
        for scope in ['wepp/output', 'wepp/roads/output']:
            target = directory / scope / 'interchange'
            target.mkdir(parents=True)
            for filename in ['return_period_events.parquet', 'return_period_event_ranks.parquet']:
                table = pq.read_table(source / filename)
                if index and filename == 'return_period_events.parquet':
                    for column, values in [('calendar_year', pc.add(table['calendar_year'], index * 20)),
                                           ('runoff_depth_mm', pc.multiply(table['runoff_depth_mm'], index + 1))]:
                        table = table.set_column(table.schema.get_field_index(column), column, values)
                if index and filename == 'return_period_event_ranks.parquet':
                    values = pc.if_else(pc.equal(table['measure_id'], 'runoff_depth'),
                                        pc.multiply(table['measure_value'], index + 1), table['measure_value'])
                    table = table.set_column(table.schema.get_field_index('measure_value'), 'measure_value', values)
                pq.write_table(table, target / filename)
            pq.write_table(pa.table({'completed': [True]}), target / 'loss_pw0.out.parquet')
        (directory / 'wepp.nodb').write_text('NoDb loading isolated; real datasets above')
        (directory / '_query_engine').mkdir()
        (directory / '_query_engine/catalog.json').write_text(wepp_module.json.dumps({'root': str(directory), 'files': []}))
        (directory / 'READONLY').touch()
    (root / 'omni.nodb').write_text('NoDb loading isolated')
    omni = SimpleNamespace(scenarios=[{'type': name} for name in names], _scenario_run_state=[])
    monkeypatch.setattr(selection.Omni, 'getInstance', lambda wd: omni)
    monkeypatch.setattr(cap_guard, 'current_user', SimpleNamespace(is_authenticated=True))
    monkeypatch.setattr(wepp_module, 'current_user', SimpleNamespace(is_authenticated=True))
    monkeypatch.setattr(wepp_module.Climate, 'getInstance', lambda wd: SimpleNamespace(years=11))
    monkeypatch.setattr(wepp_module.Watershed, 'getInstance', lambda wd: SimpleNamespace(translator_factory=lambda: None))
    monkeypatch.setattr(wepp_module, 'resolve_unitizer_presentation', lambda wd: SimpleNamespace(preferences=lambda: {}))
    service = WeppPostprocessService()
    calls = []

    class Controller:
        chn_topaz_ids_of_interest = [94]

        def __init__(self, wd):
            self.wd = wd

        @classmethod
        def getInstance(cls, wd):
            return cls(wd)

        def report_return_periods(self, **kwargs):
            calls.append((self.wd, kwargs.copy()))
            return service.report_return_periods(self, **kwargs)

    monkeypatch.setattr(wepp_module, 'Wepp', Controller)
    captured = {}

    def render(template, **context):
        captured.update(context)
        return 'rendered'

    monkeypatch.setattr(wepp_module, 'render_template', render)
    return client, roots, calls, captured


@pytest.mark.parametrize('scope', ['baseline', 'roads'])
@pytest.mark.parametrize('method', ['cta', 'am'])
def test_return_period_omni_csv_real_datasets(omni_return_period_client, scope, method):
    import csv
    import io
    from wepppy.wepp.reports import ReturnPeriodDataset

    client, roots, calls, captured = omni_return_period_client
    query = [('omni_scenario', 'uniform_low'), ('omni_scenario', 'undisturbed'),
             ('omni_scenario', 'undisturbed'), ('rec_intervals', '5,2'),
             ('method', method), ('output_scope', scope), ('exclude_yr_indxs', '0'),
             ('exclude_months', '1,2'), ('chn_topaz_id_of_interest', '94'),
             ('gringorten_correction', 'true')]
    url = f'/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods'
    assert client.get(url, query_string=query).status_code == 200
    assert captured['selected_omni_scenarios'] == ['undisturbed', 'uniform_low']
    response = client.get(url, query_string=query + [('format', 'csv'), ('table', 'runoff')])
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
    assert list(rows[0]) == ['Scenario', 'Recurrence Interval (years)', 'Date', 'Runoff (mm)']
    assert [row['Scenario'] for row in rows] == ['Undisturbed'] * 2 + ['undisturbed'] * 2 + ['uniform_low'] * 2
    for index, directory in enumerate(roots):
        expected = ReturnPeriodDataset(directory, auto_refresh=False, output_scope=scope).create_report(
            [5, 2], exclude_yr_indxs=[0], exclude_months=[1, 2], method=method,
            gringorten_correction=True, topaz_id=94)
        for row in rows[index * 2:index * 2 + 2]:
            entry = expected.return_periods['Runoff'][int(float(row['Recurrence Interval (years)']))]
            assert float(row['Runoff (mm)']) == pytest.approx(entry['Runoff'])
            assert row['Date'] == f"{entry['mo']:02d}/{entry['da']:02d}/{entry['calendar_year']:04d}"
    assert len({row['Date'] for row in rows[::2]}) == 3
    assert all(options['meoization'] is False for _, options in calls)


def test_return_period_comparison_bypasses_warmed_method_interval_cache(omni_return_period_client):
    import csv
    import io
    from wepppy.nodb.core.wepp_postprocess_service import WeppPostprocessService
    from wepppy.wepp.reports import ReturnPeriodDataset
    from types import SimpleNamespace

    client, roots, _, _ = omni_return_period_client
    service = WeppPostprocessService()
    before = {}
    for directory in roots:
        service.report_return_periods(SimpleNamespace(wd=str(directory)), rec_intervals=[10], method='cta',
                                      gringorten_correction=False)
        cache = directory / 'wepp/output/return_periods.json'
        before[cache] = cache.read_bytes()
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods', query_string=[
        ('omni_scenario', 'undisturbed'), ('omni_scenario', 'uniform_low'),
        ('rec_intervals', '5,2'), ('method', 'am'), ('format', 'csv'), ('table', 'runoff')])
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
    assert {float(row['Recurrence Interval (years)']) for row in rows} == {5, 2}
    expected = ReturnPeriodDataset(roots[1], auto_refresh=False).create_report([5, 2], method='am', gringorten_correction=False)
    assert float(rows[2]['Runoff (mm)']) == pytest.approx(expected.return_periods['Runoff'][5]['Runoff'])
    assert all(path.read_bytes() == contents for path, contents in before.items())


def test_return_period_no_selection_and_extraneous_keep_single_report(omni_return_period_client):
    client, roots, calls, captured = omni_return_period_client
    url = f'/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods'
    response = client.get(url + '?format=csv&table=runoff&rec_intervals=2')
    assert response.status_code == 200
    assert not response.get_data(as_text=True).startswith('Scenario,')
    assert len(calls) == 1
    calls.clear()
    assert client.get(url + '?extraneous=true&omni_scenario=undisturbed').status_code == 200
    assert len(calls) == 1
    assert captured['selected_omni_scenarios'] == ['undisturbed']
    assert captured['compare_scenarios'] is False
    assert calls[0][0] == str(roots[0])


@pytest.mark.parametrize('name', ['../outside', 'unknown', 'undisturbed'])
def test_return_period_unavailable_selection_is_400(omni_return_period_client, name):
    client, roots, calls, _ = omni_return_period_client
    (roots[1] / 'wepp/output/interchange/return_period_events.parquet').unlink()
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods', query_string={'omni_scenario': name})
    assert response.status_code == 400
    assert calls == []


def test_return_period_child_missing_channel_has_no_events(omni_return_period_client):
    import pyarrow.parquet as pq
    import pyarrow.compute as pc
    client, roots, _, captured = omni_return_period_client
    for filename in ['return_period_events.parquet', 'return_period_event_ranks.parquet']:
        path = roots[1] / 'wepp/output/interchange' / filename
        table = pq.read_table(path)
        table = table.set_column(table.schema.get_field_index('topaz_id'), 'topaz_id', pc.add(table['topaz_id'], 10))
        pq.write_table(table, path)
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods?omni_scenario=undisturbed&chn_topaz_id_of_interest=94')
    assert response.status_code == 200
    assert captured['scenario_reports'][1]['report'].return_periods == {}


@pytest.mark.parametrize('english', [False, True])
@pytest.mark.parametrize('has_map', [False, True])
def test_return_period_rendered_csv_link_and_table_agree(omni_return_period_client, monkeypatch, english, has_map):
    import csv
    import io
    import re
    from html import unescape
    from flask import url_for
    from jinja2 import Environment, ChoiceLoader, DictLoader, FileSystemLoader
    from types import SimpleNamespace

    client, _, _, _ = omni_return_period_client
    monkeypatch.setattr(wepp_module.nodb_mods.Disturbed, 'tryGetInstance',
                        lambda wd, **kwargs: SimpleNamespace(has_map=has_map))
    preferences = {wepp_module._determine_unitclass('mm'): 'in'} if english else {}
    monkeypatch.setattr(wepp_module, 'resolve_unitizer_presentation', lambda wd: SimpleNamespace(preferences=lambda: preferences))
    # Isolate the shared shell; render the actual report and its CSV links.
    env = Environment(loader=ChoiceLoader([
        DictLoader({'reports/_base_report.htm': '{% block report_content %}{% endblock %}'}),
        FileSystemLoader(Path(wepp_module.__file__).parents[2] / 'templates'),
    ]), autoescape=True)
    env.filters['sort_numeric'] = lambda values, reverse=False: sorted(values, key=float, reverse=reverse)
    env.globals.update(url_for=url_for, url_for_run=wepp_module.url_for_run,
                       unitizer=lambda value, units: str(wepp_module._convert_scalar_to_preference(value, units, preferences)[0]),
                       unitizer_units=lambda units: wepp_module._convert_scalar_to_preference(1, units, preferences)[1])
    monkeypatch.setattr(wepp_module, 'render_template', lambda name, **context: env.get_template(name).render(**context))
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods', query_string=[
        ('omni_scenario', 'undisturbed'), ('omni_scenario', 'uniform_low'), ('rec_intervals', '5,2'),
        ('exclude_yr_indxs', '0,1')])
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    button = re.search(r'<button[^>]*data-report-csv="runoff_tbl"[^>]*>', html).group()
    csv_url = unescape(re.search(r'data-report-url="([^"]+)"', button).group(1))
    assert csv_url.count('omni_scenario=') == 2
    assert 'rec_intervals=5,2' in csv_url or 'rec_intervals=5%2C2' in csv_url
    csv_response = client.get(csv_url)
    assert csv_response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(csv_response.get_data(as_text=True))))
    assert rows[0]['Scenario'] == ('Burned' if has_map else 'Undisturbed')
    table = re.search(r'<table[^>]*id="runoff_tbl".*?</table>', html, re.S).group()
    cells = [re.findall(r'<td[^>]*>\s*(.*?)\s*</td>', row, re.S)
             for row in re.findall(r'<tr>(.*?)</tr>', table, re.S)]
    cells = [row for row in cells if row]
    assert len(cells) == len(rows) == 6
    for actual, exported in zip(cells, rows):
        assert actual[:1] == [exported['Scenario']]
        assert float(actual[1]) == float(exported['Recurrence Interval (years)'])
        assert actual[2] == exported['Date']
        # HTML uses the established two-decimal depth presentation; CSV retains
        # the full numeric precision for further analysis.
        assert float(actual[3]) == pytest.approx(float(exported['Runoff (in)' if english else 'Runoff (mm)']), abs=0.005)


@pytest.mark.parametrize('year_fields', [{'calendar_year': 2050}, {'calendar_year': None, 'display_year': 2050},
                                        {'year': None, 'calendar_year': 2050}])
def test_return_period_comparison_csv_prefers_explicit_event_year(year_fields):
    from types import SimpleNamespace
    report = SimpleNamespace(y0=2001, units_d={'Runoff': 'mm'},
        return_periods={'Runoff': {2: {'mo': 4, 'da': 5, 'year': 2, 'Runoff': 5, **year_fields}}})
    frame = wepp_module._build_return_period_simple_dataframe(report, 'Runoff', SimpleNamespace(preferences=lambda: {}), calendar_dates=True)
    assert frame.iloc[0]['Date'] == '04/05/2050'


def test_return_period_comparison_all_months_excluded_has_empty_reports(omni_return_period_client):
    client, _, _, captured = omni_return_period_client
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods', query_string={
        'omni_scenario': 'undisturbed', 'exclude_months': ','.join(map(str, range(1, 13)))})
    assert response.status_code == 200
    assert all(not group['report'].return_periods for group in captured['scenario_reports'])


@pytest.mark.parametrize(('empty_index', 'remaining_name'), [(0, 'undisturbed'), (1, 'Undisturbed')])
def test_return_period_comparison_filtered_group_does_not_hide_other_rows(omni_return_period_client, empty_index, remaining_name):
    import csv
    import io
    import pyarrow as pa
    import pyarrow.parquet as pq
    client, roots, _, captured = omni_return_period_client
    path = roots[empty_index] / 'wepp/output/interchange/return_period_events.parquet'
    table = pq.read_table(path)
    table = table.set_column(table.schema.get_field_index('mo'), 'mo', pa.array([1] * table.num_rows))
    pq.write_table(table, path)
    url = f'/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods?omni_scenario=undisturbed&exclude_months=1&exclude_yr_indxs=0&rec_intervals=5,2'
    assert client.get(url).status_code == 200
    assert captured['scenario_reports'][empty_index]['report'].return_periods == {}
    assert captured['scenario_reports'][empty_index]['report'].exclude_yr_indxs == [0]
    response = client.get(url + '&format=csv&table=runoff')
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
    assert len(rows) == 2
    assert {row['Scenario'] for row in rows} == {remaining_name}


def test_return_period_comparison_empty_csv_has_explicit_404(omni_return_period_client):
    client, _, _, _ = omni_return_period_client
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods', query_string={
        'omni_scenario': 'undisturbed', 'exclude_months': ','.join(map(str, range(1, 13))),
        'format': 'csv', 'table': 'runoff'})
    assert response.status_code == 404


def test_return_period_malformed_calendar_is_not_filtered_empty_success(omni_return_period_client):
    import pyarrow as pa
    import pyarrow.parquet as pq
    client, roots, _, captured = omni_return_period_client
    path = roots[1] / 'wepp/output/interchange/return_period_events.parquet'
    table = pq.read_table(path)
    for column in ['year', 'calendar_year']:
        table = table.set_column(table.schema.get_field_index(column), column, pa.nulls(table.num_rows, type=pa.int64()))
    pq.write_table(table, path)
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods?omni_scenario=undisturbed&exclude_months=1')
    assert response.status_code == 500
    assert captured == {}


@pytest.mark.parametrize('partial', [False, True])
def test_return_period_selection_stages_existing_outputs(omni_return_period_client, partial):
    import csv
    import io
    import shutil
    import pyarrow.parquet as pq
    from wepppy.weppcloud.routes.nodb_api.return_period_scenarios import completed_return_period_scenarios
    from wepppy.wepp.reports import ReturnPeriodDataset

    client, roots, _, _ = omni_return_period_client
    child = roots[1]
    (child / 'READONLY').unlink()
    target = child / 'wepp/output/interchange'
    (target / 'return_period_event_ranks.parquet').unlink()
    if not partial:
        (target / 'return_period_events.parquet').unlink()
    source = Path(__file__).parents[2] / 'wepp/interchange/fixtures/decimal-pleasing/wepp/output/interchange'
    for name in ['ebe_pw0.parquet', 'totalwatsed3.parquet']:
        shutil.copyfile(source / name, target / name)
    before = sorted(str(p) for p in child.rglob('*'))
    assert completed_return_period_scenarios(roots[0], 'baseline')[0]['reason'] is None
    assert before == sorted(str(p) for p in child.rglob('*'))
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods', query_string={
        'omni_scenario': 'undisturbed', 'format': 'csv', 'table': 'runoff',
        'rec_intervals': '5,2', 'exclude_yr_indxs': '0,1', 'chn_topaz_id_of_interest': '94',
        'gringorten_correction': 'true', 'exclude_months': ''})
    assert response.status_code == 200
    assert pq.read_table(target / 'return_period_events.parquet').num_rows > 0
    rows = [row for row in csv.DictReader(io.StringIO(response.get_data(as_text=True)))
            if row['Scenario'] == 'undisturbed']
    report = ReturnPeriodDataset(child, auto_refresh=False).create_report(
        [5, 2], exclude_yr_indxs=[0, 1], gringorten_correction=True, topaz_id=94)
    assert len(rows) == 2
    for row in rows:
        event = report.return_periods['Runoff'][int(float(row['Recurrence Interval (years)']))]
        assert float(row['Runoff (mm)']) == pytest.approx(event['Runoff'])


@pytest.mark.parametrize(('mods', 'has_map', 'single_input', 'expected'), [
    ([], None, False, 'Undisturbed'), (['disturbed'], False, False, 'Undisturbed'),
    (['disturbed'], True, False, 'Burned'), (['baer', 'disturbed'], True, False, 'Burned'),
    (['baer', 'disturbed'], False, False, 'Undisturbed'), (['disturbed'], True, True, 'Undisturbed'),
])
def test_return_period_baseline_map_labels(monkeypatch, mods, has_map, single_input, expected):
    from types import SimpleNamespace
    calls = []

    def load(name):
        def existing(wd, **kwargs):
            calls.append((name, wd, kwargs))
            return None if has_map is None else SimpleNamespace(has_map=has_map)
        return existing

    monkeypatch.setattr(wepp_module.nodb_mods.Baer, 'tryGetInstance', load('baer'))
    monkeypatch.setattr(wepp_module.nodb_mods.Disturbed, 'tryGetInstance', load('disturbed'))
    ron = SimpleNamespace(mods=mods, config_get_str=lambda *args: 'true' if single_input else 'false')
    assert wepp_module._return_period_baseline_label('/project', ron) == expected
    assert calls == ([] if single_input else [
        ('baer' if 'baer' in mods else 'disturbed', '/project', {'allow_nonexistent': False})])
