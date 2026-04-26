from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import Mock

import pytest

import wepppy.microservices.rq_engine.wepp_run_payload as wepp_run_payload_module
from wepppy.microservices.rq_engine.wepp_run_payload import apply_wepp_run_payload
from wepppy.nodb.core.soils import Soils
from wepppy.nodb.core.watershed import Watershed


pytestmark = pytest.mark.unit


class _LockRecorder:
    def __init__(self) -> None:
        self.calls = 0
        self.enters = 0
        self.exits = 0

    def locked(self):
        self.calls += 1

        @contextmanager
        def _lock_scope():
            self.enters += 1
            try:
                yield
            finally:
                self.exits += 1

        return _lock_scope()


def test_soils_apply_wepp_run_payload_updates_noop_skips_lock_and_mutation() -> None:
    soils = object.__new__(Soils)
    soils._clip_soils = True
    soils._clip_soils_depth = 9.0
    soils._clip_soils_minimum = True
    soils._clip_soils_minimum_depth = 7.0
    soils._rosetta_wc_fc_from_disturbed_bd_override = True
    soils._initial_sat = 0.75

    lock = _LockRecorder()
    soils.locked = lock.locked

    soils.apply_wepp_run_payload_updates(
        clip_soils=None,
        clip_soils_depth=None,
        clip_soils_minimum=None,
        clip_soils_minimum_depth=None,
        rosetta_wc_fc_from_disturbed_bd_override=None,
        initial_sat=None,
    )

    assert lock.calls == 0
    assert soils._clip_soils is True
    assert soils._clip_soils_depth == 9.0
    assert soils._clip_soils_minimum is True
    assert soils._clip_soils_minimum_depth == 7.0
    assert soils._rosetta_wc_fc_from_disturbed_bd_override is True
    assert soils._initial_sat == 0.75


def test_soils_apply_wepp_run_payload_updates_uses_one_lock_and_applies_falsey_values() -> None:
    soils = object.__new__(Soils)
    soils._clip_soils = True
    soils._clip_soils_depth = 9.0
    soils._clip_soils_minimum = True
    soils._clip_soils_minimum_depth = 7.0
    soils._rosetta_wc_fc_from_disturbed_bd_override = True
    soils._initial_sat = 0.75

    lock = _LockRecorder()
    soils.locked = lock.locked

    soils.apply_wepp_run_payload_updates(
        clip_soils=False,
        clip_soils_depth=0.0,
        clip_soils_minimum=False,
        clip_soils_minimum_depth=0.0,
        rosetta_wc_fc_from_disturbed_bd_override=False,
        initial_sat=0.0,
    )

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert soils._clip_soils is False
    assert soils._clip_soils_depth == 0.0
    assert soils._clip_soils_minimum is False
    assert soils._clip_soils_minimum_depth == 0.0
    assert soils._rosetta_wc_fc_from_disturbed_bd_override is False
    assert soils._initial_sat == 0.0


def test_watershed_apply_wepp_run_payload_updates_noop_skips_lock_and_mutation() -> None:
    watershed = object.__new__(Watershed)
    watershed._clip_hillslopes = True
    watershed._clip_hillslope_length = 450.0

    lock = _LockRecorder()
    watershed.locked = lock.locked

    watershed.apply_wepp_run_payload_updates(
        clip_hillslopes=None,
        clip_hillslope_length=None,
    )

    assert lock.calls == 0
    assert watershed._clip_hillslopes is True
    assert watershed._clip_hillslope_length == 450.0


def test_watershed_apply_wepp_run_payload_updates_uses_one_lock_and_applies_falsey_values() -> None:
    watershed = object.__new__(Watershed)
    watershed._clip_hillslopes = True
    watershed._clip_hillslope_length = 450.0

    lock = _LockRecorder()
    watershed.locked = lock.locked

    watershed.apply_wepp_run_payload_updates(
        clip_hillslopes=False,
        clip_hillslope_length=0.0,
    )

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert watershed._clip_hillslopes is False
    assert watershed._clip_hillslope_length == 0.0


class _AtomicSoilsDummy:
    class_name = "soils"

    def __init__(
        self,
        event_log: list[tuple[str, str]],
        *,
        fail_on_lock: Exception | None = None,
        fail_on_stage: bool = False,
        fail_on_dump_call: int | None = None,
        fail_on_restore: Exception | None = None,
        fail_on_unlock: Exception | None = None,
        fail_on_unlock_call: int = 1,
        fail_on_snapshot_without_lock: bool = False,
    ) -> None:
        self._event_log = event_log
        self._fail_on_lock = fail_on_lock
        self._fail_on_stage = fail_on_stage
        self._fail_on_dump_call = fail_on_dump_call
        self._fail_on_restore = fail_on_restore
        self._fail_on_unlock = fail_on_unlock
        self._fail_on_unlock_call = fail_on_unlock_call
        self._fail_on_snapshot_without_lock = fail_on_snapshot_without_lock
        self._locked = False
        self._clip_soils = False
        self._clip_soils_depth = 100.0
        self._clip_soils_minimum = False
        self._clip_soils_minimum_depth = 0.0
        self._rosetta_wc_fc_from_disturbed_bd_override = False
        self._initial_sat = 0.75
        self.dump_states: list[dict[str, object]] = []
        self.snapshot_locked_states: list[bool] = []
        self.restore_calls = 0
        self.post_finalize_calls = 0
        self._unlock_calls = 0
        self._dump_calls = 0

    @property
    def clip_soils(self) -> bool:
        return self._clip_soils

    @property
    def clip_soils_depth(self) -> float:
        return self._clip_soils_depth

    @property
    def clip_soils_minimum(self) -> bool:
        return self._clip_soils_minimum

    @property
    def clip_soils_minimum_depth(self) -> float:
        return self._clip_soils_minimum_depth

    def lock(self) -> None:
        if self._fail_on_lock is not None:
            raise self._fail_on_lock
        if self._locked:
            raise RuntimeError("soils already locked")
        self._locked = True
        self._event_log.append(("lock", self.class_name))

    def unlock(self) -> None:
        self._unlock_calls += 1
        if self._fail_on_unlock is not None and self._unlock_calls >= self._fail_on_unlock_call:
            raise self._fail_on_unlock
        self._locked = False
        self._event_log.append(("unlock", self.class_name))

    def dump(self) -> None:
        if not self._locked:
            raise RuntimeError("soils dump without lock")
        self._dump_calls += 1
        self.dump_states.append(self.snapshot_wepp_run_payload_updates())
        self._event_log.append(("dump", self.class_name))
        if self._fail_on_dump_call is not None and self._dump_calls == self._fail_on_dump_call:
            raise RuntimeError("soils commit failed")

    def snapshot_wepp_run_payload_updates(self) -> dict[str, object]:
        self.snapshot_locked_states.append(self._locked)
        if self._fail_on_snapshot_without_lock and not self._locked:
            raise RuntimeError("soils snapshot without lock")
        return {
            "_clip_soils": self._clip_soils,
            "_clip_soils_depth": self._clip_soils_depth,
            "_clip_soils_minimum": self._clip_soils_minimum,
            "_clip_soils_minimum_depth": self._clip_soils_minimum_depth,
            "_rosetta_wc_fc_from_disturbed_bd_override": self._rosetta_wc_fc_from_disturbed_bd_override,
            "_initial_sat": self._initial_sat,
        }

    def restore_wepp_run_payload_updates(self, snapshot: dict[str, object]) -> None:
        self.restore_calls += 1
        if self._fail_on_restore is not None:
            raise self._fail_on_restore
        self._clip_soils = bool(snapshot["_clip_soils"])
        self._clip_soils_depth = float(snapshot["_clip_soils_depth"])
        self._clip_soils_minimum = bool(snapshot["_clip_soils_minimum"])
        self._clip_soils_minimum_depth = float(snapshot["_clip_soils_minimum_depth"])
        self._rosetta_wc_fc_from_disturbed_bd_override = bool(
            snapshot["_rosetta_wc_fc_from_disturbed_bd_override"]
        )
        self._initial_sat = float(snapshot["_initial_sat"])

    def stage_wepp_run_payload_updates(
        self,
        *,
        clip_soils=None,
        clip_soils_depth=None,
        clip_soils_minimum=None,
        clip_soils_minimum_depth=None,
        rosetta_wc_fc_from_disturbed_bd_override=None,
        initial_sat=None,
    ) -> bool:
        if self._fail_on_stage:
            raise RuntimeError("soils stage failed")
        has_updates = any(
            value is not None
            for value in (
                clip_soils,
                clip_soils_depth,
                clip_soils_minimum,
                clip_soils_minimum_depth,
                rosetta_wc_fc_from_disturbed_bd_override,
                initial_sat,
            )
        )
        if not has_updates:
            return False
        if clip_soils is not None:
            self._clip_soils = bool(clip_soils)
        if clip_soils_depth is not None:
            self._clip_soils_depth = float(clip_soils_depth)
        if clip_soils_minimum is not None:
            self._clip_soils_minimum = bool(clip_soils_minimum)
        if clip_soils_minimum_depth is not None:
            self._clip_soils_minimum_depth = float(clip_soils_minimum_depth)
        if rosetta_wc_fc_from_disturbed_bd_override is not None:
            self._rosetta_wc_fc_from_disturbed_bd_override = bool(
                rosetta_wc_fc_from_disturbed_bd_override
            )
        if initial_sat is not None:
            self._initial_sat = float(initial_sat)
        self._event_log.append(("stage", self.class_name))
        return True

    def post_finalize_grouped_wepp_run_payload_updates(self) -> None:
        self.post_finalize_calls += 1
        self._event_log.append(("post", self.class_name))


class _AtomicWatershedDummy:
    class_name = "watershed"

    def __init__(
        self,
        event_log: list[tuple[str, str]],
        *,
        fail_on_stage: bool = False,
        fail_on_dump_call: int | None = None,
        fail_on_unlock: Exception | None = None,
        fail_on_unlock_call: int = 1,
        fail_on_snapshot_without_lock: bool = False,
    ) -> None:
        self._event_log = event_log
        self._fail_on_stage = fail_on_stage
        self._fail_on_dump_call = fail_on_dump_call
        self._fail_on_unlock = fail_on_unlock
        self._fail_on_unlock_call = fail_on_unlock_call
        self._fail_on_snapshot_without_lock = fail_on_snapshot_without_lock
        self._locked = False
        self._clip_hillslopes = False
        self._clip_hillslope_length = 300.0
        self.dump_states: list[dict[str, object]] = []
        self.snapshot_locked_states: list[bool] = []
        self.restore_calls = 0
        self.post_finalize_calls = 0
        self._unlock_calls = 0
        self._dump_calls = 0

    @property
    def clip_hillslopes(self) -> bool:
        return self._clip_hillslopes

    @property
    def clip_hillslope_length(self) -> float:
        return self._clip_hillslope_length

    def lock(self) -> None:
        if self._locked:
            raise RuntimeError("watershed already locked")
        self._locked = True
        self._event_log.append(("lock", self.class_name))

    def unlock(self) -> None:
        self._unlock_calls += 1
        if self._fail_on_unlock is not None and self._unlock_calls >= self._fail_on_unlock_call:
            raise self._fail_on_unlock
        self._locked = False
        self._event_log.append(("unlock", self.class_name))

    def dump(self) -> None:
        if not self._locked:
            raise RuntimeError("watershed dump without lock")
        self._dump_calls += 1
        self.dump_states.append(self.snapshot_wepp_run_payload_updates())
        self._event_log.append(("dump", self.class_name))
        if self._fail_on_dump_call is not None and self._dump_calls == self._fail_on_dump_call:
            raise RuntimeError("watershed commit failed")

    def snapshot_wepp_run_payload_updates(self) -> dict[str, object]:
        self.snapshot_locked_states.append(self._locked)
        if self._fail_on_snapshot_without_lock and not self._locked:
            raise RuntimeError("watershed snapshot without lock")
        return {
            "_clip_hillslopes": self._clip_hillslopes,
            "_clip_hillslope_length": self._clip_hillslope_length,
        }

    def restore_wepp_run_payload_updates(self, snapshot: dict[str, object]) -> None:
        self.restore_calls += 1
        self._clip_hillslopes = bool(snapshot["_clip_hillslopes"])
        self._clip_hillslope_length = float(snapshot["_clip_hillslope_length"])

    def stage_wepp_run_payload_updates(
        self,
        *,
        clip_hillslopes=None,
        clip_hillslope_length=None,
    ) -> bool:
        if self._fail_on_stage:
            raise RuntimeError("watershed stage failed")
        if clip_hillslopes is None and clip_hillslope_length is None:
            return False
        if clip_hillslopes is not None:
            self._clip_hillslopes = bool(clip_hillslopes)
        if clip_hillslope_length is not None:
            self._clip_hillslope_length = float(clip_hillslope_length)
        self._event_log.append(("stage", self.class_name))
        return True

    def post_finalize_grouped_wepp_run_payload_updates(self) -> None:
        self.post_finalize_calls += 1
        self._event_log.append(("post", self.class_name))


class _AtomicWeppDummy:
    dss_excluded_channel_orders = [1, 2]
    _run_wepp_ui = True
    _run_wepp_watershed = True
    _run_pmet = True
    _run_frost = False
    _run_tcr = False
    _run_snow = True

    def __init__(self) -> None:
        self.parse_calls = 0

    def parse_inputs(self, payload: dict[str, object]) -> None:
        self.parse_calls += 1
        self.last_payload = dict(payload)

    @contextmanager
    def locked(self):
        yield self


class _AtomicRonDummy:
    mods = []


def test_apply_wepp_run_payload_grouped_updates_lock_conflict_raises_before_parse_or_persist() -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(event_log, fail_on_lock=RuntimeError("soils lock conflict"))
    watershed = _AtomicWatershedDummy(event_log)
    wepp = _AtomicWeppDummy()

    with pytest.raises(RuntimeError, match="soils lock conflict"):
        apply_wepp_run_payload(
            "/tmp/unit",
            {"clip_soils": True, "clip_hillslopes": True},
            wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
            soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
            watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
            ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
        )

    assert wepp.parse_calls == 0
    assert soils.dump_states == []
    assert watershed.dump_states == []
    assert soils.post_finalize_calls == 0
    assert watershed.post_finalize_calls == 0
    assert event_log == []


def test_apply_wepp_run_payload_grouped_updates_partial_lock_conflict_unlocks_already_acquired_lock() -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(event_log)
    watershed = _AtomicWatershedDummy(event_log)
    watershed.lock = Mock(side_effect=RuntimeError("watershed lock conflict"))
    wepp = _AtomicWeppDummy()

    with pytest.raises(RuntimeError, match="watershed lock conflict"):
        apply_wepp_run_payload(
            "/tmp/unit",
            {"clip_soils": True, "clip_hillslopes": True},
            wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
            soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
            watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
            ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
        )

    assert event_log == [("lock", "soils"), ("unlock", "soils")]
    assert wepp.parse_calls == 0
    assert soils.dump_states == []
    assert watershed.dump_states == []
    assert soils.post_finalize_calls == 0
    assert watershed.post_finalize_calls == 0


def test_apply_wepp_run_payload_grouped_updates_atomic_success() -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(event_log)
    watershed = _AtomicWatershedDummy(event_log)
    wepp = _AtomicWeppDummy()
    wd = "/tmp/unit"

    apply_wepp_run_payload(
        wd,
        {
            "clip_soils": True,
            "clip_soils_depth": 250,
            "clip_hillslopes": True,
            "hillslope_clip_length": 180,
            "initial_sat": 0.3,
        },
        wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
        soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
        watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
        ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
    )

    assert soils.clip_soils is True
    assert soils.clip_soils_depth == 250.0
    assert soils._initial_sat == 0.3
    assert watershed.clip_hillslopes is True
    assert watershed.clip_hillslope_length == 180.0
    assert len(soils.dump_states) == 1
    assert len(watershed.dump_states) == 1
    assert soils.post_finalize_calls == 1
    assert watershed.post_finalize_calls == 1
    assert event_log[:2] == [("lock", "soils"), ("lock", "watershed")]
    assert ("unlock", "watershed") in event_log
    assert ("unlock", "soils") in event_log
    assert ("post", "soils") in event_log
    assert ("post", "watershed") in event_log
    assert event_log.index(("unlock", "watershed")) < event_log.index(("post", "soils"))
    assert event_log.index(("unlock", "soils")) < event_log.index(("post", "watershed"))
    assert soils.snapshot_locked_states and all(soils.snapshot_locked_states)
    assert watershed.snapshot_locked_states and all(watershed.snapshot_locked_states)


def test_apply_wepp_run_payload_grouped_updates_soils_only_locks_only_soils() -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(event_log)
    watershed = _AtomicWatershedDummy(event_log)
    wepp = _AtomicWeppDummy()

    apply_wepp_run_payload(
        "/tmp/unit",
        {"clip_soils": True, "clip_soils_depth": 210},
        wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
        soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
        watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
        ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
    )

    assert ("lock", "watershed") not in event_log
    assert ("unlock", "watershed") not in event_log
    assert watershed.snapshot_locked_states == []
    assert watershed.dump_states == []
    assert watershed.post_finalize_calls == 0
    assert len(soils.dump_states) == 1
    assert soils.post_finalize_calls == 1


def test_apply_wepp_run_payload_grouped_updates_watershed_only_locks_only_watershed() -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(event_log)
    watershed = _AtomicWatershedDummy(event_log)
    wepp = _AtomicWeppDummy()

    apply_wepp_run_payload(
        "/tmp/unit",
        {"clip_hillslopes": True, "hillslope_clip_length": 190},
        wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
        soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
        watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
        ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
    )

    assert ("lock", "soils") not in event_log
    assert ("unlock", "soils") not in event_log
    assert soils.snapshot_locked_states == []
    assert soils.dump_states == []
    assert soils.post_finalize_calls == 0
    assert len(watershed.dump_states) == 1
    assert watershed.post_finalize_calls == 1


def test_apply_wepp_run_payload_grouped_updates_failure_before_commit_restores_both() -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(event_log)
    watershed = _AtomicWatershedDummy(event_log, fail_on_stage=True)
    wepp = _AtomicWeppDummy()
    wd = "/tmp/unit"
    soils_before = soils.snapshot_wepp_run_payload_updates()
    watershed_before = watershed.snapshot_wepp_run_payload_updates()

    with pytest.raises(RuntimeError, match="watershed stage failed"):
        apply_wepp_run_payload(
            wd,
            {
                "clip_soils": True,
                "clip_hillslopes": True,
            },
            wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
            soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
            watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
            ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
        )

    assert soils.snapshot_wepp_run_payload_updates() == soils_before
    assert watershed.snapshot_wepp_run_payload_updates() == watershed_before
    assert soils.dump_states == []
    assert watershed.dump_states == []
    assert soils.restore_calls == 1
    assert watershed.restore_calls == 1
    assert soils.post_finalize_calls == 0
    assert watershed.post_finalize_calls == 0
    assert event_log[:2] == [("lock", "soils"), ("lock", "watershed")]
    assert event_log[-2:] == [("unlock", "watershed"), ("unlock", "soils")]


def test_apply_wepp_run_payload_grouped_updates_restore_failure_logs_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(event_log, fail_on_restore=ValueError("soils restore failed"))
    watershed = _AtomicWatershedDummy(event_log, fail_on_stage=True)
    wepp = _AtomicWeppDummy()
    exception_mock = Mock()
    monkeypatch.setattr(wepp_run_payload_module.logger, "exception", exception_mock)

    with pytest.raises(RuntimeError, match="watershed stage failed"):
        apply_wepp_run_payload(
            "/tmp/unit",
            {"clip_soils": True, "clip_hillslopes": True},
            wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
            soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
            watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
            ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
        )

    assert exception_mock.call_count == 1
    logged_call = exception_mock.call_args_list[0]
    assert "restore failed" in str(logged_call.args[0])
    assert logged_call.args[1] == "soils"


def test_apply_wepp_run_payload_grouped_updates_commit_failure_rolls_back_persisted_controller() -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(event_log)
    watershed = _AtomicWatershedDummy(event_log, fail_on_dump_call=1)
    wepp = _AtomicWeppDummy()
    wd = "/tmp/unit"
    soils_before = soils.snapshot_wepp_run_payload_updates()
    watershed_before = watershed.snapshot_wepp_run_payload_updates()

    with pytest.raises(RuntimeError, match="watershed commit failed"):
        apply_wepp_run_payload(
            wd,
            {
                "clip_soils": True,
                "clip_soils_depth": 210,
                "clip_hillslopes": True,
            },
            wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
            soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
            watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
            ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
        )

    assert soils.snapshot_wepp_run_payload_updates() == soils_before
    assert watershed.snapshot_wepp_run_payload_updates() == watershed_before
    assert len(soils.dump_states) == 2
    assert soils.dump_states[0]["_clip_soils"] is True
    assert soils.dump_states[1] == soils_before
    assert len(watershed.dump_states) == 2
    assert watershed.dump_states[1] == watershed_before
    assert soils.restore_calls == 1
    assert watershed.restore_calls == 1
    assert event_log[:2] == [("lock", "soils"), ("lock", "watershed")]
    assert event_log[-2:] == [("unlock", "watershed"), ("unlock", "soils")]


def test_apply_wepp_run_payload_grouped_updates_rollback_failure_logs_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(event_log, fail_on_dump_call=2)
    watershed = _AtomicWatershedDummy(event_log, fail_on_dump_call=1)
    wepp = _AtomicWeppDummy()
    exception_mock = Mock()
    monkeypatch.setattr(wepp_run_payload_module.logger, "exception", exception_mock)

    with pytest.raises(RuntimeError, match="watershed commit failed"):
        apply_wepp_run_payload(
            "/tmp/unit",
            {"clip_soils": True, "clip_hillslopes": True},
            wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
            soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
            watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
            ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
        )

    assert exception_mock.call_count == 1
    logged_call = exception_mock.call_args_list[0]
    assert "rollback failed" in str(logged_call.args[0])
    assert logged_call.args[1] == "soils"


def test_apply_wepp_run_payload_grouped_updates_unlock_failure_on_success_is_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(
        event_log,
        fail_on_unlock=ValueError("soils unlock failed"),
        fail_on_unlock_call=1,
    )
    watershed = _AtomicWatershedDummy(event_log)
    wepp = _AtomicWeppDummy()
    exception_mock = Mock()
    monkeypatch.setattr(wepp_run_payload_module.logger, "exception", exception_mock)

    with pytest.raises(ValueError, match="soils unlock failed"):
        apply_wepp_run_payload(
            "/tmp/unit",
            {"clip_soils": True, "clip_hillslopes": True},
            wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
            soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
            watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
            ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
        )

    assert len(soils.dump_states) == 1
    assert len(watershed.dump_states) == 1
    assert soils.post_finalize_calls == 0
    assert watershed.post_finalize_calls == 0
    assert exception_mock.call_count == 1
    logged_call = exception_mock.call_args_list[0]
    assert "unlock failed" in str(logged_call.args[0])
    assert logged_call.args[1] == "soils"


def test_apply_wepp_run_payload_grouped_updates_preserves_primary_error_when_rollback_and_unlock_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(
        event_log,
        fail_on_dump_call=2,
        fail_on_unlock=TypeError("soils unlock failed"),
        fail_on_unlock_call=1,
    )
    watershed = _AtomicWatershedDummy(
        event_log,
        fail_on_dump_call=1,
        fail_on_unlock=ValueError("watershed unlock failed"),
        fail_on_unlock_call=1,
    )
    wepp = _AtomicWeppDummy()
    exception_mock = Mock()
    monkeypatch.setattr(wepp_run_payload_module.logger, "exception", exception_mock)

    with pytest.raises(RuntimeError, match="watershed commit failed"):
        apply_wepp_run_payload(
            "/tmp/unit",
            {"clip_soils": True, "clip_hillslopes": True},
            wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
            soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
            watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
            ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
        )

    assert soils.post_finalize_calls == 0
    assert watershed.post_finalize_calls == 0
    assert exception_mock.call_count >= 3
    logged_labels_by_fragment = {(str(call.args[0]), call.args[1]) for call in exception_mock.call_args_list}
    assert any("rollback failed" in message and label == "soils" for message, label in logged_labels_by_fragment)
    assert any("unlock failed" in message and label == "watershed" for message, label in logged_labels_by_fragment)
    assert any("unlock failed" in message and label == "soils" for message, label in logged_labels_by_fragment)


def test_apply_wepp_run_payload_grouped_updates_requires_snapshot_under_lock() -> None:
    event_log: list[tuple[str, str]] = []
    soils = _AtomicSoilsDummy(event_log, fail_on_snapshot_without_lock=True)
    watershed = _AtomicWatershedDummy(event_log, fail_on_snapshot_without_lock=True)
    wepp = _AtomicWeppDummy()

    apply_wepp_run_payload(
        "/tmp/unit",
        {"clip_soils": True, "clip_hillslopes": True},
        wepp_cls=type("W", (), {"getInstance": staticmethod(lambda _wd: wepp)}),
        soils_cls=type("S", (), {"getInstance": staticmethod(lambda _wd: soils)}),
        watershed_cls=type("WS", (), {"getInstance": staticmethod(lambda _wd: watershed)}),
        ron_cls=type("R", (), {"getInstance": staticmethod(lambda _wd: _AtomicRonDummy())}),
    )

    assert soils.snapshot_locked_states
    assert watershed.snapshot_locked_states
    assert all(soils.snapshot_locked_states)
    assert all(watershed.snapshot_locked_states)


def test_soils_snapshot_stage_restore_roundtrip_uses_real_methods() -> None:
    soils = object.__new__(Soils)
    soils._clip_soils = False
    soils._clip_soils_depth = 100.0
    soils._clip_soils_minimum = False
    soils._clip_soils_minimum_depth = 0.0
    soils._rosetta_wc_fc_from_disturbed_bd_override = False
    soils._initial_sat = 0.75

    snapshot = soils.snapshot_wepp_run_payload_updates()
    staged = soils.stage_wepp_run_payload_updates(
        clip_soils=True,
        clip_soils_depth=200.0,
        clip_soils_minimum=True,
        clip_soils_minimum_depth=25.0,
        rosetta_wc_fc_from_disturbed_bd_override=True,
        initial_sat=0.2,
    )

    assert staged is True
    assert soils._clip_soils is True
    assert soils._clip_soils_depth == 200.0
    assert soils._clip_soils_minimum is True
    assert soils._clip_soils_minimum_depth == 25.0
    assert soils._rosetta_wc_fc_from_disturbed_bd_override is True
    assert soils._initial_sat == 0.2

    soils.restore_wepp_run_payload_updates(snapshot)
    assert soils.snapshot_wepp_run_payload_updates() == snapshot


def test_watershed_snapshot_stage_restore_roundtrip_uses_real_methods() -> None:
    watershed = object.__new__(Watershed)
    watershed._clip_hillslopes = False
    watershed._clip_hillslope_length = 300.0

    snapshot = watershed.snapshot_wepp_run_payload_updates()
    staged = watershed.stage_wepp_run_payload_updates(
        clip_hillslopes=True,
        clip_hillslope_length=180.0,
    )

    assert staged is True
    assert watershed._clip_hillslopes is True
    assert watershed._clip_hillslope_length == 180.0

    watershed.restore_wepp_run_payload_updates(snapshot)
    assert watershed.snapshot_wepp_run_payload_updates() == snapshot


def test_soils_finalize_grouped_updates_calls_dump() -> None:
    soils = object.__new__(Soils)
    calls = {"dump": 0}
    soils.dump = lambda: calls.__setitem__("dump", calls["dump"] + 1)

    soils.finalize_grouped_wepp_run_payload_updates()

    assert calls["dump"] == 1


def test_watershed_finalize_grouped_updates_calls_dump() -> None:
    watershed = object.__new__(Watershed)
    calls = {"dump": 0}
    watershed.dump = lambda: calls.__setitem__("dump", calls["dump"] + 1)

    watershed.finalize_grouped_wepp_run_payload_updates()

    assert calls["dump"] == 1


def test_soils_post_finalize_grouped_updates_runs_validate_then_post_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    soils = object.__new__(Soils)
    soils.wd = "/tmp/unit"
    call_order: list[str] = []

    monkeypatch.setattr(
        Soils,
        "getInstance",
        classmethod(lambda cls, wd: call_order.append(f"validate:{wd}") or soils),
    )
    monkeypatch.setattr(
        Soils,
        "_post_dump_and_unlock",
        classmethod(lambda cls, instance: call_order.append("post") or instance),
    )

    soils.post_finalize_grouped_wepp_run_payload_updates()

    assert call_order == ["validate:/tmp/unit", "post"]


def test_watershed_post_finalize_grouped_updates_runs_validate_then_post_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watershed = object.__new__(Watershed)
    watershed.wd = "/tmp/unit"
    call_order: list[str] = []

    monkeypatch.setattr(
        Watershed,
        "getInstance",
        classmethod(lambda cls, wd: call_order.append(f"validate:{wd}") or watershed),
    )
    monkeypatch.setattr(
        Watershed,
        "_post_dump_and_unlock",
        classmethod(lambda cls, instance: call_order.append("post") or instance),
    )

    watershed.post_finalize_grouped_wepp_run_payload_updates()

    assert call_order == ["validate:/tmp/unit", "post"]
