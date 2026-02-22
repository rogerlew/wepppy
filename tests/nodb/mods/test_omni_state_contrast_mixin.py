from __future__ import annotations

import json as jsonlib
import logging
import os
import shutil
import sys
import types
from contextlib import contextmanager
from pathlib import Path

import pytest

from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.mods.omni.omni_state_contrast_mixin import OmniStateContrastMixin

pytestmark = pytest.mark.unit


@pytest.fixture()
def omni_module_stub(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    sleep_calls: list[float] = []

    time_stub = types.SimpleNamespace(
        time=lambda: 123.0,
        sleep=lambda seconds: sleep_calls.append(float(seconds)),
    )

    module = types.ModuleType("wepppy.nodb.mods.omni.omni")
    module.OMNI_REL_DIR = "_pups/omni"
    # Stub coverage: the OmniStateContrastMixin proxy layer reads these attributes
    # from `wepppy.nodb.mods.omni.omni` (via _OmniAttrProxy).
    module.os = os
    module.shutil = shutil
    module.json = jsonlib
    module.time = time_stub
    module._exists = lambda path: os.path.exists(path)
    module._join = lambda *parts: os.path.join(*parts)
    module.isdir = lambda path: os.path.isdir(path)
    module._sleep_calls = sleep_calls

    monkeypatch.setitem(sys.modules, "wepppy.nodb.mods.omni.omni", module)
    import wepppy.nodb.mods.omni as omni_pkg

    monkeypatch.setattr(omni_pkg, "omni", module, raising=False)
    return module


class _OmniContrastDummy(OmniStateContrastMixin):
    _instance: "_OmniContrastDummy | None" = None

    def __init__(self, wd: Path, *, logger_name: str) -> None:
        self.wd = str(wd)
        self.runid = "run-123"
        self.omni_dir = str(wd / "omni")
        self.logger = logging.getLogger(logger_name)
        self._contrast_dependency_tree: dict[str, dict] = {"stale": {"signature": "old"}}
        self._lock_calls = 0
        self._fail_first_lock = True

    @classmethod
    def getInstance(cls, wd: str) -> "_OmniContrastDummy":
        assert cls._instance is not None
        assert wd == cls._instance.wd
        return cls._instance

    @contextmanager
    def locked(self):
        self._lock_calls += 1
        if self._fail_first_lock:
            self._fail_first_lock = False
            raise NoDbAlreadyLockedError("lock busy")
        yield


def test_update_contrast_dependency_tree_retries_once_then_updates(
    tmp_path: Path,
    omni_module_stub: types.ModuleType,
) -> None:
    omni = _OmniContrastDummy(tmp_path, logger_name="tests.omni_state_contrast_mixin.update")
    type(omni)._instance = omni

    omni._update_contrast_dependency_tree(
        "fresh",
        {"signature": "new"},
        max_tries=2,
        delay=0.0,
    )

    assert omni._lock_calls == 2
    assert omni._contrast_dependency_tree["fresh"] == {"signature": "new"}
    assert omni_module_stub._sleep_calls == [0.0]


def test_remove_contrast_dependency_entry_retries_once_then_removes(
    tmp_path: Path,
    omni_module_stub: types.ModuleType,
) -> None:
    omni = _OmniContrastDummy(tmp_path, logger_name="tests.omni_state_contrast_mixin.remove")
    type(omni)._instance = omni
    omni._contrast_dependency_tree = {"drop": {"signature": "stale"}, "keep": {"signature": "ok"}}

    omni._remove_contrast_dependency_entry(
        "drop",
        max_tries=2,
        delay=0.0,
    )

    assert omni._lock_calls == 2
    assert omni._contrast_dependency_tree == {"keep": {"signature": "ok"}}
    assert omni_module_stub._sleep_calls == [0.0]


def test_write_contrast_run_status_swallows_oserror_and_logs_debug(
    tmp_path: Path,
    omni_module_stub: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import wepppy.nodb.mods.omni.omni_state_contrast_mixin as mixin_module

    omni = _OmniContrastDummy(tmp_path, logger_name="tests.omni_state_contrast_mixin.write_status")
    type(omni)._instance = omni

    def _raise_open(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(mixin_module, "open", _raise_open, raising=False)

    with caplog.at_level(logging.DEBUG, logger=omni.logger.name):
        omni._write_contrast_run_status(1, "contrast", "started", job_id="job-1")

    assert "Failed to write contrast status" in caplog.text


def test_clear_contrast_run_status_swallows_oserror_and_logs_debug(
    tmp_path: Path,
    omni_module_stub: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    omni = _OmniContrastDummy(tmp_path, logger_name="tests.omni_state_contrast_mixin.clear_status")
    type(omni)._instance = omni

    status_path = Path(omni._contrast_run_status_path(1))
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(jsonlib.dumps({"ok": True}), encoding="utf-8")

    monkeypatch.setattr(omni_module_stub.os, "remove", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("busy")))

    with caplog.at_level(logging.DEBUG, logger=omni.logger.name):
        omni._clear_contrast_run_status(1)

    assert "Failed to remove contrast status" in caplog.text
