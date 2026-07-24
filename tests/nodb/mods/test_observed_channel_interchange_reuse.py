from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.nodb.mods.observed import observed as observed_module
from wepppy.nodb.mods.observed.observed import Observed


pytestmark = pytest.mark.nodb


def test_channel_simulation_reuses_parquet_when_raw_outputs_are_absent(
    tmp_path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "wepp" / "output"
    interchange_dir = output_dir / "interchange"
    interchange_dir.mkdir(parents=True)

    ebe_path = interchange_dir / "ebe_pw0.parquet"
    pq.write_table(
        pa.table(
            {
                "year": [2000],
                "simulation_year": [1],
                "month": [1],
                "day_of_month": [2],
                "julian": [2],
                "water_year": [2000],
                "sediment_yield": [3.5],
            }
        ),
        ebe_path,
    )

    chan_path = interchange_dir / "chanwb.parquet"
    pq.write_table(
        pa.table(
            {
                "year": [2000],
                "month": [1],
                "day_of_month": [2],
                "julian": [2],
                "water_year": [2000],
                "Outflow (m^3)": [2.0],
            }
        ),
        chan_path,
    )

    def fail_interchange(_output_dir):
        raise AssertionError("raw-text interchange should not run")

    monkeypatch.setattr(
        observed_module,
        "_interchange_module",
        lambda: SimpleNamespace(
            run_wepp_watershed_ebe_interchange=fail_interchange,
            run_wepp_watershed_chanwb_interchange=fail_interchange,
        ),
    )

    observed = object.__new__(Observed)
    observed.wd = str(tmp_path)

    result = observed._load_channel_simulation(wsarea_m2=1000.0, first_year=2000)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.loc[0, "Streamflow (mm)"] == pytest.approx(2.0)
    assert result.loc[0, "Sed Del (kg)"] == pytest.approx(3.5)
