from __future__ import annotations

import threading
from contextlib import contextmanager
import zipfile
from pathlib import Path

import pytest

from wepppy.nodir.errors import NoDirError, nodir_locked
from wepppy.nodir.wepp_inputs import (
    copy_input_file,
    glob_input_files,
    input_exists,
    list_input_files,
    materialize_input_file,
    open_input_binary,
    with_input_file_path,
    open_input_text,
)

pytestmark = pytest.mark.unit


class _RedisLockStub:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._mutex = threading.Lock()

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):  # noqa: ARG002
        with self._mutex:
            if nx and key in self._store:
                return False
            self._store[key] = value
            return True

    def get(self, key: str):
        with self._mutex:
            return self._store.get(key)

    def delete(self, key: str):
        with self._mutex:
            self._store.pop(key, None)
            return 1

    def eval(self, script: str, numkeys: int, key: str, *args):  # noqa: ARG002
        expected = str(args[0]) if args else ""
        with self._mutex:
            current = self._store.get(key)
            if "redis.call('del', KEYS[1])" in script:
                if current == expected:
                    self._store.pop(key, None)
                    return 1
                return 0
            if "redis.call('expire', KEYS[1], ARGV[2])" in script:
                if current == expected:
                    return 1
                return 0
        raise AssertionError(f"unexpected eval script: {script}")



def _write_zip(path: Path, entries: dict[str, bytes | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries.items():
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            zf.writestr(name, data)


def test_open_input_binary_dir_form(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed" / "a.txt").parent.mkdir(parents=True, exist_ok=True)
    (wd / "watershed" / "a.txt").write_text("alpha", encoding="utf-8")

    with open_input_binary(str(wd), "watershed/a.txt") as fp:
        assert fp.read() == b"alpha"


def test_open_input_binary_archive_form(tmp_path: Path) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"subdir/a.txt": "alpha"})

    with open_input_binary(str(wd), "watershed/subdir/a.txt") as fp:
        assert fp.read() == b"alpha"


def test_open_input_text_archive_form(tmp_path: Path) -> None:
    wd = tmp_path
    _write_zip(wd / "soils.nodir", {"soil.txt": "silty"})

    with open_input_text(str(wd), "soils/soil.txt") as fp:
        assert fp.read() == "silty"


def test_copy_input_file_archive_form(tmp_path: Path) -> None:
    wd = tmp_path
    _write_zip(wd / "landuse.nodir", {"foo/bar.man": "man-data"})
    dst = wd / "out" / "bar.man"

    copied = copy_input_file(str(wd), "landuse/foo/bar.man", dst)

    assert copied == str(dst)
    assert dst.read_text(encoding="utf-8") == "man-data"


def test_copy_input_file_dir_form(tmp_path: Path) -> None:
    wd = tmp_path
    src = wd / "climate" / "site.cli"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("cli", encoding="utf-8")

    dst = wd / "wepp" / "runs" / "p1.cli"
    copied = copy_input_file(str(wd), "climate/site.cli", dst)

    assert copied == str(dst)
    assert dst.read_text(encoding="utf-8") == "cli"


def test_list_and_glob_input_files_archive_form(tmp_path: Path) -> None:
    wd = tmp_path
    _write_zip(
        wd / "watershed.nodir",
        {
            "slope_files/flowpaths/a.slps": "a",
            "slope_files/flowpaths/b.slps": "b",
            "slope_files/flowpaths/c.txt": "c",
        },
    )

    listed = list_input_files(str(wd), "watershed/slope_files/flowpaths")
    globbed = glob_input_files(str(wd), "watershed/slope_files/flowpaths/*.slps")

    assert listed == ["a.slps", "b.slps", "c.txt"]
    assert globbed == [
        "watershed/slope_files/flowpaths/a.slps",
        "watershed/slope_files/flowpaths/b.slps",
    ]


def test_glob_input_files_rejects_wildcard_parent(tmp_path: Path) -> None:
    wd = tmp_path
    with pytest.raises(ValueError, match="final segment"):
        glob_input_files(str(wd), "watershed/*/flowpaths/*.slps")


def test_input_exists_archive_form(tmp_path: Path) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "x"})

    assert input_exists(str(wd), "watershed/hillslopes/h001.slp") is True
    assert input_exists(str(wd), "watershed/hillslopes/missing.slp") is False


def test_materialize_input_file_archive_form(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.materialize as materialize_mod

    monkeypatch.setattr(materialize_mod, "redis_lock_client", _RedisLockStub())

    path = Path(materialize_input_file(str(wd), "watershed/hillslopes/h001.slp", purpose="test"))

    assert path.read_text(encoding="utf-8") == "alpha"
    assert "/.nodir/cache/" in path.as_posix()


def test_open_input_binary_mixed_state_preserves_canonical_error(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed" / "a.txt").parent.mkdir(parents=True, exist_ok=True)
    (wd / "watershed" / "a.txt").write_text("alpha", encoding="utf-8")
    _write_zip(wd / "watershed.nodir", {"a.txt": "archived"})

    with pytest.raises(NoDirError) as exc:
        open_input_binary(str(wd), "watershed/a.txt")

    assert exc.value.http_status == 409
    assert exc.value.code == "NODIR_MIXED_STATE"


def test_open_input_binary_mixed_state_can_prefer_archive(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed" / "a.txt").parent.mkdir(parents=True, exist_ok=True)
    (wd / "watershed" / "a.txt").write_text("from-dir", encoding="utf-8")
    _write_zip(wd / "watershed.nodir", {"a.txt": "from-archive"})

    with open_input_binary(
        str(wd),
        "watershed/a.txt",
        tolerate_mixed=True,
        mixed_prefer="archive",
    ) as fp:
        assert fp.read() == b"from-archive"


def test_input_exists_mixed_state_can_prefer_archive(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed" / "only-in-dir.txt").parent.mkdir(parents=True, exist_ok=True)
    (wd / "watershed" / "only-in-dir.txt").write_text("dir", encoding="utf-8")
    _write_zip(wd / "watershed.nodir", {"only-in-archive.txt": "archive"})

    assert input_exists(str(wd), "watershed/only-in-archive.txt", tolerate_mixed=True, mixed_prefer="archive")
    assert not input_exists(str(wd), "watershed/only-in-dir.txt", tolerate_mixed=True, mixed_prefer="archive")


def test_open_input_binary_invalid_archive_preserves_canonical_error(tmp_path: Path) -> None:
    wd = tmp_path
    (wd / "watershed.nodir").write_bytes(b"not-a-zip")

    with pytest.raises(NoDirError) as exc:
        open_input_binary(str(wd), "watershed/a.txt")

    assert exc.value.http_status == 500
    assert exc.value.code == "NODIR_INVALID_ARCHIVE"


def test_open_input_binary_transition_lock_preserves_canonical_error(tmp_path: Path) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"a.txt": "archived"})
    (wd / "watershed.thaw.tmp").mkdir(parents=True, exist_ok=True)

    with pytest.raises(NoDirError) as exc:
        open_input_binary(str(wd), "watershed/a.txt")

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"


def test_with_input_file_path_archive_form_prefers_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.projections as projections_mod

    monkeypatch.setattr(projections_mod, "redis_lock_client", _RedisLockStub())

    with with_input_file_path(str(wd), "watershed/hillslopes/h001.slp", purpose="test-proj") as src_fn:
        src_path = Path(src_fn)
        assert src_path.read_text(encoding="utf-8") == "alpha"
        assert "/watershed/" in src_path.as_posix()
        assert "/.nodir/cache/" not in src_path.as_posix()


def test_with_input_file_path_projection_error_can_fallback_to_materialize(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.wepp_inputs as wepp_inputs_mod

    @contextmanager
    def _fail_projection(*_args, **_kwargs):
        raise nodir_locked("projection lock is held")
        yield  # pragma: no cover

    calls: list[tuple[str, str, str]] = []

    def _fake_materialize(wd_arg: str, rel_arg: str, *, purpose: str) -> str:
        calls.append((wd_arg, rel_arg, purpose))
        dst = Path(wd_arg) / "fallback" / "h001.slp"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text("fallback", encoding="utf-8")
        return str(dst)

    monkeypatch.setattr(wepp_inputs_mod, "with_root_projection", _fail_projection)
    monkeypatch.setattr(wepp_inputs_mod, "materialize_input_file", _fake_materialize)

    with with_input_file_path(
        str(wd),
        "watershed/hillslopes/h001.slp",
        purpose="test-fallback",
        allow_materialize_fallback=True,
    ) as src_fn:
        assert Path(src_fn).read_text(encoding="utf-8") == "fallback"

    assert calls == [(str(wd), "watershed/hillslopes/h001.slp", "test-fallback")]


def test_with_input_file_path_projection_error_without_fallback_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.wepp_inputs as wepp_inputs_mod

    @contextmanager
    def _fail_projection(*_args, **_kwargs):
        raise nodir_locked("projection lock is held")
        yield  # pragma: no cover

    monkeypatch.setattr(wepp_inputs_mod, "with_root_projection", _fail_projection)

    with pytest.raises(NoDirError) as exc:
        with with_input_file_path(
            str(wd),
            "watershed/hillslopes/h001.slp",
            purpose="test-no-fallback",
            allow_materialize_fallback=False,
        ):
            pass

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"


def test_with_input_file_path_projection_disabled_requires_explicit_fallback(
    tmp_path: Path,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    with pytest.raises(ValueError, match="require projection or explicit materialize fallback"):
        with with_input_file_path(
            str(wd),
            "watershed/hillslopes/h001.slp",
            purpose="test-projection-disabled",
            use_projection=False,
            allow_materialize_fallback=False,
        ):
            pass


def test_with_input_file_path_projection_disabled_fallback_logs_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.wepp_inputs as wepp_inputs_mod

    def _fake_materialize(wd_arg: str, rel_arg: str, *, purpose: str) -> str:
        dst = Path(wd_arg) / "fallback-disabled" / "h001.slp"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text("fallback", encoding="utf-8")
        return str(dst)

    monkeypatch.setattr(wepp_inputs_mod, "materialize_input_file", _fake_materialize)

    with caplog.at_level("WARNING", logger=wepp_inputs_mod.__name__):
        with with_input_file_path(
            str(wd),
            "watershed/hillslopes/h001.slp",
            purpose="test-projection-disabled-fallback",
            use_projection=False,
            allow_materialize_fallback=True,
        ) as src_fn:
            assert Path(src_fn).read_text(encoding="utf-8") == "fallback"

    assert "fallback to materialize (projection disabled)" in caplog.text


def test_with_input_file_path_mixed_state_preserves_canonical_error(
    tmp_path: Path,
) -> None:
    wd = tmp_path
    (wd / "watershed" / "a.txt").parent.mkdir(parents=True, exist_ok=True)
    (wd / "watershed" / "a.txt").write_text("from-dir", encoding="utf-8")
    _write_zip(wd / "watershed.nodir", {"a.txt": "from-archive"})

    with pytest.raises(NoDirError) as exc:
        with with_input_file_path(str(wd), "watershed/a.txt", purpose="test-mixed"):
            pass

    assert exc.value.http_status == 409
    assert exc.value.code == "NODIR_MIXED_STATE"


def test_with_input_file_path_invalid_archive_preserves_canonical_error(
    tmp_path: Path,
) -> None:
    wd = tmp_path
    (wd / "watershed.nodir").write_bytes(b"not-a-zip")

    with pytest.raises(NoDirError) as exc:
        with with_input_file_path(str(wd), "watershed/a.txt", purpose="test-invalid"):
            pass

    assert exc.value.http_status == 500
    assert exc.value.code == "NODIR_INVALID_ARCHIVE"


def test_with_input_file_path_projection_error_fallback_logs_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    wd = tmp_path
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    import wepppy.nodir.wepp_inputs as wepp_inputs_mod

    @contextmanager
    def _fail_projection(*_args, **_kwargs):
        raise nodir_locked("projection lock is held")
        yield  # pragma: no cover

    def _fake_materialize(wd_arg: str, rel_arg: str, *, purpose: str) -> str:
        dst = Path(wd_arg) / "fallback" / "h001.slp"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text("fallback", encoding="utf-8")
        return str(dst)

    monkeypatch.setattr(wepp_inputs_mod, "with_root_projection", _fail_projection)
    monkeypatch.setattr(wepp_inputs_mod, "materialize_input_file", _fake_materialize)

    with caplog.at_level("WARNING", logger=wepp_inputs_mod.__name__):
        with with_input_file_path(
            str(wd),
            "watershed/hillslopes/h001.slp",
            purpose="test-fallback-log",
            allow_materialize_fallback=True,
        ) as src_fn:
            assert Path(src_fn).read_text(encoding="utf-8") == "fallback"

    assert "fallback to materialize (projection error)" in caplog.text
