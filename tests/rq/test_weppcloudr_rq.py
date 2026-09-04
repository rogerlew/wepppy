from __future__ import annotations

import inspect
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.rq.weppcloudr_rq as weppcloudr_rq
from wepppy.rq.weppcloudr_backends import KubernetesRenderError
from wepppy.rq.weppcloudr_rq import (
    WeppcloudRError,
    _assert_no_retired_root_resources,
    _disable_job_retries,
    _record_kubernetes_error,
    _validate_run_paths,
    _write_command_logs,
    render_deval_details_rq,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _approve_test_run_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WEPPCLOUDR_RUN_ROOTS", str(tmp_path))


def test_render_deval_details_rq_accepts_legacy_parquet_overrides_kwarg() -> None:
    signature = inspect.signature(render_deval_details_rq)
    assert "parquet_overrides" in signature.parameters


def test_kubernetes_retry_helpers_preserve_only_transient_api_retries() -> None:
    job = SimpleNamespace(
        id="job-1",
        meta={"error": "stale", "error_id": "stale"},
        retries_left=2,
        save_meta=lambda: None,
        save=lambda: None,
    )

    _record_kubernetes_error(
        job,
        KubernetesRenderError("weppcloudr_k8s_api_unavailable", "unavailable"),
    )
    assert job.retries_left == 2
    assert "error" not in job.meta
    assert "error_id" not in job.meta

    exhausted = SimpleNamespace(
        id="job-exhausted",
        meta={},
        retries_left=0,
        save_meta=lambda: None,
        save=lambda: None,
    )
    _record_kubernetes_error(
        exhausted,
        KubernetesRenderError("weppcloudr_k8s_api_unavailable", "unavailable"),
    )
    assert exhausted.meta["error"] == {
        "code": "weppcloudr_k8s_api_unavailable",
        "message": "WEPPcloudR render failed.",
    }
    assert exhausted.meta["error_id"] == "job-exhausted"

    _record_kubernetes_error(
        job,
        KubernetesRenderError("weppcloudr_k8s_oom_killed", "terminal"),
    )
    assert job.retries_left == 0
    assert job.meta["error"]["code"] == "weppcloudr_k8s_oom_killed"

    job.retries_left = 3
    _disable_job_retries(job)
    assert job.retries_left == 0


def test_kubernetes_legacy_job_without_run_root_disables_retry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job = SimpleNamespace(
        id="job-legacy",
        meta={},
        retries_left=3,
        save_meta=lambda: None,
        save=lambda: None,
    )
    monkeypatch.setattr(weppcloudr_rq, "get_current_job", lambda: job)
    monkeypatch.setattr(weppcloudr_rq.StatusMessenger, "publish", lambda *_args: None)

    with pytest.raises(WeppcloudRError, match="rejects legacy jobs"):
        render_deval_details_rq(
            "run-1", "cfg", str(tmp_path), backend="kubernetes-job"
        )

    assert job.retries_left == 0


def test_assert_no_retired_root_resources_allows_clean_directory(tmp_path: Path) -> None:
    (tmp_path / "landuse").mkdir()
    _assert_no_retired_root_resources(tmp_path)


def test_assert_no_retired_root_resources_rejects_retired_sidecars(tmp_path: Path) -> None:
    (tmp_path / "landuse.parquet").write_text("x", encoding="utf-8")
    (tmp_path / "climate.wepp_cli.parquet").write_text("x", encoding="utf-8")

    with pytest.raises(WeppcloudRError, match="Migration required"):
        _assert_no_retired_root_resources(tmp_path)


def test_assert_no_retired_root_resources_rejects_mixed_canonical_and_sidecar_state(
    tmp_path: Path,
) -> None:
    (tmp_path / "landuse").mkdir()
    (tmp_path / "landuse" / "landuse.parquet").write_text("canonical", encoding="utf-8")
    (tmp_path / "landuse.parquet").write_text("retired", encoding="utf-8")

    with pytest.raises(WeppcloudRError, match="Migration required"):
        _assert_no_retired_root_resources(tmp_path)


def test_command_logs_are_bounded_sanitized_and_protected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEPPCLOUDR_LOG_MAX_BYTES", "1024")
    log_dir = tmp_path / "_logs" / "weppcloudr"
    log_dir.mkdir(parents=True)

    _write_command_logs(tmp_path, "job-1", "prefix\x00" + "x" * 2048, "ok")

    stdout = log_dir / "render_deval_job-1.stdout"
    assert stdout.stat().st_size <= 1024
    assert stdout.read_text(encoding="utf-8").startswith("[WEPPcloudR log truncated")
    assert "\x00" not in stdout.read_text(encoding="utf-8")
    assert stdout.stat().st_mode & 0o777 == 0o660


def test_command_log_byte_cap_is_exact_for_unicode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WEPPCLOUDR_LOG_MAX_BYTES", "1024")
    log_dir = tmp_path / "_logs" / "weppcloudr"
    log_dir.mkdir(parents=True)

    _write_command_logs(tmp_path, "job-1", "🙂" * 1024, "€" * 1024)

    for suffix in ("stdout", "stderr"):
        assert (log_dir / f"render_deval_job-1.{suffix}").stat().st_size <= 1024


def test_compose_shared_paths_override_restrictive_worker_umask(tmp_path: Path) -> None:
    previous_umask = os.umask(0o027)
    try:
        weppcloudr_rq._secure_deval_paths(tmp_path, "run-1", "job-1")
        generation = weppcloudr_rq._next_compose_fencing_generation(tmp_path, "run-1")
    finally:
        os.umask(previous_umask)

    assert generation == 1
    for directory in (
        tmp_path / "export",
        tmp_path / "export" / "WEPPcloudR",
        tmp_path / "_locks",
        tmp_path / "_locks" / "weppcloudr",
    ):
        assert directory.stat().st_mode & 0o777 == 0o770
    fence_dir = tmp_path / "_locks" / "weppcloudr"
    assert (fence_dir / "deval_run-1.fence").stat().st_mode & 0o777 == 0o660
    assert (fence_dir / "deval_run-1.fence.publish.lock").stat().st_mode & 0o777 == 0o660


def test_run_path_validation_preserves_pup_links_to_parent(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    active_root = run_root / "_pups" / "shared"
    resource = run_root / "watershed"
    resource.mkdir(parents=True)
    active_root.mkdir(parents=True)
    (active_root / "watershed").symlink_to(resource, target_is_directory=True)

    actual_run_root, actual_active_root = _validate_run_paths(
        str(run_root), str(active_root)
    )

    assert actual_run_root == run_root
    assert actual_active_root == active_root
    assert (actual_active_root / "watershed").resolve() == resource


def test_unknown_backend_fails_without_docker_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        weppcloudr_rq,
        "get_current_job",
        lambda: SimpleNamespace(id="job-unknown"),
    )
    monkeypatch.setattr(weppcloudr_rq.StatusMessenger, "publish", lambda *_args: None)
    monkeypatch.setattr(
        weppcloudr_rq,
        "list_existing_retired_root_resources",
        lambda _path: [],
    )
    monkeypatch.setattr(
        weppcloudr_rq.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("Docker fallback is forbidden"),
    )

    with pytest.raises(WeppcloudRError, match="Unknown WEPPcloudR execution backend"):
        render_deval_details_rq(
            "run-1", "cfg", str(tmp_path), run_root=str(tmp_path), backend="unknown"
        )


def test_render_deval_details_rq_runs_container_and_publishes_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[tuple[str, str]] = []
    commands: list[tuple[list[str], dict[str, object]]] = []
    output_path = tmp_path / "export" / "WEPPcloudR" / "deval_run-1.htm"

    monkeypatch.setattr(weppcloudr_rq.shutil, "which", lambda _name: "/usr/bin/docker")
    monkeypatch.setattr(
        weppcloudr_rq,
        "get_current_job",
        lambda: SimpleNamespace(id="job-1"),
    )
    monkeypatch.setattr(
        weppcloudr_rq.StatusMessenger,
        "publish",
        lambda channel, message: messages.append((channel, message)),
    )
    monkeypatch.setattr(
        weppcloudr_rq,
        "list_existing_retired_root_resources",
        lambda _path: [],
    )

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        commands.append((command, kwargs))
        output_path.write_text("<h1>DEVAL</h1>", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="rendered", stderr="")

    monkeypatch.setattr(weppcloudr_rq.subprocess, "run", fake_run)

    result = render_deval_details_rq(
        "run-1",
        "cfg",
        str(tmp_path),
        skip_cache=True,
        container_name="renderer",
        timeout=42,
    )

    assert result == str(output_path)
    command, kwargs = commands[0]
    assert command == [
        "docker",
        "exec",
        "-i",
        "renderer",
        "Rscript",
        "/srv/weppcloudr/render-compose-request.R",
    ]
    payload = kwargs.pop("input")
    assert '"run_path": "' + str(tmp_path) + '"' in payload
    assert '"runid": "run-1"' in payload
    assert '"config": "cfg"' in payload
    assert '"skip_cache": true' in payload
    assert kwargs == {
        "check": False,
        "capture_output": True,
        "text": True,
        "timeout": 42,
    }
    assert (tmp_path / "_logs" / "weppcloudr" / "render_deval_job-1.stdout").read_text(
        encoding="utf-8"
    ) == "rendered"
    assert messages[0][0] == "run-1:weppcloudr"
    assert "STARTED" in messages[0][1]
    assert "COMPLETED" in messages[-1][1]


def test_render_deval_details_rq_records_failure_and_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(weppcloudr_rq.shutil, "which", lambda _name: "/usr/bin/docker")
    monkeypatch.setattr(
        weppcloudr_rq,
        "get_current_job",
        lambda: SimpleNamespace(id="job-2"),
    )
    monkeypatch.setattr(
        weppcloudr_rq.StatusMessenger,
        "publish",
        lambda _channel, message: messages.append(message),
    )
    monkeypatch.setattr(
        weppcloudr_rq,
        "list_existing_retired_root_resources",
        lambda _path: [],
    )
    monkeypatch.setattr(
        weppcloudr_rq.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[],
            returncode=7,
            stdout="partial",
            stderr="R failed",
        ),
    )

    with pytest.raises(WeppcloudRError, match="exit 7"):
        render_deval_details_rq("run-1", "cfg", str(tmp_path))

    assert "STARTED" in messages[0]
    assert "EXCEPTION" in messages[-1]


@pytest.mark.parametrize(
    "symlink_name",
    [
        "export",
        "WEPPcloudR",
        "deval_run-1.htm",
        "render_deval_job-3.stdout",
        "render_deval_job-3.stderr",
    ],
)
def test_render_deval_details_rq_rejects_symlink_escape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    symlink_name: str,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    export_parent = tmp_path / "export"
    if symlink_name == "export":
        export_parent.symlink_to(outside, target_is_directory=True)
    else:
        export_parent.mkdir()
    if symlink_name == "WEPPcloudR":
        (export_parent / symlink_name).symlink_to(outside, target_is_directory=True)
    elif symlink_name.startswith("render_deval_"):
        export_dir = export_parent / "WEPPcloudR"
        export_dir.mkdir()
        log_dir = tmp_path / "_logs" / "weppcloudr"
        log_dir.mkdir(parents=True)
        (log_dir / symlink_name).symlink_to(outside / "target")
    elif symlink_name != "export":
        export_dir = export_parent / "WEPPcloudR"
        export_dir.mkdir()
        (export_dir / symlink_name).symlink_to(outside / "target")

    monkeypatch.setattr(weppcloudr_rq.shutil, "which", lambda _name: "/usr/bin/docker")
    monkeypatch.setattr(
        weppcloudr_rq,
        "get_current_job",
        lambda: SimpleNamespace(id="job-3"),
    )
    monkeypatch.setattr(weppcloudr_rq.StatusMessenger, "publish", lambda *_args: None)
    monkeypatch.setattr(
        weppcloudr_rq,
        "list_existing_retired_root_resources",
        lambda _path: [],
    )
    monkeypatch.setattr(
        weppcloudr_rq.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("Docker must not run"),
    )

    with pytest.raises(WeppcloudRError, match="symlink"):
        render_deval_details_rq("run-1", "cfg", str(tmp_path))
