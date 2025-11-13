from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

try:  # pragma: no cover - optional dependency probing
    import pandas  # type: ignore  # noqa: F401
    import pyarrow  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    _ASH_TESTS_ENABLED = False
else:
    _ASH_TESTS_ENABLED = True

pytestmark = pytest.mark.skipif(not _ASH_TESTS_ENABLED, reason="pandas/pyarrow required")

if _ASH_TESTS_ENABLED:
    from wepppy.wepp.interchange.totalwatsed3 import ASH_METRIC_COLUMNS, run_totalwatsed3
else:  # pragma: no cover - module-level skip
    ASH_METRIC_COLUMNS = tuple()


class _BaseflowOpts:
    def __init__(self, gwstorage: float = 0.0, dscoeff: float = 0.0, bfcoeff: float = 0.0) -> None:
        self.gwstorage = gwstorage
        self.dscoeff = dscoeff
        self.bfcoeff = bfcoeff


def _read_parquet_dict(path: Path) -> dict[str, list]:
    with duckdb.connect() as con:
        cursor = con.execute("SELECT * FROM read_parquet(?)", [str(path)])
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
    return {col: [row[idx] for row in rows] for idx, col in enumerate(columns)}


def _write_pass(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = str(path).replace("'", "''")
    query = f"""
    COPY (
        SELECT
            1 AS wepp_id,
            2020 AS year,
            1 AS sim_day_index,
            1 AS julian,
            1 AS month,
            1 AS day_of_month,
            2020 AS water_year,
            1.0 AS runvol,
            0.2 AS sbrunv,
            0.5 AS tdet,
            0.1 AS tdep,
            0.05 AS sedcon_1,
            0.05 AS sedcon_2,
            0.05 AS sedcon_3,
            0.05 AS sedcon_4,
            0.05 AS sedcon_5
    ) TO '{safe}' (FORMAT PARQUET)
    """
    with duckdb.connect() as con:
        con.execute(query)


def _write_wat(path: Path, area_m2: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = str(path).replace("'", "''")
    query = f"""
    COPY (
        SELECT
            1 AS wepp_id,
            1 AS ofe_id,
            2020 AS year,
            1 AS sim_day_index,
            1 AS julian,
            1 AS month,
            1 AS day_of_month,
            2020 AS water_year,
            ? AS Area,
            5.0 AS P,
            6.0 AS RM,
            1.0 AS Q,
            0.5 AS Dp,
            0.4 AS latqcc,
            0.3 AS QOFE,
            0.2 AS Ep,
            0.1 AS Es,
            0.05 AS Er,
            0.0 AS UpStrmQ,
            0.0 AS SubRIn,
            0.0 AS "Total-Soil Water",
            0.0 AS frozwt,
            0.0 AS "Snow-Water",
            0.0 AS Tile,
            0.0 AS Irr
    ) TO '{safe}' (FORMAT PARQUET)
    """
    with duckdb.connect() as con:
        con.execute(query, [float(area_m2)])


def _write_ash(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = str(path).replace("'", "''")
    query = f"""
    COPY (
        SELECT
            2020 AS year0,
            2020 AS year,
            1 AS julian,
            1 AS mo,
            1 AS da,
            0 AS "days_from_fire (days)",
            CAST(0.5 AS DOUBLE) AS "wind_transport (tonne/ha)",
            CAST(0.2 AS DOUBLE) AS "water_transport (tonne/ha)",
            CAST(0.7 AS DOUBLE) AS "ash_transport (tonne/ha)",
            CAST(1.1 AS DOUBLE) AS "transportable_ash (tonne/ha)",
            CAST(0.0 AS DOUBLE) AS "ash_runoff (mm)",
            CAST(0.0 AS DOUBLE) AS "ash_depth (mm)"
    ) TO '{safe}' (FORMAT PARQUET)
    """
    with duckdb.connect() as con:
        con.execute(query)


def test_run_totalwatsed3_merges_ash_metrics(tmp_path):
    run_dir = tmp_path / "run"
    interchange_dir = run_dir / "wepp" / "output" / "interchange"
    pass_path = interchange_dir / "H.pass.parquet"
    wat_path = interchange_dir / "H.wat.parquet"
    _write_pass(pass_path)
    _write_wat(wat_path, area_m2=10_000.0)

    ash_dir = run_dir / "ash"
    _write_ash(ash_dir / "H1_ash.parquet")

    baseflow_opts = _BaseflowOpts(gwstorage=1.0, dscoeff=0.1, bfcoeff=0.05)

    output_path = run_totalwatsed3(
        interchange_dir,
        baseflow_opts,
        wepp_ids=[1],
        ash_dir=ash_dir,
        ash_area_lookup={1: 2.0},
    )

    data = _read_parquet_dict(output_path)
    assert "ash_transport (tonne)" in data
    assert data["wind_transport (tonne)"][0] == pytest.approx(1.0)
    assert data["wind_transport (tonne/ha)"][0] == pytest.approx(0.5)
    assert data["ash_transport (tonne)"][0] == pytest.approx(1.4)

    # Missing ash directory should still produce rows with zeroed ash metrics.
    run_totalwatsed3(
        interchange_dir,
        baseflow_opts,
        wepp_ids=[1],
        ash_dir=ash_dir / "missing",
        ash_area_lookup={1: 2.0},
    )
    filtered = _read_parquet_dict(output_path)
    for column in ASH_METRIC_COLUMNS:
        assert all(value == 0.0 for value in filtered.get(column, []))
