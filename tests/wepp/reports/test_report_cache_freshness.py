"""Real native/DuckDB cache generations; only controller acquisition is isolated."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pyarrow.parquet as pq
import pytest

from wepppy.nodb.core import Watershed
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport
from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport
from wepppy.wepp.reports import _cache_freshness as freshness

pytestmark = pytest.mark.integration


def _table(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_parquet(path, index=False, compression=None,
                                   use_dictionary=False, write_statistics=False)


def _rewrite(path, column, value):
    version = path.stat()
    frame = pd.read_parquet(path)
    frame[column] = value
    frame.to_parquet(path, index=False, compression=None, use_dictionary=False, write_statistics=False)
    os.utime(path, ns=(version.st_atime_ns, version.st_mtime_ns))
    assert path.stat().st_size == version.st_size


@pytest.fixture
def run(tmp_path, monkeypatch):
    root = tmp_path / "run"
    _table(root / "watershed/hillslopes.parquet", [
        {"topaz_id": 101, "wepp_id": 1, "area": 1000.0},
        {"topaz_id": 201, "wepp_id": 2, "area": 3000.0},
    ])
    _table(root / "watershed/channels.parquet", [{"topaz_id": 204}])
    _table(root / "landuse/landuse.parquet", [
        {"topaz_id": 101, "key": 100, "desc": "Forest"},
        {"topaz_id": 201, "key": 200, "desc": "Meadow"},
    ])
    _table(root / "wepp/output/interchange/loss_pw0.hill.parquet", [
        {"wepp_id": 1, "Runoff Volume": 100.0, "Subrunoff Volume": 20.0,
         "Baseflow Volume": 10.0, "Soil Loss": 5.0, "Sediment Yield": 3.0,
         "Sediment Deposition": 2.0},
    ])
    _table(root / "wepp/output/interchange/H.wat.parquet", [
        {"wepp_id": 1, "ofe_id": 1, "sim_day_index": 1, "water_year": 2001,
         "P": 1.0, "Dp": 0.5, "QOFE": 0.2, "latqcc": 0.1,
         "Ep": 0.05, "Es": 0.03, "Er": 0.02, "Area": 1000.0},
    ])
    owner = object.__new__(Watershed)
    owner.wd = str(root)
    owner._subs_summary = None
    owner._chns_summary = None
    monkeypatch.setattr(Watershed, "getInstance", lambda wd: owner)
    return root


def _rows(report):
    iterator = report.avg_annual_iter() if isinstance(report, HillslopeWatbalReport) else report
    return [dict(row.row) for row in iterator]


@pytest.mark.parametrize("change", ["wat", "translator", "loss", "area", "landuse", "roads"])
def test_actual_report_changes_with_consumed_bytes(run, change):
    roads = change == "roads"
    if roads:
        source = run / "wepp/roads/output/interchange/H.wat.parquet"
        source.parent.mkdir(parents=True)
        shutil.copyfile(run / "wepp/output/interchange/H.wat.parquet", source)
        _rewrite(source, "wepp_id", 900001)
        manifest = run / "wepp/roads/segments/roads.segment.pass.manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text('[{"segment_run_id":900001,"target_hillslope_wepp_id":1}]')
        baseline = _rows(HillslopeWatbalReport(run))
    constructor = (lambda: HillslopeWatbalReport(run, output_scope="roads" if roads else "baseline")) if change in {"wat", "translator", "roads"} else lambda: AverageAnnualsByLanduseReport(run)
    before = _rows(constructor())
    if change == "wat":
        _rewrite(run / "wepp/output/interchange/H.wat.parquet", "P", 9.0)
    elif change == "translator":
        _rewrite(run / "watershed/hillslopes.parquet", "topaz_id", [301, 401])
    elif change == "loss":
        _rewrite(run / "wepp/output/interchange/loss_pw0.hill.parquet", "Runoff Volume", 900.0)
    elif change == "area":
        _rewrite(run / "watershed/hillslopes.parquet", "area", [2000.0, 3000.0])
    elif change == "landuse":
        _rewrite(run / "landuse/landuse.parquet", "desc", ["Shrubs", "Meadow"])
    else:
        stamp = manifest.stat()
        manifest.write_text(manifest.read_text().replace('"wepp_id":1', '"wepp_id":2').replace('"target_hillslope_wepp_id":1', '"target_hillslope_wepp_id":2'))
        os.utime(manifest, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    after = constructor()
    assert after.cache_status == "built"
    assert _rows(after) != before
    assert constructor().cache_status == "current"
    if roads:
        assert _rows(HillslopeWatbalReport(run)) == baseline


@pytest.mark.parametrize("report_type", [HillslopeWatbalReport, AverageAnnualsByLanduseReport])
def test_metadata_churn_and_partial_history(run, report_type):
    first = report_type(run)
    source = run / ("wepp/output/interchange/H.wat.parquet" if report_type is HillslopeWatbalReport else "landuse/landuse.parquet")
    accepted = run / "wepp/reports/cache" / f"{report_type._CACHE_KEY}.parquet"
    generation = accepted.read_bytes()
    source.touch()
    os.link(source, source.with_suffix(".hardlink"))
    assert report_type(run).cache_status == "current"
    assert accepted.read_bytes() == generation
    source.unlink()
    historical = report_type(run)
    assert historical.cache_status == "historical_unverified"
    assert _rows(historical) == _rows(first)
    if report_type is AverageAnnualsByLanduseReport:
        _rewrite(run / "watershed/hillslopes.parquet", "area", [2000.0, 3000.0])
        with pytest.raises(FileNotFoundError):
            report_type(run)
    else:
        _rewrite(run / "watershed/hillslopes.parquet", "topaz_id", [301, 401])
        with pytest.raises(FileNotFoundError):
            report_type(run)


@pytest.mark.parametrize("report_type", [HillslopeWatbalReport, AverageAnnualsByLanduseReport])
def test_changed_during_real_build_preserves_cache_and_work(run, monkeypatch, report_type):
    report_type(run)
    cache = run / "wepp/reports/cache" / f"{report_type._CACHE_KEY}.parquet"
    previous = cache.read_bytes()
    source = run / ("wepp/output/interchange/H.wat.parquet" if report_type is HillslopeWatbalReport else "wepp/output/interchange/loss_pw0.hill.parquet")
    column = "P" if report_type is HillslopeWatbalReport else "Runoff Volume"
    _rewrite(source, column, 2.0)
    method = "_write_native_summary" if report_type is HillslopeWatbalReport else "_build_dataframe"
    real = getattr(report_type, method)
    def changed(self, *args, **kwargs):
        result = real(self, *args, **kwargs)
        _rewrite(source, column, 3.0)
        return result
    monkeypatch.setattr(report_type, method, changed)
    with pytest.raises(RuntimeError, match="dependencies changed"):
        report_type(run)
    assert cache.read_bytes() == previous
    statuses = [json.loads(p.read_text()) for p in cache.parent.glob(f"{report_type._CACHE_KEY}.attempts/*/status.json")]
    assert any(status["status"] == "failed" for status in statuses)
    if report_type is HillslopeWatbalReport:
        assert len(list(cache.parent.glob(f"{report_type._CACHE_KEY}.attempts/*/native.parquet"))) == 2


def test_catalog_aliases_are_consumed_and_symlink_destination_preserved(run):
    AverageAnnualsByLanduseReport(run)
    cache = run / "wepp/reports/cache/average_annuals_by_landuse.parquet"
    target = cache.with_name("historical-location.parquet")
    cache.rename(target)
    cache.symlink_to(target.name)
    _rewrite(run / "wepp/output/interchange/loss_pw0.hill.parquet", "Runoff Volume", 900.0)
    report = AverageAnnualsByLanduseReport(run)
    assert cache.is_symlink() and report.cache_status == "built"
    assert _rows(report)[0]["Avg Runoff Depth (mm/yr)"] == 900.0
    catalog_path = run / "_query_engine/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    for entry in catalog["files"]:
        if entry["path"] == "watershed/hillslopes.parquet":
            entry["schema"]["fields"].append({"name": "WeppID"})
    catalog_path.write_text(json.dumps(catalog))
    # Aliases changed even though the selected data bytes and paths did not.
    assert AverageAnnualsByLanduseReport(run).cache_status == "built"


def test_native_destination_mode_and_concurrent_generations(run):
    HillslopeWatbalReport(run)
    cache = run / "wepp/reports/cache/hillslope_watbal_summary.parquet"
    cache.chmod(0o640)
    source = run / "wepp/output/interchange/H.wat.parquet"
    _rewrite(source, "P", 9.0)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _rows(HillslopeWatbalReport(run)), range(2)))
    assert results[0] == results[1]
    assert cache.stat().st_mode & 0o777 == 0o640
    for candidate in cache.parent.glob("hillslope_watbal_summary.attempts/*/native.parquet"):
        if pd.read_parquet(candidate)["Precipitation (mm)"].iloc[0] == 9.0:
            assert candidate.stat().st_mode & 0o777 == 0o640
    assert HillslopeWatbalReport(run).cache_status == "current"
    target = cache.with_name("target.parquet")
    cache.rename(target)
    cache.symlink_to(target.name)
    _rewrite(source, "P", 8.0)
    previous = target.read_bytes()
    with pytest.raises(OSError, match="regular file"):
        HillslopeWatbalReport(run)
    assert cache.is_symlink() and target.read_bytes() == previous


def test_malformed_provenance_is_not_legacy(run):
    HillslopeWatbalReport(run)
    cache = run / "wepp/reports/cache/hillslope_watbal_summary.parquet"
    table = pq.read_table(cache)
    metadata = dict(table.schema.metadata)
    metadata[freshness._METADATA_KEY] = b'{"version": 999}'
    pq.write_table(table.replace_schema_metadata(metadata), cache)
    with pytest.raises(ValueError, match="provenance"):
        HillslopeWatbalReport(run)


def test_missing_translator_is_historical_but_changed_source_is_not(run):
    expected = _rows(HillslopeWatbalReport(run))
    (run / "watershed/channels.parquet").unlink()
    historical = HillslopeWatbalReport(run)
    assert historical.cache_status == "historical_unverified"
    assert _rows(historical) == expected
    _rewrite(run / "wepp/output/interchange/H.wat.parquet", "P", 9.0)
    with pytest.raises(FileNotFoundError, match="Translator source absent"):
        HillslopeWatbalReport(run)


def test_in_memory_translator_precedence_and_unknown_id(run, monkeypatch):
    owner = Watershed.getInstance(str(run))
    owner._subs_summary = {301: {}, 401: {}}
    owner._chns_summary = {404: {}}
    first = HillslopeWatbalReport(run)
    assert _rows(first)[0]["TopazID"] == 301
    _rewrite(run / "watershed/hillslopes.parquet", "topaz_id", [501, 601])
    assert HillslopeWatbalReport(run).cache_status == "current"
    owner._subs_summary = {701: {}, 801: {}}
    assert _rows(HillslopeWatbalReport(run))[0]["TopazID"] == 701
    _rewrite(run / "wepp/output/interchange/H.wat.parquet", "wepp_id", 99)
    with pytest.raises(KeyError):
        HillslopeWatbalReport(run)


@pytest.mark.parametrize("report_type", [HillslopeWatbalReport, AverageAnnualsByLanduseReport])
def test_required_read_denial_never_becomes_history(run, report_type):
    assert os.geteuid() != 0, "Permission regression requires normal service identity"
    report_type(run)
    source = run / ("wepp/output/interchange/H.wat.parquet" if report_type is HillslopeWatbalReport else "landuse/landuse.parquet")
    source.chmod(0)
    try:
        with pytest.raises(PermissionError):
            report_type(run)
    finally:
        source.chmod(0o644)


@pytest.mark.parametrize("legacy_location", [False, True])
def test_unverified_legacy_native_unavailable_is_historical(run, monkeypatch, legacy_location):
    from wepppy.wepp.interchange import _rust_interchange
    from types import SimpleNamespace

    expected = _rows(HillslopeWatbalReport(run))
    cache = run / "wepp/reports/cache/hillslope_watbal_summary.parquet"
    table = pq.read_table(cache)
    metadata = dict(table.schema.metadata)
    metadata.pop(freshness._METADATA_KEY)
    if legacy_location:
        destination = run / "wepp/output/interchange/hillslope_watbal_summary.parquet"
        cache.unlink()
    else:
        destination = cache
    pq.write_table(table.replace_schema_metadata(metadata), destination)
    monkeypatch.setattr(_rust_interchange, "_import_wepppyo3_interchange", lambda: SimpleNamespace())
    report = HillslopeWatbalReport(run)
    assert report.cache_status == "historical_unverified" and _rows(report) == expected
    source = run / "wepp/output/interchange/H.wat.parquet"
    newer = destination.stat().st_mtime_ns + 1_000_000_000
    os.utime(source, ns=(newer, newer))
    with pytest.raises(_rust_interchange.WeppInterchangeUnavailableError):
        HillslopeWatbalReport(run)


@pytest.mark.parametrize("report_type", [HillslopeWatbalReport, AverageAnnualsByLanduseReport])
def test_real_publication_denial_retains_prior_and_failed_candidate(run, monkeypatch, report_type):
    assert os.geteuid() != 0
    report_type(run)
    cache = run / "wepp/reports/cache" / f"{report_type._CACHE_KEY}.parquet"
    before = cache.read_bytes()
    source = run / ("wepp/output/interchange/H.wat.parquet" if report_type is HillslopeWatbalReport else "wepp/output/interchange/loss_pw0.hill.parquet")
    _rewrite(source, "P" if report_type is HillslopeWatbalReport else "Runoff Volume", 9.0)
    status = freshness._CacheBuild._status
    def deny_commit(self, state, error=None):
        status(self, state, error)
        if state == "ready_to_publish":
            cache.parent.chmod(0o555)
    monkeypatch.setattr(freshness._CacheBuild, "_status", deny_commit)
    try:
        with pytest.raises(PermissionError):
            report_type(run)
    finally:
        cache.parent.chmod(0o755)
    assert cache.read_bytes() == before
    attempts = cache.parent.glob(f"{report_type._CACHE_KEY}.attempts/*/status.json")
    failed = [p.parent for p in attempts if json.loads(p.read_text())["status"] == "failed"]
    assert len(failed) == 1
    assert (failed[0] / "candidate.parquet").is_file()
    assert (failed[0] / ("native.parquet" if report_type is HillslopeWatbalReport else "query.parquet")).is_file()


def test_postcommit_status_failure_does_not_rollback(run, monkeypatch):
    HillslopeWatbalReport(run)
    _rewrite(run / "wepp/output/interchange/H.wat.parquet", "P", 9.0)
    real = freshness._CacheBuild._status
    def failed_status(self, status, error=None):
        if status == "complete":
            raise OSError("status volume unavailable after commit")
        return real(self, status, error)
    monkeypatch.setattr(freshness._CacheBuild, "_status", failed_status)
    report = HillslopeWatbalReport(run)
    assert report.cache_status == "built"
    assert _rows(report)[0]["Precipitation (mm)"] == 9.0
    assert HillslopeWatbalReport(run).cache_status == "current"


def test_canonical_archive_restore_keeps_report_provenance_and_failed_work(run, monkeypatch):
    import zipfile
    from types import SimpleNamespace
    from wepppy.rq.project_rq_archive import ArchiveRuntime, archive_rq, restore_archive_rq
    from wepppy.nodb.project_config_update import project_config_lifecycle_guard

    HillslopeWatbalReport(run)
    AverageAnnualsByLanduseReport(run)
    _rewrite(run / "wepp/output/interchange/H.wat.parquet", "P", 9.0)
    real = HillslopeWatbalReport._write_native_summary
    def changed(self, *args, **kwargs):
        result = real(self, *args, **kwargs)
        _rewrite(run / "wepp/output/interchange/H.wat.parquet", "P", 8.0)
        return result
    with monkeypatch.context() as patch:
        patch.setattr(HillslopeWatbalReport, "_write_native_summary", changed)
        with pytest.raises(RuntimeError, match="dependencies changed"):
            HillslopeWatbalReport(run)
    # Restore the accepted input generation so the archived cache is current.
    _rewrite(run / "wepp/output/interchange/H.wat.parquet", "P", 1.0)
    expected = {str(path.relative_to(run)): path.read_bytes()
                for path in (run / "wepp/reports/cache").rglob("*") if path.is_file()}
    runtime = ArchiveRuntime(
        get_current_job=lambda: SimpleNamespace(id="report-archive-test"),
        get_wd=lambda runid: str(run), get_prep_from_runid=lambda runid: None,
        lock_statuses=lambda runid: {}, clear_nodb_file_cache=lambda runid: [],
        publish_status=lambda channel, message: None, disk_usage=shutil.disk_usage,
        zip_file_cls=zipfile.ZipFile, project_config_lifecycle_guard=project_config_lifecycle_guard,
        project_config_authority_wd=lambda runid: str(run),
    )
    archive_rq("report-fixture", "report generations", runtime=runtime)
    archive = next((run / "archives").glob("*.zip"))
    with zipfile.ZipFile(archive) as members:
        assert expected.keys() <= set(members.namelist())
        assert all(members.read(name) == content for name, content in expected.items())
    shutil.rmtree(run / "wepp/reports/cache")
    restore_archive_rq("report-fixture", archive.name, runtime=runtime)
    assert all((run / name).read_bytes() == content for name, content in expected.items())
    assert HillslopeWatbalReport(run).cache_status == "current"
    assert AverageAnnualsByLanduseReport(run).cache_status == "current"


@pytest.mark.parametrize("missing", ["hillslopes", "channels"])
def test_missing_translator_does_not_hide_denied_peer(run, missing):
    HillslopeWatbalReport(run)
    (run / f"watershed/{missing}.parquet").unlink()
    peer = run / f"watershed/{'channels' if missing == 'hillslopes' else 'hillslopes'}.parquet"
    peer.chmod(0)
    try:
        with pytest.raises(PermissionError):
            HillslopeWatbalReport(run)
    finally:
        peer.chmod(0o644)


def test_changed_source_uses_new_native_ids(run):
    source = run / "wepp/output/interchange/H.wat.parquet"
    _rewrite(source, "wepp_id", 2)
    assert _rows(HillslopeWatbalReport(run))[0]["TopazID"] == 201
    _rewrite(source, "wepp_id", 1)
    _table(run / "watershed/hillslopes.parquet", [{"topaz_id": 301, "wepp_id": 1, "area": 1000.0}])
    _table(run / "watershed/channels.parquet", [])
    # Persisted empty channel summaries are a supported actual translator state.
    owner = Watershed.getInstance(str(run))
    owner._subs_summary, owner._chns_summary = {301: {}}, {}
    report = HillslopeWatbalReport(run)
    assert report.cache_status == "built"
    assert _rows(report)[0]["TopazID"] == 301


def test_missing_catalog_historical_read_requires_no_writes(run):
    expected = _rows(AverageAnnualsByLanduseReport(run))
    for source in (AverageAnnualsByLanduseReport._LOSS_DATASET,
                   AverageAnnualsByLanduseReport._HILLSLOPE_DATASET,
                   AverageAnnualsByLanduseReport._LANDUSE_DATASET):
        (run / source).unlink()
    shutil.rmtree(run / "_query_engine")
    run.chmod(0o555)
    try:
        report = AverageAnnualsByLanduseReport(run)
        assert report.cache_status == "historical_unverified" and _rows(report) == expected
        assert not (run / "_query_engine").exists()
    finally:
        run.chmod(0o755)


@pytest.mark.parametrize("proof_value", [None, {"invalid": True}])
def test_absent_observation_does_not_hide_invalid_accepted_alias(run, proof_value):
    AverageAnnualsByLanduseReport(run)
    cache = run / "wepp/reports/cache/average_annuals_by_landuse.parquet"
    table = pq.read_table(cache)
    metadata = dict(table.schema.metadata)
    proof = json.loads(metadata[freshness._METADATA_KEY])
    logical = AverageAnnualsByLanduseReport._LANDUSE_DATASET
    proof["dependencies"][f"{logical}:aliases"] = proof_value
    metadata[freshness._METADATA_KEY] = json.dumps(proof).encode()
    pq.write_table(table.replace_schema_metadata(metadata), cache)
    (run / logical).unlink()
    catalog_path = run / "_query_engine/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    catalog["files"] = [entry for entry in catalog["files"] if entry["path"] != logical]
    catalog_path.write_text(json.dumps(catalog))
    with pytest.raises(ValueError, match="alias provenance"):
        AverageAnnualsByLanduseReport(run)


def test_unverified_partial_history_validates_present_parquet(run):
    AverageAnnualsByLanduseReport(run)
    cache = run / "wepp/reports/cache/average_annuals_by_landuse.parquet"
    table = pq.read_table(cache)
    metadata = dict(table.schema.metadata)
    metadata.pop(freshness._METADATA_KEY)
    pq.write_table(table.replace_schema_metadata(metadata), cache)
    (run / "landuse/landuse.parquet").unlink()
    (run / "watershed/hillslopes.parquet").write_bytes(b"not a parquet table")
    with pytest.raises(ValueError):
        AverageAnnualsByLanduseReport(run)


def test_read_cache_rows_and_proof_share_opened_generation(run, monkeypatch):
    HillslopeWatbalReport(run)
    cache = run / "wepp/reports/cache/hillslope_watbal_summary.parquet"
    original = cache.read_bytes()
    original_proof = pq.read_schema(cache).metadata[freshness._METADATA_KEY]
    _rewrite(run / "wepp/output/interchange/H.wat.parquet", "P", 9.0)
    HillslopeWatbalReport(run)
    replacement = cache.with_name("replacement.parquet")
    cache.rename(replacement)
    cache.write_bytes(original)
    real = pq.read_table
    def replace_after_open(incoming, *args, **kwargs):
        if getattr(incoming, "name", None) == str(cache):
            os.replace(replacement, cache)
        return real(incoming, *args, **kwargs)
    monkeypatch.setattr(pq, "read_table", replace_after_open)
    table, proof = freshness._read_cache(cache, "hillslope_watbal_summary")
    assert table.to_pandas()["Precipitation (mm)"].iloc[0] == 1.0
    assert proof == json.loads(original_proof)
    assert real(cache).to_pandas()["Precipitation (mm)"].iloc[0] == 9.0


def test_concurrent_publications_retain_distinct_matching_attempts(run, monkeypatch):
    import threading

    HillslopeWatbalReport(run)
    _rewrite(run / "wepp/output/interchange/H.wat.parquet", "P", 9.0)
    barrier = threading.Barrier(2, timeout=20)
    status = freshness._CacheBuild._status
    def overlap(self, state, error=None):
        status(self, state, error)
        if state == "ready_to_publish":
            barrier.wait()
    monkeypatch.setattr(freshness._CacheBuild, "_status", overlap)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _rows(HillslopeWatbalReport(run)), range(2)))
    assert results[0] == results[1]
    cache = run / "wepp/reports/cache/hillslope_watbal_summary.parquet"
    proof = json.loads(pq.read_schema(cache).metadata[freshness._METADATA_KEY])
    complete = [json.loads(path.read_text()) for path in cache.parent.glob("hillslope_watbal_summary.attempts/*/status.json")]
    assert len(complete) == 3 and len({entry["attempt_id"] for entry in complete}) == 3
    assert all(entry["status"] == "complete" for entry in complete)
    matching = [entry for entry in complete if entry["attempt_id"] == proof["attempt_id"]]
    assert len(matching) == 1 and matching[0]["observations"]["after"] == proof["dependencies"]


@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize("absolute", [False, True])
def test_relocated_catalog_query_and_proof_use_requested_run(run, tmp_path, partial, absolute):
    original = AverageAnnualsByLanduseReport(run)
    catalog_path = run / "_query_engine/catalog.json"
    if absolute:
        catalog = json.loads(catalog_path.read_text())
        for entry in catalog["files"]:
            if entry["path"] in (AverageAnnualsByLanduseReport._LOSS_DATASET,
                                 AverageAnnualsByLanduseReport._HILLSLOPE_DATASET,
                                 AverageAnnualsByLanduseReport._LANDUSE_DATASET):
                entry["fs_path"] = str(run / entry["path"])
        catalog_path.write_text(json.dumps(catalog))
    relocated = tmp_path / "relocated"
    shutil.copytree(run, relocated)
    unchanged_catalog = (relocated / "_query_engine/catalog.json").read_bytes()
    if partial:
        (relocated / "landuse/landuse.parquet").unlink()
        report = AverageAnnualsByLanduseReport(relocated)
        assert report.cache_status == "historical_unverified" and _rows(report) == _rows(original)
    else:
        _rewrite(relocated / "wepp/output/interchange/loss_pw0.hill.parquet", "Runoff Volume", 900.0)
        report = AverageAnnualsByLanduseReport(relocated)
        assert _rows(report)[0]["Avg Runoff Depth (mm/yr)"] == 900.0
        proof = json.loads(pq.read_schema(relocated / "wepp/reports/cache/average_annuals_by_landuse.parquet").metadata[freshness._METADATA_KEY])
        source = relocated / AverageAnnualsByLanduseReport._LOSS_DATASET
        assert proof["dependencies"][AverageAnnualsByLanduseReport._LOSS_DATASET] == freshness._observe_file(relocated, source)
        assert _rows(AverageAnnualsByLanduseReport(run)) == _rows(original)
    assert (relocated / "_query_engine/catalog.json").read_bytes() == unchanged_catalog


def test_relocated_parent_reference_and_standalone_rejection(run, tmp_path):
    AverageAnnualsByLanduseReport(run)
    old_parent = tmp_path / "old-parent"
    old_child = old_parent / "_pups/omni/scenarios/child"
    shutil.copytree(run, old_child)
    loss = AverageAnnualsByLanduseReport._LOSS_DATASET
    inherited = old_parent / loss
    inherited.parent.mkdir(parents=True)
    shutil.copyfile(run / loss, inherited)
    catalog_path = old_child / "_query_engine/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    catalog["root"] = str(old_child)
    for entry in catalog["files"]:
        if entry["path"] == loss:
            entry["fs_path"] = str(inherited)
    catalog_path.write_text(json.dumps(catalog))
    AverageAnnualsByLanduseReport(old_child)
    new_parent = tmp_path / "new-parent"
    shutil.copytree(old_parent, new_parent)
    _rewrite(new_parent / loss, "Runoff Volume", 900.0)
    new_child = new_parent / "_pups/omni/scenarios/child"
    assert _rows(AverageAnnualsByLanduseReport(new_child))[0]["Avg Runoff Depth (mm/yr)"] == 900.0
    standalone = tmp_path / "standalone"
    shutil.copytree(old_child, standalone)
    with pytest.raises(ValueError, match="allowed parent"):
        AverageAnnualsByLanduseReport(standalone)


def test_relocation_keeps_current_absolute_selection_and_rejects_escape(run, tmp_path):
    AverageAnnualsByLanduseReport(run)
    relocated = tmp_path / "relocated"
    shutil.copytree(run, relocated)
    logical = AverageAnnualsByLanduseReport._LOSS_DATASET
    chosen = relocated / "chosen-loss.parquet"
    shutil.copyfile(relocated / logical, chosen)
    _rewrite(chosen, "Runoff Volume", 900.0)
    catalog_path = relocated / "_query_engine/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    for entry in catalog["files"]:
        if entry["path"] == logical:
            entry["fs_path"] = str(chosen)
    catalog_path.write_text(json.dumps(catalog))
    assert _rows(AverageAnnualsByLanduseReport(relocated))[0]["Avg Runoff Depth (mm/yr)"] == 900.0
    for entry in catalog["files"]:
        if entry["path"] == logical:
            entry["fs_path"] = str(tmp_path / "external.parquet")
    shutil.copyfile(chosen, tmp_path / "external.parquet")
    catalog_path.write_text(json.dumps(catalog))
    with pytest.raises(ValueError, match="escapes allowed roots"):
        AverageAnnualsByLanduseReport(relocated)


def test_missing_catalog_observes_prior_redirect_only_as_history(run):
    AverageAnnualsByLanduseReport(run)
    logical = AverageAnnualsByLanduseReport._LOSS_DATASET
    redirected = run / "redirected-loss.parquet"
    (run / logical).rename(redirected)
    catalog_path = run / "_query_engine/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    for entry in catalog["files"]:
        if entry["path"] == logical:
            entry["fs_path"] = str(redirected)
    catalog_path.write_text(json.dumps(catalog))
    expected = _rows(AverageAnnualsByLanduseReport(run))
    (run / "landuse/landuse.parquet").unlink()
    shutil.rmtree(run / "_query_engine")
    historical = AverageAnnualsByLanduseReport(run)
    assert historical.cache_status == "historical_unverified" and _rows(historical) == expected
    assert not (run / "_query_engine").exists()
    _rewrite(redirected, "Runoff Volume", 900.0)
    with pytest.raises(FileNotFoundError):
        AverageAnnualsByLanduseReport(run)


def test_relocation_ignores_unconsumed_parent_catalog_entries(run, tmp_path):
    AverageAnnualsByLanduseReport(run)
    old_parent = tmp_path / "old-parent"
    child = old_parent / "_pups/omni/scenarios/child"
    shutil.copytree(run, child)
    catalog_path = child / "_query_engine/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    catalog["root"] = str(child)
    catalog["files"].append({"path": "soils/unconsumed.parquet", "extension": ".parquet",
                             "size_bytes": 0, "modified": "unused",
                             "fs_path": str(old_parent / "soils/unconsumed.parquet")})
    catalog_path.write_text(json.dumps(catalog))
    standalone = tmp_path / "standalone"
    shutil.copytree(child, standalone)
    assert AverageAnnualsByLanduseReport(standalone).cache_status == "current"


def test_relocation_rejects_selected_symlink_escape(run, tmp_path):
    AverageAnnualsByLanduseReport(run)
    relocated = tmp_path / "relocated"
    shutil.copytree(run, relocated)
    logical = AverageAnnualsByLanduseReport._LOSS_DATASET
    outside = tmp_path / "external.parquet"
    shutil.copyfile(run / logical, outside)
    (relocated / logical).unlink()
    (relocated / logical).symlink_to(outside)
    with pytest.raises(ValueError, match="escapes allowed roots"):
        AverageAnnualsByLanduseReport(relocated)


def test_missing_catalog_changed_complete_inputs_rebuild_in_one_call(run, monkeypatch):
    AverageAnnualsByLanduseReport(run)
    shutil.rmtree(run / "_query_engine")
    _rewrite(run / AverageAnnualsByLanduseReport._LOSS_DATASET, "Runoff Volume", 900.0)
    counts = {}
    real = freshness.sha256_file
    def counted(path):
        counts[str(path)] = counts.get(str(path), 0) + 1
        return real(path)
    monkeypatch.setattr(freshness, "sha256_file", counted)
    report = AverageAnnualsByLanduseReport(run)
    assert report.cache_status == "built"
    assert _rows(report)[0]["Avg Runoff Depth (mm/yr)"] == 900.0
    assert list(counts.values()) == [2, 2, 2]
