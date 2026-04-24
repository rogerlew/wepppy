from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

import wepppy.nodb.core.landuse as landuse_module
from wepppy.nodb.core.landuse import Landuse, LanduseCustomMappingError

pytestmark = pytest.mark.unit


def test_resolve_effective_mapping_reference_prefers_custom_map(tmp_path: Path) -> None:
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(tmp_path)
    landuse._mapping = "disturbed"
    landuse._custom_mapping_relpath = "landuse/custom-map.json"

    map_path = tmp_path / "landuse" / "custom-map.json"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text("{}", encoding="utf-8")

    resolved = landuse._resolve_effective_mapping_reference(landuse.mapping)
    assert resolved == str(map_path)


def test_resolve_effective_mapping_reference_rejects_missing_custom_map(tmp_path: Path) -> None:
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(tmp_path)
    landuse._mapping = "disturbed"
    landuse._custom_mapping_relpath = "landuse/missing-map.json"

    with pytest.raises(LanduseCustomMappingError) as exc_info:
        landuse._resolve_effective_mapping_reference(landuse.mapping)

    assert exc_info.value.code == "LANDUSE_CUSTOM_MAP_MISSING"
    assert exc_info.value.details["custom_mapping_relpath"] == "landuse/missing-map.json"


def test_resolve_effective_mapping_reference_clears_missing_system_override(tmp_path: Path) -> None:
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(tmp_path)
    landuse._mapping = "disturbed"
    landuse._custom_mapping_relpath = "landuse/landuse_user_defined_mapping.json"

    resolved = landuse._resolve_effective_mapping_reference(landuse.mapping)

    assert resolved == "disturbed"
    assert landuse.custom_mapping_relpath is None


def test_resolve_effective_mapping_reference_clears_system_override_legacy_relpath_format(
    tmp_path: Path,
) -> None:
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(tmp_path)
    landuse._mapping = "disturbed"
    landuse._custom_mapping_relpath = r"./landuse\landuse_user_defined_mapping.json"

    resolved = landuse._resolve_effective_mapping_reference(landuse.mapping)

    assert resolved == "disturbed"
    assert landuse.custom_mapping_relpath is None


def test_clear_stale_system_custom_mapping_reference_does_not_acquire_lock_when_unlocked(
    tmp_path: Path,
) -> None:
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(tmp_path)
    landuse._custom_mapping_relpath = "landuse/landuse_user_defined_mapping.json"

    lock_calls = {"count": 0}

    @contextmanager
    def fake_locked():
        lock_calls["count"] += 1
        raise AssertionError("locked() should not be called from unlocked stale-map recovery")
        yield

    landuse.locked = fake_locked
    landuse.islocked = lambda: False

    cleared = landuse._clear_stale_system_custom_mapping_reference(
        "landuse/landuse_user_defined_mapping.json"
    )

    assert cleared is True
    assert landuse.custom_mapping_relpath is None
    assert lock_calls["count"] == 0


def test_get_mapping_dict_wraps_invalid_custom_map(tmp_path: Path) -> None:
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(tmp_path)
    landuse._mapping = "disturbed"
    landuse._custom_mapping_relpath = "landuse/custom-map.json"

    map_path = tmp_path / "landuse" / "custom-map.json"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text("{bad json", encoding="utf-8")

    with pytest.raises(LanduseCustomMappingError) as exc_info:
        landuse.get_mapping_dict()

    assert exc_info.value.code == "management_map_invalid_json"
    assert exc_info.value.details["custom_mapping_relpath"] == "landuse/custom-map.json"


def test_single_selection_setter_uses_effective_mapping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(tmp_path)
    landuse._mapping = "disturbed"
    landuse._custom_mapping_relpath = "landuse/custom-map.json"

    map_path = tmp_path / "landuse" / "custom-map.json"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text("{}", encoding="utf-8")

    captured: dict[str, str | None] = {"map": None}

    def fake_get_management_summary(dom: int, _map: str | None = None):
        captured["map"] = _map
        return {"dom": dom}

    monkeypatch.setattr(landuse_module, "get_management_summary", fake_get_management_summary)

    Landuse.single_selection.fset.__wrapped__(landuse, 21)  # type: ignore[attr-defined]
    assert captured["map"] == str(map_path)


def test_mofe_buffer_selection_setter_uses_effective_mapping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(tmp_path)
    landuse._mapping = "disturbed"
    landuse._custom_mapping_relpath = "landuse/custom-map.json"

    map_path = tmp_path / "landuse" / "custom-map.json"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text("{}", encoding="utf-8")

    captured: dict[str, str | None] = {"map": None}

    def fake_get_management_summary(dom: int, _map: str | None = None):
        captured["map"] = _map
        return {"dom": dom}

    monkeypatch.setattr(landuse_module, "get_management_summary", fake_get_management_summary)

    Landuse.mofe_buffer_selection.fset.__wrapped__(landuse, 22)  # type: ignore[attr-defined]
    assert captured["map"] == str(map_path)


def test_build_managements_rebuilds_cached_management_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummySummary:
        def __init__(self, marker: str) -> None:
            self.marker = marker
            self.area = 0.0
            self.pct_coverage = 0.0

    class DummyWatershed:
        @staticmethod
        def hillslope_area(_topaz_id: str) -> float:
            return 10.0

    class DummyRon:
        cellsize = 1.0

    landuse = Landuse.__new__(Landuse)
    landuse.wd = "/tmp/run"
    landuse._mapping = "disturbed"
    landuse._custom_mapping_relpath = None
    landuse.domlc_d = {"101": "21"}
    landuse.managements = {"21": DummySummary("stale")}
    landuse.dump_landuse_parquet = lambda: None
    landuse.trigger = lambda *_args, **_kwargs: None

    @contextmanager
    def fake_locked():
        yield

    landuse.locked = fake_locked

    monkeypatch.setattr(Landuse, "watershed_instance", property(lambda self: DummyWatershed()))
    monkeypatch.setattr(Landuse, "ron_instance", property(lambda self: DummyRon()))
    monkeypatch.setattr(Landuse, "multi_ofe", property(lambda self: False))
    monkeypatch.setattr(
        landuse_module,
        "get_management_summary",
        lambda dom, _map=None: DummySummary("fresh"),
    )

    landuse.build_managements(_map="disturbed")
    assert landuse.managements["21"].marker == "fresh"


def test_build_managements_relabels_stale_custom_mapping_description(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class DummySummary:
        def __init__(self, marker: str, *, man_fn: str, desc: str) -> None:
            self.marker = marker
            self.man_fn = man_fn
            self.desc = desc
            self.area = 0.0
            self.pct_coverage = 0.0

    class DummyWatershed:
        @staticmethod
        def hillslope_area(_topaz_id: str) -> float:
            return 10.0

    class DummyRon:
        cellsize = 1.0

    custom_map_path = str(tmp_path / "landuse" / "landuse_user_defined_mapping.json")
    custom_map = {
        "43": {
            "Key": 43,
            "Description": "Mixed Forest",
            "DisturbedClass": "forest",
            "ManagementFile": "UnDisturbed/Moderate_Severity_Fire.man",
            "ManagementDir": "/maps",
        }
    }
    base_map = {
        "43": {
            "Key": 43,
            "Description": "Mixed Forest",
            "DisturbedClass": "forest",
            "ManagementFile": "UnDisturbed/Old_Forest.man",
            "ManagementDir": "/maps",
        }
    }

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(tmp_path)
    landuse._mapping = "disturbed"
    landuse._custom_mapping_relpath = "landuse/landuse_user_defined_mapping.json"
    landuse.domlc_d = {"101": "43"}
    landuse.managements = {}
    landuse.dump_landuse_parquet = lambda: None
    landuse.trigger = lambda *_args, **_kwargs: None

    @contextmanager
    def fake_locked():
        yield

    landuse.locked = fake_locked

    monkeypatch.setattr(Landuse, "watershed_instance", property(lambda self: DummyWatershed()))
    monkeypatch.setattr(Landuse, "ron_instance", property(lambda self: DummyRon()))
    monkeypatch.setattr(Landuse, "multi_ofe", property(lambda self: False))

    def fake_load_map(reference):
        token = str(reference)
        if token == custom_map_path:
            return custom_map
        if token == "disturbed":
            return base_map
        raise AssertionError(f"Unexpected map reference: {reference}")

    monkeypatch.setattr(landuse_module, "load_map", fake_load_map)
    monkeypatch.setattr(
        landuse_module,
        "get_management_summary",
        lambda dom, _map=None: DummySummary(
            "fresh",
            man_fn="UnDisturbed/Moderate_Severity_Fire.man",
            desc="Mixed Forest",
        ),
    )

    landuse.build_managements(_map=custom_map_path)

    assert landuse.managements["43"].desc == "Moderate Severity Fire"
