from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.core.climate_user_defined_station_meta_service import (
    ClimateUserDefinedStationMetaService,
)

pytestmark = pytest.mark.unit


def _cli_stub(
    *,
    header: list[str],
    lat: float = 34.18,
    lng: float = -118.57,
    elevation: float | None = 304.8,
    input_years: int = 40,
) -> SimpleNamespace:
    return SimpleNamespace(
        header=header,
        lat=lat,
        lng=lng,
        elevation=elevation,
        input_years=input_years,
    )


def test_build_station_meta_parses_header_station_id_and_monthlies(tmp_path: Path) -> None:
    service = ClimateUserDefinedStationMetaService()
    header = [
        "  Station:  TEST STATION CA                     CLIGEN VER. 5.32300",
        " Command Line: -itest.par -Ows.prn -owepp.cli",
    ]
    cli = _cli_stub(header=header)
    monthlies = {
        "ppts": [10.0, 20.0, 30.0],
        "nwds": [2.0, 4.0, 0.0],
        "tmaxs": [20.0] * 12,
        "tmins": [10.0] * 12,
    }

    meta = service.build_station_meta_from_cli(
        cli=cli,
        cli_filename="uploaded.cli",
        cli_dir=str(tmp_path),
        monthlies=monthlies,
    )

    expected_station_id = service._resolve_station_id(header, "uploaded.cli")
    par_path = tmp_path / f"{expected_station_id}.par"
    assert par_path.exists()
    assert meta.id == expected_station_id
    assert meta.par == f"{expected_station_id}.par"
    assert meta.state == expected_station_id[:2].upper()
    assert meta.desc == "TEST STATION CA"
    assert meta.elevation == 1000.0
    assert meta.annual_ppt == 60.0
    assert meta._monthlies_override["ppts"] == [5.0, 5.0, 0.0]

    par_lines = par_path.read_text().splitlines()
    assert par_lines[0] == f"TEST STATION CA {expected_station_id} 0"
    assert par_lines[3].startswith("MEAN P")


def test_build_station_meta_falls_back_to_filename_and_description_state(tmp_path: Path) -> None:
    service = ClimateUserDefinedStationMetaService()
    cli = _cli_stub(
        header=["Station: Example Place tx CLIGEN VER. 5.32300"],
        elevation=None,
    )

    meta = service.build_station_meta_from_cli(
        cli=cli,
        cli_filename="12-station?.cli",
        cli_dir=str(tmp_path),
        monthlies=None,
    )

    assert meta.id == "12-station"
    assert meta.par == "12-station.par"
    assert meta.state == "TX"
    assert meta.desc == "Example Place tx"
    assert meta.elevation is None
    assert not hasattr(meta, "_monthlies_override")


def test_build_station_meta_uses_default_station_id_and_preserves_existing_stub(tmp_path: Path) -> None:
    service = ClimateUserDefinedStationMetaService()
    existing = tmp_path / "user_defined.par"
    existing.write_text("existing par\n")
    cli = _cli_stub(header=["No station metadata here"])

    meta = service.build_station_meta_from_cli(
        cli=cli,
        cli_filename="$$$.cli",
        cli_dir=str(tmp_path),
        monthlies=None,
    )

    assert meta.id == "user_defined"
    assert meta.par == "user_defined.par"
    assert meta.desc == "User defined climate"
    assert existing.read_text() == "existing par\n"
