from __future__ import annotations

from contextlib import contextmanager

import pytest

import wepppy.nodb.core.landuse as landuse_module
from wepppy.nodb.core.landuse import Landuse, LanduseMode
from wepppy.nodb.mods.disturbed import Disturbed


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


def test_landuse_apply_set_landuse_mode_updates_noop_skips_lock_and_mutation() -> None:
    landuse = object.__new__(Landuse)
    landuse._mode = LanduseMode.Gridded
    landuse._single_selection = "101"
    landuse._single_man = {"dom": "101"}

    lock = _LockRecorder()
    landuse.locked = lock.locked

    landuse.apply_set_landuse_mode_updates(mode=None, single_selection=None)

    assert lock.calls == 0
    assert landuse._mode == LanduseMode.Gridded
    assert landuse._single_selection == "101"
    assert landuse._single_man == {"dom": "101"}


def test_landuse_apply_set_landuse_mode_updates_uses_one_lock_and_applies_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    landuse = object.__new__(Landuse)
    landuse._mode = LanduseMode.Gridded
    landuse._mapping = "disturbed"
    landuse._custom_mapping_relpath = None
    landuse._single_selection = "101"
    landuse._single_man = {"dom": "101"}
    landuse._resolve_effective_mapping_reference = lambda mapping_reference=None: "effective-map"

    captured: dict[str, object] = {}

    def fake_get_management_summary(selection, mapping_reference=None):
        captured["selection"] = selection
        captured["mapping_reference"] = mapping_reference
        return {"dom": selection, "map": mapping_reference}

    monkeypatch.setattr(landuse_module, "get_management_summary", fake_get_management_summary)

    lock = _LockRecorder()
    landuse.locked = lock.locked

    landuse.apply_set_landuse_mode_updates(
        mode=int(LanduseMode.UserDefined),
        single_selection="forest",
    )

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert landuse._mode == LanduseMode.UserDefined
    assert landuse._single_selection == "forest"
    assert landuse._single_man == {"dom": "forest", "map": "effective-map"}
    assert captured == {"selection": "forest", "mapping_reference": "effective-map"}


def test_landuse_apply_set_landuse_mode_updates_mode_only_preserves_single_selection_state() -> None:
    landuse = object.__new__(Landuse)
    landuse._mode = LanduseMode.Gridded
    landuse._single_selection = "101"
    landuse._single_man = {"dom": "101"}

    lock = _LockRecorder()
    landuse.locked = lock.locked

    landuse.apply_set_landuse_mode_updates(
        mode=int(LanduseMode.UserDefined),
        single_selection=None,
    )

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert landuse._mode == LanduseMode.UserDefined
    assert landuse._single_selection == "101"
    assert landuse._single_man == {"dom": "101"}


def test_landuse_apply_set_landuse_mode_updates_selection_only_preserves_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    landuse = object.__new__(Landuse)
    landuse._mode = LanduseMode.Gridded
    landuse._mapping = "disturbed"
    landuse._custom_mapping_relpath = None
    landuse._single_selection = "101"
    landuse._single_man = {"dom": "101"}
    landuse._resolve_effective_mapping_reference = lambda mapping_reference=None: "effective-map"

    captured: dict[str, object] = {}

    def fake_get_management_summary(selection, mapping_reference=None):
        captured["selection"] = selection
        captured["mapping_reference"] = mapping_reference
        return {"dom": selection, "map": mapping_reference}

    monkeypatch.setattr(landuse_module, "get_management_summary", fake_get_management_summary)

    lock = _LockRecorder()
    landuse.locked = lock.locked

    landuse.apply_set_landuse_mode_updates(
        mode=None,
        single_selection="forest",
    )

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert landuse._mode == LanduseMode.Gridded
    assert landuse._single_selection == "forest"
    assert landuse._single_man == {"dom": "forest", "map": "effective-map"}
    assert captured == {"selection": "forest", "mapping_reference": "effective-map"}


def test_landuse_apply_set_landuse_mode_updates_preserves_mode_validation_contract() -> None:
    landuse = object.__new__(Landuse)
    landuse._mode = LanduseMode.Gridded
    landuse._single_selection = "101"
    landuse._single_man = {"dom": "101"}

    lock = _LockRecorder()
    landuse.locked = lock.locked

    with pytest.raises(ValueError, match="most be LanduseMode or int"):
        landuse.apply_set_landuse_mode_updates(mode="bad", single_selection=None)

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1


def test_disturbed_apply_build_landuse_updates_noop_skips_lock_and_mutation() -> None:
    disturbed = object.__new__(Disturbed)
    disturbed._burn_shrubs = True
    disturbed._burn_grass = False

    lock = _LockRecorder()
    disturbed.locked = lock.locked

    disturbed.apply_build_landuse_updates()

    assert lock.calls == 0
    assert disturbed._burn_shrubs is True
    assert disturbed._burn_grass is False


def test_disturbed_apply_build_landuse_updates_uses_one_lock_and_applies_values() -> None:
    disturbed = object.__new__(Disturbed)
    disturbed._burn_shrubs = True
    disturbed._burn_grass = False

    lock = _LockRecorder()
    disturbed.locked = lock.locked

    disturbed.apply_build_landuse_updates(burn_shrubs=0, burn_grass="yes")

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert disturbed._burn_shrubs is False
    assert disturbed._burn_grass is True


def test_disturbed_apply_build_landuse_updates_partial_preserves_untouched_field() -> None:
    disturbed = object.__new__(Disturbed)
    disturbed._burn_shrubs = True
    disturbed._burn_grass = False

    lock = _LockRecorder()
    disturbed.locked = lock.locked

    disturbed.apply_build_landuse_updates(burn_shrubs=0)

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert disturbed._burn_shrubs is False
    assert disturbed._burn_grass is False
