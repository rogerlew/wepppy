from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("pulp")

from wepppy.nodb.mods.path_ce_model import ce_select_sites_2, path_data_ag

pytestmark = pytest.mark.unit


def _write_path_data_inputs(tmp_path, hillslope_df, outlet_df, hillslope_char_df):
    hillslope_path = tmp_path / "hillslope.csv"
    outlet_path = tmp_path / "outlet.csv"
    hillslope_char_path = tmp_path / "hillslope_char.csv"

    hillslope_df.to_csv(hillslope_path, index=False)
    outlet_df.to_csv(outlet_path, index=False)
    hillslope_char_df.to_csv(hillslope_char_path, index=False)

    return str(hillslope_path), str(outlet_path), str(hillslope_char_path)


def _build_hillslope_df():
    def row(
        scenario,
        *,
        landuse,
        sdyd_t,
        runoff_mm,
        lateral_mm,
        baseflow_mm,
        ntu,
    ):
        return {
            "WeppID": 1,
            "TopazID": 10,
            "Landuse": landuse,
            "Soil": "S1",
            "Length (m)": 100.0,
            "Hillslope Area (ha)": 1.0,
            "Runoff (mm)": runoff_mm,
            "Lateral Flow (mm)": lateral_mm,
            "Baseflow (mm)": baseflow_mm,
            "Soil Loss (kg/ha)": 1000.0,
            "Sediment Deposition (kg/ha)": 20.0,
            "Sediment Yield (kg/ha)": 980.0,
            "scenario": scenario,
            "Runoff (m^3)": 100.0,
            "Lateral Flow (m^3)": 20.0,
            "Baseflow (m^3)": 5.0,
            "Soil Loss (t)": 1.0,
            "Sediment Deposition (t)": 0.02,
            "Sediment Yield (t)": sdyd_t,
            "NTU (g/L)": ntu,
        }

    return pd.DataFrame(
        [
            row(
                "mulch_15_sbs_map",
                landuse=105,
                sdyd_t=8.0,
                runoff_mm=90.0,
                lateral_mm=18.0,
                baseflow_mm=5.0,
                ntu=30.0,
            ),
            row(
                "mulch_30_sbs_map",
                landuse=105,
                sdyd_t=6.0,
                runoff_mm=80.0,
                lateral_mm=16.0,
                baseflow_mm=4.0,
                ntu=25.0,
            ),
            row(
                "mulch_60_sbs_map",
                landuse=105,
                sdyd_t=4.0,
                runoff_mm=70.0,
                lateral_mm=14.0,
                baseflow_mm=4.0,
                ntu=20.0,
            ),
            row(
                "sbs_map",
                landuse=105,
                sdyd_t=10.0,
                runoff_mm=100.0,
                lateral_mm=20.0,
                baseflow_mm=5.0,
                ntu=40.0,
            ),
            row(
                "undisturbed",
                landuse=105,
                sdyd_t=2.0,
                runoff_mm=50.0,
                lateral_mm=10.0,
                baseflow_mm=3.0,
                ntu=10.0,
            ),
        ]
    )


def _build_outlet_df():
    def row(suffix, value):
        return {
            "key": "Avg. Ann. sediment discharge from outlet",
            "v": value,
            "units": "kg",
            "control_scenario": "sbs_map",
            "contrast_topaz_id": 10,
            "contrast": f"prefix_{suffix}",
            "_contrast_name": "contrast",
            "contrast_id": 1,
            "control_v": 120.0,
            "control_units": "kg",
            "control-contrast_v": 0.0,
        }

    return pd.DataFrame(
        [
            row("mulch_15_sbs_map", 90.0),
            row("mulch_30_sbs_map", 70.0),
            row("mulch_60_sbs_map", 50.0),
        ]
    )


def _build_hillslope_char_df():
    return pd.DataFrame(
        [
            {
                "slope_scalar": 1.0,
                "length": 100.0,
                "width": 10.0,
                "direction": 180.0,
                "aspect": 90.0,
                "area": 10000.0,
                "elevation": 1000.0,
                "centroid_px": 1.0,
                "centroid_py": 1.0,
                "centroid_lon": -120.0,
                "centroid_lat": 45.0,
                "wepp_id": 1,
                "TopazID": 10,
                "topaz_id": 10,
            }
        ]
    )


def test_path_data_ag_builds_aggregated_outputs(tmp_path):
    hillslope_df = _build_hillslope_df()
    outlet_df = _build_outlet_df()
    hillslope_char_df = _build_hillslope_char_df()
    hillslope_path, outlet_path, hillslope_char_path = _write_path_data_inputs(
        tmp_path=tmp_path,
        hillslope_df=hillslope_df,
        outlet_df=outlet_df,
        hillslope_char_df=hillslope_char_df,
    )

    result = path_data_ag(hillslope_path, outlet_path, hillslope_char_path)

    assert list(result["wepp_id"]) == [1]
    assert list(result["Burn severity"]) == ["High"]
    assert float(result.loc[0, "Sddc reduction 0.5 tons/acre"]) == pytest.approx(30.0)
    assert float(result.loc[0, "Sdyd reduction 1 tons/acre"]) == pytest.approx(4.0)
    assert float(result.loc[0, "NTU reduction 2 tons/acre"]) == pytest.approx(20.0)
    assert float(result.loc[0, "area"]) == pytest.approx(1.0)
    assert float(result.loc[0, "slope_deg"]) == pytest.approx(45.0)


def test_path_data_ag_raises_for_missing_required_columns(tmp_path):
    hillslope_df = _build_hillslope_df().drop(columns=["NTU (g/L)"])
    outlet_df = _build_outlet_df()
    hillslope_char_df = _build_hillslope_char_df()
    hillslope_path, outlet_path, hillslope_char_path = _write_path_data_inputs(
        tmp_path=tmp_path,
        hillslope_df=hillslope_df,
        outlet_df=outlet_df,
        hillslope_char_df=hillslope_char_df,
    )

    with pytest.raises(ValueError, match="Hillslope data file is missing required columns"):
        path_data_ag(hillslope_path, outlet_path, hillslope_char_path)


def test_ce_select_sites_2_returns_expected_tuple_and_readds_filtered_hillslopes():
    data = pd.DataFrame(
        {
            "wepp_id": [101, 102],
            "slope_deg": [5.0, 25.0],
            "Burn severity": ["High", "High"],
            "NTU post-fire": [10.0, 5.0],
            "Sdyd post-fire": [5.0, 3.0],
            "area": [1.0, 1.5],
            "NTU reduction 0.5 tons/acre": [3.0, 2.0],
            "NTU reduction 1 tons/acre": [4.0, 2.0],
            "Sdyd reduction 0.5 tons/acre": [4.0, 2.0],
            "Sdyd reduction 1 tons/acre": [1.0, 3.0],
            "Sdyd post-treat 0.5 tons/acre": [1.0, 1.0],
            "Sdyd post-treat 1 tons/acre": [4.0, 0.0],
        }
    )

    result = ce_select_sites_2(
        data=data,
        treatments=["0.5 tons/acre", "1 tons/acre"],
        treatment_cost=[100.0, 50.0],
        treatment_quantity=[1.0, 1.0],
        fixed_cost=[10.0, 5.0],
        sdyd_threshold=1.0,
        sddc_threshold=20.0,
        slope_range=(0.0, 10.0),
        bs_threshold=["High"],
    )

    assert result is not None

    (
        treatment_cost_vectors,
        _sediment_yield_reduction_thresholds,
        selected_hillslopes,
        treatment_hillslopes,
        _total_sddc_reduction,
        _final_sddc,
        hillslopes_sdyd,
        sdyd_df,
        _untreatable_sdyd,
        _total_cost,
        _total_fixed_cost,
    ) = result

    assert set(treatment_cost_vectors.keys()) == {"0.5 tons/acre", "1 tons/acre"}
    assert selected_hillslopes == [101]
    assert treatment_hillslopes[0] == [101]
    assert treatment_hillslopes[1] == []
    assert len(hillslopes_sdyd) == 1
    assert list(sdyd_df["wepp_id"]) == [101, 102]
