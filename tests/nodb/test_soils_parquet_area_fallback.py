from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from wepppy.nodb.core.soils import Soils

pytestmark = pytest.mark.unit


def _write_soils_parquet(run_dir: Path, frame: pd.DataFrame) -> None:
    soils_dir = run_dir / "soils"
    soils_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(soils_dir / "soils.parquet", index=False)


def test_clay_and_liquid_limit_fall_back_to_watershed_area_when_soils_area_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    _write_soils_parquet(
        run_dir,
        pd.DataFrame(
            {
                "topaz_id": [21, 22, 23],
                "mukey": ["1", "2", "3"],
                "clay": [10.0, 20.0, 30.0],
                "ll": [30.0, None, 50.0],
            }
        ),
    )

    watershed_stub = SimpleNamespace(
        hillslope_area=lambda topaz_id: {"21": 1.0, "22": 2.0, "23": 3.0}[str(topaz_id)],
    )
    monkeypatch.setattr(Soils, "watershed_instance", property(lambda _self: watershed_stub))

    soils = Soils.__new__(Soils)
    soils.wd = str(run_dir)

    assert soils.clay_pct == pytest.approx((10.0 * 1.0 + 20.0 * 2.0 + 30.0 * 3.0) / 6.0)
    assert soils.liquid_limit == pytest.approx((30.0 * 1.0 + 50.0 * 3.0) / 4.0)


def test_clay_and_liquid_limit_use_soils_area_when_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    _write_soils_parquet(
        run_dir,
        pd.DataFrame(
            {
                "topaz_id": [21, 22, 23],
                "mukey": ["1", "2", "3"],
                "clay": [10.0, 20.0, 30.0],
                "ll": [30.0, None, 50.0],
                "area": [4.0, 5.0, 6.0],
            }
        ),
    )

    watershed_stub = SimpleNamespace(
        hillslope_area=lambda _topaz_id: (_ for _ in ()).throw(
            AssertionError("hillslope_area should not be used when soils.parquet has area")
        ),
    )
    monkeypatch.setattr(Soils, "watershed_instance", property(lambda _self: watershed_stub))

    soils = Soils.__new__(Soils)
    soils.wd = str(run_dir)

    assert soils.clay_pct == pytest.approx((10.0 * 4.0 + 20.0 * 5.0 + 30.0 * 6.0) / 15.0)
    assert soils.liquid_limit == pytest.approx((30.0 * 4.0 + 50.0 * 6.0) / 10.0)
