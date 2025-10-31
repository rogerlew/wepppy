from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

from wepppy.cli_agent_orchestrator.models.flow import Flow




def db_create_flow(*_args, **_kwargs):  # noqa: D401
    """Placeholder that should be monkeypatched by tests."""

    raise RuntimeError("db_create_flow must be provided by tests")


def _get_next_run_time(cron_expression: str) -> datetime:  # noqa: D401, ARG001
    """Return the next execution time; tests monkeypatch this helper."""

    return datetime.now()


def _parse_flow_file(file_path: Path) -> Tuple[Dict[str, str], str]:
    """Parse a tiny subset of YAML front-matter used in flow tests."""

    if not file_path.exists():
        raise ValueError(f"Flow file not found: {file_path}")

    text = file_path.read_text()
    lines = text.splitlines()
    meta: Dict[str, str] = {}
    content_start = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines):
            line = lines[i].strip()
            if line == "---":
                content_start = i + 1
                break
            if line and not line.startswith("#") and ":" in line:
                key, raw_val = line.split(":", 1)
                val = raw_val.strip().strip('"').strip("'")
                meta[key.strip()] = val
            i += 1
    content = "\n".join(lines[content_start:])
    return meta, content


def add_flow(file_path: str) -> Flow:
    """Create a Flow record using metadata from `file_path`."""

    path = Path(file_path).resolve()
    metadata, _ = _parse_flow_file(path)

    for field in ("name", "schedule", "agent_profile"):
        if field not in metadata:
            raise ValueError(f"Missing required field: {field}")

    name = metadata["name"]
    schedule = metadata["schedule"]
    agent_profile = metadata["agent_profile"]
    script = metadata.get("script", "")

    next_run = _get_next_run_time(schedule)

    try:
        flow = globals()["db_create_flow"](
            name=name,
            file_path=str(path),
            schedule=schedule,
            agent_profile=agent_profile,
            script=script,
            next_run=next_run,
        )
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Flow '{name}' already exists") from exc

    return flow


__all__ = ["_get_next_run_time", "_parse_flow_file", "add_flow"]
