from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from wepppy.weppcloud._scripts import compile_dot_logs as script

pytestmark = pytest.mark.unit


class RonStub:
    def __init__(self, config_stem: str, has_sbs: bool) -> None:
        self.config_stem = config_stem
        self.has_sbs = has_sbs

    @staticmethod
    def getInstance(_wd: str) -> "RonStub":
        return RonStub("disturbed", True)


class WatershedStub:
    def __init__(self, centroid: tuple[float, float]) -> None:
        self.centroid = centroid

    @staticmethod
    def getInstance(_wd: str) -> "WatershedStub":
        return WatershedStub((-116.1, 43.6))


def _write_access_log(path: Path, timestamps: list[datetime]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for stamp in timestamps:
            handle.write(f"user@example.com,127.0.0.1,{stamp}\n")


def _read_access_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_compile_dot_logs_builds_outputs_and_touches_ttl(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "runs"
    prefix_dir = run_root / "ab"
    prefix_dir.mkdir(parents=True)
    runid = "alpha-bravo"
    run_dir = prefix_dir / runid
    run_dir.mkdir(parents=True)

    (run_dir / "wepp" / "runs").mkdir(parents=True)
    (run_dir / "wepp" / "runs" / "a.slp").write_text("slp", encoding="utf-8")
    (run_dir / "wepp" / "runs" / "b.slp").write_text("slp", encoding="utf-8")
    (run_dir / "ash").mkdir(parents=True)
    (run_dir / "ash" / "fooash.csv").write_text("ash", encoding="utf-8")

    log_path = prefix_dir / f".{runid}"
    timestamps = [
        datetime(2025, 1, 1, 8, 0, 0),
        datetime(2025, 1, 2, 9, 30, 0),
    ]
    _write_access_log(log_path, timestamps)

    monkeypatch.setattr(script, "Ron", RonStub)
    monkeypatch.setattr(script, "Watershed", WatershedStub)

    ttl_calls: list[tuple[str, datetime, str]] = []

    def fake_touch_ttl(wd: str, accessed_at: datetime, touched_by: str = "access_log") -> None:
        ttl_calls.append((wd, accessed_at, touched_by))

    def fake_read_ttl_state(_wd: str) -> dict[str, str]:
        return {"delete_state": "active"}

    ttl_module = __import__("wepppy.weppcloud.utils.run_ttl", fromlist=["touch_ttl"])
    monkeypatch.setattr(ttl_module, "touch_ttl", fake_touch_ttl)
    monkeypatch.setattr(ttl_module, "read_ttl_state", fake_read_ttl_state)
    monkeypatch.setattr(ttl_module, "DELETE_STATE_ACTIVE", "active")

    access_csv = tmp_path / "access.csv"
    run_locations = tmp_path / "runid-locations.json"

    legacy_root = tmp_path / "legacy"
    result = script.compile_dot_logs(
        access_log_path=str(access_csv),
        run_locations_path=str(run_locations),
        run_roots=[str(run_root)],
        legacy_roots=[str(legacy_root)],
    )

    assert result["logs"] == 1
    assert result["runs"] == 1
    assert access_csv.exists()
    assert run_locations.exists()

    rows = _read_access_csv(access_csv)
    assert rows[0]["runid"] == runid
    assert rows[0]["config"] == "disturbed"
    assert rows[0]["hillslopes"] == "2"
    assert rows[0]["ash_hillslopes"] == "1"

    payload = json.loads(run_locations.read_text(encoding="utf-8"))
    assert len(payload) == 1
    record = payload[0]
    assert record["runid"] == runid
    assert record["coordinates"] == [-116.1, 43.6]
    assert record["access_count"] == 2
    assert record["last_accessed"] == timestamps[-1].isoformat()

    assert ttl_calls
    assert ttl_calls[0][0] == str(run_dir)
    assert ttl_calls[0][1] == timestamps[-1]


def test_compile_dot_logs_filters_deleted_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "runs"
    prefix_dir = run_root / "cd"
    prefix_dir.mkdir(parents=True)
    runid = "charlie-delta"
    run_dir = prefix_dir / runid
    run_dir.mkdir(parents=True)

    log_path = prefix_dir / f".{runid}"
    timestamps = [datetime(2025, 2, 1, 12, 0, 0)]
    _write_access_log(log_path, timestamps)

    monkeypatch.setattr(script, "Ron", RonStub)
    monkeypatch.setattr(script, "Watershed", WatershedStub)

    ttl_module = __import__("wepppy.weppcloud.utils.run_ttl", fromlist=["read_ttl_state"])
    monkeypatch.setattr(ttl_module, "touch_ttl", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ttl_module, "read_ttl_state", lambda _wd: {"delete_state": "queued"})
    monkeypatch.setattr(ttl_module, "DELETE_STATE_ACTIVE", "active")

    access_csv = tmp_path / "access.csv"
    run_locations = tmp_path / "runid-locations.json"

    legacy_root = tmp_path / "legacy"
    result = script.compile_dot_logs(
        access_log_path=str(access_csv),
        run_locations_path=str(run_locations),
        run_roots=[str(run_root)],
        legacy_roots=[str(legacy_root)],
    )

    assert result["runs"] == 1
    payload = json.loads(run_locations.read_text(encoding="utf-8"))
    assert payload == []
