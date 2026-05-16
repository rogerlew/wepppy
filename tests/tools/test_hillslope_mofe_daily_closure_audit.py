from __future__ import annotations

import json
from pathlib import Path
import runpy

import duckdb
import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.unit


def _module() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    return runpy.run_path(str(repo_root / "tools/hillslope_mofe_daily_closure_audit.py"))


def _write_parquet(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame.from_records(records)
    con = duckdb.connect(":memory:")
    try:
        con.register("_frame", frame)
        con.execute(f"COPY _frame TO '{path.as_posix()}' (FORMAT PARQUET)")
    finally:
        con.close()


def _write_interchange(
    interchange_dir: Path,
    *,
    wat_records: list[dict[str, object]],
    pass_records: list[dict[str, object]],
    soil_records: list[dict[str, object]] | None = None,
    element_records: list[dict[str, object]] | None = None,
) -> None:
    _write_parquet(interchange_dir / "H.wat.parquet", wat_records)
    _write_parquet(interchange_dir / "H.pass.parquet", pass_records)
    if soil_records is not None:
        _write_parquet(interchange_dir / "H.soil.parquet", soil_records)
    if element_records is not None:
        _write_parquet(interchange_dir / "H.element.parquet", element_records)


def _mofe_wat_rows(wepp_id: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    ofe_area = {1: 40.0, 2: 60.0, 3: 90.0}

    def _row(
        day: int,
        julian: int,
        ofe: int,
        *,
        rm: float,
        up: float,
        subin: float,
        lat: float,
        qofe: float,
        soil_water: float,
    ) -> None:
        rows.append(
            {
                "wepp_id": wepp_id,
                "ofe_id": ofe,
                "year": 1987,
                "sim_day_index": day,
                "julian": julian,
                "month": 2,
                "day_of_month": 12 + day,
                "water_year": 1987,
                "OFE": ofe,
                "P": rm,
                "RM": rm,
                "Q": qofe,
                "Ep": 1.0,
                "Es": 0.5,
                "Er": 0.5,
                "Dp": 1.0,
                "UpStrmQ": up,
                "SubRIn": subin,
                "latqcc": lat,
                "Total-Soil Water": soil_water,
                "SoilWaterTotal": soil_water,
                "frozwt": 0.0,
                "Snow-Water": 0.0,
                "QOFE": qofe,
                "Tile": 0.0,
                "Irr": 0.0,
                "Area": ofe_area[ofe],
            }
        )

    # Day 1: exact chain closure and full-physics closure = 0 for each OFE.
    _row(1, 44, 1, rm=17.0, up=0.0, subin=0.0, lat=4.0, qofe=10.0, soil_water=100.0)
    _row(1, 44, 2, rm=2.6666667, up=6.6666667, subin=2.6666667, lat=2.0, qofe=7.0, soil_water=100.0)
    _row(1, 44, 3, rm=1.0, up=4.6666667, subin=1.3333333, lat=1.0, qofe=3.0, soil_water=100.0)

    # Day 2: intentional chain mismatches + non-zero full-physics residual.
    _row(2, 45, 1, rm=18.0, up=0.0, subin=0.0, lat=5.0, qofe=8.0, soil_water=100.0)
    _row(2, 45, 2, rm=1.0, up=6.0, subin=4.5, lat=2.5, qofe=5.0, soil_water=100.0)
    _row(2, 45, 3, rm=0.5, up=5.5, subin=3.0, lat=1.0, qofe=2.0, soil_water=100.0)

    return rows


def _mofe_pass_rows(wepp_id: int) -> list[dict[str, object]]:
    return [
        {
            "wepp_id": wepp_id,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "runvol": 0.15,
            "sbrunv": 0.02,
        },
        {
            "wepp_id": wepp_id,
            "year": 1987,
            "sim_day_index": 2,
            "julian": 45,
            "month": 2,
            "day_of_month": 14,
            "water_year": 1987,
            "runvol": 0.10,
            "sbrunv": 0.01,
        },
    ]


def _mofe_scireview_wat_rows(wepp_id: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    area = 100.0

    def _row(
        day: int,
        julian: int,
        ofe: int,
        *,
        rm: float,
        q_eff: float,
        qofe: float,
        up: float,
        subin: float,
        lat: float,
        soil_water: float,
        ep: float = 0.06,
        es: float = 0.04,
        er: float = 0.0,
        dp: float = 0.02,
    ) -> None:
        rows.append(
            {
                "wepp_id": wepp_id,
                "ofe_id": ofe,
                "year": 1987,
                "sim_day_index": day,
                "julian": julian,
                "month": 2,
                "day_of_month": 12 + day,
                "water_year": 1987,
                "OFE": ofe,
                "P": rm,
                "RM": rm,
                "Q": q_eff,
                "Ep": ep,
                "Es": es,
                "Er": er,
                "Dp": dp,
                "UpStrmQ": up,
                "SubRIn": subin,
                "latqcc": lat,
                "Total-Soil Water": soil_water,
                "SoilWaterTotal": soil_water,
                "frozwt": 0.0,
                "Snow-Water": 0.0,
                "QOFE": qofe,
                "Tile": 0.0,
                "Irr": 0.0,
                "Area": area,
            }
        )

    # Day 1 baseline.
    _row(1, 44, 1, rm=12.0, q_eff=5.0, qofe=5.0, up=0.0, subin=0.0, lat=2.0, soil_water=100.0)
    _row(1, 44, 2, rm=8.0, q_eff=6.0, qofe=6.0, up=5.0, subin=2.0, lat=1.5, soil_water=100.0)
    _row(1, 44, 3, rm=4.0, q_eff=3.0, qofe=3.0, up=6.0, subin=1.0, lat=1.0, soil_water=100.0)

    # Day 2 terminal anomaly signature with high QOFE/Q amplification and large residual.
    _row(2, 45, 1, rm=12.0, q_eff=4.0, qofe=4.0, up=0.0, subin=0.0, lat=2.0, soil_water=100.0)
    _row(2, 45, 2, rm=8.0, q_eff=6.0, qofe=6.0, up=4.0, subin=2.0, lat=1.5, soil_water=100.0)
    _row(2, 45, 3, rm=34.0, q_eff=23.0, qofe=437.8, up=210.0, subin=55.0, lat=43.5, soil_water=100.0)
    return rows


def _mofe_pure_subsurface_wat_rows(wepp_id: int) -> list[dict[str, object]]:
    return [
        {
            "wepp_id": wepp_id,
            "ofe_id": 1,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 325,
            "month": 11,
            "day_of_month": 21,
            "water_year": 1988,
            "OFE": 1,
            "P": 13.4,
            "RM": 13.4,
            "Q": 0.0,
            "Ep": 0.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 0.0,
            "UpStrmQ": 0.0,
            "SubRIn": 0.0,
            "latqcc": 50.0,
            "Total-Soil Water": 100.0,
            "SoilWaterTotal": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 0.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
        },
        {
            "wepp_id": wepp_id,
            "ofe_id": 2,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 325,
            "month": 11,
            "day_of_month": 21,
            "water_year": 1988,
            "OFE": 2,
            "P": 13.4,
            "RM": 13.4,
            "Q": 0.0,
            "Ep": 0.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 0.0,
            "UpStrmQ": 0.0,
            "SubRIn": 50.0,
            "latqcc": 110.0,
            "Total-Soil Water": 100.0,
            "SoilWaterTotal": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 0.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
        },
        {
            "wepp_id": wepp_id,
            "ofe_id": 3,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 325,
            "month": 11,
            "day_of_month": 21,
            "water_year": 1988,
            "OFE": 3,
            "P": 13.4,
            "RM": 13.4,
            "Q": 0.0,
            "Ep": 0.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 0.0,
            "UpStrmQ": 0.0,
            "SubRIn": 60.01,
            "latqcc": 177.11,
            "Total-Soil Water": 100.0,
            "SoilWaterTotal": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 0.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
        },
    ]


def _mofe_mixed_late_window_wat_rows(wepp_id: int) -> list[dict[str, object]]:
    return [
        {
            "wepp_id": wepp_id,
            "ofe_id": 1,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 120,
            "month": 4,
            "day_of_month": 30,
            "water_year": 1987,
            "OFE": 1,
            "P": 10.0,
            "RM": 10.0,
            "Q": 0.0,
            "Ep": 0.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 0.0,
            "UpStrmQ": 0.0,
            "SubRIn": 10.0,
            "latqcc": 100.0,
            "Total-Soil Water": 100.0,
            "SoilWaterTotal": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 0.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
        },
        {
            "wepp_id": wepp_id,
            "ofe_id": 2,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 120,
            "month": 4,
            "day_of_month": 30,
            "water_year": 1987,
            "OFE": 2,
            "P": 10.0,
            "RM": 10.0,
            "Q": 10.0,
            "Ep": 0.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 0.0,
            "UpStrmQ": 0.0,
            "SubRIn": 10.0,
            "latqcc": 70.0,
            "Total-Soil Water": 100.0,
            "SoilWaterTotal": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 10.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
        },
        {
            "wepp_id": wepp_id,
            "ofe_id": 3,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 120,
            "month": 4,
            "day_of_month": 30,
            "water_year": 1987,
            "OFE": 3,
            "P": 10.0,
            "RM": 10.0,
            "Q": 20.0,
            "Ep": 0.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 0.0,
            "UpStrmQ": 0.0,
            "SubRIn": 10.0,
            "latqcc": 140.0,
            "Total-Soil Water": 100.0,
            "SoilWaterTotal": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 20.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
        },
    ]


def _mofe_ratio_unsupported_high_residual_rows(wepp_id: int) -> list[dict[str, object]]:
    return [
        {
            "wepp_id": wepp_id,
            "ofe_id": 1,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 45,
            "month": 2,
            "day_of_month": 14,
            "water_year": 1987,
            "OFE": 1,
            "P": 5.0,
            "RM": 5.0,
            "Q": 0.0,
            "Ep": 0.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 0.0,
            "UpStrmQ": 0.0,
            "SubRIn": 0.0,
            "latqcc": 0.0,
            "Total-Soil Water": 100.0,
            "SoilWaterTotal": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 5.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
        },
        {
            "wepp_id": wepp_id,
            "ofe_id": 2,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 45,
            "month": 2,
            "day_of_month": 14,
            "water_year": 1987,
            "OFE": 2,
            "P": 5.0,
            "RM": 5.0,
            "Q": 0.0,
            "Ep": 0.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 0.0,
            "UpStrmQ": 0.0,
            "SubRIn": 0.0,
            "latqcc": 0.0,
            "Total-Soil Water": 100.0,
            "SoilWaterTotal": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 5.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
        },
        {
            "wepp_id": wepp_id,
            "ofe_id": 3,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 45,
            "month": 2,
            "day_of_month": 14,
            "water_year": 1987,
            "OFE": 3,
            "P": 10.0,
            "RM": 10.0,
            "Q": 0.0,
            "Ep": 0.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 0.0,
            "UpStrmQ": 0.0,
            "SubRIn": 0.0,
            "latqcc": 0.0,
            "Total-Soil Water": 100.0,
            "SoilWaterTotal": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 220.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
        },
    ]


def test_full_physical_closure_uses_p_plus_irr_and_interception_storage(tmp_path: Path) -> None:
    module = _module()
    load_ofe_rows = module["_load_wat_ofe_rows_for_wepp"]
    compute_full = module["_compute_daily_full_physical_closure"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    _write_interchange(
        interchange_dir,
        wat_records=[
            {
                "wepp_id": 501,
                "ofe_id": 1,
                "year": 1987,
                "sim_day_index": 1,
                "julian": 44,
                "month": 2,
                "day_of_month": 13,
                "water_year": 1987,
                "OFE": 1,
                "P": 0.0,
                "RM": 0.0,
                "Q": 0.0,
                "Ep": 1.0,
                "Es": 0.0,
                "Er": 0.0,
                "Dp": 0.0,
                "UpStrmQ": 0.0,
                "SubRIn": 0.0,
                "latqcc": 0.0,
                "Total-Soil Water": 100.0,
                "SoilWaterTotal": 100.0,
                "frozwt": 0.0,
                "Snow-Water": 5.0,
                "QOFE": 0.0,
                "Tile": 0.0,
                "Irr": 0.0,
                "Area": 100.0,
                "InterceptionStorage": 0.0,
            },
            {
                "wepp_id": 501,
                "ofe_id": 1,
                "year": 1987,
                "sim_day_index": 2,
                "julian": 45,
                "month": 2,
                "day_of_month": 14,
                "water_year": 1987,
                "OFE": 1,
                "P": 10.0,
                "RM": 15.0,
                "Q": 1.0,
                "Ep": 1.0,
                "Es": 1.0,
                "Er": 0.0,
                "Dp": 1.0,
                "UpStrmQ": 0.0,
                "SubRIn": 0.0,
                "latqcc": 0.0,
                "Total-Soil Water": 100.0,
                "SoilWaterTotal": 100.0,
                "frozwt": 0.0,
                "Snow-Water": 0.0,
                "QOFE": 1.0,
                "Tile": 0.0,
                "Irr": 0.0,
                "Area": 100.0,
                "InterceptionStorage": 11.0,
            },
        ],
        pass_records=_mofe_pass_rows(501),
    )

    ofe_rows = load_ofe_rows(interchange_dir, 501)
    daily_full, full_meta = compute_full(ofe_rows)

    assert full_meta["storage_basis"] == "SoilWaterTotal_plus_SnowWater_plus_InterceptionStorage"
    assert full_meta["uses_interception_storage"] is True

    day2 = daily_full[daily_full["sim_day_index"] == 2].iloc[0]
    assert day2["audit_full_physical_closure_residual_mm"] == pytest.approx(0.0, abs=1.0e-8)
    assert day2["audit_full_external_input_mm"] == pytest.approx(10.0, abs=1.0e-8)
    assert day2["audit_full_rm_mm"] == pytest.approx(15.0, abs=1.0e-8)


def test_chain_transfer_residuals_and_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _module()
    main = module["main"]
    load_ofe_rows = module["_load_wat_ofe_rows_for_wepp"]
    compute_chain = module["compute_mofe_chain_audit"]
    compute_full = module["_compute_daily_full_physical_closure"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    _write_interchange(
        interchange_dir,
        wat_records=_mofe_wat_rows(71),
        pass_records=_mofe_pass_rows(71),
    )

    ofe_rows = load_ofe_rows(interchange_dir, 71)
    chain_df, first_df = compute_chain(ofe_rows)

    assert chain_df.shape[0] == 4
    day1_12 = chain_df[
        (chain_df["sim_day_index"] == 1) & (chain_df["ofe_up"] == 1) & (chain_df["ofe_down"] == 2)
    ].iloc[0]
    assert day1_12["audit_chain_subsurface_transfer_residual_m3"] == pytest.approx(0.0, abs=1.0e-8)
    assert day1_12["audit_chain_surface_transfer_residual_m3_geometry_sensitive"] == pytest.approx(0.0, abs=1.0e-8)

    day2_12 = chain_df[
        (chain_df["sim_day_index"] == 2) & (chain_df["ofe_up"] == 1) & (chain_df["ofe_down"] == 2)
    ].iloc[0]
    assert day2_12["audit_chain_subsurface_transfer_residual_m3"] == pytest.approx(0.07)
    assert day2_12["audit_chain_surface_transfer_residual_m3_geometry_sensitive"] == pytest.approx(0.04)

    assert first_df["audit_first_ofe_upstrmq_mm"].max() == pytest.approx(0.0)
    assert first_df["audit_first_ofe_subrin_mm"].max() == pytest.approx(0.0)

    daily_full, full_meta = compute_full(ofe_rows)
    assert full_meta["storage_basis"] == "SoilWaterTotal_plus_SnowWater"
    assert daily_full.loc[daily_full["sim_day_index"] == 1, "audit_full_physical_closure_residual_mm"].iloc[0] == pytest.approx(
        0.0, abs=1.0e-7
    )
    assert daily_full.loc[daily_full["sim_day_index"] == 2, "audit_full_physical_closure_residual_mm"].iloc[0] == pytest.approx(
        2.1578947368,
        rel=1.0e-7,
    )

    out_dir = tmp_path / "audit_out"
    monkeypatch.setitem(main.__globals__, "base", module["base"])
    monkeypatch.setitem(module["base"].__dict__, "_resolve_topaz_from_wepp", lambda _path, _wepp: None)
    monkeypatch.setattr(
        "sys.argv",
        [
            "hillslope_mofe_daily_closure_audit.py",
            str(interchange_dir),
            "--wepp-id",
            "71",
            "--output-dir",
            str(out_dir),
            "--top-n",
            "3",
        ],
    )

    result = main()
    assert result == 0
    captured = capsys.readouterr().out
    assert "wepp_id=71" in captured
    assert "mofe_chain_rows=4" in captured
    assert "full_physical_storage_basis=SoilWaterTotal_plus_SnowWater" in captured

    summary_path = out_dir / "hillslope_mofe_daily_closure_audit_summary.json"
    top_path = out_dir / "hillslope_mofe_daily_closure_audit_top_days.csv"
    daily_path = out_dir / "hillslope_mofe_daily_closure_audit_daily.csv"
    assert summary_path.exists()
    assert top_path.exists()
    assert daily_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["rows"] == 2
    assert summary["mofe_chain"]["rows"] == 4
    assert summary["mofe_chain"]["first_ofe_nonzero_upstrmq_days"] == 0
    assert summary["mofe_chain"]["first_ofe_nonzero_subrin_days"] == 0
    assert summary["mofe_chain"]["subsurface_transfer_residual_m3"]["max_abs"] == pytest.approx(0.12)
    assert summary["mofe_chain"]["strict_chain_invariants_applicability"] == "unknown_from_interchange"

    full = summary["full_physical_closure"]
    assert full["storage_basis"] == "SoilWaterTotal_plus_SnowWater"
    assert full["uses_soilwatertotal"] is True
    assert full["requires_scientific_review"] is False
    assert full["requires_scientific_review_days"] == 0
    assert full["closure_residual_mm"]["max_abs"] == pytest.approx(2.1578947368, rel=1.0e-7)
    assert full["closure_residual_total_mm"] == pytest.approx(2.1578947368, rel=1.0e-7)
    assert full["max_abs_day"]["julian"] == 45

    top = pd.read_csv(top_path)
    assert top.shape[0] == 2
    assert {
        "ofe_up",
        "ofe_down",
        "abs_full_physical_closure_residual_mm",
        "audit_full_outlier_ofe_id",
        "audit_full_outlier_ofe_closure_residual_mm",
    }.issubset(top.columns)
    assert int(top.iloc[0]["julian"]) == 45

    daily = pd.read_csv(daily_path)
    assert daily.shape[0] == 2
    assert {
        "wepp_id",
        "topaz_id",
        "audit_requires_scientific_review",
        "audit_late_max_surface_pulse_proxy_mm",
    }.issubset(daily.columns)
    assert set(daily["wepp_id"].astype(int)) == {71}


def test_main_topaz_selector_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    main = module["main"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    _write_interchange(
        interchange_dir,
        wat_records=_mofe_wat_rows(33),
        pass_records=_mofe_pass_rows(33),
    )

    monkeypatch.setitem(main.__globals__, "base", module["base"])
    monkeypatch.setitem(module["base"].__dict__, "_resolve_wepp_from_topaz", lambda _path, _top: 33)
    monkeypatch.setitem(module["base"].__dict__, "_resolve_topaz_from_wepp", lambda _path, _wepp: 777)

    out_dir = tmp_path / "audit_out_topaz"
    monkeypatch.setattr(
        "sys.argv",
        [
            "hillslope_mofe_daily_closure_audit.py",
            str(interchange_dir),
            "--topaz-id",
            "777",
            "--output-dir",
            str(out_dir),
            "--top-n",
            "2",
        ],
    )

    result = main()
    assert result == 0

    summary = json.loads((out_dir / "hillslope_mofe_daily_closure_audit_summary.json").read_text(encoding="utf-8"))
    assert summary["wepp_id"] == 33
    assert summary["topaz_id"] == 777


def test_main_wepp_selector_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    main = module["main"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    _write_interchange(
        interchange_dir,
        wat_records=_mofe_wat_rows(44),
        pass_records=_mofe_pass_rows(44),
    )

    monkeypatch.setitem(main.__globals__, "base", module["base"])
    monkeypatch.setitem(module["base"].__dict__, "_resolve_topaz_from_wepp", lambda _path, _wepp: 888)

    out_dir = tmp_path / "audit_out_wepp"
    monkeypatch.setattr(
        "sys.argv",
        [
            "hillslope_mofe_daily_closure_audit.py",
            str(interchange_dir),
            "--wepp-id",
            "44",
            "--output-dir",
            str(out_dir),
            "--top-n",
            "1",
        ],
    )

    result = main()
    assert result == 0
    summary = json.loads((out_dir / "hillslope_mofe_daily_closure_audit_summary.json").read_text(encoding="utf-8"))
    assert summary["wepp_id"] == 44
    assert summary["topaz_id"] == 888


def test_parse_args_rejects_invalid_selector_combinations(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    parse_args = module["parse_args"]

    monkeypatch.setattr(
        "sys.argv",
        [
            "hillslope_mofe_daily_closure_audit.py",
            "/tmp/interchange",
            "--wepp-id",
            "1",
            "--topaz-id",
            "2",
        ],
    )
    with pytest.raises(SystemExit):
        parse_args()


def test_scientific_review_diagnostic_flags_terminal_amplification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    main = module["main"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    _write_interchange(
        interchange_dir,
        wat_records=_mofe_scireview_wat_rows(88),
        pass_records=_mofe_pass_rows(88),
    )

    monkeypatch.setitem(main.__globals__, "base", module["base"])
    monkeypatch.setitem(module["base"].__dict__, "_resolve_topaz_from_wepp", lambda _path, _wepp: None)

    out_dir = tmp_path / "audit_out_scireview"
    monkeypatch.setattr(
        "sys.argv",
        [
            "hillslope_mofe_daily_closure_audit.py",
            str(interchange_dir),
            "--wepp-id",
            "88",
            "--output-dir",
            str(out_dir),
            "--top-n",
            "2",
        ],
    )

    result = main()
    assert result == 0

    summary = json.loads((out_dir / "hillslope_mofe_daily_closure_audit_summary.json").read_text(encoding="utf-8"))
    full = summary["full_physical_closure"]
    assert full["requires_scientific_review"] is True
    assert full["requires_scientific_review_days"] == 1
    assert full["max_requires_scientific_review_day"]["julian"] == 45
    assert full["max_requires_scientific_review_day"]["late_outlier_ofe_id"] == 3
    assert full["max_requires_scientific_review_day"]["late_max_qofe_to_q_ratio"] > 2.0
    assert full["max_requires_scientific_review_day"]["late_max_surface_pulse_proxy_mm"] > 100.0

    top = pd.read_csv(out_dir / "hillslope_mofe_daily_closure_audit_top_days.csv")
    day45 = top[top["julian"] == 45].iloc[0]
    assert str(day45["audit_requires_scientific_review"]).lower() in {"true", "1"}
    assert (
        day45["audit_requires_scientific_review_reason"]
        == "late_ofe_residual_plus_qofe_to_q_ratio_plus_surface_pulse_proxy"
    )


def test_pure_subsurface_day_masks_surface_proxy_and_does_not_flag(tmp_path: Path) -> None:
    module = _module()
    load_ofe_rows = module["_load_wat_ofe_rows_for_wepp"]
    compute_full = module["_compute_daily_full_physical_closure"]
    compute_surface_pulse_proxy = module["_compute_surface_pulse_proxy_mm_ofe"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    _write_interchange(
        interchange_dir,
        wat_records=_mofe_pure_subsurface_wat_rows(136),
        pass_records=_mofe_pass_rows(136),
    )

    ofe_rows = load_ofe_rows(interchange_dir, 136)
    surface_proxy = compute_surface_pulse_proxy(
        qofe=ofe_rows["QOFE"].to_numpy(dtype=np.float64, copy=False),
        upstrmq=ofe_rows["UpStrmQ"].to_numpy(dtype=np.float64, copy=False),
        precip=ofe_rows["P"].to_numpy(dtype=np.float64, copy=False),
        irr=ofe_rows["Irr"].to_numpy(dtype=np.float64, copy=False),
        subrin=ofe_rows["SubRIn"].to_numpy(dtype=np.float64, copy=False),
        latqcc=ofe_rows["latqcc"].to_numpy(dtype=np.float64, copy=False),
    )
    daily_full, _meta = compute_full(ofe_rows)

    assert np.isnan(surface_proxy).all()

    day = daily_full.iloc[0]
    assert np.isnan(day["audit_late_max_surface_pulse_proxy_mm"])
    assert bool(day["audit_requires_scientific_review"]) is False
    assert day["audit_requires_scientific_review_reason"] == "none"


def test_mixed_late_window_uses_nanmax_for_surface_pulse_proxy(tmp_path: Path) -> None:
    module = _module()
    load_ofe_rows = module["_load_wat_ofe_rows_for_wepp"]
    compute_full = module["_compute_daily_full_physical_closure"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    _write_interchange(
        interchange_dir,
        wat_records=_mofe_mixed_late_window_wat_rows(777),
        pass_records=_mofe_pass_rows(777),
    )

    ofe_rows = load_ofe_rows(interchange_dir, 777)
    daily_full, _meta = compute_full(ofe_rows)

    day = daily_full.iloc[0]
    assert day["audit_late_max_surface_pulse_proxy_mm"] == pytest.approx(140.0, abs=1.0e-8)
    assert bool(day["audit_requires_scientific_review"]) is False


def test_scireview_requires_all_three_signals_supported(tmp_path: Path) -> None:
    module = _module()
    load_ofe_rows = module["_load_wat_ofe_rows_for_wepp"]
    compute_full = module["_compute_daily_full_physical_closure"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    _write_interchange(
        interchange_dir,
        wat_records=_mofe_ratio_unsupported_high_residual_rows(901),
        pass_records=_mofe_pass_rows(901),
    )

    ofe_rows = load_ofe_rows(interchange_dir, 901)
    daily_full, _meta = compute_full(ofe_rows)

    day = daily_full.iloc[0]
    assert day["audit_late_max_abs_ofe_closure_residual_mm"] >= 100.0
    assert day["audit_late_max_surface_pulse_proxy_mm"] >= 100.0
    assert np.isnan(day["audit_late_max_qofe_to_q_ratio"])
    assert bool(day["audit_requires_scientific_review"]) is False
    assert day["audit_requires_scientific_review_reason"] == "none"
