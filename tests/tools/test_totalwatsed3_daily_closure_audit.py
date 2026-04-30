from __future__ import annotations

import json
from pathlib import Path
import runpy

import pandas as pd
import pytest

pytestmark = pytest.mark.unit


def _module() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    return runpy.run_path(str(repo_root / "tools/totalwatsed3_daily_closure_audit.py"))


def _write_totalwatsed3(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Day 2 is constructed so reconstructed closure with storage is exactly 0.
    records = [
        {
            "year": 1987,
            "sim_day_index": 1,
            "julian": 44,
            "month": 2,
            "day_of_month": 13,
            "water_year": 1987,
            "Area": 100.0,
            "P": 0.5,
            "RM": 0.5,
            "runvol": 0.3,
            "latqcc": 0.1,
            "Dp": 0.05,
            "Ep": 0.05,
            "Es": 0.03,
            "Er": 0.02,
            "Total-Soil Water": 100.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "SoilWaterTotal": 100.0,
            "ProfileDepth": 1000.0,
            "ProfilePorosityCap": 500.0,
            "ProfileFCStore": 300.0,
            "ProfileWPStore": 120.0,
            "Precipitation": 5.0,
            "Rain+Melt": 5.0,
            "Runoff": 20.0,
            "Lateral Flow": 1.0,
            "Percolation": 0.5,
            "ET": 1.0,
        },
        {
            "year": 1987,
            "sim_day_index": 2,
            "julian": 45,
            "month": 2,
            "day_of_month": 14,
            "water_year": 1987,
            "Area": 100.0,
            "P": 0.5,
            "RM": 0.5,
            "runvol": 0.4,
            "latqcc": 0.2,
            "Dp": 0.1,
            "Ep": 0.1,
            "Es": 0.1,
            "Er": 0.1,
            "Total-Soil Water": 95.0,
            "frozwt": 0.0,
            "Snow-Water": 0.0,
            "SoilWaterTotal": 94.0,
            "ProfileDepth": 1000.0,
            "ProfilePorosityCap": 500.0,
            "ProfileFCStore": 300.0,
            "ProfileWPStore": 120.0,
            "Precipitation": 5.0,
            "Rain+Melt": 5.0,
            "Runoff": 40.0,
            "Lateral Flow": 2.0,
            "Percolation": 1.0,
            "ET": 3.0,
        },
    ]
    pd.DataFrame.from_records(records).to_parquet(path, index=False)


def test_compute_daily_audit_detects_runoff_consistency_and_closure(tmp_path: Path) -> None:
    module = _module()
    compute_daily_audit = module["compute_daily_audit"]
    load_dataset = module["load_dataset"]
    build_summary = module["build_summary"]

    dataset = tmp_path / "totalwatsed3.parquet"
    _write_totalwatsed3(dataset)

    audit = compute_daily_audit(load_dataset(dataset))
    summary = build_summary(audit, dataset)

    # Day 1 runoff mismatch: reported 20 mm vs reconstructed 3 mm.
    assert audit.loc[0, "audit_runoff_consistency_mm"] == pytest.approx(17.0)
    # Day 2 runoff mismatch: reported 40 mm vs reconstructed 4 mm.
    assert audit.loc[1, "audit_runoff_consistency_mm"] == pytest.approx(36.0)

    # Day 2 reconstructed closure with storage: 5 - (4+2+3+1) - (-5) = 0.
    assert audit.loc[1, "audit_closure_reconstructed_with_storage_mm"] == pytest.approx(0.0)
    # Enriched storage uses producer-authoritative SoilWaterTotal, so day 2 delta is -6.
    assert audit.loc[1, "audit_closure_reconstructed_with_enriched_storage_mm"] == pytest.approx(1.0)
    # Reported closure remains strongly negative due inflated reported runoff.
    assert audit.loc[1, "audit_closure_reported_with_storage_mm"] == pytest.approx(-36.0)

    assert summary["rows"] == 2
    assert summary["max_reported_runoff_mm"] == pytest.approx(40.0)
    assert summary["max_reconstructed_runoff_mm"] == pytest.approx(4.0)
    assert summary["max_runoff_to_precip_reconstructed_pct"] == pytest.approx(80.0)
    whole = summary["whole_run_closure"]
    assert whole["rain_melt_total_mm"] == pytest.approx(10.0)
    assert whole["runoff_reported_total_mm"] == pytest.approx(60.0)
    assert whole["runoff_reconstructed_total_mm"] == pytest.approx(7.0)
    assert whole["storage_change_mm"] == pytest.approx(-5.0)
    assert whole["closure_reported_with_storage_total_mm"] == pytest.approx(-53.5)
    assert whole["closure_reconstructed_with_storage_total_mm"] == pytest.approx(-0.5)
    assert whole["closure_reconstructed_with_storage_pct_of_rain_melt"] == pytest.approx(-5.0)
    assert whole["enriched_storage_available"] is True
    assert whole["enriched_storage_change_mm"] == pytest.approx(-6.0)
    assert whole["closure_reconstructed_with_enriched_storage_total_mm"] == pytest.approx(0.5)
    assert whole["closure_reconstructed_with_enriched_storage_pct_of_rain_melt"] == pytest.approx(5.0)
    assert summary["closure_reconstructed_with_enriched_storage_mm"]["max_abs"] == pytest.approx(1.0)


def test_main_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    main = module["main"]

    dataset = tmp_path / "totalwatsed3.parquet"
    _write_totalwatsed3(dataset)

    out_dir = tmp_path / "audit_out"
    monkeypatch.setattr(
        "sys.argv",
        [
            "totalwatsed3_daily_closure_audit.py",
            str(dataset),
            "--output-dir",
            str(out_dir),
            "--top-n",
            "1",
        ],
    )

    result = main()
    assert result == 0
    summary_path = out_dir / "daily_closure_audit_summary.json"
    assert summary_path.exists()
    assert (out_dir / "daily_closure_audit_top_days.csv").exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert "whole_run_closure" in summary
