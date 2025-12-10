from __future__ import annotations

import pytest

from wepppy.weppcloud.routes.batch_runner.batch_runner_bp import (
    _build_batch_runner_snapshot,
)


@pytest.mark.unit
def test_build_batch_runner_snapshot_minimal():
    class Task:
        def __init__(self, value: str) -> None:
            self.value = value

        def label(self) -> str:
            return self.value.title()

    task = Task("task_a")

    class RunnerStub:
        DEFAULT_TASKS = [task]
        batch_name = "demo"
        base_config = "disturbed9002_wbt"
        geojson_state = None
        runid_template_state = None

        def __init__(self) -> None:
            self.run_directives = {task: True}

    snapshot = _build_batch_runner_snapshot(RunnerStub())

    assert snapshot["batch_name"] == "demo"
    assert snapshot["base_config"] == "disturbed9002_wbt"
    assert snapshot["run_directives"] == [
        {"slug": "task_a", "label": "Task_A", "enabled": True}
    ]
    assert snapshot["runid_template"] is None
    assert snapshot["resources"] == {}
