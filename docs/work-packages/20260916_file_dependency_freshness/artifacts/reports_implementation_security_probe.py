"""Independent report filesystem/error boundaries with real native/query readers."""
import json
import os
from pathlib import Path
import shutil
import stat

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tests.wepp.reports.test_report_cache_freshness import run, _rewrite, _rows
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport
from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport
from wepppy.wepp.reports import _cache_freshness as freshness


@pytest.mark.parametrize('missing,denied', [('hillslopes.parquet', 'channels.parquet'),
                                          ('channels.parquet', 'hillslopes.parquet')])
def test_characterize_partial_mapping_absence_hides_denial(run, missing, denied):
    assert os.getuid() != 0
    HillslopeWatbalReport(run)
    (run / 'watershed' / missing).unlink()
    denied_path = run / 'watershed' / denied
    mode = stat.S_IMODE(denied_path.stat().st_mode)
    denied_path.chmod(0)
    try:
        with pytest.raises(PermissionError):
            denied_path.read_bytes()
        report = HillslopeWatbalReport(run)
        print(json.dumps({'missing': missing, 'denied': denied,
                          'observed_status': report.cache_status}))
        assert report.cache_status == 'historical_unverified'
    finally:
        denied_path.chmod(mode)


@pytest.mark.parametrize('report_type,relative', [
    (HillslopeWatbalReport, 'wepp/output/interchange/H.wat.parquet'),
    (AverageAnnualsByLanduseReport, 'landuse/landuse.parquet'),
])
def test_present_input_denial_preserves_accepted_cache(run, report_type, relative):
    assert os.getuid() != 0
    report_type(run)
    cache = run / 'wepp/reports/cache' / f'{report_type._CACHE_KEY}.parquet'
    previous = cache.read_bytes()
    source = run / relative
    mode = stat.S_IMODE(source.stat().st_mode)
    source.chmod(0)
    try:
        with pytest.raises(PermissionError):
            report_type(run)
        assert cache.read_bytes() == previous
    finally:
        source.chmod(mode)


@pytest.mark.parametrize('report_type,column,relative', [
    (HillslopeWatbalReport, 'P', 'wepp/output/interchange/H.wat.parquet'),
    (AverageAnnualsByLanduseReport, 'Runoff Volume', 'wepp/output/interchange/loss_pw0.hill.parquet'),
])
@pytest.mark.parametrize('mode', [0o600, 0o640])
def test_restricted_payloads_and_publication_error_preserve_previous(run, monkeypatch, report_type, column, relative, mode):
    report_type(run)
    cache = run / 'wepp/reports/cache' / f'{report_type._CACHE_KEY}.parquet'
    cache.chmod(mode)
    previous = cache.read_bytes()
    _rewrite(run / relative, column, 9.)
    old_attempts = set(cache.parent.glob(f'{report_type._CACHE_KEY}.attempts/*'))
    real_replace = os.replace
    def fail_commit(source, target):
        if Path(target) == cache:
            raise OSError(28, 'controlled publication ENOSPC')
        return real_replace(source, target)
    monkeypatch.setattr(freshness.os, 'replace', fail_commit)
    with pytest.raises(OSError, match='ENOSPC'):
        report_type(run)
    assert cache.read_bytes() == previous and stat.S_IMODE(cache.stat().st_mode) == mode
    new_attempt, = set(cache.parent.glob(f'{report_type._CACHE_KEY}.attempts/*')) - old_attempts
    status = json.loads((new_attempt / 'status.json').read_text())
    assert status['status'] == 'failed'
    assert (new_attempt / 'candidate.parquet').is_file()
    assert (new_attempt / ('native.parquet' if report_type is HillslopeWatbalReport else 'query.parquet')).is_file()
    for path in new_attempt.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) == mode
    assert stat.S_IMODE(new_attempt.stat().st_mode) == (0o700 if mode == 0o600 else 0o750)


def test_same_opened_cache_generation_on_atomic_replacement(run, monkeypatch):
    HillslopeWatbalReport(run)
    cache = run / 'wepp/reports/cache/hillslope_watbal_summary.parquet'
    old_table, old_proof = freshness._read_cache(cache, 'hillslope_watbal_summary')
    old_copy = cache.with_name('old.parquet')
    shutil.copyfile(cache, old_copy)
    _rewrite(run / 'wepp/output/interchange/H.wat.parquet', 'P', 9.)
    HillslopeWatbalReport(run)
    new_table, new_proof = freshness._read_cache(cache, 'hillslope_watbal_summary')
    new_copy = cache.with_name('new.parquet')
    cache.rename(new_copy)
    old_copy.rename(cache)
    real_read = freshness.pq.read_table
    replaced = False
    def read_then_replace(source, *args, **kwargs):
        nonlocal replaced
        if not replaced and hasattr(source, 'fileno'):
            os.replace(new_copy, cache)
            replaced = True
        return real_read(source, *args, **kwargs)
    monkeypatch.setattr(freshness.pq, 'read_table', read_then_replace)
    observed_table, observed_proof = freshness._read_cache(cache, 'hillslope_watbal_summary')
    assert observed_table.equals(old_table) and observed_proof == old_proof
    assert observed_proof != new_proof and not observed_table.equals(new_table)


def test_characterize_historical_no_catalog_readonly_run(run):
    assert os.getuid() != 0
    expected = _rows(AverageAnnualsByLanduseReport(run))
    for relative in (AverageAnnualsByLanduseReport._LOSS_DATASET,
                     AverageAnnualsByLanduseReport._HILLSLOPE_DATASET,
                     AverageAnnualsByLanduseReport._LANDUSE_DATASET):
        (run / relative).unlink()
    shutil.rmtree(run / '_query_engine')
    mode = stat.S_IMODE(run.stat().st_mode)
    run.chmod(0o555)
    try:
        with pytest.raises(PermissionError) as error:
            AverageAnnualsByLanduseReport(run)
        print(json.dumps({'cache_rows_readable': len(expected), 'observed_error': str(error.value)}))
    finally:
        run.chmod(mode)
