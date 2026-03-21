from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.runtime_paths.errors import NoDirError
from wepppy.wepp.interchange._utils import _ensure_cli_parquet

pytestmark = pytest.mark.unit


def test_ensure_cli_parquet_prefers_canonical_directory_file(tmp_path: Path) -> None:
    cli_dir = tmp_path / "climate"
    cli_dir.mkdir(parents=True)
    canonical = cli_dir / "wepp_cli.parquet"
    canonical.write_text("ok", encoding="utf-8")

    resolved = _ensure_cli_parquet(cli_dir)

    assert resolved == canonical


def test_ensure_cli_parquet_rejects_retired_root_sidecar(tmp_path: Path) -> None:
    cli_dir = tmp_path / "climate"
    cli_dir.mkdir(parents=True)
    retired = tmp_path / "climate.wepp_cli.parquet"
    retired.write_text("retired", encoding="utf-8")

    with pytest.raises(NoDirError, match="NODIR_MIGRATION_REQUIRED"):
        _ensure_cli_parquet(cli_dir)


def test_ensure_cli_parquet_generates_peak_intensity_60_when_materializing(tmp_path: Path) -> None:
    cli_dir = tmp_path / "climate"
    cli_dir.mkdir(parents=True)
    cli_path = cli_dir / "generated.cli"
    cli_path.write_text(
        "\n".join(
            [
                "5.32300",
                "   1   0   0",
                "  Station:  TEST STATION                               CLIGEN VER. 5.32300 -r:    0 -I: 2",
                " Latitude Longitude Elevation (m) Obs. Years   Beginning year  Years simulated Command Line:",
                "    34.18  -118.57         240          40        1980             2          -itest.par -Ows.prn -owepp.cli -t6 -I2",
                " Observed monthly ave max temperature (C)",
                "  20.3  20.8  22.5  25.0  27.6  31.2  35.1  35.6  33.5  29.0  24.0  20.3",
                " Observed monthly ave min temperature (C)",
                "   4.6   5.0   6.0   7.3   9.9  12.1  14.3  14.3  13.1  10.1   6.2   4.0",
                " Observed monthly ave solar radiation (Langleys/day)",
                " 236.0 291.0 404.0 529.0 557.0 569.0 553.0 548.0 452.0 346.0 277.0 225.0",
                " Observed monthly ave precipitation (mm)",
                "  95.9 105.8  79.7  23.4   9.9   1.7   0.5   2.3   5.3  18.3  27.6  61.9",
                " da mo year  prcp  dur   tp     ip  tmax  tmin  rad  w-vl w-dir  tdew",
                "             (mm)  (h)               (C)   (C) (l/d) (m/s)(Deg)   (C)",
                "  1  1 1980   4.0  0.50  0.2    1.2  19.4  11.5  267  2.7   295  13.4",
                "  2  1 1980   5.0  0.60  0.2    1.4  20.5  11.0  291  2.3     5  12.7",
                "",
            ]
        ),
        encoding="utf-8",
    )

    resolved = _ensure_cli_parquet(cli_dir, cli_file_hint=cli_path.name)
    assert resolved is not None
    assert resolved.exists()

    import pandas as pd

    df = pd.read_parquet(resolved)
    assert "peak_intensity_60" in df.columns
