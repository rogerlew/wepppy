from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.rq.weppcloudr_rq import (
    _discover_nodir_parquet_overrides,
    _sidecar_to_logical_parquet,
)

pytestmark = pytest.mark.unit


def test_sidecar_to_logical_parquet_maps_known_nodir_sidecars() -> None:
    assert _sidecar_to_logical_parquet("landuse.parquet") == "landuse/landuse.parquet"
    assert _sidecar_to_logical_parquet("soils.parquet") == "soils/soils.parquet"
    assert (
        _sidecar_to_logical_parquet("watershed.hillslopes.parquet")
        == "watershed/hillslopes.parquet"
    )
    assert _sidecar_to_logical_parquet("climate.wepp_cli.parquet") == "climate/wepp_cli.parquet"
    assert _sidecar_to_logical_parquet("totals.parquet") is None


def test_discover_nodir_parquet_overrides_collects_existing_sidecars(tmp_path: Path) -> None:
    (tmp_path / "landuse.parquet").write_text("x", encoding="utf-8")
    (tmp_path / "soils.parquet").write_text("x", encoding="utf-8")
    (tmp_path / "watershed.hillslopes.parquet").write_text("x", encoding="utf-8")
    (tmp_path / "climate.wepp_cli.parquet").write_text("x", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
    (tmp_path / "watershed").mkdir()

    overrides = _discover_nodir_parquet_overrides(tmp_path)

    assert overrides == {
        "climate/wepp_cli.parquet": str(tmp_path / "climate.wepp_cli.parquet"),
        "landuse/landuse.parquet": str(tmp_path / "landuse.parquet"),
        "soils/soils.parquet": str(tmp_path / "soils.parquet"),
        "watershed/hillslopes.parquet": str(tmp_path / "watershed.hillslopes.parquet"),
    }
