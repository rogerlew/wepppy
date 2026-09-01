from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import importlib

import pytest
from flask import Flask

from wepppy.nodb.core.watershed import DelineationBackend
from wepppy.nodb.project_config_capabilities import RunCapabilityMode
from wepppy.weppcloud.routes._run_context import load_run_context

run0_module = importlib.import_module("wepppy.weppcloud.routes.run_0.run_0_bp")

pytestmark = [pytest.mark.routes, pytest.mark.unit]


def test_builder_manifest_for_reserved_config_token_is_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run0_module, "project_config_manifest_source_kind", lambda *_args, **_kwargs: "builder")

    assert run0_module._resolve_run_config_maturity_label("config", "/wc1/runs/aa/example", "example", None) == "Preview"


def test_nonbuilder_or_other_token_does_not_invent_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run0_module, "project_config_manifest_source_kind", lambda *_args, **_kwargs: None)
    stable = SimpleNamespace(maturity="stable")

    assert run0_module._resolve_run_config_maturity_label("config", "/wc1/runs/aa/example", "example", None) is None
    assert run0_module._resolve_run_config_maturity_label("disturbed9002", "/wc1/runs/aa/example", "example", stable) == "Stable"


def test_config_summary_uses_effective_runtime_and_stored_selection_authority() -> None:
    authority = SimpleNamespace(
        mode=RunCapabilityMode.STORED,
        locale_profile="continental-us",
        graph=SimpleNamespace(
            defaults={
                "dem_source": "usgs-ned1-2024",
                "climate_station_database": "cligen-stations-2015",
            }
        ),
    )

    summary = run0_module._build_run_config_summary(
        "config",
        authority,
        SimpleNamespace(cellsize=10.0),
        SimpleNamespace(delineation_backend=DelineationBackend.WBT),
        SimpleNamespace(multi_ofe=True),
    )

    assert summary == {
        "locale_id": "continental-us",
        "rows": (
            ("Locale", "continental-us"),
            ("Delineation Backend", "wbt"),
            ("Representation", "Multiple OFE"),
            ("DEM Data Source", "usgs-ned1-2024"),
            ("Cell Size (m)", "10"),
            ("CLIGEN Database", "cligen-stations-2015"),
        ),
    }


def test_config_summary_does_not_substitute_live_graph_defaults() -> None:
    authority = SimpleNamespace(
        mode=RunCapabilityMode.LEGACY_BUILDER,
        locale_profile="europe",
        graph=SimpleNamespace(
            defaults={
                "dem_source": "copernicus-dem-30m",
                "climate_station_database": "cligen-stations-ghcn",
            }
        ),
    )

    summary = run0_module._build_run_config_summary(
        "config",
        authority,
        SimpleNamespace(cellsize=float("nan")),
        SimpleNamespace(delineation_backend=""),
        SimpleNamespace(multi_ofe=False),
    )

    assert summary == {
        "locale_id": "europe",
        "rows": (
            ("Locale", "europe"),
            ("Delineation Backend", "Not available"),
            ("Representation", "Single OFE"),
            ("DEM Data Source", "Not available"),
            ("Cell Size (m)", "Not available"),
            ("CLIGEN Database", "Not available"),
        ),
    }


def test_config_summary_is_scoped_to_exact_config_stem() -> None:
    summary = run0_module._build_run_config_summary(
        "disturbed9002",
        SimpleNamespace(),
        SimpleNamespace(),
        SimpleNamespace(),
        SimpleNamespace(),
    )

    assert summary is None


def test_config_summary_preserves_rows_when_effective_values_are_absent() -> None:
    summary = run0_module._build_run_config_summary(
        "config",
        None,
        SimpleNamespace(),
        SimpleNamespace(),
        SimpleNamespace(),
    )

    assert summary == {
        "locale_id": None,
        "rows": (
            ("Locale", "Not available"),
            ("Delineation Backend", "Not available"),
            ("Representation", "Not available"),
            ("DEM Data Source", "Not available"),
            ("Cell Size (m)", "Not available"),
            ("CLIGEN Database", "Not available"),
        ),
    }


def test_config_summary_loads_models_from_nested_pup_active_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run"
    child_root = run_root / "_pups" / "omni" / "scenarios" / "child"
    child_root.mkdir(parents=True)
    parent_ron = SimpleNamespace(cellsize=30)
    child_ron = SimpleNamespace(cellsize=10)
    parent_wepp = SimpleNamespace(multi_ofe=False)
    child_wepp = SimpleNamespace(multi_ofe=True)
    parent_watershed = SimpleNamespace(delineation_backend=DelineationBackend.TOPAZ)
    child_watershed = SimpleNamespace(delineation_backend=DelineationBackend.WBT)
    model_roots: list[str] = []

    def model_for_root(parent, child):
        def load(wd):
            model_roots.append(wd)
            return child if wd == str(child_root.resolve()) else parent

        return load

    monkeypatch.setattr(
        run0_module.Ron,
        "getInstance",
        staticmethod(model_for_root(parent_ron, child_ron)),
    )
    monkeypatch.setattr(
        run0_module.Watershed,
        "getInstance",
        staticmethod(model_for_root(parent_watershed, child_watershed)),
    )
    monkeypatch.setattr(
        run0_module.Wepp,
        "getInstance",
        staticmethod(model_for_root(parent_wepp, child_wepp)),
    )
    monkeypatch.setattr(
        run0_module,
        "resolve_run_capability_authority",
        lambda wepp: SimpleNamespace(
            mode=RunCapabilityMode.STORED,
            locale_profile="europe" if wepp is child_wepp else "continental-us",
            graph=SimpleNamespace(
                defaults={
                    "dem_source": "copernicus-dem-30m" if wepp is child_wepp else "usgs-ned1-2024",
                    "climate_station_database": "cligen-stations-ghcn",
                }
            ),
        ),
    )

    app = Flask(__name__)
    with app.test_request_context("/runs/test-run/config/?pup=omni/scenarios/child"):
        ctx = load_run_context(
            "test-run",
            "config",
            get_wd_fn=lambda *_args, **_kwargs: str(run_root),
        )
        summary, _graph = run0_module._load_run_config_summary("config", ctx.active_root)

    assert model_roots == [str(child_root.resolve())] * 3
    assert summary["locale_id"] == "europe"
    assert summary["rows"] == (
        ("Locale", "europe"),
        ("Delineation Backend", "wbt"),
        ("Representation", "Multiple OFE"),
        ("DEM Data Source", "copernicus-dem-30m"),
        ("Cell Size (m)", "10"),
        ("CLIGEN Database", "cligen-stations-ghcn"),
    )
