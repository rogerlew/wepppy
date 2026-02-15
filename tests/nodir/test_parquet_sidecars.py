from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.nodir.parquet_sidecars import (
    logical_parquet_to_sidecar_relpath,
    pick_existing_parquet_relpath,
    sidecar_relpath_to_logical_parquet,
)

pytestmark = pytest.mark.unit


def test_parquet_sidecar_mapping_round_trip() -> None:
    assert (
        logical_parquet_to_sidecar_relpath("climate/wepp_cli.parquet") == "climate.wepp_cli.parquet"
    )
    assert (
        sidecar_relpath_to_logical_parquet("climate.wepp_cli.parquet") == "climate/wepp_cli.parquet"
    )
    assert (
        logical_parquet_to_sidecar_relpath("watershed/hillslopes.parquet")
        == "watershed.hillslopes.parquet"
    )
    assert (
        sidecar_relpath_to_logical_parquet("watershed.hillslopes.parquet")
        == "watershed/hillslopes.parquet"
    )


def test_pick_existing_parquet_prefers_sidecar(tmp_path: Path) -> None:
    logical = "watershed/hillslopes.parquet"
    sidecar = tmp_path / "watershed.hillslopes.parquet"
    legacy = tmp_path / "watershed" / "hillslopes.parquet"
    legacy.parent.mkdir(parents=True, exist_ok=True)

    legacy.write_text("legacy", encoding="utf-8")
    assert pick_existing_parquet_relpath(tmp_path, logical) == str(Path("watershed") / "hillslopes.parquet")

    sidecar.write_text("sidecar", encoding="utf-8")
    assert pick_existing_parquet_relpath(tmp_path, logical) == "watershed.hillslopes.parquet"

