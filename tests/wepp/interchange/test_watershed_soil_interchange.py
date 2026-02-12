from __future__ import annotations

import shutil
from pathlib import Path
from typing import Set

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from .module_loader import PROJECT_OUTPUT, cleanup_import_state, load_module


load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")

_watershed_soil = load_module(
    "wepppy.wepp.interchange.watershed_soil_interchange",
    "wepppy/wepp/interchange/watershed_soil_interchange.py",
)
cleanup_import_state()

run_wepp_watershed_soil_interchange = _watershed_soil.run_wepp_watershed_soil_interchange
SOIL_PARQUET = _watershed_soil.SOIL_PARQUET
_write_soil_parquet = _watershed_soil._write_soil_parquet
_SCHEMA = _watershed_soil.SCHEMA
_MEASUREMENT_COLUMNS = _watershed_soil.MEASUREMENT_COLUMNS

PROFILE_DATA_ROOT = Path("/workdir/wepppy-test-engine-data/profiles")


def test_watershed_soil_interchange_writes_parquet(tmp_path: Path) -> None:
    src = PROJECT_OUTPUT
    if not any((src / name).exists() for name in ("soil_pw0.txt", "soil_pw0.txt.gz")):
        pytest.skip("soil_pw0 dataset not available in test fixture")
    workdir = tmp_path / "output"
    shutil.copytree(src, workdir)

    target = run_wepp_watershed_soil_interchange(workdir)
    assert target == workdir / "interchange" / SOIL_PARQUET
    assert target.exists()

    table = pq.read_table(target)
    schema = table.schema

    expected_columns = [
        "wepp_id",
        "ofe_id",
        "year",
        "day",
        "julian",
        "month",
        "day_of_month",
        "water_year",
        "OFE",
        "Poros",
        "Keff",
        "Suct",
        "FC",
        "WP",
        "Rough",
        "Ki",
        "Kr",
        "Tauc",
        "Saturation",
        "TSW",
        "TSMF",
    ]
    assert schema.names == expected_columns

    poros_field = schema.field(schema.get_field_index("Poros"))
    assert poros_field.metadata.get(b"units") == b"%"
    keff_field = schema.field(schema.get_field_index("Keff"))
    assert keff_field.metadata.get(b"units") == b"mm/hr"
    tsw_field = schema.field(schema.get_field_index("TSW"))
    assert tsw_field.metadata.get(b"units") == b"mm"
    tsmf_field = schema.field(schema.get_field_index("TSMF"))
    assert tsmf_field.metadata.get(b"units") == b"frac"

    df = table.to_pandas()
    assert not df.empty
    assert set(df["wepp_id"].unique()) == {1}
    assert (df["wepp_id"] == df["ofe_id"]).all()
    assert (df["wepp_id"] == df["OFE"]).all()
    assert (df["day"] == df["julian"]).all()
    first_row = df.iloc[0]
    assert 1 <= first_row["month"] <= 12
    assert 1 <= first_row["day_of_month"] <= 31


def test_watershed_soil_interchange_parses_tsmf_layout(tmp_path: Path) -> None:
    source = tmp_path / "soil_pw0.txt"
    target = tmp_path / "soil.parquet"
    source.write_text(
        "\n".join(
            [
                " Soil properties, daily output",
                "------------------------------------------------------------------------------------------------",
                " OFE Day   Y   Poros   Keff  Suct    FC     WP    Rough    Ki     Kr    Tauc    Saturation    TSW    TSMF",
                "                 %    mm/hr   mm    mm/mm  mm/mm    mm   adjsmt adjsmt adjsmt   frac          mm    frac",
                "------------------------------------------------------------------------------------------------",
                "",
                "  1    1   2001   66.01  40.00  17.65   0.20   0.05 100.00   0.04   0.13   2.00    0.46   30.56   0.6123",
                "  1    2   2001   66.01  39.50  17.10   0.20   0.05 100.00   0.04   0.13   2.00    0.45   29.95   0.6050",
            ]
        )
        + "\n"
    )

    _write_soil_parquet(source, target)
    table = pq.read_table(target)
    df = table.to_pandas()

    assert df["TSMF"].tolist() == pytest.approx([0.6123, 0.6050])


@pytest.mark.unit
def test_watershed_soil_interchange_falls_back_when_rust_schema_missing_tsmf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workdir = tmp_path / "output"
    workdir.mkdir()
    source = workdir / "soil_pw0.txt"
    source.write_text(
        "\n".join(
            [
                " Soil properties, daily output",
                "------------------------------------------------------------------------------------------------",
                " OFE Day   Y   Poros   Keff  Suct    FC     WP    Rough    Ki     Kr    Tauc    Saturation    TSW",
                "                 %    mm/hr   mm    mm/mm  mm/mm    mm   adjsmt adjsmt adjsmt   frac          mm",
                "------------------------------------------------------------------------------------------------",
                "",
                "  1    1   2001   66.01  40.00  17.65   0.20   0.05 100.00   0.04   0.13   2.00    0.46   30.56",
            ]
        )
        + "\n"
    )

    class _FakeRustSoil:
        def __init__(self) -> None:
            self.calls = 0

        def watershed_soil_to_parquet(
            self,
            source_path: str,
            target_path: str,
            major: int,
            minor: int,
            *,
            cli_calendar_path: str | None = None,
            chunk_rows: int = 250_000,
        ) -> None:
            self.calls += 1
            # Deliberately old schema: no TSMF column.
            table = pa.table(
                {
                    "wepp_id": [1],
                    "ofe_id": [1],
                    "year": [2001],
                    "day": [1],
                    "julian": [1],
                    "month": [1],
                    "day_of_month": [1],
                    "water_year": [2001],
                    "OFE": [1],
                    "Poros": [66.01],
                    "Keff": [40.0],
                    "Suct": [17.65],
                    "FC": [0.20],
                    "WP": [0.05],
                    "Rough": [100.0],
                    "Ki": [0.04],
                    "Kr": [0.13],
                    "Tauc": [2.0],
                    "Saturation": [0.46],
                    "TSW": [30.56],
                }
            )
            pq.write_table(table, target_path)

    fake_rust = _FakeRustSoil()
    monkeypatch.setattr(_watershed_soil, "load_rust_interchange", lambda: (fake_rust, None))
    monkeypatch.setattr(_watershed_soil, "resolve_cli_calendar_path", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_watershed_soil, "version_args", lambda: (1, 2))

    target = run_wepp_watershed_soil_interchange(workdir)
    assert target.exists()
    assert fake_rust.calls == 1

    table = pq.read_table(target)
    assert table.schema == _SCHEMA
    assert "TSMF" in table.schema.names
    assert table.column("TSMF").null_count == table.num_rows


@pytest.mark.integration
@pytest.mark.parametrize(
    ("profile", "missing_columns"),
    [
        ("legacy-palouse", {"Saturation", "TSW", "TSMF"}),
        ("us-small-wbt-daymet-rap-wepp", {"TSMF"}),
    ],
    ids=["legacy-layout", "modern-layout"],
)
def test_watershed_soil_interchange_supports_multiple_layouts(tmp_path: Path, profile: str, missing_columns: Set[str]) -> None:
    source = PROFILE_DATA_ROOT / profile / "run/wepp/output" / "soil_pw0.txt"
    if not source.exists():
        pytest.skip(f"profile dataset missing: {source}")

    tmp_source = tmp_path / "soil_pw0.txt"
    tmp_source.write_bytes(source.read_bytes())
    target = tmp_path / "soil.parquet"

    _write_soil_parquet(tmp_source, target)
    assert target.exists()

    table = pq.read_table(target)
    assert table.schema == _SCHEMA
    assert table.num_rows > 0

    for column in _MEASUREMENT_COLUMNS:
        arr = table.column(column)
        if column in missing_columns:
            assert arr.null_count == table.num_rows
        else:
            assert arr.null_count < table.num_rows
