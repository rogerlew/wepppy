"""Configuration and cooperative local failure behavior (no Redis required)."""
from dataclasses import FrozenInstanceError, replace
import pickle
import time

import pytest

from wepppy.climates.gridmet import admission as mod

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("enabled", [None, "false", "0", "NO", " off "])
def test_disabled_does_not_parse_or_construct(monkeypatch, enabled):
    monkeypatch.delenv("GRIDMET_REDIS_ADMISSION_ENABLED", raising=False)
    if enabled is not None:
        monkeypatch.setenv("GRIDMET_REDIS_ADMISSION_ENABLED", enabled)
    monkeypatch.setenv("GRIDMET_REDIS_ADMISSION_LIMIT", "invalid")
    monkeypatch.setattr(mod, "redis_connection_kwargs", lambda *a, **kw: pytest.fail("Redis construction"))
    assert mod.GridMetAdmissionConfig.from_env() is None


@pytest.mark.parametrize("enabled", ["", "maybe", "2"])
def test_malformed_enable_fails_explicitly(monkeypatch, enabled):
    monkeypatch.setenv("GRIDMET_REDIS_ADMISSION_ENABLED", enabled)
    with pytest.raises(mod.GridMetAdmissionConfigError):
        mod.GridMetAdmissionConfig.from_env()


def test_enabled_config_is_lazy_frozen_and_pickle_safe(monkeypatch):
    for key in list(mod.os.environ):
        if key.startswith("GRIDMET_REDIS_ADMISSION_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("GRIDMET_REDIS_ADMISSION_ENABLED", " YES ")
    monkeypatch.setattr(mod, "redis_connection_kwargs", lambda *a, **kw: pytest.fail("Redis construction"))
    config = mod.GridMetAdmissionConfig.from_env()
    assert config == mod.GridMetAdmissionConfig()
    assert pickle.loads(pickle.dumps(config)) == config
    assert mod.GridMetAdmissionController(config)._redis is None
    with pytest.raises(FrozenInstanceError):
        config.limit = 10


@pytest.mark.parametrize("values", [
    {"enabled": False}, {"limit": True}, {"limit": 0}, {"limit": 1.5},
    {"key": "x" * 161}, {"key": "{unsafe}"}, {"key": "héllo"}, {"key": " space"},
    {"lease_seconds": float("nan")}, {"lease_seconds": float("inf")},
    {"lease_seconds": True}, {"lease_seconds": 21}, {"queue_ttl_seconds": 6},
    {"wait_timeout_seconds": -1}, {"poll_interval_seconds": 0},
])
def test_invalid_supplied_config_rejected(values):
    with pytest.raises(mod.GridMetAdmissionConfigError):
        mod.GridMetAdmissionConfig(**values)


def test_http_lease_relationship():
    config = mod.GridMetAdmissionConfig(lease_seconds=100)
    config.validate_http_timeout((10, 60))
    with pytest.raises(mod.GridMetAdmissionConfigError):
        config.validate_http_timeout((10, 120))
    assert replace(config, key="x" * 160).key == "x" * 160


class _Controller:
    _retry_transition = mod.GridMetAdmissionController._retry_transition
    config = mod.GridMetAdmissionConfig()

    def __init__(self, error=None):
        self.error = error
        self.operations = []

    def _transition(self, operation, *_args):
        self.operations.append(operation)
        if self.error is not None:
            raise self.error
        return None, time.monotonic()


def _permit(controller, valid_until=None):
    snapshot = mod.GridMetAdmissionSnapshot("active", None, 0, 1, 4, 0)
    return mod.GridMetPermit(controller, "id", "secret-owner", valid_until or time.monotonic() + 100, snapshot)


def test_local_expiry_fails_even_without_background_failure():
    permit = _permit(_Controller(), time.monotonic() - 1)
    with pytest.raises(mod.GridMetAdmissionLostLease):
        permit.check()


def test_delayed_renew_reply_is_not_fresh(monkeypatch):
    controller = _Controller()
    permit = _permit(controller)
    monkeypatch.setattr(controller, "_transition", lambda *_: (None, time.monotonic() - 400))
    with pytest.raises(mod.GridMetAdmissionLostLease):
        permit.renew()


def test_renewal_failure_overrides_concurrent_upstream_error():
    permit = _permit(_Controller())
    permit._failure = mod.GridMetAdmissionUnavailable("renew unavailable")
    with pytest.raises(mod.GridMetAdmissionUnavailable, match="renew unavailable"):
        permit.__exit__(ValueError, ValueError("upstream"), None)
    assert permit.controller.operations == ["release"]


def test_cleanup_failure_preserves_primary_and_sanitizes_log(caplog):
    controller = _Controller(mod.GridMetAdmissionUnavailable("sensitive connection details"))
    permit = _permit(controller)
    assert permit.__exit__(ValueError, ValueError("primary"), None) is False
    assert "GridMetAdmissionUnavailable" in caplog.text
    assert "sensitive" not in caplog.text
    assert "secret-owner" not in caplog.text


def test_successful_payload_cannot_hide_release_failure():
    permit = _permit(_Controller(mod.GridMetAdmissionUnavailable("release unavailable")))
    with pytest.raises(mod.GridMetAdmissionUnavailable):
        permit.__exit__(None, None, None)


def test_delayed_acquire_reply_cannot_start_http(monkeypatch):
    controller = mod.GridMetAdmissionController(mod.GridMetAdmissionConfig())
    now = [100.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: now[0])
    operations = []

    def transition(operation, *_args, **_kwargs):
        operations.append(operation)
        now[0] = 500.0
        return mod.GridMetAdmissionSnapshot("active", None, 0, 1, 4, 0), 100.0

    monkeypatch.setattr(controller, "_transition", transition)
    with pytest.raises(mod.GridMetAdmissionLostLease):
        controller.acquire(request_kind="delayed")
    assert operations == ["enqueue", "cancel"]
    assert controller._wait_started == {}


def test_live_waiter_survives_more_than_fifteen_minutes(monkeypatch):
    controller = mod.GridMetAdmissionController(mod.GridMetAdmissionConfig())
    now = [100.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(mod.time, "sleep", lambda _: now.__setitem__(0, now[0] + 901))
    monkeypatch.setattr(mod.GridMetPermit, "_start_renewal", lambda self: None)
    tickets = []

    def transition(operation, ticket, token, **kwargs):
        tickets.append((ticket, token))
        state = "queued" if len(tickets) == 1 else "active"
        return mod.GridMetAdmissionSnapshot(state, 0, 1, 1, 4, 0), now[0]

    monkeypatch.setattr(controller, "_transition", transition)
    permit = controller.acquire(request_kind="long wait")
    assert permit.snapshot.waited_seconds == 901
    assert tickets[0] == tickets[1]
    permit.release()


@pytest.mark.parametrize("operation", ["enqueue", "poll", "renew", "release"])
def test_transport_recovery_preserves_ticket_and_sanitizes_logs(monkeypatch, caplog, operation):
    controller = mod.GridMetAdmissionController(mod.GridMetAdmissionConfig())
    calls = []
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)

    def transition(op, ticket, token):
        calls.append((op, ticket, token))
        if len(calls) == 1:
            raise mod._GridMetTransportError("GridMET admission unavailable (TimeoutError)")
        return "confirmed", time.monotonic()

    monkeypatch.setattr(controller, "_transition", transition)
    assert controller._retry_transition(operation, "private-ticket", "private-token")[0] == "confirmed"
    assert calls == [(operation, "private-ticket", "private-token")] * 2
    assert "recovering" in caplog.text
    assert "private-" not in caplog.text


def test_renewal_recovery_cannot_extend_expired_local_authority(monkeypatch):
    controller = mod.GridMetAdmissionController(mod.GridMetAdmissionConfig())
    now = [100.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: now[0])
    permit = _permit(controller, 101.0)

    def transition(*args):
        now[0] = 102.0
        return None, 100.0

    monkeypatch.setattr(controller, "_transition", transition)
    with pytest.raises(mod.GridMetAdmissionLostLease):
        permit.renew()
    with pytest.raises(mod.GridMetAdmissionLostLease):
        permit.check()


def test_manual_renew_failure_is_terminal():
    controller = _Controller(mod.GridMetAdmissionUnavailable("renew failed"))
    permit = _permit(controller)
    with pytest.raises(mod.GridMetAdmissionUnavailable):
        permit.renew()
    with pytest.raises(mod.GridMetAdmissionUnavailable):
        permit.check()
    with pytest.raises(mod.GridMetAdmissionUnavailable):
        permit.renew()


@pytest.mark.parametrize("renew_failed", [True, False])
@pytest.mark.parametrize("release_failed", [True, False])
def test_inflight_renew_is_joined_before_terminal_failure_check(renew_failed, release_failed):
    import threading
    controller = _Controller()
    entered = threading.Event()
    complete = threading.Event()
    permit = _permit(controller)

    def transition(operation, *_args):
        controller.operations.append(operation)
        if operation == "renew":
            entered.set()
            assert complete.wait(2)
            if renew_failed:
                raise mod.GridMetAdmissionUnavailable("inflight renewal failed")
        if operation == "release" and release_failed and controller.operations.count("release") == 1:
            raise mod._GridMetTransportError("release timeout")
        return None, time.monotonic()

    controller._transition = transition

    def run_renew():
        try:
            permit.renew()
        except mod.GridMetAdmissionError:
            pass  # The public method records the terminal error for the owner.

    permit._thread = threading.Thread(target=run_renew)
    permit._thread.start()
    assert entered.wait(2)
    original_join = permit._thread.join

    def join(timeout):
        complete.set()
        original_join(timeout)

    permit._thread.join = join
    if renew_failed:
        with pytest.raises(mod.GridMetAdmissionUnavailable, match="inflight renewal failed"):
            permit.__exit__(None, None, None)
    else:
        assert permit.__exit__(None, None, None) is False
    assert controller.operations == ["renew", "release"] + (["release"] if release_failed and not renew_failed else [])


@pytest.mark.parametrize("field", ["lease_seconds", "queue_ttl_seconds", "wait_timeout_seconds", "poll_interval_seconds"])
@pytest.mark.parametrize("value", [1e100, 10**400])
def test_unrepresentable_timings_rejected_before_io(field, value):
    with pytest.raises(mod.GridMetAdmissionConfigError):
        mod.GridMetAdmissionConfig(**{field: value})


def test_active_snapshot_freezes_queue_wait(monkeypatch):
    controller = mod.GridMetAdmissionController(mod.GridMetAdmissionConfig())
    now = [95.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(mod.GridMetPermit, "_start_renewal", lambda self: None)

    class Connection:
        calls = 0

        def eval(self, *_args):
            self.calls += 1
            if self.calls == 1:
                now[0] = 99.0
            return ["ok", "active", -1, 0, 1, 4, "100000", "policy", 1]

    connection = Connection()
    monkeypatch.setattr(controller, "_connection", lambda: connection)
    permit = controller.acquire(request_kind="wait timing")
    assert permit.snapshot.waited_seconds == 4
    assert controller.snapshot(permit.ticket_id).waited_seconds == 4
    now[0] = 200
    assert controller.snapshot(permit.ticket_id).waited_seconds == 4
    assert controller.snapshot("foreign").waited_seconds == 0
    permit.release()
    assert controller._wait_started == {}


def test_invalid_context_entry_releases_owned_state():
    controller = _Controller()
    permit = _permit(controller, time.monotonic() - 1)
    with pytest.raises(mod.GridMetAdmissionLostLease):
        permit.__enter__()
    assert controller.operations == ["release"]


def test_release_revokes_authority_before_lost_reply_recovery(monkeypatch):
    controller = _Controller()
    permit = _permit(controller)
    calls = []
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)

    def transition(*args):
        calls.append(args)
        with pytest.raises(mod.GridMetAdmissionLostLease):
            permit.check()
        if len(calls) == 1:
            raise mod._GridMetTransportError("release timeout")
        return None, time.monotonic()

    controller._transition = transition
    permit.release()
    permit.release()
    assert len(calls) == 2


@pytest.mark.parametrize("primary", [KeyboardInterrupt(), SystemExit(), ValueError("upstream")])
def test_active_exception_cleanup_does_not_wait_for_redis_recovery(primary):
    controller = _Controller(mod._GridMetTransportError("release timeout"))
    permit = _permit(controller)
    assert permit.__exit__(type(primary), primary, None) is False
    assert controller.operations == ["release"]
    with pytest.raises(mod.GridMetAdmissionLostLease):
        permit.check()


def test_failed_release_can_be_retried_without_restoring_authority():
    controller = _Controller(mod.GridMetAdmissionUnavailable("state unavailable"))
    permit = _permit(controller)
    with pytest.raises(mod.GridMetAdmissionUnavailable):
        permit.release()
    with pytest.raises(mod.GridMetAdmissionLostLease):
        permit.check()
    controller.error = None
    permit.release()
    assert controller.operations == ["release", "release"]


@pytest.mark.parametrize("error_name,retryable", [
    ("AuthenticationError", False), ("AuthorizationError", False),
    ("ResponseError", False), ("ConnectionError", True), ("TimeoutError", True),
])
def test_redis_exception_classification_and_redaction(monkeypatch, caplog, error_name, retryable):
    import redis
    controller = mod.GridMetAdmissionController(mod.GridMetAdmissionConfig())
    calls = []

    class Connection:
        def eval(self, *args):
            calls.append(args)
            if len(calls) == 1:
                raise getattr(redis.exceptions, error_name)("private password token URL")
            return ["ok", "active", -1, 0, 1, 4, "100000", "policy", 1]

    monkeypatch.setattr(controller, "_connection", lambda: Connection())
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)
    if retryable:
        assert controller._retry_transition("enqueue", "ticket", "token")[0].state == "active"
        assert len(calls) == 2
    else:
        with pytest.raises(mod.GridMetAdmissionUnavailable) as caught:
            controller._retry_transition("enqueue", "ticket", "token")
        assert error_name in str(caught.value)
        assert "private" not in str(caught.value)
        assert len(calls) == 1
    assert "private" not in caplog.text


def test_manual_and_background_renewals_do_not_overlap():
    import threading
    controller = _Controller()
    permit = _permit(controller)
    first_entered = threading.Event()
    finish_first = threading.Event()
    second_started = threading.Event()
    second_entered = threading.Event()
    failures = []
    calls = []

    def transition(*args):
        calls.append(args)
        if len(calls) == 1:
            first_entered.set()
            assert finish_first.wait(2)
        else:
            second_entered.set()
        return None, time.monotonic()

    controller._transition = transition

    def renew(started=None):
        if started is not None:
            started.set()
        try:
            permit.renew()
        except mod.GridMetAdmissionError as exc:
            failures.append(exc)

    first = threading.Thread(target=renew)
    second = threading.Thread(target=renew, args=(second_started,))
    first.start()
    assert first_entered.wait(2)
    second.start()
    assert second_started.wait(2)
    try:
        assert not second_entered.wait(0.05)
    finally:
        finish_first.set()
        first.join(2)
        second.join(2)
    assert not first.is_alive() and not second.is_alive()
    assert second_entered.is_set() and not failures
    permit.check()
    permit.release()
