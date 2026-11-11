from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from wepppy.weppcloud.bootstrap import pre_receive

pytestmark = pytest.mark.integration


MULTI_OFE_SLP = """97.5
2
180 10
1 50
0.0 0.1
1 50
0.0 0.1
"""


def _run_git(cwd: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"git {' '.join(args)} failed: {result.stdout.strip()} {result.stderr.strip()}".strip()
    )
    return result.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    _run_git(tmp_path, ["init", "-b", "main"])
    _run_git(tmp_path, ["config", "user.name", "Test User"])
    _run_git(tmp_path, ["config", "user.email", "test@example.com"])
    _run_git(tmp_path, ["commit", "--allow-empty", "-m", "baseline"])
    return tmp_path


def _commit_all(cwd: Path, message: str) -> str:
    _run_git(cwd, ["add", "--", "."])
    _run_git(cwd, ["commit", "-m", message])
    return _run_git(cwd, ["rev-parse", "HEAD"])


def _run_pre_receive(
    monkeypatch: pytest.MonkeyPatch,
    repo: Path,
    old_sha: str,
    new_sha: str,
    user: str = "alice@example.com",
    ref: str = "refs/heads/main",
) -> int:
    monkeypatch.chdir(repo)
    monkeypatch.setenv("HTTP_X_AUTH_USER", user)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(f"{old_sha} {new_sha} {ref}\n"),
        raising=False,
    )
    return pre_receive.main()


def test_pre_receive_rejects_run_file_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path)
    run_path = repo / "wepp" / "runs" / "inputs.run"
    run_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.write_text("baseline")
    baseline_sha = _commit_all(repo, "add run file")

    _run_git(repo, ["checkout", "-b", "push"])
    run_path.write_text("modified")
    new_sha = _commit_all(repo, "modify run file")
    _run_git(repo, ["checkout", "main"])
    _run_git(repo, ["branch", "-D", "push"])

    with pytest.raises(RuntimeError, match=r"\.run files are read-only"):
        _run_pre_receive(monkeypatch, repo, baseline_sha, new_sha)


def test_pre_receive_logs_push_for_multi_ofe_slp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path)
    baseline_sha = _run_git(repo, ["rev-parse", "HEAD"])

    _run_git(repo, ["checkout", "-b", "push"])
    slp_path = repo / "wepp" / "runs" / "multi.slp"
    slp_path.parent.mkdir(parents=True, exist_ok=True)
    slp_path.write_text(MULTI_OFE_SLP)
    new_sha = _commit_all(repo, "add multi ofe slp")
    _run_git(repo, ["checkout", "main"])
    _run_git(repo, ["branch", "-D", "push"])

    result = _run_pre_receive(monkeypatch, repo, baseline_sha, new_sha)
    assert result == 0

    log_path = repo / ".git" / "bootstrap" / "push-log.ndjson"
    assert log_path.exists()
    entries = [
        json.loads(line)
        for line in log_path.read_text().splitlines()
        if line.strip()
    ]
    assert any(entry["sha"] == new_sha and entry["user"] == "alice@example.com" for entry in entries)


def test_pre_receive_rejects_oversize_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path)
    baseline_sha = _run_git(repo, ["rev-parse", "HEAD"])

    _run_git(repo, ["checkout", "-b", "push"])
    data_path = repo / "wepp" / "runs" / "big.txt"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text("x" * 32)
    new_sha = _commit_all(repo, "add large file")
    _run_git(repo, ["checkout", "main"])
    _run_git(repo, ["branch", "-D", "push"])

    monkeypatch.setattr(pre_receive, "MAX_FILE_BYTES", 10)
    with pytest.raises(RuntimeError, match=r"exceeds"):
        _run_pre_receive(monkeypatch, repo, baseline_sha, new_sha)


def test_pre_receive_rejects_binary_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path)
    baseline_sha = _run_git(repo, ["rev-parse", "HEAD"])

    _run_git(repo, ["checkout", "-b", "push"])
    data_path = repo / "wepp" / "runs" / "binary.txt"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_bytes(b"abc\x00def")
    new_sha = _commit_all(repo, "add binary file")
    _run_git(repo, ["checkout", "main"])
    _run_git(repo, ["branch", "-D", "push"])

    with pytest.raises(RuntimeError, match=r"binary"):
        _run_pre_receive(monkeypatch, repo, baseline_sha, new_sha)


def test_pre_receive_rejects_disallowed_path_in_non_tip_new_ref_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)

    _run_git(repo, ["checkout", "-b", "push"])
    bad_path = repo / "outside-allowed-path.txt"
    bad_path.write_text("nope")
    _commit_all(repo, "add disallowed path")
    _run_git(repo, ["commit", "--allow-empty", "-m", "tip commit"])
    tip_sha = _run_git(repo, ["rev-parse", "HEAD"])
    _run_git(repo, ["checkout", "main"])
    _run_git(repo, ["branch", "-D", "push"])

    with pytest.raises(RuntimeError, match=r"outside allowed directories"):
        _run_pre_receive(
            monkeypatch,
            repo,
            pre_receive.ZERO_SHA,
            tip_sha,
            ref="refs/heads/incoming",
        )


def test_pre_receive_new_ref_logs_only_introduced_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_repo(tmp_path)
    _run_git(repo, ["commit", "--allow-empty", "-m", "baseline-2"])
    main_head = _run_git(repo, ["rev-parse", "HEAD"])

    _run_git(repo, ["checkout", "-b", "push"])
    slp_path = repo / "wepp" / "runs" / "multi.slp"
    slp_path.parent.mkdir(parents=True, exist_ok=True)
    slp_path.write_text(MULTI_OFE_SLP)
    new_sha = _commit_all(repo, "add multi ofe slp")
    _run_git(repo, ["checkout", "main"])
    _run_git(repo, ["branch", "-D", "push"])

    result = _run_pre_receive(
        monkeypatch,
        repo,
        pre_receive.ZERO_SHA,
        new_sha,
        ref="refs/heads/incoming",
    )
    assert result == 0

    log_path = repo / ".git" / "bootstrap" / "push-log.ndjson"
    entries = [
        json.loads(line)
        for line in log_path.read_text().splitlines()
        if line.strip()
    ]
    shas = {entry["sha"] for entry in entries}
    assert new_sha in shas
    assert main_head not in shas


def test_pre_receive_rejects_symlink_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path)
    baseline_sha = _run_git(repo, ["rev-parse", "HEAD"])

    _run_git(repo, ["checkout", "-b", "push"])
    runs_dir = repo / "wepp" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "plain.sol").write_text("plain text")
    (runs_dir / "linked.sol").symlink_to("plain.sol")
    new_sha = _commit_all(repo, "add symlink")
    _run_git(repo, ["checkout", "main"])
    _run_git(repo, ["branch", "-D", "push"])

    with pytest.raises(RuntimeError, match=r"Symlinks are not allowed"):
        _run_pre_receive(monkeypatch, repo, baseline_sha, new_sha)


def test_pre_receive_rejects_submodule_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path)
    baseline_sha = _run_git(repo, ["rev-parse", "HEAD"])

    _run_git(repo, ["checkout", "-b", "push"])
    head_sha = _run_git(repo, ["rev-parse", "HEAD"])
    _run_git(
        repo,
        ["update-index", "--add", "--cacheinfo", f"160000,{head_sha},wepp/runs/submodule-entry"],
    )
    _run_git(repo, ["commit", "-m", "add gitlink"])
    new_sha = _run_git(repo, ["rev-parse", "HEAD"])
    _run_git(repo, ["checkout", "main"])
    _run_git(repo, ["branch", "-D", "push"])

    with pytest.raises(RuntimeError, match=r"Submodules are not allowed"):
        _run_pre_receive(monkeypatch, repo, baseline_sha, new_sha)


def test_pre_receive_rejects_rename_operations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path)
    runs_dir = repo / "wepp" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    original_path = runs_dir / "source.sol"
    original_path.write_text("source")
    baseline_sha = _commit_all(repo, "add source")

    _run_git(repo, ["checkout", "-b", "push"])
    _run_git(repo, ["mv", "wepp/runs/source.sol", "wepp/runs/renamed.sol"])
    new_sha = _commit_all(repo, "rename source")
    _run_git(repo, ["checkout", "main"])
    _run_git(repo, ["branch", "-D", "push"])

    with pytest.raises(RuntimeError, match=r"Rename/copy not allowed"):
        _run_pre_receive(monkeypatch, repo, baseline_sha, new_sha)


def test_pre_receive_rejects_deleting_allowed_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path)
    runs_dir = repo / "wepp" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    target_path = runs_dir / "delete-me.sol"
    target_path.write_text("delete me")
    baseline_sha = _commit_all(repo, "add input")

    _run_git(repo, ["checkout", "-b", "push"])
    _run_git(repo, ["rm", "wepp/runs/delete-me.sol"])
    new_sha = _commit_all(repo, "remove input")
    _run_git(repo, ["checkout", "main"])
    _run_git(repo, ["branch", "-D", "push"])

    with pytest.raises(RuntimeError, match=r"Deleting inputs is not allowed"):
        _run_pre_receive(monkeypatch, repo, baseline_sha, new_sha)


@pytest.mark.parametrize("suffix", [".pkl", ".pickle", ".PkL", ".PiCkLe"])
@pytest.mark.parametrize("prefix", ["wepp/runs", "swat/TxtInOut"])
def test_pickle_push_rejected_without_ref_or_log(tmp_path, suffix, prefix, monkeypatch):
    import shlex

    source = tmp_path / "source"
    source.mkdir()
    _init_repo(source)
    remote = tmp_path / "remote.git"
    _run_git(tmp_path, ["init", "--bare", "-b", "main", str(remote)])
    _run_git(source, ["remote", "add", "origin", str(remote)])
    _run_git(source, ["push", "origin", "main"])
    baseline = _run_git(remote, ["rev-parse", "main"])
    hook = remote / "hooks" / "pre-receive"
    hook.write_text(
        "#!/bin/sh\nexec " + shlex.quote(sys.executable)
        + " -m wepppy.weppcloud.bootstrap.pre_receive\n"
    )
    hook.chmod(0o755)
    monkeypatch.setenv("PYTHONPATH", str(Path(pre_receive.__file__).resolve().parents[3]))
    monkeypatch.setenv("HTTP_X_AUTH_USER", "pickle-test")
    artifact = source / prefix / "nested" / f"legacy{suffix}"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"N.")  # Inert NUL-free protocol-shaped bytes, never loaded.
    _commit_all(source, "add forbidden artifact")
    result = subprocess.run(
        ["git", "push", "origin", "main"], cwd=source,
        text=True, capture_output=True, check=False,
    )
    assert result.returncode != 0
    assert "Pickle files are not allowed" in result.stderr
    assert _run_git(remote, ["rev-parse", "main"]) == baseline
    assert not (remote / "bootstrap" / "push-log.ndjson").exists()


@pytest.mark.parametrize("suffix", [".pkl", ".PiCkLe", ".txt"])
@pytest.mark.parametrize("mode", ["main-first", "legacy-first", "fast-forward"])
def test_merge_from_existing_remote_branch_admission(tmp_path, suffix, mode, monkeypatch):
    import shlex

    source = tmp_path / "source"
    source.mkdir()
    _init_repo(source)
    inherited = source / "wepp" / "runs" / "inherited.pkl"
    inherited.parent.mkdir(parents=True)
    inherited.write_bytes(b"unchanged legacy bytes")
    _commit_all(source, "baseline legacy artifact")
    remote = tmp_path / "remote.git"
    _run_git(tmp_path, ["init", "--bare", "-b", "main", str(remote)])
    _run_git(source, ["remote", "add", "origin", str(remote)])
    _run_git(source, ["push", "origin", "main"])
    baseline = _run_git(remote, ["rev-parse", "main"])
    # Model an already reachable legacy branch from before suffix restriction.
    _run_git(source, ["checkout", "-b", "legacy"])
    artifact = source / "wepp" / "runs" / f"legacy{suffix}"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"N.")
    _commit_all(source, "legacy artifact")
    _run_git(source, ["push", "origin", "legacy"])
    _run_git(source, ["checkout", "main"])
    if mode == "fast-forward":
        _run_git(source, ["merge", "--ff-only", "legacy"])
    else:
        _run_git(source, ["commit", "--allow-empty", "-m", "diverge main"])
        if mode == "legacy-first":
            _run_git(source, ["checkout", "legacy"])
            _run_git(source, ["merge", "--no-ff", "main", "-m", "merge main"])
        else:
            _run_git(source, ["merge", "--no-ff", "legacy", "-m", "merge legacy inputs"])
    hook = remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable)
                    + " -m wepppy.weppcloud.bootstrap.pre_receive\n")
    hook.chmod(0o755)
    monkeypatch.setenv("PYTHONPATH", str(Path(pre_receive.__file__).resolve().parents[3]))
    monkeypatch.setenv("HTTP_X_AUTH_USER", "pickle-test")
    result = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=source,
                            text=True, capture_output=True, check=False)
    if suffix == ".txt":
        assert result.returncode == 0, result.stderr
        assert _run_git(remote, ["rev-parse", "main"]) == _run_git(source, ["rev-parse", "HEAD"])
        return
    assert result.returncode != 0
    assert "Pickle files are not allowed" in result.stderr
    assert _run_git(remote, ["rev-parse", "main"]) == baseline
    assert not (remote / "bootstrap" / "push-log.ndjson").exists()
