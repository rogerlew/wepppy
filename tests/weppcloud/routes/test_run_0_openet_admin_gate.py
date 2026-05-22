from __future__ import annotations

import importlib
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask, render_template

pytestmark = pytest.mark.routes


class _RoleUser:
    def __init__(self, roles: set[str] | None = None) -> None:
        self._roles = set(roles or set())
        self.is_authenticated = True

    def has_role(self, role: str) -> bool:
        return role in self._roles


class _BrokenAshRon(SimpleNamespace):
    @property
    def has_ash_results(self) -> bool:  # pragma: no cover - should never be touched
        raise FileNotFoundError("ash.nodb missing for stale ash mod")


@pytest.fixture()
def run0_module():
    return importlib.reload(importlib.import_module("wepppy.weppcloud.routes.run_0.run_0_bp"))


@pytest.fixture()
def run0_client(run0_module):
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="run0-openet-test")
    app.register_blueprint(run0_module.run_0_bp)
    with app.test_client() as client:
        yield client, run0_module


@pytest.fixture()
def run0_template_app(run0_module):
    template_dir = Path(run0_module.__file__).resolve().parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))
    app.config.update(TESTING=True, SECRET_KEY="run0-openet-template-test")
    return app


def _bootstrap_context(user_roles: set[str]) -> dict:
    user = _RoleUser(user_roles)
    openet_admin_enabled = bool({"Dev", "Root"} & user_roles)
    allow_debris_flow = bool({"PowerUser", "Admin", "Root"} & user_roles)
    return {
        "ron": SimpleNamespace(
            mods=["openet_ts"],
            boundary=None,
            runid="run-1",
            config_stem="cfg",
            readonly=False,
            cellsize=30,
            center0=[-117.0, 46.0],
            zoom0=10,
            has_sbs=False,
            has_dem=False,
            has_ash_results=False,
        ),
        "site_prefix": "/weppcloud",
        "current_user": user,
        "user": user,
        "current_ttl": None,
        "rq_job_ids": {},
        "playwright_load_all": False,
        "openet_admin_enabled": openet_admin_enabled,
        "allow_debris_flow": allow_debris_flow,
        "watershed": SimpleNamespace(
            has_channels=False,
            has_subcatchments=False,
            has_outlet=False,
            delineation_backend_is_wbt=True,
        ),
        "landuse": SimpleNamespace(has_landuse=False, mode="none", single_selection=False),
        "soils": SimpleNamespace(has_soils=False, mode="none", single_dbselection=False),
        "climate": SimpleNamespace(
            precip_scaling_mode=None,
            has_station=False,
            has_climate=False,
            has_observed=False,
        ),
        "observed": SimpleNamespace(results=None),
        "rangeland_cover": SimpleNamespace(has_covers=False),
        "wepp": SimpleNamespace(
            has_run=False,
            dss_export_mode=0,
            has_dss_zip=False,
            bootstrap_enabled=False,
            job_id=None,
            job_key=None,
        ),
        "bootstrap_admin_disabled": False,
        "bootstrap_is_anonymous": True,
        "omni_has_ran_scenarios": False,
        "omni_has_ran_contrasts": False,
        "omni": None,
        "rhem": SimpleNamespace(has_run=False),
        "ash": SimpleNamespace(ash_depth_mode=None),
        "disturbed": SimpleNamespace(sbs_mode=0, uniform_severity=None),
        "baer": None,
        "toc_task_emojis": {},
        "disabled_controllers": [],
    }


def _extract_openet_flag(js_text: str) -> str:
    match = re.search(r'"openet_ts"\s*:\s*(true|false)', js_text)
    assert match is not None
    return match.group(1)


def _extract_mod_flag(js_text: str, flag_name: str) -> str:
    match = re.search(rf'"{re.escape(flag_name)}"\s*:\s*(true|false)', js_text)
    assert match is not None
    return match.group(1)


def test_call_landuse_with_stale_mapping_recovery_retries_once(run0_template_app, run0_module) -> None:
    class DummyLanduse:
        def __init__(self) -> None:
            self.custom_mapping_relpath = "landuse/landuse_user_defined_mapping.json"

        def _clear_stale_system_custom_mapping_reference(self, relpath: str) -> bool:
            assert relpath == "landuse/landuse_user_defined_mapping.json"
            self.custom_mapping_relpath = None
            return True

    landuse = DummyLanduse()
    attempts = {"count": 0}

    def producer():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise run0_module.LanduseCustomMappingError(
                "Configured landuse custom mapping file is missing: landuse/landuse_user_defined_mapping.json",
                code="LANDUSE_CUSTOM_MAP_MISSING",
                details={"custom_mapping_relpath": "landuse/landuse_user_defined_mapping.json"},
            )
        return {"options": []}

    with run0_template_app.app_context():
        payload = run0_module._call_landuse_with_stale_mapping_recovery(landuse, producer)

    assert payload == {"options": []}
    assert attempts["count"] == 2
    assert landuse.custom_mapping_relpath is None


def test_call_landuse_with_stale_mapping_recovery_raises_non_system_paths(
    run0_template_app,
    run0_module,
) -> None:
    class DummyLanduse:
        custom_mapping_relpath = "landuse/custom-map.json"

    landuse = DummyLanduse()

    def producer():
        raise run0_module.LanduseCustomMappingError(
            "Configured landuse custom mapping file is missing: landuse/custom-map.json",
            code="LANDUSE_CUSTOM_MAP_MISSING",
            details={"custom_mapping_relpath": "landuse/custom-map.json"},
        )

    with run0_template_app.app_context():
        with pytest.raises(run0_module.LanduseCustomMappingError):
            run0_module._call_landuse_with_stale_mapping_recovery(landuse, producer)


def test_call_landuse_with_stale_mapping_recovery_retries_on_stale_write_for_system_path(
    run0_template_app,
    run0_module,
) -> None:
    class DummyLanduse:
        def __init__(self) -> None:
            self.custom_mapping_relpath = "landuse/landuse_user_defined_mapping.json"

        def _clear_stale_system_custom_mapping_reference(self, relpath: str) -> bool:
            assert relpath == "landuse/landuse_user_defined_mapping.json"
            self.custom_mapping_relpath = None
            return True

    landuse = DummyLanduse()
    attempts = {"count": 0}

    def producer():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise run0_module.NoDbStaleWriteError("stale NoDb write rejected")
        return {"options": []}

    with run0_template_app.app_context():
        payload = run0_module._call_landuse_with_stale_mapping_recovery(landuse, producer)

    assert payload == {"options": []}
    assert attempts["count"] == 2
    assert landuse.custom_mapping_relpath is None


def test_call_landuse_with_stale_mapping_recovery_raises_stale_write_for_non_system_path(
    run0_template_app,
    run0_module,
) -> None:
    class DummyLanduse:
        custom_mapping_relpath = "landuse/custom-map.json"

    landuse = DummyLanduse()

    def producer():
        raise run0_module.NoDbStaleWriteError("stale NoDb write rejected")

    with run0_template_app.app_context():
        with pytest.raises(run0_module.NoDbStaleWriteError):
            run0_module._call_landuse_with_stale_mapping_recovery(landuse, producer)


def test_view_mod_section_openet_denied_for_non_dev(
    run0_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module = run0_client
    monkeypatch.setattr(
        module,
        "_feature_role_enabled",
        lambda mod_name, *, playwright_load_all: False if mod_name == "openet_ts" else True,
    )

    response = client.get("/runs/run-1/cfg/view/mod/openet_ts")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["error"]["message"] == "OpenET Time Series is restricted to Dev users"


def test_view_mod_section_openet_allows_dev(
    run0_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module = run0_client
    monkeypatch.setattr(
        module,
        "_feature_role_enabled",
        lambda mod_name, *, playwright_load_all: True,
    )
    monkeypatch.setattr(
        module,
        "_build_runs0_context",
        lambda runid, config, playwright_load_all=False: {
            "mod_visibility": {"openet_ts": True},
            "dummy": True,
        },
    )

    render_calls: list[str] = []

    def fake_render(template_name: str, **_kwargs) -> str:
        render_calls.append(template_name)
        return f"<{template_name}>"

    monkeypatch.setattr(module, "render_template", fake_render)

    response = client.get("/runs/run-1/cfg/view/mod/openet_ts")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["mod"] == "openet_ts"
    assert render_calls == [
        "controls/openet_ts_pure.htm",
        "run_0/mod_section_wrapper.htm",
    ]


def test_view_mod_section_geneva_renders_module_template(
    run0_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module = run0_client
    monkeypatch.setattr(
        module,
        "_build_runs0_context",
        lambda runid, config, playwright_load_all=False: {
            "mod_visibility": {"geneva": True},
            "dummy": True,
        },
    )

    render_calls: list[str] = []

    def fake_render(template_name: str, **_kwargs) -> str:
        render_calls.append(template_name)
        return f"<{template_name}>"

    monkeypatch.setattr(module, "render_template", fake_render)

    response = client.get("/runs/run-1/cfg/view/mod/geneva")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["mod"] == "geneva"
    assert render_calls == [
        "controls/geneva_pure.htm",
        "run_0/mod_section_wrapper.htm",
    ]


def test_run_page_bootstrap_openet_flag_false_for_non_dev(run0_template_app) -> None:
    context = _bootstrap_context(set())
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)
    assert _extract_openet_flag(js) == "false"


def test_run_page_bootstrap_openet_flag_true_for_dev(run0_template_app) -> None:
    context = _bootstrap_context({"Dev"})
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)
    assert _extract_openet_flag(js) == "true"


def test_run_page_bootstrap_openet_flag_true_for_root(run0_template_app) -> None:
    context = _bootstrap_context({"Root"})
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)
    assert _extract_openet_flag(js) == "true"


def test_run_page_bootstrap_debris_flow_flag_false_for_non_power_roles(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["ron"].mods = ["debris_flow"]
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)
    assert _extract_mod_flag(js, "debris_flow") == "false"


def test_run_page_bootstrap_debris_flow_flag_true_for_root(run0_template_app) -> None:
    context = _bootstrap_context({"Root"})
    context["ron"].mods = ["debris_flow"]
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)
    assert _extract_mod_flag(js, "debris_flow") == "true"


def test_run_page_bootstrap_debris_flow_flag_respects_show_debris_flow_false(run0_template_app) -> None:
    context = _bootstrap_context({"Root"})
    context["ron"].mods = ["debris_flow"]
    context["show_debris_flow"] = False
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)
    assert _extract_mod_flag(js, "debris_flow") == "false"


def test_playwright_load_all_requires_test_support_flag(run0_template_app, run0_module, monkeypatch) -> None:
    monkeypatch.setattr(run0_module, "current_user", _RoleUser({"Admin"}))
    with run0_template_app.test_request_context("/runs/run-1/cfg/?playwright_load_all=true"):
        assert run0_module._playwright_load_all_enabled() is False


def test_playwright_load_all_requires_admin_role(run0_template_app, run0_module, monkeypatch) -> None:
    run0_template_app.config["TEST_SUPPORT_ENABLED"] = True
    monkeypatch.setattr(run0_module, "current_user", _RoleUser(set()))
    with run0_template_app.test_request_context("/runs/run-1/cfg/?playwright_load_all=true"):
        assert run0_module._playwright_load_all_enabled() is False


def test_playwright_load_all_enabled_for_admin_in_test_support(
    run0_template_app,
    run0_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run0_template_app.config["TEST_SUPPORT_ENABLED"] = True
    monkeypatch.setattr(run0_module, "current_user", _RoleUser({"Admin"}))
    with run0_template_app.test_request_context("/runs/run-1/cfg/?playwright_load_all=true"):
        assert run0_module._playwright_load_all_enabled() is True


def test_build_runs0_context_does_not_elevate_debris_with_test_support_flag(run0_module) -> None:
    source = Path(run0_module.__file__).read_text(encoding="utf-8")
    allow_block = re.search(
        r"allow_debris_flow\s*=\s*\((?:.|\n)*?\)\n\s*show_debris_flow",
        source,
    )
    assert allow_block is not None
    assert "TEST_SUPPORT_ENABLED" not in allow_block.group(0)


def test_run_page_bootstrap_serializes_wepp_controller_job_id(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["wepp"].job_id = "wepp-job-42"
    context["wepp"].job_key = "run_wepp_watershed_rq"
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert re.search(
        r'"wepp"\s*:\s*\{\s*"job_id"\s*:\s*"wepp-job-42"\s*,\s*"job_key"\s*:\s*"run_wepp_watershed_rq"\s*\}',
        js,
    )


def test_run_page_bootstrap_rusle_flag_false_without_disturbed(run0_template_app) -> None:
    context = _bootstrap_context({"Admin"})
    context["ron"].mods = ["rusle"]
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert _extract_mod_flag(js, "rusle") == "false"


def test_run_page_bootstrap_rusle_flag_true_with_disturbed(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["ron"].mods = ["rusle", "disturbed"]
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert _extract_mod_flag(js, "rusle") == "true"


def test_run_page_bootstrap_rusle_flag_respects_show_rusle_false(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["ron"].mods = ["rusle", "disturbed"]
    context["show_rusle"] = False
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert _extract_mod_flag(js, "rusle") == "false"


def test_run_page_bootstrap_rusle_flag_false_for_topaz_backend(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["ron"].mods = ["rusle", "disturbed"]
    context["watershed"].delineation_backend_is_wbt = False
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert _extract_mod_flag(js, "rusle") == "false"


def test_run_page_bootstrap_ash_flag_false_when_show_ash_context_false(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["ron"].mods = ["ash"]
    context["show_ash"] = False
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert _extract_mod_flag(js, "ash") == "false"


def test_run_page_bootstrap_ash_missing_nodb_does_not_raise(run0_template_app) -> None:
    context = _bootstrap_context(set())
    ron_payload = dict(vars(context["ron"]))
    ron_payload.pop("has_ash_results", None)
    ron_payload["mods"] = ["ash"]
    context["ron"] = _BrokenAshRon(**ron_payload)
    context["ash"] = None

    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert _extract_mod_flag(js, "ash") == "false"


def test_run_page_bootstrap_roads_flag_true_when_enabled(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["ron"].mods = ["roads"]
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert _extract_mod_flag(js, "roads") == "true"


def test_run_page_bootstrap_geneva_flag_true_when_enabled(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["ron"].mods = ["geneva"]
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert _extract_mod_flag(js, "geneva") == "true"
    assert re.search(
        r'"geneva"\s*:\s*\{\s*"stateAuthority"\s*:\s*"rq_engine"\s*\}',
        js,
    )


def test_run_page_bootstrap_features_export_flag_true_when_enabled(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["ron"].mods = ["features_export"]
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert _extract_mod_flag(js, "features_export") == "true"


def test_features_export_catalog_payload_builds_from_catalog(
    run0_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_catalog = SimpleNamespace(
        metadata=SimpleNamespace(
            catalog_version="2026.03.26",
            schema_version="1",
            updated_at_utc="2026-03-26T00:00:00Z",
            owner="wepppy",
            status="active",
            allowed_locator_kinds=("nodb_ref", "relpath", "path_template"),
            temporal_modes=("annual_average", "yearly", "event"),
            event_selectors=("date", "return_period"),
            path_template_vars={"scope_root": "output"},
        ),
        layers=[
            SimpleNamespace(
                layer_id="watershed.subcatchments",
                family="watershed",
                scope_class="scope_invariant",
                temporal_supported_modes=(),
                raw={"geometry": {"type": "polygon"}},
            ),
            SimpleNamespace(
                layer_id="wepp.temporal.events",
                family="wepp_temporal",
                scope_class="scope_aware",
                temporal_supported_modes=("event",),
                raw={
                    "label": "return_period_events.parquet",
                    "geometry": {"type": "polygon"},
                },
            ),
            SimpleNamespace(
                layer_id="agfields.metrics.field",
                family="agfields_metrics",
                scope_class="scope_invariant",
                temporal_supported_modes=("annual_average",),
                raw={"geometry": {"type": "polygon"}},
            ),
        ],
    )
    monkeypatch.setattr(run0_module, "load_layer_catalog", lambda: fake_catalog)

    payload = run0_module._build_features_export_catalog_payload()

    assert payload["load_error"] is None
    assert payload["metadata"]["catalog_version"] == "2026.03.26"
    assert payload["family_order"][0] == "watershed"
    assert [layer["layer_id"] for layer in payload["layers"]] == [
        "watershed.subcatchments",
        "wepp.temporal.events",
        "agfields.metrics.field",
    ]
    wepp_events = next(
        layer for layer in payload["layers"] if layer["layer_id"] == "wepp.temporal.events"
    )
    assert wepp_events["label"] == "return_period_events.parquet"
    agfields = next(
        layer for layer in payload["layers"] if layer["layer_id"] == "agfields.metrics.field"
    )
    assert agfields["selector_requirements"] == ["agfields_auto_prep"]


def test_features_export_catalog_payload_prefers_discovered_columns(
    run0_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_catalog = SimpleNamespace(
        metadata=SimpleNamespace(
            catalog_version="2026.03.26",
            schema_version="1",
            updated_at_utc="2026-03-26T00:00:00Z",
            owner="wepppy",
            status="active",
            allowed_locator_kinds=("nodb_ref", "relpath", "path_template"),
            temporal_modes=("annual_average", "yearly", "event"),
            event_selectors=("date", "return_period"),
            path_template_vars={"scope_root": "output"},
        ),
        layers=[
            SimpleNamespace(
                layer_id="wepp.summary.hillslopes",
                family="wepp_summary",
                scope_class="scope_aware",
                temporal_supported_modes=("annual_average", "yearly"),
                raw={
                    "geometry": {"type": "polygon", "feature_id_keys": ["TopazID"]},
                    "join": {"primary_key": "TopazID", "fallback_keys": []},
                    "sources": [],
                },
            )
        ],
    )
    monkeypatch.setattr(run0_module, "load_layer_catalog", lambda: fake_catalog)
    monkeypatch.setattr(
        run0_module,
        "_features_export_discover_layer_columns",
        lambda **kwargs: [
            {
                "column_id": "Runoff Volume",
                "label": "Runoff Volume",
                "display_unit": "m^3",
                "description": "Runoff volume exported from interchange schema.",
                "default_selected": True,
            }
        ],
    )

    payload = run0_module._build_features_export_catalog_payload("/tmp/features-export")
    layer = payload["layers"][0]

    assert [entry["column_id"] for entry in layer["columns"]] == ["TopazID", "Runoff Volume"]
    assert layer["columns"][1]["display_unit"] == "m^3"
    assert layer["columns"][1]["description"] == "Runoff volume exported from interchange schema."


def test_features_export_column_contract_dedupes_and_infers_units(run0_module) -> None:
    columns, required_columns = run0_module._features_export_column_contract(
        {
            "join": {"primary_key": "topaz_id", "fallback_keys": ["TopazID"]},
            "geometry": {"feature_id_keys": ["TopazID"]},
            "measures": {
                "required": ["baseflow_mm", "runoff_mm"],
                "optional": [{"key_aliases": ["sediment_yield_kg_ha"]}],
            },
        },
        discovered_columns=[
            {
                "column_id": "baseflow_mm",
                "label": "Baseflow",
                "display_unit": "mm",
                "description": "Groundwater baseflow depth",
            },
            {"column_id": "runoff_mm", "label": "Runoff", "display_unit": "mm"},
            {"column_id": "runoff_mm", "label": "Runoff duplicate", "display_unit": "mm"},
            {"column_id": "sediment_yield_kg_ha"},
        ],
    )

    column_ids = [entry["column_id"] for entry in columns]
    assert column_ids.count("baseflow_mm") == 1
    assert column_ids.count("runoff_mm") == 1

    by_id = {entry["column_id"]: entry for entry in columns}
    assert by_id["baseflow_mm"]["display_unit"] == "mm"
    assert by_id["baseflow_mm"]["description"] == "Groundwater baseflow depth"
    assert by_id["runoff_mm"]["display_unit"] == "mm"
    assert by_id["sediment_yield_kg_ha"]["display_unit"] == "kg/ha"
    assert required_columns == {"topaz_id"}


def test_features_export_parse_interchange_readme_extracts_column_docs(
    run0_module,
    tmp_path: Path,
) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        """
### `loss_pw0.hill.parquet`

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| Runoff Volume | double | m^3 | Annual runoff volume |
| Baseflow Volume | double | m^3 |  |
""".strip()
        + "\n",
        encoding="utf-8",
    )

    parsed = run0_module._features_export_parse_interchange_readme(readme_path)
    docs = parsed["loss_pw0.hill.parquet"]

    assert docs["exact"]["Runoff Volume"]["display_unit"] == "m^3"
    assert docs["exact"]["Runoff Volume"]["description"] == "Annual runoff volume"
    assert docs["match"]["runoffvolume"]["label"] == "Runoff Volume"


def test_features_export_catalog_payload_handles_catalog_load_failure(
    run0_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_catalog_load() -> None:
        raise RuntimeError("catalog unavailable")

    monkeypatch.setattr(run0_module, "load_layer_catalog", _raise_catalog_load)

    payload = run0_module._build_features_export_catalog_payload()

    assert payload["metadata"] == {}
    assert payload["layers"] == []
    assert payload["load_error"] == "Unable to load features export layer catalog."


def test_features_export_omni_selector_discovery_uses_sorted_non_hidden_dirs(
    run0_module,
    tmp_path: Path,
) -> None:
    scenarios_root = tmp_path / "_pups" / "omni" / "scenarios"
    contrasts_root = tmp_path / "_pups" / "omni" / "contrasts"
    (scenarios_root / "zeta").mkdir(parents=True)
    (scenarios_root / "Alpha").mkdir(parents=True)
    (scenarios_root / ".hidden").mkdir(parents=True)
    (scenarios_root / "not_a_dir.txt").write_text("skip", encoding="utf-8")
    (contrasts_root / "mulch").mkdir(parents=True)
    (contrasts_root / "control").mkdir(parents=True)

    scenarios, contrasts = run0_module._discover_features_export_omni_selectors(str(tmp_path))

    assert [row["id"] for row in scenarios] == ["Alpha", "zeta"]
    assert [row["id"] for row in contrasts] == ["control", "mulch"]


def test_features_export_swat_catalog_discovers_runs_tables_and_latest(
    run0_module,
    tmp_path: Path,
) -> None:
    run_001 = tmp_path / "swat" / "outputs" / "run_001" / "interchange"
    run_002 = tmp_path / "swat" / "outputs" / "run_002" / "interchange"
    run_001.mkdir(parents=True)
    run_002.mkdir(parents=True)

    (run_001 / "hru.parquet").write_text("hru", encoding="utf-8")
    (run_001 / "rch.parquet").write_text("rch", encoding="utf-8")
    (run_002 / "sub.parquet").write_text("sub", encoding="utf-8")

    os.utime(tmp_path / "swat" / "outputs" / "run_001", (1000, 1000))
    os.utime(tmp_path / "swat" / "outputs" / "run_002", (2000, 2000))

    payload = run0_module._discover_features_export_swat_catalog(str(tmp_path))

    assert payload["latest_run_id"] == "002"
    assert [row["id"] for row in payload["runs"]] == ["002", "001"]
    assert payload["tables_by_run"]["001"] == ["hru", "rch"]
    assert payload["tables_by_run"]["002"] == ["sub"]
    assert payload["all_tables"] == ["hru", "rch", "sub"]


def test_features_export_resolve_utm_epsg_handles_int_str_and_invalid(run0_module) -> None:
    assert run0_module._resolve_features_export_utm_epsg(
        SimpleNamespace(map=SimpleNamespace(srid=32611))
    ) == 32611
    assert run0_module._resolve_features_export_utm_epsg(
        SimpleNamespace(map=SimpleNamespace(srid="32612"))
    ) == 32612
    assert run0_module._resolve_features_export_utm_epsg(
        SimpleNamespace(map=SimpleNamespace(srid="bad"))
    ) is None
    assert run0_module._resolve_features_export_utm_epsg(SimpleNamespace(map=None)) is None


def test_features_export_bootstrap_payload_includes_defaults_selectors_and_runtime(
    run0_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        run0_module,
        "_discover_features_export_omni_selectors",
        lambda wd: ([{"id": "uniform_low", "label": "Uniform Low"}], [{"id": "c1", "label": "Contrast 1"}]),
    )
    monkeypatch.setattr(
        run0_module,
        "_discover_features_export_swat_catalog",
        lambda wd: {
            "runs": [{"id": "run_123", "label": "run_123"}],
            "latest_run_id": "run_123",
            "tables_by_run": {"run_123": ["hru", "rch"]},
            "all_tables": ["hru", "rch"],
        },
    )
    monkeypatch.setattr(
        run0_module,
        "_build_features_export_discovery_payload",
        lambda _wd, scenarios, contrasts, swat_catalog: {
            "roads_scope_available": True,
            "available_layer_ids": [
                "watershed.subcatchments",
                "omni.scenarios.hillslopes",
            ],
            "available_families": ["watershed", "omni_scenarios"],
            "refresh_channel": "features_export",
        },
    )
    monkeypatch.setattr(
        run0_module,
        "load_builtin_profiles",
        lambda: (
            {
                "key": "post_wepp",
                "label": "Post Wepp",
                "request": {
                    "format": "geopackage",
                    "units": "project",
                    "crs": "wgs",
                    "output_scopes": ["baseline"],
                    "tabular": {"concatenate_tables": False, "temporal_layout": "wide"},
                    "swat_run_id": "latest",
                    "layers": ["watershed.subcatchments"],
                },
            },
            {
                "key": "prep_details",
                "label": "Prep details",
                "request": {
                    "format": "parquet",
                    "units": "project",
                    "crs": "wgs",
                    "output_scopes": ["baseline"],
                    "tabular": {"concatenate_tables": True, "temporal_layout": "wide"},
                    "swat_run_id": "latest",
                    "layers": ["watershed.channels"],
                },
            },
        ),
    )

    payload = run0_module._build_features_export_bootstrap_payload(
        "/tmp/fake-run",
        SimpleNamespace(readonly=True),
        32611,
    )

    assert payload["defaults"] == {
        "format": "geopackage",
        "units": "project",
        "crs": "wgs",
        "output_scopes": ["baseline"],
        "tabular": {
            "concatenate_tables": False,
            "temporal_layout": "wide",
        },
    }
    assert payload["default_profile_key"] == "post_wepp"
    assert payload["profiles"]["post_wepp"]["tabular"] == {
        "concatenate_tables": False,
        "temporal_layout": "wide",
    }
    assert payload["profiles"]["post_wepp"]["swat_run_id"] == "latest"
    assert payload["profiles"]["prep_details"]["format"] == "parquet"
    assert payload["profiles"]["prep_wepp_gpkg_gdb"]["output_scopes"] == ["baseline", "roads"]
    assert payload["profiles"]["prep_wepp_gpkg_gdb"]["scenarios"] == ["uniform_low"]
    assert "omni.scenarios.hillslopes" in payload["profiles"]["prep_wepp_gpkg_gdb"]["layers"]
    assert {"key": "post_wepp", "label": "Post Wepp"} in payload["profile_buttons"]
    assert {"key": "prep_details", "label": "Prep details"} in payload["profile_buttons"]
    assert {"key": "prep_wepp_gpkg_gdb", "label": "Post Wepp (GPKG + GDB)"} in payload["profile_buttons"]
    assert payload["omni"]["scenarios"] == [{"id": "uniform_low", "label": "Uniform Low"}]
    assert payload["omni"]["contrasts"] == [{"id": "c1", "label": "Contrast 1"}]
    assert payload["swat"]["preferred_run_id"] == "run_123"
    assert payload["resolved_utm_epsg"] == 32611
    assert payload["utm_available"] is True
    assert payload["runtime"]["readonly"] is True


def test_features_export_bootstrap_virtual_profile_is_discovery_conditioned(
    run0_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run0_module, "_discover_features_export_omni_selectors", lambda wd: ([], []))
    monkeypatch.setattr(
        run0_module,
        "_discover_features_export_swat_catalog",
        lambda wd: {"runs": [], "latest_run_id": None, "tables_by_run": {}, "all_tables": []},
    )
    monkeypatch.setattr(
        run0_module,
        "_build_features_export_discovery_payload",
        lambda _wd, scenarios, contrasts, swat_catalog: {
            "roads_scope_available": False,
            "available_layer_ids": ["watershed.subcatchments"],
            "available_families": ["watershed"],
            "refresh_channel": "features_export",
        },
    )
    monkeypatch.setattr(
        run0_module,
        "load_builtin_profiles",
        lambda: (
            {
                "key": "post_wepp",
                "label": "Post Wepp",
                "request": {
                    "format": "geopackage",
                    "units": "project",
                    "crs": "wgs",
                    "output_scopes": ["baseline"],
                    "layers": ["watershed.subcatchments"],
                },
            },
        ),
    )

    payload = run0_module._build_features_export_bootstrap_payload(
        "/tmp/fake-run",
        SimpleNamespace(readonly=False),
        None,
    )

    virtual_profile = payload["profiles"]["prep_wepp_gpkg_gdb"]
    assert virtual_profile["output_scopes"] == ["baseline"]
    assert virtual_profile.get("scenarios") in (None, [])
    assert "omni.scenarios.hillslopes" not in virtual_profile["layers"]


def test_run_page_bootstrap_ttl_missing_expires_at_defaults_to_null(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["current_ttl"] = {
        "policy": "disabled",
        "user_disabled": False,
        "disabled_reason": "readonly",
    }
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert re.search(r'"expiresAt"\s*:\s*null', js) is not None


def test_run_page_bootstrap_ttl_missing_fields_defaults_cleanly(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["current_ttl"] = {}
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert re.search(r'"policy"\s*:\s*null', js) is not None
    assert re.search(r'"userDisabled"\s*:\s*false', js) is not None
    assert re.search(r'"disabledReason"\s*:\s*null', js) is not None
    assert re.search(r'"expiresAt"\s*:\s*null', js) is not None


def test_run_page_bootstrap_public_readonly_ttl_missing_expires_at(run0_template_app) -> None:
    context = _bootstrap_context(set())
    context["ron"].readonly = True
    context["user"] = SimpleNamespace(is_authenticated=False)
    context["current_ttl"] = {
        "policy": "disabled",
        "user_disabled": False,
        "disabled_reason": "readonly",
    }

    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)

    assert re.search(r'"readonly"\s*:\s*true', js) is not None
    assert re.search(r'"isAuthenticated"\s*:\s*false', js) is not None
    assert re.search(r'"expiresAt"\s*:\s*null', js) is not None
