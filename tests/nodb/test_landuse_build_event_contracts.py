from __future__ import annotations

from contextlib import nullcontext
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


def test_build_multi_ofe_runs_single_management_pass_after_domlc_trigger(
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
    get_instance_calls: list[str] = []

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
        "build_multiple_ofe:domlc_mofe_d=None",
        "trigger:LANDUSE_DOMLC_COMPLETE:defer=True",
        "build_managements",
        "set_cover_defaults",
        "build_fractionals",
    ]
    assert get_instance_calls == [str(run_dir), str(run_dir), str(run_dir)]
    assert landuse._defer_disturbed_management_rebuild is False


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
