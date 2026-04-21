import os
import stat
from types import SimpleNamespace

import pytest

from wepp_runner import wepp_runner as wepp_runner_module

pytestmark = pytest.mark.unit


def _write_executable_stub(path):
    path.write_text("stub\n", encoding="ascii")
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR)


@pytest.fixture(autouse=True)
def _reset_provenance_cache(monkeypatch):
    monkeypatch.setattr(wepp_runner_module, "_PROVENANCE_OK_BINARY_PATHS", set())


def test_binary_runtime_provenance_accepts_system_paths(monkeypatch, tmp_path):
    binary_path = tmp_path / "wepp_test"
    _write_executable_stub(binary_path)

    calls = []

    def _fake_run_text_command(args):
        calls.append(tuple(args))
        if args[:2] == ["readelf", "-l"]:
            return SimpleNamespace(
                returncode=0,
                stdout="  [Requesting program interpreter: /lib64/ld-linux-x86-64.so.2]\n",
                stderr="",
            )
        if args[:2] == ["readelf", "-d"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if args[0] == "ldd":
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "libgfortran.so.5 => /lib64/libgfortran.so.5 (0x1)\n"
                    "libm.so.6 => /lib64/libm.so.6 (0x2)\n"
                    "libc.so.6 => /lib64/libc.so.6 (0x3)\n"
                ),
                stderr="",
            )
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr(wepp_runner_module, "_run_text_command", _fake_run_text_command)

    wepp_runner_module._assert_binary_runtime_provenance(str(binary_path))
    wepp_runner_module._assert_binary_runtime_provenance(str(binary_path))

    assert calls == [
        ("readelf", "-l", str(binary_path)),
        ("readelf", "-d", str(binary_path)),
        ("ldd", str(binary_path)),
    ]


def test_binary_runtime_provenance_rejects_banned_runtime_paths(monkeypatch, tmp_path):
    binary_path = tmp_path / "wepp_test"
    _write_executable_stub(binary_path)

    def _fake_run_text_command(args):
        if args[:2] == ["readelf", "-l"]:
            return SimpleNamespace(
                returncode=0,
                stdout="  [Requesting program interpreter: /lib64/ld-linux-x86-64.so.2]\n",
                stderr="",
            )
        if args[:2] == ["readelf", "-d"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if args[0] == "ldd":
            return SimpleNamespace(
                returncode=0,
                stdout="libgfortran.so.5 => /home/linuxbrew/.linuxbrew/lib/libgfortran.so.5 (0x1)\n",
                stderr="",
            )
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr(wepp_runner_module, "_run_text_command", _fake_run_text_command)

    with pytest.raises(RuntimeError) as exc:
        wepp_runner_module._assert_binary_runtime_provenance(str(binary_path))

    assert "runtime provenance check failed" in str(exc.value)
    assert (
        "blocked Homebrew/Conda runtime paths" in str(exc.value)
        or "non-system dependency path" in str(exc.value)
    )


def test_binary_runtime_provenance_break_glass_skip(monkeypatch, tmp_path):
    binary_path = tmp_path / "wepp_test"
    _write_executable_stub(binary_path)

    monkeypatch.setenv("WEPP_RUNNER_SKIP_BINARY_PROVENANCE_CHECK", "1")
    monkeypatch.setattr(
        wepp_runner_module,
        "_run_text_command",
        lambda _args: pytest.fail("runtime guard should be skipped when break-glass env is enabled"),
    )

    wepp_runner_module._assert_binary_runtime_provenance(str(binary_path))
    assert os.path.abspath(str(binary_path)) not in wepp_runner_module._PROVENANCE_OK_BINARY_PATHS


def test_binary_runtime_provenance_accepts_legacy_static_binary(monkeypatch, tmp_path):
    binary_path = tmp_path / "wepp_static"
    _write_executable_stub(binary_path)

    def _fake_run_text_command(args):
        if args[:2] == ["readelf", "-l"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if args[:2] == ["readelf", "-d"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="There is no dynamic section in this file.\n")
        if args[0] == "ldd":
            return SimpleNamespace(returncode=1, stdout="", stderr="not a dynamic executable\n")
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr(wepp_runner_module, "_run_text_command", _fake_run_text_command)

    wepp_runner_module._assert_binary_runtime_provenance(str(binary_path))
    assert os.path.abspath(str(binary_path)) in wepp_runner_module._PROVENANCE_OK_BINARY_PATHS
