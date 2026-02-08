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
