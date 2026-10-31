"""Real persisted-state regressions for grouped compensation and failed reuse."""
from pathlib import Path

import pytest

import wepppy.nodb.base as base
from tests.nodb.test_base_boundary_characterization import _RedisStub
from wepppy.microservices.rq_engine.wepp_run_payload import _apply_grouped_soils_watershed_updates
from wepppy.nodb.core import Ron, Soils, Watershed

pytestmark = pytest.mark.integration


@pytest.fixture
def controllers(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "redis_lock_client", _RedisStub())
    monkeypatch.setattr(base, "redis_nodb_cache_client", None)
    wd = str(tmp_path)
    Ron(wd, "canada-wbt-mofe.cfg", initialize_components=False)
    soils = Soils(wd, "canada-wbt-mofe.cfg")
    watershed = Watershed(wd, "canada-wbt-mofe.cfg")
    with soils.locked():
        soils._initial_sat = 0.2
    with watershed.locked():
        watershed._clip_hillslopes = False
    try:
        yield soils, watershed
    finally:
        Ron.cleanup_run_instances(wd)
        Soils.cleanup_run_instances(wd)
        Watershed.cleanup_run_instances(wd)


def apply_group(soils, watershed):
    _apply_grouped_soils_watershed_updates(
        soils=soils, watershed=watershed, clip_soils=None,
        clip_soils_depth=None, clip_soils_minimum=None, clip_soils_minimum_depth=None,
        rosetta_wc_fc_from_disturbed_bd_override=None, initial_sat=0.9,
        clip_hillslopes=True, clip_hillslope_length=None,
    )


@pytest.mark.parametrize("compensation_fails", [False, True])
def test_grouped_failure_memory_matches_actual_compensation_outcome(
    controllers, monkeypatch, compensation_fails,
):
    soils, watershed = controllers
    replace = base.os.replace
    soils_replaces = 0

    def fail_named_replace(source, destination):
        nonlocal soils_replaces
        if Path(destination).name == "watershed.nodb":
            raise OSError("watershed persistence unavailable")
        if Path(destination).name == "soils.nodb":
            soils_replaces += 1
            if compensation_fails and soils_replaces == 2:
                raise OSError("soil compensation unavailable")
        return replace(source, destination)

    with monkeypatch.context() as fault:
        fault.setattr(base.os, "replace", fail_named_replace)
        with pytest.raises(OSError, match="watershed persistence unavailable"):
            apply_group(soils, watershed)

    # Successful compensation restores A. Failed compensation leaves the already
    # committed B authoritative; memory must not advertise the restored snapshot A.
    expected = 0.9 if compensation_fails else 0.2
    assert soils.initial_sat == expected
    assert Soils.load_detached(soils.wd).initial_sat == expected
    assert watershed.clip_hillslopes is False
    assert Watershed.load_detached(watershed.wd).clip_hillslopes is False
    with soils.locked():
        soils._clip_soils = True
    with watershed.locked():
        watershed._clip_hillslope_length = 456
    assert Soils.load_detached(soils.wd).initial_sat == expected
    assert Watershed.load_detached(watershed.wd).clip_hillslopes is False


def test_grouped_post_hook_failure_recovers_committed_generation(controllers, monkeypatch):
    soils, watershed = controllers

    def fail_hook(self, **kwargs):
        self._initial_sat = 0.7
        raise RuntimeError("post hook failed")

    monkeypatch.setattr(Soils, "post_finalize_grouped_wepp_run_payload_updates", fail_hook)
    with pytest.raises(RuntimeError, match="post hook failed"):
        apply_group(soils, watershed)
    assert soils.initial_sat == 0.9
    assert Soils.load_detached(soils.wd).initial_sat == 0.9
    assert watershed._clip_hillslopes is True
    assert Watershed.load_detached(watershed.wd)._clip_hillslopes is True


def test_grouped_cancellation_recovers_state_and_releases_locks(controllers, monkeypatch):
    soils, watershed = controllers

    class Cancelled(BaseException):
        pass

    def cancel_stage(self, **kwargs):
        self._clip_hillslopes = True
        raise Cancelled("cancelled")

    monkeypatch.setattr(Watershed, "stage_wepp_run_payload_updates", cancel_stage)
    with pytest.raises(Cancelled, match="cancelled"):
        apply_group(soils, watershed)
    assert soils.initial_sat == 0.2
    assert watershed.clip_hillslopes is False
    assert not soils.islocked()
    assert not watershed.islocked()


def test_grouped_compensation_cannot_overwrite_newer_writer(controllers, monkeypatch):
    soils, watershed = controllers
    replace = base.os.replace
    newer_committed = False

    def competing_writer_before_failure(source, destination):
        nonlocal newer_committed
        if Path(destination).name == "watershed.nodb":
            if not newer_committed:
                soils.unlock()
                other = Soils.load_detached(soils.wd)
                other.lock()
                try:
                    other._initial_sat = 0.6
                    other.dump()
                finally:
                    other.unlock()
                newer_committed = True
            raise OSError("watershed persistence unavailable")
        return replace(source, destination)

    with monkeypatch.context() as fault:
        fault.setattr(base.os, "replace", competing_writer_before_failure)
        with pytest.raises(OSError, match="watershed persistence unavailable"):
            apply_group(soils, watershed)
    assert newer_committed
    assert soils.initial_sat == 0.6
    assert Soils.load_detached(soils.wd).initial_sat == 0.6
    with soils.locked():
        soils._clip_soils = True
    assert Soils.load_detached(soils.wd).initial_sat == 0.6


@pytest.mark.parametrize("signal_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("cleanup_stage", ["restore", "compensation", "unlock"])
def test_cleanup_signal_after_operation_error_propagates_with_primary_context(
    controllers, monkeypatch, signal_type, cleanup_stage,
):
    soils, watershed = controllers
    signal = signal_type("cleanup signal")
    primary = OSError("primary grouped failure")

    if cleanup_stage == "compensation":
        replace = base.os.replace
        soil_writes = 0

        def fail_replacement(source, destination):
            nonlocal soil_writes
            if Path(destination).name == "watershed.nodb":
                raise primary
            if Path(destination).name == "soils.nodb":
                soil_writes += 1
                if soil_writes == 2:
                    raise signal
            return replace(source, destination)

        monkeypatch.setattr(base.os, "replace", fail_replacement)
    else:
        def fail_stage(self, **kwargs):
            self._clip_hillslopes = True
            raise primary

        monkeypatch.setattr(Watershed, "stage_wepp_run_payload_updates", fail_stage)
        if cleanup_stage == "restore":
            def interrupt_restore(self, snapshot):
                raise signal

            monkeypatch.setattr(Soils, "restore_wepp_run_payload_updates", interrupt_restore)
        else:
            unlock = Watershed.unlock
            interrupted = False

            def interrupt_unlock(self, *args, **kwargs):
                nonlocal interrupted
                unlock(self, *args, **kwargs)
                if not interrupted:
                    interrupted = True
                    raise signal

            monkeypatch.setattr(Watershed, "unlock", interrupt_unlock)

    with pytest.raises(signal_type, match="cleanup signal") as caught:
        apply_group(soils, watershed)
    assert caught.value is signal
    context = caught.value.__context__
    while context is not None and context is not primary:
        context = context.__context__
    assert context is primary
    expected = 0.9 if cleanup_stage == "compensation" else 0.2
    assert soils.initial_sat == expected
    assert Soils.load_detached(soils.wd).initial_sat == expected
    assert watershed._clip_hillslopes is False
    assert not soils.islocked()
    assert not watershed.islocked()
