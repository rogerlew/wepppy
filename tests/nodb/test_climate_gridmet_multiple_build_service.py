from __future__ import annotations

from concurrent.futures import Future
from types import SimpleNamespace

import pytest

import wepppy.nodb.core.climate_gridmet_multiple_build_service as service_module
from wepppy.nodb.core.climate_gridmet_multiple_build_service import (
    ClimateGridmetMultipleBuildService,
)

pytestmark = pytest.mark.unit


class _RecordingLogger:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class _RecordingExecutor:
    def __init__(self) -> None:
        self.shutdown_calls: list[tuple[bool, bool]] = []

    def shutdown(self, *, wait: bool, cancel_futures: bool) -> None:
        self.shutdown_calls.append((wait, cancel_futures))


def test_wait_for_futures_logs_warning_until_work_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClimateGridmetMultipleBuildService()
    logger = _RecordingLogger()
    climate = SimpleNamespace(logger=logger)

    completed = Future()
    completed.set_result("ws")

    rounds = {"count": 0}

    def _fake_wait(_pending, timeout, return_when):
        rounds["count"] += 1
        assert timeout == 60
        assert return_when is service_module.FIRST_COMPLETED
        if rounds["count"] == 1:
            return set(), {completed}
        return {completed}, set()

    monkeypatch.setattr(service_module, "wait", _fake_wait)

    seen: list[str] = []
    service._wait_for_futures(
        futures=[completed],
        climate=climate,
        timeout=60,
        waiting_message="still waiting",
        on_done=seen.append,
    )

    assert logger.warnings == ["still waiting"]
    assert seen == ["ws"]


def test_wait_for_futures_cancels_pending_and_stops_executor_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateGridmetMultipleBuildService()
    logger = _RecordingLogger()
    climate = SimpleNamespace(logger=logger)
    executor = _RecordingExecutor()

    failed = Future()
    failed.set_exception(RuntimeError("boom"))
    pending = Future()

    monkeypatch.setattr(
        service_module,
        "wait",
        lambda _pending, timeout, return_when: ({failed}, {pending}),
    )

    with pytest.raises(RuntimeError, match="boom"):
        service._wait_for_futures(
            futures=[failed, pending],
            climate=climate,
            timeout=60,
            waiting_message="still waiting",
            executor=executor,
        )

    assert pending.cancelled()
    assert executor.shutdown_calls == [(False, True)]


def test_worker_count_honors_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClimateGridmetMultipleBuildService()

    monkeypatch.delenv("WEPPPY_NCPU", raising=False)
    assert service._worker_count(default_workers=12, ncpu=8) == 12

    monkeypatch.setenv("WEPPPY_NCPU", "1")
    assert service._worker_count(default_workers=12, ncpu=8) == 8


def test_build_rejects_invalid_observed_year_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClimateGridmetMultipleBuildService()

    monkeypatch.setattr(
        service,
        "_load_gridmet_client_functions",
        lambda: (object(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(service, "_build_measures", lambda _enum: [])
    monkeypatch.setattr(service, "_build_interpolation_spec", lambda: {})

    climate = SimpleNamespace(
        logger=_RecordingLogger(),
        watershed_instance=SimpleNamespace(centroid=(-116.0, 43.0)),
        cli_dir="/tmp",
        _require_observed_year_bounds_for_build=lambda: (_ for _ in ()).throw(
            ValueError("observed_end_year must be an integer year")
        ),
    )

    with pytest.raises(ValueError, match="observed_end_year must be an integer year"):
        service.build(
            climate,
            build_observed_gridmet_interpolated_fn=lambda *_args, **_kwargs: "unused",
            ncpu=1,
        )
