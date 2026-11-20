from __future__ import annotations

import contextlib
import logging
import types
from pathlib import Path

import pytest

from wepppy.nodb.core.climate import Climate, ClimateMode, ClimateSpatialMode

pytestmark = pytest.mark.nodb


def _write_minimal_cli(path: Path) -> None:
    """Write a small but CLIGEN-parsable CLI file to ``path``."""
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
                "  1  1 1980   0.0  0.00  0.0    0.0  19.4  11.5  267  2.7   295  13.4",
                "  2  1 1980   0.0  0.00  0.0    0.0  20.5  11.0  291  2.3     5  12.7",
                "  1  1 1981   0.0  0.00  0.0    0.0  19.4  11.5  267  2.7   295  13.4",
                "  2  1 1981   0.0  0.00  0.0    0.0  20.5  11.0  291  2.3     5  12.7",
                "",
            ]
        )
    )


def test_calendar_start_year_infers_from_cli_when_unset(tmp_path: Path) -> None:
    cli_dir = tmp_path / "climate"
    cli_dir.mkdir()
    cli_path = cli_dir / "user.cli"
    _write_minimal_cli(cli_path)

    climate = Climate.__new__(Climate)
    climate.logger = logging.getLogger("test")
    climate.wd = str(tmp_path)
    climate._observed_start_year = ""
    climate._future_start_year = ""
    climate.cli_fn = cli_path.name

    assert climate.calendar_start_year == 1980


@pytest.mark.parametrize(('old_mode', 'new_mode'), [
    (ClimateMode.UserDefinedSingleStorm, ClimateMode.UserDefined),
    (ClimateMode.UserDefined, ClimateMode.UserDefinedSingleStorm),
])
def test_set_user_defined_cli_refreshes_cli_parquet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, old_mode, new_mode) -> None:
    cli_dir = tmp_path / "climate"
    cli_dir.mkdir()
    cli_path = cli_dir / "user.cli"
    _write_minimal_cli(cli_path)
    if new_mode == ClimateMode.UserDefinedSingleStorm:
        cli_path.write_text('\n'.join(cli_path.read_text().splitlines()[:16]) + '\n')

    climate = Climate.__new__(Climate)
    climate.logger = logging.getLogger("test")
    climate.wd = str(tmp_path)
    climate._climate_mode = old_mode
    climate._ss_batch_storms = [{'ss_batch_key': 'older-storm'}]
    climate._climate_spatialmode = ClimateSpatialMode.Single

    committed = []

    @contextlib.contextmanager
    def capture_commit():
        yield
        committed.append((
            climate.climate_mode, climate.cli_fn, climate._catalog_id, climate.ss_batch_storms,
        ))

    climate.locked = capture_commit

    climate._prism_revision = lambda *args, **kwargs: None

    calls: dict[str, int] = {"export": 0, "freq": 0, "atlas": 0}

    def _export_cli_parquet():
        calls["export"] += 1
        return cli_dir / "wepp_cli.parquet"

    climate._export_cli_parquet = _export_cli_parquet
    climate._export_cli_precip_frequency_csv = lambda *_args, **_kwargs: calls.__setitem__("freq", calls["freq"] + 1)
    climate._download_noaa_atlas14_intensity = lambda *_args, **_kwargs: calls.__setitem__(
        "atlas", calls["atlas"] + 1
    )

    # Keep the test fast (the implementation includes a 1s sleep to ensure writes flush).
    monkeypatch.setattr("wepppy.nodb.core.climate.time.sleep", lambda *_args, **_kwargs: None)

    # Avoid Redis access inside the timestamp block.
    monkeypatch.setattr(
        "wepppy.nodb.core.climate.RedisPrep.getInstance",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )

    climate.set_user_defined_cli(cli_path.name)

    assert committed == [(new_mode, cli_path.name, "user_defined_cli", None)]
    assert calls["export"] == 1
    assert climate.climate_mode == new_mode
    assert climate.active_uploaded_cli_mode == new_mode
    assert climate.ss_batch_storms is None
    assert climate.cli_fn == cli_path.name


def test_set_user_defined_cli_delegates_station_meta_builder(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cli_dir = tmp_path / "climate"
    cli_dir.mkdir()
    cli_path = cli_dir / "user.cli"
    _write_minimal_cli(cli_path)

    climate = Climate.__new__(Climate)
    climate.logger = logging.getLogger("test")
    climate.wd = str(tmp_path)
    climate._climate_mode = ClimateMode.UserDefined
    climate._climate_spatialmode = ClimateSpatialMode.Single

    @contextlib.contextmanager
    def _noop_locked(_self, *args, **kwargs):
        yield

    climate.locked = types.MethodType(_noop_locked, climate)
    climate._prism_revision = lambda *args, **kwargs: None
    climate._export_cli_parquet = lambda: cli_dir / "wepp_cli.parquet"
    climate._export_cli_precip_frequency_csv = lambda *_args, **_kwargs: None
    climate._download_noaa_atlas14_intensity = lambda *_args, **_kwargs: None

    monkeypatch.setattr(
        "wepppy.nodb.core.climate.RedisPrep.getInstance",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )

    sentinel_meta = object()
    captured: dict[str, object] = {}

    def _fake_build_station_meta_from_cli(*, cli, cli_filename, cli_dir, monthlies):
        captured["cli"] = cli
        captured["cli_filename"] = cli_filename
        captured["cli_dir"] = cli_dir
        captured["monthlies"] = monthlies
        return sentinel_meta

    monkeypatch.setattr(
        "wepppy.nodb.core.climate._CLIMATE_USER_DEFINED_STATION_META_SERVICE.build_station_meta_from_cli",
        _fake_build_station_meta_from_cli,
    )

    climate.set_user_defined_cli(cli_path.name)

    assert climate._user_station_meta is sentinel_meta
    assert captured["cli_filename"] == cli_path.name
    assert captured["cli_dir"] == str(cli_dir)
    assert isinstance(captured["monthlies"], dict)


def test_active_upload_display_and_repair_do_not_share_an_implicit_write(tmp_path):
    directory = tmp_path / 'climate'
    directory.mkdir()
    active = directory / 'user.cli'
    _write_minimal_cli(active)
    climate = Climate.__new__(Climate)
    climate.wd = str(tmp_path)
    climate.cli_fn = active.name
    climate._orig_cli_fn = '/original-run/climate/user.cli'
    climate._user_station_meta = object()
    climate._climate_mode = ClimateMode.UserDefinedSingleStorm
    climate._ss_batch_storms = [{'ss_batch_key': 'obsolete'}]

    assert climate.active_uploaded_cli_mode == ClimateMode.UserDefined
    assert climate.climate_mode == ClimateMode.UserDefinedSingleStorm
    assert climate.is_single_storm

    writes = []

    @contextlib.contextmanager
    def record_write():
        writes.append('lock')
        yield

    climate.locked = record_write
    climate.reconcile_uploaded_cli_mode()
    assert writes == ['lock']
    assert climate.climate_mode == ClimateMode.UserDefined
    assert not climate.is_single_storm
    assert climate.ss_batch_storms is None

    active.write_text('\n'.join(active.read_text().splitlines()[:16]) + '\n')
    assert climate.active_uploaded_cli_mode == ClimateMode.UserDefinedSingleStorm


@pytest.mark.parametrize('invalid', ['no-days', 'non-numeric', 'invalid-date', 'breakpoints', 'without-provenance', 'external-provenance', 'symlink'])
def test_active_upload_requires_parsed_run_owned_content_and_provenance(tmp_path, invalid):
    directory = tmp_path / 'climate'
    directory.mkdir()
    active = directory / 'user.cli'
    _write_minimal_cli(active)
    climate = Climate.__new__(Climate)
    climate.wd = str(tmp_path)
    climate.cli_fn = active.name
    climate._orig_cli_fn = str(active)
    climate._user_station_meta = object()
    climate._climate_mode = ClimateMode.UserDefined
    lines = active.read_text().splitlines()
    if invalid == 'no-days':
        active.write_text('\n'.join(lines[:15]) + '\n')
    elif invalid == 'non-numeric':
        active.write_text('\n'.join(lines[:15] + [lines[15].replace('19.4', 'bad')]) + '\n')
    elif invalid == 'invalid-date':
        active.write_text('\n'.join(lines[:15] + [lines[15].replace('1  1 1980', '31  2 1980')]) + '\n')
    elif invalid == 'breakpoints':
        lines[1] = '1 1 0'
        lines[13] = 'da mo year nbrkpt tmax tmin rad w-vl w-dir tdew'
        lines[15] = '1 1 1980 1 19.4 11.5 267 2.7 295 13.4'
        active.write_text('\n'.join(lines[:17]) + '\n')
    elif invalid == 'without-provenance':
        climate._user_station_meta = None
    elif invalid == 'external-provenance':
        climate._orig_cli_fn = '/observed/database/user.cli'
    else:
        elsewhere = tmp_path / 'elsewhere.cli'
        active.rename(elsewhere)
        active.symlink_to(elsewhere)

    assert climate.active_uploaded_cli_mode is None
    assert climate.climate_mode == ClimateMode.UserDefined

    if invalid not in ('without-provenance', 'external-provenance'):
        climate._climate_mode = ClimateMode.UserDefinedSingleStorm
        with pytest.raises(ValueError, match='active uploaded climate is missing or invalid'):
            climate.reconcile_uploaded_cli_mode()
