from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path

import pytest

import wepppy.nodb.core.wepp as wepp_module
from wepppy.nodb.core.wepp import Wepp

pytestmark = pytest.mark.unit


def test_remove_pmet_removes_pmetpara_file(tmp_path: Path) -> None:
    wepp = Wepp.__new__(Wepp)
    wepp.wd = str(tmp_path)

    runs_dir = Path(wepp.runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    pmetpara = runs_dir / "pmetpara.txt"
    pmetpara.write_text("pmet\n", encoding="utf-8")

    wepp._remove_pmet()

    assert not pmetpara.exists()


def test_init_reads_baseflow_threshold_from_baseflow_opts_section(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    float_calls: list[tuple[str, str]] = []

    def _fake_nodb_init(
        self: Wepp,
        wd_arg: str,
        cfg_fn: str,
        run_group: str | None = None,
        group_name: str | None = None,
    ) -> None:
        self.wd = wd_arg
        self.logger = logging.getLogger("tests.wepp.init_baseflow_opts")
        self._logger = self.logger
        self._mods = []

    @contextmanager
    def _fake_locked():
        yield

    monkeypatch.setattr(wepp_module.NoDbBase, "__init__", _fake_nodb_init)
    monkeypatch.setattr(Wepp, "locked", lambda self: _fake_locked())
    monkeypatch.setattr(Wepp, "clean", lambda self: None)
    monkeypatch.setattr(Wepp, "_mint_default_frost_file", lambda self: None)
    monkeypatch.setattr(
        Wepp,
        "config_get_float",
        lambda self, section, option, default=None: float_calls.append((section, option)) or 1.0,
    )
    monkeypatch.setattr(
        Wepp,
        "config_get_int",
        lambda self, section, option, default=None: default if default is not None else 1,
    )
    monkeypatch.setattr(
        Wepp,
        "config_get_bool",
        lambda self, section, option, default=False: bool(default),
    )
    monkeypatch.setattr(Wepp, "config_get_str", lambda self, section, option, default="wepp": str(default))
    monkeypatch.setattr(Wepp, "config_get_path", lambda self, section, option, default=None: default)
    monkeypatch.setattr(
        Wepp,
        "config_get_list",
        lambda self, section, option, default=None: [] if default is None else list(default),
    )

    _ = Wepp(str(wd), "dummy.cfg")

    assert ("baseflow_opts", "bfthreshold") in float_calls
    assert ("baseflows_opts", "bfthreshold") not in float_calls
