from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.climates.cligen import ClimateFile, Cligen, StationMeta


pytestmark = pytest.mark.integration


def test_vendored_cligen_generates_parseable_cli_with_verified_identity(tmp_path):
    station_path = (
        Path(__file__).resolve().parents[2]
        / "wepppy"
        / "climates"
        / "cligen"
        / "2015_par_files"
        / "or354811.par"
    )
    if not station_path.is_file():
        pytest.skip(f"CLIGEN station fixture is unavailable: {station_path}")

    station = StationMeta(
        "OR",
        "LEABURG OR 354811",
        str(station_path),
        44.63,
        -122.72,
        45,
        0,
        205.0,
        0,
        0,
        0.0,
    )
    runner = Cligen(station, wd=str(tmp_path), cliver="5.3.2")

    cli_name = runner.run_multiple_year(1, cli_fname="verified.cli")

    cli_path = tmp_path / cli_name
    climate = ClimateFile(str(cli_path))
    assert cli_path.stat().st_size > 0
    assert len(climate.as_dataframe()) in (365, 366)
    log_text = (tmp_path / "cligen_verified.log").read_text(encoding="utf-8")
    assert "[run_multiple_year] binary_identity" in log_text
    assert "binary_identity_status=verified" in log_text
    assert 'cligen_version="5.32300"' in log_text
    assert 'release_label="5.323-k10.1"' in log_text
    assert "binary_sha256=119ba1de5bc48757901224c8d6e91022a91bf255a45043a98579199e681aaddc" in log_text
    assert "source_commit=f7f337b026dc2eee18e098a3c5de72cd0c601a2e" in log_text
