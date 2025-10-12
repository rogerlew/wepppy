from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from wepppy.wepp.reports.sediment_characteristics import SedimentCharacteristics


def _configure_sediment_stubs(monkeypatch, tmp_path: Path):
    dataset_paths = {
        "wepp/output/interchange/loss_pw0.class_data.parquet",
        "wepp/output/interchange/loss_pw0.out.parquet",
        "wepp/output/interchange/loss_pw0.hill.parquet",
        "wepp/output/interchange/loss_pw0.all_years.hill.parquet",
        "wepp/output/interchange/H.pass.parquet",
    }

    class_records = [
        {
            "class": 1,
            "diameter_mm": 0.01,
            "specific_gravity": 2.65,
            "pct_sand": 30.0,
            "pct_silt": 40.0,
            "pct_clay": 25.0,
            "pct_om": 5.0,
            "fraction": 0.20,
        },
        {
            "class": 2,
            "diameter_mm": 0.05,
            "specific_gravity": 2.50,
            "pct_sand": 50.0,
            "pct_silt": 30.0,
            "pct_clay": 15.0,
            "pct_om": 5.0,
            "fraction": 0.30,
        },
        {
            "class": 3,
            "diameter_mm": 0.10,
            "specific_gravity": 2.45,
            "pct_sand": 40.0,
            "pct_silt": 35.0,
            "pct_clay": 20.0,
            "pct_om": 5.0,
            "fraction": 0.20,
        },
        {
            "class": 4,
            "diameter_mm": 0.20,
            "specific_gravity": 2.40,
            "pct_sand": 35.0,
            "pct_silt": 45.0,
            "pct_clay": 15.0,
            "pct_om": 5.0,
            "fraction": 0.20,
        },
        {
            "class": 5,
            "diameter_mm": 0.50,
            "specific_gravity": 2.35,
            "pct_sand": 25.0,
            "pct_silt": 50.0,
            "pct_clay": 20.0,
            "pct_om": 5.0,
            "fraction": 0.10,
        },
    ]

    out_value_map = {
        "Avg. Ann. sediment discharge from outlet": 120.0,
        "Index of specific surface": 1.8,
        "Enrichment ratio of specific surface": 2.2,
    }

    class StubQueryContext:
        def __init__(self, run_directory, *, run_interchange=False, auto_activate=True):
            assert Path(run_directory) == tmp_path
            self.catalog = SimpleNamespace(has=lambda path: path in dataset_paths)

        def ensure_datasets(self, *paths: str) -> None:
            missing = [path for path in paths if not self.catalog.has(path)]
            if missing:
                raise FileNotFoundError(', '.join(sorted(missing)))

        def query(self, payload):
            dataset = payload.datasets[0]["path"]
            if dataset == "wepp/output/interchange/loss_pw0.class_data.parquet":
                return SimpleNamespace(records=class_records, schema=None, row_count=len(class_records))
            if dataset == "wepp/output/interchange/loss_pw0.all_years.hill.parquet":
                return SimpleNamespace(records=[{"year_count": 5}], schema=None, row_count=1)
            if dataset == "wepp/output/interchange/H.pass.parquet":
                return SimpleNamespace(
                    records=[
                        {
                            "mass_c1": 6000.0,
                            "mass_c2": 14000.0,
                            "mass_c3": 0.0,
                            "mass_c4": 0.0,
                            "mass_c5": 0.0,
                        }
                    ],
                    schema=None,
                    row_count=1,
                )
            if dataset == "wepp/output/interchange/loss_pw0.out.parquet":
                key = payload.filters[0]["value"] if payload.filters else None
                value = out_value_map.get(key, 0.0)
                if payload.columns == ["out.key", "out.value"]:
                    return SimpleNamespace(records=[{"key": key, "value": value}], schema=None, row_count=1)
                return SimpleNamespace(records=[{"value": value}], schema=None, row_count=1)
            raise AssertionError(f"Unexpected dataset requested: {dataset}")

    monkeypatch.setattr(
        "wepppy.wepp.reports.sediment_characteristics.ReportQueryContext",
        StubQueryContext,
    )


def test_sediment_characteristics_builds_reports(monkeypatch, tmp_path):
    _configure_sediment_stubs(monkeypatch, tmp_path)

    report = SedimentCharacteristics(tmp_path)

    class_df = pd.DataFrame([dict(row.row) for row in report.class_info_report])
    assert list(class_df["Class"]) == [1, 2, 3, 4, 5]
    assert "Sand (%)" in class_df.columns

    # Channel distribution
    channel_total = report.channel.total_discharge_tonne
    assert channel_total == 120.0

    channel_rows = list(report.channel.class_fraction_report)
    first_row = dict(channel_rows[0].row)
    assert abs(first_row["Fraction (ratio)"] - 0.2) < 1e-6
    assert abs(first_row["Sediment Discharge (tonne/yr)"] - 24.0) < 1e-6

    # Hillslope distribution (mass totals: (6000+14000)/5 years = 4000 kg/yr = 4 tonne/yr)
    hill_total = report.hillslope.total_delivery_tonne
    assert abs(hill_total - 4.0) < 1e-6

    hill_rows = list(report.hillslope.class_fraction_report)
    fractions = [dict(r.row)["Fraction (ratio)"] for r in hill_rows]
    assert abs(sum(fractions) - 1.0) < 1e-6
    assert abs(fractions[0] - 6000 / 20000) < 1e-6
    assert abs(dict(hill_rows[0].row)["Sediment Delivery (tonne/yr)"] - (6000 / 20000) * 4.0) < 1e-6

    assert report.specific_surface_index == 1.8
    assert report.enrichment_ratio_of_spec_surface == 2.2
