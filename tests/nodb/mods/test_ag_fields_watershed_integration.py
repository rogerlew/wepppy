from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from osgeo import gdal

from wepppy.nodb.mods.ag_fields import AgFields
from wepppy.nodb.mods.ag_fields import watershed_integration as integration_module
from wepppy.nodb.mods.ag_fields.watershed_integration import (
    AgFieldsWatershedIntegrationError,
    AgFieldsWatershedIntegrator,
    ParentPlan,
    SourcePlan,
)
from wepppy.topo.watershed_abstraction.wepp_top_translator import WeppTopTranslator


pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def _write_raster(path: Path, values: np.ndarray, *, transform: tuple[float, ...] = (0, 10, 0, 20, 0, -10)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(str(path), values.shape[1], values.shape[0], 1, gdal.GDT_Int32)
    dataset.SetGeoTransform(transform)
    dataset.SetProjection("")
    dataset.GetRasterBand(1).WriteArray(values.astype(np.int32))
    dataset.FlushCache()
    dataset = None


def _area_controller(tmp_path: Path, field_map: np.ndarray | None = None) -> SimpleNamespace:
    parent_raster = tmp_path / "dem" / "wbt" / "subwta.tif"
    subfield_raster = tmp_path / "ag_fields" / "sub_fields" / "sub_field_id_map.tif"
    _write_raster(parent_raster, np.array([[11, 11, 12], [11, 12, 12]]))
    _write_raster(
        subfield_raster,
        np.array([[1, 1, 0], [0, 2, 0]]) if field_map is None else field_map,
    )
    translator = WeppTopTranslator([11, 12], [])
    subfields = pd.DataFrame(
        [
            {"field_id": 101, "topaz_id": 11, "wepp_id": 1, "sub_field_id": 1},
            {"field_id": 202, "topaz_id": 12, "wepp_id": 2, "sub_field_id": 2},
        ]
    )
    return SimpleNamespace(
        wd=str(tmp_path),
        ag_field_watershed_root=str(tmp_path / "wepp" / "ag_fields" / "watershed"),
        ag_field_watershed_runs_dir=str(tmp_path / "wepp" / "ag_fields" / "watershed" / "runs"),
        ag_field_watershed_output_dir=str(tmp_path / "wepp" / "ag_fields" / "watershed" / "output"),
        ag_field_watershed_manifest_dir=str(tmp_path / "wepp" / "ag_fields" / "watershed" / "manifest"),
        ag_field_wepp_runs_dir=str(tmp_path / "wepp" / "ag_fields" / "runs"),
        ag_field_wepp_output_dir=str(tmp_path / "wepp" / "ag_fields" / "output"),
        subfields_parquet_path=str(tmp_path / "ag_fields" / "sub_fields" / "fields.parquet"),
        sub_fields_map=str(subfield_raster),
        subfields_parquet=subfields,
        watershed_instance=SimpleNamespace(
            subwta=str(parent_raster),
            translator_factory=lambda: translator,
        ),
    )


def test_area_plan_uses_aligned_raster_cells_and_preserves_parent_closure(tmp_path: Path) -> None:
    controller = _area_controller(tmp_path)
    integrator = AgFieldsWatershedIntegrator(controller)

    plans = integrator._build_area_plan()

    assert len(plans) == 2
    assert plans[0].parent_raster_area_m2 == 300.0
    assert plans[0].retained_field_area_m2 == 200.0
    assert plans[0].background_area_m2 == 100.0
    assert plans[1].parent_raster_area_m2 == 300.0
    assert plans[1].retained_field_area_m2 == 100.0
    assert plans[1].background_area_m2 == 200.0
    for plan in plans:
        assert sum(source.represented_area_m2 for source in plan.sources) == plan.parent_raster_area_m2


def test_area_plan_rejects_subfield_cells_owned_by_another_parent(tmp_path: Path) -> None:
    controller = _area_controller(tmp_path, np.array([[1, 1, 0], [2, 0, 0]]))
    integrator = AgFieldsWatershedIntegrator(controller)

    with pytest.raises(AgFieldsWatershedIntegrationError, match="mismatches parent ownership"):
        integrator._build_area_plan()


def test_materialization_stages_exactly_one_pass_for_each_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _area_controller(tmp_path)
    controller.climate_instance = SimpleNamespace(input_years=2)
    controller.wepp_instance = SimpleNamespace(wepp_bin="test-wepp")
    integrator = AgFieldsWatershedIntegrator(controller, max_workers=2)
    integrator.plans = (
        ParentPlan(11, 1, 300.0, 0.0, 300.0, (SourcePlan("background:1", "background", 300.0, integrator.background_pass_dir / "H1.pass.dat"),)),
        ParentPlan(12, 2, 300.0, 0.0, 300.0, (SourcePlan("background:2", "background", 300.0, integrator.background_pass_dir / "H2.pass.dat"),)),
    )
    integrator.parent_runs_dir.mkdir(parents=True)
    for wepp_id in (1, 2):
        for suffix in ("cli", "man", "slp", "sol"):
            (integrator.parent_runs_dir / f"p{wepp_id}.{suffix}").write_text(suffix, encoding="utf-8")
    for name in ("pw0.chn", "pw0.cli", "pw0.man", "pw0.slp", "pw0.sol", "pw0.str"):
        (integrator.parent_runs_dir / name).write_text(name, encoding="utf-8")

    monkeypatch.setattr(integration_module, "make_hillslope_run", lambda *_args, **_kwargs: None)

    materialized: list[int] = []

    def fake_run(wepp_id: int, _runs_dir: str, **_kwargs: object) -> None:
        materialized.append(wepp_id)
        (integrator.output_dir / f"H{wepp_id}.pass.dat").write_text("pass", encoding="utf-8")

    monkeypatch.setattr(integration_module, "run_hillslope", fake_run)
    integrator._reset_isolated_tree()
    integrator._materialize_parents()

    assert sorted(path.name for path in integrator.output_dir.glob("H*.pass.dat")) == [
        "H1.pass.dat",
        "H2.pass.dat",
    ]
    assert sorted(materialized) == [1, 2]
    assert (integrator.background_pass_dir / "H1.pass.dat").stat().st_ino == (
        integrator.output_dir / "H1.pass.dat"
    ).stat().st_ino
    assert (integrator.runs_dir / "p1.cli").read_text(encoding="utf-8") == "cli"


def test_historical_state_defaults_without_migration(tmp_path: Path) -> None:
    controller = AgFields(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    with controller.locked():
        controller.__dict__.pop("_watershed_integration_source_signature", None)
        controller.__dict__.pop("_watershed_integration_summary", None)
        controller.__dict__.pop("_watershed_integration_status", None)
        controller.__dict__.pop("_watershed_integration_error", None)

    state = controller.get_watershed_integration_state()

    assert state["status"] == "not_run"
    assert state["summary"] is None
    assert state["source_signature"] is None


def test_completed_state_checks_upstream_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = AgFields(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    summary = {
        "status": "completed",
        "stage4_source_signature": None,
        "upstream_timestamps": {
            str(task): index
            for index, task in enumerate(
                (
                    integration_module.TaskEnum.abstract_watershed,
                    integration_module.TaskEnum.build_landuse,
                    integration_module.TaskEnum.build_soils,
                    integration_module.TaskEnum.build_climate,
                    integration_module.TaskEnum.run_wepp_hillslopes,
                    integration_module.TaskEnum.run_ag_fields,
                ),
                start=1,
            )
        },
    }
    manifest = Path(controller.ag_field_watershed_manifest_dir) / "integration_summary.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(summary), encoding="utf-8")
    with controller.locked():
        controller._watershed_integration_summary = summary
        controller._watershed_integration_status = "completed"
    timestamps = summary["upstream_timestamps"]
    prep = {str(task): timestamps[str(task)] for task in integration_module.TaskEnum if str(task) in timestamps}
    monkeypatch.setattr(
        "wepppy.nodb.mods.ag_fields.ag_fields.RedisPrep.tryGetInstance",
        lambda _wd: prep,
    )
    monkeypatch.setattr(controller, "get_staleness", lambda: {"wepp_runs": False})

    state = controller.get_watershed_integration_state()

    assert state["status"] == "completed"
    assert state["stale"] is False


def test_run_clears_prior_terminal_state_before_long_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = AgFields(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    with controller.locked():
        controller._watershed_integration_source_signature = "old-signature"
        controller._watershed_integration_summary = {"status": "completed"}

    class FakeIntegrator:
        phase = "preflight"

        def __init__(self, facade: AgFields, **_kwargs: object) -> None:
            assert facade._watershed_integration_source_signature is None
            assert facade._watershed_integration_summary is None

        def run(self) -> dict[str, str]:
            return {"source_signature": "new-signature", "status": "completed"}

    monkeypatch.setattr(integration_module, "AgFieldsWatershedIntegrator", FakeIntegrator)

    summary = controller.run_watershed_integration()

    assert summary["source_signature"] == "new-signature"
    assert controller.get_watershed_integration_state()["status"] == "completed"


def test_clear_removes_only_fixed_isolated_tree(tmp_path: Path) -> None:
    controller = AgFields(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    baseline = tmp_path / "wepp" / "output" / "keep.txt"
    baseline.parent.mkdir(parents=True)
    baseline.write_text("authoritative", encoding="utf-8")
    isolated = Path(controller.ag_field_watershed_output_dir) / "remove.txt"
    isolated.parent.mkdir(parents=True)
    isolated.write_text("isolated", encoding="utf-8")

    controller.clear_watershed_integration()

    assert baseline.read_text(encoding="utf-8") == "authoritative"
    assert not Path(controller.ag_field_watershed_root).exists()


def test_clear_rejects_symlinked_isolated_root(tmp_path: Path) -> None:
    controller = AgFields(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    external = tmp_path / "external"
    external.mkdir()
    root = Path(controller.ag_field_watershed_root)
    root.parent.mkdir(parents=True, exist_ok=True)
    root.symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinked"):
        controller.clear_watershed_integration()


def test_clear_rejects_symlinked_isolated_ancestor(tmp_path: Path) -> None:
    controller = AgFields(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    external = tmp_path / "external"
    (external / "watershed").mkdir(parents=True)
    wepp = tmp_path / "wepp"
    wepp.mkdir(exist_ok=True)
    ag_fields = wepp / "ag_fields"
    ag_fields.rename(external / "original_ag_fields")
    ag_fields.symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinked"):
        controller.clear_watershed_integration()


def test_input_validation_rejects_symlinks_and_run_root_escapes(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    external = tmp_path / "external.cli"
    external.write_text("climate", encoding="utf-8")
    linked = run_root / "linked.cli"
    linked.symlink_to(external)

    with pytest.raises(AgFieldsWatershedIntegrationError, match="Symlink input"):
        AgFieldsWatershedIntegrator._require_regular_file(linked, root=run_root)
    with pytest.raises(AgFieldsWatershedIntegrationError, match="escapes the run root"):
        AgFieldsWatershedIntegrator._require_regular_file(external, root=run_root)


def test_manifest_schemas_match_frozen_v1_contract() -> None:
    source_names = integration_module._source_schema().names
    event_names = integration_module._event_schema().names
    run_names = integration_module._run_schema().names

    assert source_names[:8] == [
        "schema_version",
        "algorithm",
        "semantic_contract",
        "adr",
        "parent_topaz_id",
        "parent_wepp_id",
        "source_id",
        "source_kind",
    ]
    assert "raw_runvol_m3" in source_names
    assert "weighted_sediment_class_5_kg" in source_names
    assert "budget_tdet_kg" in event_names
    assert "max_event_budget_ratio_sediment_class_5_kg" in run_names
    assert integration_module._source_schema().metadata == {
        b"schema_version": b"1.0",
        b"algorithm": b"ag_fields_v1",
        b"semantic_contract": b"ag_fields_pass_semantics_v1",
        b"adr": b"ADR-0018",
    }


def test_preflight_failure_persists_sanitized_terminal_summary(tmp_path: Path) -> None:
    controller = _area_controller(tmp_path)
    controller.wepp_instance = SimpleNamespace(wepp_bin=None)
    controller.wepp_bin = None
    integrator = AgFieldsWatershedIntegrator(controller)
    integrator.phase = "preflight"

    integrator._write_failure_summary(RuntimeError(f"invalid input under {tmp_path}"))

    summary = json.loads(
        (integrator.manifest_dir / "integration_summary.json").read_text(encoding="utf-8")
    )
    assert summary["status"] == "failed"
    assert summary["failure"]["phase"] == "preflight"
    assert str(tmp_path) not in summary["failure"]["message"]
