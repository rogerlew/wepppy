from __future__ import annotations

import logging
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from wepppy.nodb.core.climate_artifact_export_service import ClimateArtifactExportService

pytestmark = pytest.mark.unit


def _write_minimal_cli(path: Path) -> None:
    path.write_text(
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
                "  1  1 1981   6.0  0.70  0.2    1.6  19.4  11.5  267  2.7   295  13.4",
                "  2  1 1981   7.0  0.80  0.2    1.8  20.5  11.0  291  2.3     5  12.7",
                "",
            ]
        )
    )


def test_export_post_build_artifacts_runs_sequence(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClimateArtifactExportService()
    calls: list[str] = []

    class _Climate:
        def _export_cli_parquet(self):
            calls.append("parquet")
            return Path("/tmp/dummy.parquet")

        def _export_cli_precip_frequency_csv(self, _path: Path):
            calls.append("freq")

        def _download_noaa_atlas14_intensity(self):
            calls.append("atlas")

    monkeypatch.setattr("wepppy.nodb.core.climate_artifact_export_service.time.sleep", lambda _v: None)

    service.export_post_build_artifacts(_Climate())

    assert calls == ["parquet", "freq", "atlas"]


def test_export_cli_parquet_writes_expected_sidecar(tmp_path: Path) -> None:
    service = ClimateArtifactExportService()
    cli_dir = tmp_path / "cli"
    cli_dir.mkdir()
    cli_fn = "user.cli"
    _write_minimal_cli(cli_dir / cli_fn)

    climate = SimpleNamespace(
        cli_fn=cli_fn,
        cli_dir=str(cli_dir),
        wd=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.parquet"),
    )

    parquet_path = service.export_cli_parquet(climate)

    assert parquet_path == tmp_path / "climate" / "wepp_cli.parquet"
    assert parquet_path.exists()

    df = pd.read_parquet(parquet_path)
    assert {"peak_intensity_30", "storm_duration_hours", "julian", "sim_day_index"}.issubset(df.columns)


def test_export_cli_precip_frequency_csv_writes_recurrence_limited_by_years(tmp_path: Path) -> None:
    service = ClimateArtifactExportService()

    parquet_path = tmp_path / "climate" / "wepp_cli.parquet"
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "year": [1980, 1980, 1981, 1981],
            "month": [1, 2, 1, 2],
            "prcp": [10.0, 8.0, 12.0, 6.0],
            "storm_duration_hours": [1.0, 0.5, 1.2, 0.8],
            "peak_intensity_30": [20.0, 18.0, 25.0, 16.0],
            "peak_intensity_10": [40.0, 35.0, 45.0, 33.0],
            "peak_intensity_15": [30.0, 28.0, 34.0, 24.0],
            "peak_intensity_60": [12.0, 11.0, 15.0, 9.0],
        }
    ).to_parquet(parquet_path, index=False)

    climate = SimpleNamespace(
        logger=logging.getLogger("tests.nodb.climate.artifacts.freq"),
        climatestation="STA-1",
        runid="run-123",
        watershed_instance=SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    output = service.export_cli_precip_frequency_csv(climate, parquet_path)

    assert output is not None
    text = output.read_text()
    assert "PRECIPITATION FREQUENCY ESTIMATES" in text
    assert "ARI (years):, 1,2" in text


def test_download_noaa_atlas14_intensity_skips_non_legacy_cligen_db(tmp_path: Path) -> None:
    service = ClimateArtifactExportService()

    climate = SimpleNamespace(
        cligen_db="ghcn",
        cli_dir=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.atlas"),
        watershed_instance=SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    assert service.download_noaa_atlas14_intensity(climate) is None


def _install_fake_atlas14(monkeypatch: pytest.MonkeyPatch, atlas14_obj: object) -> None:
    pfdf_mod = types.ModuleType("pfdf")
    data_mod = types.ModuleType("pfdf.data")
    noaa_mod = types.ModuleType("pfdf.data.noaa")
    noaa_mod.atlas14 = atlas14_obj
    data_mod.noaa = noaa_mod
    pfdf_mod.data = data_mod

    monkeypatch.setitem(sys.modules, "pfdf", pfdf_mod)
    monkeypatch.setitem(sys.modules, "pfdf.data", data_mod)
    monkeypatch.setitem(sys.modules, "pfdf.data.noaa", noaa_mod)


def test_download_noaa_atlas14_intensity_returns_path_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateArtifactExportService()
    output_path = tmp_path / "atlas14_intensity_pds_mean_metric.csv"

    class _Atlas14:
        @staticmethod
        def download(**_kwargs):
            output_path.write_text("atlas14")
            return str(output_path)

    _install_fake_atlas14(monkeypatch, _Atlas14)

    climate = SimpleNamespace(
        cligen_db="ghcn_2015",
        cli_dir=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.atlas.success"),
        watershed_instance=SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    result = service.download_noaa_atlas14_intensity(climate)

    assert result == output_path
    assert output_path.exists()


def test_download_noaa_atlas14_intensity_returns_none_on_no_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateArtifactExportService()

    class _Atlas14:
        @staticmethod
        def download(**_kwargs):
            raise ValueError("no coverage")

    _install_fake_atlas14(monkeypatch, _Atlas14)

    climate = SimpleNamespace(
        cligen_db="legacy",
        cli_dir=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.atlas.nocoverage"),
        watershed_instance=SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    assert service.download_noaa_atlas14_intensity(climate) is None


def test_download_noaa_atlas14_intensity_returns_none_on_download_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateArtifactExportService()

    class _Atlas14:
        @staticmethod
        def download(**_kwargs):
            raise RuntimeError("network down")

    _install_fake_atlas14(monkeypatch, _Atlas14)

    climate = SimpleNamespace(
        cligen_db="legacy",
        cli_dir=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.atlas.failure"),
        watershed_instance=SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    assert service.download_noaa_atlas14_intensity(climate) is None
