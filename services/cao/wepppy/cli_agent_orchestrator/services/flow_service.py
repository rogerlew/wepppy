"""Minimal flow_service shim for tests under services/cao.

Implements only the helpers used by unit tests to avoid importing
external dependencies and the full CAO database layer.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

from wepppy.cli_agent_orchestrator.models.flow import Flow


def _get_next_run_time(cron_expression: str) -> datetime:
    """Placeholder next-run calculator.

    The test suite monkeypatches this function to return a fixed
    datetime. This default keeps behavior deterministic without
    pulling in APScheduler.
    """

    # Default to "now"; tests override via monkeypatch.
    return datetime.now()


def _parse_flow_file(file_path: Path) -> Tuple[Dict[str, str], str]:
    """Parse a very small subset of front-matter.

    Supports files that begin with a YAML-like block bounded by
    lines containing only '---'. Each metadata line must be
    in the form `key: value`. Surrounding quotes are stripped.

    Returns a (metadata, content) tuple.
    """

    if not file_path.exists():
        raise ValueError(f"Flow file not found: {file_path}")

    text = file_path.read_text()

    # Detect front-matter section
    lines = text.splitlines()
    meta: Dict[str, str] = {}
    content_start = 0
    if lines and lines[0].strip() == "---":
        # Parse until the next '---'
        i = 1
        while i < len(lines):
            line = lines[i].strip()
            if line == "---":
                content_start = i + 1
                break
            if line and not line.startswith("#"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip().strip('"').strip("'")
                    meta[key.strip()] = val
            i += 1
    content = "\n".join(lines[content_start:])
    return meta, content


def add_flow(file_path: str) -> Flow:
    """Add a flow using metadata from `file_path`.

    Expects tests to monkeypatch `db_create_flow` and `_get_next_run_time`.
    """

    path = Path(file_path).resolve()
    metadata, _ = _parse_flow_file(path)

    # Validate required fields
    for field in ("name", "schedule", "agent_profile"):
        if field not in metadata:
            raise ValueError(f"Missing required field: {field}")

    name = metadata["name"]
    schedule = metadata["schedule"]
    agent_profile = metadata["agent_profile"]
    script = metadata.get("script", "")

    # Calculate next run (tests patch the implementation)
    next_run = _get_next_run_time(schedule)

    # Delegate persistence to a function the tests will patch in
    try:
        flow = globals()["db_create_flow"](
            name=name,
            file_path=str(path),
            schedule=schedule,
            agent_profile=agent_profile,
            script=script,
            next_run=next_run,
        )
    except Exception as exc:  # Broad by design to avoid extra deps
        # Normalize duplicate-name errors to the message the tests expect
        raise ValueError(f"Flow '{name}' already exists") from exc

    return flow

