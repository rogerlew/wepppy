from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

import pytest

import wepppy.soils.ssurgo.ssurgo as ssurgo_module
from wepppy.soils.ssurgo import SurgoSoilCollection, surgo_cache_metadata_path

pytestmark = pytest.mark.unit


def test_surgo_collection_defaults_to_in_memory_sqlite_cache() -> None:
    collection = SurgoSoilCollection([])
    try:
        assert collection._db_path is None
        row = collection.conn.execute("PRAGMA database_list").fetchone()
        assert row["file"] == ""
    finally:
        collection._disconnect()


def test_surgo_collection_uses_explicit_file_backed_cache(tmp_path: Path) -> None:
    cache_path = tmp_path / "ssurgo_tabular_cache.sqlite"

    collection = SurgoSoilCollection([], cache_db_path=str(cache_path))
    try:
        assert collection._db_path == str(cache_path)
        assert cache_path.is_file()
    finally:
        collection._disconnect()

    metadata_path = Path(surgo_cache_metadata_path(str(cache_path)))
    metadata = metadata_path.read_text(encoding="utf-8")
    assert metadata_path.is_file()
    assert "# SSURGO SQLite Cache Metadata" in metadata
    assert "| Source service | Soil Data Access Tabular API |" in metadata
    assert "| Cache file | `ssurgo_tabular_cache.sqlite` |" in metadata
    assert str(tmp_path) not in metadata

    with sqlite3.connect(cache_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    assert "component" in tables
    assert "chorizon" in tables


def test_log_invalid_soils_handles_failed_worker_without_soil_object(
    tmp_path: Path,
) -> None:
    class _InvalidSoilStub:
        def __init__(self) -> None:
            self.calls: list[tuple[str, bool, bool]] = []

        def write_log(
            self,
            wd: str,
            overwrite: bool = True,
            *,
            db_build: bool = False,
        ) -> None:
            self.calls.append((wd, overwrite, db_build))
            Path(wd, "456.log").write_text("invalid soil details", encoding="utf-8")

    invalid_soil = _InvalidSoilStub()
    collection = SurgoSoilCollection([])
    try:
        collection.invalidSoils = {
            123: None,
            456: invalid_soil,
        }

        collection.logInvalidSoils(wd=str(tmp_path))
    finally:
        collection._disconnect()

    failed_worker_log = tmp_path / "123.log"
    assert failed_worker_log.is_file()
    assert "failed for mukey 123 before a soil object was produced" in (
        failed_worker_log.read_text(encoding="utf-8")
    )
    assert (tmp_path / "456.log").read_text(encoding="utf-8") == "invalid soil details"
    assert invalid_soil.calls == [(str(tmp_path), True, False)]


def test_file_backed_cache_reuses_persisted_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_path = tmp_path / "ssurgo_tabular_cache.sqlite"
    calls: Counter[str] = Counter()

    def fetch_components(keys: set[int]) -> list[tuple[object, ...]]:
        calls["component"] += 1
        assert keys == {123}
        return [
            (
                123,
                456,
                "Cache Test",
                100.0,
                0.1,
                0.0,
                0.0,
                "Cache Test Mapunit",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            )
        ]

    def fetch_chorizon(keys: set[int]) -> list[tuple[object, ...]]:
        calls["chorizon"] += 1
        assert keys == {456}
        return [
            (
                456,
                789,
                "A",
                10.0,
                0.0,
                10.0,
                1.2,
                5.0,
                50.0,
                20.0,
                2.0,
                10.0,
                0.1,
                0.0,
                0.0,
                "A",
                90.0,
                20.0,
                10.0,
                15.0,
                None,
            )
        ]

    def fetch_corestrictions(keys: set[int]) -> list[tuple[object, ...]]:
        calls["corestrictions"] += 1
        assert keys == {456}
        return [(456, "N/A")]

    def fetch_chfrags(keys: set[int]) -> list[tuple[object, ...]]:
        calls["chfrags"] += 1
        assert keys == {789}
        return [(789, 0.0)]

    def fetch_chtexturegrp(keys: set[int]) -> list[tuple[object, ...]]:
        calls["chtexturegrp"] += 1
        assert keys == {789}
        return [(789, "loam")]

    monkeypatch.setattr(ssurgo_module, "_fetch_components", fetch_components)
    monkeypatch.setattr(ssurgo_module, "_fetch_chorizon", fetch_chorizon)
    monkeypatch.setattr(ssurgo_module, "_fetch_corestrictions", fetch_corestrictions)
    monkeypatch.setattr(ssurgo_module, "_fetch_chfrags", fetch_chfrags)
    monkeypatch.setattr(ssurgo_module, "_fetch_chtexturegrp", fetch_chtexturegrp)

    collection = SurgoSoilCollection([123], cache_db_path=str(cache_path))
    try:
        assert collection.get_components(123)[0]["cokey"] == 456
        assert collection.get_layers(456)[0]["chkey"] == 789
    finally:
        collection._disconnect()

    assert dict(calls) == {
        "component": 1,
        "chorizon": 1,
        "corestrictions": 1,
        "chfrags": 1,
        "chtexturegrp": 1,
    }
    metadata = Path(surgo_cache_metadata_path(str(cache_path))).read_text(
        encoding="utf-8"
    )
    assert "| Requested map unit keys | 1 |" in metadata
    assert "| `component` | 1 |" in metadata
    assert "| `chorizon` | 1 |" in metadata

    cached_collection = SurgoSoilCollection([123], cache_db_path=str(cache_path))
    try:
        assert cached_collection.get_components(123)[0]["compname"] == "Cache Test"
        assert cached_collection.get_texture(789) == "loam"
    finally:
        cached_collection._disconnect()

    assert dict(calls) == {
        "component": 1,
        "chorizon": 1,
        "corestrictions": 1,
        "chfrags": 1,
        "chtexturegrp": 1,
    }
