from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
import types

import pytest

from wepppy.runtime_paths.errors import NoDirError

pytestmark = pytest.mark.unit


class _DummyAsh:
    def __init__(self, wd: Path) -> None:
        self.wd = str(wd)
        self.ash_dir = str(wd / "ash")
        Path(self.ash_dir).mkdir(parents=True, exist_ok=True)
        (Path(self.ash_dir) / "post").mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("tests.ash.run_ash")
        self.model = "multi"
        self.config_stem = "cfg"
        self._run_wind_transport = False
        self._ash_load_fn = None
        self._ash_type_map_fn = None
        self._field_black_ash_bulkdensity = 1.0
        self._field_white_ash_bulkdensity = 1.0
        self._black_ash_bulkdensity = 1.0
        self._white_ash_bulkdensity = 1.0

    class _NoopLock:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def locked(self):
        return self._NoopLock()

    @property
    def run_wind_transport(self) -> bool:
        return self._run_wind_transport

    @property
    def ash_load_fn(self):
        return None

    @property
    def ash_type_map_fn(self):
        return None

    @property
    def field_white_ash_bulkdensity(self) -> float:
        return self._field_white_ash_bulkdensity

    @property
    def field_black_ash_bulkdensity(self) -> float:
        return self._field_black_ash_bulkdensity

    @property
    def white_ash_bulkdensity(self) -> float:
        return self._white_ash_bulkdensity

    @property
    def black_ash_bulkdensity(self) -> float:
        return self._black_ash_bulkdensity


@pytest.fixture()
def ash_module():
    import wepppy.nodb.mods.ash_transport as ash_pkg
    import wepppy.nodb.mods.ash_transport.ash as ash_module

    return ash_pkg, ash_module


@pytest.fixture()
def ash_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ash_module):
    ash_pkg, ash_module_impl = ash_module

    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    dummy_ash = _DummyAsh(wd)

    class DummyWatershed:
        _subs_summary = []

        @staticmethod
        def translator_factory():
            return object()

    monkeypatch.setattr(ash_module_impl.Watershed, "getInstance", lambda _wd: DummyWatershed())
    monkeypatch.setattr(ash_module_impl.Wepp, "getInstance", lambda _wd: types.SimpleNamespace(output_dir=str(wd / "wepp" / "output")))
    monkeypatch.setattr(ash_module_impl.Landuse, "getInstance", lambda _wd: types.SimpleNamespace())

    post_calls = []

    class DummyAshPost:
        def __init__(self, _wd: str, _cfg_fn: str):
            post_calls.append(("init", _wd, _cfg_fn))

        @classmethod
        def getInstance(cls, _wd: str):
            post_calls.append(("get", _wd))
            return cls(_wd, "cfg.cfg")

        def run_post(self) -> None:
            post_calls.append(("run",))

    monkeypatch.setattr(ash_pkg, "AshPost", DummyAshPost)

    class DummyPrep:
        def timestamp(self, _key) -> None:
            return None

    class DummyRedisPrep:
        @staticmethod
        def getInstance(_wd: str) -> DummyPrep:
            return DummyPrep()

    monkeypatch.setattr(ash_module_impl, "RedisPrep", DummyRedisPrep)

    return ash_module_impl, dummy_ash, wd, post_calls


def test_run_ash_uses_projection_for_cli_inside_wd(ash_runtime, monkeypatch: pytest.MonkeyPatch):
    ash_module, dummy_ash, wd, post_calls = ash_runtime

    climate_cli_rel = "climate/inputs/example.cli"
    projected_cli = str(wd / ".nodir" / "mount" / "climate" / "inputs" / "example.cli")

    class DummyClimate:
        cli_path = str(wd / climate_cli_rel)
        input_years = 3

    monkeypatch.setattr(ash_module.Climate, "getInstance", lambda _wd: DummyClimate())

    cli_reads = []

    class DummyClimateFile:
        def __init__(self, path: str):
            cli_reads.append(path)

        def as_dataframe(self, calc_peak_intensities: bool = False):
            assert calc_peak_intensities is False
            return object()

    monkeypatch.setattr(ash_module, "ClimateFile", DummyClimateFile)

    projection_calls = []

    @contextmanager
    def _with_input_file_path(wd_arg: str, rel: str, *, purpose: str):
        projection_calls.append((wd_arg, rel, purpose))
        yield projected_cli

    monkeypatch.setattr(ash_module, "with_input_file_path", _with_input_file_path)

    ash_module.Ash.run_ash(dummy_ash, fire_date="8/4", ini_white_ash_depth_mm=3.0, ini_black_ash_depth_mm=5.0)

    assert projection_calls == [(str(wd), climate_cli_rel, "ash-run-climate-cli")]
    assert cli_reads == [projected_cli]
    assert ("run",) in post_calls


def test_run_ash_propagates_projection_nodir_errors(ash_runtime, monkeypatch: pytest.MonkeyPatch):
    ash_module, dummy_ash, wd, _post_calls = ash_runtime

    class DummyClimate:
        cli_path = str(wd / "climate" / "inputs" / "example.cli")
        input_years = 3

    monkeypatch.setattr(ash_module.Climate, "getInstance", lambda _wd: DummyClimate())

    class DummyClimateFile:
        def __init__(self, path: str):
            self.path = path

        def as_dataframe(self, calc_peak_intensities: bool = False):
            return object()

    monkeypatch.setattr(ash_module, "ClimateFile", DummyClimateFile)

    @contextmanager
    def _raise_projection(*_args, **_kwargs):
        raise NoDirError(http_status=503, code="NODIR_LOCKED", message="projection locked")
        yield

    monkeypatch.setattr(ash_module, "with_input_file_path", _raise_projection)

    with pytest.raises(NoDirError) as exc_info:
        ash_module.Ash.run_ash(dummy_ash, fire_date="8/4", ini_white_ash_depth_mm=3.0, ini_black_ash_depth_mm=5.0)

    assert exc_info.value.code == "NODIR_LOCKED"


def test_run_ash_uses_direct_cli_when_path_outside_wd(ash_runtime, monkeypatch: pytest.MonkeyPatch):
    ash_module, dummy_ash, _wd, post_calls = ash_runtime

    outside_cli_path = "/tmp/external/example.cli"

    class DummyClimate:
        cli_path = outside_cli_path
        input_years = 3

    monkeypatch.setattr(ash_module.Climate, "getInstance", lambda _wd: DummyClimate())

    cli_reads = []

    class DummyClimateFile:
        def __init__(self, path: str):
            cli_reads.append(path)

        def as_dataframe(self, calc_peak_intensities: bool = False):
            assert calc_peak_intensities is False
            return object()

    monkeypatch.setattr(ash_module, "ClimateFile", DummyClimateFile)

    @contextmanager
    def _unexpected_projection(*_args, **_kwargs):
        raise AssertionError("with_input_file_path should not be used for outside-wd cli path")
        yield

    monkeypatch.setattr(ash_module, "with_input_file_path", _unexpected_projection)

    ash_module.Ash.run_ash(dummy_ash, fire_date="8/4", ini_white_ash_depth_mm=3.0, ini_black_ash_depth_mm=5.0)

    assert cli_reads == [outside_cli_path]
    assert ("run",) in post_calls
