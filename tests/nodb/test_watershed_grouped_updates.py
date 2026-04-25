from __future__ import annotations

from contextlib import contextmanager

import pytest

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
        def _scope():
            self.enters += 1
            try:
                yield
            finally:
                self.exits += 1

        return _scope()


def test_apply_build_subcatchment_updates_noop_skips_lock_and_mutation() -> None:
    watershed = object.__new__(Watershed)
    watershed._clip_hillslopes = True
    watershed._walk_flowpaths = True
    watershed._clip_hillslope_length = 450.0
    watershed._mofe_target_length = 50.0
    watershed._mofe_buffer = True
    watershed._mofe_buffer_length = 15.0
    watershed._mofe_max_ofes = 7
    watershed._bieger2015_widths = True

    lock = _LockRecorder()
    watershed.locked = lock.locked

    watershed.apply_build_subcatchment_updates()

    assert lock.calls == 0
    assert watershed._clip_hillslopes is True
    assert watershed._walk_flowpaths is True
    assert watershed._clip_hillslope_length == 450.0
    assert watershed._mofe_target_length == 50.0
    assert watershed._mofe_buffer is True
    assert watershed._mofe_buffer_length == 15.0
    assert watershed._mofe_max_ofes == 7
    assert watershed._bieger2015_widths is True


def test_apply_build_subcatchment_updates_uses_one_lock_and_applies_falsey_values() -> None:
    watershed = object.__new__(Watershed)
    watershed._clip_hillslopes = True
    watershed._walk_flowpaths = True
    watershed._clip_hillslope_length = 450.0
    watershed._mofe_target_length = 50.0
    watershed._mofe_buffer = True
    watershed._mofe_buffer_length = 15.0
    watershed._mofe_max_ofes = 7
    watershed._bieger2015_widths = True

    lock = _LockRecorder()
    watershed.locked = lock.locked

    watershed.apply_build_subcatchment_updates(
        clip_hillslopes=False,
        walk_flowpaths=False,
        clip_hillslope_length=0.0,
        mofe_target_length=0.0,
        mofe_buffer=False,
        mofe_buffer_length=0.0,
        mofe_max_ofes=42,
        bieger2015_widths=False,
    )

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert watershed._clip_hillslopes is False
    assert watershed._walk_flowpaths is False
    assert watershed._clip_hillslope_length == 0.0
    assert watershed._mofe_target_length == 0.0
    assert watershed._mofe_buffer is False
    assert watershed._mofe_buffer_length == 0.0
    assert watershed._mofe_max_ofes == 19
    assert watershed._bieger2015_widths is False


def test_apply_build_subcatchment_updates_clamps_mofe_max_ofes_floor_to_one() -> None:
    watershed = object.__new__(Watershed)
    watershed._mofe_max_ofes = 7

    lock = _LockRecorder()
    watershed.locked = lock.locked

    watershed.apply_build_subcatchment_updates(mofe_max_ofes=0)

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert watershed._mofe_max_ofes == 1
