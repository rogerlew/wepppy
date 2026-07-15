from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from wepppy.nodb.mods.ag_fields.concept1_integration import (
    AgFieldsConcept1Integrator,
    PASS_HEADER_RELATIVE_AREA_BUDGET,
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


def test_concept1_workspace_is_fixed_below_scheme_slug(tmp_path: Path) -> None:
    legacy = tmp_path / "wepp" / "ag_fields" / "watershed" / "legacy.txt"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("preserve\n", encoding="utf-8")
    integrator = AgFieldsConcept1Integrator(_controller(tmp_path))

    integrator._reset_isolated_tree()

    assert integrator.root == legacy.parent / "concept-1"
    assert integrator.runs_dir.is_dir()
    assert integrator.output_dir.is_dir()
    assert integrator.manifest_dir.is_dir()
    assert legacy.read_text(encoding="utf-8") == "preserve\n"


def test_concept1_pass_validation_detects_non_finite_tokens(tmp_path: Path) -> None:
    valid = tmp_path / "valid.pass.dat"
    invalid = tmp_path / "invalid.pass.dat"
    valid.write_text("1 2 3\ninformation\n", encoding="utf-8")
    invalid.write_text("1 -Infinity 3\n", encoding="utf-8")

    assert not AgFieldsConcept1Integrator._pass_has_nonfinite(valid)
    assert AgFieldsConcept1Integrator._pass_has_nonfinite(invalid)


def test_concept1_routing_row_records_serialized_area_contract(
    tmp_path: Path,
) -> None:
    pass_path = tmp_path / "H7.pass.dat"
    pass_path.write_text("pass\n", encoding="utf-8")

    row = AgFieldsConcept1Integrator._routing_row(
        parent_topaz_id=71,
        parent_wepp_id=7,
        pass_path=pass_path,
        pass_area=124.99,
        plan_family="source_order",
        generated={
            "ofe_count": 2,
            "referenced_yearly_scenario_count": 3,
            "target_area_m2": 125.0,
            "serialized_target_area_m2": 124.995,
        },
        residual=-0.005,
        budget=0.00625,
    )

    assert row["routing_branch"] == "concept_1"
    assert row["ofe_count"] == 2
    assert row["serialized_target_area_m2"] == 124.995
    assert row["pass_area_residual_m2"] == -0.005
    assert len(row["pass_sha256"]) == 64


def test_concept1_pass_area_budget_matches_legacy_header_precision() -> None:
    assert PASS_HEADER_RELATIVE_AREA_BUDGET == 5.0e-5
    assert PASS_HEADER_RELATIVE_AREA_BUDGET * 167_410.0 == 8.3705
