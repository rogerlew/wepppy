from __future__ import annotations

import json
import os
import shutil
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit


def _extract_excludes(cmd: list[str]) -> list[str]:
    return [cmd[index + 1] for index, token in enumerate(cmd[:-1]) if token == "--exclude"]


def test_build_fork_rsync_cmd_directory_mode_has_no_nodir_cache_exclude() -> None:
    import wepppy.rq.project_rq as project

    cmd = project._build_fork_rsync_cmd("/tmp/target/", undisturbify=False)
    excludes = _extract_excludes(cmd)

    assert ".nodir/cache/***" not in excludes
    assert "wepp/runs" not in excludes
    assert "wepp/output" not in excludes
    assert "-v" not in cmd
    assert "--progress" not in cmd
    assert "--stats" in cmd
    assert cmd[-2:] == [".", "/tmp/target/"]


def test_build_fork_rsync_cmd_adds_undisturbify_excludes() -> None:
    import wepppy.rq.project_rq as project

    cmd = project._build_fork_rsync_cmd("/tmp/target/", undisturbify=True)
    excludes = _extract_excludes(cmd)

    assert ".nodir/cache/***" not in excludes
    assert "wepp/runs" in excludes
    assert "wepp/output" in excludes
    assert cmd[-2:] == [".", "/tmp/target/"]


def test_build_fork_rsync_cmd_adds_skip_wepp_runs_output_excludes() -> None:
    import wepppy.rq.project_rq as project

    cmd = project._build_fork_rsync_cmd(
        "/tmp/target/",
        undisturbify=False,
        skip_wepp_runs_output=True,
    )
    excludes = _extract_excludes(cmd)

    assert ".nodir/cache/***" not in excludes
    assert "wepp/runs" in excludes
    assert "wepp/output" in excludes
    assert cmd[-2:] == [".", "/tmp/target/"]


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_retargets_missing_grandparent(tmp_path: Path) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    scenario = destination / "_pups" / "omni" / "scenarios" / "prescribed_fire"
    scenario.mkdir(parents=True)
    (destination / "climate").mkdir()
    (destination / "watershed").mkdir()
    (destination / "dem").mkdir()
    (destination / "climate.nodb").write_text("{}", encoding="utf-8")
    (scenario / "climate").symlink_to("/wc1/runs/missing-grandparent/climate")
    (scenario / "climate.nodb").symlink_to("/wc1/runs/missing-grandparent/climate.nodb")
    unrelated = scenario / "unrelated"
    unrelated.symlink_to("/some/intentional/external/target")

    normalized = fork_helpers._normalize_fork_omni_links(str(destination))

    assert normalized == 2
    assert os.readlink(scenario / "climate") == "../../../../climate"
    assert os.readlink(scenario / "climate.nodb") == "../../../../climate.nodb"
    assert os.readlink(unrelated) == "/some/intentional/external/target"
    assert (scenario / "climate").resolve() == destination / "climate"


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_rejects_symlinked_child_without_touching_outside(
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    scenarios = destination / "_pups" / "omni" / "scenarios"
    scenarios.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_text("unchanged", encoding="utf-8")
    (scenarios / "malicious").symlink_to(outside, target_is_directory=True)

    with pytest.raises(OSError):
        fork_helpers._normalize_fork_omni_links(str(destination))

    assert sentinel.read_text(encoding="utf-8") == "unchanged"
    assert not list(outside.glob("*.fork-link-*.tmp"))


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_handles_contrast_wepp_runs(tmp_path: Path) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    root_runs = destination / "wepp" / "runs"
    root_runs.mkdir(parents=True)
    (root_runs / "p1.cli").write_text("climate", encoding="utf-8")
    contrast_runs = destination / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "runs"
    contrast_runs.mkdir(parents=True)
    (contrast_runs / "p1.cli").symlink_to("/wc1/runs/old/wepp/runs/p1.cli")

    assert fork_helpers._normalize_fork_omni_links(str(destination)) == 1
    assert os.readlink(contrast_runs / "p1.cli") == "../../../../../../wepp/runs/p1.cli"
    assert (contrast_runs / "p1.cli").resolve() == root_runs / "p1.cli"


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_skip_removes_only_contrast_run_links(
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    contrast_runs = destination / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "runs"
    contrast_runs.mkdir(parents=True)
    copied_link = contrast_runs / "p1.cli"
    copied_link.symlink_to("/wc1/runs/old/wepp/runs/p1.cli")
    materialized = contrast_runs / "p2.cli"
    materialized.write_text("retained", encoding="utf-8")

    assert fork_helpers._normalize_fork_omni_links(
        str(destination), skip_wepp_runs_output=True
    ) == 1
    assert not copied_link.exists()
    assert not copied_link.is_symlink()
    assert materialized.read_text(encoding="utf-8") == "retained"
    assert not list(contrast_runs.glob("*.fork-quarantine-*.tmp"))


@pytest.mark.parametrize("collection", ["scenarios", "contrasts"])
def test_normalize_fork_omni_links_preserves_collection_metadata(
    tmp_path: Path, collection: str
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    collection_dir = destination / "_pups" / "omni" / collection
    collection_dir.mkdir(parents=True)
    report = collection_dir / "build_report.ndjson"
    payload = b'{"status":"ok"}\n\x00exact-bytes'
    report.write_bytes(payload)

    assert fork_helpers._normalize_fork_omni_links(str(destination)) == 0
    assert report.read_bytes() == payload


@pytest.mark.parametrize("collection", ["scenarios", "contrasts"])
def test_normalize_fork_omni_links_rejects_other_collection_regular_file(
    tmp_path: Path, collection: str
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    collection_dir = destination / "_pups" / "omni" / collection
    collection_dir.mkdir(parents=True)
    (collection_dir / "unexpected.txt").write_text("foreign", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        fork_helpers._normalize_fork_omni_links(str(destination))


@pytest.mark.parametrize("collection", ["scenarios", "contrasts"])
@pytest.mark.parametrize("entry_type", ["symlink", "fifo"])
def test_normalize_fork_omni_links_rejects_nonregular_collection_metadata(
    tmp_path: Path, collection: str, entry_type: str
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    collection_dir = destination / "_pups" / "omni" / collection
    collection_dir.mkdir(parents=True)
    report = collection_dir / "build_report.ndjson"
    if entry_type == "symlink":
        report.symlink_to("/outside/metadata")
    else:
        os.mkfifo(report)

    with pytest.raises(NotADirectoryError):
        fork_helpers._normalize_fork_omni_links(str(destination))


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_rejects_symlinked_target_ancestor(
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    contrast_runs = destination / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "runs"
    contrast_runs.mkdir(parents=True)
    copied_link = contrast_runs / "p1.cli"
    original = "/wc1/runs/old/wepp/runs/p1.cli"
    copied_link.symlink_to(original)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "p1.cli"
    sentinel.write_text("unchanged", encoding="utf-8")
    (destination / "wepp").symlink_to(outside, target_is_directory=True)

    with pytest.raises(OSError):
        fork_helpers._normalize_fork_omni_links(str(destination))

    assert os.readlink(copied_link) == original
    assert sentinel.read_text(encoding="utf-8") == "unchanged"


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_detects_candidate_replacement_race(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    scenario = destination / "_pups" / "omni" / "scenarios" / "one"
    scenario.mkdir(parents=True)
    (destination / "climate").mkdir()
    link = scenario / "climate"
    link.symlink_to("/wc1/runs/old/climate")
    foreign = "/intentional/foreign/target"
    original_check = fork_helpers._same_inventoried_link
    raced = False

    def _race(dir_fd: int, action) -> bool:
        nonlocal raced
        if not raced:
            raced = True
            os.unlink(action.name, dir_fd=dir_fd)
            os.symlink(foreign, action.name, dir_fd=dir_fd)
        return original_check(dir_fd, action)

    monkeypatch.setattr(fork_helpers, "_same_inventoried_link", _race)

    with pytest.raises(RuntimeError, match="changed after preflight"):
        fork_helpers._normalize_fork_omni_links(str(destination))

    assert os.readlink(link) == foreign


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_does_not_overwrite_post_capture_race(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    scenario = destination / "_pups" / "omni" / "scenarios" / "one"
    scenario.mkdir(parents=True)
    (destination / "climate").mkdir()
    link = scenario / "climate"
    link.symlink_to("/wc1/runs/old/climate")
    original_symlink = os.symlink
    raced = False

    def _race_after_capture(target: str, name: str, *, dir_fd=None) -> None:
        nonlocal raced
        if name == "climate" and not raced:
            raced = True
            fd = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=dir_fd,
            )
            try:
                os.write(fd, b"foreign regular bytes")
            finally:
                os.close(fd)
        original_symlink(target, name, dir_fd=dir_fd)

    monkeypatch.setattr(fork_helpers.os, "symlink", _race_after_capture)

    with pytest.raises(RuntimeError, match="rollback failed"):
        fork_helpers._normalize_fork_omni_links(str(destination))

    assert link.read_bytes() == b"foreign regular bytes"


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_quarantine_preserves_raced_regular_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    contrast_runs = destination / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "runs"
    contrast_runs.mkdir(parents=True)
    candidate = contrast_runs / "p1.cli"
    candidate.symlink_to("/wc1/runs/old/wepp/runs/p1.cli")
    original_rename = fork_helpers._capture_to_quarantine
    raced = False

    def _race_before_quarantine(
        source_fd: int, src: str, destination_fd: int, dst: str
    ) -> None:
        nonlocal raced
        if src == "p1.cli" and not raced:
            raced = True
            os.unlink(src, dir_fd=source_fd)
            fd = os.open(
                src,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=source_fd,
            )
            try:
                os.write(fd, b"foreign regular bytes")
            finally:
                os.close(fd)
        original_rename(source_fd, src, destination_fd, dst)

    monkeypatch.setattr(fork_helpers, "_capture_to_quarantine", _race_before_quarantine)

    with pytest.raises(RuntimeError, match="changed before quarantine"):
        fork_helpers._normalize_fork_omni_links(
            str(destination), skip_wepp_runs_output=True
        )

    assert candidate.read_bytes() == b"foreign regular bytes"
    assert not list(contrast_runs.glob("*.fork-quarantine-*.tmp"))


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_confines_raced_directory_to_failed_destination(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    contrast_runs = destination / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "runs"
    contrast_runs.mkdir(parents=True)
    candidate = contrast_runs / "p1.cli"
    candidate.symlink_to("/wc1/runs/old/wepp/runs/p1.cli")
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"unchanged")
    original_capture = fork_helpers._capture_to_quarantine
    raced = False

    def _race_before_capture(
        source_fd: int, src: str, destination_fd: int, dst: str
    ) -> None:
        nonlocal raced
        if src == "p1.cli" and not raced:
            raced = True
            os.unlink(src, dir_fd=source_fd)
            os.mkdir(src, dir_fd=source_fd)
            raced_dir_fd = os.open(
                src, os.O_RDONLY | os.O_DIRECTORY, dir_fd=source_fd
            )
            try:
                fd = os.open(
                    "marker",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=raced_dir_fd,
                )
                os.close(fd)
            finally:
                os.close(raced_dir_fd)
        original_capture(source_fd, src, destination_fd, dst)

    monkeypatch.setattr(fork_helpers, "_capture_to_quarantine", _race_before_capture)

    with pytest.raises(RuntimeError, match="rollback failed"):
        fork_helpers._normalize_fork_omni_links(
            str(destination), skip_wepp_runs_output=True
        )

    assert not candidate.exists()
    quarantine_dirs = list(destination.glob(".fork-omni-quarantine-*"))
    assert len(quarantine_dirs) == 1
    captured = list(quarantine_dirs[0].iterdir())
    assert len(captured) == 1
    assert captured[0].is_dir()
    assert (captured[0] / "marker").exists()
    assert sentinel.read_bytes() == b"unchanged"


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_removal_rollback_restores_raw_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    contrast_runs = destination / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "runs"
    contrast_runs.mkdir(parents=True)
    candidate = contrast_runs / "p1.cli"
    raw_target = "../../../../../../old-root/wepp/runs/p1.cli"
    candidate.symlink_to(raw_target)
    original_matches = fork_helpers._quarantined_link_matches
    calls = 0

    def _fail_validation(dir_fd: int, quarantine: str, action) -> bool:
        nonlocal calls
        calls += 1
        if calls == 2:
            return False
        return original_matches(dir_fd, quarantine, action)

    monkeypatch.setattr(fork_helpers, "_quarantined_link_matches", _fail_validation)

    with pytest.raises(RuntimeError, match="quarantine changed"):
        fork_helpers._normalize_fork_omni_links(
            str(destination), skip_wepp_runs_output=True
        )

    assert os.readlink(candidate) == raw_target
    assert not list(contrast_runs.glob("*.fork-quarantine-*.tmp"))


@pytest.mark.parametrize(
    ("undisturbify", "skip_wepp_runs_output", "expected"),
    [(False, False, False), (False, True, True), (True, False, True), (True, True, True)],
)
def test_prepare_fork_run_passes_effective_skip_mode_to_omni_normalizer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    undisturbify: bool,
    skip_wepp_runs_output: bool,
    expected: bool,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    observed: list[bool] = []

    def _fake_rsync(**_kwargs) -> None:
        destination.mkdir()

    def _capture(_new_wd: str, *, skip_wepp_runs_output: bool = False) -> int:
        observed.append(skip_wepp_runs_output)
        raise RuntimeError("stop after mode capture")

    monkeypatch.setattr(fork_helpers.shutil, "which", lambda _name: "/usr/bin/rsync")
    monkeypatch.setattr(fork_helpers, "_run_rsync_with_bounded_output", _fake_rsync)
    monkeypatch.setattr(fork_helpers, "_normalize_fork_omni_links", _capture)

    with pytest.raises(RuntimeError, match="stop after mode capture"):
        fork_helpers.prepare_fork_run(
            "source-run",
            "destination-run",
            undisturbify=undisturbify,
            skip_wepp_runs_output=skip_wepp_runs_output,
            status_channel="source-run:fork",
            publish_status=lambda _channel, _message: None,
            get_wd=lambda _runid: str(source),
            get_primary_wd=lambda _runid: str(destination),
            wait_for_paths=lambda _paths, timeout_s=60.0: None,
            ron_cls=object(),
            disturbed_cls=object(),
            landuse_cls=object(),
            soils_cls=object(),
            initialize_ttl=None,
            clean_env_for_system_tools=lambda: {"PATH": "/usr/bin:/bin"},
        )

    assert observed == [expected]


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_rolls_back_after_publish_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    scenario = destination / "_pups" / "omni" / "scenarios" / "one"
    scenario.mkdir(parents=True)
    (destination / "climate").mkdir()
    (destination / "watershed").mkdir()
    originals = {
        "climate": "/wc1/runs/old/climate",
        "watershed": "/wc1/runs/old/watershed",
    }
    for name, target in originals.items():
        (scenario / name).symlink_to(target)
    original_symlink = os.symlink
    calls = 0

    def _fail_second(target: str, name: str, *, dir_fd=None) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected publish failure")
        original_symlink(target, name, dir_fd=dir_fd)

    monkeypatch.setattr(fork_helpers.os, "symlink", _fail_second)

    with pytest.raises(OSError, match="injected publish failure"):
        fork_helpers._normalize_fork_omni_links(str(destination))

    for name, target in originals.items():
        assert os.readlink(scenario / name) == target
    assert not list(destination.glob(".fork-omni-quarantine-*"))


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_normalize_fork_omni_links_revalidates_target_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    destination = tmp_path / "destination"
    scenario = destination / "_pups" / "omni" / "scenarios" / "one"
    scenario.mkdir(parents=True)
    target = destination / "climate"
    target.mkdir()
    link = scenario / "climate"
    original = "/wc1/runs/old/climate"
    link.symlink_to(original)
    original_symlink = os.symlink
    removed = False

    def _remove_target_after_publish(link_target: str, name: str, *, dir_fd=None) -> None:
        nonlocal removed
        original_symlink(link_target, name, dir_fd=dir_fd)
        if not removed:
            removed = True
            target.rmdir()

    monkeypatch.setattr(fork_helpers.os, "symlink", _remove_target_after_publish)

    with pytest.raises(FileNotFoundError):
        fork_helpers._normalize_fork_omni_links(str(destination))

    assert os.readlink(link) == original
    assert not list(destination.glob(".fork-omni-quarantine-*"))


def test_clean_env_for_system_tools_uses_sanitized_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import wepppy.rq.project_rq as project

    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("PATH", "/custom/bin")

    env = project._clean_env_for_system_tools()

    assert env["PATH"] == "/usr/sbin:/usr/bin:/bin"
    assert env["LANG"] == "en_US.UTF-8"
    assert env["LC_ALL"] == "C"
    assert "/custom/bin" not in env["PATH"]


def test_fork_rq_undisturbify_enqueues_finish_job(monkeypatch: pytest.MonkeyPatch) -> None:
    import wepppy.rq.project_rq as project

    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="job-fork"))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda _channel, _message: None)
    monkeypatch.setattr(project, "_reset_forked_run_job_markers", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        project._fork_helpers,
        "prepare_fork_run",
        lambda *args, **kwargs: "/tmp/forked-run",
    )

    final_wepp_job = object()
    monkeypatch.setattr(project, "run_wepp_rq", lambda _runid: final_wepp_job)
    monkeypatch.setattr(project, "redis_connection_kwargs", lambda _db: {})

    class _RedisStub:
        def __init__(self, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _tb):
            return False

    monkeypatch.setattr(project.redis, "Redis", _RedisStub)

    enqueue_calls: list[tuple[object, list[str] | None, object]] = []

    class _QueueStub:
        def __init__(self, connection=None) -> None:
            self.connection = connection

        def enqueue(self, func, args=None, depends_on=None):
            enqueue_calls.append((func, args, depends_on))
            return SimpleNamespace(id="queued")

    monkeypatch.setattr(project, "Queue", _QueueStub)

    project.fork_rq("source-run", "new-run", undisturbify=True)

    assert len(enqueue_calls) == 1
    func, args, depends_on = enqueue_calls[0]
    assert func is project._finish_fork_rq
    assert args == ["source-run"]
    assert depends_on is final_wepp_job


def test_fork_rq_reports_ttl_import_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq as project

    published: list[str] = []
    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="job-fork-ttl"))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda _channel, message: published.append(message))
    monkeypatch.setattr(project, "_reset_forked_run_job_markers", lambda *_args, **_kwargs: None)

    source_wd = tmp_path / "source"
    source_wd.mkdir(parents=True)
    target_wd = tmp_path / "target"

    monkeypatch.setattr(project, "get_wd", lambda _runid: str(source_wd))
    monkeypatch.setattr(project, "get_primary_wd", lambda _runid: str(target_wd))
    monkeypatch.setattr(project._fork_helpers.shutil, "which", lambda _name: "/usr/bin/rsync")
    monkeypatch.setattr(
        project._fork_helpers,
        "_run_rsync_with_bounded_output",
        lambda **_kwargs: target_wd.mkdir(parents=True),
    )

    # Simulate missing initialize_ttl symbol at import time.
    monkeypatch.setitem(
        sys.modules,
        "wepppy.weppcloud.utils.run_ttl",
        types.ModuleType("wepppy.weppcloud.utils.run_ttl"),
    )

    project.fork_rq("source-run", "new-run", undisturbify=False)

    assert any("STATUS TTL initialization failed" in message for message in published)


def test_fork_rq_uses_wrapper_helper_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    import wepppy.rq.project_rq as project

    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="job-fork-aliases"))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda _channel, _message: None)
    monkeypatch.setattr(project, "_reset_forked_run_job_markers", lambda *_args, **_kwargs: None)

    monkeypatch.setattr(
        project,
        "_build_fork_rsync_cmd",
        lambda run_right, undisturbify=False, skip_wepp_runs_output=False: [
            "patched-rsync",
            run_right,
            undisturbify,
            skip_wepp_runs_output,
        ],
    )
    monkeypatch.setattr(project, "_clean_env_for_system_tools", lambda: {"PATH": "patched"})

    captured: dict[str, object] = {}

    def _prepare(*_args, **kwargs):
        captured["cmd"] = kwargs["build_rsync_cmd"]("/tmp/target/", False, True)
        captured["env"] = kwargs["clean_env_for_system_tools"]()
        return "/tmp/forked-run"

    monkeypatch.setattr(project._fork_helpers, "prepare_fork_run", _prepare)

    project.fork_rq("source-run", "new-run", undisturbify=False, skip_wepp_runs_output=True)

    assert captured["cmd"] == ["patched-rsync", "/tmp/target/", False, True]
    assert captured["env"] == {"PATH": "patched"}


def test_run_rsync_with_bounded_output_emits_heartbeat_without_streaming_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    published: list[str] = []
    monkeypatch.setattr(fork_helpers, "FORK_RSYNC_HEARTBEAT_SECONDS", 0.01)

    fork_helpers._run_rsync_with_bounded_output(
        cmd=[
            sys.executable,
            "-u",
            "-c",
            "import time; print('summary line'); time.sleep(0.25)",
        ],
        run_left="/tmp",
        status_channel="source:fork",
        publish_status=lambda _channel, message: published.append(message),
        env=os.environ.copy(),
    )

    assert any(message.startswith(fork_helpers.FORK_RSYNC_HEARTBEAT_PREFIX) for message in published)
    assert "summary line" not in published
    assert any(message == "rsync summary:\nsummary line" for message in published)


def test_run_rsync_with_bounded_output_limits_summary_and_failure_tails() -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    published: list[str] = []
    fork_helpers._run_rsync_with_bounded_output(
        cmd=[
            sys.executable,
            "-c",
            "[print(f'line-{index}') for index in range(500)]",
        ],
        run_left="/tmp",
        status_channel="source:fork",
        publish_status=lambda _channel, message: published.append(message),
        env=os.environ.copy(),
    )

    summary = next(message for message in published if message.startswith("rsync summary:"))
    assert "line-0\n" not in summary
    assert "line-299\n" not in summary
    assert "line-300" in summary
    assert "line-499" in summary
    assert len(summary.splitlines()) == fork_helpers.FORK_RSYNC_TAIL_LINES + 1

    published.clear()
    with pytest.raises(RuntimeError, match="return code 7") as exc_info:
        fork_helpers._run_rsync_with_bounded_output(
            cmd=[
                sys.executable,
                "-c",
                "import sys; [print(f'err-{index}', file=sys.stderr) for index in range(500)]; raise SystemExit(7)",
            ],
            run_left="/tmp",
            status_channel="source:fork",
            publish_status=lambda _channel, message: published.append(message),
            env=os.environ.copy(),
        )

    error_text = str(exc_info.value)
    assert "err-0\n" not in error_text
    assert "err-299\n" not in error_text
    assert "err-300" in error_text
    assert "err-499" in error_text
    assert published == [error_text]


def test_fork_rq_invokes_reset_markers_with_new_run_context(monkeypatch: pytest.MonkeyPatch) -> None:
    import wepppy.rq.project_rq as project

    reset_calls: list[tuple[str, str, str]] = []
    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="job-fork-reset"))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda _channel, _message: None)
    monkeypatch.setattr(
        project._fork_helpers,
        "prepare_fork_run",
        lambda *args, **kwargs: "/tmp/new-run-wd",
    )
    monkeypatch.setattr(
        project,
        "_reset_forked_run_job_markers",
        lambda new_runid, new_wd, status_channel: reset_calls.append((new_runid, new_wd, status_channel)),
    )

    project.fork_rq("source-run", "new-run", undisturbify=False)

    assert reset_calls == [("new-run", "/tmp/new-run-wd", "source-run:fork")]


def test_fork_rq_reset_marker_failure_emits_fork_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wepppy.rq.project_rq as project

    published: list[str] = []
    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="job-fork-reset-fail"))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda _channel, message: published.append(message))
    monkeypatch.setattr(
        project._fork_helpers,
        "prepare_fork_run",
        lambda *args, **kwargs: "/tmp/new-run-wd",
    )

    def _raise_reset(*_args, **_kwargs):
        raise RuntimeError("reset marker failure")

    monkeypatch.setattr(project, "_reset_forked_run_job_markers", _raise_reset)

    with pytest.raises(RuntimeError, match="reset marker failure"):
        project.fork_rq("source-run", "new-run", undisturbify=False)

    assert any("rq:job-fork-reset-fail TRIGGER   fork FORK_FAILED" in msg for msg in published)
    assert any("rq:job-fork-reset-fail EXCEPTION fork_rq(source-run)" in msg for msg in published)


def test_reset_forked_run_job_markers_clears_wepp_hints_and_redis_job_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wepppy.rq.project_rq as project

    clear_cache_calls: list[tuple[str, str]] = []
    clear_lock_calls: list[tuple[str, str]] = []
    call_order: list[str] = []
    published: list[str] = []
    persisted_job_hints: list[tuple[object, object]] = []
    hdel_calls: list[tuple[str, str]] = []

    class _WeppStub:
        def persist_job_hint(self, *, job_id, job_key) -> None:
            call_order.append("persist_job_hint")
            persisted_job_hints.append((job_id, job_key))

    class _RedisStub:
        def hdel(self, run_id: str, key: str) -> None:
            hdel_calls.append((run_id, key))

    class _PrepStub:
        run_id = "forked-run"

        def __init__(self) -> None:
            self.redis = _RedisStub()
            self.dump_calls = 0
            self.archive_job_id = "archive-job-9"
            self.clear_archive_calls = 0

        def get_rq_job_ids(self) -> dict[str, str]:
            return {
                "run_wepp_rq": "job-old-1",
                "run_wepp_watershed_rq": "job-old-2",
            }

        def dump(self) -> None:
            self.dump_calls += 1

        def get_archive_job_id(self) -> str | None:
            return self.archive_job_id

        def clear_archive_job_id(self) -> None:
            self.clear_archive_calls += 1
            self.archive_job_id = None

    prep_stub = _PrepStub()

    def _clear_nodb_file_cache(runid: str, *, pup_relpath: str) -> None:
        call_order.append("clear_nodb_file_cache")
        clear_cache_calls.append((runid, str(pup_relpath)))

    def _clear_locks(runid: str, *, pup_relpath: str) -> None:
        call_order.append("clear_locks")
        clear_lock_calls.append((runid, str(pup_relpath)))

    monkeypatch.setattr(
        project,
        "clear_nodb_file_cache",
        _clear_nodb_file_cache,
    )
    monkeypatch.setattr(
        project,
        "clear_locks",
        _clear_locks,
    )
    monkeypatch.setattr(project.Wepp, "tryGetInstance", lambda _wd: _WeppStub())
    monkeypatch.setattr(project.RedisPrep, "tryGetInstance", lambda _wd: prep_stub)
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda _channel, message: published.append(message))

    project._reset_forked_run_job_markers("forked-run", "/tmp/forked-run", "source-run:fork")

    assert clear_cache_calls == [("forked-run", "wepp.nodb")]
    assert clear_lock_calls == [("forked-run", "wepp.nodb")]
    assert call_order[:3] == ["clear_nodb_file_cache", "clear_locks", "persist_job_hint"]
    assert persisted_job_hints == [(None, None)]
    assert hdel_calls == [
        ("forked-run", "rq:run_wepp_rq"),
        ("forked-run", "rq:run_wepp_watershed_rq"),
    ]
    assert prep_stub.dump_calls == 1
    assert prep_stub.clear_archive_calls == 1
    assert "Clearing inherited job markers...\n" in published
    assert "Clearing inherited job markers... done.\n" in published


def test_reset_forked_run_job_markers_propagates_nodb_lock_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wepppy.rq.project_rq as project
    from wepppy.nodb.base import NoDbAlreadyLockedError

    monkeypatch.setattr(project, "clear_nodb_file_cache", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(project, "clear_locks", lambda *_args, **_kwargs: [])

    class _WeppStub:
        def persist_job_hint(self, *, job_id, job_key) -> None:
            raise NoDbAlreadyLockedError("wepp.nodb lock is still active")

    monkeypatch.setattr(project.Wepp, "tryGetInstance", lambda _wd: _WeppStub())
    monkeypatch.setattr(project.RedisPrep, "tryGetInstance", lambda _wd: None)
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda *_args, **_kwargs: None)

    with pytest.raises(NoDbAlreadyLockedError, match="lock is still active"):
        project._reset_forked_run_job_markers("forked-run", "/tmp/forked-run", "source-run:fork")


def test_clear_reports_cache_removes_cache_directory(tmp_path: Path) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    run_wd = tmp_path / "run"
    cache_dir = run_wd / "wepp" / "reports" / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "stale.parquet").write_text("stale")

    published: list[str] = []
    fork_helpers._clear_reports_cache(
        str(run_wd),
        status_channel="run:fork",
        publish_status=lambda _channel, message: published.append(message),
    )

    assert not cache_dir.exists()
    assert "Clearing WEPP reports cache...\n" in published
    assert "Clearing WEPP reports cache... done.\n" in published


def test_clear_reports_cache_reports_missing_directory(tmp_path: Path) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    run_wd = tmp_path / "run"
    run_wd.mkdir(parents=True)
    published: list[str] = []

    fork_helpers._clear_reports_cache(
        str(run_wd),
        status_channel="run:fork",
        publish_status=lambda _channel, message: published.append(message),
    )

    assert "Clearing WEPP reports cache...\n" in published
    assert "No WEPP reports cache directory to clear.\n" in published


def test_clear_export_dir_removes_and_recreates_directory(tmp_path: Path) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    run_wd = tmp_path / "run"
    export_dir = run_wd / "export"
    export_dir.mkdir(parents=True)
    stale_file = export_dir / "stale.txt"
    stale_file.write_text("stale", encoding="utf-8")

    published: list[str] = []
    fork_helpers._clear_export_dir(
        str(run_wd),
        status_channel="run:fork",
        publish_status=lambda _channel, message: published.append(message),
    )

    assert export_dir.exists()
    assert export_dir.is_dir()
    assert not stale_file.exists()
    assert "Clearing export directory...\n" in published
    assert "Clearing export directory... done.\n" in published


def test_clear_export_dir_creates_missing_directory(tmp_path: Path) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    run_wd = tmp_path / "run"
    run_wd.mkdir(parents=True)
    export_dir = run_wd / "export"
    published: list[str] = []

    fork_helpers._clear_export_dir(
        str(run_wd),
        status_channel="run:fork",
        publish_status=lambda _channel, message: published.append(message),
    )

    assert export_dir.exists()
    assert export_dir.is_dir()
    assert "Clearing export directory...\n" in published
    assert "Clearing export directory... done.\n" in published


def test_clear_query_engine_catalog_cache_removes_catalog_and_cache(tmp_path: Path) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    run_wd = tmp_path / "run"
    query_engine_root = run_wd / "_query_engine"
    query_engine_cache = query_engine_root / "cache"
    query_engine_cache.mkdir(parents=True)
    (query_engine_cache / "stale.bin").write_text("stale", encoding="utf-8")
    catalog_path = query_engine_root / "catalog.json"
    catalog_path.write_text('{"files": []}', encoding="utf-8")
    instructions_path = query_engine_root / "mcp_integration_instructions.md"
    instructions_path.write_text("keep", encoding="utf-8")

    published: list[str] = []
    fork_helpers._clear_query_engine_catalog_cache(
        str(run_wd),
        status_channel="run:fork",
        publish_status=lambda _channel, message: published.append(message),
    )

    assert not query_engine_cache.exists()
    assert not catalog_path.exists()
    assert instructions_path.exists()
    assert "Clearing query engine catalog cache...\n" in published
    assert "Clearing query engine catalog cache... done.\n" in published


def test_clear_query_engine_catalog_cache_reports_missing_artifacts(tmp_path: Path) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    run_wd = tmp_path / "run"
    run_wd.mkdir(parents=True)
    published: list[str] = []

    fork_helpers._clear_query_engine_catalog_cache(
        str(run_wd),
        status_channel="run:fork",
        publish_status=lambda _channel, message: published.append(message),
    )

    assert "Clearing query engine catalog cache...\n" in published
    assert "No query engine catalog cache artifacts to clear.\n" in published


def test_prepare_fork_run_normalizes_batch_identity_without_touching_pups(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    source_wd = tmp_path / "source-batch-leaf"
    target_wd = tmp_path / "interactive-run"
    source_wd.mkdir(parents=True)

    def _write_controller(path: Path, *, wd: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "py/object": "example.Controller",
                    "py/state": {
                        "_run_group": "batch",
                        "_group_name": "example-batch",
                        "wd": str(wd),
                        "preserved": {"value": 42},
                    },
                }
            ),
            encoding="utf-8",
        )

    _write_controller(source_wd / "ash.nodb", wd=source_wd)
    child_path = source_wd / "_pups" / "omni" / "scenario" / "ash.nodb"
    _write_controller(child_path, wd=child_path.parent)
    child_before = child_path.read_bytes()
    (source_wd / "run_metadata.json").write_text(
        json.dumps(
            {
                "runid": "batch;;example-batch;;WA-10",
                "batch_name": "example-batch",
                "status": "success",
            }
        ),
        encoding="utf-8",
    )

    def _fake_rsync(**kwargs) -> None:
        run_left = Path(kwargs["run_left"].rstrip("/"))
        run_right = Path(kwargs["cmd"][-1].rstrip("/"))
        shutil.copytree(run_left, run_right)

    monkeypatch.setattr(fork_helpers.shutil, "which", lambda _name: "/usr/bin/rsync")
    monkeypatch.setattr(fork_helpers, "_run_rsync_with_bounded_output", _fake_rsync)
    published: list[str] = []

    result = fork_helpers.prepare_fork_run(
        "batch;;example-batch;;WA-10",
        "interactive-run",
        undisturbify=False,
        status_channel="batch-source:fork",
        publish_status=lambda _channel, message: published.append(message),
        get_wd=lambda _runid: str(source_wd),
        get_primary_wd=lambda _runid: str(target_wd),
        wait_for_paths=lambda _paths, timeout_s=60.0: None,
        ron_cls=object(),
        disturbed_cls=object(),
        landuse_cls=object(),
        soils_cls=object(),
        initialize_ttl=None,
        clean_env_for_system_tools=lambda: {
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        },
    )

    assert result == str(target_wd)
    root_state = json.loads((target_wd / "ash.nodb").read_text())["py/state"]
    assert root_state["_run_group"] is None
    assert root_state["_group_name"] is None
    assert root_state["wd"] == str(target_wd)
    assert root_state["preserved"] == {"value": 42}
    assert (target_wd / "_pups" / "omni" / "scenario" / "ash.nodb").read_bytes() == child_before
    assert not (target_wd / "run_metadata.json").exists()
    assert "Normalized grouped-run identity in 1 root .nodb files.\n" in published
    assert "Removed copied batch run_metadata.json.\n" in published


def test_non_batch_fork_keeps_non_batch_run_metadata(tmp_path: Path) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    metadata_path = tmp_path / "run_metadata.json"
    metadata_path.write_text('{"runid": "ordinary-run"}', encoding="utf-8")

    removed = fork_helpers._remove_copied_batch_run_metadata(
        str(tmp_path),
        "ordinary-run",
    )

    assert removed is False
    assert metadata_path.exists()


def test_contaminated_ordinary_fork_removes_copied_batch_metadata(
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    metadata_path = tmp_path / "run_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "runid": "batch;;example-batch;;WA-10",
                "batch_name": "example-batch",
            }
        ),
        encoding="utf-8",
    )

    removed = fork_helpers._remove_copied_batch_run_metadata(
        str(tmp_path),
        "ordinary-contaminated-run",
    )

    assert removed is True
    assert not metadata_path.exists()


@pytest.mark.parametrize(
    ("payload", "source_runid", "message"),
    [
        (
            {"runid": "batch;;example-batch;;WA-10"},
            "ordinary-run",
            "Incomplete batch identity",
        ),
        (
            {"batch_name": "example-batch"},
            "ordinary-run",
            "Incomplete batch identity",
        ),
        (
            {
                "runid": "batch;;example-batch;;WA-10",
                "batch_name": "different-batch",
            },
            "ordinary-run",
            "Conflicting batch names",
        ),
        (
            {"runid": "ordinary-run"},
            "batch;;example-batch;;WA-10",
            "Batch fork source has non-batch",
        ),
        (
            {"runid": "batch;;example-batch;;WA-10", "batch_name": ""},
            "ordinary-run",
            "Invalid batch_name",
        ),
    ],
)
def test_copied_batch_metadata_rejects_ambiguous_identity(
    tmp_path: Path,
    payload: dict[str, object],
    source_runid: str,
    message: str,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    metadata_path = tmp_path / "run_metadata.json"
    metadata_path.write_text(json.dumps(payload), encoding="utf-8")
    before = metadata_path.read_bytes()

    with pytest.raises(ValueError, match=message):
        fork_helpers._remove_copied_batch_run_metadata(
            str(tmp_path),
            source_runid,
        )

    assert metadata_path.read_bytes() == before


@pytest.mark.parametrize(
    ("run_group", "group_name", "message"),
    [
        ("culvert", "culvert-group", "non-batch run_group"),
        (None, "orphaned-group", "Inconsistent grouped-run identity"),
        ("batch", None, "lacks a valid group_name"),
    ],
)
def test_fork_identity_normalization_rejects_unsafe_group_state(
    run_group: str | None,
    group_name: str | None,
    message: str,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    text = json.dumps(
        {
            "py/object": "example.Controller",
            "py/state": {
                "_run_group": run_group,
                "_group_name": group_name,
            },
        }
    )

    with pytest.raises(ValueError, match=message):
        fork_helpers._normalize_interactive_fork_nodb_identity(
            text,
            path="/tmp/unsafe.nodb",
        )


def test_fork_identity_normalization_rejects_non_json_nodb() -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    with pytest.raises(ValueError, match="Invalid NoDb JSON"):
        fork_helpers._normalize_interactive_fork_nodb_identity(
            "not-json",
            path="/tmp/invalid.nodb",
        )


def test_atomic_fork_write_preserves_original_on_replace_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    target = tmp_path / "ash.nodb"
    target.write_text('{"original": true}', encoding="utf-8")
    original = target.read_bytes()

    def _fail_replace(_source: str, _target: str) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(fork_helpers.os, "replace", _fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        fork_helpers._atomic_write_fork_text(target.as_posix(), '{"updated": true}')

    assert target.read_bytes() == original
    assert list(tmp_path.iterdir()) == [target]


def test_prepare_fork_run_rejects_root_nodb_symlink_without_mutating_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    source_wd = tmp_path / "source-batch-leaf"
    target_wd = tmp_path / "interactive-run"
    source_wd.mkdir(parents=True)
    external = tmp_path / "external.nodb"
    external.write_text(
        json.dumps(
            {
                "py/object": "example.Controller",
                "py/state": {
                    "_run_group": "batch",
                    "_group_name": "example-batch",
                },
            }
        ),
        encoding="utf-8",
    )
    external_before = external.read_bytes()
    (source_wd / "ash.nodb").symlink_to(external)

    def _fake_rsync(**kwargs) -> None:
        run_left = Path(kwargs["run_left"].rstrip("/"))
        run_right = Path(kwargs["cmd"][-1].rstrip("/"))
        shutil.copytree(run_left, run_right, symlinks=True)

    monkeypatch.setattr(fork_helpers.shutil, "which", lambda _name: "/usr/bin/rsync")
    monkeypatch.setattr(fork_helpers, "_run_rsync_with_bounded_output", _fake_rsync)

    with pytest.raises(ValueError, match="regular non-symlink file"):
        fork_helpers.prepare_fork_run(
            "batch;;example-batch;;WA-10",
            "interactive-run",
            undisturbify=False,
            status_channel="batch-source:fork",
            publish_status=lambda _channel, _message: None,
            get_wd=lambda _runid: str(source_wd),
            get_primary_wd=lambda _runid: str(target_wd),
            wait_for_paths=lambda _paths, timeout_s=60.0: None,
            ron_cls=object(),
            disturbed_cls=object(),
            landuse_cls=object(),
            soils_cls=object(),
            initialize_ttl=None,
            clean_env_for_system_tools=lambda: {
                "PATH": "/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
            },
        )

    assert external.read_bytes() == external_before
    assert (target_wd / "ash.nodb").is_symlink()


def _prepare_identity_fork(
    *,
    fork_helpers,
    source_wd: Path,
    target_wd: Path,
    source_runid: str = "batch;;example-batch;;WA-10",
) -> str:
    return fork_helpers.prepare_fork_run(
        source_runid,
        "interactive-run",
        undisturbify=False,
        status_channel="batch-source:fork",
        publish_status=lambda _channel, _message: None,
        get_wd=lambda _runid: str(source_wd),
        get_primary_wd=lambda _runid: str(target_wd),
        wait_for_paths=lambda _paths, timeout_s=60.0: None,
        ron_cls=object(),
        disturbed_cls=object(),
        landuse_cls=object(),
        soils_cls=object(),
        initialize_ttl=None,
        clean_env_for_system_tools=lambda: {
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        },
    )


def test_prepare_fork_run_preflights_all_roots_before_first_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    source_wd = tmp_path / "source"
    target_wd = tmp_path / "target"
    source_wd.mkdir()
    first_path = source_wd / "a.nodb"
    first_path.write_text(
        json.dumps(
            {
                "py/state": {
                    "_run_group": "batch",
                    "_group_name": "example-batch",
                    "wd": str(source_wd),
                }
            }
        ),
        encoding="utf-8",
    )
    (source_wd / "z.nodb").write_text("not-json", encoding="utf-8")
    first_before = first_path.read_bytes()

    def _fake_rsync(**kwargs) -> None:
        shutil.copytree(
            Path(kwargs["run_left"].rstrip("/")),
            Path(kwargs["cmd"][-1].rstrip("/")),
        )

    monkeypatch.setattr(fork_helpers.shutil, "which", lambda _name: "/usr/bin/rsync")
    monkeypatch.setattr(fork_helpers, "_run_rsync_with_bounded_output", _fake_rsync)

    with pytest.raises(ValueError, match="Invalid NoDb JSON"):
        _prepare_identity_fork(
            fork_helpers=fork_helpers,
            source_wd=source_wd,
            target_wd=target_wd,
        )

    assert (target_wd / "a.nodb").read_bytes() == first_before


@pytest.mark.parametrize(
    ("source_runid", "root_groups"),
    [
        ("batch;;source-batch;;WA-10", ("different-batch",)),
        ("ordinary-run", ("batch-a", "batch-b")),
    ],
)
def test_prepare_fork_run_rejects_cross_file_batch_name_disagreement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    source_runid: str,
    root_groups: tuple[str, ...],
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    source_wd = tmp_path / "source"
    target_wd = tmp_path / "target"
    source_wd.mkdir()
    source_bytes: dict[str, bytes] = {}
    for index, group_name in enumerate(root_groups):
        filename = f"controller-{index}.nodb"
        path = source_wd / filename
        path.write_text(
            json.dumps(
                {
                    "py/state": {
                        "_run_group": "batch",
                        "_group_name": group_name,
                        "wd": str(source_wd),
                    }
                }
            ),
            encoding="utf-8",
        )
        source_bytes[filename] = path.read_bytes()

    def _fake_rsync(**kwargs) -> None:
        shutil.copytree(
            Path(kwargs["run_left"].rstrip("/")),
            Path(kwargs["cmd"][-1].rstrip("/")),
        )

    monkeypatch.setattr(fork_helpers.shutil, "which", lambda _name: "/usr/bin/rsync")
    monkeypatch.setattr(fork_helpers, "_run_rsync_with_bounded_output", _fake_rsync)

    with pytest.raises(ValueError, match="Conflicting batch names"):
        _prepare_identity_fork(
            fork_helpers=fork_helpers,
            source_wd=source_wd,
            target_wd=target_wd,
            source_runid=source_runid,
        )

    assert {
        filename: (target_wd / filename).read_bytes()
        for filename in source_bytes
    } == source_bytes


def test_prepare_fork_run_rolls_back_earlier_root_after_write_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    source_wd = tmp_path / "source"
    target_wd = tmp_path / "target"
    source_wd.mkdir()
    source_bytes: dict[str, bytes] = {}
    for filename in ("a.nodb", "z.nodb"):
        path = source_wd / filename
        path.write_text(
            json.dumps(
                {
                    "py/state": {
                        "_run_group": "batch",
                        "_group_name": "example-batch",
                        "wd": str(source_wd),
                    }
                }
            ),
            encoding="utf-8",
        )
        source_bytes[filename] = path.read_bytes()

    def _fake_rsync(**kwargs) -> None:
        shutil.copytree(
            Path(kwargs["run_left"].rstrip("/")),
            Path(kwargs["cmd"][-1].rstrip("/")),
        )

    real_atomic_write = fork_helpers._atomic_write_fork_text
    calls = 0

    def _fail_second_write(path: str, text: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second write failure")
        real_atomic_write(path, text)

    monkeypatch.setattr(fork_helpers.shutil, "which", lambda _name: "/usr/bin/rsync")
    monkeypatch.setattr(fork_helpers, "_run_rsync_with_bounded_output", _fake_rsync)
    monkeypatch.setattr(fork_helpers, "_atomic_write_fork_text", _fail_second_write)

    with pytest.raises(OSError, match="simulated second write failure"):
        _prepare_identity_fork(
            fork_helpers=fork_helpers,
            source_wd=source_wd,
            target_wd=target_wd,
        )

    assert {
        filename: (target_wd / filename).read_bytes()
        for filename in source_bytes
    } == source_bytes


def test_prepare_fork_run_undisturbify_clears_new_run_scoped_nodb_cache(
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    source_wd = tmp_path / "source-run"
    target_wd = tmp_path / "target-run"
    source_wd.mkdir(parents=True, exist_ok=True)

    for nodb_name in ("ron.nodb", "wepp.nodb", "landuse.nodb", "soils.nodb", "disturbed.nodb"):
        (source_wd / nodb_name).write_text(
            json.dumps({"py/state": {"wd": str(source_wd), "runid": "source-run"}}),
            encoding="utf-8",
        )

    disturbed_dir = source_wd / "disturbed"
    disturbed_dir.mkdir(parents=True, exist_ok=True)
    (disturbed_dir / "source_sbs.tif").write_text("source", encoding="ascii")
    (disturbed_dir / "sbs_4class.tif").write_text("4class", encoding="ascii")

    cache_dir = source_wd / "wepp" / "reports" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "stale.bin").write_text("stale", encoding="ascii")
    (source_wd / "export").mkdir(parents=True, exist_ok=True)
    (source_wd / "export" / "stale.txt").write_text("stale", encoding="ascii")
    query_cache = source_wd / "_query_engine" / "cache"
    query_cache.mkdir(parents=True, exist_ok=True)
    (query_cache / "stale.bin").write_text("stale", encoding="ascii")
    (source_wd / "_query_engine" / "catalog.json").write_text("{}", encoding="ascii")

    class RonStub:
        _instances: dict[str, "RonStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.scenario = "Disturbed"

        @classmethod
        def getInstance(cls, wd: str) -> "RonStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    class DisturbedStub:
        _instances: dict[str, "DisturbedStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.remove_calls = 0

        @classmethod
        def getInstance(cls, wd: str) -> "DisturbedStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def remove_sbs(self) -> None:
            self.remove_calls += 1

    class LanduseStub:
        _instances: dict[str, "LanduseStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.build_calls = 0

        @classmethod
        def getInstance(cls, wd: str) -> "LanduseStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def build(self) -> None:
            self.build_calls += 1

    class SoilsStub:
        _instances: dict[str, "SoilsStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.build_calls = 0

        @classmethod
        def getInstance(cls, wd: str) -> "SoilsStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def build(self) -> None:
            self.build_calls += 1

    published: list[str] = []
    clear_calls: list[tuple[str, str]] = []
    mutate_calls: list[tuple[str, str]] = []

    def _fake_rsync(**kwargs) -> None:
        cmd = kwargs["cmd"]
        run_left = Path(kwargs["run_left"].rstrip("/"))
        run_right = Path(cmd[-1].rstrip("/"))
        run_right.mkdir(parents=True, exist_ok=True)
        for child in run_left.iterdir():
            destination = run_right / child.name
            if child.is_dir():
                shutil.copytree(child, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(child, destination)

    def _mutate_root(
        _wd: str,
        _root: str,
        callback,
        *,
        purpose: str,
    ):
        mutate_calls.append((_root, purpose))
        return callback()

    new_wd = fork_helpers.prepare_fork_run(
        "source-run",
        "new-run",
        undisturbify=True,
        status_channel="run:fork",
        publish_status=lambda _channel, message: published.append(message),
        get_wd=lambda _runid: str(source_wd),
        get_primary_wd=lambda _runid: str(target_wd),
        wait_for_paths=lambda _paths, timeout_s=60.0: None,
        ron_cls=RonStub,
        disturbed_cls=DisturbedStub,
        landuse_cls=LanduseStub,
        soils_cls=SoilsStub,
        initialize_ttl=None,
        mutate_root_fn=_mutate_root,
        clear_nodb_cache_fn=lambda runid, *, pup_relpath: clear_calls.append((runid, str(pup_relpath))),
        clean_env_for_system_tools=lambda: {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
    )

    assert new_wd == str(target_wd)
    assert clear_calls == [
        ("new-run", "ron.nodb"),
        ("new-run", "disturbed.nodb"),
        ("new-run", "landuse.nodb"),
        ("new-run", "soils.nodb"),
    ]

    ron = RonStub.getInstance(str(target_wd))
    disturbed = DisturbedStub.getInstance(str(target_wd))
    landuse = LanduseStub.getInstance(str(target_wd))
    soils = SoilsStub.getInstance(str(target_wd))

    assert ron.scenario == "Undisturbed"
    assert disturbed.remove_calls == 1
    assert landuse.build_calls == 1
    assert soils.build_calls == 1
    assert (target_wd / "disturbed" / "source_sbs.tif").read_text(encoding="ascii") == "source"
    assert (target_wd / "disturbed" / "sbs_4class.tif").read_text(encoding="ascii") == "4class"
    assert mutate_calls == [
        ("landuse", "fork-undisturbify-build-landuse"),
        ("soils", "fork-undisturbify-build-soils"),
    ]
    assert any("Undisturbifying Project..." in message for message in published)


def test_prepare_fork_run_skip_wepp_copy_ensures_output_dirs(
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    source_wd = tmp_path / "source-run"
    target_wd = tmp_path / "target-run"
    source_wd.mkdir(parents=True, exist_ok=True)
    (source_wd / "ron.nodb").write_text(
        json.dumps({"py/state": {"wd": str(source_wd), "runid": "source-run"}}),
        encoding="utf-8",
    )
    source_runs_dir = source_wd / "wepp" / "runs"
    source_runs_dir.mkdir(parents=True, exist_ok=True)
    (source_runs_dir / "source-only.run").write_text("run", encoding="ascii")
    source_output_dir = source_wd / "wepp" / "output"
    source_output_dir.mkdir(parents=True, exist_ok=True)
    (source_output_dir / "source-only.txt").write_text("output", encoding="ascii")

    captured_cmd: list[str] = []

    def _fake_rsync(**kwargs) -> None:
        run_left = Path(kwargs["run_left"].rstrip("/"))
        cmd = kwargs["cmd"]
        captured_cmd.extend(cmd)
        run_right = Path(cmd[-1].rstrip("/"))
        excludes = _extract_excludes(cmd)

        def _ignore(path: str, names: list[str]) -> set[str]:
            rel_root = os.path.relpath(path, run_left)
            rel_root = "" if rel_root == "." else rel_root.replace(os.sep, "/")
            ignored: set[str] = set()
            for name in names:
                rel_path = name if not rel_root else f"{rel_root}/{name}"
                if any(
                    rel_path == excluded or rel_path.startswith(f"{excluded}/")
                    for excluded in excludes
                ):
                    ignored.add(name)
            return ignored

        shutil.copytree(run_left, run_right, dirs_exist_ok=True, ignore=_ignore)

    published: list[str] = []
    original_rsync_runner = fork_helpers._run_rsync_with_bounded_output
    fork_helpers._run_rsync_with_bounded_output = _fake_rsync
    try:
        new_wd = fork_helpers.prepare_fork_run(
            "source-run",
            "new-run",
            undisturbify=False,
            skip_wepp_runs_output=True,
            status_channel="run:fork",
            publish_status=lambda _channel, message: published.append(message),
            get_wd=lambda _runid: str(source_wd),
            get_primary_wd=lambda _runid: str(target_wd),
            wait_for_paths=lambda _paths, timeout_s=60.0: None,
            ron_cls=object(),
            disturbed_cls=object(),
            landuse_cls=object(),
            soils_cls=object(),
            initialize_ttl=None,
            clean_env_for_system_tools=lambda: {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    finally:
        fork_helpers._run_rsync_with_bounded_output = original_rsync_runner

    assert new_wd == str(target_wd)
    assert (target_wd / "wepp" / "runs").is_dir()
    assert (target_wd / "wepp" / "output").is_dir()
    assert "wepp/runs" in _extract_excludes(captured_cmd)
    assert "wepp/output" in _extract_excludes(captured_cmd)
    assert not (target_wd / "wepp" / "runs" / "source-only.run").exists()
    assert not (target_wd / "wepp" / "output" / "source-only.txt").exists()
    assert any("Ensured empty directories exist: wepp/runs and wepp/output." in message for message in published)
