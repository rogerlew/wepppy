"""Real-Git regression tests for integration receipts and accidental-loss guards."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "tools/check_integration_history.py"
INSTALLER = ROOT / "tools/install_integration_hooks.py"


def run(*args, cwd=None, ok=True):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.invalid",
               GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.invalid")
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env,
                            capture_output=True, text=True, timeout=20)
    if ok:
        assert result.returncode == 0, result.stderr
    return result


def git(repo, *args, ok=True):
    return run("git", "-C", repo, *args, ok=ok).stdout.strip()


def commit(repo, name):
    (repo / name).write_text(name)
    git(repo, "add", name)
    git(repo, "commit", "-m", name)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def history(tmp_path):
    remote = tmp_path / "remote.git"
    repo = tmp_path / "checkout"
    run("git", "init", "--bare", "--initial-branch=master", remote)
    run("git", "clone", remote, repo)
    base = commit(repo, "base")
    git(repo, "push", "origin", "master")
    return repo, remote, base


def receipt(repo, accepted, output, *extra, ok=True):
    return run(sys.executable, CHECKER, "receipt", "--repo", repo,
               "--accepted", accepted, "--output", output, *extra, ok=ok)


def install(repo, *extra, ok=True):
    return run(sys.executable, INSTALLER, "--repo", repo, *extra, ok=ok)


def verify(repo, path, *extra, ok=True):
    return run(sys.executable, CHECKER, "verify", "--repo", repo,
               "--receipt", path, *extra, ok=ok)


def test_published_receipt_preserves_dirty_state_and_ref_namespace(history, tmp_path):
    repo, remote, base = history
    (repo / "base").write_text("dirty")
    (repo / "untracked").write_text("untouched")
    status = git(repo, "status", "--porcelain")
    refs = git(repo, "show-ref")
    path = tmp_path / "receipt.json"
    value = json.loads(receipt(repo, base, path).stdout)
    assert json.loads(path.read_text()) == value
    assert value["repository"] == str(remote)
    assert value["observed_remote_sha"] == base
    assert value["claim"] == "remote_integration_snapshot"
    assert git(repo, "status", "--porcelain") == status
    assert git(repo, "show-ref") == refs
    assert (repo / "base").read_text() == "dirty"
    assert not json.loads(verify(repo, path).stdout)["remote_advanced_since_receipt"]


def test_exact_incident_fast_forward_cannot_close_unpublished_history(history, tmp_path):
    repo, remote, base = history
    for i in range(20):
        accepted = commit(repo, f"accepted-{i}")
    soils = commit(repo, "soils")
    git(repo, "update-ref", "refs/recovery/accepted", accepted)
    git(repo, "checkout", "--detach", base)
    git(repo, "cherry-pick", soils)
    git(repo, "branch", "-f", "master", "HEAD")
    git(repo, "push", "origin", "master")
    path = tmp_path / "false-receipt.json"
    result = receipt(repo, accepted, path, ok=False)
    assert result.returncode != 0
    assert "NOT_INTEGRATED" in result.stderr
    assert not path.exists()
    assert "accepted-0" not in git(repo, "ls-tree", "--name-only", "master")


def test_merge_preserving_integration_and_remote_advance(history, tmp_path):
    repo, remote, base = history
    git(repo, "checkout", "-b", "task")
    accepted = commit(repo, "accepted")
    git(repo, "checkout", "master")
    commit(repo, "other")
    git(repo, "merge", "--no-ff", "task", "-m", "integrate")
    git(repo, "push", "origin", "master")
    path = tmp_path / "receipt.json"
    snapshot = json.loads(receipt(repo, accepted, path).stdout)
    commit(repo, "later")
    git(repo, "push", "origin", "master")
    assert json.loads(verify(repo, path).stdout)["remote_advanced_since_receipt"]
    assert verify(repo, path, "--expected-remote-sha", snapshot["observed_remote_sha"], ok=False).returncode
    assert json.loads(path.read_text()) == snapshot


def test_stale_tracking_ref_cannot_substitute_for_remote(history, tmp_path):
    repo, remote, base = history
    accepted = commit(repo, "local")
    git(repo, "update-ref", "refs/remotes/origin/master", accepted)
    assert receipt(repo, accepted, tmp_path / "receipt", ok=False).returncode


def test_offline_shallow_and_missing_object_fail(history, tmp_path):
    repo, remote, base = history
    shallow = tmp_path / "shallow"
    run("git", "clone", "--depth=1", remote.as_uri(), shallow)
    assert "SHALLOW_HISTORY" in receipt(shallow, base, tmp_path / "s", ok=False).stderr
    assert receipt(repo, "a" * 40, tmp_path / "m", ok=False).returncode
    git(repo, "remote", "set-url", "origin", str(tmp_path / "missing.git"))
    assert receipt(repo, base, tmp_path / "o", ok=False).returncode
    assert git(repo, "for-each-ref", "refs/integration-observations") == ""


def test_receipt_does_not_clobber_or_follow_output_symlink(history, tmp_path):
    repo, remote, base = history
    target = tmp_path / "existing"
    target.write_text("keep")
    alias = tmp_path / "alias"
    alias.symlink_to(target)
    assert receipt(repo, base, target, ok=False).returncode
    assert receipt(repo, base, alias, ok=False).returncode
    assert target.read_text() == "keep"
    assert not list(tmp_path.glob(".integration-receipt-*"))


def test_wrong_remote_branch_and_malformed_receipt_refused(history, tmp_path):
    repo, remote, base = history
    path = tmp_path / "receipt"
    receipt(repo, base, path)
    git(repo, "remote", "add", "other", str(remote))
    assert "WRONG_TARGET" in verify(repo, path, "--remote", "other", ok=False).stderr
    assert "WRONG_TARGET" in verify(repo, path, "--branch", "other", ok=False).stderr
    value = json.loads(path.read_text())
    value["integration_mode"] = "squash"
    path.write_text(json.dumps(value))
    assert "INVALID_RECEIPT" in verify(repo, path, ok=False).stderr


def test_snapshot_rewrite_is_detected_even_when_accepted_survives(history, tmp_path):
    repo, remote, base = history
    commit(repo, "one")
    git(repo, "push", "origin", "master")
    path = tmp_path / "receipt"
    receipt(repo, base, path)
    git(repo, "reset", "--hard", base)
    commit(repo, "replacement")
    git(repo, "push", "--force", "origin", "master")
    assert "REMOTE_HISTORY_CHANGED" in verify(repo, path, ok=False).stderr


def test_credential_remote_refused_before_output(history, tmp_path):
    repo, remote, base = history
    git(repo, "remote", "set-url", "origin", "https://secret@example.invalid/repo")
    result = receipt(repo, base, tmp_path / "receipt", ok=False)
    assert "REMOTE_CREDENTIALS" in result.stderr
    assert "secret" not in result.stderr


def test_hook_install_preserves_lfs_and_detects_missing_conflict(history):
    repo, remote, base = history
    assert "HOOK_MISSING" in install(repo, "--check", ok=False).stderr
    hooks = repo / ".git/hooks"
    lfs = hooks / "pre-push"
    lfs.write_text("#!/bin/sh\ngit lfs pre-push \"$@\"\n")
    lfs.chmod(0o755)
    before = lfs.read_bytes()
    install(repo)
    install(repo, "--check")
    install(repo)
    assert lfs.read_bytes() == before
    guard = hooks / "reference-transaction"
    guard.write_text("#!/bin/sh\nexit 0\n")
    assert "HOOK_CONFLICT" in install(repo, ok=False).stderr
    assert guard.read_text() == "#!/bin/sh\nexit 0\n"


def test_hook_refuses_custom_hook_manager(history):
    repo, remote, base = history
    git(repo, "config", "core.hooksPath", "custom")
    assert "CUSTOM_HOOKS_PATH" in install(repo, ok=False).stderr


@pytest.mark.parametrize("operation", ["reset", "delete", "update", "rebase"])
def test_guard_refuses_protected_master_loss(history, operation):
    repo, remote, base = history
    accepted = commit(repo, "accepted")
    commit(repo, "soils")
    tip = git(repo, "rev-parse", "master")
    install(repo)
    if operation == "reset":
        args = ["reset", "--soft", base]
    elif operation == "delete":
        args = ["update-ref", "-d", "refs/heads/master"]
    elif operation == "update":
        args = ["update-ref", "refs/heads/master", base]
    else:
        args = ["rebase", "--onto", base, accepted, "master"]
    result = run("git", "-C", repo, *args, ok=False)
    assert result.returncode != 0
    assert "PROTECTED_MASTER" in result.stderr
    assert git(repo, "rev-parse", "master") == tip


def test_guard_allows_fast_forward_commit_and_other_branch_changes(history):
    repo, remote, base = history
    install(repo)
    newer = commit(repo, "new")
    assert git(repo, "rev-parse", "master") == newer
    git(repo, "branch", "task")
    git(repo, "branch", "-f", "task", base)
    git(repo, "branch", "-D", "task")


def test_ambient_git_selection_cannot_redirect_receipt_or_installer(history, tmp_path, monkeypatch):
    repo, remote, base = history
    other = tmp_path / "other"
    run("git", "init", "--initial-branch=master", other)
    unrelated = commit(other, "unrelated")
    git(other, "remote", "add", "origin", str(tmp_path / "nonexistent"))
    original_index = (repo / ".git/index").read_bytes()
    other_index = (other / ".git/index").read_bytes()
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_COMMON_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    monkeypatch.setenv("GIT_INDEX_FILE", str(other / ".git/index"))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(other / ".git/objects"))
    monkeypatch.setenv("GIT_ALTERNATE_OBJECT_DIRECTORIES", str(other / ".git/objects"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "remote.origin.url")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(tmp_path / "wrong-remote"))
    path = tmp_path / "receipt"
    value = json.loads(receipt(repo, base, path).stdout)
    assert value["repository"] == str(remote)
    assert value["observed_remote_sha"] == base
    verify(repo, path)
    install(repo)
    assert (repo / ".git/hooks/reference-transaction").exists()
    assert not (other / ".git/hooks/reference-transaction").exists()
    assert (repo / ".git/index").read_bytes() == original_index
    assert (other / ".git/index").read_bytes() == other_index
    assert unrelated != base


def test_installed_guard_works_in_linked_worktree(history, tmp_path):
    repo, remote, base = history
    accepted = commit(repo, "accepted")
    # Move master to its own linked checkout; guard must resolve that checkout's
    # shared repository correctly after removing Git's exported selection env.
    git(repo, "switch", "--detach")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", str(linked), "master")
    install(linked)
    result = run("git", "-C", linked, "reset", "--soft", base, ok=False)
    assert result.returncode != 0
    assert "PROTECTED_MASTER" in result.stderr
    assert git(linked, "rev-parse", "master") == accepted


@pytest.mark.parametrize("venv_mode", ["--copies", "--symlinks"])
def test_installed_checker_survives_removal_of_installer_worktree(history, tmp_path, venv_mode):
    repo, remote, base = history
    source_tree = tmp_path / "installer-worktree"
    git(repo, "worktree", "add", "--detach", str(source_tree), base)
    tools = source_tree / "tools"
    tools.mkdir()
    (tools / CHECKER.name).write_bytes(CHECKER.read_bytes())
    (tools / INSTALLER.name).write_bytes(INSTALLER.read_bytes())
    environment = source_tree / ".venv"
    run(sys.executable, "-m", "venv", "--without-pip", venv_mode, environment)
    run(environment / "bin/python", tools / INSTALLER.name, "--repo", source_tree)
    installed = repo / ".git/hooks/wepppy-integration-history-v1.py"
    assert installed.read_bytes() == CHECKER.read_bytes()
    hook = (repo / ".git/hooks/reference-transaction").read_text()
    assert str(source_tree) not in hook
    assert "/usr/bin/python3 -I " in hook
    git(repo, "worktree", "remove", "--force", str(source_tree))
    assert not source_tree.exists()
    accepted = commit(repo, "accepted-after-removal")
    git(repo, "push", "origin", "master")
    path = tmp_path / "stable-receipt"
    receipt(repo, accepted, path)
    assert json.loads(path.read_text())["accepted_sha"] == accepted
    result = run("git", "-C", repo, "reset", "--soft", base, ok=False)
    assert result.returncode != 0
    assert "PROTECTED_MASTER" in result.stderr
    assert git(repo, "rev-parse", "master") == accepted
    install(repo, "--check")


def test_installed_checker_drift_is_reported_without_replacement(history):
    repo, remote, base = history
    install(repo)
    checker = repo / ".git/hooks/wepppy-integration-history-v1.py"
    original_hook = (repo / ".git/hooks/reference-transaction").read_bytes()
    checker.write_text("# drift\n")
    for options in [("--check",), ()]:
        result = install(repo, *options, ok=False)
        assert result.returncode != 0
        assert "HOOK_CONFLICT" in result.stderr
        assert checker.read_text() == "# drift\n"
        assert (repo / ".git/hooks/reference-transaction").read_bytes() == original_hook


def test_checker_symlink_conflict_prevents_partial_hook_install(history, tmp_path):
    repo, remote, base = history
    unrelated = tmp_path / "unrelated"
    unrelated.write_text("keep")
    (repo / ".git/hooks/wepppy-integration-history-v1.py").symlink_to(unrelated)
    result = install(repo, ok=False)
    assert result.returncode != 0
    assert "HOOK_CONFLICT" in result.stderr
    assert not (repo / ".git/hooks/reference-transaction").exists()
    assert unrelated.read_text() == "keep"
