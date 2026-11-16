from __future__ import annotations

from pathlib import Path
import shlex
import subprocess
import sys

import pytest

from tools.wctl2.checkout_identity import checked_test_command, requested_checkout

pytestmark = pytest.mark.unit


def _execute_checked(command: str, mounted: Path) -> subprocess.CompletedProcess:
    # Use the actual embedded verifier and shell ordering against a real local
    # directory; only interpreter/mount locations replace the Docker boundary.
    check, test_command = command.split(" && ", 1)
    argv = shlex.split(check)
    argv[0] = sys.executable
    argv[2] = argv[2].replace("'/workdir/wepppy'", repr(str(mounted)))
    return subprocess.run(
        shlex.join(argv) + " && " + test_command,
        shell=True, capture_output=True, text=True,
    )


def test_live_checkout_allows_dirty_and_untracked_source(tmp_path: Path) -> None:
    (tmp_path / "dirty.py").write_text("dirty source")
    (tmp_path / "new.py").write_text("untracked source")
    with checked_test_command(tmp_path, "printf tests-ran") as command:
        result = _execute_checked(command, tmp_path)
        assert result.returncode == 0
        assert result.stdout == "tests-ran"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dirty.py", "new.py"]


def test_same_revision_copied_checkout_is_rejected_before_test(tmp_path: Path) -> None:
    caller = tmp_path / "caller"
    mounted = tmp_path / "mounted"
    caller.mkdir()
    mounted.mkdir()
    for root in (caller, mounted):
        (root / "source.py").write_text("identical committed source")
    (caller / "source.py").write_text("caller dirty source")
    with checked_test_command(caller, "printf must-not-run") as command:
        result = _execute_checked(command, mounted)
        assert result.returncode == 2
        assert result.stdout == ""
        assert "WCTL_CHECKOUT_MISMATCH" in result.stderr
    assert not list(caller.glob(".wctl-checkout-*"))
    assert (caller / "source.py").read_text() == "caller dirty source"


def test_mount_alias_passes_and_probe_is_cleaned_on_exception(tmp_path: Path) -> None:
    alias = tmp_path / "alias"
    root = tmp_path / "root"
    root.mkdir()
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(RuntimeError, match="interrupted"):
        with checked_test_command(root, "true") as command:
            assert _execute_checked(command, alias).returncode == 0
            raise RuntimeError("interrupted")
    assert not list(root.iterdir())


def test_probe_tampering_fails_closed(tmp_path: Path) -> None:
    with checked_test_command(tmp_path, "printf must-not-run") as command:
        probe = next(tmp_path.glob(".wctl-checkout-*"))
        probe.write_text("wrong nonce")
        result = _execute_checked(command, tmp_path)
        assert result.returncode == 2
        assert result.stdout == ""


def test_selection_prefers_explicit_then_caller_then_installed(tmp_path: Path) -> None:
    installed = tmp_path / "installed"
    caller = tmp_path / "caller"
    unrelated = tmp_path / "unrelated"
    for root in (installed, caller):
        (root / "tools/wctl2").mkdir(parents=True)
        (root / "docker").mkdir()
        (root / "tools/wctl2/__main__.py").touch()
        (root / "docker/defaults.env").touch()
    unrelated.mkdir()
    assert requested_checkout(installed, str(caller / "tools"), explicit=False) == caller
    assert requested_checkout(installed, str(caller), explicit=True) == installed
    assert requested_checkout(installed, str(unrelated), explicit=False) == installed


def test_missing_host_checkout_does_not_run_command(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        with checked_test_command(tmp_path / "missing", "printf must-not-run"):
            pytest.fail("missing checkout must fail before executing")
