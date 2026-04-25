from __future__ import annotations

from contextlib import contextmanager

import pytest

from wepppy.nodb.batch_runner import BatchRunner


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


def test_apply_sbs_resource_update_noop_skips_lock_and_mutation() -> None:
    runner = object.__new__(BatchRunner)
    runner._sbs_map = "resources/existing.tif"
    runner._sbs_map_metadata = {"filename": "existing.tif"}

    lock = _LockRecorder()
    runner.locked = lock.locked

    runner.apply_sbs_resource_update()

    assert lock.calls == 0
    assert runner._sbs_map == "resources/existing.tif"
    assert runner._sbs_map_metadata == {"filename": "existing.tif"}


def test_apply_sbs_resource_update_uses_one_lock_and_applies_deepcopied_values() -> None:
    runner = object.__new__(BatchRunner)
    runner._sbs_map = None
    runner._sbs_map_metadata = None

    lock = _LockRecorder()
    runner.locked = lock.locked

    metadata = {
        "filename": "map.tif",
        "burn_class_counts": {"high": 1, "moderate": 2},
    }
    runner.apply_sbs_resource_update(sbs_map="resources/map.tif", metadata=metadata)

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert runner._sbs_map == "resources/map.tif"
    assert runner._sbs_map_metadata == metadata
    assert runner._sbs_map_metadata is not metadata

    metadata["filename"] = "mutated.tif"
    metadata["burn_class_counts"]["high"] = 99
    assert runner._sbs_map_metadata["filename"] == "map.tif"
    assert runner._sbs_map_metadata["burn_class_counts"]["high"] == 1


def test_apply_sbs_resource_update_sbs_map_only_preserves_existing_metadata() -> None:
    runner = object.__new__(BatchRunner)
    runner._sbs_map = "resources/old.tif"
    runner._sbs_map_metadata = {"filename": "old.tif", "resource_type": "sbs_map"}

    lock = _LockRecorder()
    runner.locked = lock.locked

    existing_metadata = runner._sbs_map_metadata
    runner.apply_sbs_resource_update(sbs_map="resources/new.tif")

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert runner._sbs_map == "resources/new.tif"
    assert runner._sbs_map_metadata == {"filename": "old.tif", "resource_type": "sbs_map"}
    assert runner._sbs_map_metadata is existing_metadata


def test_apply_sbs_resource_update_metadata_only_preserves_existing_sbs_map() -> None:
    runner = object.__new__(BatchRunner)
    runner._sbs_map = "resources/existing.tif"
    runner._sbs_map_metadata = {"filename": "existing.tif"}

    lock = _LockRecorder()
    runner.locked = lock.locked

    metadata = {"filename": "new.tif", "burn_class_counts": {"high": 2}}
    runner.apply_sbs_resource_update(metadata=metadata)

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert runner._sbs_map == "resources/existing.tif"
    assert runner._sbs_map_metadata == metadata
    assert runner._sbs_map_metadata is not metadata

    metadata["filename"] = "mutated.tif"
    metadata["burn_class_counts"]["high"] = 99
    assert runner._sbs_map_metadata["filename"] == "new.tif"
    assert runner._sbs_map_metadata["burn_class_counts"]["high"] == 2


def test_apply_sbs_resource_update_metadata_none_clears_metadata_and_preserves_map() -> None:
    runner = object.__new__(BatchRunner)
    runner._sbs_map = "resources/existing.tif"
    runner._sbs_map_metadata = {"filename": "existing.tif"}

    lock = _LockRecorder()
    runner.locked = lock.locked

    runner.apply_sbs_resource_update(metadata=None)

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert runner._sbs_map == "resources/existing.tif"
    assert runner._sbs_map_metadata is None
