"""HTTP lifecycle tests; the atomic admission boundary has separate real-Redis tests."""
from __future__ import annotations

import json
import traceback
from datetime import date
from pathlib import Path

import pytest
import requests

from wepppy.climates.gridmet import acquisition
from wepppy.climates.gridmet import admission as admission_module
from wepppy.climates.gridmet import client as grid_client
from wepppy.climates.gridmet import gridmet_singlelocation_client as point_client

pytestmark = pytest.mark.unit
_PAYLOAD = {"data": [{"yyyy-mm-dd": ["2025-01-01"], "pr(mm)": [1.0]}]}


class _Lifecycle:
    def __init__(self):
        self.events = []
        self.deadlines = []
        self.active = False
        self.lost = False

    def acquire(self, *, request_kind, deadline):
        assert not self.active
        self.events.append(("acquire", request_kind))
        self.deadlines.append(deadline)
        return self

    def __enter__(self):
        self.active = True
        return self

    def check(self):
        assert self.active
        self.events.append("check")
        if self.lost:
            raise admission_module.GridMetAdmissionLostLease("test lease lost")

    def __exit__(self, exc_type, exc_value, tb):
        assert self.active
        self.active = False
        self.events.append("release")

    def sleep(self, seconds):
        assert not self.active
        self.events.append(("sleep", seconds))


class _Response:
    def __init__(self, lifecycle, *, status=200, body=None, failure=None):
        self.lifecycle = lifecycle
        self.status_code = status
        self.headers = {}
        self.body = json.dumps(_PAYLOAD).encode() if body is None else body
        self.failure = failure
        self.closed = False

    def iter_content(self, *, chunk_size):
        assert self.lifecycle.active
        self.lifecycle.events.append("stream")
        if self.failure == "lease":
            self.lifecycle.lost = True
        elif self.failure == "timeout":
            raise requests.exceptions.Timeout("stream timed out")
        yield self.body

    def close(self):
        assert self.lifecycle.active
        self.lifecycle.events.append("close")
        self.closed = True


@pytest.fixture
def lifecycle(monkeypatch):
    state = _Lifecycle()
    monkeypatch.setattr(admission_module, "GridMetAdmissionController", lambda _config: state)
    monkeypatch.setattr(acquisition.time, "sleep", state.sleep)
    return state


@pytest.fixture
def config():
    return admission_module.GridMetAdmissionConfig()


def _invoke(kind, config, monkeypatch, tmp_path, get):
    if kind == "point":
        return acquisition.request_single_location_json(
            "https://example.invalid/gridmet",
            required_series=("pr(mm)",),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 1),
            get=get,
            admission=config,
        )
    monkeypatch.setattr(grid_client.requests, "get", get)
    return grid_client.retrieve_nc(
        grid_client.GridMetVariable.Precipitation,
        [-117.0, 47.0, -116.0, 46.0],
        2025,
        str(tmp_path),
        _id="admitted",
        admission=config,
    )


def _track_validation(kind, lifecycle, monkeypatch):
    if kind == "point":
        original = acquisition.validate_single_location_payload

        def validate(*args, **kwargs):
            assert not lifecycle.active
            lifecycle.events.append("validate")
            return original(*args, **kwargs)

        monkeypatch.setattr(acquisition, "validate_single_location_payload", validate)
    else:
        # NetCDF semantics are covered by test_download_clients; isolate lifetime.
        def validate(path, *_args, **_kwargs):
            assert not lifecycle.active
            lifecycle.events.append("validate")
            if Path(path).read_bytes() == b"invalid":
                raise acquisition.GridMetPayloadError("invalid test payload")

        monkeypatch.setattr(grid_client, "_validate_gridmet_netcdf", validate)


@pytest.mark.parametrize("kind", ["point", "grid"])
def test_enabled_attempt_closes_and_releases_before_validation(
    kind, lifecycle, config, monkeypatch, tmp_path
):
    _track_validation(kind, lifecycle, monkeypatch)
    response = _Response(lifecycle)

    def get(*_args, **_kwargs):
        assert lifecycle.active
        lifecycle.events.append("get")
        return response

    _invoke(kind, config, monkeypatch, tmp_path, get)

    assert response.closed
    assert lifecycle.events.index("close") < lifecycle.events.index("release")
    assert lifecycle.events.index("release") < lifecycle.events.index("validate")
    assert lifecycle.events[lifecycle.events.index("get") - 1] == "check"
    assert lifecycle.events[lifecycle.events.index("get") + 1] == "check"
    assert lifecycle.events[lifecycle.events.index("stream") - 1] == "check"
    assert lifecycle.events[lifecycle.events.index("stream") + 1] == "check"
    assert lifecycle.events[lifecycle.events.index("close") + 1] == "check"


@pytest.mark.parametrize("kind", ["point", "grid"])
def test_retries_requeue_and_share_deadline_after_released_backoff(
    kind, lifecycle, config, monkeypatch, tmp_path
):
    _track_validation(kind, lifecycle, monkeypatch)
    bad_body = json.dumps({"data": []}).encode() if kind == "point" else b"invalid"
    responses = [
        _Response(lifecycle, status=503),
        _Response(lifecycle, body=bad_body),
        _Response(lifecycle),
    ]
    pending = iter(responses)
    _invoke(kind, config, monkeypatch, tmp_path, lambda *_a, **_k: next(pending))

    assert len(lifecycle.deadlines) == 3
    assert len(set(lifecycle.deadlines)) == 1
    assert lifecycle.events.count("release") == 3
    assert [event for event in lifecycle.events if isinstance(event, tuple)] == [
        ("acquire", kind), ("sleep", 5.0), ("acquire", kind),
        ("sleep", 10.0), ("acquire", kind),
    ]
    assert all(response.closed for response in responses)


@pytest.mark.parametrize("kind", ["point", "grid"])
@pytest.mark.parametrize("failure_at", ["get", "stream"])
def test_lease_loss_closes_response_and_stops_without_validation_or_retry(
    kind, failure_at, lifecycle, config, monkeypatch, tmp_path
):
    _track_validation(kind, lifecycle, monkeypatch)
    response = _Response(lifecycle, failure="lease" if failure_at == "stream" else None)

    def get(*_args, **_kwargs):
        if failure_at == "get":
            lifecycle.lost = True
        return response

    with pytest.raises(admission_module.GridMetAdmissionLostLease):
        _invoke(kind, config, monkeypatch, tmp_path, get)

    assert response.closed
    assert not lifecycle.active
    assert lifecycle.events.count("release") == 1
    assert "validate" not in lifecycle.events
    assert not (tmp_path / "admitted.nc").exists()
    assert list(tmp_path.glob("*.part")) == []


@pytest.mark.parametrize("kind", ["point", "grid"])
def test_stream_exception_releases_before_backoff(
    kind, lifecycle, config, monkeypatch, tmp_path
):
    response = _Response(lifecycle, failure="timeout")
    with pytest.raises(acquisition.GridMetAcquisitionError, match="after 3 attempts"):
        _invoke(kind, config, monkeypatch, tmp_path, lambda *_a, **_k: response)
    assert response.closed
    assert lifecycle.events.count("release") == 3
    assert not lifecycle.active
    assert list(tmp_path.glob("*.part")) == []


@pytest.mark.parametrize("kind", ["point", "grid"])
def test_disabled_does_not_construct_admission_even_with_enabled_environment(
    kind, monkeypatch, tmp_path
):
    monkeypatch.setenv("GRIDMET_REDIS_ADMISSION_ENABLED", "true")
    monkeypatch.setattr(
        admission_module, "GridMetAdmissionController",
        lambda *_args: pytest.fail("disabled client constructed admission"),
    )
    monkeypatch.setattr(
        admission_module.GridMetAdmissionConfig, "from_env",
        lambda: pytest.fail("direct client reinterpreted None"),
    )
    lifecycle = _Lifecycle()
    # A response independent of admission; this flag only permits test stream IO.
    lifecycle.active = True
    response = _Response(lifecycle)
    monkeypatch.setattr(grid_client, "_validate_gridmet_netcdf", lambda *_a, **_k: None)
    _invoke(kind, None, monkeypatch, tmp_path, lambda *_a, **_k: response)
    assert response.closed


@pytest.mark.parametrize("kind", ["point", "grid"])
def test_request_exception_query_is_absent_from_logs_and_formatted_traceback(
    kind, lifecycle, config, monkeypatch, tmp_path, caplog
):
    private_url = "https://example.invalid/gridmet?private-location=1234"

    def get(*_args, **_kwargs):
        raise requests.exceptions.Timeout(private_url)

    with pytest.raises(acquisition.GridMetAcquisitionError) as caught:
        _invoke(kind, config, monkeypatch, tmp_path, get)
    assert private_url not in caplog.text
    assert private_url not in "".join(traceback.format_exception(caught.value))
    assert lifecycle.events.count("release") == 3


@pytest.mark.parametrize("kind", ["point", "grid"])
def test_invalid_lease_rejected_before_http(kind, monkeypatch, tmp_path):
    config = admission_module.GridMetAdmissionConfig(lease_seconds=30)
    with pytest.raises(admission_module.GridMetAdmissionConfigError):
        _invoke(
            kind, config, monkeypatch, tmp_path,
            lambda *_a, **_k: pytest.fail("invalid config reached HTTP"),
        )


@pytest.mark.parametrize("kind", ["point", "grid"])
def test_admission_outage_is_not_retried(kind, config, monkeypatch, tmp_path):
    class Controller:
        def acquire(self, **_kwargs):
            raise admission_module.GridMetAdmissionUnavailable("test outage")

    monkeypatch.setattr(admission_module, "GridMetAdmissionController", lambda _config: Controller())
    monkeypatch.setattr(acquisition.time, "sleep", lambda *_args: pytest.fail("admission retried"))
    with pytest.raises(admission_module.GridMetAdmissionUnavailable):
        _invoke(
            kind, config, monkeypatch, tmp_path,
            lambda *_a, **_k: pytest.fail("outage reached HTTP"),
        )


@pytest.mark.parametrize("name", ["precip", "wind", "timeseries"])
def test_public_point_functions_forward_configuration(name, config, monkeypatch):
    class Forwarded(Exception):
        pass

    def request(_url, *, admission, **_kwargs):
        assert admission is config
        raise Forwarded

    monkeypatch.setattr(point_client, "request_single_location_json", request)
    with pytest.raises(Forwarded):
        getattr(point_client, f"retrieve_historical_{name}")(-116, 46, 2025, 2025, admission=config)


def test_grid_timeseries_forwards_configuration(config, monkeypatch, tmp_path):
    class Forwarded(Exception):
        pass

    def retrieve(*_args, admission, **_kwargs):
        assert admission is config
        raise Forwarded

    monkeypatch.setattr(grid_client, "retrieve_nc", retrieve)
    with pytest.raises(Forwarded):
        grid_client.retrieve_timeseries(
            [grid_client.GridMetVariable.Precipitation], {"point": (-116, 46)},
            2025, 2025, str(tmp_path), admission=config,
        )


@pytest.mark.parametrize("kind", ["point", "grid"])
def test_backoff_exhausts_original_deadline_without_another_http_attempt(
    kind, lifecycle, monkeypatch, tmp_path
):
    now = [100.0]
    deadlines = []
    config = admission_module.GridMetAdmissionConfig(wait_timeout_seconds=1)
    original_acquire = lifecycle.acquire

    def acquire(*, request_kind, deadline):
        deadlines.append(deadline)
        if now[0] >= deadline:
            raise admission_module.GridMetAdmissionTimeout("test deadline exhausted")
        return original_acquire(request_kind=request_kind, deadline=deadline)

    def sleep(seconds):
        assert not lifecycle.active
        now[0] += seconds

    monkeypatch.setattr(acquisition.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(acquisition.time, "sleep", sleep)
    monkeypatch.setattr(lifecycle, "acquire", acquire)
    response = _Response(lifecycle, status=503)
    requests_made = []

    def get(*_args, **_kwargs):
        requests_made.append(1)
        return response

    with pytest.raises(admission_module.GridMetAdmissionTimeout):
        _invoke(kind, config, monkeypatch, tmp_path, get)
    assert deadlines == [101.0, 101.0]
    assert requests_made == [1]
    assert response.closed
    assert not lifecycle.active


@pytest.mark.parametrize("kind", ["point", "grid"])
def test_lease_loss_on_response_close_prevents_validation(
    kind, lifecycle, config, monkeypatch, tmp_path
):
    _track_validation(kind, lifecycle, monkeypatch)
    response = _Response(lifecycle)
    original_close = response.close

    def close():
        original_close()
        lifecycle.lost = True

    monkeypatch.setattr(response, "close", close)
    with pytest.raises(admission_module.GridMetAdmissionLostLease):
        _invoke(kind, config, monkeypatch, tmp_path, lambda *_a, **_k: response)
    assert response.closed
    assert not lifecycle.active
    assert "validate" not in lifecycle.events
    assert not (tmp_path / "admitted.nc").exists()


@pytest.mark.parametrize("kind", ["point", "grid"])
def test_keyboard_interrupt_closes_response_and_releases(
    kind, lifecycle, config, monkeypatch, tmp_path
):
    response = _Response(lifecycle)

    def chunks(**_kwargs):
        raise KeyboardInterrupt
        yield b""  # Make interruption occur on the blocking iterator step.

    monkeypatch.setattr(response, "iter_content", chunks)
    with pytest.raises(KeyboardInterrupt):
        _invoke(kind, config, monkeypatch, tmp_path, lambda *_a, **_k: response)
    assert response.closed
    assert lifecycle.events.count("release") == 1
    assert not lifecycle.active
    assert list(tmp_path.glob("*.part")) == []
