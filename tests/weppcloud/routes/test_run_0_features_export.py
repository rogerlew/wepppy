"""Run-page Features Export catalog and bootstrap contracts."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.routes


@pytest.fixture()
def export_columns():
    return importlib.import_module("wepppy.weppcloud.routes.run_0.features_export_columns")


@pytest.fixture()
def export_presentation():
    return importlib.import_module("wepppy.weppcloud.routes.run_0.features_export_presentation")


def test_features_export_catalog_payload_builds_from_catalog(
    export_presentation,
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
    monkeypatch.setattr(export_presentation, "load_layer_catalog", lambda: fake_catalog)

    payload = export_presentation._build_features_export_catalog_payload()

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
    export_presentation,
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
    monkeypatch.setattr(export_presentation, "load_layer_catalog", lambda: fake_catalog)
    monkeypatch.setattr(
        export_presentation,
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

    payload = export_presentation._build_features_export_catalog_payload("/tmp/features-export")
    layer = payload["layers"][0]

    assert [entry["column_id"] for entry in layer["columns"]] == ["TopazID", "Runoff Volume"]
    assert layer["columns"][1]["display_unit"] == "m^3"
    assert layer["columns"][1]["description"] == "Runoff volume exported from interchange schema."


def test_features_export_column_contract_dedupes_and_infers_units(export_columns) -> None:
    columns, required_columns = export_columns._features_export_column_contract(
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
    export_columns,
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

    parsed = export_columns._features_export_parse_interchange_readme(readme_path)
    docs = parsed["loss_pw0.hill.parquet"]

    assert docs["exact"]["Runoff Volume"]["display_unit"] == "m^3"
    assert docs["exact"]["Runoff Volume"]["description"] == "Annual runoff volume"
    assert docs["match"]["runoffvolume"]["label"] == "Runoff Volume"


def test_features_export_catalog_payload_handles_catalog_load_failure(
    export_presentation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_catalog_load() -> None:
        raise RuntimeError("catalog unavailable")

    monkeypatch.setattr(export_presentation, "load_layer_catalog", _raise_catalog_load)

    payload = export_presentation._build_features_export_catalog_payload()

    assert payload["metadata"] == {}
    assert payload["layers"] == []
    assert payload["load_error"] == "Unable to load features export layer catalog."


def test_features_export_omni_selector_discovery_uses_sorted_non_hidden_dirs(
    export_presentation,
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

    scenarios, contrasts = export_presentation._discover_features_export_omni_selectors(str(tmp_path))

    assert [row["id"] for row in scenarios] == ["Alpha", "zeta"]
    assert [row["id"] for row in contrasts] == ["control", "mulch"]


def test_features_export_swat_catalog_discovers_runs_tables_and_latest(
    export_presentation,
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

    payload = export_presentation._discover_features_export_swat_catalog(str(tmp_path))

    assert payload["latest_run_id"] == "002"
    assert [row["id"] for row in payload["runs"]] == ["002", "001"]
    assert payload["tables_by_run"]["001"] == ["hru", "rch"]
    assert payload["tables_by_run"]["002"] == ["sub"]
    assert payload["all_tables"] == ["hru", "rch", "sub"]


def test_features_export_resolve_utm_epsg_handles_int_str_and_invalid(export_presentation) -> None:
    assert export_presentation._resolve_features_export_utm_epsg(
        SimpleNamespace(map=SimpleNamespace(srid=32611))
    ) == 32611
    assert export_presentation._resolve_features_export_utm_epsg(
        SimpleNamespace(map=SimpleNamespace(srid="32612"))
    ) == 32612
    assert export_presentation._resolve_features_export_utm_epsg(
        SimpleNamespace(map=SimpleNamespace(srid="bad"))
    ) is None
    assert export_presentation._resolve_features_export_utm_epsg(SimpleNamespace(map=None)) is None


def test_features_export_bootstrap_payload_includes_defaults_selectors_and_runtime(
    export_presentation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        export_presentation,
        "_discover_features_export_omni_selectors",
        lambda wd: ([{"id": "uniform_low", "label": "Uniform Low"}], [{"id": "c1", "label": "Contrast 1"}]),
    )
    monkeypatch.setattr(
        export_presentation,
        "_discover_features_export_swat_catalog",
        lambda wd: {
            "runs": [{"id": "run_123", "label": "run_123"}],
            "latest_run_id": "run_123",
            "tables_by_run": {"run_123": ["hru", "rch"]},
            "all_tables": ["hru", "rch"],
        },
    )
    monkeypatch.setattr(
        export_presentation,
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
        export_presentation,
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

    payload = export_presentation._build_features_export_bootstrap_payload(
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
    export_presentation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(export_presentation, "_discover_features_export_omni_selectors", lambda wd: ([], []))
    monkeypatch.setattr(
        export_presentation,
        "_discover_features_export_swat_catalog",
        lambda wd: {"runs": [], "latest_run_id": None, "tables_by_run": {}, "all_tables": []},
    )
    monkeypatch.setattr(
        export_presentation,
        "_build_features_export_discovery_payload",
        lambda _wd, scenarios, contrasts, swat_catalog: {
            "roads_scope_available": False,
            "available_layer_ids": ["watershed.subcatchments"],
            "available_families": ["watershed"],
            "refresh_channel": "features_export",
        },
    )
    monkeypatch.setattr(
        export_presentation,
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

    payload = export_presentation._build_features_export_bootstrap_payload(
        "/tmp/fake-run",
        SimpleNamespace(readonly=False),
        None,
    )

    virtual_profile = payload["profiles"]["prep_wepp_gpkg_gdb"]
    assert virtual_profile["output_scopes"] == ["baseline"]
    assert virtual_profile.get("scenarios") in (None, [])
    assert "omni.scenarios.hillslopes" not in virtual_profile["layers"]
