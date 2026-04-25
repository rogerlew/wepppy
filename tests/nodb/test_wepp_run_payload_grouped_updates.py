from __future__ import annotations

from contextlib import contextmanager

import pytest

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
