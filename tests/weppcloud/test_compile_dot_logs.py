from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from rq.timeouts import JobTimeoutException

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


def _write_parquet_rows(path: Path, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({"topaz_id": list(range(count))}), path)


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

    _write_parquet_rows(run_dir / "watershed" / "hillslopes.parquet", 2)
    _write_parquet_rows(run_dir / "ash" / "post" / "hillslope_annuals.parquet", 1)
    (run_dir / "wepp" / "runs").mkdir(parents=True)
    (run_dir / "wepp" / "runs" / "ignored.slp").write_text("slp", encoding="utf-8")
    (run_dir / "ash").mkdir(parents=True, exist_ok=True)
    (run_dir / "ash" / "ignoredash.csv").write_text("ash", encoding="utf-8")

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

    run_count_rows = _read_access_csv(tmp_path / "run_counts.csv")
    assert run_count_rows == [{
        "runid": runid,
        "hillslopes": "2",
        "ash_hillslopes": "1",
        "year": "2025",
        "config": "disturbed",
    }]
    counters = json.loads((tmp_path / "runs_counter.json").read_text(encoding="utf-8"))
    assert counters["projects"] == 1
    assert counters["hillruns"] == 2
    assert counters["ash_hillruns"] == 1

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
    _write_parquet_rows(run_dir / "watershed" / "hillslopes.parquet", 1)

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


def test_missing_artifact_does_not_remove_location_or_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "runs"
    prefix_dir = run_root / "ef"
    prefix_dir.mkdir(parents=True)

    for runid, rows in (("echo-foxtrot", 3), ("empty-count", None)):
        run_dir = prefix_dir / runid
        run_dir.mkdir()
        if rows is not None:
            _write_parquet_rows(run_dir / "watershed" / "hillslopes.parquet", rows)
        _write_access_log(prefix_dir / f".{runid}", [datetime(2025, 3, 1, 12, 0, 0)])

    monkeypatch.setattr(script, "Ron", RonStub)
    monkeypatch.setattr(script, "Watershed", WatershedStub)
    ttl_module = __import__("wepppy.weppcloud.utils.run_ttl", fromlist=["read_ttl_state"])
    monkeypatch.setattr(ttl_module, "touch_ttl", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ttl_module, "read_ttl_state", lambda _wd: {"delete_state": "active"})
    monkeypatch.setattr(ttl_module, "DELETE_STATE_ACTIVE", "active")

    access_csv = tmp_path / "access.csv"
    run_locations = tmp_path / "runid-locations.json"
    script.compile_dot_logs(
        access_log_path=str(access_csv),
        run_locations_path=str(run_locations),
        run_roots=[str(run_root)],
        legacy_roots=[str(tmp_path / "legacy")],
    )

    locations = json.loads(run_locations.read_text(encoding="utf-8"))
    by_runid = {entry["runid"]: entry for entry in locations}
    assert by_runid["empty-count"]["hillslopes"] == 0
    counters = json.loads((tmp_path / "runs_counter.json").read_text(encoding="utf-8"))
    assert counters["projects"] == 2


def test_systemic_parquet_failure_preserves_existing_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "runs"
    prefix_dir = run_root / "gh"
    prefix_dir.mkdir(parents=True)
    runid = "golf-hotel"
    run_dir = prefix_dir / runid
    run_dir.mkdir()
    bad_parquet = run_dir / "watershed" / "hillslopes.parquet"
    bad_parquet.parent.mkdir()
    bad_parquet.write_text("not parquet", encoding="utf-8")
    _write_access_log(prefix_dir / f".{runid}", [datetime(2025, 4, 1, 12, 0, 0)])

    monkeypatch.setattr(script, "Ron", RonStub)
    monkeypatch.setattr(script, "Watershed", WatershedStub)
    outputs = {
        tmp_path / "access.csv": "old access",
        tmp_path / "runid-locations.json": "old locations",
        tmp_path / "runs_counter.json": "old counters",
        tmp_path / "run_counts.csv": "old counts",
    }
    for path, value in outputs.items():
        path.write_text(value, encoding="utf-8")

    with pytest.raises(RuntimeError, match="no watershed hillslopes parquet was readable"):
        script.compile_dot_logs(
            access_log_path=str(tmp_path / "access.csv"),
            run_locations_path=str(tmp_path / "runid-locations.json"),
            run_roots=[str(run_root)],
            legacy_roots=[str(tmp_path / "legacy")],
        )

    for path, value in outputs.items():
        assert path.read_text(encoding="utf-8") == value


def test_zero_discovery_preserves_existing_outputs(tmp_path: Path) -> None:
    access_csv = tmp_path / "access.csv"
    access_csv.write_text("last good", encoding="utf-8")

    with pytest.raises(RuntimeError, match="zero-log discovery"):
        script.compile_dot_logs(
            access_log_path=str(access_csv),
            run_locations_path=str(tmp_path / "runid-locations.json"),
            run_roots=[str(tmp_path / "missing-runs")],
            legacy_roots=[str(tmp_path / "missing-legacy")],
        )

    assert access_csv.read_text(encoding="utf-8") == "last good"


def test_ash_systemic_error_threshold() -> None:
    health = script.ArtifactHealth(watershed_readable=40, ash_errors=10)

    with pytest.raises(RuntimeError, match="systemic ash parquet errors"):
        script._validate_artifact_health(40, health)


def test_initial_empty_publication(tmp_path: Path) -> None:
    result = script.compile_dot_logs(
        access_log_path=str(tmp_path / "access.csv"),
        run_locations_path=str(tmp_path / "runid-locations.json"),
        run_roots=[str(tmp_path / "missing-runs")],
        legacy_roots=[str(tmp_path / "missing-legacy")],
    )

    assert result == {"logs": 0, "access_rows": 0, "run_locations": 0, "runs": 0}
    assert (tmp_path / "access.csv").exists()
    assert json.loads((tmp_path / "runid-locations.json").read_text(encoding="utf-8")) == []


def test_isolated_corrupt_artifact_warns_and_publishes_zero(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "runs"
    prefix_dir = run_root / "ij"
    prefix_dir.mkdir(parents=True)
    for runid, corrupt in (("india-juliet", False), ("invalid-parquet", True)):
        run_dir = prefix_dir / runid
        run_dir.mkdir()
        parquet_path = run_dir / "watershed" / "hillslopes.parquet"
        if corrupt:
            parquet_path.parent.mkdir()
            parquet_path.write_text("invalid", encoding="utf-8")
        else:
            _write_parquet_rows(parquet_path, 2)
        _write_access_log(prefix_dir / f".{runid}", [datetime(2025, 5, 1, 12, 0, 0)])

    monkeypatch.setattr(script, "Ron", RonStub)
    monkeypatch.setattr(script, "Watershed", WatershedStub)
    ttl_module = __import__("wepppy.weppcloud.utils.run_ttl", fromlist=["read_ttl_state"])
    monkeypatch.setattr(ttl_module, "touch_ttl", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ttl_module, "read_ttl_state", lambda _wd: {"delete_state": "active"})
    monkeypatch.setattr(ttl_module, "DELETE_STATE_ACTIVE", "active")
    logger = logging.getLogger("test.compile_dot_logs.corrupt")

    with caplog.at_level(logging.WARNING, logger=logger.name):
        script.compile_dot_logs(
            access_log_path=str(tmp_path / "access.csv"),
            run_locations_path=str(tmp_path / "runid-locations.json"),
            run_roots=[str(run_root)],
            legacy_roots=[str(tmp_path / "legacy")],
            logger=logger,
        )

    rows = {row["runid"]: row for row in _read_access_csv(tmp_path / "access.csv")}
    assert rows["invalid-parquet"]["hillslopes"] == "0"
    assert "failed to read watershed parquet for invalid-parquet" in caplog.text


def test_centroid_absence_does_not_remove_project_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class NoCentroidWatershedStub:
        centroid = None

        @staticmethod
        def getInstance(_wd: str) -> "NoCentroidWatershedStub":
            return NoCentroidWatershedStub()

    run_root = tmp_path / "runs"
    prefix_dir = run_root / "kl"
    prefix_dir.mkdir(parents=True)
    runid = "kilo-lima"
    run_dir = prefix_dir / runid
    run_dir.mkdir()
    _write_parquet_rows(run_dir / "watershed" / "hillslopes.parquet", 2)
    _write_access_log(prefix_dir / f".{runid}", [datetime(2025, 6, 1, 12, 0, 0)])
    monkeypatch.setattr(script, "Ron", RonStub)
    monkeypatch.setattr(script, "Watershed", NoCentroidWatershedStub)
    ttl_module = __import__("wepppy.weppcloud.utils.run_ttl", fromlist=["read_ttl_state"])
    monkeypatch.setattr(ttl_module, "touch_ttl", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ttl_module, "read_ttl_state", lambda _wd: {"delete_state": "active"})
    monkeypatch.setattr(ttl_module, "DELETE_STATE_ACTIVE", "active")

    script.compile_dot_logs(
        access_log_path=str(tmp_path / "access.csv"),
        run_locations_path=str(tmp_path / "runid-locations.json"),
        run_roots=[str(run_root)],
        legacy_roots=[str(tmp_path / "legacy")],
    )

    assert json.loads((tmp_path / "runid-locations.json").read_text(encoding="utf-8")) == []
    assert json.loads((tmp_path / "runs_counter.json").read_text(encoding="utf-8"))["projects"] == 1


@pytest.mark.parametrize("failure_index", range(4))
@pytest.mark.parametrize("failure_type", [OSError, JobTimeoutException])
def test_publication_failure_restores_all_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure_index: int,
    failure_type: type[Exception],
) -> None:
    generation = "test-generation"
    publications: list[tuple[Path, Path]] = []
    old_values: dict[Path, str] = {}
    for index, name in enumerate(("access.csv", "runid-locations.json", "runs_counter.json", "run_counts.csv")):
        target = tmp_path / name
        candidate = script._candidate_path(target, generation)
        old_values[target] = f"old-{index}"
        target.write_text(old_values[target], encoding="utf-8")
        candidate.write_text(f"new-{index}", encoding="utf-8")
        publications.append((candidate, target))

    original_replace = Path.replace
    candidate_promotions = 0

    def failing_replace(self: Path, target: Path) -> Path:
        nonlocal candidate_promotions
        if ".candidate." in self.name:
            if candidate_promotions == failure_index:
                raise failure_type("injected promotion failure")
            candidate_promotions += 1
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", failing_replace)
    with pytest.raises(failure_type, match="injected promotion failure"):
        script._publish_candidates(tuple(publications), generation)

    for target, old_value in old_values.items():
        assert target.read_text(encoding="utf-8") == old_value


def test_compile_lock_rejects_overlap(tmp_path: Path) -> None:
    with script._compile_lock(tmp_path):
        with pytest.raises(RuntimeError, match="already running"):
            with script._compile_lock(tmp_path):
                pass


def test_duplicate_runid_logs_reuse_same_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runid = "mike-november"
    run_root = tmp_path / "runs"
    primary_dir = run_root / "mn" / runid
    primary_dir.mkdir(parents=True)
    _write_parquet_rows(primary_dir / "watershed" / "hillslopes.parquet", 4)
    _write_access_log(run_root / "mn" / f".{runid}", [datetime(2025, 7, 1, 12, 0, 0)])

    legacy_root = tmp_path / "legacy"
    (legacy_root / runid).mkdir(parents=True)
    _write_access_log(legacy_root / f".{runid}", [datetime(2025, 7, 2, 12, 0, 0)])
    monkeypatch.setattr(script, "Ron", RonStub)
    monkeypatch.setattr(script, "Watershed", WatershedStub)
    ttl_module = __import__("wepppy.weppcloud.utils.run_ttl", fromlist=["read_ttl_state"])
    monkeypatch.setattr(ttl_module, "touch_ttl", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ttl_module, "read_ttl_state", lambda _wd: {"delete_state": "active"})
    monkeypatch.setattr(ttl_module, "DELETE_STATE_ACTIVE", "active")

    result = script.compile_dot_logs(
        access_log_path=str(tmp_path / "access.csv"),
        run_locations_path=str(tmp_path / "runid-locations.json"),
        run_roots=[str(run_root)],
        legacy_roots=[str(legacy_root)],
    )

    rows = _read_access_csv(tmp_path / "access.csv")
    assert result["logs"] == 2
    assert result["runs"] == 1
    assert [row["hillslopes"] for row in rows] == ["4", "4"]


def test_disappearance_after_stat_is_counted_as_read_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parquet_path = tmp_path / "hillslopes.parquet"
    parquet_path.write_text("present before read", encoding="utf-8")
    health = script.ArtifactHealth()

    def disappear(_path: Path) -> None:
        raise FileNotFoundError("disappeared after stat")

    monkeypatch.setattr(script.pq, "ParquetFile", disappear)
    assert script._parquet_row_count(parquet_path, "race-run", "watershed", health) == 0
    assert health.watershed_errors == 1
    assert health.watershed_missing == 0


@pytest.mark.parametrize("artifact", ["watershed", "ash"])
def test_systemic_threshold_preserves_all_outputs_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    artifact: str,
) -> None:
    class Metadata:
        num_rows = 1

    class FakeParquetFile:
        metadata = Metadata()

        def __init__(self, path: Path) -> None:
            path = Path(path)
            run_number = int(path.parents[1 if path.parent.name == "watershed" else 2].name.split("-")[-1])
            is_target = path.parent.name == "watershed" if artifact == "watershed" else path.parent.name == "post"
            if is_target and run_number < 10:
                raise pa.ArrowInvalid("injected systemic corruption")

    run_root = tmp_path / "runs"
    prefix_dir = run_root / "op"
    prefix_dir.mkdir(parents=True)
    for index in range(40):
        runid = f"oscar-papa-{index}"
        run_dir = prefix_dir / runid
        run_dir.mkdir()
        for path in (
            run_dir / "watershed" / "hillslopes.parquet",
            run_dir / "ash" / "post" / "hillslope_annuals.parquet",
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        _write_access_log(prefix_dir / f".{runid}", [datetime(2025, 8, 1, 12, 0, 0)])

    monkeypatch.setattr(script, "Ron", RonStub)
    monkeypatch.setattr(script, "Watershed", WatershedStub)
    monkeypatch.setattr(script.pq, "ParquetFile", FakeParquetFile)
    outputs = {
        tmp_path / "access.csv": "old access",
        tmp_path / "runid-locations.json": "old locations",
        tmp_path / "runs_counter.json": "old counters",
        tmp_path / "run_counts.csv": "old counts",
    }
    for path, value in outputs.items():
        path.write_text(value, encoding="utf-8")

    with pytest.raises(RuntimeError, match=f"systemic {artifact} parquet errors"):
        script.compile_dot_logs(
            access_log_path=str(tmp_path / "access.csv"),
            run_locations_path=str(tmp_path / "runid-locations.json"),
            run_roots=[str(run_root)],
            legacy_roots=[str(tmp_path / "legacy")],
        )

    for path, value in outputs.items():
        assert path.read_text(encoding="utf-8") == value
    assert list(tmp_path.glob("*.candidate.*")) == []


@pytest.mark.parametrize(
    "health",
    [
        script.ArtifactHealth(watershed_readable=31, watershed_errors=9),
        script.ArtifactHealth(watershed_readable=40, ash_readable=31, ash_errors=9),
    ],
)
def test_systemic_threshold_does_not_trip_below_boundary(health: script.ArtifactHealth) -> None:
    script._validate_artifact_health(40, health)


def test_next_locked_run_recovers_interrupted_publication(tmp_path: Path) -> None:
    generation = "interrupted"
    target = tmp_path / "access.csv"
    backup = tmp_path / f"access.csv.last-good.{generation}"
    candidate = script._candidate_path(target, generation)
    target.write_text("mixed new", encoding="utf-8")
    backup.write_text("last good", encoding="utf-8")
    candidate.write_text("candidate", encoding="utf-8")
    journal = tmp_path / f".compile_dot_logs.publish.{generation}.json"
    journal.write_text(
        json.dumps({"publications": [{"candidate": str(candidate), "target": str(target), "existed": True}]}),
        encoding="utf-8",
    )

    with script._compile_lock(tmp_path):
        script._recover_interrupted_publications({tmp_path})

    assert target.read_text(encoding="utf-8") == "last good"
    assert not backup.exists()
    assert not candidate.exists()
    assert not journal.exists()


def test_rollback_failure_is_recovered_on_next_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    generation = "rollback-failure"
    publications: list[tuple[Path, Path]] = []
    for index, name in enumerate(("access.csv", "runid-locations.json")):
        target = tmp_path / name
        candidate = script._candidate_path(target, generation)
        target.write_text(f"old-{index}", encoding="utf-8")
        candidate.write_text(f"new-{index}", encoding="utf-8")
        publications.append((candidate, target))

    original_replace = Path.replace
    promotion_count = 0
    rollback_failed = False

    def failing_replace(self: Path, target: Path) -> Path:
        nonlocal promotion_count, rollback_failed
        if ".candidate." in self.name:
            if promotion_count == 1:
                raise JobTimeoutException("timeout during promotion")
            promotion_count += 1
        if ".last-good." in self.name and target.name == "access.csv" and not rollback_failed:
            rollback_failed = True
            raise OSError("rollback unavailable")
        return original_replace(self, target)

    with monkeypatch.context() as patch_context:
        patch_context.setattr(Path, "replace", failing_replace)
        with pytest.raises(JobTimeoutException, match="timeout during promotion"):
            script._publish_candidates(tuple(publications), generation)

    assert (tmp_path / f".compile_dot_logs.publish.{generation}.json").exists()
    with script._compile_lock(tmp_path):
        script._recover_interrupted_publications({tmp_path})

    assert (tmp_path / "access.csv").read_text(encoding="utf-8") == "old-0"
    assert (tmp_path / "runid-locations.json").read_text(encoding="utf-8") == "old-1"


def test_cross_directory_run_locations_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "runs"
    prefix_dir = run_root / "qr"
    prefix_dir.mkdir(parents=True)
    runid = "quebec-romeo"
    run_dir = prefix_dir / runid
    run_dir.mkdir()
    _write_parquet_rows(run_dir / "watershed" / "hillslopes.parquet", 1)
    _write_access_log(prefix_dir / f".{runid}", [datetime(2025, 9, 1, 12, 0, 0)])
    monkeypatch.setattr(script, "Ron", RonStub)
    monkeypatch.setattr(script, "Watershed", WatershedStub)
    ttl_module = __import__("wepppy.weppcloud.utils.run_ttl", fromlist=["read_ttl_state"])
    monkeypatch.setattr(ttl_module, "touch_ttl", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ttl_module, "read_ttl_state", lambda _wd: {"delete_state": "active"})
    monkeypatch.setattr(ttl_module, "DELETE_STATE_ACTIVE", "active")
    locations_dir = tmp_path / "external-locations"
    locations_path = locations_dir / "runid-locations.json"

    script.compile_dot_logs(
        access_log_path=str(tmp_path / "access.csv"),
        run_locations_path=str(locations_path),
        run_roots=[str(run_root)],
        legacy_roots=[str(tmp_path / "legacy")],
    )

    assert json.loads(locations_path.read_text(encoding="utf-8"))[0]["runid"] == runid
    assert (locations_dir / ".compile_dot_logs.lock").exists()


@pytest.mark.parametrize("commit_phase", ["backup", "candidate"])
def test_post_commit_timeout_reconciles_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    commit_phase: str,
) -> None:
    generation = f"post-commit-{commit_phase}"
    target = tmp_path / "access.csv"
    candidate = script._candidate_path(target, generation)
    candidate.write_text("new", encoding="utf-8")
    if commit_phase == "backup":
        target.write_text("old", encoding="utf-8")

    original_replace = Path.replace
    injected = False

    def post_commit_timeout(self: Path, destination: Path) -> Path:
        nonlocal injected
        result = original_replace(self, destination)
        is_phase = ".last-good." in destination.name if commit_phase == "backup" else ".candidate." in self.name
        if is_phase and not injected:
            injected = True
            raise JobTimeoutException(f"timeout after {commit_phase} commit")
        return result

    monkeypatch.setattr(Path, "replace", post_commit_timeout)
    with pytest.raises(JobTimeoutException, match=f"timeout after {commit_phase} commit"):
        script._publish_candidates(((candidate, target),), generation)

    if commit_phase == "backup":
        assert target.read_text(encoding="utf-8") == "old"
    else:
        assert not target.exists()
    assert not (tmp_path / f".compile_dot_logs.publish.{generation}.json").exists()
