import datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from cli_agent_orchestrator.models.flow import Flow
from cli_agent_orchestrator.services import flow_service


def _write_flow_file(path: Path, body: str) -> Path:
    path.write_text(body)
    return path


def test_add_flow_success(tmp_path, monkeypatch):
    flow_path = _write_flow_file(
        tmp_path / "example_flow.md",
        (
            "---\n"
            "name: example-flow\n"
            'schedule: "0 12 * * *"\n'
            "agent_profile: code_supervisor\n"
            "script: ../scripts/example.sh\n"
            "---\n"
            "# placeholder prompt\n"
        ),
    )

    captured = {}

    def fake_create_flow(name, file_path, schedule, agent_profile, script, next_run):
        captured.update(
            {
                "name": name,
                "file_path": file_path,
                "schedule": schedule,
                "agent_profile": agent_profile,
                "script": script,
                "next_run": next_run,
            }
        )
        return Flow(
            name=name,
            file_path=file_path,
            schedule=schedule,
            agent_profile=agent_profile,
            script=script,
            next_run=next_run,
            enabled=True,
        )

    fixed_next_run = datetime.datetime(2025, 10, 28, 9, 0, 0)

    monkeypatch.setattr(flow_service, "_get_next_run_time", lambda _: fixed_next_run)
    monkeypatch.setattr(flow_service, "db_create_flow", fake_create_flow)

    result = flow_service.add_flow(str(flow_path))

    assert captured["name"] == "example-flow"
    assert captured["file_path"] == str(flow_path.resolve())
    assert captured["schedule"] == "0 12 * * *"
    assert captured["agent_profile"] == "code_supervisor"
    assert captured["script"] == "../scripts/example.sh"
    assert captured["next_run"] == fixed_next_run
    assert isinstance(result, Flow)
    assert result.name == "example-flow"
    assert result.next_run == fixed_next_run


def test_add_flow_duplicate_name(tmp_path, monkeypatch):
    flow_path = _write_flow_file(
        tmp_path / "duplicate_flow.md",
        (
            "---\n"
            "name: duplicate-flow\n"
            'schedule: \"0 1 * * *\"\n'
            "agent_profile: code_supervisor\n"
            "---\n"
        ),
    )

    def fake_create_flow(*_args, **_kwargs):
        raise IntegrityError("insert", {}, Exception("UNIQUE constraint failed"))

    monkeypatch.setattr(flow_service, "db_create_flow", fake_create_flow)
    monkeypatch.setattr(
        flow_service, "_get_next_run_time", lambda *_: datetime.datetime.now()
    )

    with pytest.raises(ValueError, match="Flow 'duplicate-flow' already exists"):
        flow_service.add_flow(str(flow_path))


def test_add_flow_missing_required_field(tmp_path):
    flow_path = _write_flow_file(
        tmp_path / "missing_field.md",
        (
            "---\n"
            "name: missing-field\n"
            'schedule: \"0 2 * * *\"\n'
            # agent_profile intentionally omitted
            "---\n"
        ),
    )

    with pytest.raises(ValueError, match="Missing required field: agent_profile"):
        flow_service.add_flow(str(flow_path))
