from pathlib import Path
from types import SimpleNamespace

from wepppy.rq import ermit_export_rq


def test_run_ermit_export_rq_returns_run_relative_artifact_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    artifact_path = tmp_path / "export" / "ERMiT_input_demo.zip"
    artifact_path.parent.mkdir()
    artifact_path.write_bytes(b"ermit")
    messages: list[tuple[str, str]] = []

    monkeypatch.setattr(
        ermit_export_rq,
        "get_current_job",
        lambda: SimpleNamespace(id="ermit-job-1"),
    )
    monkeypatch.setattr(
        ermit_export_rq,
        "create_ermit_input",
        lambda wd: str(artifact_path),
    )
    monkeypatch.setattr(
        ermit_export_rq.StatusMessenger,
        "publish",
        lambda channel, message: messages.append((channel, message)),
    )

    result = ermit_export_rq.run_ermit_export_rq(
        "demo-run",
        "demo-config",
        str(tmp_path),
    )

    assert result == {
        "artifact_relpath": "export/ERMiT_input_demo.zip",
        "filename": "ERMiT_input_demo.zip",
        "config": "demo-config",
    }
    assert messages[0] == (
        "demo-run:ermit_export",
        "rq:ermit-job-1 STARTED run_ermit_export_rq(demo-run)",
    )
    assert messages[-1] == (
        "demo-run:ermit_export",
        "rq:ermit-job-1 TRIGGER ermit_export ERMIT_EXPORT_TASK_COMPLETED",
    )
