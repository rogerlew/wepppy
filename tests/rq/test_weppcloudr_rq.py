from __future__ import annotations

import inspect
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.rq.weppcloudr_rq as weppcloudr_rq
from wepppy.rq.weppcloudr_rq import (
    WeppcloudRError,
    _assert_no_retired_root_resources,
    _build_render_deval_expression,
    render_deval_details_rq,
)

pytestmark = pytest.mark.unit


def test_render_deval_details_rq_accepts_legacy_parquet_overrides_kwarg() -> None:
    signature = inspect.signature(render_deval_details_rq)
    assert "parquet_overrides" in signature.parameters


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


def test_build_render_deval_expression_uses_stable_render_signature() -> None:
    expression = _build_render_deval_expression("{}")

    assert "render_deval(payload$run_path, payload$runid, payload$config," in expression
    assert "skip_cache = payload$skip_cache" in expression
    assert "parquet_overrides" not in expression
    assert "do.call(" not in expression


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
    assert command[:4] == ["docker", "exec", "renderer", "Rscript"]
    assert '"run_path": "' + str(tmp_path) + '"' in command[-1]
    assert '"runid": "run-1"' in command[-1]
    assert '"config": "cfg"' in command[-1]
    assert '"skip_cache": true' in command[-1]
    assert kwargs == {
        "check": False,
        "capture_output": True,
        "text": True,
        "timeout": 42,
    }
    assert (output_path.parent / "render_deval_job-1.stdout").read_text(
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

    with pytest.raises(WeppcloudRError, match="R failed"):
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
