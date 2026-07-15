from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.ag_fields.hybrid_integration import AgFieldsHybridIntegrator
from wepppy.nodb.mods.ag_fields.watershed_integration import (
    AgFieldsWatershedIntegrationError,
    ParentPlan,
    SourcePlan,
)


def _controller(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        wd=str(tmp_path),
        ag_field_watershed_root=str(
            tmp_path / "wepp" / "ag_fields" / "watershed"
        ),
        ag_field_wepp_runs_dir=str(tmp_path / "wepp" / "ag_fields" / "runs"),
        ag_field_wepp_output_dir=str(tmp_path / "wepp" / "ag_fields" / "output"),
    )


def _source(
    tmp_path: Path,
    source_id: str,
    area: float,
    sub_field_id: int | None = None,
) -> SourcePlan:
    return SourcePlan(
        source_id=source_id,
        source_kind="background" if sub_field_id is None else "sub_field",
        represented_area_m2=area,
        pass_path=tmp_path / f"{source_id}.pass.dat",
        sub_field_id=sub_field_id,
    )


def test_hybrid_workspace_is_fixed_below_scheme_slug(tmp_path: Path) -> None:
    integrator = AgFieldsHybridIntegrator(_controller(tmp_path))

    integrator._reset_isolated_tree()

    assert integrator.root == (
        tmp_path / "wepp" / "ag_fields" / "watershed" / "hybrid"
    )
    assert integrator.runs_dir.is_dir()
    assert integrator.output_dir.is_dir()
    assert integrator.manifest_dir.is_dir()


def test_hybrid_plan_uses_residual_source_plus_connected_sources(
    tmp_path: Path,
) -> None:
    integrator = AgFieldsHybridIntegrator(_controller(tmp_path))
    integrator.connectivity_payload = {
        "subfields": [
            {"subfield_id": 1, "channel_connected": True},
            {"subfield_id": 2, "channel_connected": False},
        ]
    }
    baseline = ParentPlan(
        parent_topaz_id=11,
        parent_wepp_id=1,
        parent_raster_area_m2=300.0,
        retained_field_area_m2=200.0,
        background_area_m2=100.0,
        sources=(
            _source(tmp_path, "background", 100.0),
            _source(tmp_path, "field:1", 100.0, 1),
            _source(tmp_path, "field:2", 100.0, 2),
        ),
    )

    plans = integrator._build_hybrid_plans(
        (baseline,),
        {
            1: {
                "routing_branch": "mixed",
                "residual_area_m2": 200.0,
                "connected_area_m2": 100.0,
            }
        },
    )

    plan = plans[0]
    assert plan.parent_raster_area_m2 == 300.0
    assert plan.background_area_m2 == 200.0
    assert plan.retained_field_area_m2 == 100.0
    assert [source.source_id for source in plan.sources] == [
        "concept_1_residual:1",
        "field:1",
    ]
    assert plan.sources[0].pass_path == integrator.background_pass_dir / "H1.pass.dat"


def test_hybrid_plan_stages_pure_concept1_without_weighted_recombination(
    tmp_path: Path,
) -> None:
    integrator = AgFieldsHybridIntegrator(_controller(tmp_path))
    integrator.connectivity_payload = {
        "subfields": [{"subfield_id": 2, "channel_connected": False}]
    }
    baseline = ParentPlan(
        parent_topaz_id=11,
        parent_wepp_id=1,
        parent_raster_area_m2=300.0,
        retained_field_area_m2=100.0,
        background_area_m2=200.0,
        sources=(
            _source(tmp_path, "background", 200.0),
            _source(tmp_path, "field:2", 100.0, 2),
        ),
    )

    plan = integrator._build_hybrid_plans(
        (baseline,),
        {
            1: {
                "routing_branch": "pure_concept_1",
                "residual_area_m2": 300.0,
                "connected_area_m2": 0.0,
            }
        },
    )[0]

    assert plan.affected is False
    assert len(plan.sources) == 1
    assert plan.sources[0].pass_path == integrator.output_dir / "H1.pass.dat"


def test_hybrid_plan_uses_only_connected_sources_at_full_coverage(
    tmp_path: Path,
) -> None:
    integrator = AgFieldsHybridIntegrator(_controller(tmp_path))
    integrator.connectivity_payload = {
        "subfields": [{"subfield_id": 1, "channel_connected": True}]
    }
    baseline = ParentPlan(
        parent_topaz_id=11,
        parent_wepp_id=1,
        parent_raster_area_m2=300.0,
        retained_field_area_m2=300.0,
        background_area_m2=0.0,
        sources=(_source(tmp_path, "field:1", 300.0, 1),),
    )

    plan = integrator._build_hybrid_plans(
        (baseline,),
        {
            1: {
                "routing_branch": "pure_concept_2",
                "residual_area_m2": 0.0,
                "connected_area_m2": 300.0,
            }
        },
    )[0]

    assert plan.affected is True
    assert plan.background_area_m2 == 0.0
    assert [source.source_id for source in plan.sources] == ["field:1"]


def test_hybrid_residual_pass_records_serialized_area_check(tmp_path: Path) -> None:
    pass_path = tmp_path / "H1.pass.dat"
    pass_path.write_text(
        "p1.cli\nheader\n1.0000E+02\nheader\nheader\n1 2 3\n",
        encoding="utf-8",
    )

    diagnostic = AgFieldsHybridIntegrator._validate_residual_pass(
        1,
        pass_path,
        {"serialized_target_area_m2": 100.002},
    )

    assert diagnostic["serialized_residual_area_m2"] == 100.002
    assert diagnostic["residual_pass_header_area_m2"] == 100.0
    assert diagnostic["residual_pass_area_residual_m2"] == pytest.approx(-0.002)
    assert diagnostic["residual_pass_area_budget_m2"] == pytest.approx(0.0050001)


def test_hybrid_residual_pass_rejects_area_drift_and_nonfinite_data(
    tmp_path: Path,
) -> None:
    pass_path = tmp_path / "H1.pass.dat"
    pass_path.write_text(
        "p1.cli\nheader\n1.0000E+02\nheader\nheader\n1 2 3\n",
        encoding="utf-8",
    )

    with pytest.raises(AgFieldsWatershedIntegrationError, match="serialized slope area"):
        AgFieldsHybridIntegrator._validate_residual_pass(
            1,
            pass_path,
            {"serialized_target_area_m2": 99.0},
        )

    pass_path.write_text(
        "p1.cli\nheader\n1.0000E+02\nheader\nheader\n1 NaN 3\n",
        encoding="utf-8",
    )
    with pytest.raises(AgFieldsWatershedIntegrationError, match="non-finite"):
        AgFieldsHybridIntegrator._validate_residual_pass(
            1,
            pass_path,
            {"serialized_target_area_m2": 100.0},
        )
