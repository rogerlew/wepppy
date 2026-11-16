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


def _git(repo: Path, *args: str) -> str:
    import os
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
        GIT_AUTHOR_NAME="Checkout test", GIT_AUTHOR_EMAIL="checkout@example.invalid",
        GIT_COMMITTER_NAME="Checkout test", GIT_COMMITTER_EMAIL="checkout@example.invalid",
    )
    return subprocess.run(
        ["git", "-C", str(repo), *args], env=env, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def _source_repository(root: Path) -> None:
    root.mkdir()
    _git(root, "init", "--initial-branch=master")
    for name in ("tools/wctl2/__main__.py", "docker/defaults.env", "selected/source.py"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("source")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "source")


def test_sparse_linked_checkout_is_selected_and_mismatched_mount_refused(tmp_path: Path) -> None:
    installed = tmp_path / "installed"
    _source_repository(installed)
    sparse = tmp_path / "sparse"
    _git(installed, "worktree", "add", "--detach", str(sparse))
    _git(sparse, "sparse-checkout", "set", "--cone", "selected")
    assert not (sparse / "tools").exists()
    assert not (sparse / "docker").exists()
    selected = requested_checkout(installed, str(sparse / "selected"), explicit=False)
    assert selected == sparse
    with checked_test_command(selected, "printf must-not-run") as command:
        result = _execute_checked(command, installed)
    assert result.returncode == 2
    assert not result.stdout
    assert "WCTL_CHECKOUT_MISMATCH" in result.stderr


def test_deleted_checkout_markers_still_recognized_from_head(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _source_repository(source)
    _git(source, "rm", "tools/wctl2/__main__.py", "docker/defaults.env")
    assert requested_checkout(tmp_path / "installed", str(source), explicit=False) == source


def test_unrelated_and_unborn_git_repositories_keep_preset_fallback(tmp_path: Path) -> None:
    installed = tmp_path / "installed"
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    _git(unrelated, "init", "--initial-branch=master")
    assert requested_checkout(installed, str(unrelated), explicit=False) == installed
    (unrelated / "other.py").write_text("unrelated")
    _git(unrelated, "add", ".")
    _git(unrelated, "commit", "-m", "unrelated")
    assert requested_checkout(installed, str(unrelated), explicit=False) == installed


def test_caller_git_inspection_ignores_ambient_repository_selection(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    _source_repository(source)
    _git(source, "sparse-checkout", "set", "--cone", "selected")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    _git(unrelated, "init", "--initial-branch=master")
    monkeypatch.setenv("GIT_DIR", str(unrelated / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(unrelated))
    monkeypatch.setenv("GIT_INDEX_FILE", str(unrelated / ".git/index"))
    assert requested_checkout(unrelated, str(source), explicit=False) == source


def test_unreadable_git_metadata_does_not_silently_choose_installed(tmp_path: Path) -> None:
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / ".git").write_text("gitdir: missing-directory\n")
    with pytest.raises(OSError, match="Cannot inspect caller Git checkout"):
        requested_checkout(tmp_path / "installed", str(broken), explicit=False)
