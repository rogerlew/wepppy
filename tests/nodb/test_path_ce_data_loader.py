from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from wepppy.nodb.mods.path_ce.data_loader import (
    PathCEDataError,
    TreatmentOption,
    _resolve_omni_dir,
    load_solver_inputs,
)

pytestmark = pytest.mark.unit


def _touch_expected(base):
    (base / "scenarios.hillslope_summaries.parquet").touch()
    (base / "contrasts.out.parquet").touch()


def _write_parquet(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def _hillslope_summaries_df(*, scenarios: dict[str, list[dict]]) -> pd.DataFrame:
    rows: list[dict] = []
    for scenario, scenario_rows in scenarios.items():
        for row in scenario_rows:
            rows.append(
                {
                    "scenario": scenario,
                    "WeppID": row["wepp_id"],
                    "TopazID": row["topaz_id"],
                    "Landuse": row["landuse"],
                    "Sediment Yield (t)": row["sdyd"],
                    "NTU (g/L)": row["ntu"],
                    "Hillslope Area (ha)": row.get("area_ha", 1.0),
                }
            )
    return pd.DataFrame(rows)


def _watershed_hillslopes_df(*, hillslopes: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "wepp_id": row["wepp_id"],
                "topaz_id": row["topaz_id"],
                "slope_scalar": row.get("slope_scalar", 0.1),
                "area": row.get("area_m2", 10000.0),
            }
            for row in hillslopes
        ]
    )


def _outlet_contrasts_df(*, scenario_key: str, rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "key": "Avg. Ann. sediment discharge from outlet",
                "contrast": f"control_vs::{scenario_key}",
                "contrast_topaz_id": row["topaz_id"],
                "v": row["v"],
                "control_v": row["control_v"],
            }
            for row in rows
        ]
    )


def _build_run_dir(
    tmp_path: Path,
    *,
    hillslope_df: pd.DataFrame,
    watershed_df: pd.DataFrame,
    watershed_layout: str = "canonical",
    outlet_df: pd.DataFrame | None = None,
) -> Path:
    wd = tmp_path
    omni_dir = wd / "omni"
    omni_dir.mkdir(parents=True, exist_ok=True)
    _write_parquet(omni_dir / "scenarios.hillslope_summaries.parquet", hillslope_df)
    if outlet_df is not None:
        _write_parquet(omni_dir / "contrasts.out.parquet", outlet_df)

    if watershed_layout == "canonical":
        _write_parquet(wd / "watershed" / "hillslopes.parquet", watershed_df)
    else:
        raise ValueError(f"Unknown watershed_layout={watershed_layout!r}")

    return wd


def test_resolve_omni_uses_pups_layout(tmp_path):
    canonical = tmp_path / "omni"
    canonical.mkdir(parents=True)
    _touch_expected(canonical)

    resolved = _resolve_omni_dir(tmp_path)
    assert resolved == canonical


def test_resolve_omni_raises_when_missing(tmp_path):
    with pytest.raises(PathCEDataError):
        _resolve_omni_dir(tmp_path)


def test_load_solver_inputs_happy_path_with_outlet_contrasts(tmp_path):
    hillslope_df = _hillslope_summaries_df(
        scenarios={
            "post_fire": [
                {"wepp_id": 1, "topaz_id": 10, "landuse": 105, "sdyd": 10.0, "ntu": 100.0, "area_ha": 1.0},
                {"wepp_id": 2, "topaz_id": 20, "landuse": 106, "sdyd": 20.0, "ntu": 200.0, "area_ha": 2.0},
            ],
            "undisturbed": [
                {"wepp_id": 1, "topaz_id": 10, "landuse": 105, "sdyd": 5.0, "ntu": 50.0, "area_ha": 1.0},
                {"wepp_id": 2, "topaz_id": 20, "landuse": 106, "sdyd": 10.0, "ntu": 100.0, "area_ha": 2.0},
            ],
            "treat_s1": [
                {"wepp_id": 1, "topaz_id": 10, "landuse": 105, "sdyd": 8.0, "ntu": 80.0, "area_ha": 1.0},
                {"wepp_id": 2, "topaz_id": 20, "landuse": 106, "sdyd": 15.0, "ntu": 150.0, "area_ha": 2.0},
            ],
        }
    )
    watershed_df = _watershed_hillslopes_df(
        hillslopes=[
            {"wepp_id": 1, "topaz_id": 10, "slope_scalar": 0.1, "area_m2": 10000.0},
            {"wepp_id": 2, "topaz_id": 20, "slope_scalar": 0.2, "area_m2": 20000.0},
        ]
    )
    outlet_df = _outlet_contrasts_df(
        scenario_key="treat_s1",
        rows=[
            {"topaz_id": 10, "v": 50.0, "control_v": 60.0},
            {"topaz_id": 20, "v": 100.0, "control_v": 120.0},
        ],
    )

    wd = _build_run_dir(
        tmp_path,
        hillslope_df=hillslope_df,
        watershed_df=watershed_df,
        watershed_layout="canonical",
        outlet_df=outlet_df,
    )

    options = [
        TreatmentOption(label="S1", scenario="treat_s1", quantity=123.0, unit_cost=4.5, fixed_cost=6.0)
    ]
    solver_inputs = load_solver_inputs(
        wd,
        post_fire_scenario="post_fire",
        undisturbed_scenario="undisturbed",
        treatment_options=options,
    )

    assert solver_inputs.treatments == ["S1"]
    assert solver_inputs.treatment_costs == [4.5]
    assert solver_inputs.treatment_quantities == [123.0]
    assert solver_inputs.fixed_costs == [6.0]
    assert solver_inputs.scenario_lookup == {"S1": "treat_s1"}

    df = solver_inputs.data
    for col in ("Sdyd reduction S1", "Sddc reduction S1", "NTU reduction S1"):
        assert col in df.columns

    assert "Sddc post-fire" in df.columns
    assert "Sddc post-treat S1" in df.columns
    assert df["Sddc reduction S1"].notna().any()

    row = df.loc[df["wepp_id"] == 1].iloc[0]
    assert row["Sdyd reduction S1"] == pytest.approx(2.0)
    assert row["NTU reduction S1"] == pytest.approx(20.0)
    assert row["Sddc reduction S1"] == pytest.approx(10.0)


def test_load_solver_inputs_raises_when_post_fire_missing(tmp_path):
    hillslope_df = _hillslope_summaries_df(
        scenarios={
            "some_other": [
                {"wepp_id": 1, "topaz_id": 10, "landuse": 105, "sdyd": 10.0, "ntu": 100.0, "area_ha": 1.0},
            ],
            "treat_s1": [
                {"wepp_id": 1, "topaz_id": 10, "landuse": 105, "sdyd": 8.0, "ntu": 80.0, "area_ha": 1.0},
            ],
        }
    )
    watershed_df = _watershed_hillslopes_df(
        hillslopes=[{"wepp_id": 1, "topaz_id": 10, "slope_scalar": 0.1, "area_m2": 10000.0}]
    )
    wd = _build_run_dir(tmp_path, hillslope_df=hillslope_df, watershed_df=watershed_df)

    with pytest.raises(PathCEDataError, match="Post-fire scenario"):
        load_solver_inputs(
            wd,
            post_fire_scenario="post_fire",
            undisturbed_scenario=None,
            treatment_options=[TreatmentOption(label="S1", scenario="treat_s1", quantity=1.0, unit_cost=1.0)],
        )


def test_load_solver_inputs_raises_when_treatment_scenario_missing(tmp_path):
    hillslope_df = _hillslope_summaries_df(
        scenarios={
            "post_fire": [
                {"wepp_id": 1, "topaz_id": 10, "landuse": 105, "sdyd": 10.0, "ntu": 100.0, "area_ha": 1.0},
            ],
        }
    )
    watershed_df = _watershed_hillslopes_df(
        hillslopes=[{"wepp_id": 1, "topaz_id": 10, "slope_scalar": 0.1, "area_m2": 10000.0}]
    )
    wd = _build_run_dir(tmp_path, hillslope_df=hillslope_df, watershed_df=watershed_df)

    with pytest.raises(PathCEDataError, match="Treatment scenario"):
        load_solver_inputs(
            wd,
            post_fire_scenario="post_fire",
            undisturbed_scenario=None,
            treatment_options=[TreatmentOption(label="S1", scenario="treat_s1", quantity=1.0, unit_cost=1.0)],
        )


@pytest.mark.parametrize("outlet_mode", ["missing_file", "unmatched_rows"])
def test_load_solver_inputs_allows_missing_outlet_contrasts(tmp_path, outlet_mode):
    hillslope_df = _hillslope_summaries_df(
        scenarios={
            "post_fire": [
                {"wepp_id": 1, "topaz_id": 10, "landuse": 105, "sdyd": 10.0, "ntu": 100.0, "area_ha": 1.0},
            ],
            "treat_s1": [
                {"wepp_id": 1, "topaz_id": 10, "landuse": 105, "sdyd": 8.0, "ntu": 80.0, "area_ha": 1.0},
            ],
        }
    )
    watershed_df = _watershed_hillslopes_df(
        hillslopes=[{"wepp_id": 1, "topaz_id": 10, "slope_scalar": 0.1, "area_m2": 10000.0}]
    )
    outlet_df = None
    if outlet_mode == "unmatched_rows":
        outlet_df = pd.DataFrame(
            [
                {
                    "key": "Avg. Ann. sediment discharge from outlet",
                    "contrast": "control_vs::some_other_scenario",
                    "contrast_topaz_id": 10,
                    "v": 1.0,
                    "control_v": 2.0,
                }
            ]
        )

    wd = _build_run_dir(
        tmp_path,
        hillslope_df=hillslope_df,
        watershed_df=watershed_df,
        outlet_df=outlet_df,
    )

    solver_inputs = load_solver_inputs(
        wd,
        post_fire_scenario="post_fire",
        undisturbed_scenario=None,
        treatment_options=[TreatmentOption(label="S1", scenario="treat_s1", quantity=1.0, unit_cost=1.0)],
    )

    df = solver_inputs.data
    assert "Sddc post-treat S1" in df.columns
    assert df["Sddc post-treat S1"].isna().all()


def test_load_solver_inputs_custom_severity_map_unknown_fallback(tmp_path):
    hillslope_df = _hillslope_summaries_df(
        scenarios={
            "post_fire": [
                {"wepp_id": 1, "topaz_id": 10, "landuse": 105, "sdyd": 10.0, "ntu": 100.0, "area_ha": 1.0},
                {"wepp_id": 2, "topaz_id": 20, "landuse": 999, "sdyd": 20.0, "ntu": 200.0, "area_ha": 2.0},
            ],
            "treat_s1": [
                {"wepp_id": 1, "topaz_id": 10, "landuse": 105, "sdyd": 8.0, "ntu": 80.0, "area_ha": 1.0},
                {"wepp_id": 2, "topaz_id": 20, "landuse": 999, "sdyd": 15.0, "ntu": 150.0, "area_ha": 2.0},
            ],
        }
    )
    watershed_df = _watershed_hillslopes_df(
        hillslopes=[
            {"wepp_id": 1, "topaz_id": 10, "slope_scalar": 0.1, "area_m2": 10000.0},
            {"wepp_id": 2, "topaz_id": 20, "slope_scalar": 0.2, "area_m2": 20000.0},
        ]
    )
    wd = _build_run_dir(tmp_path, hillslope_df=hillslope_df, watershed_df=watershed_df)

    solver_inputs = load_solver_inputs(
        wd,
        post_fire_scenario="post_fire",
        undisturbed_scenario=None,
        treatment_options=[TreatmentOption(label="S1", scenario="treat_s1", quantity=1.0, unit_cost=1.0)],
        severity_map={"CustomHigh": {105}},
    )

    severities = set(solver_inputs.data["Burn severity"].astype(str).tolist())
    assert "CustomHigh" in severities
    assert "Unknown" in severities
