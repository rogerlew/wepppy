from __future__ import annotations

import errno
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from wepppy.nodb import _read_retry as retry

pytestmark = pytest.mark.unit


@pytest.fixture
def fake_clock(monkeypatch):
    class Clock:
        now = 0.0
        sleeps = []

        def monotonic(self):
            return self.now

        def sleep(self, delay):
            self.sleeps.append(delay)
            self.now += delay

    clock = Clock()
    # Patch the module's clock, not process-wide time used by other libraries.
    monkeypatch.setattr(retry, "time", clock)
    return clock


@pytest.mark.parametrize("error_number", [errno.ENOENT, errno.ESTALE])
@pytest.mark.parametrize("operation", ["read", "stat"])
def test_transient_read_recovers_with_original_errno_diagnostics(tmp_path, monkeypatch, fake_clock, caplog, error_number, operation):
    path = str(tmp_path / "state.nodb")
    Path(path).write_text('payload')
    calls = []
    real_action = retry.os.stat if operation == "stat" else open

    def action(*args, **kwargs):
        calls.append(args[0])
        if len(calls) < 3:
            raise OSError(error_number, "injected transient", path)
        return real_action(*args, **kwargs)

    if operation == "stat":
        monkeypatch.setattr(retry, "os", type("OS", (), {"stat": staticmethod(action)}))
    else:
        monkeypatch.setattr(retry, "open", action, raising=False)
    caplog.set_level(logging.INFO, logger=retry.__name__)
    with retry.initial_read_retry(runid="run-1", job_id="job-1"):
        result = retry.stat_path(path) if operation == "stat" else retry.read_text(path)
    assert result is not None
    assert fake_clock.sleeps == [2.0, 4.0]
    assert "recovered" in caplog.text
    assert f"errno={error_number}" in caplog.text
    assert "runid=run-1 job_id=job-1" in caplog.text


@pytest.mark.parametrize("error_number", [errno.ENOENT, errno.ESTALE, errno.EACCES, errno.EPERM, errno.EIO, errno.ENOTDIR, errno.ELOOP])
def test_permanent_error_preserves_original_exception(monkeypatch, fake_clock, error_number):
    original = OSError(error_number, "failure", "/missing/controller.nodb")
    calls = []

    def fail(*args):
        calls.append(args)
        raise original

    monkeypatch.setattr(retry, "open", fail, raising=False)
    with retry.initial_read_retry(runid="run", job_id="job"):
        with pytest.raises(OSError) as caught:
            retry.read_text(original.filename)
    assert caught.value is original
    assert fake_clock.now < 120.0
    if error_number in (errno.ENOENT, errno.ESTALE):
        assert len(calls) == 14
        assert fake_clock.now == 114.0
        assert min(fake_clock.sleeps) >= 2.0
        assert max(fake_clock.sleeps) <= 10.0
    else:
        assert len(calls) == 1
        assert not fake_clock.sleeps


def test_outside_context_does_not_retry(tmp_path, fake_clock):
    with pytest.raises(FileNotFoundError) as caught:
        retry.read_text(str(tmp_path / "missing"))
    assert caught.value.errno == errno.ENOENT
    assert not fake_clock.sleeps


def test_optional_missing_is_immediate_and_estale_is_not_absence(tmp_path, monkeypatch, fake_clock):
    path = str(tmp_path / "optional.nodb")
    with retry.initial_read_retry(runid="run", job_id="job"):
        assert retry.read_text(path, allow_missing=True) is None
        assert retry.stat_path(path, allow_missing=True) is None
    assert not fake_clock.sleeps

    def stale(*args):
        raise OSError(errno.ESTALE, "stale", path)

    monkeypatch.setattr(retry, "open", stale, raising=False)
    with retry.initial_read_retry(runid="run", job_id="job"):
        with pytest.raises(OSError) as caught:
            retry.read_text(path, allow_missing=True)
    assert caught.value.errno == errno.ESTALE
    assert fake_clock.sleeps


def test_budget_is_shared_and_nested_context_does_not_extend_it(monkeypatch, fake_clock):
    calls = []

    def stale(*args):
        calls.append(fake_clock.now)
        raise OSError(errno.ESTALE, "stale", "controller.nodb")

    monkeypatch.setattr(retry, "open", stale, raising=False)
    with retry.initial_read_retry(runid="run", job_id="job"):
        with pytest.raises(OSError):
            retry.read_text("one.nodb")
        with retry.initial_read_retry(runid="run", job_id="job"):
            with pytest.raises(OSError):
                retry.read_text("two.nodb")
    assert fake_clock.now < 120.0
    assert all(t < 120.0 for t in calls)
    assert not retry.read_retry_active()


def test_context_isolated_across_threads_and_reset_on_error():
    barrier = threading.Barrier(2)

    def scoped():
        with pytest.raises(RuntimeError):
            with retry.initial_read_retry(runid="run", job_id="job"):
                barrier.wait(timeout=5)
                assert retry.read_retry_active()
                barrier.wait(timeout=5)
                raise RuntimeError("end")
        assert not retry.read_retry_active()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(scoped)
        barrier.wait(timeout=5)
        assert not retry.read_retry_active()
        barrier.wait(timeout=5)
        future.result()


@pytest.mark.integration
def test_actual_missing_file_then_atomic_publication(tmp_path, monkeypatch, caplog):
    """Real OS ENOENT recovery; not a reproduction of production NFS ESTALE."""
    path = tmp_path / "state.nodb"
    missing_observed = threading.Event()
    real_open = open

    def observe_open(*args, **kwargs):
        try:
            return real_open(*args, **kwargs)
        except FileNotFoundError:
            missing_observed.set()
            raise

    monkeypatch.setattr(retry, "open", observe_open, raising=False)
    caplog.set_level(logging.INFO, logger=retry.__name__)

    def publish():
        assert missing_observed.wait(timeout=5)
        temporary = path.with_suffix('.tmp')
        temporary.write_text('complete payload')
        temporary.replace(path)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(publish)
        with retry.initial_read_retry(runid="real-read", job_id="real-read-job"):
            assert retry.read_text(str(path)) == 'complete payload'
        future.result()

    assert "recovered" in caplog.text


@pytest.mark.parametrize("error_number", [errno.ENOENT, errno.ESTALE])
def test_read_recovers_after_minute_of_storage_visibility_delay(
    tmp_path, monkeypatch, fake_clock, error_number,
):
    path = tmp_path / "state.nodb"
    path.write_text("ready")
    attempts = []

    def delayed_open(*args, **kwargs):
        attempts.append(fake_clock.now)
        if fake_clock.now < 60.0:
            raise OSError(error_number, "visibility delayed", str(path))
        return open(*args, **kwargs)

    monkeypatch.setattr(retry, "open", delayed_open, raising=False)
    with retry.initial_read_retry(runid="run", job_id="job"):
        assert retry.read_text(str(path)) == "ready"
    assert attempts == [0.0, 2.0, 6.0, 14.0, 24.0, 34.0, 44.0, 54.0, 64.0]
