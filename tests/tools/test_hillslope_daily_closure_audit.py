from __future__ import annotations

import json
from pathlib import Path
import runpy

import duckdb
import pandas as pd
import pytest

pytestmark = pytest.mark.unit


def _module() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    return runpy.run_path(str(repo_root / "tools/hillslope_daily_closure_audit.py"))


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


def test_single_ofe_closure_and_optional_terms(tmp_path: Path) -> None:
    module = _module()
    load_dataset = module["load_dataset"]
    compute_daily_audit = module["compute_daily_audit"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    wat_records = [
        {
            "wepp_id": 11,
            "ofe_id": 1,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "OFE": 1,
            "P": 10.0,
            "RM": 10.0,
            "Q": 0.0,
            "Ep": 1.0,
            "Es": 1.0,
            "Er": 1.0,
            "Dp": 1.0,
            "UpStrmQ": 0.0,
            "SubRIn": 0.0,
            "latqcc": 0.0,
            "Total-Soil Water": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 100.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
            "SoilWaterTotal": 100.0,
            "ProfileDepth": 1000.0,
            "ProfilePorosityCap": 500.0,
            "ProfileFCStore": 300.0,
            "ProfileWPStore": 120.0,
        },
        {
            "wepp_id": 11,
            "ofe_id": 1,
            "year": 1987,
            "sim_day_index": 2,
            "julian": 45,
            "month": 2,
            "day_of_month": 14,
            "water_year": 1987,
            "OFE": 1,
            "P": 5.0,
            "RM": 5.0,
            "Q": 0.0,
            "Ep": 1.0,
            "Es": 1.0,
            "Er": 0.0,
            "Dp": 1.0,
            "UpStrmQ": 0.0,
            "SubRIn": 0.0,
            "latqcc": 1.0,
            "Total-Soil Water": 99.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 80.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
            "SoilWaterTotal": 98.0,
            "ProfileDepth": 1000.0,
            "ProfilePorosityCap": 500.0,
            "ProfileFCStore": 300.0,
            "ProfileWPStore": 120.0,
        },
    ]
    pass_records = [
        {
            "wepp_id": 11,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "runvol": 2.0,
            "sbrunv": 0.3,
        },
        {
            "wepp_id": 11,
            "year": 1987,
            "sim_day_index": 2,
            "julian": 45,
            "month": 2,
            "day_of_month": 14,
            "water_year": 1987,
            "runvol": 0.2,
            "sbrunv": 0.1,
        },
    ]
    soil_records = [
        {
            "wepp_id": 11,
            "ofe_id": 1,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "OFE": 1,
            "TSMF": 0.5,
        },
        {
            "wepp_id": 11,
            "ofe_id": 1,
            "year": 1987,
            "sim_day_index": 2,
            "julian": 45,
            "month": 2,
            "day_of_month": 14,
            "water_year": 1987,
            "OFE": 1,
            "TSMF": 0.4,
        },
    ]
    element_records = [
        {
            "wepp_id": 11,
            "ofe_id": 1,
            "year": 1987,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "OFE": 1,
            "QRain": 10.0,
            "QSnow": 0.0,
        },
        {
            "wepp_id": 11,
            "ofe_id": 1,
            "year": 1987,
            "julian": 45,
            "month": 2,
            "day_of_month": 14,
            "water_year": 1987,
            "OFE": 1,
            "QRain": 2.0,
            "QSnow": 0.0,
        },
    ]

    _write_interchange(
        interchange_dir,
        wat_records=wat_records,
        pass_records=pass_records,
        soil_records=soil_records,
        element_records=element_records,
    )

    dataset = load_dataset(interchange_dir, 11)
    assert list(dataset["n_ofe"]) == [1, 1]
    assert dataset.loc[0, "TSMF"] == pytest.approx(0.5)
    assert dataset.loc[1, "TSMF"] == pytest.approx(0.4)
    assert dataset.loc[0, "QRain"] == pytest.approx(10.0)
    assert dataset.loc[1, "QRain"] == pytest.approx(2.0)

    audit = compute_daily_audit(dataset)
    # Day 2: 5 - (2 + 1 + 2 + 1) - (-1) = 0
    assert audit.loc[1, "audit_closure_reconstructed_with_storage_mm"] == pytest.approx(0.0)
    # Enriched storage uses SoilWaterTotal (day2 delta = -2), so closure shifts by +1 mm.
    assert audit.loc[1, "audit_closure_reconstructed_with_enriched_storage_mm"] == pytest.approx(1.0)
    assert audit.loc[1, "audit_sbrunv_calc_mm"] == pytest.approx(1.0)


def test_mofe_uses_outlet_lateral_and_pass_runvol(tmp_path: Path) -> None:
    module = _module()
    load_dataset = module["load_dataset"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    wat_records = [
        {
            "wepp_id": 22,
            "ofe_id": 1,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "OFE": 1,
            "P": 10.0,
            "RM": 10.0,
            "Q": 0.0,
            "Ep": 1.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 1.0,
            "UpStrmQ": 0.0,
            "SubRIn": 0.0,
            "latqcc": 20.0,
            "Total-Soil Water": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 100.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 50.0,
        },
        {
            "wepp_id": 22,
            "ofe_id": 2,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "OFE": 2,
            "P": 10.0,
            "RM": 10.0,
            "Q": 0.0,
            "Ep": 1.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 1.0,
            "UpStrmQ": 0.0,
            "SubRIn": 0.0,
            "latqcc": 30.0,
            "Total-Soil Water": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 100.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 50.0,
        },
    ]
    pass_records = [
        {
            "wepp_id": 22,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "runvol": 0.1,
            "sbrunv": 0.0,
        }
    ]

    _write_interchange(interchange_dir, wat_records=wat_records, pass_records=pass_records)

    dataset = load_dataset(interchange_dir, 22)
    assert list(dataset["n_ofe"]) == [2]

    # Lateral flow should use only outlet OFE (ofe_id=2): 30 mm over 50 m2 => 1.5 m3 / 100 m2 => 15 mm.
    assert dataset.loc[0, "Lateral Flow"] == pytest.approx(15.0)
    # Runoff should come from H.pass.runvol (0.1 m3 / 100 m2 => 1 mm), not summed QOFE.
    assert dataset.loc[0, "Runoff"] == pytest.approx(1.0)


def test_main_topaz_selector_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    main = module["main"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    wat_records = [
        {
            "wepp_id": 33,
            "ofe_id": 1,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "OFE": 1,
            "P": 1.0,
            "RM": 1.0,
            "Q": 0.0,
            "Ep": 0.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 0.0,
            "UpStrmQ": 0.0,
            "SubRIn": 0.0,
            "latqcc": 0.0,
            "Total-Soil Water": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 0.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
        }
    ]
    pass_records = [
        {
            "wepp_id": 33,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "runvol": 0.0,
            "sbrunv": 0.0,
        }
    ]
    _write_interchange(interchange_dir, wat_records=wat_records, pass_records=pass_records)

    monkeypatch.setitem(main.__globals__, "_resolve_wepp_from_topaz", lambda _path, _top: 33)
    monkeypatch.setitem(main.__globals__, "_resolve_topaz_from_wepp", lambda _path, _wepp: 777)

    out_dir = tmp_path / "audit_out"
    monkeypatch.setattr(
        "sys.argv",
        [
            "hillslope_daily_closure_audit.py",
            str(interchange_dir),
            "--topaz-id",
            "777",
            "--output-dir",
            str(out_dir),
            "--top-n",
            "1",
        ],
    )

    result = main()
    assert result == 0

    summary_path = out_dir / "hillslope_daily_closure_audit_summary.json"
    top_days_path = out_dir / "hillslope_daily_closure_audit_top_days.csv"
    assert summary_path.exists()
    assert top_days_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["wepp_id"] == 33
    assert summary["topaz_id"] == 777
    assert summary["rows"] == 1


def test_main_wepp_selector_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    main = module["main"]

    interchange_dir = tmp_path / "run" / "wepp" / "output" / "interchange"
    wat_records = [
        {
            "wepp_id": 44,
            "ofe_id": 1,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "OFE": 1,
            "P": 1.0,
            "RM": 1.0,
            "Q": 0.0,
            "Ep": 0.0,
            "Es": 0.0,
            "Er": 0.0,
            "Dp": 0.0,
            "UpStrmQ": 0.0,
            "SubRIn": 0.0,
            "latqcc": 0.0,
            "Total-Soil Water": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "QOFE": 0.0,
            "Tile": 0.0,
            "Irr": 0.0,
            "Area": 100.0,
        }
    ]
    pass_records = [
        {
            "wepp_id": 44,
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "runvol": 0.0,
            "sbrunv": 0.0,
        }
    ]
    _write_interchange(interchange_dir, wat_records=wat_records, pass_records=pass_records)

    monkeypatch.setitem(main.__globals__, "_resolve_topaz_from_wepp", lambda _path, _wepp: 888)

    out_dir = tmp_path / "audit_out_wepp"
    monkeypatch.setattr(
        "sys.argv",
        [
            "hillslope_daily_closure_audit.py",
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
    summary = json.loads((out_dir / "hillslope_daily_closure_audit_summary.json").read_text(encoding="utf-8"))
    assert summary["wepp_id"] == 44
    assert summary["topaz_id"] == 888


def test_parse_args_rejects_invalid_selector_combinations(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    parse_args = module["parse_args"]

    monkeypatch.setattr(
        "sys.argv",
        [
            "hillslope_daily_closure_audit.py",
            "/tmp/interchange",
            "--wepp-id",
            "1",
            "--topaz-id",
            "2",
        ],
    )
    with pytest.raises(SystemExit):
        parse_args()
