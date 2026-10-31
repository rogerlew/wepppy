"""NFMS failure-stage and compatibility evidence through real NoDb files."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from uuid import uuid4

import pytest

import wepppy.nodb.base as base
from tests.nodb.test_base_boundary_characterization import _DummyNoDb, _RedisStub
from tests.rq.test_rq212_lifecycle import lifecycle  # noqa: F401

pytestmark = pytest.mark.integration


class MatrixNoDb(_DummyNoDb):
    filename = "matrix.nodb"


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "redis_lock_client", _RedisStub())
    monkeypatch.setattr(base, "redis_nodb_cache_client", None)
    wd = tmp_path / ("nfms-" + uuid4().hex)
    wd.mkdir()
    controller = MatrixNoDb(str(wd))
    with controller.locked():
        controller.value = "A"
        controller.nested = {"list": ["A"]}
    controller = MatrixNoDb.getInstance(str(wd))
    try:
        yield controller, wd
    finally:
        MatrixNoDb._instances.pop(str(wd), None)


def _assert_clean_followup(controller, wd, expected="A"):
    assert controller.value == expected
    assert MatrixNoDb.getInstance(str(wd)) is controller
    assert MatrixNoDb.load_detached(str(wd)).value == expected
    with controller.locked():
        controller.unrelated = "C"
    assert MatrixNoDb.load_detached(str(wd)).value == expected
    assert not list(wd.glob(".matrix.nodb.*.tmp"))


@pytest.mark.parametrize("stage", ["encode", "temp_write", "temp_fsync", "replace"])
def test_precommit_fault_restores_memory_and_later_save(state, monkeypatch, stage):
    controller, wd = state
    original = (wd / MatrixNoDb.filename).read_bytes()
    with monkeypatch.context() as fault:
        def fail(*_args, **_kwargs):
            raise OSError("injected " + stage)

        if stage == "encode":
            real_encode = base.jsonpickle.encode

            def encode(value, *args, **kwargs):
                if value is controller:
                    fail()
                return real_encode(value, *args, **kwargs)

            fault.setattr(base.jsonpickle, "encode", encode)
        elif stage == "temp_write":
            real_fdopen = base.os.fdopen

            class FailingWriter:
                def __init__(self, *args, **kwargs):
                    self.file = real_fdopen(*args, **kwargs)

                def __enter__(self):
                    self.file.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.file.__exit__(*args)

                def __getattr__(self, name):
                    return getattr(self.file, name)

                def write(self, payload):
                    self.file.write(payload[:10])
                    fail()

            fault.setattr(base.os, "fdopen", FailingWriter)
        else:
            fault.setattr(base.os, "fsync" if stage == "temp_fsync" else "replace", fail)
        with pytest.raises(OSError, match="injected " + stage):
            with controller.locked():
                controller.value = "B"
                controller.nested["list"].append("B")
    assert (wd / MatrixNoDb.filename).read_bytes() == original
    assert controller.nested == {"list": ["A"]}
    _assert_clean_followup(controller, wd)


@pytest.mark.parametrize("stage", ["version", "notification", "unlock", "hook"])
def test_postcommit_fault_keeps_committed_generation(state, monkeypatch, stage):
    controller, wd = state
    with monkeypatch.context() as fault:
        def fail(*_args, **_kwargs):
            raise RuntimeError("postcommit " + stage)

        if stage == "version":
            fault.setattr(base, "write_version", fail)
        elif stage == "notification":
            from wepppy.nodb import persistence_events
            fault.setattr(persistence_events, "notify_committed", fail)
        elif stage == "unlock":
            real_unlock = MatrixNoDb.unlock
            failed = False

            def unlock_once(self, *args, **kwargs):
                nonlocal failed
                if not failed:
                    failed = True
                    fail()
                return real_unlock(self, *args, **kwargs)

            fault.setattr(MatrixNoDb, "unlock", unlock_once)
        else:
            def hook(cls, instance):
                instance.value = "rejected hook mutation"
                fail()

            fault.setattr(MatrixNoDb, "_post_dump_and_unlock", classmethod(hook))
        with pytest.raises(RuntimeError, match="postcommit " + stage):
            with controller.locked():
                controller.value = "B"
    _assert_clean_followup(controller, wd, expected="B")


def test_intermediate_commit_followed_by_failure_keeps_that_generation(state):
    controller, wd = state
    with pytest.raises(ValueError, match="later failure"):
        with controller.locked():
            controller.value = "committed"
            controller.dump()
            controller.value = "rejected"
            raise ValueError("later failure")
    _assert_clean_followup(controller, wd, expected="committed")


@pytest.mark.parametrize("signal", [KeyboardInterrupt, SystemExit])
def test_baseexception_signal_restores_state_and_propagates(state, signal):
    controller, wd = state
    with pytest.raises(signal):
        with controller.locked():
            controller.value = "B"
            raise signal("cancelled")
    _assert_clean_followup(controller, wd)


@pytest.mark.parametrize("fault_kind", ["missing", "malformed", "unreadable", "redis"])
def test_failed_recovery_blocks_held_state_then_explicitly_recovers(state, monkeypatch, fault_kind):
    controller, wd = state
    path = wd / MatrixNoDb.filename
    original = path.read_bytes()
    with monkeypatch.context() as fault:
        with pytest.raises(ValueError, match="primary failure") as raised:
            with controller.locked():
                controller.value = "B"
                if fault_kind == "missing":
                    path.unlink()
                elif fault_kind == "malformed":
                    path.write_text("{broken")
                elif fault_kind == "unreadable":
                    def unreadable(*_args, **_kwargs):
                        raise PermissionError("recovery read denied")
                    fault.setattr(base._read_retry, "read_text_snapshot", unreadable)
                else:
                    def unavailable(*_args, **_kwargs):
                        raise base.redis.exceptions.ConnectionError("recovery redis outage")
                    fault.setattr(base.redis_lock_client, "get", unavailable)
                raise ValueError("primary failure")
        assert getattr(raised.value, "__notes__", None) or raised.value.__context__
        with pytest.raises(RuntimeError):
            _ = controller.value
        with pytest.raises(RuntimeError):
            controller.dump()
    if fault_kind in ("missing", "malformed"):
        path.write_bytes(original)
    controller.recover_mutation_state()
    _assert_clean_followup(controller, wd)


@pytest.mark.parametrize("mode", ["legacy", "detached", "ignore_lock", "readonly"])
def test_compatible_read_modes_and_failed_mutation(state, mode):
    original, wd = state
    if mode == "legacy":
        path = wd / MatrixNoDb.filename
        payload = json.loads(path.read_text())
        persisted = payload.get("py/state", payload)
        persisted.pop("_nodb_mtime", None)
        persisted.pop("_nodb_size", None)
        path.write_text(json.dumps(payload))
        controller = MatrixNoDb.getInstance(str(wd))
    elif mode == "detached":
        controller = MatrixNoDb.load_detached(str(wd))
    elif mode == "ignore_lock":
        controller = MatrixNoDb.getInstance(str(wd), ignore_lock=True)
    else:
        (wd / "READONLY").touch()
        controller = MatrixNoDb.getInstance(str(wd), ignore_lock=True)
        assert controller.value == "A"
        with pytest.raises(Exception, match="readonly"):
            with controller.locked():
                pytest.fail("readonly mutation admitted")
        assert controller.value == "A"
        return
    with pytest.raises(ValueError, match="discard"):
        with controller.locked():
            controller.value = "B"
            raise ValueError("discard")
    assert controller.value == "A"
    assert original.value == "A"
    with controller.locked():
        controller.unrelated = "C"
    assert MatrixNoDb.load_detached(str(wd)).value == "A"


@pytest.mark.slow
def test_real_redis_expired_scope_fences_same_object_and_keeps_newer_writer(state, monkeypatch, lifecycle):
    controller, wd = state
    connection = lifecycle.connection
    monkeypatch.setattr(base, "redis_lock_client", connection)
    entered, release = threading.Event(), threading.Event()
    errors = []
    key = controller._distributed_lock_key
    runid = controller.runid

    def old_owner():
        try:
            with controller.locked():
                controller.value = "B"
                entered.set()
                assert release.wait(10)
                raise ValueError("old owner aborted")
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=old_owner)
    thread.start()
    try:
        assert entered.wait(10)
        token = base._get_local_lock_token(controller)
        signature = (controller._nodb_mtime, controller._nodb_size)
        # Expire only this disposable run's key, without waiting on wall-clock TTL.
        assert connection.pexpire(key, 0)
        with pytest.raises(base.NoDbAlreadyLockedError):
            controller.lock()
        assert base._get_local_lock_token(controller) == token
        assert (controller._nodb_mtime, controller._nodb_size) == signature
        assert controller.value == "B"
        competing = MatrixNoDb.load_detached(str(wd))
        with competing.locked(validate_on_success=False):
            competing.value = "newer"
        release.set()
        thread.join(10)
        assert not thread.is_alive()
        assert len(errors) == 1 and isinstance(errors[0], ValueError)
        assert str(errors[0]) == "old owner aborted"
        _assert_clean_followup(controller, wd, expected="newer")
        assert connection.get(key) is None
    finally:
        release.set()
        thread.join(10)
        connection.delete(key, runid)


def test_explicit_recovery_cannot_quarantine_another_threads_live_owner(state):
    controller, wd = state
    entered, release = threading.Event(), threading.Event()
    failures = []

    def owner():
        try:
            with controller.locked():
                controller.value = "valid owner"
                entered.set()
                assert release.wait(10)
        except BaseException as exc:
            failures.append(exc)

    thread = threading.Thread(target=owner)
    thread.start()
    try:
        assert entered.wait(10)
        with pytest.raises(RuntimeError, match="thread|owner|mutation"):
            controller.recover_mutation_state()
        assert controller.value == "valid owner"
        assert MatrixNoDb.load_detached(str(wd)).value == "A"
    finally:
        release.set()
        thread.join(10)
    assert not thread.is_alive()
    assert not failures
    assert MatrixNoDb.load_detached(str(wd)).value == "valid owner"


def test_hydration_install_cannot_overwrite_newly_acquired_owner(state, monkeypatch):
    controller, wd = state
    competing = MatrixNoDb.load_detached(str(wd))
    with competing.locked(validate_on_success=False):
        competing.value = "new durable generation"
    hydrated, install = threading.Event(), threading.Event()
    errors = []
    real_hydrate = MatrixNoDb._hydrate_instance

    def pause_hydration(cls, *args, **kwargs):
        loaded = real_hydrate(*args, **kwargs)
        hydrated.set()
        assert install.wait(10)
        return loaded

    monkeypatch.setattr(MatrixNoDb, "_hydrate_instance", classmethod(pause_hydration))

    def reader():
        try:
            MatrixNoDb.getInstance(str(wd))
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=reader)
    thread.start()
    try:
        assert hydrated.wait(10)
        with pytest.raises(ValueError, match="abort new owner"):
            with controller.locked():
                controller.value = "new owner live mutation"
                install.set()
                thread.join(10)
                assert not thread.is_alive()
                assert len(errors) == 1 and isinstance(errors[0], base.NoDbAlreadyLockedError)
                assert controller.value == "new owner live mutation"
                raise ValueError("abort new owner")
        assert controller.value == "new durable generation"
    finally:
        install.set()
        thread.join(10)


@pytest.mark.slow
def test_real_redis_lost_owner_cannot_release_or_restore_active_replacement(state, monkeypatch, lifecycle):
    controller, wd = state
    connection = lifecycle.connection
    monkeypatch.setattr(base, "redis_lock_client", connection)
    key, runid = controller._distributed_lock_key, controller.runid
    competing = MatrixNoDb.load_detached(str(wd))
    try:
        with pytest.raises(ValueError, match="old operation failed"):
            with controller.locked():
                controller.value = "rejected B"
                assert connection.pexpire(key, 0)
                competing.lock()
                competing.value = "replacement C"
                replacement_payload = connection.get(key)
                raise ValueError("old operation failed")
        assert connection.get(key) == replacement_payload
        assert competing.value == "replacement C"
        assert MatrixNoDb.load_detached(str(wd)).value == "A"
        with pytest.raises(RuntimeError):
            _ = controller.value
        competing.dump()
        competing.unlock()
        controller.recover_mutation_state()
        _assert_clean_followup(controller, wd, expected="replacement C")
        assert connection.get(key) is None
    finally:
        connection.delete(key, runid)


def test_later_request_thread_recovers_orphaned_abort_lock_after_redis_outage(state, monkeypatch):
    controller, wd = state
    failures = []
    with monkeypatch.context() as fault:
        def owner():
            try:
                with controller.locked():
                    controller.value = "B"

                    def unavailable(*_args, **_kwargs):
                        raise base.redis.exceptions.ConnectionError("abort outage")

                    fault.setattr(base.redis_lock_client, "get", unavailable)
                    raise ValueError("failed request")
            except BaseException as exc:
                failures.append(exc)

        thread = threading.Thread(target=owner)
        thread.start()
        thread.join(10)
        assert not thread.is_alive()
    assert len(failures) == 1 and isinstance(failures[0], ValueError)
    controller.recover_mutation_state()
    _assert_clean_followup(controller, wd)


@pytest.mark.parametrize("stage,signal", [("recovery", KeyboardInterrupt), ("cleanup", SystemExit)])
def test_secondary_cancellation_propagates_with_primary_context(state, monkeypatch, stage, signal):
    controller, wd = state
    with monkeypatch.context() as fault:
        if stage == "recovery":
            def cancel_recovery(*_args, **_kwargs):
                raise signal("secondary cancellation")
            fault.setattr(base._read_retry, "read_text_snapshot", cancel_recovery)
        else:
            real_unlock = MatrixNoDb.unlock
            cancelled = False

            def cancel_cleanup(self, *args, **kwargs):
                nonlocal cancelled
                if not cancelled:
                    cancelled = True
                    raise signal("secondary cancellation")
                return real_unlock(self, *args, **kwargs)

            fault.setattr(MatrixNoDb, "unlock", cancel_cleanup)
        with pytest.raises(signal, match="secondary cancellation") as raised:
            with controller.locked():
                controller.value = "B"
                raise ValueError("primary operation error")
        assert isinstance(raised.value.__cause__, ValueError)
        assert str(raised.value.__cause__) == "primary operation error"
    if stage == "recovery":
        controller.recover_mutation_state()
    else:
        controller.unlock()
    _assert_clean_followup(controller, wd)


def test_failed_live_identity_change_recovers_original_file_and_releases_original_key(state):
    controller, wd = state
    original_key = controller._distributed_lock_key
    foreign = wd.parent / "foreign-run"
    with pytest.raises(ValueError, match="identity mutation failed"):
        with controller.locked():
            controller.value = "B"
            controller.wd = str(foreign)
            controller._run_group = "batch"
            controller._group_name = "foreign-group"
            raise ValueError("identity mutation failed")
    assert controller.wd == str(wd)
    assert controller._distributed_lock_key == original_key
    assert base.redis_lock_client.get(original_key) is None
    assert not foreign.exists()
    _assert_clean_followup(controller, wd)


def test_recovery_rejects_durable_identity_change_then_recovers_original(state):
    controller, wd = state
    path = wd / MatrixNoDb.filename
    original = path.read_bytes()
    original_key = controller._distributed_lock_key
    with pytest.raises(ValueError, match="primary identity failure") as raised:
        with controller.locked():
            controller.value = "B"
            payload = json.loads(original)
            persisted = payload.get("py/state", payload)
            persisted["_run_group"] = "batch"
            persisted["_group_name"] = "foreign-group"
            path.write_text(json.dumps(payload))
            raise ValueError("primary identity failure")
    assert "identity" in " ".join(getattr(raised.value, "__notes__", []))
    assert base.redis_lock_client.get(original_key) is None
    with pytest.raises(RuntimeError):
        _ = controller.value
    path.write_bytes(original)
    controller.recover_mutation_state()
    _assert_clean_followup(controller, wd)


def test_delayed_hydration_cannot_clear_a_later_failed_recovery(state, monkeypatch):
    controller, wd = state
    competing = MatrixNoDb.load_detached(str(wd))
    with competing.locked(validate_on_success=False):
        competing.value = "new durable generation"
    path = wd / MatrixNoDb.filename
    accepted = path.read_bytes()
    hydrated, install = threading.Event(), threading.Event()
    errors = []
    real_hydrate = MatrixNoDb._hydrate_instance

    def pause_hydration(cls, *args, **kwargs):
        loaded = real_hydrate(*args, **kwargs)
        hydrated.set()
        assert install.wait(10)
        return loaded

    monkeypatch.setattr(MatrixNoDb, "_hydrate_instance", classmethod(pause_hydration))

    def reader():
        try:
            MatrixNoDb.getInstance(str(wd))
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=reader)
    thread.start()
    try:
        assert hydrated.wait(10)
        with pytest.raises(ValueError, match="fail after earlier hydration"):
            with controller.locked():
                controller.value = "B"
                path.write_text("{malformed")
                raise ValueError("fail after earlier hydration")
        install.set()
        thread.join(10)
        assert not thread.is_alive()
        assert len(errors) == 1 and isinstance(errors[0], RuntimeError)
        with pytest.raises(RuntimeError):
            _ = controller.value
        path.write_bytes(accepted)
        controller.recover_mutation_state()
        assert controller.value == "new durable generation"
    finally:
        install.set()
        thread.join(10)


@pytest.mark.parametrize("signal", [KeyboardInterrupt, SystemExit])
def test_recovery_unlock_error_does_not_mask_recovery_cancellation(state, monkeypatch, signal):
    controller, wd = state
    with monkeypatch.context() as fault:
        with pytest.raises(signal, match="cancel during recovery") as raised:
            with controller.locked():
                controller.value = "B"
                # Force recovery to reacquire rather than reuse the original lock.
                controller.unlock()

                def cancel_read(*_args, **_kwargs):
                    raise signal("cancel during recovery")

                def fail_cleanup(*_args, **_kwargs):
                    raise RuntimeError("recovery unlock service failure")

                fault.setattr(base._read_retry, "read_text_snapshot", cancel_read)
                fault.setattr(MatrixNoDb, "unlock", fail_cleanup)
                raise ValueError("original operation failure")
        assert isinstance(raised.value.__cause__, ValueError)
        assert "recovery unlock service failure" in " ".join(getattr(raised.value, "__notes__", []))
        with pytest.raises(RuntimeError):
            _ = controller.value
    controller.recover_mutation_state()
    _assert_clean_followup(controller, wd)


def test_quarantined_state_rejects_direct_attribute_deletion(state):
    controller, wd = state
    path = wd / MatrixNoDb.filename
    original = path.read_bytes()
    with pytest.raises(ValueError, match="failed mutation"):
        with controller.locked():
            controller.value = "B"
            path.write_text("{corrupt")
            raise ValueError("failed mutation")
    with pytest.raises(RuntimeError, match="recover|unavailable"):
        del controller.value
    path.write_bytes(original)
    controller.recover_mutation_state()
    _assert_clean_followup(controller, wd)


def test_failed_first_create_allows_optional_absence_and_fresh_initialization(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "redis_lock_client", _RedisStub())
    monkeypatch.setattr(base, "redis_nodb_cache_client", None)
    wd = tmp_path / ("nfms-initial-" + uuid4().hex)
    wd.mkdir()
    failed = MatrixNoDb(str(wd))
    try:
        with pytest.raises(ValueError, match="first creation failed"):
            with failed.locked():
                failed.value = "rejected"
                raise ValueError("first creation failed")
        assert not (wd / MatrixNoDb.filename).exists()
        with pytest.raises(RuntimeError):
            _ = failed.value
        assert MatrixNoDb.getInstance(str(wd), allow_nonexistent=True) is None
        fresh = MatrixNoDb(str(wd))
        with fresh.locked():
            fresh.value = "accepted initialization"
        assert MatrixNoDb.load_detached(str(wd)).value == "accepted initialization"
        assert fresh.value == "accepted initialization"
    finally:
        MatrixNoDb._instances.pop(str(wd), None)


class TransientMatrixNoDb(MatrixNoDb):
    filename = "transient-matrix.nodb"
    TRANSIENT_FIELDS = ("derived_cache",)

    @classmethod
    def _post_instance_loaded(cls, instance):
        instance = super()._post_instance_loaded(instance)
        instance.derived_cache = {"derived_from": instance.value}
        return instance


def test_failed_mutation_rebuilds_declared_transient_cache_from_durable_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "redis_lock_client", _RedisStub())
    monkeypatch.setattr(base, "redis_nodb_cache_client", None)
    wd = tmp_path / ("nfms-transient-" + uuid4().hex)
    wd.mkdir()
    controller = TransientMatrixNoDb(str(wd))
    try:
        with controller.locked():
            controller.value = "A"
            controller.derived_cache = {"derived_from": "A"}
        with pytest.raises(ValueError, match="cache mutation failed"):
            with controller.locked():
                controller.value = "B"
                controller.derived_cache["derived_from"] = "B"
                raise ValueError("cache mutation failed")
        assert controller.value == "A"
        assert controller.derived_cache == {"derived_from": "A"}
        assert "derived_cache" not in (wd / controller.filename).read_text()
        with controller.locked():
            controller.unrelated = "C"
        assert TransientMatrixNoDb.load_detached(str(wd)).derived_cache == {"derived_from": "A"}
    finally:
        TransientMatrixNoDb._instances.pop(str(wd), None)


def test_concurrent_explicit_recovery_cannot_replace_first_recoverers_token(state, monkeypatch):
    controller, wd = state
    path = wd / MatrixNoDb.filename
    original = path.read_bytes()
    key = controller._distributed_lock_key
    with pytest.raises(ValueError, match="quarantine initial failure"):
        with controller.locked():
            controller.value = "B"
            path.write_text("{malformed")
            raise ValueError("quarantine initial failure")
    path.write_bytes(original)
    entered, release = threading.Event(), threading.Event()
    failures = []
    real_read = base._read_retry.read_text_snapshot

    def paused_read(*args, **kwargs):
        if threading.current_thread().name == "first-nfms-recoverer":
            entered.set()
            assert release.wait(10)
        return real_read(*args, **kwargs)

    monkeypatch.setattr(base._read_retry, "read_text_snapshot", paused_read)

    def first_recoverer():
        try:
            controller.recover_mutation_state()
        except BaseException as exc:
            failures.append(exc)

    thread = threading.Thread(target=first_recoverer, name="first-nfms-recoverer")
    thread.start()
    try:
        assert entered.wait(10)
        first_token = base._get_local_lock_token(controller)
        assert first_token is not None
        base.redis_lock_client.delete(key)
        with pytest.raises((RuntimeError, base.NoDbAlreadyLockedError)):
            controller.recover_mutation_state()
        assert base._get_local_lock_token(controller) == first_token
    finally:
        release.set()
        thread.join(10)
    assert not thread.is_alive()
    assert len(failures) == 1 and isinstance(failures[0], RuntimeError)
    controller.recover_mutation_state()
    _assert_clean_followup(controller, wd)


def test_high_level_stale_write_rejection_recovers_newer_durable_generation(state):
    controller, wd = state
    competing = MatrixNoDb.load_detached(str(wd))
    with competing.locked(validate_on_success=False):
        competing.value = "accepted newer generation"
    with pytest.raises(base.NoDbStaleWriteError):
        with controller.locked():
            controller.value = "rejected stale mutation"
    _assert_clean_followup(controller, wd, expected="accepted newer generation")
