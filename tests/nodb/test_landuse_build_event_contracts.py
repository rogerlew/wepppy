from __future__ import annotations

from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.core.landuse import Landuse, LanduseMode

pytestmark = pytest.mark.unit


class _LoggerStub:
    def info(self, *_args, **_kwargs) -> None:
        return None

    def debug(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None

    def error(self, *_args, **_kwargs) -> None:
        return None


def test_build_landuse_selection_pair_is_persisted_in_one_lock_scope() -> None:
    landuse = Landuse.__new__(Landuse)
    landuse._mode = LanduseMode.Gridded
    landuse._nlcd_db = "nlcd/2019"
    lock_entries: list[str] = []

    @contextmanager
    def locked():
        lock_entries.append("enter")
        yield
        lock_entries.append("exit")

    landuse.locked = locked
    landuse.validate_landuse_mode_for_mofe = lambda mode=None: None

    landuse.apply_build_landuse_selection_updates(
        nlcd_db="eu/CORINE_LandCover/2018",
        mode=LanduseMode.Single,
    )

    assert landuse._nlcd_db == "eu/CORINE_LandCover/2018"
    assert landuse._mode == LanduseMode.Single
    assert lock_entries == ["enter", "exit"]


def test_stored_australia_runtime_token_overrides_incongruent_landuse_locales(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _AustralianDispatch(Exception):
        pass

    class _LanduseStub:
        wd = str(tmp_path)
        lc_dir = str(tmp_path / "landuse")
        _mode = LanduseMode.Gridded
        locales = ["us"]
        mods: list[str] = []
        multi_ofe = False
        watershed_instance = SimpleNamespace(is_abstracted=True)
        logger = _LoggerStub()

        @staticmethod
        def islocked() -> bool:
            return False

        @staticmethod
        def validate_landuse_mode_for_mofe(mode=None) -> None:
            return None

        @staticmethod
        def clean() -> None:
            return None

        @staticmethod
        def locked():
            return nullcontext()

        @staticmethod
        def _build_lu10v5ua() -> None:
            raise _AustralianDispatch()

        @staticmethod
        def _build_NLCD(*_args, **_kwargs) -> None:
            pytest.fail("used incongruent Continental-US landuse dispatch")

    monkeypatch.setattr(
        "wepppy.nodb.project_config_capabilities.resolve_run_capability_authority",
        lambda _landuse: SimpleNamespace(graph=object(), runtime_tokens=("au",)),
    )

    with pytest.raises(_AustralianDispatch):
        Landuse.build(_LanduseStub())


def test_build_multi_ofe_rejects_single_landuse_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(run_dir)
    landuse._mode = LanduseMode.Single
    landuse._mods = []
    landuse.logger = _LoggerStub()
    landuse.locked = lambda: nullcontext()
    landuse.islocked = lambda: False
    call_log: list[str] = []

    def _build_single_selection() -> None:
        call_log.append("build_single_selection")
        landuse.domlc_d = {"101": "42"}

    def _build_multiple_ofe() -> None:
        call_log.append(f"build_multiple_ofe:domlc_mofe_d={landuse.domlc_mofe_d!r}")
        landuse.domlc_mofe_d = {"101": {"1": "42"}}

    landuse._build_single_selection = _build_single_selection
    landuse._build_multiple_ofe = _build_multiple_ofe
    landuse.build_managements = lambda: call_log.append("build_managements")
    landuse.set_cover_defaults = lambda: call_log.append("set_cover_defaults")
    landuse._build_fractionals = lambda: call_log.append("build_fractionals")
    landuse.trigger = (
        lambda event: call_log.append(
            f"trigger:{event.name}:defer={getattr(landuse, '_defer_disturbed_management_rebuild', False)}"
        )
    )

    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: SimpleNamespace(is_abstracted=True)),
    )
    monkeypatch.setattr(
        Landuse,
        "wepp_instance",
        property(lambda _self: SimpleNamespace(_multi_ofe=True)),
    )
    monkeypatch.setattr(
        "wepppy.nodb.core.landuse.RedisPrep.getInstance",
        lambda _wd: (_ for _ in ()).throw(FileNotFoundError()),
    )

    with pytest.raises(ValueError, match="MOFE projects require a gridded landuse map"):
        landuse.build(retrieve_nlcd=False)

    assert call_log == []


def test_build_single_ofe_keeps_management_build_before_and_after_domlc_trigger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(run_dir)
    landuse._mode = LanduseMode.Single
    landuse._mods = []
    landuse.logger = _LoggerStub()
    landuse.locked = lambda: nullcontext()
    landuse.islocked = lambda: False
    landuse.config_get_raw = (
        lambda section, option, default=None: False
        if (section, option) == ("config", "flattened")
        else ["us"]
        if (section, option) == ("general", "locales")
        else default
    )
    landuse.config_get_list = (
        lambda section, option, default=None: ["us"]
        if (section, option) == ("general", "locales")
        else default
    )

    call_log: list[str] = []
    get_instance_calls: list[str] = []

    def _build_single_selection() -> None:
        call_log.append("build_single_selection")
        landuse.domlc_d = {"101": "42"}

    landuse._build_single_selection = _build_single_selection
    landuse.build_managements = lambda: call_log.append("build_managements")
    landuse.set_cover_defaults = lambda: call_log.append("set_cover_defaults")
    landuse._build_fractionals = lambda: call_log.append("build_fractionals")
    landuse.trigger = (
        lambda event: call_log.append(
            f"trigger:{event.name}:defer={getattr(landuse, '_defer_disturbed_management_rebuild', False)}"
        )
    )

    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: SimpleNamespace(is_abstracted=True)),
    )
    monkeypatch.setattr(
        Landuse,
        "wepp_instance",
        property(lambda _self: SimpleNamespace(_multi_ofe=False)),
    )
    monkeypatch.setattr(
        Landuse,
        "getInstance",
        classmethod(lambda cls, wd: get_instance_calls.append(str(wd)) or landuse),
    )
    monkeypatch.setattr(
        "wepppy.nodb.core.landuse.RedisPrep.getInstance",
        lambda _wd: (_ for _ in ()).throw(FileNotFoundError()),
    )

    landuse.build(retrieve_nlcd=False)

    assert call_log == [
        "build_single_selection",
        "build_managements",
        "trigger:LANDUSE_DOMLC_COMPLETE:defer=True",
        "build_managements",
        "set_cover_defaults",
        "build_fractionals",
    ]
    assert get_instance_calls == [str(run_dir), str(run_dir), str(run_dir)]
    assert landuse._defer_disturbed_management_rebuild is False
