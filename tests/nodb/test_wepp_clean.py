from __future__ import annotations

import errno
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.core.wepp as wepp_module
from wepppy.nodb.core.wepp import ClimateMode, Wepp

pytestmark = pytest.mark.unit

_RETRYABLE_ERRNOS = [errno.EBUSY, errno.ENOTEMPTY, errno.EACCES]
if hasattr(errno, "ESTALE"):
    _RETRYABLE_ERRNOS.append(errno.ESTALE)


class _DummyLogger:
    def warning(self, *_args: object, **_kwargs: object) -> None:
        return None

    def error(self, *_args: object, **_kwargs: object) -> None:
        return None

    def info(self, *_args: object, **_kwargs: object) -> None:
        return None


@pytest.fixture(autouse=True)
def _disable_cleanup_backoff_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wepp_module, "sleep", lambda _seconds: None)


def _make_detached_wepp(tmp_path: Path) -> Wepp:
    wd = tmp_path / "ab" / "ab-run"
    wd.mkdir(parents=True, exist_ok=True)
    wepp = object.__new__(Wepp)
    wepp.wd = str(wd)
    wepp.logger = _DummyLogger()
    return wepp


def _create_dirty_dirs(wepp: Wepp) -> None:
    for path in (
        Path(wepp.runs_dir),
        Path(wepp.output_dir),
        Path(wepp.plot_dir),
        Path(wepp.stats_dir),
        Path(wepp.fp_runs_dir),
        Path(wepp.fp_output_dir),
    ):
        path.mkdir(parents=True, exist_ok=True)
        (path / "old.txt").write_text("stale", encoding="utf-8")


def _set_climate(
    monkeypatch: pytest.MonkeyPatch,
    *,
    mode: ClimateMode | None,
    storms: list[dict[str, str]] | None = None,
) -> None:
    monkeypatch.setattr(
        Wepp,
        "climate_instance",
        property(
            lambda _self: SimpleNamespace(
                climate_mode=mode,
                ss_batch_storms=list(storms or []),
            )
        ),
    )


def test_clean_uses_rename_fallback_when_rmtree_stays_busy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wepp = _make_detached_wepp(tmp_path)
    _create_dirty_dirs(wepp)
    _set_climate(monkeypatch, mode=None)

    real_rmtree = shutil.rmtree

    def _flaky_rmtree(path: str) -> None:
        path_text = str(path)
        if path_text == wepp.runs_dir:
            raise OSError(errno.EBUSY, "Device or resource busy")
        if path_text.startswith(f"{wepp.runs_dir}.stale."):
            raise OSError(errno.EBUSY, "stale handle still open")
        real_rmtree(path)

    monkeypatch.setattr("wepppy.nodb.core.wepp.shutil.rmtree", _flaky_rmtree)

    wepp.clean()

    for path in (
        Path(wepp.runs_dir),
        Path(wepp.output_dir),
        Path(wepp.plot_dir),
        Path(wepp.stats_dir),
        Path(wepp.fp_runs_dir),
        Path(wepp.fp_output_dir),
    ):
        assert path.exists()
        assert not (path / "old.txt").exists()

    stale_dirs = list(Path(wepp.wepp_dir).glob("runs.stale.*"))
    assert len(stale_dirs) == 1


def test_clean_raises_runtime_error_when_rename_fallback_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wepp = _make_detached_wepp(tmp_path)
    Path(wepp.runs_dir).mkdir(parents=True, exist_ok=True)
    _set_climate(monkeypatch, mode=None)

    def _always_busy_rmtree(_path: str) -> None:
        raise OSError(errno.EBUSY, "Device or resource busy")

    def _rename_fails(_src: str, _dst: str) -> None:
        raise OSError(errno.EBUSY, "rename failed")

    monkeypatch.setattr("wepppy.nodb.core.wepp.shutil.rmtree", _always_busy_rmtree)
    monkeypatch.setattr("wepppy.nodb.core.wepp.os.replace", _rename_fails)

    with pytest.raises(RuntimeError, match="Failed to clean directory"):
        wepp.clean()


def test_clean_fails_fast_on_non_retryable_cleanup_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wepp = _make_detached_wepp(tmp_path)
    Path(wepp.runs_dir).mkdir(parents=True, exist_ok=True)
    _set_climate(monkeypatch, mode=None)

    replace_calls: list[tuple[str, str]] = []

    def _non_retryable_rmtree(_path: str) -> None:
        raise OSError(errno.EIO, "I/O error")

    def _record_replace(src: str, dst: str) -> None:
        replace_calls.append((src, dst))

    monkeypatch.setattr("wepppy.nodb.core.wepp.shutil.rmtree", _non_retryable_rmtree)
    monkeypatch.setattr("wepppy.nodb.core.wepp.os.replace", _record_replace)

    with pytest.raises(RuntimeError, match="Failed to clean directory"):
        wepp.clean()

    assert replace_calls == []


def test_clean_retries_then_succeeds_without_rename_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wepp = _make_detached_wepp(tmp_path)
    _create_dirty_dirs(wepp)
    _set_climate(monkeypatch, mode=None)

    real_rmtree = shutil.rmtree
    runs_rmtree_calls = {"count": 0}
    replace_calls: list[tuple[str, str]] = []

    def _rmtree_one_retry(path: str) -> None:
        path_text = str(path)
        if path_text == wepp.runs_dir:
            runs_rmtree_calls["count"] += 1
            if runs_rmtree_calls["count"] == 1:
                raise OSError(errno.EBUSY, "Device or resource busy")
        real_rmtree(path)

    def _record_replace(src: str, dst: str) -> None:
        replace_calls.append((src, dst))

    monkeypatch.setattr("wepppy.nodb.core.wepp.shutil.rmtree", _rmtree_one_retry)
    monkeypatch.setattr("wepppy.nodb.core.wepp.os.replace", _record_replace)

    wepp.clean()

    assert runs_rmtree_calls["count"] == 2
    assert replace_calls == []
    assert list(Path(wepp.wepp_dir).glob("runs.stale.*")) == []


def test_clean_handles_rmtree_filenotfound_race(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wepp = _make_detached_wepp(tmp_path)
    _create_dirty_dirs(wepp)
    _set_climate(monkeypatch, mode=None)

    real_rmtree = shutil.rmtree

    def _rmtree_with_disappearing_dir(path: str) -> None:
        if str(path) == wepp.runs_dir:
            real_rmtree(path)
            raise FileNotFoundError(path)
        real_rmtree(path)

    monkeypatch.setattr("wepppy.nodb.core.wepp.shutil.rmtree", _rmtree_with_disappearing_dir)

    wepp.clean()

    assert Path(wepp.runs_dir).exists()
    assert not Path(wepp.runs_dir, "old.txt").exists()
    assert list(Path(wepp.wepp_dir).glob("runs.stale.*")) == []


def test_clean_handles_replace_filenotfound_race(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wepp = _make_detached_wepp(tmp_path)
    _create_dirty_dirs(wepp)
    _set_climate(monkeypatch, mode=None)

    real_rmtree = shutil.rmtree
    real_replace = os.replace

    def _always_busy_runs_dir(path: str) -> None:
        if str(path) == wepp.runs_dir:
            raise OSError(errno.EBUSY, "Device or resource busy")
        real_rmtree(path)

    def _replace_disappearing_src(src: str, dst: str) -> None:
        if src == wepp.runs_dir:
            if Path(src).exists():
                real_rmtree(src)
            raise FileNotFoundError(src)
        real_replace(src, dst)

    monkeypatch.setattr("wepppy.nodb.core.wepp.shutil.rmtree", _always_busy_runs_dir)
    monkeypatch.setattr("wepppy.nodb.core.wepp.os.replace", _replace_disappearing_src)

    wepp.clean()

    assert Path(wepp.runs_dir).exists()
    assert not Path(wepp.runs_dir, "old.txt").exists()
    assert list(Path(wepp.wepp_dir).glob("runs.stale.*")) == []


def test_clean_propagates_makedirs_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wepp = _make_detached_wepp(tmp_path)
    _create_dirty_dirs(wepp)
    _set_climate(monkeypatch, mode=None)

    real_makedirs = os.makedirs

    def _failing_makedirs(path: str, mode: int = 0o777, exist_ok: bool = False) -> None:
        if str(path) == wepp.runs_dir:
            raise OSError(errno.EACCES, "Permission denied")
        real_makedirs(path, mode=mode, exist_ok=exist_ok)

    monkeypatch.setattr("wepppy.nodb.core.wepp.os.makedirs", _failing_makedirs)

    with pytest.raises(OSError) as exc_info:
        wepp.clean()

    assert exc_info.value.errno == errno.EACCES


def test_clean_single_storm_batch_creates_ss_batch_output_dirs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wepp = _make_detached_wepp(tmp_path)
    _create_dirty_dirs(wepp)
    _set_climate(
        monkeypatch,
        mode=ClimateMode.SingleStormBatch,
        storms=[
            {"ss_batch_key": "storm-a"},
            {"ss_batch_key": "storm-b"},
        ],
    )

    wepp.clean()

    assert Path(wepp.output_dir, "storm-a").is_dir()
    assert Path(wepp.output_dir, "storm-b").is_dir()


@pytest.mark.parametrize("err_no", _RETRYABLE_ERRNOS)
def test_cleanup_retryable_errno_matrix(err_no: int) -> None:
    assert wepp_module._is_cleanup_retryable(OSError(err_no, "retryable"))


def test_cleanup_retryable_errno_matrix_excludes_non_retryable() -> None:
    assert not wepp_module._is_cleanup_retryable(OSError(errno.EIO, "non-retryable"))
