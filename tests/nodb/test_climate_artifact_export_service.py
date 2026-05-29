from __future__ import annotations

import logging
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


def _write_minimal_breakpoint_cli(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "0.00",
                "   1   1   0",
                "Station: Test",
                " Latitude Longitude Elevation (m) Obs. Years    Beginning year  Years simulated",
                "    33.66  -109.31             1831             6             2011             2",
                " Observed monthly ave max temperature (C)",
                " 27.0 27.0 27.0 27.0 27.0 27.0 27.0 27.0 27.0 27.0 27.0 27.0",
                " Observed monthly ave min temperature (C)",
                "  8.0  8.0  8.0  8.0  8.0  8.0  8.0  8.0  8.0  8.0  8.0  8.0",
                " Observed monthly ave solar radiation (Langleys)",
                " 300.0 300.0 300.0 300.0 300.0 300.0 300.0 300.0 300.0 300.0 300.0 300.0",
                " Observed monthly ave rainfall (mm)",
                "  20.0 20.0 20.0 20.0 20.0 20.0 20.0 20.0 20.0 20.0 20.0 20.0",
                "   day mon year nbrkpt tmax  tmin    rad   w-vel  w-dir   dew",
                "                (mm)    (C)   (C) (ly/day) m/sec    deg    (C)",
                "    1   1  2011   3    -4.28  -23.72 277.6    2.20  290.0 -25.6",
                "00.75     0.000",
                "01.00     10.000",
                "05.00     10.254",
                "    2   1  2011   0    -5.39  -22.06 259.2    5.60  324.0 -18.4",
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


def test_export_cli_parquet_breakpoint_writes_real_intensities_and_nullable_tp_ip(tmp_path: Path) -> None:
    service = ClimateArtifactExportService()
    cli_dir = tmp_path / "cli"
    cli_dir.mkdir()
    cli_fn = "breakpoint.cli"
    _write_minimal_breakpoint_cli(cli_dir / cli_fn)

    climate = SimpleNamespace(
        cli_fn=cli_fn,
        cli_dir=str(cli_dir),
        wd=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.breakpoint.parquet"),
    )

    parquet_path = service.export_cli_parquet(climate)
    assert parquet_path == tmp_path / "climate" / "wepp_cli.parquet"
    assert parquet_path.exists()

    df = pd.read_parquet(parquet_path)
    required = {
        "dur",
        "tp",
        "ip",
        "peak_intensity_10",
        "peak_intensity_15",
        "peak_intensity_30",
        "peak_intensity_60",
    }
    assert required.issubset(df.columns)
    assert (df[["peak_intensity_10", "peak_intensity_15", "peak_intensity_30", "peak_intensity_60"]] >= 0.0).all().all()
    assert pd.isna(df.loc[0, "tp"])
    assert pd.isna(df.loc[0, "ip"])
    assert float(df.loc[0, "dur"]) > 0.0
    assert float(df.loc[0, "peak_intensity_10"]) == pytest.approx(40.0)
    assert float(df.loc[0, "peak_intensity_15"]) == pytest.approx(40.0)
    assert float(df.loc[0, "peak_intensity_30"]) == pytest.approx(20.03175)
    assert float(df.loc[0, "peak_intensity_60"]) == pytest.approx(10.047625)


def test_export_cli_parquet_prefers_canonical_intensity_columns_and_backfills_nullable_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateArtifactExportService()
    cli_dir = tmp_path / "cli"
    cli_dir.mkdir()
    cli_fn = "stub.cli"
    (cli_dir / cli_fn).write_text("stub")

    stub_df = pd.DataFrame(
        {
            "year": [1980],
            "mo": [1],
            "da": [1],
            "peak_intensity_10": [11.0],
            "10-min Peak Rainfall Intensity (mm/hour)": [99.0],
            "peak_intensity_15": [pd.NA],
            "15-min Peak Rainfall Intensity (mm/hour)": [88.0],
            "30-min Peak Rainfall Intensity (mm/hour)": [77.0],
            "peak_intensity_60": [66.0],
        }
    )

    class _FakeClimateFile:
        def __init__(self, _path: str) -> None:
            pass

        def as_dataframe(self, *, calc_peak_intensities: bool) -> pd.DataFrame:
            assert calc_peak_intensities is True
            return stub_df.copy()

    monkeypatch.setattr("wepppy.nodb.core.climate_artifact_export_service.ClimateFile", _FakeClimateFile)

    climate = SimpleNamespace(
        cli_fn=cli_fn,
        cli_dir=str(cli_dir),
        wd=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.coalesce.parquet"),
    )

    parquet_path = service.export_cli_parquet(climate)
    assert parquet_path is not None
    assert parquet_path.exists()

    df = pd.read_parquet(parquet_path)
    assert float(df.loc[0, "peak_intensity_10"]) == pytest.approx(11.0)
    assert float(df.loc[0, "10-min Peak Rainfall Intensity (mm/hour)"]) == pytest.approx(11.0)
    assert float(df.loc[0, "peak_intensity_15"]) == pytest.approx(88.0)
    assert float(df.loc[0, "15-min Peak Rainfall Intensity (mm/hour)"]) == pytest.approx(88.0)
    assert float(df.loc[0, "peak_intensity_30"]) == pytest.approx(77.0)
    assert float(df.loc[0, "peak_intensity_60"]) == pytest.approx(66.0)
    assert pd.isna(df.loc[0, "dur"])
    assert pd.isna(df.loc[0, "tp"])
    assert pd.isna(df.loc[0, "ip"])


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
    monkeypatch.setattr("wepppy.nodb.core.climate_artifact_export_service.atlas14", atlas14_obj)


def _configure_noaa_retry_env(
    monkeypatch: pytest.MonkeyPatch,
    sleeps: list[float],
    *,
    total_attempts: str = "3",
    base_seconds: str = "1.0",
    cap_seconds: str = "8.0",
    timeout_seconds: str | None = None,
) -> None:
    monkeypatch.setattr("wepppy.nodb.core.climate_artifact_export_service.time.sleep", lambda v: sleeps.append(v))
    monkeypatch.setenv("WEPPPY_NOAA_ATLAS14_TOTAL_ATTEMPTS", total_attempts)
    monkeypatch.setenv("WEPPPY_NOAA_ATLAS14_RETRY_BASE_SECONDS", base_seconds)
    monkeypatch.setenv("WEPPPY_NOAA_ATLAS14_RETRY_CAP_SECONDS", cap_seconds)
    if timeout_seconds is None:
        monkeypatch.delenv("WEPPPY_NOAA_ATLAS14_TIMEOUT_SECONDS", raising=False)
        return
    monkeypatch.setenv("WEPPPY_NOAA_ATLAS14_TIMEOUT_SECONDS", timeout_seconds)


def test_download_noaa_atlas14_intensity_returns_path_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateArtifactExportService()
    output_path = tmp_path / "atlas14_intensity_pds_mean_metric.csv"
    kwargs_calls: list[dict[str, object]] = []

    class _Atlas14:
        @staticmethod
        def download(**_kwargs):
            kwargs_calls.append(_kwargs)
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
    assert kwargs_calls[-1]["timeout"] == 30


def test_download_noaa_atlas14_intensity_transient_failure_then_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateArtifactExportService()
    output_path = tmp_path / "atlas14_intensity_pds_mean_metric.csv"
    attempts: list[int] = []
    sleeps: list[float] = []
    kwargs_calls: list[dict[str, object]] = []

    class _Atlas14:
        @staticmethod
        def download(**_kwargs):
            kwargs_calls.append(_kwargs)
            attempts.append(len(attempts) + 1)
            if len(attempts) == 1:
                raise RuntimeError("temporary upstream failure")
            output_path.write_text("atlas14")
            return str(output_path)

    _install_fake_atlas14(monkeypatch, _Atlas14)
    _configure_noaa_retry_env(monkeypatch, sleeps)

    climate = SimpleNamespace(
        cligen_db="legacy",
        cli_dir=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.atlas.transient"),
        watershed_instance=SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    result = service.download_noaa_atlas14_intensity(climate)

    assert result == output_path
    assert attempts == [1, 2]
    assert sleeps == [1.0]
    assert kwargs_calls[0]["timeout"] == 30
    assert kwargs_calls[1]["timeout"] == 30


def test_download_noaa_atlas14_intensity_retry_exhaustion_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateArtifactExportService()
    attempts: list[int] = []
    sleeps: list[float] = []

    class _Atlas14:
        @staticmethod
        def download(**_kwargs):
            attempts.append(len(attempts) + 1)
            raise RuntimeError("network down")

    _install_fake_atlas14(monkeypatch, _Atlas14)
    _configure_noaa_retry_env(monkeypatch, sleeps)

    climate = SimpleNamespace(
        cligen_db="legacy",
        cli_dir=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.atlas.exhausted"),
        watershed_instance=SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    assert service.download_noaa_atlas14_intensity(climate) is None
    assert attempts == [1, 2, 3]
    assert sleeps == [1.0, 2.0]


def test_download_noaa_atlas14_intensity_no_coverage_is_non_retryable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateArtifactExportService()
    attempts: list[int] = []
    sleeps: list[float] = []

    class _Atlas14:
        @staticmethod
        def download(**_kwargs):
            attempts.append(len(attempts) + 1)
            raise ValueError("no coverage")

    _install_fake_atlas14(monkeypatch, _Atlas14)
    _configure_noaa_retry_env(monkeypatch, sleeps)

    climate = SimpleNamespace(
        cligen_db="legacy",
        cli_dir=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.atlas.no_coverage"),
        watershed_instance=SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    assert service.download_noaa_atlas14_intensity(climate) is None
    assert attempts == [1]
    assert sleeps == []


def test_download_noaa_atlas14_intensity_applies_timeout_cap_and_attempt_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateArtifactExportService()
    attempts: list[int] = []
    sleeps: list[float] = []
    kwargs_calls: list[dict[str, object]] = []

    class _Atlas14:
        @staticmethod
        def download(**_kwargs):
            kwargs_calls.append(_kwargs)
            attempts.append(len(attempts) + 1)
            raise RuntimeError("network down")

    _install_fake_atlas14(monkeypatch, _Atlas14)
    _configure_noaa_retry_env(
        monkeypatch,
        sleeps,
        total_attempts="4",
        base_seconds="4.0",
        cap_seconds="5.0",
        timeout_seconds="17",
    )

    climate = SimpleNamespace(
        cligen_db="legacy",
        cli_dir=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.atlas.env_override"),
        watershed_instance=SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    assert service.download_noaa_atlas14_intensity(climate) is None
    assert attempts == [1, 2, 3, 4]
    assert sleeps == [4.0, 5.0, 5.0]
    assert [call["timeout"] for call in kwargs_calls] == [17, 17, 17, 17]


def test_download_noaa_atlas14_intensity_invalid_env_uses_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateArtifactExportService()
    attempts: list[int] = []
    sleeps: list[float] = []
    kwargs_calls: list[dict[str, object]] = []

    class _Atlas14:
        @staticmethod
        def download(**_kwargs):
            kwargs_calls.append(_kwargs)
            attempts.append(len(attempts) + 1)
            raise RuntimeError("network down")

    _install_fake_atlas14(monkeypatch, _Atlas14)
    _configure_noaa_retry_env(
        monkeypatch,
        sleeps,
        total_attempts="invalid",
        base_seconds="NaN",
        cap_seconds="invalid",
        timeout_seconds="invalid",
    )

    climate = SimpleNamespace(
        cligen_db="legacy",
        cli_dir=str(tmp_path),
        logger=logging.getLogger("tests.nodb.climate.artifacts.atlas.invalid_env"),
        watershed_instance=SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    assert service.download_noaa_atlas14_intensity(climate) is None
    assert attempts == [1, 2, 3]
    assert sleeps == [1.0, 2.0]
    assert [call["timeout"] for call in kwargs_calls] == [30, 30, 30]
